import random
from pathlib import Path
import numpy as np
import pandas as pd
from fractal.loaders.base_loader import Loader
from typing import Dict
from datetime import UTC

class LogVaultLoader(Loader):
    """
    A class that represents a Logarithm vault states loader.

    This loader performs Monte Carlo simulation for each data point

    Attributes:
        log_vault_name: The name of the Logarithm vault
        init_balance: The initial balance of the vault
        std_deviation_ratio: The ratio of the standard deviation to the initial balance that is used to simulate pending amounts
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
        log_vault_name: str,
        init_balance: float,
        std_deviation_ratio: float,
        data_base_path: str,
        interval: str = 'd',
        seed: int = 420,
    ) -> None:
        super().__init__()
        self._data = None
        self.init_balance = init_balance
        self.std_deviation_ratio = std_deviation_ratio
        self.log_vault_name = log_vault_name
        self.data_base_path = data_base_path
        self.interval = interval
        self._file_id = f"{self.log_vault_name}_simulated_data"
        self._random = random.Random()
        self._random.seed(seed)
    
    def get_data(self) -> pd.DataFrame:
        with open(f"{self.data_base_path}/{self.log_vault_name}/strategy_backtest_data.csv", "r") as f:
            df = pd.read_csv(f)
            # Convert timestamp to datetime and ensure UTC timezone
            timestamps = pd.to_datetime(df['timestamp'])
            # Remove Timezone if it exists
            timestamps = timestamps.dt.tz_localize(None)
            df['timestamp'] = timestamps
            df.set_index('timestamp', inplace=True)
            df = df.sort_index()
            # Group by day and take the last value of each day
            df = df.resample('d').last()
            return df
    

    def extract(self):
        self._data = self.get_data()

    def transform(self):
        # self._data[self._data['vault_name']==vault_name].copy()
        self._data['share_price'] = self._data['net_balance'] / self.init_balance
        idle_assets_array = []
        pending_withdrawals_array = []
        std_deviation = self.init_balance * self.std_deviation_ratio
        for _ in range(len(self._data)):
            assets = self._random.normalvariate(0, std_deviation)
            idle_assets_array.append(assets if assets > 0 else 0)
            pending_withdrawals_array.append(-assets if assets < 0 else 0)
        self._data['idle_assets'] = np.array(idle_assets_array)
        self._data['pending_withdrawals'] = np.array(pending_withdrawals_array)


    def load(self):
        self._load(self._file_id)

    def read(self, with_run: bool = False) -> pd.DataFrame:
        if with_run:
            self.run()
        else:
            self._read(self._file_id)

        return self._data

    def delete_dump_file(self):
        Path(self.file_path(self._file_id)).unlink(missing_ok=True)
