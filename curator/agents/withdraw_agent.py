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
You are given a total asset amount to withdraw, along with the allocated (eligible to withdraw) amounts for each vault. 
Your task is to recommend which vaults to withdraw from and how much to withdraw from each,
ensuring that sum of the withdrawal amounts exactly equals to the specified total.
Your goal is to minimize exit costs while prioritizing underperforming vaults.
Some vaults may not have allocated assets or may be absent in the input list, so withdrawals from them are not possible.
The withdrawal amount can't exceed the allocated amount of the corresponding vault.

Available tools:
- get_logarithm_vaults_infos: Get current states of all vaults (share price, exit cost rate, idle assets)
- share_price_trend_analysis: Analyze vault performance trends, possible to process multiple vaults at once.

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

