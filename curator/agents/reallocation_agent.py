from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class Actions(BaseModel):
    redeem_vault_names: List[str] = Field(description="Names of vaults from which shares should be redeemed (e.g., ['btc', 'eth']). Empty if no redemption is required.")
    redeem_share_amounts: List[float] = Field(description="Amounts of shares to redeem from the corresponding vaults listed in `redeem_vault_names`. Empty if no redemption is required.")
    allocation_vault_names: List[str] = Field(description="Names of vaults to which the redeemed assets should be allocated (e.g., ['btc', 'eth']). Empty if no allocation is required.")
    allocation_weights: List[float] = Field(description="Proportional weights (summing to 1) for allocating the redeemed assets to the corresponding vaults in `allocation_vault_names`. Empty if no allocation is required.")
    

class ReallocationAction(BaseModel):
    action_needed: bool = Field(description="Indicates whether a reallocation is required or not.")
    actions: Actions = Field(description="Reallocation actions to perform. May be empty if no action is required.")
    reasoning: str = Field(description="The agent's reasoning for taking this action in markdown format.")

REALLOCATION_PROMPT = """
You are an asset reallocation advisor responsible for rebalancing the capital distribution across on-chain vaults to maximize returns.

You are provided with a list of vault names to analyze.
You detect a reallocation opportunity, and if so, recommend a reallocation action.

### Objective
Your goal is to:
- Prevent short-term losses based on the current profits.
- Ride an opportunity to gain more by allocating to better trend vaults from worse trend ones.

### Note
The on-chain vaults charge exit costs when redeeming and entry costs when allocating.

### Heuristics
- As long as possible, you have to ensure the costs associated with the reallocation actions will be covered by the short-term profits.
- When redeeming from negative trend vaults, the amounts should be adjusted so that the exit costs won't exceed the expected losses.

### Cost Calculation
- Redemption Cost:  
  If `share_price * share_to_redeem ≤ idle_assets`: no cost
  Else: `(share_price * share_to_redeem - idle_assets) * exit_cost_rate / (exit_cost_rate + 1)`

- Allocation Cost:  
  If `assets_to_allocate ≤ pending_withdrawals`: no cost
  Else: `(assets_to_allocate - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

### Tools Available
- `get_logarithm_vault_infos`: return the following information for each vault:
    - `current_share_price` (float): Current price per share of the vault
    - `entry_cost_rate` (float): Fee rate applied when depositing assets (as a decimal)
    - `exit_cost_rate` (float): Fee rate applied when withdrawing assets (as a decimal)
    - `idle_assets` (float): Assets in the vault available for withdrawal without exit cost
    - `pending_withdrawals` (float): Assets queued for withdrawal in the vault, offsetting entry costs
    - `current_share_holding` (float): Current share holding amount in the vault
    - `allocated_assets` (float): Assets amount invested in the vault, can be negative which means the vault is in profit
    - `current_assets` (float): Assets amount valued by the current share price with the holding
- `get_share_price_trend_analysis`: performance analysis for given vaults
"""

# Note: We will add available tools at runtime
reallocation_agent = Agent(
    name="ReallocationAgent",
    instructions=REALLOCATION_PROMPT,
    output_type=ReallocationAction,
    model="o4-mini"
)