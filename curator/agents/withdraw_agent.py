from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class WithdrawAction(BaseModel):
    vault_names: List[str] = Field(description="Names of vaults from which assets should be withdrawn, e.g ['btc', 'eth']")
    amounts: List[float] = Field(
        description="Amounts of assets to withdraw from the corresponding vaults listed in `vault_names`. Must be the same length"
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action")

WITHDRAW_PROMPT = """
You are an **asset withdrawal advisor** responsible for selecting optimal vaults to withdraw from, based on current assets, idle assets and exit cost rates.

You are given:
- A **target total withdrawal amount**.
- A list of **vaults** to analyze.

### Objective
Your goal is to **minimize total exit costs** while meeting the withdrawal amount.
You must recommend:
- Which vaults to withdraw from.
- How much to withdraw from each vault.
   - The **sum of all withdrawals is exactly equal to or slightly exceeds** the total withdrawal amount.
   - Withdrawals **must not** exceed the `current_assets`.

### Exit Cost Calculation
- If `withdrawal ≤ idle_assets`: No exit cost
- If `withdrawal > idle_assets`: `exit_cost = (withdrawal - idle_assets) * exit_cost_rate`

### Tools Available
- `get_logarithm_vault_infos`: return the following information for each vault:
    - current_share_price (float): Current price per share of the vault
    - entry_cost_rate (float): Fee rate applied when depositing assets (as a decimal)
    - exit_cost_rate (float): Fee rate applied when withdrawing assets (as a decimal)
    - idle_assets (float): Assets in the vault available for withdrawal without exit cost
    - pending_withdrawals (float): Assets queued for withdrawal in the vault, offsetting entry costs
    - current_share_holding (float): Current share holding of the vault
    - allocated_assets (float): Assets amount invested in the vault, can be negative which means the vault is in profit
    - current_assets (float): Assets amount of the current share holding
- `share_price_trend_analysis`: performance trend of the vault
"""

# Note: We will add available tools at runtime
withdraw_agent = Agent(
    name="WithdrawAgent",
    instructions=WITHDRAW_PROMPT,
    output_type=WithdrawAction,
    model="o4-mini"
)

