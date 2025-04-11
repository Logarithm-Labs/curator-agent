from dataclasses import dataclass
from fractal.core.base.entity import BaseEntity, EntityException, InternalState, GlobalState

class LogarithmVaultEntityException(EntityException):
    """
    Exception raised for errors in the Logarithm Vault entity.
    """

@dataclass
class LogarithmVaultGlobalState(GlobalState):
    share_price: float = 1.0

@dataclass
class LogarithmVaultInternalState:
    shares: float = 0.0

class LogarithmVault(BaseEntity):
    """
    Represents a logarithm vault entity.
    """

    def __init__(self, entry_cost: float = 0.0035, exit_cost: float = 0.0035):
        if entry_cost <= 0 or exit_cost <= 0 or entry_cost >= 0.01 or exit_cost >= 0.01:
            raise LogarithmVaultEntityException("Entry and exit costs must be between 0 and 0.01")
        
        self._entry_cost = entry_cost
        self._exit_cost = exit_cost
        super().__init__()

    def _initialize_states(self):
        self._global_state: LogarithmVaultGlobalState = LogarithmVaultGlobalState()
        self._internal_state: LogarithmVaultInternalState = LogarithmVaultInternalState()

    def action_deposit(self, assets: float) -> float:
        # deposit assets to the vault entity
        # receive shares in return
        # entry cost is taken from the amount
        # TODO entry cost should be dynamic based on the pending withdrawals on the vault

        if assets <= 0:
            raise LogarithmVaultEntityException("Assets must be greater than 0")
        
        shares_in_return = self.preview_deposit(assets)

        self._internal_state.shares += shares_in_return

        return shares_in_return
    
    def action_redeem(self, shares: float) -> float:
        # redeem the shares from the vault entity
        # receive assets in return
        # exit cost is taken from the amount
        # TODO exit cost should be dynamic based on the pending deposits on the vault

        if shares <= 0:
            raise LogarithmVaultEntityException("Shares must be greater than 0")
        if (shares > self._internal_state.shares):
            raise LogarithmVaultEntityException("Shares to redeem are greater than the available shares")

        self._internal_state.shares -= shares

        return self.preview_redeem(shares)
    
    def action_withdraw(self, assets: float) -> float:
        # withdraw assets from the vault entity
        # burn shares required to withdraw the assets
        # exit cost is taken from the amount
        # TODO exit cost should be dynamic based on the idle assets on the vault
        
        if assets <= 0:
            raise LogarithmVaultEntityException("Assets must be greater than 0")
        
        shares_to_burn = self.preview_withdraw(assets)

        if shares_to_burn > self._internal_state.shares:
            raise LogarithmVaultEntityException("Not enough shares available to withdraw the requested assets")

        self._internal_state.shares -= shares_to_burn

        return shares_to_burn
        
    def update_state(self, state: LogarithmVaultGlobalState):
        if state.share_price <= 0:
            raise LogarithmVaultEntityException("Share price must be greater than 0")
        
        self._global_state = state

    @property
    def balance(self) -> float:
        # balance is the amount of assets in the vault entity
        # exit cost is taken into account
        # TODO exit cost should be dynamic based on the idle assets on the vault
        return self.preview_redeem(self._internal_state.shares)

    def preview_redeem(self, shares: float) -> float:
        # Preview the assets that would be received for a given number of shares
        # without modifying the internal state.
        
        assets_before_exit_cost = shares * self._global_state.share_price
        assets_after_exit_cost = assets_before_exit_cost / (1 + self._exit_cost)

        return assets_after_exit_cost

    def preview_withdraw(self, assets: float) -> float:
        # Preview the number of shares that would be burned for a given amount of assets
        # without modifying the internal state.
        
        assets_after_exit_cost = assets * (1 + self._exit_cost)
        shares_to_burn = assets_after_exit_cost / self._global_state.share_price

        return shares_to_burn

    def preview_deposit(self, assets: float) -> float:
        # Preview the number of shares that would be received for a given amount of assets
        # without modifying the internal state.
        
        assets_after_entry_cost = assets / (1 + self._entry_cost)
        shares_in_return = assets_after_entry_cost / self._global_state.share_price

        return shares_in_return
