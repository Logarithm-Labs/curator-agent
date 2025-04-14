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
from prompts import REFINED_PROMPT
from openai_agent import create_agent, ActionList

# Define vault names
LOG_VAULT_NAMES = ['btc', 'eth', 'doge', 'pepe']

@dataclass
class CuratorStrategyParams(BaseStrategyParams):
    """
    Parameters for configuring the CuratorStrategy.
    
    Attributes:
        INIT_BALANCE (float): Initial balance to start with (default: 100,000)
        WINDOW_SIZE (int): Size of the observation window (default: 30)
        MODEL (str): Name of the AI model to use (default: 'gpt-4o-mini')
        PROMPT (str): Prompt template for the AI agent (default: PROMPT)
    """
    INIT_BALANCE: float = 100_000
    WINDOW_SIZE: int = 300
    MODEL: str = 'gpt-4o-mini'
    PROMPT: str = REFINED_PROMPT

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
        
        @function_tool
        def get_logarithm_vault_infos() -> List[Dict]:
            """Get comprehensive information about all logarithm vaults.

            Returns:
                List[Dict]: List of dictionaries containing vault information, where each dictionary contains:
                    - vault_name: Name of the vault
                    - share_price: Current share price of the vault as float
                    - entry_cost_rate: Entry cost rate for the vault as float
                    - exit_cost_rate: Exit cost rate for the vault as float
                    - free_assets: Free assets in the vault as float
                    - pending_withdrawals: Pending withdrawals from the vault as float
                    - meta_vault_shares: Number of shares held by the meta vault as float
            """
            vault_infos = []
            
            for vault_name in LOG_VAULT_NAMES:
                # get vault entity
                vault: LogarithmVault = self.get_entity(vault_name)
                global_state: LogarithmVaultGlobalState = vault.global_state
                internal_state: LogarithmVaultInternalState = vault.internal_state
                
                vault_info = {
                    "vault_name": vault_name,
                    "share_price": float(global_state.share_price),
                    "entry_cost_rate": float(vault.entry_cost()),
                    "exit_cost_rate": float(vault.exit_cost()),
                    "free_assets": float(0),
                    "pending_withdrawals": float(0),
                    "meta_vault_shares": float(internal_state.shares)
                }
                vault_infos.append(vault_info)
            
            return vault_infos

        @function_tool
        def get_share_price_history() -> Dict[str, List[Dict[str, str | float]]]:
            """Get the share price history of all logarithm vaults.  

            Returns:
                Dict[str, List[Dict[str, str | float]]]: Dictionary where:
                    - Key: Vault name
                    - Value: List of dictionaries containing:
                        - timestamp: Timestamp of the observation as ISO format string
                        - share_price: Share price of the vault as float
            """
            observations = self.observations_storage.read()
            history = {}
            
            for vault_name in LOG_VAULT_NAMES:
                history[vault_name] = [
                    {
                        'timestamp': observation.timestamp.isoformat(),
                        'share_price': float(observation.states[vault_name].share_price)
                    } 
                    for observation in observations
                ]
            
            return history
        
        @function_tool
        def get_meta_vault_infos() -> Dict:
            """Get comprehensive information about the meta vault.

            Returns:
                Dict: Dictionary containing:
                    - idle_assets: Amount of idle assets in the meta vault as float
                    - total_assets: Total assets in the meta vault (idle + allocated) as float
            """
            meta_vault: MetaVault = self.get_entity("meta_vault")
            internal_state: MetaVaultInternalState = meta_vault.internal_state
            
            return {
                "idle_assets": float(internal_state.assets),
                "total_assets": float(meta_vault.balance)
            }
        
        return create_agent(
            tools=[
                get_logarithm_vault_infos,
                get_share_price_history,
                get_meta_vault_infos
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
        meta_vault = self.get_entity('meta_vault')
        meta_vault.action_deposit(self._params.INIT_BALANCE)

    def predict(self, *args, **kwargs) -> List[ActionToTake]:
        """
        Make predictions about asset allocation actions based on current market conditions.

        Returns:
            List[ActionToTake]: List of actions to take for asset allocation
        """
        if self._window_size == 0:
            res = Runner.run_sync(
                self._agent,
                "Make a prediction of actions to take, and return empty action list if no action is needed",
            )
            prediction: ActionList = res.final_output
            self._debug(prediction)
            # sleep to avoid rate limit
            time.sleep(5)
            self._window_size = self._params.WINDOW_SIZE
            actions = prediction.actions
            if len(actions) > 0:
                return [
                    ActionToTake(
                        entity_name="meta_vault",
                        action=Action(
                            action=action.name.lower(),
                            args={
                                'targets': [NamedEntity(entity_name=vault_name, entity=self.get_entity(vault_name)) for vault_name in action.vault_names],
                                'amounts': action.amounts
                            }
                        )
                    ) 
                    for action in actions
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
        
        
        
