from pydantic import BaseModel, Field
from typing import List
from agents import Agent


class AgentAction(BaseModel):
    action: str = Field(description="The type of action to take: 'allocate_assets', 'redeem_allocations', 'withdraw_allocations'")
    vault_names: List[str] = Field(description="List of logarithm vault names to allocate/redeem/withdraw assets from")
    amounts: List[float] = Field(description="List of amounts corresponding to each vault")
    reasoning: str = Field(description="The agent's reasoning for taking this action")


def create_agent(prompt: str, tools: List, model: str) -> Agent:
    return Agent(
        name="Curator",
        instructions=prompt,
        tools=tools,
        output_type=List[AgentAction]
    )
