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
        init_balance: The initial balance of the meta vault
        start_time: The start time of the meta vault
        end_time: The end time of the meta vault
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
        start_time: datetime,
        end_time: datetime,
        data_base_path: str,
        interval: str = 'd',
        seed: int = 420,
    ) -> None:
        super().__init__()
        self._data = None
        self.init_balance = init_balance
        self.start_time = start_time
        self.end_time = end_time
        self.data_base_path = data_base_path
        self.interval = interval
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
            self._data.loc[self._data.index[index], 'deposits_withdrawals'] = self._random.uniform(-self.init_balance / 200, self.init_balance / 200) if self._random.randint(0,1) == 0 else 0


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
