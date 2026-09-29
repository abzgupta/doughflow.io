"""
Savings Account Module

Handles interest-bearing savings accounts, checking accounts, and emergency funds.
"""

from typing import Dict, Any
from dataclasses import dataclass

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class SavingsState(ModuleState):
    """State for savings account"""
    ytd_interest_earned: float = 0.0
    ytd_deposits: float = 0.0
    ytd_withdrawals: float = 0.0


@register_module
class SavingsAccountModule(BaseModule):
    """
    Savings/Checking Account Module

    Models interest-bearing accounts with:
    - APY (Annual Percentage Yield)
    - Minimum balance requirements
    - Target balance (for emergency funds)
    - Interest compounding

    Config Parameters:
        name: Account name
        account_type: 'checking', 'savings', 'emergency_fund', 'money_market'
        initial_balance: Starting balance
        apy: Annual Percentage Yield
        compound_frequency: 'daily', 'monthly', 'quarterly', 'annually'
        minimum_balance: Minimum balance requirement
        target_balance: Target balance (for emergency funds)
        low_balance_fee: Monthly fee if below minimum balance
    """

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.ACCOUNT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.BOTH

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'Savings Account')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Account Name", "default": "Savings Account"},
                "account_type": {
                    "type": "string",
                    "enum": ["checking", "savings", "emergency_fund", "money_market"],
                    "title": "Account Type",
                    "default": "savings"
                },
                "initial_balance": {"type": "number", "title": "Initial Balance", "default": 0},
                "apy": {"type": "number", "title": "APY %", "default": 4.5},
                "compound_frequency": {
                    "type": "string",
                    "enum": ["daily", "monthly", "quarterly", "annually"],
                    "title": "Compound Frequency",
                    "default": "monthly"
                },
                "minimum_balance": {"type": "number", "title": "Minimum Balance", "default": 0},
                "target_balance": {"type": "number", "title": "Target Balance", "default": 0},
                "low_balance_fee": {"type": "number", "title": "Low Balance Fee", "default": 0}
            },
            "required": ["name"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', 'Savings Account')
        self.config.setdefault('account_type', 'savings')
        self.config.setdefault('initial_balance', 0)
        self.config.setdefault('apy', 4.5)
        self.config.setdefault('compound_frequency', 'monthly')
        self.config.setdefault('minimum_balance', 0)
        self.config.setdefault('target_balance', 0)
        self.config.setdefault('low_balance_fee', 0)

    def initialize(self, start_date: str) -> ModuleState:
        state = SavingsState()
        state.balance = self.config['initial_balance']
        self._state = state
        return state

    def _calculate_monthly_interest(self, balance: float) -> float:
        """Calculate interest for one month based on APY and compound frequency"""
        apy = self.config['apy'] / 100.0
        frequency = self.config['compound_frequency']

        if frequency == 'daily':
            # Convert APY to daily rate, then compound for ~30 days
            daily_rate = (1 + apy) ** (1/365) - 1
            monthly_rate = (1 + daily_rate) ** 30 - 1
        elif frequency == 'monthly':
            monthly_rate = (1 + apy) ** (1/12) - 1
        elif frequency == 'quarterly':
            # Interest only applied every 3 months
            monthly_rate = 0  # Will handle quarterly separately
        else:  # annually
            monthly_rate = 0  # Will handle annually separately

        return balance * monthly_rate

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        # Ensure we have a properly initialized state
        if not isinstance(self._state, SavingsState):
            self.initialize(f"{year}-{month:02d}")
        state = self._state
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_interest_earned = 0
            state.ytd_deposits = 0
            state.ytd_withdrawals = 0

        # Process inflows (deposits)
        total_deposits = sum(inflows.values())
        state.balance += total_deposits
        state.ytd_deposits += total_deposits

        # Calculate interest
        frequency = self.config['compound_frequency']
        interest = 0.0

        if frequency == 'daily' or frequency == 'monthly':
            interest = self._calculate_monthly_interest(state.balance)
        elif frequency == 'quarterly' and month in [3, 6, 9, 12]:
            apy = self.config['apy'] / 100.0
            quarterly_rate = (1 + apy) ** (1/4) - 1
            interest = state.balance * quarterly_rate
        elif frequency == 'annually' and month == 12:
            apy = self.config['apy'] / 100.0
            interest = state.balance * apy

        state.balance += interest
        state.ytd_interest_earned += interest

        # Check for low balance fee
        if state.balance < self.config['minimum_balance'] and self.config['low_balance_fee'] > 0:
            fee = self.config['low_balance_fee']
            state.balance -= fee
            result.events.append(f"Low balance fee charged: ${fee:.2f}")

        # Tax info - interest is taxable income
        tax_info.taxable_income = interest

        # Calculate available for outflow (respecting target balance for emergency funds)
        target = self.config['target_balance']
        if target > 0:
            available = max(0, state.balance - target)
        else:
            available = state.balance

        result.amount_received = total_deposits + interest
        result.amount_sent = 0  # Will be calculated by executor based on edges
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, SavingsState) else SavingsState()
        return {
            'ending_balance': state.balance,
            'interest_earned': state.ytd_interest_earned,
            'total_deposits': state.ytd_deposits,
            'total_withdrawals': state.ytd_withdrawals
        }
