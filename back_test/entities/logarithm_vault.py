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
    idle_assets: float = 0.0
    pending_withdrawals: float = 0.0

class LogarithmVault(BaseEntity):
    """
    Represents a logarithm vault entity.
    """

    def __init__(self, entry_cost_rate: float = 0.0035, exit_cost_rate: float = 0.0035):
        if entry_cost_rate < 0 or exit_cost_rate < 0 or entry_cost_rate > 0.01 or exit_cost_rate > 0.01:
            raise LogarithmVaultEntityException("Entry and exit costs must be between 0 and 0.01")
        
        self._entry_cost_rate = entry_cost_rate
        self._exit_cost_rate = exit_cost_rate

        super().__init__()

    def _initialize_states(self):
        self._global_state: LogarithmVaultGlobalState = LogarithmVaultGlobalState()
        self._internal_state: LogarithmVaultInternalState = LogarithmVaultInternalState()

    def mock_idle_n_pending_withdrawals(self, idle_assets: float, pending_withdrawals: float):
        """
        Mock the idle assets and pending withdrawals.
        """
        if idle_assets < 0 or pending_withdrawals < 0:
            raise LogarithmVaultEntityException("Idle assets and pending withdrawals must be greater than 0")
        if idle_assets > 0 and pending_withdrawals > 0:
            raise LogarithmVaultEntityException("Idle assets and pending withdrawals cannot be both greater than 0")

        self._internal_state.idle_assets = idle_assets
        self._internal_state.pending_withdrawals = pending_withdrawals

        print(f"Idle assets: {self._internal_state.idle_assets}")
        print(f"Pending withdrawals: {self._internal_state.pending_withdrawals}")

    def action_deposit(self, assets: float) -> float:
        # deposit assets to the vault entity
        # receive shares in return

        if assets < 0:
            raise LogarithmVaultEntityException("Assets must be greater than 0")
        
        shares_to_mint = self.preview_deposit(assets)

        self._internal_state.shares += shares_to_mint

        return shares_to_mint
    
    def action_redeem(self, shares: float) -> float:
        # redeem the shares from the vault entity
        # receive assets in return

        if shares < 0:
            raise LogarithmVaultEntityException("Shares must be greater than 0")
        if (shares > self._internal_state.shares):
            raise LogarithmVaultEntityException("Shares to redeem are greater than the available shares")
        
        assets_to_withdraw = self.preview_redeem(shares)

        self._internal_state.shares -= shares

        return assets_to_withdraw
    
    def action_withdraw(self, assets: float) -> float:
        # withdraw assets from the vault entity
        # burn shares required to withdraw the assets
        
        if assets < 0:
            raise LogarithmVaultEntityException("Assets must be greater than 0")
        
        allocated_assets = self.balance
        if assets == allocated_assets:
            shares_to_burn = self._internal_state.shares
            self._internal_state.shares = 0
            return shares_to_burn
        elif assets > allocated_assets:
            raise LogarithmVaultEntityException("Not enough allocated assets")
        else:
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
        # balance is the amount of assets held in the vault entity
        return self.preview_redeem(self._internal_state.shares)

    @property
    def shares(self) -> float:
        return self._internal_state.shares
    
    @property
    def entry_cost_rate(self) -> float:
        return self._entry_cost_rate

    @property
    def exit_cost_rate(self) -> float:
        return self._exit_cost_rate
    
    @property
    def idle_assets(self) -> float:
        return self._internal_state.idle_assets
    
    @property
    def pending_withdrawals(self) -> float:
        return self._internal_state.pending_withdrawals
    
    def preview_deposit(self, assets: float) -> float:
        # Preview the number of shares that would be received for a given amount of assets
        # without modifying the internal state.

        assets_to_utilize = assets - self.pending_withdrawals if assets > self.pending_withdrawals else 0        
        entry_cost = assets_to_utilize * self.entry_cost_rate / (1 + self.entry_cost_rate)
        assets_after_entry_cost = assets - entry_cost
        shares_in_return = assets_after_entry_cost / self._global_state.share_price

        return shares_in_return
    
    def preview_redeem(self, shares: float) -> float:
        # Preview the assets that would be received for a given number of shares
        # without modifying the internal state.
        
        assets = shares * self._global_state.share_price
        assets_to_deutilize = assets - self.idle_assets if assets > self.idle_assets else 0
        exit_cost = assets_to_deutilize * self.exit_cost_rate / (1 + self.exit_cost_rate)
        assets_after_exit_cost = assets - exit_cost

        return assets_after_exit_cost

    def preview_withdraw(self, assets: float) -> float:
        # Preview the number of shares that would be burned for a given amount of assets
        # without modifying the internal state.
        
        assets_from_deutilize = assets - self.idle_assets if assets > self.idle_assets else 0
        exit_cost = assets_from_deutilize * self.exit_cost_rate
        assets_after_exit_cost = assets + exit_cost
        shares_to_burn = assets_after_exit_cost / self._global_state.share_price

        return shares_to_burn
