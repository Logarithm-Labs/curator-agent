"""
Curator Strategy Module

This module implements a strategy for managing asset allocation across multiple logarithm vaults
using an AI agent to make allocation decisions.
"""
import time
from dataclasses import dataclass
import pandas as pd
from agents import Runner, trace, TResponseInputItem
from typing import List, Dict, Tuple
from fractal.core.base import (
    BaseStrategy, Action, BaseStrategyParams,
    ActionToTake, NamedEntity)
from fractal.core.base.observations import ObservationsStorage, SQLiteObservationsStorage
from back_test.entities.logarithm_vault import LogarithmVault, LogarithmVaultGlobalState
from back_test.entities.meta_vault import MetaVault, MetaVaultGlobalState
from curator.agents.allocation_agent import allocation_agent, AllocationAction
from curator.agents.withdraw_agent import withdraw_agent, WithdrawAction
from curator.agents.reallocation_agent import reallocation_agent, ReallocationAction
from curator.agents.analysis_agent import analysis_agent, summary_extractor
from curator.utils.validate_actions import validate_allocation, validate_withdraw, validate_redeem, validate_reallocation
from back_test.constants import LOG_VAULT_NAMES, META_VAULT_NAME
from back_test.build_observations import build_observations

DUST = 0.000001
INIT_WINDOW_SIZE = 14

@dataclass
class BaselineStrategyParams(BaseStrategyParams):
    """
    Parameters for configuring the BaselineStrategy.
    
    Attributes:
        INIT_BALANCE (float): Initial balance to start with (default: 100,000)
        WINDOW_SIZE (int): Size of the observation window (default: 7)
    """
    INIT_BALANCE: float = 100_000
    WINDOW_SIZE: int = 7
    TREND_ANALYSIS_HORIZON: int = 14
    FORECAST_HORIZON: int = 7

@dataclass
class SharePriceAnalysisResult:
    """
    Result of the share price analysis
    """
    slope: float
    forecast_price: float
    forecast_increase_rate: float

