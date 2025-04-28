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
        if withdrawal > 0 and not balances[vault_name]:
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

def validate_redeem(vault_names: list[str], redeem_shares: list[float], balances: dict[str, float]) -> ValidationFeedback:
    if len(vault_names) != 0:
        if len(vault_names) != len(redeem_shares):
            return ValidationFeedback(
                feedback='The length of vaults names is not the same as the length of share amounts.',
                result='fail'
            )
        for amount in redeem_shares:
            if amount < 0:
                return ValidationFeedback(
                    feedback=f'The share amount {amount} cannot be negative.',
                    result='fail'
                )
        for (vault_name, share) in zip(vault_names, redeem_shares):
            if share > 0 and not balances[vault_name]:
                return ValidationFeedback(
                    feedback=f'Cannot redeem from {vault_name} because it dose not have allocation.',
                    result='fail'
                )
            elif share > balances[vault_name]:
                return ValidationFeedback(
                    feedback=f'The redeem share amount ({share}) of {vault_name} cannot exceeds the the balance ({balances[vault_name]})',
                    result='fail'
                )
    return ValidationFeedback(
        feedback='',
        result='pass'
    )

def validate_reallocation(vault_names: list[str], weights: list[float]) -> ValidationFeedback:
    if len(vault_names) != 0:
        if len(vault_names) != len(weights):
            return ValidationFeedback(
                feedback='The length of vaults names is not the same as the length of weights.',
                result='fail'
            )
        for weight in weights:
            if weight < 0 or weight > 1:
                return ValidationFeedback(
                    feedback=f'The weight ({weight}) should be between 0 and 1.',
                    result='fail'
                )
        if sum(weights) != 1:
            return ValidationFeedback(
                feedback=f'Sum of weights ({sum(weights)}) should equal to 1.',
                result='fail'
            )
    return ValidationFeedback(
        feedback='',
        result='pass'
    )