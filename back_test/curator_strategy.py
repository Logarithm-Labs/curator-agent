"""
Curator Strategy Module

This module implements a strategy for managing asset allocation across multiple logarithm vaults
using an AI agent to make allocation decisions.
"""
import math
import time
from dataclasses import dataclass
from agents import function_tool, Runner, Agent, trace, TResponseInputItem
from typing import List, Dict, Tuple
from fractal.core.base import (
    BaseStrategy, Action, BaseStrategyParams,
    ActionToTake, NamedEntity)
from fractal.core.base.observations import ObservationsStorage, SQLiteObservationsStorage
from back_test.entities.logarithm_vault import LogarithmVault, LogarithmVaultGlobalState
from back_test.entities.meta_vault import MetaVault, MetaVaultGlobalState
from back_test.prompts import ACTIVE_PROMPT
from curator.agents.allocation_agent import allocation_agent, AllocationAction
from curator.agents.withdraw_agent import withdraw_agent, WithdrawAction
from curator.agents.reallocation_agent import reallocation_agent, ReallocationAction
from curator.agents.analysis_agent import analysis_agent, summary_extractor
from curator.utils.validate_actions import validate_allocation, validate_withdraw, validate_redeem, validate_reallocation
from back_test.constants import LOG_VAULT_NAMES, META_VAULT_NAME
from back_test.build_observations import build_observations

DUST = 0.000001
@dataclass
class CuratorStrategyParams(BaseStrategyParams):
    """
    Parameters for configuring the CuratorStrategy.
    
    Attributes:
        INIT_BALANCE (float): Initial balance to start with (default: 100,000)
        WINDOW_SIZE (int): Size of the observation window (default: 7)
        MODEL (str): Name of the AI model to use (default: 'gpt-4-turbo')
        PROMPT (str): Prompt template for the AI agent (default: ACTIVE_PROMPT)
    """
    INIT_BALANCE: float = 100_000
    WINDOW_SIZE: int = 7
    MODEL: str = 'gpt-4-turbo'
    PROMPT: str = ACTIVE_PROMPT

