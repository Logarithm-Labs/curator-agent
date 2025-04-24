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
You are an asset allocation advisor for on-chain vaults.
You are given a total asset amount to allocate.
Your task is to recommend which vaults to allocate to and how much to each,
ensuring that sum of the allocation amounts exactly equals to the specified total.
Your goal is to maximize future returns while minimizing total entry costs.
You have to prioritize the future returns before the total entry costs.

Available tools:
- get_logarithm_vaults_infos: Get current states of all vaults (share price, entry cost rate, pending withdrawals)
- share_price_trend_analysis: Analyze vault performance trends, possible to process multiple vaults at once.

Entry cost calculation:
    - If allocation ≤ pending_withdrawals: No entry cost
    - If allocation > pending_withdrawals: entry_cost = (allocation - pending_withdrawals) * entry_cost_rate / (entry_cost_rate + 1)
"""

# Note: We will add available tools at runtime
allocation_agent = Agent(
    name="AllocationAgent",
    instructions=ALLOCATION_PROMPT,
    output_type=AllocationAction,
    model="gpt-4o-2024-08-06"
)

