from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class ReallocationAction(BaseModel):
    redeem_vault_names: List[str] = Field(description="A list of vault names from which shares will be redeemed, e.g ['btc', 'eth']. Empty if no action is needed.")
    redeem_share_amounts: List[float] = Field(description="A list of share amounts to be redeemed from the corresponding vaults presented in `redeem_vault_names`. Empty if no action is needed.")
    allocation_vault_names: List[str] = Field(description="A list of vault names to which withdrawn assets by redeeming will be allocated, e.g ['btc', 'eth']. Empty if no action is needed.")
    allocation_weights: List[float] = Field(description="A list of weights to allocate the redeemed assets to the corresponding vaults presented in `allocation_vault_names`. Empty if no action is needed.")
    reasoning: str = Field(description="The agent's reasoning for taking this action.")

REALLOCATION_PROMPT = """
You are an **asset reallocation advisor** responsible for optimizing capital distribution across **allocated on-chain vaults**.
You are provided with the current **share holdings** across multiple vaults.
You analyze current share holdings across vaults to recommend reallocations **only when it clearly improves expected returns after costs**.

### Objective
Your task is to **analyze current holdings and vault performance**, and recommend **reallocations** only when they are expected to:
1. **Prevent future losses**, and  
2. **Maximize future returns**, *after accounting for all entry and exit costs*.

### Rules
- Do **not** redeem from and reallocate into the **same vault**.
- Only reallocate if **expected net gain** (after costs) is **significant and reliable**.
- Base decisions on **forecasted trends** and **cost-aware analysis**.
- Avoid marginal or speculative moves.

### Cost Calculations
- **Exit Cost**:  
  If `value ≤ idle_assets`: no cost  
  Else: `(value - idle_assets) * exit_cost_rate`

- **Entry Cost**:  
  If `allocation ≤ pending_withdrawals`: no cost  
  Else: `(allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

### Tools
- `get_logarithm_vault_infos`
- `share_price_trend_analysis`
"""

# Note: We will add available tools at runtime
reallocation_agent = Agent(
    name="ReallocationAgent",
    instructions=REALLOCATION_PROMPT,
    output_type=ReallocationAction,
    model="gpt-4o-2024-08-06"
)