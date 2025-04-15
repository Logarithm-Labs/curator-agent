from pydantic import BaseModel, Field
from typing import List
from agents import Agent


class Action(BaseModel):
    name: str = Field(description="The name of action to take: 'allocate_assets', 'redeem_allocations'")
    vault_names: List[str] = Field(description="List of logarithm vault names to allocate assets to or redeem shares from")
    amounts: List[float] = Field(description="List of amounts corresponding to each logarithm vault presented in vault_names")
class ActionList(BaseModel):
    actions: List[Action] = Field(description="List of actions in sequence to take")
    reasoning: str = Field(description="The agent's reasoning for taking these actions")

def create_agent(prompt: str, tools: List, model: str) -> Agent:
    return Agent(
        name="Curator Assistant",
        instructions=prompt,
        tools=tools,
        output_type=ActionList
    )
