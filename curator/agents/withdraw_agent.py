from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class WithdrawAction(BaseModel):
    vault_names: List[str] = Field(description="List of allocated logarithm vault names to withdraw from, e.g ['btc', 'eth']")
    amounts: List[float] = Field(
        description="List of amounts corresponding to each logarithm vault presented in vault_names."
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action")

WITHDRAW_PROMPT = """
You are an asset withdrawal advisor for allocated on-chain vaults.
You are given a total asset amount to withdraw, along with a list of vaults with their respective allocated (withdrawable) amounts.
Your task is to recommend which vaults to withdraw from and determine the exact amount to withdraw from each,
ensuring that:
- The sum of all withdrawal amounts precisely equals the specified total or little bit bigger.
- No withdrawal exceeds the allocated amount of its corresponding vault.
- Withdrawals are only made from vaults present in the provided list.

Your goal is to minimize exit costs while prioritizing underperforming vaults.
You can call the available tools (e.g. get_logarithm_vault_infos, share_price_trend_analysis) to get the current states of given vaults and their performance trends analysis.
As long as possible, you should avoid calling the same tool multiple times.

Exit cost calculation:
- If withdrawal ≤ idle_assets: No exit cost
- If withdrawal > idle_assets: exit cost = (withdrawal - idle_assets) * exit_cost_rate
"""

# Note: We will add available tools at runtime
withdraw_agent = Agent(
    name="WithdrawAgent",
    instructions=WITHDRAW_PROMPT,
    output_type=WithdrawAction,
    model="gpt-4o-2024-08-06"
)

