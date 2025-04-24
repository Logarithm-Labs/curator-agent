from dataclasses import dataclass
from typing import Literal

@dataclass
class ValidationFeedback:
    feedback: str
    result: Literal["pass", "fail"]
    
def validate_allocation(total_assets: float, vault_names: list[str], allocations: list[float]) -> ValidationFeedback:
    if len(vault_names) != len(allocations):
        return ValidationFeedback(
            feedback='The lengths of vaults names and allocations should match.',
            result='fail'
        )
    for amount in allocations:
         if amount < 0:
            return ValidationFeedback(
                feedback=f'The allocation amount {amount} cannot be negative.',
                result='fail'
            )
    if total_assets < sum(allocations):
        return ValidationFeedback(
            feedback=f'Sum of allocations ({sum(allocations)}) cannot exceed the total asset amount ({total_assets}) to allocate',
            result='fail'
        )
    return ValidationFeedback(
        feedback='',
        result='pass'
    )
    
def validate_withdraw(total_assets: float, vault_names: list[str], withdrawals: list[float], balances: dict[str, float]) -> ValidationFeedback:
    if len(vault_names) != len(withdrawals):
        return ValidationFeedback(
            feedback='The length of vaults names is not the same as the length of withdrawal amounts.',
            result='fail'
        )
    for amount in withdrawals:
        if amount < 0:
            return ValidationFeedback(
                feedback=f'The withdrawal amount {amount} cannot be negative.',
                result='fail'
            )
    if total_assets > sum(withdrawals):
        return ValidationFeedback(
            feedback=f'Sum of withdraw amounts ({sum(withdrawals)}) cannot be smaller than the total asset amount ({total_assets}) to withdraw',
            result='fail'
        )
    for (vault_name, withdrawal) in zip(vault_names, withdrawals):
        if not balances[vault_name]:
            return ValidationFeedback(
                feedback=f'Cannot withdraw from {vault_name} because it dose not have allocation.',
                result='fail'
            )
        elif withdrawal > balances[vault_name]:
            return ValidationFeedback(
                feedback=f'The withdrawal amount ({withdrawal}) of {vault_name} cannot exceeds the the balance ({balances[vault_name]})',
                result='fail'
            )
    return ValidationFeedback(
        feedback='',
        result='pass'
    )