class CuratorStrategy(BaseStrategy):
    """
    Strategy implementation that uses an AI agent to manage asset allocation
    across multiple logarithm vaults.
    """
    def __init__(self, debug: bool = False, params: CuratorStrategyParams | None = None,
                 observations_storage: ObservationsStorage | None = None):
        """
        Initialize the CuratorStrategy.

        Args:
            debug (bool): Enable debug mode
            params (CuratorStrategyParams | None): Strategy parameters
            observations_storage (ObservationsStorage | None): Storage for observations
        """
        self._params: CuratorStrategyParams = None  # set for type hinting
        super().__init__(params=params, debug=debug, observations_storage=observations_storage)
        agents = self.__create_agent()
        self._allocation_agent = agents['allocation_agent']
        self._reallocation_agent = agents['reallocation_agent']
        self._withdraw_agent = agents['withdraw_agent']
        self._window_size = params.WINDOW_SIZE

    def __create_agent(self) -> Dict[str, Agent]:
        """
        Create and configure the AI agent with necessary tools for vault management.

        Returns:
            Dict[str, Agent]: Dictionary of agents, where the key is the agent's name and the value is the agent instance
        """
        
        @function_tool
        def get_logarithm_vault_infos(vault_names: List[str]) -> Dict[str, Dict]:
            """Get the comprehensive information of Logarithm vaults.

            Input:
                vault_names (List): List of Logarithm vault names

            Returns:
                Dict[str, Dict]: A dictionary mapping vault names to their detailed information.
                    Each vault's information contains:
                    - share_price (float): Current price per share of the Logarithm vault
                    - entry_cost_rate (float): Fee rate applied when depositing assets (as a decimal)
                    - exit_cost_rate (float): Fee rate applied when withdrawing assets (as a decimal)
                    - idle_assets (float): Assets in the Logarithm vault available for withdrawal without exit cost
                    - pending_withdrawals (float): Assets queued for withdrawal in the Logarithm vault, offsetting entry costs
            """
            vault_infos = {}
            
            for vault_name in vault_names:
                # get vault entity
                vault: LogarithmVault = self.get_entity(vault_name)
                
                if vault is None:
                    raise ValueError(f"Vault {vault_name} not found")
                
                global_state: LogarithmVaultGlobalState = vault.global_state
                
                vault_info = {
                    "share_price": float(global_state.share_price),
                    "entry_cost_rate": float(vault.entry_cost_rate),
                    "exit_cost_rate": float(vault.exit_cost_rate),
                    "idle_assets": float(vault.idle_assets),
                    "pending_withdrawals": float(vault.pending_withdrawals),
                }

                vault_infos[vault_name] = vault_info
            
            return vault_infos

        @function_tool
        def get_share_price_history(vault_name: str, length: int) -> List[Tuple[str, float]]:
            """Use to get the historical daily share price for a given Logarithm vault.

            Input:
                vault_name (str): Logarithm vault name
                length: Number of the most recent data points

            Returns:
                List[Tuple[str, float]]: List of tuples containing:
                    - timestamp: Timestamp of the observation as ISO format string
                    - share_price: Share price of the vault as float
                        
            """
            observations = self.observations_storage.read()
            
            # Get only the last 2 * WINDOW_SIZE of observations
            recent_observations = observations[-length:] if len(observations) > length else observations
            # Filter out observations that do not contain the vault name
            recent_observations = [observation for observation in recent_observations if vault_name in observation.states]
            # Sort observations by timestamp in ascending order
            recent_observations.sort(key=lambda x: x.timestamp, reverse=False)
            # Get the share price history for the vault
            return [
                (observation.timestamp.isoformat(), float(observation.states[vault_name].share_price))
                for observation in recent_observations
            ]
        
        # @function_tool
        # def allocate_action_validation(vault_names: list[str], amounts: list[float]) -> str:
        #     """Validate the allocation action.

        #     Args:
        #         vault_names (list[str]): List of logarithm vault names
        #         amounts (list[float]): List of amounts
        #     """
        #     return "Validation successful"
        
        analysis_agent_with_tools = analysis_agent.clone(tools=[get_share_price_history])
        analysis_tool = analysis_agent_with_tools.as_tool(
            tool_name="share_price_trend_analysis",
            tool_description="Use to get performance trends of given logarithm vaults which are separated by commas.",
            custom_output_extractor=summary_extractor
        )

        allocation_agent_with_tools = allocation_agent.clone(tools=[get_logarithm_vault_infos, analysis_tool])
        withdraw_agent_with_tools = withdraw_agent.clone(tools=[get_logarithm_vault_infos, analysis_tool])
        reallocation_agent_with_tools = reallocation_agent.clone(tools=[get_logarithm_vault_infos, analysis_tool])

        return {
            "allocation_agent": allocation_agent_with_tools,
            "withdraw_agent": withdraw_agent_with_tools,
            "reallocation_agent": reallocation_agent_with_tools
        }

    def set_up(self):
        """
        Set up the initial state of the strategy by:
        1. Registering the meta vault and logarithm vaults
        2. Depositing initial balance into the meta vault
        """
        self.register_entity(NamedEntity(entity_name=META_VAULT_NAME, entity=MetaVault()))
        for vault_name in LOG_VAULT_NAMES:
            self.register_entity(NamedEntity(entity_name=vault_name, entity=LogarithmVault()))
        meta_vault = self.get_entity(META_VAULT_NAME)
        meta_vault.action_deposit(self._params.INIT_BALANCE)

    def predict(self, *args, **kwargs) -> List[ActionToTake]:
        """
        Make predictions about asset allocation actions based on current market conditions.

        Returns:
            List[ActionToTake]: List of actions to take for asset allocation
        """
        meta_vault: MetaVault = self.get_entity(META_VAULT_NAME)
        meta_vault_state: MetaVaultGlobalState = meta_vault.global_state
        if meta_vault_state.deposits > 0:
            meta_vault.action_deposit(meta_vault_state.deposits)
        elif meta_vault_state.withdrawals > 0:
            assets = min(meta_vault_state.withdrawals, meta_vault.total_assets)
            meta_vault.action_withdraw(assets)

        if self._window_size == 0:
            # predict actions
            actions = []

            # reallocation check
            msg = f"Share holdings for each vault:\n "
            balances: dict[str, float] = {}
            for vault_name in LOG_VAULT_NAMES:
                vault: LogarithmVault = self.get_entity(vault_name)
                msg += f"- `{vault_name}`: {vault.shares} \n"
                balances[vault_name] = vault.shares
                    
            input_items: list[TResponseInputItem] = [{"content": msg, "role": "user"}]

            with trace("Reallocation with Feedback"):
                while True:
                    res = Runner.run_sync(
                        self._reallocation_agent,
                        input_items
                    )
                    input_items = res.to_input_list()
                    reallocation_prediction: ReallocationAction = res.final_output
                    validation_result = validate_redeem(reallocation_prediction.redeem_vault_names, reallocation_prediction.redeem_share_amounts, balances)
                    if validation_result.result == 'pass':
                        validation_result = validate_reallocation(reallocation_prediction.allocation_vault_names, reallocation_prediction.allocation_weights)
                        if validation_result.result == 'pass':
                            self._debug(f"Action: reallocation, Prediction: {reallocation_prediction}")
                            if len(reallocation_prediction.redeem_vault_names) > 0:
                                assets_to_redeem = [
                                    self.get_entity(redeem_vault_name.lower()).preview_redeem(redeem_share_amount)
                                    for (redeem_vault_name, redeem_share_amount) in zip(reallocation_prediction.redeem_vault_names, reallocation_prediction.redeem_share_amounts)
                                ]
                                total_idle = sum(assets_to_redeem) + meta_vault.idle_assets- meta_vault.pending_withdrawals

                                if len(reallocation_prediction.redeem_vault_names) > 0:
                                    actions.append(
                                        ActionToTake(
                                            entity_name=META_VAULT_NAME,
                                            action=Action(
                                                action="redeem_allocations",
                                                args={
                                                    'targets': [NamedEntity(entity_name=redeem_vault_name, entity=self.get_entity(redeem_vault_name.lower())) for redeem_vault_name in reallocation_prediction.redeem_vault_names],
                                                    'amounts': reallocation_prediction.redeem_share_amounts
                                                }
                                            )
                                        )
                                    )

                                    # debug the vault names and assets amounts that are going to be withdrawn
                                    self._debug(f"Action: redeem_allocations, vault_names: {reallocation_prediction.redeem_vault_names}, amounts: {assets_to_redeem}")
                                
                                if total_idle > 0 and len(reallocation_prediction.allocation_vault_names) > 0:
                                    assets_to_allocate = [total_idle * weight for weight in reallocation_prediction.allocation_weights[:-1]]
                                    allocated_sum = sum(assets_to_allocate)
                                    last_allocation = total_idle - allocated_sum
                                    assets_to_allocate.append(last_allocation)
                                    actions.append(
                                        ActionToTake(
                                            entity_name=META_VAULT_NAME,
                                            action=Action(
                                                action="allocate_assets",
                                                args={
                                                    'targets': [NamedEntity(entity_name=allocation_vault_name, entity=self.get_entity(allocation_vault_name.lower())) for allocation_vault_name in reallocation_prediction.allocation_vault_names],
                                                    'amounts': assets_to_allocate
                                                }
                                            )
                                        )
                                    )

                                    # debug the vault names and assets amounts to which to allocate withdrawn assets
                                    self._debug(f"Action: allocate_assets, vault_names: {reallocation_prediction.allocation_vault_names}, amounts: {assets_to_allocate}")

                            break
                        else:
                            self._debug(f"Action(Failed): reallocation, Prediction: {reallocation_prediction}")
                            input_items.append({"content": f"Feedback: {validation_result.feedback}", "role": "user"})
                    else:
                        self._debug(f"Action(Failed): reallocation, Prediction: {reallocation_prediction}")
                        input_items.append({"content": f"Feedback: {validation_result.feedback}", "role": "user"})

            if len(actions) == 0 and meta_vault.idle_assets > DUST:
                msg = f"Total asset amount to allocate is {meta_vault.idle_assets}.\n"
                msg += f"The target vaults are {LOG_VAULT_NAMES}.\n"
                msg += f"Sum of the output amounts must be the same as the total asset amount {meta_vault.idle_assets}"
                input_items: list[TResponseInputItem] = [{"content": msg, "role": "user"}]

                with trace("Allocation with Feedback"):
                    while True:
                        res = Runner.run_sync(
                            self._allocation_agent,
                            input_items
                        )
                        input_items = res.to_input_list()
                        prediction: AllocationAction = res.final_output
                        validation_result = validate_allocation(meta_vault.idle_assets, prediction.vault_names, prediction.amounts)
                        if validation_result.result == 'pass':
                            self._debug(f"Action: allocate_assets, Prediction: {prediction}")
                            actions.append(
                                ActionToTake(
                                    entity_name=META_VAULT_NAME,
                                    action=Action(
                                        action="allocate_assets",
                                        args={
                                            'targets': [NamedEntity(entity_name=vault_name, entity=self.get_entity(vault_name.lower())) for vault_name in prediction.vault_names],
                                            'amounts': prediction.amounts
                                        }
                                    )
                                )
                            )
                            break
                        else:
                            self._debug(f"Action(Failed): allocate_assets, Prediction: {prediction}")
                            input_items.append({"content": f"Feedback: {validation_result.feedback}", "role": "user"})

            elif len(actions) == 0 and meta_vault.pending_withdrawals > DUST:
                msg = f"Total asset amount to withdraw is {meta_vault.pending_withdrawals}.\n Allocated asset amount for each vault:\n "
                balances: dict[str, float] = {}
                for vault_name in LOG_VAULT_NAMES:
                    vault: LogarithmVault = self.get_entity(vault_name)
                    if vault.balance > 0:
                        msg += f"- `{vault_name}`: {vault.balance} \n"
                        balances[vault_name] = vault.balance
                msg += f"\nSum of the output amounts must be the same as the total asset amount {meta_vault.pending_withdrawals}."
                input_items: list[TResponseInputItem] = [{"content": msg, "role": "user"}]

                with trace("Withdraw with Feedback"):
                    while True:
                        res = Runner.run_sync(
                            self._withdraw_agent,
                            input_items
                        )
                        input_items = res.to_input_list()
                        prediction: WithdrawAction = res.final_output
                        validation_result = validate_withdraw(meta_vault.pending_withdrawals, prediction.vault_names, prediction.amounts, balances)
                        if validation_result.result == 'pass':
                            self._debug(f"Action: withdraw_allocations, Prediction: {prediction}")
                            actions.append(
                                ActionToTake(
                                    entity_name=META_VAULT_NAME,
                                    action=Action(
                                        action="withdraw_allocations",
                                        args={
                                            'targets': [NamedEntity(entity_name=vault_name, entity=self.get_entity(vault_name.lower())) for vault_name in prediction.vault_names],
                                            'amounts': prediction.amounts
                                        }
                                    )
                                )
                            )
                            break
                        else:
                            self._debug(f"Action(Failed): withdraw_allocations, Prediction: {prediction}")
                            input_items.append({"content": f"Feedback: {validation_result.feedback}", "role": "user"})
            # sleep to avoid rate limit
            time.sleep(1)
            self._window_size = self._params.WINDOW_SIZE
            return actions
        else:
            self._window_size -= 1
            return []

if __name__ == "__main__":
    # load strategy_backtest_data.csv for each of the logarithm vaults
    observations = build_observations(False)
    # Run the strategy with an Agent
    params: CuratorStrategyParams = CuratorStrategyParams()
    strategy = CuratorStrategy(debug=True, params=params,
                                    observations_storage=SQLiteObservationsStorage())
    result = strategy.run(observations)
    print(result.get_default_metrics())  # show metrics
    result.to_dataframe().to_csv('result.csv')  # save result to csv
        
        
        
