## How to Use

1. **Install `uv`**  
   Run the following command to install `uv`:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Dependencies**  
   Synchronize the required dependencies by running:

   ```bash
   uv sync --locked
   ```

3. **Run Backtest**  
   1. Execute to build observations:
      ```bash
      uv run -m back_test.build_observations
      ```
   2. Execute to get backtest data:
      ```bash
      uv run -m back_test.curator_strategy
      ```

4. **View Results in Charts**  
   Visualize the results in chart format by running:
   ```bash
   uv run -m back_test.dashboard
   ```
   Important: Make sure you set the latest running log path in `dashboard.py`.
