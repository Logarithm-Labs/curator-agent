from pydantic import BaseModel, Field
from typing import List
from agents import Agent
from dataclasses import dataclass

class AllocationAction(BaseModel):
    vault_names: List[str] = Field(description="List of vault names to allocate, e.g ['btc', 'eth']")
    amounts: List[float] = Field(
        description="List of amounts corresponding to each vault presented in vault_names."
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action")


ALLOCATION_PROMPT = """
You are an **asset allocation advisor** for on-chain vaults.

You are given:
- A **total asset amount** to allocate.
- A list of **target vault names** (e.g. ["btc", "pepe"]).

### Objective
Your goal is to **maximize expected future returns**, while **minimizing total entry costs** — but **return potential must always be prioritized** over cost minimization.

### Rules
1. **Prioritize vaults with the highest expected return**, based on trend analysis.
2. The total allocation must **sum to the total or slightly less** (to avoid over-allocation).
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

