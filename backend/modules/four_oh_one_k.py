"""
401(k) Retirement Account Module

Handles traditional and Roth 401(k) accounts with contribution limits,
employer matching, and vesting schedules.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class FourOhOneKState(ModuleState):
    """State for 401(k) account"""
    employee_balance: float = 0.0
    employer_balance: float = 0.0
    vested_employer_balance: float = 0.0
    ytd_employee_contributions: float = 0.0
    ytd_employer_contributions: float = 0.0
    years_of_service: int = 0


@register_module
class FourOhOneKModule(BaseModule):
    """
    401(k) Retirement Account Module

    Models 401(k) accounts with:
    - Traditional (pre-tax) and Roth (post-tax) contributions
    - 2024 contribution limits ($23,000 employee, $69,000 total)
    - Catch-up contributions for age 50+ ($7,500)
    - Employer matching with various formulas
    - Vesting schedules (cliff, graded)
    - Expected growth rate
    - Early withdrawal penalties

    Config Parameters:
        name: Account name
        account_type: 'traditional' or 'roth'
        initial_balance: Starting balance
        expected_annual_return: Expected annual return %
        employer_match_pct: Employer match as % of salary
        employer_match_limit: Maximum % of salary employer will match
        vesting_type: 'immediate', 'cliff', 'graded'
        vesting_years: Years for cliff vesting or full graded vesting
        linked_salary_node: Node ID of linked salary for contribution limits
    """

    # 2024 limits
    EMPLOYEE_LIMIT_2024 = 23000
    CATCHUP_LIMIT_2024 = 7500
    TOTAL_LIMIT_2024 = 69000

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.INVESTMENT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.BOTH

    @property
    def display_name(self) -> str:
        return self.config.get('name', '401(k)')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Account Name", "default": "401(k)"},
                "account_type": {
                    "type": "string",
                    "enum": ["traditional", "roth"],
                    "title": "Account Type",
                    "default": "traditional"
                },
                "initial_balance": {"type": "number", "title": "Initial Balance", "default": 0},
                "expected_annual_return": {"type": "number", "title": "Expected Annual Return %", "default": 7},
                "employer_match_pct": {
                    "type": "number",
                    "title": "Employer Match %",
                    "description": "Employer matches this % of your contribution",
                    "default": 50
                },
                "employer_match_limit": {
                    "type": "number",
                    "title": "Match Limit (% of salary)",
                    "description": "Employer matches up to this % of your salary",
                    "default": 6
                },
                "vesting_type": {
                    "type": "string",
                    "enum": ["immediate", "cliff", "graded"],
                    "title": "Vesting Type",
                    "default": "graded"
                },
                "vesting_years": {"type": "integer", "title": "Vesting Years", "default": 4},
                "linked_salary_node": {"type": "string", "title": "Linked Salary Node ID"}
            },
            "required": ["name"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', '401(k)')
        self.config.setdefault('account_type', 'traditional')
        self.config.setdefault('initial_balance', 0)
        self.config.setdefault('expected_annual_return', 7)
        self.config.setdefault('employer_match_pct', 50)
        self.config.setdefault('employer_match_limit', 6)
        self.config.setdefault('vesting_type', 'graded')
        self.config.setdefault('vesting_years', 4)

    def initialize(self, start_date: str) -> ModuleState:
        state = FourOhOneKState()
        initial = self.config['initial_balance']
        state.employee_balance = initial
        state.employer_balance = 0
        state.vested_employer_balance = 0
        state.balance = initial
        self._state = state
        return state

    def _get_vesting_percentage(self, years: int) -> float:
        """Calculate vesting percentage based on years of service"""
        vesting_type = self.config['vesting_type']
        vesting_years = self.config['vesting_years']

        if vesting_type == 'immediate':
            return 1.0
        elif vesting_type == 'cliff':
            return 1.0 if years >= vesting_years else 0.0
        else:  # graded
            if years >= vesting_years:
                return 1.0
            # Linear vesting
            return years / vesting_years

    def _get_monthly_return(self) -> float:
        annual_return = self.config['expected_annual_return'] / 100.0
        return (1 + annual_return) ** (1/12) - 1

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, FourOhOneKState) else FourOhOneKState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD and increment years at start of year
        if month == 1:
            state.ytd_employee_contributions = 0
            state.ytd_employer_contributions = 0
            state.years_of_service += 1

        # Process inflows (employee contributions)
        contribution = sum(inflows.values())

        # Check against annual limit
        employee_limit = self.EMPLOYEE_LIMIT_2024
        age = user_profile.get('age', 30)
        if age >= 50:
            employee_limit += self.CATCHUP_LIMIT_2024

        if state.ytd_employee_contributions + contribution > employee_limit:
            contribution = max(0, employee_limit - state.ytd_employee_contributions)
            result.events.append(f"401(k) contribution limit reached")

        if contribution > 0:
            state.employee_balance += contribution
            state.ytd_employee_contributions += contribution

            # Calculate employer match
            # Match is based on salary, which we need from user_profile or linked node
            annual_salary = user_profile.get('annual_salary', 100000)
            max_matchable = (annual_salary * (self.config['employer_match_limit'] / 100.0)) / 12

            matchable_contribution = min(contribution, max_matchable)
            employer_match = matchable_contribution * (self.config['employer_match_pct'] / 100.0)

            # Check total contribution limit
            total_ytd = state.ytd_employee_contributions + state.ytd_employer_contributions
            if total_ytd + employer_match > self.TOTAL_LIMIT_2024:
                employer_match = max(0, self.TOTAL_LIMIT_2024 - total_ytd)

            state.employer_balance += employer_match
            state.ytd_employer_contributions += employer_match

            # Tax treatment
            if self.config['account_type'] == 'traditional':
                tax_info.tax_deferred_income = contribution
            # Roth contributions are post-tax, so no deduction

        # Apply monthly growth
        monthly_return = self._get_monthly_return()
        growth_employee = state.employee_balance * monthly_return
        growth_employer = state.employer_balance * monthly_return
        state.employee_balance += growth_employee
        state.employer_balance += growth_employer

        # Calculate vested employer balance
        vesting_pct = self._get_vesting_percentage(state.years_of_service)
        state.vested_employer_balance = state.employer_balance * vesting_pct

        # Total balance (employee + vested employer)
        state.balance = state.employee_balance + state.vested_employer_balance

        result.amount_received = contribution
        result.amount_sent = 0  # 401k doesn't typically flow out in simulation
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def apply_outflow(self, amount: float) -> float:
        # Taxes and penalties on withdrawals aren't applied in the simulation yet (#9)
        return self.withdraw(amount, {})['gross_withdrawal']

    def withdraw(self, amount: float, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a withdrawal from the 401(k).
        Returns info about taxes and penalties.
        """
        state = self._state if isinstance(self._state, FourOhOneKState) else FourOhOneKState()

        age = user_profile.get('age', 30)
        is_early = age < 59.5

        available = state.balance
        actual_withdrawal = min(amount, available)

        # Withdraw from employee balance first, then vested employer
        from_employee = min(actual_withdrawal, state.employee_balance)
        state.employee_balance -= from_employee
        remaining = actual_withdrawal - from_employee

        if remaining > 0:
            from_employer = min(remaining, state.vested_employer_balance)
            state.employer_balance -= from_employer
            state.vested_employer_balance -= from_employer

        state.balance = state.employee_balance + state.vested_employer_balance

        # Calculate taxes and penalties
        result = {
            'gross_withdrawal': actual_withdrawal,
            'taxable_income': 0,
            'penalty': 0,
            'net_withdrawal': actual_withdrawal
        }

        if self.config['account_type'] == 'traditional':
            result['taxable_income'] = actual_withdrawal
            if is_early:
                result['penalty'] = actual_withdrawal * 0.10
                result['net_withdrawal'] = actual_withdrawal - result['penalty']

        # Roth: contributions tax-free, earnings may be taxed if early

        self._state = state
        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, FourOhOneKState) else FourOhOneKState()
        return {
            'employee_balance': state.employee_balance,
            'employer_balance': state.employer_balance,
            'vested_employer_balance': state.vested_employer_balance,
            'total_balance': state.balance,
            'employee_contributions': state.ytd_employee_contributions,
            'employer_contributions': state.ytd_employer_contributions,
            'vesting_percentage': self._get_vesting_percentage(state.years_of_service) * 100
        }
