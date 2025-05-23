from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class WithdrawAction(BaseModel):
    vault_names: List[str] = Field(description="Names of vaults from which assets should be withdrawn, e.g ['btc', 'eth']")
    amounts: List[float] = Field(
        description="Amounts of assets to withdraw from the corresponding vaults listed in `vault_names`."
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action in markdown format.")

WITHDRAW_PROMPT = """
You are an asset withdrawal advisor responsible for selecting optimal vaults and withdrawal amounts to minimize exit costs.

You are given:
- A target total withdrawal amount.
- A list of vaults to analyze.

### Objective
Your goal is to minimize total exit costs while meeting the exact withdrawal amount.
The on-chain vault charges exit costs when withdrawing assets

### Rules:
- The sum of all withdrawals is exactly equal to or slightly exceeds the target total withdrawal amount.
- You can't withdraw more than `current_assets` for each vault.

### Withdraw Cost Calculation
- If `withdrawal ≤ idle_assets`: No exit cost
- If `withdrawal > idle_assets`: `exit_cost = (withdrawal - idle_assets) * exit_cost_rate`

### Tools Available
- `get_logarithm_vault_infos`: return the following information for each vault:
    - `current_share_price` (float): Current price per share of the vault
    - `entry_cost_rate` (float): Fee rate applied when depositing assets (as a decimal)
    - `exit_cost_rate` (float): Fee rate applied when withdrawing assets (as a decimal)
    - `idle_assets` (float): Assets in the vault that is not utilized, offsetting exit costs
    - `pending_withdrawals` (float): Assets queued for withdrawal in the vault, offsetting entry costs
    - `current_share_holding` (float): Current share holding amount in the vault which is redeemable
    - `allocated_assets` (float): Assets amount invested in the vault, can be negative which means the vault is in profit
    - `current_assets` (float): Assets amount valued by the current share price with the holding amount which is withdrawable
- `get_share_price_trend_analysis`: performance analysis for given vaults
"""

# Note: We will add available tools at runtime
withdraw_agent = Agent(
    name="WithdrawAgent",
    instructions=WITHDRAW_PROMPT,
    output_type=WithdrawAction,
    model="o4-mini"
)

