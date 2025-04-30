import random
from pathlib import Path
from typing import List
from uuid import uuid4
import numpy as np
import pandas as pd
from fractal.loaders.base_loader import Loader, LoaderType
from fractal.loaders.structs import PriceHistory
from typing import List, Dict, Tuple
from datetime import datetime, UTC

class VaultsLoader(Loader):
    """
    A class that represents a Vaults states loader.

    This loader performs Monte Carlo simulation for each data point

    Attributes:
        log_vault_names: The list of Logarithm vault names
        meta_vault_name: The name of meta vault
        data_base_path: The base path to the back tested vault data
        interval: The interval of observations
        seed (int): The seed value used for random number generation.

    Methods:
        extract(): Extracts the vault states from the base loader.
        transform(): Performs Monte Carlo simulation on the vault states.
        load(): Saves the simulated vault states using the specified loader type.
        read(with_run: bool = False): Reads the simulated
            vault states from the saved file.
        run(): Executes the entire process of extracting,
            transforming, and loading the data.
    """

    def __init__(
        self,
        init_balance: float,
        log_vault_names: list[str],
        meta_vault_name: str,
        data_base_path: str,
        interval: str = 'd',
        seed: int = 420,
    ) -> None:
        super().__init__()
        self._data = None
        self.init_balance = init_balance
        self.log_vault_names = log_vault_names
        self.meta_vault_name = meta_vault_name
        self.data_base_path = data_base_path
        self.interval = interval
        self._file_id = "simulated_data"
        self._random = random.Random()
        self._random.seed(seed)
    
    def get_data(self) -> Dict[str, pd.DataFrame]:
        vault_data: Dict[str, pd.DataFrame] = {}
        for vault_name in self.log_vault_names:
            with open(f"{self.data_base_path}/{vault_name}/strategy_backtest_data.csv", "r") as f:
                df = pd.read_csv(f)
                # Convert timestamp to datetime and set as index
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                df = df.sort_index()
                # Group by day and take the last value of each day
                df = df.resample('d').last()
                vault_data[vault_name] = df

        return vault_data
    
    def get_dict_data(self, vault_names: List) -> Dict[str, pd.DataFrame]:
        return {
            vault_name: self._data[self._data['vault_name']==vault_name].drop(columns='vault_name').set_index('timestamp') for vault_name in vault_names
        }
    
    def flatten_data(self, vault_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(vault_data, names=['vault_name']).reset_index()

    def extract(self):
        self._data = self.flatten_data(self.get_data())

    def transform(self):
        dict_data = self.get_dict_data(self.log_vault_names)
        for vault_name in self.log_vault_names:
            # self._data[self._data['vault_name']==vault_name].copy()
            dict_data[vault_name]['share_price'] = dict_data[vault_name]['net_balance'] / self.init_balance
            idle_assets_array = []
            pending_withdrawals_array = []
            for _ in range(len(dict_data[vault_name])):
                assets = self._random.normalvariate(0, self.init_balance / 1000)
                idle_assets_array.append(assets if assets > 0 else 0)
                pending_withdrawals_array.append(-assets if assets < 0 else 0)
            dict_data[vault_name]['idle_assets'] = np.array(idle_assets_array)
            dict_data[vault_name]['pending_withdrawals'] = np.array(pending_withdrawals_array)

        # Generate meta vault data with only timestamp and deposits/withdrawals fields
        timestamps = pd.date_range(
            start=dict_data[self.log_vault_names[0]].index[0],
            end=dict_data[self.log_vault_names[0]].index[-1],
            freq=self.interval
        )
        deposits_withdrawals = [
            self._random.uniform(-self.init_balance / 200, self.init_balance / 200) if self._random.randint(0,1) == 0 else 0  
            for _ in range(len(timestamps))
        ]
        meta_vault_data = pd.DataFrame({
            'timestamp': timestamps,
            'deposits_withdrawals': deposits_withdrawals
        })
        meta_vault_data.set_index('timestamp', inplace=True)
        dict_data[self.meta_vault_name] = meta_vault_data

        # Slice data based on timestamp so that all vaults data have the same timestamp range
        common_start = max(
            dict_data[vault_name].index[0] for vault_name in self.log_vault_names + [self.meta_vault_name]
        )
        common_end = min(
            dict_data[vault_name].index[-1] for vault_name in self.log_vault_names + [self.meta_vault_name]
        )
        for vault_name in self.log_vault_names + [self.meta_vault_name]:
            dict_data[vault_name] = dict_data[vault_name].loc[common_start:common_end]
        self._data = self.flatten_data(dict_data)

    def load(self):
        self._load(self._file_id)

    def read(self, with_run: bool = False) -> Dict[str, pd.DataFrame]:
        if with_run:
            self.run()
        else:
            self._read(self._file_id)

        return self.get_dict_data(self.log_vault_names + [self.meta_vault_name])

    def delete_dump_file(self):
        Path(self.file_path(self._file_id)).unlink(missing_ok=True)
