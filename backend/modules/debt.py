"""
Debt Module

Handles various types of debt including student loans, car loans,
personal loans, and credit card debt.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class DebtState(ModuleState):
    """State for debt accounts"""
    original_principal: float = 0.0
    current_balance: float = 0.0
    ytd_interest_paid: float = 0.0
    ytd_principal_paid: float = 0.0
    ytd_payments: float = 0.0
    total_interest_paid: float = 0.0
    total_principal_paid: float = 0.0
    months_remaining: int = 0
    is_paid_off: bool = False


@register_module
class DebtModule(BaseModule):
    """
    Debt Module

    Models various types of debt with:
    - Fixed or variable interest rates
    - Minimum monthly payments
    - Extra payment support
    - Amortization tracking
    - Interest deduction tracking (for student loans)

    Config Parameters:
        name: Debt name
        debt_type: 'student_loan', 'car_loan', 'personal_loan', 'credit_card'
        original_principal: Original loan amount
        current_balance: Current balance (defaults to original_principal)
        interest_rate_pct: Annual interest rate percentage
        minimum_payment: Minimum monthly payment
        loan_term_months: Original loan term in months (for amortized loans)
        is_tax_deductible: Whether interest is tax deductible (student loans up to $2,500)
        extra_payment: Additional monthly payment beyond minimum
    """

    # Student loan interest deduction limit
    STUDENT_LOAN_INTEREST_DEDUCTION_LIMIT = 2500

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.DEBT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.INFLOW  # Receives payments

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'Debt')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Debt Name", "default": "Loan"},
                "debt_type": {
                    "type": "string",
                    "enum": ["student_loan", "car_loan", "personal_loan", "credit_card"],
                    "title": "Debt Type",
                    "default": "student_loan"
                },
                "original_principal": {"type": "number", "title": "Original Amount", "default": 0},
                "current_balance": {"type": "number", "title": "Current Balance", "default": 0},
                "interest_rate_pct": {"type": "number", "title": "Interest Rate %", "default": 6.0},
                "minimum_payment": {"type": "number", "title": "Minimum Payment", "default": 0},
                "loan_term_months": {"type": "integer", "title": "Loan Term (Months)", "default": 120},
                "is_tax_deductible": {"type": "boolean", "title": "Tax Deductible Interest", "default": False},
                "extra_payment": {"type": "number", "title": "Extra Monthly Payment", "default": 0}
            },
            "required": ["name", "current_balance", "interest_rate_pct"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', 'Loan')
        self.config.setdefault('debt_type', 'student_loan')
        self.config.setdefault('original_principal', self.config.get('current_balance', 0))
        self.config.setdefault('current_balance', self.config.get('original_principal', 0))
        self.config.setdefault('interest_rate_pct', 6.0)
        self.config.setdefault('minimum_payment', 0)
        self.config.setdefault('loan_term_months', 120)
        self.config.setdefault('extra_payment', 0)

        # Student loans have tax-deductible interest by default
        if 'is_tax_deductible' not in self.config:
            self.config['is_tax_deductible'] = self.config['debt_type'] == 'student_loan'

        # Calculate minimum payment if not provided (standard amortization)
        if self.config['minimum_payment'] == 0 and self.config['current_balance'] > 0:
            self.config['minimum_payment'] = self._calculate_amortized_payment()

    def _calculate_amortized_payment(self) -> float:
        """Calculate standard amortized monthly payment."""
        principal = self.config['current_balance']
        rate = self.config['interest_rate_pct'] / 100.0
        months = self.config['loan_term_months']

        if rate == 0:
            return principal / months if months > 0 else 0

        monthly_rate = rate / 12
        if months <= 0:
            return 0

        # Standard amortization formula
        payment = principal * (monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        return payment

    def initialize(self, start_date: str) -> ModuleState:
        state = DebtState()
        state.original_principal = self.config['original_principal']
        state.current_balance = self.config['current_balance']
        state.balance = -state.current_balance  # Negative because it's debt

        # Calculate months remaining
        if self.config['minimum_payment'] > 0:
            state.months_remaining = self._estimate_months_remaining(state.current_balance)
        else:
            state.months_remaining = self.config['loan_term_months']

        self._state = state
        return state

    def _estimate_months_remaining(self, balance: float) -> int:
        """Estimate months to payoff at current payment rate."""
        payment = self.config['minimum_payment'] + self.config['extra_payment']
        rate = self.config['interest_rate_pct'] / 100.0 / 12

        if payment <= 0 or balance <= 0:
            return 0

        if rate == 0:
            return int(balance / payment) + 1

        # If payment doesn't cover interest, it will never be paid off
        monthly_interest = balance * rate
        if payment <= monthly_interest:
            return 999  # Essentially infinite

        # Calculate months using logarithm
        import math
        months = -math.log(1 - (balance * rate / payment)) / math.log(1 + rate)
        return int(months) + 1

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, DebtState) else DebtState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_interest_paid = 0
            state.ytd_principal_paid = 0
            state.ytd_payments = 0

        # If already paid off, nothing to do
        if state.is_paid_off or state.current_balance <= 0:
            state.is_paid_off = True
            state.current_balance = 0
            state.balance = 0
            result.new_state = state
            self._state = state
            return result

        # Calculate interest for this month
        monthly_rate = self.config['interest_rate_pct'] / 100.0 / 12
        interest_charge = state.current_balance * monthly_rate

        # Total payment received (from inflows)
        total_payment = sum(inflows.values())

        # If no payment received, use minimum + extra as the expected payment
        if total_payment == 0:
            total_payment = self.config['minimum_payment'] + self.config['extra_payment']

        # Apply payment: interest first, then principal
        interest_paid = min(interest_charge, total_payment)
        principal_paid = total_payment - interest_paid

        # Ensure we don't overpay
        if principal_paid > state.current_balance:
            principal_paid = state.current_balance
            total_payment = interest_paid + principal_paid

        # Update balance
        state.current_balance -= principal_paid

        # Update tracking
        state.ytd_interest_paid += interest_paid
        state.ytd_principal_paid += principal_paid
        state.ytd_payments += total_payment
        state.total_interest_paid += interest_paid
        state.total_principal_paid += principal_paid

        # Check if paid off
        if state.current_balance <= 0.01:  # Small threshold for floating point
            state.current_balance = 0
            state.is_paid_off = True
            state.months_remaining = 0
            result.events.append(f"{self.config['name']} paid off!")
        else:
            state.months_remaining = self._estimate_months_remaining(state.current_balance)

        # Update balance (negative for debt)
        state.balance = -state.current_balance

        # Tax deduction for student loan interest
        if self.config['is_tax_deductible'] and interest_paid > 0:
            # Student loan interest deduction is capped at $2,500/year
            if self.config['debt_type'] == 'student_loan':
                remaining_deduction = max(0, self.STUDENT_LOAN_INTEREST_DEDUCTION_LIMIT - (state.ytd_interest_paid - interest_paid))
                deductible_interest = min(interest_paid, remaining_deduction)
                tax_info.deductions['student_loan_interest'] = deductible_interest

        result.amount_received = total_payment
        result.amount_sent = 0
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, DebtState) else DebtState()
        return {
            'current_balance': state.current_balance,
            'interest_paid': state.ytd_interest_paid,
            'principal_paid': state.ytd_principal_paid,
            'total_payments': state.ytd_payments,
            'total_interest_paid_lifetime': state.total_interest_paid,
            'total_principal_paid_lifetime': state.total_principal_paid,
            'months_remaining': state.months_remaining,
            'is_paid_off': state.is_paid_off,
            'deductible_interest': min(state.ytd_interest_paid, self.STUDENT_LOAN_INTEREST_DEDUCTION_LIMIT) if self.config['is_tax_deductible'] else 0
        }
