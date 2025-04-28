## How to Use

1. **Install `uv`**  
   Run the following command to install `uv`:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Dependencies**  
   Synchronize the required dependencies by running:

   ```bash
   uv sync
   ```

3. **Run Backtest**  
   Execute the backtest to get results:

   ```bash
   uv run -m back_test.curator_strategy
   ```

4. **View Results in Charts**  
   Visualize the results in chart format by running:
   ```bash
   uv run -m back_test.dashboard
   ```
