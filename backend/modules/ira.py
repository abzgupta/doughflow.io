"""
IRA (Individual Retirement Account) Module

Handles Traditional and Roth IRAs with contribution limits,
income phase-outs, and conversion rules.
"""

from typing import Dict, Any
from dataclasses import dataclass

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class IRAState(ModuleState):
    """State for IRA account"""
    market_value: float = 0.0
    contributions: float = 0.0
    earnings: float = 0.0
    ytd_contributions: float = 0.0
    ytd_conversions: float = 0.0
    years_since_first_contribution: int = 0


@register_module
class IRAModule(BaseModule):
    """
    IRA (Individual Retirement Account) Module

    Models Traditional and Roth IRAs with:
    - 2024 contribution limits ($7,000, $8,000 for 50+)
    - Income phase-outs for Roth and Traditional deductibility
    - Backdoor Roth conversion tracking
    - 5-year rules for Roth
    - Early withdrawal penalties

    Config Parameters:
        name: Account name
        account_type: 'traditional' or 'roth'
        initial_balance: Starting balance
        expected_annual_return: Expected annual return %
        is_backdoor: Whether this is for backdoor Roth strategy
    """

    # 2024 limits
    CONTRIBUTION_LIMIT_2024 = 7000
    CATCHUP_LIMIT_2024 = 1000  # Additional for 50+

    # 2024 income phase-outs (married filing jointly)
    ROTH_PHASE_OUT_START_MFJ = 230000
    ROTH_PHASE_OUT_END_MFJ = 240000
    TRADITIONAL_PHASE_OUT_START_MFJ = 123000  # If covered by employer plan
    TRADITIONAL_PHASE_OUT_END_MFJ = 143000

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.INVESTMENT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.BOTH

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'IRA')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Account Name", "default": "Roth IRA"},
                "account_type": {
                    "type": "string",
                    "enum": ["traditional", "roth"],
                    "title": "Account Type",
                    "default": "roth"
                },
                "initial_balance": {"type": "number", "title": "Initial Balance", "default": 0},
                "expected_annual_return": {"type": "number", "title": "Expected Annual Return %", "default": 7},
                "is_backdoor": {
                    "type": "boolean",
                    "title": "Backdoor Roth Strategy",
                    "default": False
                }
            },
            "required": ["name"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', 'IRA')
        self.config.setdefault('account_type', 'roth')
        self.config.setdefault('initial_balance', 0)
        self.config.setdefault('expected_annual_return', 7)
        self.config.setdefault('is_backdoor', False)

    def initialize(self, start_date: str) -> ModuleState:
        state = IRAState()
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

    def _get_contribution_limit(self, user_profile: Dict[str, Any]) -> float:
        """Get contribution limit based on age and income"""
        age = user_profile.get('age', 30)
        limit = self.CONTRIBUTION_LIMIT_2024
        if age >= 50:
            limit += self.CATCHUP_LIMIT_2024

        # Check income phase-outs
        magi = user_profile.get('magi', 0)
        filing_status = user_profile.get('filing_status', 'single')

        if self.config['account_type'] == 'roth' and not self.config['is_backdoor']:
            if filing_status in ['married_jointly', 'mfj']:
                if magi >= self.ROTH_PHASE_OUT_END_MFJ:
                    limit = 0
                elif magi > self.ROTH_PHASE_OUT_START_MFJ:
                    phase_out_range = self.ROTH_PHASE_OUT_END_MFJ - self.ROTH_PHASE_OUT_START_MFJ
                    reduction = (magi - self.ROTH_PHASE_OUT_START_MFJ) / phase_out_range
                    limit = limit * (1 - reduction)
            else:  # Single
                single_start = 146000
                single_end = 161000
                if magi >= single_end:
                    limit = 0
                elif magi > single_start:
                    reduction = (magi - single_start) / (single_end - single_start)
                    limit = limit * (1 - reduction)

        return limit

    def _get_deductible_amount(self, contribution: float, user_profile: Dict[str, Any]) -> float:
        """Calculate deductible amount for Traditional IRA"""
        if self.config['account_type'] != 'traditional':
            return 0

        magi = user_profile.get('magi', 0)
        has_employer_plan = user_profile.get('has_employer_retirement_plan', False)
        filing_status = user_profile.get('filing_status', 'single')

        if not has_employer_plan:
            # Fully deductible if no employer plan
            return contribution

        # Phase-out for those with employer plans
        if filing_status in ['married_jointly', 'mfj']:
            if magi >= self.TRADITIONAL_PHASE_OUT_END_MFJ:
                return 0
            elif magi > self.TRADITIONAL_PHASE_OUT_START_MFJ:
                range_ = self.TRADITIONAL_PHASE_OUT_END_MFJ - self.TRADITIONAL_PHASE_OUT_START_MFJ
                reduction = (magi - self.TRADITIONAL_PHASE_OUT_START_MFJ) / range_
                return contribution * (1 - reduction)
        else:  # Single
            single_start = 77000
            single_end = 87000
            if magi >= single_end:
                return 0
            elif magi > single_start:
                reduction = (magi - single_start) / (single_end - single_start)
                return contribution * (1 - reduction)

        return contribution

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, IRAState) else IRAState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_contributions = 0
            state.ytd_conversions = 0
            if state.contributions > 0:
                state.years_since_first_contribution += 1

        # Process inflows (contributions)
        contribution = sum(inflows.values())

        # Check against limit
        limit = self._get_contribution_limit(user_profile)
        if state.ytd_contributions + contribution > limit:
            contribution = max(0, limit - state.ytd_contributions)
            if contribution < sum(inflows.values()):
                result.events.append(f"IRA contribution limit reached")

        if contribution > 0:
            state.market_value += contribution
            state.contributions += contribution
            state.ytd_contributions += contribution

            # Tax treatment
            if self.config['account_type'] == 'traditional':
                deductible = self._get_deductible_amount(contribution, user_profile)
                if deductible > 0:
                    tax_info.deductions['ira_deduction'] = deductible
                    tax_info.tax_deferred_income = deductible
            # Roth: post-tax, no deduction

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

    def convert_to_roth(self, amount: float) -> Dict[str, Any]:
        """
        Convert Traditional IRA to Roth (backdoor Roth or regular conversion).
        Returns tax implications.
        """
        state = self._state if isinstance(self._state, IRAState) else IRAState()

        if self.config['account_type'] != 'traditional':
            return {'error': 'Can only convert from Traditional IRA'}

        actual_amount = min(amount, state.market_value)

        # Calculate taxable portion
        if state.market_value > 0:
            # Pro-rata rule: proportion of pre-tax to total
            pre_tax_ratio = (state.market_value - state.contributions) / state.market_value
        else:
            pre_tax_ratio = 0

        # For backdoor Roth (recent non-deductible contributions), minimal tax
        if self.config['is_backdoor']:
            taxable = actual_amount * pre_tax_ratio  # Only earnings taxed
        else:
            taxable = actual_amount  # All taxable (was pre-tax)

        state.market_value -= actual_amount
        state.ytd_conversions += actual_amount

        # Proportionally reduce contributions and earnings
        if state.market_value > 0:
            reduction_ratio = actual_amount / (state.market_value + actual_amount)
            state.contributions *= (1 - reduction_ratio)
            state.earnings *= (1 - reduction_ratio)

        state.balance = state.market_value
        self._state = state

        return {
            'amount_converted': actual_amount,
            'taxable_income': taxable,
            'is_backdoor': self.config['is_backdoor']
        }

    def withdraw(self, amount: float, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a withdrawal from the IRA.
        Returns tax and penalty implications.
        """
        state = self._state if isinstance(self._state, IRAState) else IRAState()
        age = user_profile.get('age', 30)

        actual_amount = min(amount, state.market_value)

        result = {
            'amount': actual_amount,
            'taxable_income': 0,
            'penalty': 0
        }

        if self.config['account_type'] == 'traditional':
            # All Traditional IRA withdrawals are taxable
            result['taxable_income'] = actual_amount
            if age < 59.5:
                result['penalty'] = actual_amount * 0.10
        else:
            # Roth: contributions tax-free, earnings may be taxed
            if actual_amount <= state.contributions:
                # Withdrawing contributions: tax-free, no penalty
                pass
            else:
                # Withdrawing earnings
                earnings_withdrawn = actual_amount - state.contributions
                if age < 59.5 or state.years_since_first_contribution < 5:
                    result['taxable_income'] = earnings_withdrawn
                    result['penalty'] = earnings_withdrawn * 0.10

        # Update state
        state.market_value -= actual_amount
        if actual_amount <= state.contributions:
            state.contributions -= actual_amount
        else:
            state.earnings -= (actual_amount - state.contributions)
            state.contributions = 0

        state.balance = state.market_value
        self._state = state

        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, IRAState) else IRAState()
        return {
            'market_value': state.market_value,
            'total_contributions': state.contributions,
            'total_earnings': state.earnings,
            'ytd_contributions': state.ytd_contributions,
            'ytd_conversions': state.ytd_conversions,
            'years_since_first_contribution': state.years_since_first_contribution
        }