class BaselineStrategy(BaseStrategy):
    """
    Strategy implementation that uses an AI agent to manage asset allocation
    across multiple logarithm vaults.
    """
    def __init__(self, debug: bool = False, params: BaselineStrategyParams | None = None,
                 observations_storage: ObservationsStorage | None = None):
        """
        Initialize the BaselineStrategy.

        Args:
            debug (bool): Enable debug mode
            params (BaselineStrategyParams | None): Strategy parameters
            observations_storage (ObservationsStorage | None): Storage for observations
        """
        self._params: BaselineStrategyParams = None  # set for type hinting
        super().__init__(params=params, debug=debug, observations_storage=observations_storage)
        self._window_size = params.WINDOW_SIZE
        self._init_window_size = INIT_WINDOW_SIZE

    def _get_logarithm_vault_infos(self, vault_names: List[str]) -> Dict[str, Dict]:
        """Get the comprehensive information of Logarithm vaults.

        Args:
            vault_names (List): List of Logarithm vault names

        Returns:
            Dict[str, Dict]: A dictionary mapping vault names to their detailed information.
                Each vault's information contains:
                - current_share_price (float): Current price per share of the Logarithm vault
                - entry_cost_rate (float): Fee rate applied when depositing assets (as a decimal)
                - exit_cost_rate (float): Fee rate applied when withdrawing assets (as a decimal)
                - idle_assets (float): Assets in the Logarithm vault available for withdrawal without exit cost
                - pending_withdrawals (float): Assets queued for withdrawal in the Logarithm vault, offsetting entry costs
                - current_share_holding (float): Current share holding of the Logarithm vault
                - allocated_assets (float): Assets amount invested in the Logarithm vault
                - current_assets (float): Assets amount of the current share holding
        """
        vault_infos = {}
        
        for vault_name in vault_names:
            # get vault entity
            vault: LogarithmVault = self.get_entity(vault_name)
            
            if vault is None:
                raise ValueError(f"Vault {vault_name} not found")
            
            global_state: LogarithmVaultGlobalState = vault.global_state
            
            vault_info = {
                "current_share_price": float(global_state.share_price),
                "entry_cost_rate": float(vault.entry_cost_rate),
                "exit_cost_rate": float(vault.exit_cost_rate),
                "idle_assets": float(vault.idle_assets),
                "pending_withdrawals": float(vault.pending_withdrawals),
                "current_share_holding": float(vault.shares),
                "allocated_assets": float(vault.open_assets),
                "current_assets": float(vault.balance),
            }

            vault_infos[vault_name] = vault_info
        
        return vault_infos

    def _get_share_price_history(self, vault_name: str, length: int) -> pd.DataFrame:
        """Use to get the historical daily share price for a given Logarithm vault.

        Args:
            vault_name (str): Logarithm vault name
            length: Number of the most recent data points

        Returns:
            pd.DataFrame: A dataframe containing the historical daily share price for the given Logarithm vault.
                    
        """
        observations = self.observations_storage.read()
        
        # Get only the last 2 * WINDOW_SIZE of observations
        recent_observations = observations[-length:] if len(observations) > length else observations
        # Filter out observations that do not contain the vault name
        recent_observations = [observation for observation in recent_observations if vault_name in observation.states]
        # Sort observations by timestamp in ascending order
        recent_observations.sort(key=lambda x: x.timestamp, reverse=False)
        # Get the share price history for the vault
        return pd.DataFrame(
            [(observation.timestamp.isoformat(), float(observation.states[vault_name].share_price))
                for observation in recent_observations
            ],
            columns=['timestamp', 'share_price']
        )

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
        
        1. Get the share price history for the vaults
        2. Get the share price trend analysis for the vaults
        5. Get the reallocation action for the vaults

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

        if self._init_window_size != 0:
            self._init_window_size -= 1
            return []

        if self._window_size == 0:
            self._window_size = self._params.WINDOW_SIZE

            if meta_vault.idle_assets > DUST:
                return self._allocate_assets(meta_vault.idle_assets)
            elif meta_vault.pending_withdrawals > DUST:
                return self._withdraw_assets(meta_vault.pending_withdrawals)
            else:
                return self._rebalance_assets()
        else:
            self._window_size -= 1
            return []
        


    def _analyze_share_price_trend(self) -> Dict[str, SharePriceAnalysisResult]:
        """
        Analyze the share price trend for the vaults by linear regression
        """

        analysis_result: Dict[str, SharePriceAnalysisResult] = {}

        for vault_name in LOG_VAULT_NAMES:
            share_price_history = self._get_share_price_history(vault_name, self._params.TREND_ANALYSIS_HORIZON)
            slope = share_price_history['share_price'].diff().mean()
            latest_price = float(share_price_history['share_price'].iloc[-1])
            forecast_price = latest_price + slope * self._params.FORECAST_HORIZON
            forecast_increase_rate = (forecast_price - latest_price) / latest_price
            analysis_result[vault_name] = SharePriceAnalysisResult(slope, forecast_price, forecast_increase_rate)

        return analysis_result

    def _allocate_assets(self, amount: float) -> List[ActionToTake]:
        """
        Allocate assets to the vaults based on the forecast_increase_rate.
        Following the greedy algorithm
        """

        analysis_result = self._analyze_share_price_trend()
        vault_infos = self._get_logarithm_vault_infos(LOG_VAULT_NAMES)

        allocations: Dict[str, float] = {}
        
        # sort vaults in descending order by forecast_increase_rate
        sorted_vaults_by_forecast = sorted(LOG_VAULT_NAMES, key=lambda x: (analysis_result[x].forecast_increase_rate), reverse=True)

        # utilize pending withdrawals first to offset entry cost
        for vault_name in sorted_vaults_by_forecast:
            if amount > 0 and analysis_result[vault_name].forecast_increase_rate > 0:
                available_assets = min(amount, vault_infos[vault_name]['pending_withdrawals'])
                amount -= available_assets
                allocations[vault_name] = available_assets
            else:
                break
        
        if amount > 0 and analysis_result[sorted_vaults_by_forecast[0]].forecast_increase_rate > 0:
            # allocate the remaining amount to the top 1 vault
            allocations[sorted_vaults_by_forecast[0]] += amount
            amount = 0

        if amount == 0:
            return [
                ActionToTake(
                    entity_name=META_VAULT_NAME,
                    action=Action(
                        action="allocate_assets",
                        args={
                            'targets': [NamedEntity(entity_name=vault_name, entity=self.get_entity(vault_name.lower())) for vault_name in allocations.keys()],
                            'amounts': list(allocations.values())
                        }   
                    )
                )
            ]
        else:
            return []

    def _withdraw_assets(self, amount: float) -> List[ActionToTake]:
        """
        Withdraw assets from the vaults based on the forecast_increase_rate
        """

        analysis_result = self._analyze_share_price_trend()
        vault_infos = self._get_logarithm_vault_infos(LOG_VAULT_NAMES)

        withdrawals: Dict[str, float] = {}
        
        # sort vaults in ascending order by forecast_increase_rate
        sorted_vaults_by_forecast = sorted(LOG_VAULT_NAMES, key=lambda x: (analysis_result[x].forecast_increase_rate))

        # utilize idle assets first
        for vault_name in sorted_vaults_by_forecast:
            if amount > 0:
                available_assets = min(amount, vault_infos[vault_name]['current_assets'], vault_infos[vault_name]['idle_assets'])
                amount -= available_assets
                withdrawals[vault_name] = available_assets
            else:
                break
    
        # sort vaults in ascending order by exit_cost_rate
        sorted_vaults_by_exit_cost = sorted(LOG_VAULT_NAMES, key=lambda x: (vault_infos[x]['exit_cost_rate']))

        for vault_name in sorted_vaults_by_exit_cost:
            if amount > 0:
                available_assets = min(amount, vault_infos[vault_name]['current_assets'])
                amount -= available_assets
                withdrawals[vault_name] += available_assets
            else:
                break

        return [
            ActionToTake(
                entity_name=META_VAULT_NAME,
                action=Action(
                    action="withdraw_allocations",
                    args={
                        'targets': [NamedEntity(entity_name=vault_name, entity=self.get_entity(vault_name.lower())) for vault_name in withdrawals.keys()],
                        'amounts': list(withdrawals.values())
                    }
                )
            )
        ]

    def _rebalance_assets(self) -> List[ActionToTake]:
        """
        Rebalance the assets to the vaults based on the forecast_increase_rate
        """
        actions = []
        analysis_result = self._analyze_share_price_trend()
        vault_infos = self._get_logarithm_vault_infos(LOG_VAULT_NAMES)

        redemptions: Dict[str, float] = {}
        total_withdrawals = 0

        # pick redemption vaults
        for vault_name in LOG_VAULT_NAMES:
            forecast_increase_rate = analysis_result[vault_name].forecast_increase_rate
            if forecast_increase_rate < 0:
                # decide the amount to redeem based on the forecast_increase_rate and exit rate
                exit_cost_rate = vault_infos[vault_name]['exit_cost_rate']
                if exit_cost_rate < abs(forecast_increase_rate):
                    # full redeem if exit rate is smaller than or equal to the abs value of forecast_increase_rate
                    redemptions[vault_name] = vault_infos[vault_name]['current_share_holding']
                else:
                    idle_assets = vault_infos[vault_name]['idle_assets']
                    if vault_infos[vault_name]['current_assets'] > idle_assets:
                        available_assets = vault_infos[vault_name]['current_assets'] - idle_assets
                        # additional_assets * exit_cost_rate = abs(forecast_increase_rate) * (current_assets - idle_assets)
                        additional_assets = abs(forecast_increase_rate) * available_assets / exit_cost_rate
                        shares_to_redeem = self.get_entity(vault_name.lower()).preview_withdraw(additional_assets + idle_assets)
                        redemptions[vault_name] = shares_to_redeem
                    else:
                        redemptions[vault_name] = vault_infos[vault_name]['current_share_holding']
                total_withdrawals += self.get_entity(vault_name.lower()).preview_redeem(redemptions[vault_name])
        
        if total_withdrawals > 0:
            actions.append(
                ActionToTake(
                    entity_name=META_VAULT_NAME,
                    action=Action(
                        action="redeem_allocations",
                        args={
                            'targets': [NamedEntity(entity_name=vault_name, entity=self.get_entity(vault_name.lower())) for vault_name in redemptions.keys()],
                            'amounts': list(redemptions.values())
                        }
                    )
                )
            )

            actions.extend(self._allocate_assets(total_withdrawals))

        return actions
    

if __name__ == "__main__":
    observations = build_observations(False)
    # Run the strategy with an Agent
    params: BaselineStrategyParams = BaselineStrategyParams()
    strategy = BaselineStrategy(debug=True, params=params,
                                    observations_storage=SQLiteObservationsStorage())
    result = strategy.run(observations)
    print(result.get_default_metrics())  # show metrics
    result.to_dataframe().to_csv('result_baseline.csv')  # save result to csv
        
        
        
