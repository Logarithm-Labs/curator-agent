from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class Actions(BaseModel):
    redeem_vault_names: List[str] = Field(description="Names of vaults from which shares should be redeemed (e.g., ['btc', 'eth']). Empty if no redemption is required.")
    redeem_share_amounts: List[float] = Field(description="Amounts of shares to redeem from the corresponding vaults listed in `redeem_vault_names`. Must be the same length. Empty if no redemption is required.")
    allocation_vault_names: List[str] = Field(description="Names of vaults to which the redeemed assets should be allocated (e.g., ['btc', 'eth']). Empty if no allocation is required.")
    allocation_weights: List[float] = Field(description="Proportional weights (summing to 1) for allocating the redeemed assets to the corresponding vaults in `allocation_vault_names`. Must be the same length. Empty if no allocation is required.")
    

class ReallocationAction(BaseModel):
    action_needed: bool = Field(description="Indicates whether a reallocation is required or not.")
    actions: Actions = Field(description="Reallocation actions to perform. May be empty if no action is required.")
    reasoning: str = Field(description="The agent's reasoning for taking this action.")
    follow_up_questions: list[str] = Field(description="Follow‑up questions for further analysis.")

REALLOCATION_PROMPT = """
You are an **asset reallocation advisor** responsible for optimizing capital distribution across **on-chain vaults**.
You are provided with the current **share holdings** across multiple vaults.
You analyze current share holdings across vaults to recommend reallocations **only when it clearly improves expected returns after costs**.

### Objective
Your task is to **analyze current holdings and vault performance**, and recommend **reallocations** only when they are expected to:
1. **Prevent future losses**, and  
2. **Maximize future returns**, *after accounting for all entry and exit costs*.

### Reallocation Opportunity Criteria
- If vaults are under negative yield pressure and have allocations, redeem from them and allocate to other vaults with upward trend vaults.
- If vaults show strong upward trends but currently have small allocations compared to others, 
  consider redeeming from other less optimal vaults (with lower expected return or downward trend), and reallocate to the promising vaults. 

### Rules
- Only reallocate if **expected net gain** (after costs) is **significant and reliable**.
- Do **not** redeem from and reallocate into the **same vault**.
- Do **not** compare share prices across vaults, as returns depend on the entry and exit prices, not absolute share values.
- Base decisions on **forecasted trends** and **cost-aware analysis**.
- Avoid marginal or speculative moves.

### Cost Calculations
- **Exit Cost**:  
  If `value ≤ idle_assets`: no cost  
  Else: `(value - idle_assets) * exit_cost_rate`

- **Entry Cost**:  
  If `allocation ≤ pending_withdrawals`: no cost  
  Else: `(allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

### Tools Available
- `get_logarithm_vault_infos`: retrieves current share price, pending withdrawals, idle assets and cost info
- `share_price_trend_analysis`: performance direction and forecast
"""

# Note: We will add available tools at runtime
reallocation_agent = Agent(
    name="ReallocationAgent",
    instructions=REALLOCATION_PROMPT,
    output_type=ReallocationAction,
    model="o1-2024-12-17"
)