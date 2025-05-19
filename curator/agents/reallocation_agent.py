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

REALLOCATION_PROMPT = """
You are an **asset reallocation advisor** responsible for optimizing capital distribution across **on-chain vaults**.
You are provided with a list of vault names to analyze.

### Objective
Your task is to analyze the **performance of all given vaults** and the **current share holdings** with the **open assets**, and recommend **reallocations** only when they are expected to:
1. **Prevent future losses**, and
2. **Maximize future returns**, *after accounting for all entry and exit costs*.

### Rules
- Do **not** redeem from and reallocate into the **same vault**.
- Do **not** compare share prices across vaults.

### Cost Calculations
- **Exit Cost**:  
  If `value ≤ idle_assets`: no cost  
  Else: `(value - idle_assets) * exit_cost_rate`

- **Entry Cost**:  
  If `allocation ≤ pending_withdrawals`: no cost  
  Else: `(allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

### Current Return Calculations
  `return = current_assets - allocated_assets`
  - Positive: profit
  - Negative: loss

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
reallocation_agent = Agent(
    name="ReallocationAgent",
    instructions=REALLOCATION_PROMPT,
    output_type=ReallocationAction,
    model="o4-mini"
)