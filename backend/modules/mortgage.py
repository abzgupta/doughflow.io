"""
Mortgage Module

Handles mortgage debt with amortization, interest deductions, and extra payments.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class MortgageState(ModuleState):
    """State for mortgage"""
    original_principal: float = 0.0
    remaining_principal: float = 0.0
    ytd_interest_paid: float = 0.0
    ytd_principal_paid: float = 0.0
    ytd_extra_principal: float = 0.0
    months_remaining: int = 0
    total_interest_paid: float = 0.0
    is_paid_off: bool = False


@register_module
class MortgageModule(BaseModule):
    """
    Mortgage Module

    Models mortgage debt with:
    - Standard amortization schedule
    - Fixed or adjustable rate
    - Mortgage interest deduction (up to $750k limit)
    - Extra principal payments
    - Refinancing tracking

    Config Parameters:
        name: Mortgage name
        original_principal: Original loan amount
        interest_rate_pct: Annual interest rate %
        term_years: Loan term in years
        start_month: Month mortgage started (1-12)
        start_year: Year mortgage started
        property_value: Property value (for LTV)
        is_primary_residence: Whether this is primary residence
        extra_monthly_payment: Extra monthly principal payment
    """

    # Mortgage interest deduction limit (TCJA 2017)
    MORTGAGE_DEDUCTION_LIMIT = 750000

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.DEBT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.OUTFLOW

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'Mortgage')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Mortgage Name", "default": "Primary Mortgage"},
                "original_principal": {"type": "number", "title": "Original Loan Amount", "default": 400000},
                "interest_rate_pct": {"type": "number", "title": "Interest Rate %", "default": 6.5},
                "term_years": {"type": "integer", "title": "Loan Term (years)", "default": 30},
                "start_month": {"type": "integer", "title": "Start Month", "default": 1, "minimum": 1, "maximum": 12},
                "start_year": {"type": "integer", "title": "Start Year", "default": 2024},
                "property_value": {"type": "number", "title": "Property Value", "default": 500000},
                "is_primary_residence": {"type": "boolean", "title": "Primary Residence", "default": True},
                "extra_monthly_payment": {"type": "number", "title": "Extra Monthly Payment", "default": 0}
            },
            "required": ["original_principal", "interest_rate_pct", "term_years"]
        }

    def _validate_config(self) -> None:
        if 'original_principal' not in self.config:
            raise ValueError("original_principal is required")
        if self.config['original_principal'] <= 0:
            raise ValueError("original_principal must be positive")

        self.config.setdefault('name', 'Mortgage')
        self.config.setdefault('interest_rate_pct', 6.5)
        self.config.setdefault('term_years', 30)
        self.config.setdefault('start_month', 1)
        self.config.setdefault('start_year', 2024)
        self.config.setdefault('property_value', self.config['original_principal'] * 1.25)
        self.config.setdefault('is_primary_residence', True)
        self.config.setdefault('extra_monthly_payment', 0)

    def initialize(self, start_date: str) -> ModuleState:
        state = MortgageState()
        state.original_principal = self.config['original_principal']
        state.remaining_principal = self.config['original_principal']
        state.months_remaining = self.config['term_years'] * 12
        # Balance is negative for debt
        state.balance = -self.config['original_principal']
        self._state = state
        return state

    def _calculate_monthly_payment(self) -> float:
        """Calculate standard monthly payment using amortization formula"""
        principal = self.config['original_principal']
        annual_rate = self.config['interest_rate_pct'] / 100.0
        term_months = self.config['term_years'] * 12

        if annual_rate == 0:
            return principal / term_months

        monthly_rate = annual_rate / 12
        payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / \
                  ((1 + monthly_rate) ** term_months - 1)
        return payment

    def _get_interest_principal_split(self, remaining_principal: float) -> tuple:
        """Calculate interest and principal portions of payment"""
        if remaining_principal <= 0:
            return 0, 0

        annual_rate = self.config['interest_rate_pct'] / 100.0
        monthly_rate = annual_rate / 12
        monthly_payment = self._calculate_monthly_payment()

        interest = remaining_principal * monthly_rate
        principal = min(monthly_payment - interest, remaining_principal)

        return interest, principal

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, MortgageState) else MortgageState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_interest_paid = 0
            state.ytd_principal_paid = 0
            state.ytd_extra_principal = 0

        # Check if already paid off
        if state.is_paid_off or state.remaining_principal <= 0:
            state.is_paid_off = True
            result.new_state = state
            self._state = state
            return result

        # Calculate this month's payment breakdown
        interest, principal = self._get_interest_principal_split(state.remaining_principal)

        # Apply extra payment
        extra = self.config['extra_monthly_payment']
        extra_from_inflow = sum(inflows.values())  # Extra payments from connected nodes
        total_extra = extra + extra_from_inflow

        # Don't pay more than remaining principal
        if principal + total_extra > state.remaining_principal:
            total_extra = state.remaining_principal - principal

        # Update state
        state.remaining_principal -= (principal + total_extra)
        state.ytd_interest_paid += interest
        state.ytd_principal_paid += principal
        state.ytd_extra_principal += total_extra
        state.total_interest_paid += interest
        state.months_remaining = max(0, state.months_remaining - 1)

        # Check if paid off
        if state.remaining_principal <= 0.01:  # Small tolerance
            state.remaining_principal = 0
            state.is_paid_off = True
            result.events.append(f"Mortgage paid off!")

        # Balance is negative (it's debt)
        state.balance = -state.remaining_principal

        # Calculate interest deduction
        if self.config['is_primary_residence']:
            # Only deduct interest on first $750k of mortgage debt
            if self.config['original_principal'] <= self.MORTGAGE_DEDUCTION_LIMIT:
                deductible_interest = interest
            else:
                # Pro-rate based on limit
                deductible_ratio = self.MORTGAGE_DEDUCTION_LIMIT / self.config['original_principal']
                deductible_interest = interest * deductible_ratio

            tax_info.deductions['mortgage_interest'] = deductible_interest

        # Total payment required this month
        total_payment = interest + principal + extra

        result.amount_received = extra_from_inflow
        result.amount_sent = total_payment  # Amount that needs to come from connected nodes
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def get_amortization_schedule(self) -> List[Dict]:
        """Generate full amortization schedule"""
        schedule = []
        remaining = self.config['original_principal']
        monthly_payment = self._calculate_monthly_payment()
        annual_rate = self.config['interest_rate_pct'] / 100.0
        monthly_rate = annual_rate / 12
        extra = self.config['extra_monthly_payment']

        month = 0
        while remaining > 0.01:
            month += 1
            interest = remaining * monthly_rate
            principal = min(monthly_payment - interest + extra, remaining)
            remaining -= principal

            schedule.append({
                'month': month,
                'payment': monthly_payment + extra,
                'principal': principal,
                'interest': interest,
                'remaining': max(0, remaining)
            })

            if month > 360:  # Safety limit
                break

        return schedule

    def get_payoff_info(self) -> Dict[str, Any]:
        """Get payoff information"""
        state = self._state if isinstance(self._state, MortgageState) else MortgageState()
        schedule = self.get_amortization_schedule()
        total_interest = sum(p['interest'] for p in schedule)
        months_to_payoff = len(schedule)

        return {
            'remaining_principal': state.remaining_principal,
            'total_interest_if_paid_normally': total_interest,
            'months_to_payoff': months_to_payoff,
            'years_to_payoff': months_to_payoff / 12,
            'monthly_payment': self._calculate_monthly_payment(),
            'payoff_amount': state.remaining_principal  # Current payoff
        }

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, MortgageState) else MortgageState()
        return {
            'remaining_principal': state.remaining_principal,
            'interest_paid': state.ytd_interest_paid,
            'principal_paid': state.ytd_principal_paid,
            'extra_principal_paid': state.ytd_extra_principal,
            'total_interest_paid_lifetime': state.total_interest_paid,
            'is_paid_off': state.is_paid_off,
            'months_remaining': state.months_remaining
        }
