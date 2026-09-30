"""
Salary/Income Module

Handles W2 and 1099 income with tax withholding calculations.
"""

from typing import Dict, Any
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class SalaryState(ModuleState):
    """State for salary income"""
    ytd_gross: float = 0.0
    ytd_federal_withholding: float = 0.0
    ytd_state_withholding: float = 0.0
    ytd_fica: float = 0.0
    ytd_medicare: float = 0.0
    ytd_401k: float = 0.0


@register_module
class SalaryModule(BaseModule):
    """
    Salary/Income Module

    Models W2 or 1099 income with:
    - Base salary with annual raises
    - Federal and state tax withholding
    - FICA (Social Security) and Medicare
    - Pre-tax deductions (401k, HSA, etc.)
    - Bonus income

    Config Parameters:
        name: Display name
        income_type: 'w2' or '1099'
        annual_salary: Annual base salary
        pay_frequency: 'monthly', 'semi-monthly', 'bi-weekly', 'weekly'
        annual_raise_pct: Expected annual raise percentage
        federal_withholding_pct: Federal tax withholding percentage (estimated)
        state_withholding_pct: State tax withholding percentage
        pre_tax_401k_pct: Percentage of gross to contribute to 401k
        annual_bonus: Expected annual bonus (paid in December)
        start_month: Month when income starts (1-12, default 1)
    """

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.INCOME_SOURCE

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.INFLOW

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'Salary')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Income Name", "default": "Primary Salary"},
                "income_type": {
                    "type": "string",
                    "enum": ["w2", "1099"],
                    "title": "Income Type",
                    "default": "w2"
                },
                "annual_salary": {"type": "number", "title": "Annual Salary", "default": 100000},
                "pay_frequency": {
                    "type": "string",
                    "enum": ["monthly", "semi-monthly", "bi-weekly", "weekly"],
                    "title": "Pay Frequency",
                    "default": "monthly"
                },
                "annual_raise_pct": {"type": "number", "title": "Annual Raise %", "default": 3},
                "federal_withholding_pct": {
                    "type": "number",
                    "title": "Federal Withholding %",
                    "default": 22
                },
                "state_withholding_pct": {"type": "number", "title": "State Withholding %", "default": 5},
                "pre_tax_401k_pct": {"type": "number", "title": "401k Contribution %", "default": 0},
                "annual_bonus": {"type": "number", "title": "Annual Bonus", "default": 0},
                "start_month": {"type": "integer", "title": "Start Month", "default": 1, "minimum": 1, "maximum": 12}
            },
            "required": ["annual_salary"]
        }

    def _validate_config(self) -> None:
        if 'annual_salary' not in self.config:
            raise ValueError("annual_salary is required")
        if self.config['annual_salary'] < 0:
            raise ValueError("annual_salary must be non-negative")

        # Set defaults
        self.config.setdefault('name', 'Salary')
        self.config.setdefault('income_type', 'w2')
        self.config.setdefault('pay_frequency', 'monthly')
        self.config.setdefault('annual_raise_pct', 3)
        self.config.setdefault('federal_withholding_pct', 22)
        self.config.setdefault('state_withholding_pct', 5)
        self.config.setdefault('pre_tax_401k_pct', 0)
        self.config.setdefault('annual_bonus', 0)
        self.config.setdefault('start_month', 1)

    def initialize(self, start_date: str) -> ModuleState:
        state = SalaryState()
        state.balance = 0
        self._state = state
        self._simulation_start_year = int(start_date.split('-')[0]) if start_date else 2024
        return state

    def _get_monthly_gross(self, month: int, year: int) -> float:
        """Calculate monthly gross salary with raises"""
        base_salary = self.config['annual_salary']
        raise_pct = self.config['annual_raise_pct'] / 100.0

        # Calculate years since simulation start
        years = year - self._simulation_start_year
        adjusted_salary = base_salary * ((1 + raise_pct) ** years)

        # Calculate monthly based on pay frequency
        frequency = self.config['pay_frequency']
        if frequency == 'monthly':
            return adjusted_salary / 12
        elif frequency == 'semi-monthly':
            return adjusted_salary / 24 * 2  # 2 paychecks per month
        elif frequency == 'bi-weekly':
            # Average of 26 paychecks per year, ~2.17 per month
            return adjusted_salary / 26 * 2.17
        else:  # weekly
            return adjusted_salary / 52 * 4.33

        return adjusted_salary / 12

    def _calculate_fica(self, gross: float, ytd_gross: float) -> float:
        """Calculate Social Security tax (6.2% up to wage base)"""
        # 2024 wage base is $168,600
        wage_base = 168600
        if ytd_gross >= wage_base:
            return 0
        taxable = min(gross, wage_base - ytd_gross)
        return taxable * 0.062

    def _calculate_medicare(self, gross: float, ytd_gross: float) -> float:
        """Calculate Medicare tax (1.45%, additional 0.9% over $200k)"""
        base_tax = gross * 0.0145
        # Additional Medicare tax for high earners
        threshold = 200000
        if ytd_gross + gross > threshold:
            additional_taxable = max(0, ytd_gross + gross - threshold) - max(0, ytd_gross - threshold)
            base_tax += additional_taxable * 0.009
        return base_tax

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, SalaryState) else SalaryState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Check if income has started
        if month < self.config['start_month'] and year == self._simulation_start_year:
            result.new_state = state
            self._state = state
            return result

        # Reset YTD values at start of year
        if month == 1:
            state.ytd_gross = 0
            state.ytd_federal_withholding = 0
            state.ytd_state_withholding = 0
            state.ytd_fica = 0
            state.ytd_medicare = 0
            state.ytd_401k = 0

        # Calculate gross pay
        gross = self._get_monthly_gross(month, year)

        # Add bonus in December
        if month == 12:
            bonus = self.config['annual_bonus']
            raise_pct = self.config['annual_raise_pct'] / 100.0
            years = year - self._simulation_start_year
            gross += bonus * ((1 + raise_pct) ** years)

        # Calculate 401k contribution (pre-tax)
        contrib_401k = gross * (self.config['pre_tax_401k_pct'] / 100.0)
        # Check 401k annual limit ($23,000 for 2024)
        annual_limit_401k = 23000
        if state.ytd_401k + contrib_401k > annual_limit_401k:
            contrib_401k = max(0, annual_limit_401k - state.ytd_401k)

        taxable_gross = gross - contrib_401k

        # Calculate withholdings for W2
        if self.config['income_type'] == 'w2':
            federal_withholding = taxable_gross * (self.config['federal_withholding_pct'] / 100.0)
            state_withholding = taxable_gross * (self.config['state_withholding_pct'] / 100.0)
            fica = self._calculate_fica(gross, state.ytd_gross)
            medicare = self._calculate_medicare(gross, state.ytd_gross)

            net_pay = gross - contrib_401k - federal_withholding - state_withholding - fica - medicare

            # Update YTD
            state.ytd_federal_withholding += federal_withholding
            state.ytd_state_withholding += state_withholding
            state.ytd_fica += fica
            state.ytd_medicare += medicare

            tax_info.withholding = federal_withholding + state_withholding + fica + medicare
            tax_info.federal_withholding = federal_withholding
            tax_info.state_withholding = state_withholding
        else:
            # 1099 income - no withholding
            net_pay = gross - contrib_401k
            tax_info.withholding = 0

        state.ytd_gross += gross
        state.ytd_401k += contrib_401k

        # Tax info
        tax_info.taxable_income = taxable_gross
        tax_info.tax_deferred_income = contrib_401k

        # Update state
        # Pay not routed onward carries over instead of disappearing
        state.balance += net_pay
        state.monthly_contribution = net_pay

        result.amount_received = 0
        result.amount_sent = net_pay  # Money flows out to connected nodes
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, SalaryState) else SalaryState()
        return {
            'gross_income': state.ytd_gross,
            'federal_withholding': state.ytd_federal_withholding,
            'state_withholding': state.ytd_state_withholding,
            'fica': state.ytd_fica,
            'medicare': state.ytd_medicare,
            '401k_contributions': state.ytd_401k
        }
