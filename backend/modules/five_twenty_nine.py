"""
529 Education Savings Plan Module

Handles 529 college savings plans with qualified distributions and state tax benefits.
"""

from typing import Dict, Any
from dataclasses import dataclass

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class FiveTwentyNineState(ModuleState):
    """State for 529 plan"""
    market_value: float = 0.0
    contributions: float = 0.0
    earnings: float = 0.0
    ytd_contributions: float = 0.0
    ytd_qualified_distributions: float = 0.0
    ytd_non_qualified_distributions: float = 0.0


@register_module
class FiveTwentyNineModule(BaseModule):
    """
    529 Education Savings Plan Module

    Models 529 plans with:
    - Tax-free growth for qualified education expenses
    - State tax deduction for contributions (varies by state)
    - Federal gift tax considerations
    - Qualified distribution rules
    - Penalty for non-qualified distributions

    Config Parameters:
        name: Account name
        beneficiary: Name of beneficiary
        initial_balance: Starting balance
        expected_annual_return: Expected annual return %
        state: State for tax deduction purposes
        max_annual_contribution: Maximum annual contribution
        target_college_year: Year beneficiary starts college
    """

    # 2024 annual gift tax exclusion
    ANNUAL_GIFT_EXCLUSION = 18000
    # 5-year gift tax averaging limit
    FIVE_YEAR_LIMIT = 90000

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.INVESTMENT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.BOTH

    @property
    def display_name(self) -> str:
        return self.config.get('name', '529 Plan')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Account Name", "default": "529 Plan"},
                "beneficiary": {"type": "string", "title": "Beneficiary Name"},
                "initial_balance": {"type": "number", "title": "Initial Balance", "default": 0},
                "expected_annual_return": {"type": "number", "title": "Expected Annual Return %", "default": 6},
                "state": {"type": "string", "title": "State", "default": "CA"},
                "max_annual_contribution": {
                    "type": "number",
                    "title": "Max Annual Contribution",
                    "default": 18000
                },
                "target_college_year": {
                    "type": "integer",
                    "title": "Target College Start Year",
                    "default": 2035
                }
            },
            "required": ["name"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', '529 Plan')
        self.config.setdefault('beneficiary', 'Child')
        self.config.setdefault('initial_balance', 0)
        self.config.setdefault('expected_annual_return', 6)
        self.config.setdefault('state', 'CA')
        self.config.setdefault('max_annual_contribution', self.ANNUAL_GIFT_EXCLUSION)
        self.config.setdefault('target_college_year', 2035)

    def initialize(self, start_date: str) -> ModuleState:
        state = FiveTwentyNineState()
        initial = self.config['initial_balance']
        state.market_value = initial
        state.contributions = initial
        state.earnings = 0
        state.balance = initial
        self._state = state
        return state

    def _get_monthly_return(self) -> float:
        annual_return = self.config['expected_annual_return'] / 100.0
        return (1 + annual_return) ** (1/12) - 1

    def _get_state_deduction(self, contribution: float, state: str) -> float:
        """
        Calculate state tax deduction for 529 contribution.
        Returns maximum deductible amount (varies by state).
        """
        # State deduction limits (2024 estimates, some states have unlimited)
        state_limits = {
            'NY': 10000,  # $5k single, $10k married
            'CA': 0,      # No deduction
            'TX': 0,      # No state income tax
            'IL': 20000,  # $10k single, $20k married
            'PA': 32000,  # $16k per beneficiary
            'CO': 999999,  # Unlimited
            'VA': 8000,   # $4k per account
        }
        limit = state_limits.get(state, 5000)
        return min(contribution, limit)

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, FiveTwentyNineState) else FiveTwentyNineState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_contributions = 0
            state.ytd_qualified_distributions = 0
            state.ytd_non_qualified_distributions = 0

        # Process inflows (contributions)
        contribution = sum(inflows.values())

        # Check against annual limit
        max_contrib = self.config['max_annual_contribution']
        if state.ytd_contributions + contribution > max_contrib:
            contribution = max(0, max_contrib - state.ytd_contributions)

        if contribution > 0:
            state.market_value += contribution
            state.contributions += contribution
            state.ytd_contributions += contribution

            # State tax deduction
            user_state = user_profile.get('state', self.config['state'])
            deduction = self._get_state_deduction(contribution, user_state)
            if deduction > 0:
                tax_info.deductions['529_state_deduction'] = deduction

        # Apply monthly growth
        monthly_return = self._get_monthly_return()
        growth = state.market_value * monthly_return
        state.market_value += growth
        state.earnings += growth

        # Update balance
        state.balance = state.market_value

        result.amount_received = contribution
        result.amount_sent = 0
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def distribute(self, amount: float, qualified: bool) -> Dict[str, Any]:
        """
        Process a distribution from the 529.

        Args:
            amount: Amount to distribute
            qualified: Whether this is for qualified education expenses

        Returns:
            Dict with distribution details and tax implications
        """
        state = self._state if isinstance(self._state, FiveTwentyNineState) else FiveTwentyNineState()

        actual_amount = min(amount, state.market_value)

        # Calculate earnings portion (taxable for non-qualified)
        if state.market_value > 0:
            earnings_ratio = state.earnings / state.market_value
        else:
            earnings_ratio = 0

        earnings_portion = actual_amount * earnings_ratio
        contribution_portion = actual_amount - earnings_portion

        result = {
            'amount': actual_amount,
            'from_contributions': contribution_portion,
            'from_earnings': earnings_portion,
            'taxable_income': 0,
            'penalty': 0
        }

        if qualified:
            # Qualified: tax-free
            state.ytd_qualified_distributions += actual_amount
        else:
            # Non-qualified: earnings taxed + 10% penalty
            result['taxable_income'] = earnings_portion
            result['penalty'] = earnings_portion * 0.10
            state.ytd_non_qualified_distributions += actual_amount

        # Update balances
        state.market_value -= actual_amount
        state.contributions -= contribution_portion
        state.earnings -= earnings_portion
        state.balance = state.market_value

        self._state = state
        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, FiveTwentyNineState) else FiveTwentyNineState()
        return {
            'market_value': state.market_value,
            'total_contributions': state.contributions,
            'total_earnings': state.earnings,
            'ytd_contributions': state.ytd_contributions,
            'qualified_distributions': state.ytd_qualified_distributions,
            'non_qualified_distributions': state.ytd_non_qualified_distributions
        }
