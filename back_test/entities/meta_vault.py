from dataclasses import dataclass, field
from fractal.core.base import NamedEntity
from fractal.core.base.entity import BaseEntity, EntityException, InternalState, GlobalState
from entities.logarithm_vault import LogarithmVault, LogarithmVaultInternalState
from typing import List


class MetaVaultEntityException(EntityException):
    """
    Exception raised for errors in the Meta Vault entity.
    """

@dataclass
class MetaVaultGlobalState(GlobalState):
    pass

@dataclass
class MetaVaultInternalState(InternalState):
    assets: float = 0.0
    allocated_vaults: List[NamedEntity] = field(default_factory=list)

class MetaVault(BaseEntity):
    """
    Represents a logarithm vault entity.
    """

    def __init__(self):
        super().__init__()

    def _initialize_states(self):
        self._global_state: MetaVaultGlobalState = MetaVaultGlobalState()
        self._internal_state: MetaVaultInternalState = MetaVaultInternalState()

    def action_deposit(self, assets: float) -> None:
        if assets <= 0:
            raise MetaVaultEntityException("Assets must be greater than 0")
        self._internal_state.assets += assets
       
    def action_withdraw(self, assets: float) -> None:
        pass

    def action_allocate_assets(self, targets: List[NamedEntity], assets: List[float]) -> None:
        if not targets or not assets:
            raise MetaVaultEntityException("Targets and assets Lists cannot be empty")
        if (len(targets) != len(assets)):
            raise MetaVaultEntityException("Targets and assets must have the same length")
        for target in targets:
            if not isinstance(target.entity, LogarithmVault):
                raise MetaVaultEntityException("Target must be a logarithm vault")
        for asset in assets:
            if asset <= 0:
                raise MetaVaultEntityException("Asset amount must be greater than 0")
        
        total_assets_to_allocate = sum(assets)
        if (total_assets_to_allocate > self._internal_state.assets):
            raise MetaVaultEntityException("Assets to allocate are greater than the available assets")

        for target, asset in zip(targets, assets):
            target_vault: LogarithmVault = target.entity
            target_vault.action_deposit(asset)
            # decrease assets by the amount allocated
            self._internal_state.assets -= asset
            # add target to allocated_vaults if it is not already in the List
            if not any(allocated.entity_name == target.entity_name for allocated in self._internal_state.allocated_vaults):
                self._internal_state.allocated_vaults.append(target)

    def action_redeem_allocations(self, targets: List[NamedEntity], shares: List[float]) -> None:
        if not targets or not shares:
            raise MetaVaultEntityException("Targets and shares Lists cannot be empty")
        if (len(targets) != len(shares)):
            raise MetaVaultEntityException("Targets and shares must have the same length")
        for target in targets:
            if not isinstance(target.entity, LogarithmVault):
                raise MetaVaultEntityException("Target must be a logarithm vault")
            if not any(allocated.entity_name == target.entity_name for allocated in self._internal_state.allocated_vaults):
                raise MetaVaultEntityException("Target vault is not allocated")
        
        # validate shares against targets
        for target, share in zip(targets, shares):
            if share <= 0:
                raise MetaVaultEntityException("Share amount must be greater than 0")
            target_vault: LogarithmVault = target.entity
            internal_state: LogarithmVaultInternalState = target_vault.internal_state
            if share > internal_state.shares:
                raise MetaVaultEntityException("Share is greater than the available shares of the target")
            
        for target, share in zip(targets, shares):
            target_vault: LogarithmVault = target.entity
            assets = target_vault.action_redeem(share)
            # increase assets by the amount redeemed
            self._internal_state.assets += assets
            # remove target from allocated_vaults if the shares of target is 0
            internal_state: LogarithmVaultInternalState = target_vault.internal_state
            if internal_state.shares == 0:
                self._internal_state.allocated_vaults = [v for v in self._internal_state.allocated_vaults if v.entity_name != target.entity_name]

    def action_withdraw_allocations(self, targets: List[NamedEntity], assets: List[float]) -> None:
        if not targets or not assets:
            raise MetaVaultEntityException("Targets and assets Lists cannot be empty")
        if (len(targets) != len(assets)):
            raise MetaVaultEntityException("Targets and assets must have the same length")
        for target in targets:
            if not isinstance(target.entity, LogarithmVault):
                raise MetaVaultEntityException("Target must be a logarithm vault")
            if not any(allocated.entity_name == target.entity_name for allocated in self._internal_state.allocated_vaults):
                raise MetaVaultEntityException("Target vault is not allocated")
        
        # validate assets against targets
        for target, asset in zip(targets, assets):
            if asset <= 0:
                raise MetaVaultEntityException("Asset amount must be greater than 0")
            target_vault: LogarithmVault = target.entity
            if asset > target_vault.balance:
                raise MetaVaultEntityException("Asset is greater than the available balance of the target")

        for target, asset in zip(targets, assets):
            target_vault: LogarithmVault = target.entity
            target_vault.action_withdraw(asset)
            # increase assets by the amount withdrawn
            self._internal_state.assets += asset
            # remove target from allocated_vaults if the shares of target is 0
            internal_state: LogarithmVaultInternalState = target_vault.internal_state
            if internal_state.shares == 0:
                self._internal_state.allocated_vaults = [v for v in self._internal_state.allocated_vaults if v.entity_name != target.entity_name]
        
    def update_state(self, state: MetaVaultGlobalState):
        self._global_state = state

    @property
    def balance(self) -> float:
        # balance is the amount of assets in the vault entity
        return self._internal_state.assets + sum(vault.entity.balance for vault in self._internal_state.allocated_vaults)

