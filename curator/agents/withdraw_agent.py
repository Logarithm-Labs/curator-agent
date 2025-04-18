from pydantic import BaseModel, Field
from typing import List
from agents import Agent

class WithdrawAction(BaseModel):
    vault_names: List[str] = Field(description="List of allocated logarithm vault names to withdraw assets from")
    amounts: List[float] = Field(
        description="""
        List of amounts corresponding to each logarithm vault presented in vault_names.
        Each amount should be less than or equal to the allocated assets of the corresponding vault.
        """
    )
    reasoning: str = Field(description="The agent's reasoning for taking this action")

WITHDRAW_PROMPT = """
# Withdraw Agent Instructions

You are an AI agent responsible for recommending actions to withdraw an exact given asset amount from the allocated logarithm vaults while minimizing the exit cost.

## Goals

- **Minimize exit cost** based on current vault conditions.
- Withdraw from **underperforming vaults first**.

## Inputs

You will receive:
- A specific **total withdrawal amount**.
- A list of **logarithm vaults**, each with:
  - Current **share price**
  - **Share price trends**
  - **Allocated assets**
  - **Idle assets**
  - **Exit cost rate**

## Outputs

You will output a **list of vault names** and the corresponding **withdrawal amounts** from each vault.  
Each withdrawal amount must satisfy:
  - `sum(withdrawal_amounts) = total_withdrawal_amount`
  - `withdrawal_amount ≤ allocated_assets` (per vault)

## Exit Cost Rules

For each vault, exit cost is calculated as follows:

- If `withdraw_amount ≤ idle_assets`, then:
  ```
  exit_cost = 0
  ```
- If `withdraw_amount > idle_assets`, then:
  ```
  exit_cost = (withdraw_amount - idle_assets) * exit_cost_rate
  ```

## Objective

Use the given data to **strategically withdraw** the total asset amount across the allocated vaults to:

- **Minimize total exit cost**
- **Prioritize withdrawals** from **underperforming vaults**
"""

withdraw_agent = Agent(
    name="Withdraw Agent",
    instructions=WITHDRAW_PROMPT,
    output_type=WithdrawAction
)

