from fractal.core.base import Observation
from datetime import datetime, UTC
from typing import List, Dict, Tuple
import pandas as pd
from back_test.entities.logarithm_vault import LogarithmVaultGlobalState
from back_test.entities.meta_vault import MetaVaultGlobalState
from back_test.constants import LOG_VAULT_NAMES, META_VAULT_NAME
from back_test.loader.simulations.log_vault_loader import LogVaultLoader
from back_test.loader.simulations.meta_vault_loader import MetaVaultLoader

def build_observations(with_run: bool = True) -> List[Observation]:
    """
    Build observations list from strategy backtest data, grouped by day.
    
    Returns:
        List[Observation]: List of observations containing vault states for each day
    """
    observations: List[Observation] = []
    log_vault_df: Dict[str, pd.DataFrame] = {}
    for log_vault_name in LOG_VAULT_NAMES:
        log_vault_df[log_vault_name] = LogVaultLoader(1_000_000, log_vault_name, 'back_test/data/hyperliquid').read(with_run=with_run)
    # Find the latest timestamp in all log vault dataframes
    latest_timestamp = min(df.index[-1] for df in log_vault_df.values())
    # Find the earliest timestamp in all log vault dataframes
    earliest_timestamp = max(df.index[0] for df in log_vault_df.values())
    # Clip the dataframes to the common timestamp range
    for df in log_vault_df.values():
        df = df[earliest_timestamp:latest_timestamp]
    # Load meta vault data
    meta_vault_df = MetaVaultLoader(1_000_000, earliest_timestamp, latest_timestamp, 'back_test/data/hyperliquid').read(with_run=with_run)
    # Build observations
    for timestamp in pd.date_range(start=earliest_timestamp, end=latest_timestamp, freq='d', tz=UTC):
        states = {}
        for log_vault_name in LOG_VAULT_NAMES:
            states[log_vault_name] = LogarithmVaultGlobalState(
                share_price=log_vault_df[log_vault_name].loc[timestamp]['share_price'],
                idle_assets=log_vault_df[log_vault_name].loc[timestamp]['idle_assets'],
                pending_withdrawals=log_vault_df[log_vault_name].loc[timestamp]['pending_withdrawals']
            )
        states[META_VAULT_NAME] = MetaVaultGlobalState(
            deposits=meta_vault_df.loc[timestamp]['deposits_withdrawals'] if meta_vault_df.loc[timestamp]['deposits_withdrawals'] > 0 else 0,
            withdrawals=-meta_vault_df.loc[timestamp]['deposits_withdrawals'] if meta_vault_df.loc[timestamp]['deposits_withdrawals'] < 0 else 0
        )
        observations.append(Observation(timestamp=timestamp, states=states))
    return observations

        
    

if __name__ == "__main__":
    # load strategy_backtest_data.csv for each of the logarithm vaults
    observations = build_observations()

    