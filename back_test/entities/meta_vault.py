from dataclasses import dataclass, field
from fractal.core.base import NamedEntity
from fractal.core.base.entity import BaseEntity, EntityException, InternalState, GlobalState
from back_test.entities.logarithm_vault import LogarithmVault, LogarithmVaultInternalState
from typing import List


class MetaVaultEntityException(EntityException):
    """
    Exception raised for errors in the Meta Vault entity.
    """

@dataclass
class MetaVaultGlobalState(GlobalState):
    deposits: float = 0.0
    withdrawals: float = 0.0

@dataclass
class MetaVaultInternalState(InternalState):
    total_supply: float = 0.0

DUST = 0.000001
class MetaVault(BaseEntity):
    """
    Represents a logarithm vault entity.
    """

    def __init__(self):
        self._assets: float = 0.0
        self._allocated_vaults: list[NamedEntity] = []
        self._cumulative_requested_withdrawals: float = 0.0
        super().__init__()

    def _initialize_states(self):
        self._global_state: MetaVaultGlobalState = MetaVaultGlobalState()
        self._internal_state: MetaVaultInternalState = MetaVaultInternalState()

    def action_deposit(self, assets: float) -> float:
        if assets < 0:
            raise MetaVaultEntityException("Assets must be greater than 0")
        
        shares_to_mint = assets if self.total_assets == 0 else assets * self.total_supply / self.total_assets
        self._assets += assets
        self._internal_state.total_supply += shares_to_mint
        return shares_to_mint
       
    def action_withdraw(self, assets: float) -> float:
        if assets < 0:
            raise MetaVaultEntityException("Assets must be greater than 0")
        if assets > self.total_assets:
            raise MetaVaultEntityException("Assets to withdraw are greater than the available assets")
        
        shares_to_burn = assets * self.total_supply / self.total_assets
        if self.idle_assets >= assets:
            self._assets -= assets
        else:
            idle = self.idle_assets
            self._assets -= idle
            self._cumulative_requested_withdrawals += assets - idle
        self._internal_state.total_supply -= shares_to_burn
        return shares_to_burn

    def action_allocate_assets(self, targets: List[NamedEntity], amounts: List[float]) -> None:
        if not targets or not amounts:
            raise MetaVaultEntityException("Targets and amounts Lists cannot be empty")
        if (len(targets) != len(amounts)):
            raise MetaVaultEntityException("Targets and amounts must have the same length")
        for target in targets:
            if not isinstance(target.entity, LogarithmVault):
                raise MetaVaultEntityException("Target must be a logarithm vault")
        for amount in amounts:
            if amount < 0:
                raise MetaVaultEntityException("Asset amount must be greater than 0")

        shortfall = sum(amounts) - self.idle_assets
        amounts[0] -= shortfall if shortfall > 0 else 0
        amounts = [amount if amount > DUST else 0 for amount in amounts]
        
        if (sum(amounts) > self.idle_assets):
            raise MetaVaultEntityException(f"Assets to allocate are greater than the available assets")

        for target, amount in zip(targets, amounts):
            target_vault: LogarithmVault = target.entity
            target_vault.action_deposit(amount)
            # decrease assets by the amount allocated
            self._assets -= amount
            # add target to allocated_vaults if it is not already in the List
            if not any(allocated.entity_name == target.entity_name for allocated in self._allocated_vaults):
                self._allocated_vaults.append(target)

    def action_redeem_allocations(self, targets: List[NamedEntity], amounts: List[float]) -> None:
        if not targets or not amounts:
            raise MetaVaultEntityException("Targets and shares Lists cannot be empty")
        if (len(targets) != len(amounts)):
            raise MetaVaultEntityException("Targets and shares must have the same length")
        for target in targets:
            if not isinstance(target.entity, LogarithmVault):
                raise MetaVaultEntityException("Target must be a logarithm vault")
        
        # validate shares against targets
        for target, amount in zip(targets, amounts):
            if amount < 0:
                raise MetaVaultEntityException("Share amount must be greater than 0")
            target_vault: LogarithmVault = target.entity
            internal_state: LogarithmVaultInternalState = target_vault.internal_state
            if amount > internal_state.shares:
                raise MetaVaultEntityException("Share is greater than the available shares of the target")
            
        for target, amount in zip(targets, amounts):
            target_vault: LogarithmVault = target.entity
            assets = target_vault.action_redeem(amount)
            # increase assets by the amount redeemed
            self._assets += assets
            # remove target from allocated_vaults if the shares of target is 0
            internal_state: LogarithmVaultInternalState = target_vault.internal_state
            if internal_state.shares == 0:
                self._allocated_vaults = [v for v in self._allocated_vaults if v.entity_name != target.entity_name]

    def action_withdraw_allocations(self, targets: List[NamedEntity], amounts: List[float]) -> None:
        if not targets or not amounts:
            raise MetaVaultEntityException("Targets and amounts Lists cannot be empty")
        if (len(targets) != len(amounts)):
            raise MetaVaultEntityException("Targets and amounts must have the same length")
        for target in targets:
            if not isinstance(target.entity, LogarithmVault):
                raise MetaVaultEntityException("Target must be a logarithm vault")
        
        # validate assets against targets
        for target, amount in zip(targets, amounts):
            if amount < 0:
                raise MetaVaultEntityException("Asset amount must be greater than 0")
            target_vault: LogarithmVault = target.entity
            if amount > target_vault.balance:
                raise MetaVaultEntityException("Asset amount is greater than the available balance of the target")

        for target, amount in zip(targets, amounts):
            target_vault: LogarithmVault = target.entity
            target_vault.action_withdraw(amount)
            # increase assets by the amount withdrawn
            self._assets += amount
            # remove target from allocated_vaults if the shares of target is 0
            internal_state: LogarithmVaultInternalState = target_vault.internal_state
            if internal_state.shares == 0:
                self._allocated_vaults = [v for v in self._allocated_vaults if v.entity_name != target.entity_name]
        
    def update_state(self, state: MetaVaultGlobalState):
        if state.deposits < 0 or state.withdrawals < 0:
            raise MetaVaultEntityException("Idle assets and pending withdrawals must be greater than 0")
        if state.deposits > 0 and state.withdrawals > 0:
            raise MetaVaultEntityException("Both idle assets and pending withdrawals cannot be greater than 0")

        self._global_state = state

    @property
    def balance(self) -> float:
        return self.idle_assets - self.pending_withdrawals

    @property
    def idle_assets(self) -> float:
        idle = self._assets - self._cumulative_requested_withdrawals
        return idle if idle > 0 else 0

    @property
    def pending_withdrawals(self) -> float:
        requested = self._cumulative_requested_withdrawals - self._assets
        return requested if requested > 0 else 0
    
    @property
    def allocated_assets(self) -> float:
        return sum(vault.entity.balance for vault in self._allocated_vaults)
    
    @property
    def total_assets(self) -> float:
        return self.idle_assets + self.allocated_assets - self.pending_withdrawals
    
    @property
    def total_supply(self) -> float:
        return self._internal_state.total_supply

