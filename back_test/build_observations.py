from fractal.core.base import Observation
from datetime import datetime, UTC
from typing import List, Dict, Tuple
import pandas as pd
from back_test.entities.logarithm_vault import LogarithmVaultGlobalState
from back_test.entities.meta_vault import MetaVaultGlobalState
from back_test.constants import LOG_VAULT_NAMES, META_VAULT_NAME
from back_test.loader.simulations.vaults_loader import VaultsLoader

def build_observations(with_run: bool = True) -> List[Observation]:
    """
    Build observations list from strategy backtest data, grouped by day.
    
    Returns:
        List[Observation]: List of observations containing vault states for each day
    """
    observations: List[Observation] = []
    vault_data = VaultsLoader(1_000_000, LOG_VAULT_NAMES, META_VAULT_NAME, 'back_test/data/hyperliquid').read(with_run=with_run)
    min_length = min(len(df) for df in vault_data.values())
    for i in range(min_length):
        states = {}
        timestamp = None
        for vault_name in LOG_VAULT_NAMES:
            df = vault_data[vault_name]
            timestamp = pd.to_datetime(df.index[i]).to_pydatetime().astimezone(UTC)
            states[vault_name] = LogarithmVaultGlobalState(
                share_price=df.iloc[i]['share_price'], 
                idle_assets=df.iloc[i]['idle_assets'],
                pending_withdrawals=df.iloc[i]['pending_withdrawals']
            )
        meta_state = vault_data[META_VAULT_NAME].iloc[i]
        states[META_VAULT_NAME] = MetaVaultGlobalState(
            deposits=meta_state['deposits_withdrawals'] if meta_state['deposits_withdrawals'] > 0 else 0,
            withdrawals=-meta_state['deposits_withdrawals'] if meta_state['deposits_withdrawals'] < 0 else 0,
        )
        observations.append(Observation(timestamp=timestamp, states=states))
    return observations

        
    

if __name__ == "__main__":
    # load strategy_backtest_data.csv for each of the logarithm vaults
    observations = build_observations()

    