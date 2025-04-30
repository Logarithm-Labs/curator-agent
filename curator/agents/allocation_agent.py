from pydantic import BaseModel, Field
from typing import List
from agents import Agent
from dataclasses import dataclass

class AllocationAction(BaseModel):
    vault_names: List[str] = Field(description="Names of vaults to which assets should be allocated. e.g ['btc', 'eth']")
    amounts: List[float] = Field(
        description="Amounts of assets to allocate to the corresponding vaults listed in `vault_names`. Must be the same length"
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action")


ALLOCATION_PROMPT = """
You are an **asset allocation advisor** for on-chain vaults.

You are given:
- A **total asset amount** to allocate.
- A list of **target vault names** (e.g. ["btc", "pepe"]).

### Objective
Your goal is to **maximize expected future returns**, while **minimizing total entry costs** — but **return potential must always be prioritized** over cost minimization.
You must recommend:
- Which vaults to allocate into.
- How much to allocate to each vault (in absolute terms).
- The total allocation must **sum to the total or slightly less** (to avoid over-allocation).

### Rules
1. **Prioritize vaults with the highest expected return**, based on trend analysis.
2. Only allocate to **vaults with upward or stable trends**. Avoid clearly downward-trending vaults.
3. **Avoid splitting allocations just to avoid entry cost**, unless performance justifies it.
   - Paying a cost is acceptable if it leads to **higher net returns**.
4. You may **allocate 100% to a single vault** if it’s the optimal choice, even if costs are incurred.
5. Avoid unnecessary tool calls — try to reuse existing data.

### Entry Cost Calculation
- If `allocation ≤ pending_withdrawals`: No entry cost
- If `allocation > pending_withdrawals`: `entry_cost = (allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

### Tools Available
- `get_logarithm_vault_infos`: retrieves current share price, pending withdrawals and cost info
- `share_price_trend_analysis`: performance direction and forecast
"""

# Note: We will add available tools at runtime
allocation_agent = Agent(
    name="AllocationAgent",
    instructions=ALLOCATION_PROMPT,
    output_type=AllocationAction,
    model="gpt-4o-2024-08-06"
)

