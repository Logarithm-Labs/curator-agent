"""
Curator Strategy Module

This module implements a strategy for managing asset allocation across multiple logarithm vaults
using an AI agent to make allocation decisions.
"""

import time
import pandas as pd
from dataclasses import dataclass
from datetime import datetime, UTC
from agents import function_tool, Runner, Agent
from typing import List, Dict, Tuple
from fractal.core.base import (
    BaseStrategy, Action, BaseStrategyParams,
    ActionToTake, NamedEntity, Observation)
from fractal.core.base.observations import ObservationsStorage, SQLiteObservationsStorage
from entities.logarithm_vault import LogarithmVault, LogarithmVaultGlobalState, LogarithmVaultInternalState
from entities.meta_vault import MetaVault, MetaVaultInternalState
from prompts import PROMPT
from openai_agent import create_agent, AgentAction

# Define vault names
LOG_VAULT_NAMES = ['btc', 'eth', 'doge', 'pepe']

@dataclass
class CuratorStrategyParams(BaseStrategyParams):
    """
    Parameters for configuring the CuratorStrategy.
    
    Attributes:
        INIT_BALANCE (float): Initial balance to start with (default: 100,000)
        WINDOW_SIZE (int): Size of the observation window (default: 30)
        MODEL (str): Name of the AI model to use (default: 'o3-mini')
        PROMPT (str): Prompt template for the AI agent (default: PROMPT)
    """
    INIT_BALANCE: float = 100_000
    WINDOW_SIZE: int = 30
    MODEL: str = 'o3-mini'
    PROMPT: str = PROMPT

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
        self._agent = self.__create_agent()
        self._window_size = params.WINDOW_SIZE

    def __create_agent(self) -> Agent:
        """
        Create and configure the AI agent with necessary tools for vault management.

        Returns:
            Agent: Configured AI agent instance
        """
        # define tools for agent to utilize
        @function_tool
        def get_available_vaults() -> List[str]:
            """Get the list of available Logarithm vaults to allocate assets to.

            Returns:
                List[str]: List of available vaults' names
            """
            return LOG_VAULT_NAMES
        
        @function_tool
        def get_share_price(vault_name: str) -> float:
            """Get the share price of a given logarithm vault.

            Args:
                vault_name (str): Name of the vault

            Returns:
                float: Share price of the vault
            """

            if vault_name == "meta_vault":
                raise ValueError("Meta vault does not have a share price")
            
            # get vault entity
            vault: LogarithmVault = self.get_entity(vault_name)
            global_state: LogarithmVaultGlobalState = vault.global_state
            return global_state.share_price
        
        @function_tool
        def get_share_price_history(vault_name: str) -> List[Tuple[float, float]]:
            """Get the share price history of a given logarithm vault.  

            Args:
                vault_name (str): Name of the vault

            Returns:
                List[Tuple[float, float]]: Share price history of the vault, timestamp and share price
            """
            # get vault entity
            observations = self.observations_storage.read()
            return [(observation.timestamp, observation.states[vault_name].share_price) for observation in observations]
        
        @function_tool
        def preview_deposit(vault_name: str, assets: float) -> float:
            """Preview the amount of shares that will be received from depositing a given amount of assets.

            Args:
                vault_name (str): Name of the logarithm vault
                assets (float): Amount of assets to deposit
            
            Returns:
                float: Amount of shares that will be received
            """

            if vault_name == "meta_vault":
                raise ValueError("Meta vault does not have a share price")
            
            # get vault entity
            vault: LogarithmVault = self.get_entity(vault_name)
            return vault.preview_deposit(assets)
        
        @function_tool
        def preview_redeem(vault_name: str, shares: float) -> float:
            """Preview the amount of assets that will be received from redeeming a given amount of shares.

            Args:
                vault_name (str): Name of the logarithm vault
                shares (float): Amount of shares to redeem
            
            Returns:
                float: Amount of assets that will be received
            """

            if vault_name == "meta_vault":
                raise ValueError("Meta vault does not have a share price")

            # get vault entity
            vault: LogarithmVault = self.get_entity(vault_name)
            return vault.preview_redeem(shares)
        
        @function_tool
        def preview_withdraw(vault_name: str, assets: float) -> float:
            """Preview the amount of shares that will be burned from withdrawing a given amount of assets.

            Args:
                vault_name (str): Name of the logarithm vault
                assets (float): Amount of assets to withdraw
            
            Returns:
                float: Amount of shares that will be burned
            """

            if vault_name == "meta_vault":
                raise ValueError("Meta vault does not have a share price")
            
            # get vault entity
            vault: LogarithmVault = self.get_entity(vault_name)
            return vault.preview_withdraw(assets)
        
        @function_tool
        def get_balance_of(vault_name: str) -> float:
            """Get the balance of shares for the meta vault in a given logarithm vault.

            Args:
                vault_name (str): Name of the logarithm vault

            Returns:
                float: Balance of shares
            """

            if vault_name == "meta_vault":
                raise ValueError("Meta vault does not have a balance")
            
            # get vault entity
            vault: LogarithmVault = self.get_entity(vault_name)
            internal_state: LogarithmVaultInternalState = vault.internal_state
            return internal_state.shares
        
        @function_tool
        def get_allocated_vaults() -> List[str]:
            """Get the list of allocated logarithm vaults for the meta vault.

            Returns:
                List[str]: List of allocated vaults' names
            """
            meta_vault: MetaVault = self.get_entity("meta_vault")
            internal_state: MetaVaultInternalState = meta_vault.internal_state
            return [vault.entity_name for vault in internal_state.allocated_vaults]
        
        @function_tool
        def get_idle_assets() -> float:
            """Get the idle assets for the meta vault.

            Returns:
                float: Idle assets
            """
            meta_vault: MetaVault = self.get_entity("meta_vault")
            internal_state: MetaVaultInternalState = meta_vault.internal_state
            return internal_state.assets
        
        @function_tool
        def get_total_assets() -> float:
            """Get the total assets for the meta vault.

            Returns:
                float: Total assets
            """
            meta_vault: MetaVault = self.get_entity("meta_vault")
            return meta_vault.balance
        
        return create_agent(
            tools=[
                get_available_vaults,
                get_share_price,
                get_share_price_history,
                preview_deposit,
                preview_redeem,
                preview_withdraw,
                get_balance_of,
                get_allocated_vaults,
                get_idle_assets,
                get_total_assets
            ],
            prompt=self._params.PROMPT,
            model=self._params.MODEL
        )
            
    def set_up(self):
        """
        Set up the initial state of the strategy by:
        1. Registering the meta vault and logarithm vaults
        2. Depositing initial balance into the meta vault
        """
        self.register_entity(NamedEntity(entity_name="meta_vault", entity=MetaVault()))
        for vault_name in LOG_VAULT_NAMES:
            self.register_entity(NamedEntity(entity_name=vault_name, entity=LogarithmVault()))

    def predict(self, *args, **kwargs) -> List[ActionToTake]:
        """
        Make predictions about asset allocation actions based on current market conditions.

        Returns:
            List[ActionToTake]: List of actions to take for asset allocation
        """
        if self._window_size == 0:
            res = Runner.run_sync(
                self._agent,
                "Make a prediction of actions to take"
            )
            prediction: List[AgentAction] = res.final_output
            self._debug(prediction)
            # sleep to avoid rpc rate limit
            time.sleep(1)
            self._window_size = self._params.WINDOW_SIZE
            if len(prediction) > 0:
                return [
                    ActionToTake(
                        entity_name="meta_vault",
                        action=Action(
                            action=action.action.lower(),
                            args={
                                'targets': [NamedEntity(name=vault_name, entity=self.get_entity(vault_name)) for vault_name in action.vault_names],
                                'amounts': action.amounts
                            }
                        )
                    ) 
                    for action in prediction
                ]
            else:
                return []
        else:
            self._window_size -= 1
            return []


