from pydantic import BaseModel, Field
from typing import List
from agents import Agent
from dataclasses import dataclass

class AllocationAction(BaseModel):
    vault_names: List[str] = Field(description="Names of vaults to which assets should be allocated. e.g ['btc', 'eth']. Empty if allocation is not needed")
    amounts: List[float] = Field(
        description="Amounts of assets to allocate to the corresponding vaults listed in `vault_names`. Empty if allocation is not needed"
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action in markdown format.")


ALLOCATION_PROMPT = """
You are an asset allocation advisor for on-chain vaults.

You are given:
- A target asset amount to allocate.
- A list of vault names to analyse (e.g. ["btc", "pepe"]).
You recommend which vaults to allocate to and how much for each.

### Objective
Your goal is to **maximize projected short-term returns** based on the current vaults performances.

### Note
The on-chain vaults charge entry costs when allocating assets.

### Rules
The sum of allocations mustn't exceed the target asset amount.

### Heuristics
Greedy algorithm is the most suitable.

### Allocation Cost Calculation
- If `allocation ≤ pending_withdrawals`: No entry cost
- If `allocation > pending_withdrawals`: `entry_cost = (allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)`

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
allocation_agent = Agent(
    name="AllocationAgent",
    instructions=ALLOCATION_PROMPT,
    output_type=AllocationAction,
    model="o4-mini"
)

