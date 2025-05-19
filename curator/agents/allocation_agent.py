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
Your goal is to **maximize expected future returns**, while **minimizing total entry costs** — but **potential return must always be prioritized** over cost minimization.
You must recommend:
- Which vaults to allocate into.
- How much to allocate to each vault (in absolute terms).
- The total allocation must **sum to the total or slightly less** (to avoid over-allocation).

### Entry Cost Calculation
- If `allocation ≤ pending_withdrawals`: No entry cost
- If `allocation > pending_withdrawals`: `entry_cost = (allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

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
allocation_agent = Agent(
    name="AllocationAgent",
    instructions=ALLOCATION_PROMPT,
    output_type=AllocationAction,
    model="o4-mini"
)

