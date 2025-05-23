import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import ParameterGrid

from fractal.core.base.observations import SQLiteObservationsStorage
from fractal.core.pipeline import (
    DefaultPipeline, MLFlowConfig, ExperimentConfig)

from back_test.baseline_strategy import BaselineStrategy
from back_test.build_observations import build_observations


# Build a grid of parameters to search
def build_grid() -> ParameterGrid:
    grid = ParameterGrid({
        'INIT_BALANCE': [100_000],
        'WINDOW': [1, 7],
        'LOOKBACK_WINDOW': [7, 14, 30, 60],
        'FORECAST_HORIZON': [3, 7, 14, 30],
    })
    return grid


if __name__ == '__main__':
    # Define MLFlow and Experiment configurations
    mlflow_config: MLFlowConfig = MLFlowConfig(
        mlflow_uri='http://127.0.0.1:8080',
        experiment_name=f'baseline_curator_v0.1-2025'
    )
    experiment_config: ExperimentConfig = ExperimentConfig(
        strategy_type=BaselineStrategy,
        backtest_observations=build_observations(),
        observations_storage_type=SQLiteObservationsStorage,
        params_grid=build_grid(),
        debug=True,
    )
    pipeline: DefaultPipeline = DefaultPipeline(
        experiment_config=experiment_config,
        mlflow_config=mlflow_config
    )
    pipeline.run()