def build_observations() -> List[Observation]:
    """
    Build observations list from strategy backtest data.
    
    Returns:
        List[Observation]: List of observations containing vault states
    """
    observations: List[Observation] = []
    vault_data: Dict[str, pd.DataFrame] = {}
    
    # Load strategy backtest data for each vault
    for vault_name in LOG_VAULT_NAMES:
        with open(f"back_test/data/hyperliquid/{vault_name}/strategy_backtest_data.csv", "r") as f:
            vault_data[vault_name] = pd.read_csv(f)
    
    # Get the minimum length of data across all vaults
    min_length = min(len(df) for df in vault_data.values())
    
    # Build observations list
    for i in range(min_length):
        states = {}
        for vault_name in LOG_VAULT_NAMES:
            df = vault_data[vault_name]
            initial_balance = df.iloc[0]['net_balance']
            current_balance = df.iloc[i]['net_balance']
            share_price = current_balance / initial_balance
            timestamp = datetime.fromisoformat(df.iloc[i]['timestamp']).astimezone(UTC)
            states[vault_name] = LogarithmVaultGlobalState(share_price=share_price)
        
        observations.append(Observation(timestamp=timestamp, states=states))
    
    return observations

if __name__ == "__main__":
    # load strategy_backtest_data.csv for each of the logarithm vaults
    observations = build_observations()
     # Run the strategy with an Agent
    params: CuratorStrategyParams = CuratorStrategyParams()
    strategy = CuratorStrategy(debug=True, params=params,
                                    observations_storage=SQLiteObservationsStorage())
    result = strategy.run(observations)
    print(result.get_default_metrics())  # show metrics
    result.to_dataframe().to_csv('result.csv')  # save result to csv
        
        
        
