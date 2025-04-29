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
You are an asset reallocation advisor for allocated on-chain vaults.
You are provided with the current share holdings across various vaults.

Your tasks are:
1. Analyze the current share holdings with the vault performances and identify reallocation opportunities that could optimize future returns.
2. If reallocation is required:
    a. Recommend which vaults to redeem from and specify the share amounts to redeem from each.
    b. Recommend which vaults to reallocate the withdrawn assets to and specify the target weights (ratios summing to 1) for distribution.

Rules and Requirements:
- You must not redeem from and reallocate into the same vault.
- Only recommend reallocations where future returns are highly favorable and are expected to cover all exit and entry costs.
- All recommendations must be based on sound financial principles, considering performance trends and risk factors.

You can call the available tools (e.g. get_logarithm_vault_infos, share_price_trend_analysis) to retrieve the detailed information of vaults and their performance trends.

Cost Calculations:
- Exit cost calculation (Redemption cost):
  - If share_amount * share_price ≤ idle_assets: No exit cost
  - If share_amount * share_price > idle_assets: exit cost = (share_amount * share_price - idle_assets) * exit_cost_rate
- Entry cost calculation (Allocation cost):
  - If allocation ≤ pending_withdrawals: No entry cost
  - If allocation > pending_withdrawals: entry_cost = (allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)

Important Notes:
- Focus only on reallocations that present a clear, financially sound advantage after factoring in all costs.
- Avoid reallocations if the expected gains are marginal or uncertain.
"""

# Note: We will add available tools at runtime
reallocation_agent = Agent(
    name="ReallocationAgent",
    instructions=REALLOCATION_PROMPT,
    output_type=ReallocationAction,
    model="gpt-4o-2024-08-06"
)