import random
from pathlib import Path
import pandas as pd
from fractal.loaders.base_loader import Loader
from typing import Dict
from datetime import datetime, UTC

class MetaVaultLoader(Loader):
    """
    A class that represents a Meta vault states loader.

    This loader performs Monte Carlo simulation for each data point

    Attributes:
        deposit_simulation_limit: The range of deposits of the meta vault
        withdraw_simulation_limit: The range of withdrawals of the meta vault
        start_time: The start time of the meta vault
        end_time: The end time of the meta vault
        data_base_path: The base path to the back tested vault data
        seed (int): The seed value used for random number generation.
        interval: The interval of observations
        precision: float precision for simulated deposits/withdrawals

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
        deposit_simulation_limit: float,
        withdraw_simulation_limit: float,
        start_time: datetime,
        end_time: datetime,
        data_base_path: str,
        seed: int = 420,
        interval: str = 'd',
        precision: int = 6
    ) -> None:
        super().__init__()
        self._data = None
        self.deposit_simulation_limit = deposit_simulation_limit
        self.withdraw_simulation_limit = withdraw_simulation_limit
        self.start_time = start_time
        self.end_time = end_time
        self.data_base_path = data_base_path
        self.interval = interval
        self.precision = precision
        self._file_id = "meta_simulated_data"
        self._random = random.Random()
        self._random.seed(seed)
    

    def extract(self):
        self._data = pd.DataFrame(index=pd.date_range(start=self.start_time, end=self.end_time, freq=self.interval, tz=None))
        # set index field name as 'timestamp'
        self._data.index.name = 'timestamp'

    def transform(self):
        # Generate random deposits/withdrawals for each row
        for index in range(len(self._data)):
            choice = self._random.randint(0, 2)
            if choice == 0:
                self._data.loc[self._data.index[index], 'deposits_withdrawals'] = round(self._random.uniform(0, self.deposit_simulation_limit), self.precision)
            elif choice == 1:
                self._data.loc[self._data.index[index], 'deposits_withdrawals'] = 0
            else:
                self._data.loc[self._data.index[index], 'deposits_withdrawals'] = -round(self._random.uniform(0, self.withdraw_simulation_limit), self.precision)


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
