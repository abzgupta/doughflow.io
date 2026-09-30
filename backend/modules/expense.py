"""
Expense Module

Handles various types of recurring and one-time expenses like
daycare, subscriptions, utilities, summer programs, etc.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class ExpenseState(ModuleState):
    """State for expense tracking"""
    ytd_spent: float = 0.0
    total_spent: float = 0.0
    months_active: int = 0


@register_module
class ExpenseModule(BaseModule):
    """
    Expense Module

    Models various types of expenses with:
    - Fixed monthly expenses (daycare, rent, subscriptions)
    - Annual expenses (summer camp, vacation)
    - Seasonal expenses (active only certain months)
    - Inflation/annual increase tracking
    - Tax deductible options (childcare, medical)

    Config Parameters:
        name: Expense name
        expense_type: 'fixed', 'variable', 'annual', 'seasonal'
        category: 'childcare', 'education', 'utilities', 'subscription',
                  'healthcare', 'transportation', 'food', 'entertainment', 'other'
        monthly_amount: Monthly expense amount (for fixed/variable)
        annual_amount: Annual expense amount (for annual type)
        annual_increase_pct: Expected annual increase percentage
        active_months: List of months when expense is active (1-12), empty = all months
        is_tax_deductible: Whether expense qualifies for tax deduction/credit
        tax_deduction_type: 'childcare_credit', 'medical', 'education', 'none'
        start_month: Month when expense starts (1-12)
        end_month: Month when expense ends (0 = never)
    """

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.EXPENSE

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.INFLOW  # Receives money (outflow from accounts)

    @property
    def display_name(self) -> str:
        return self.config.get('name', 'Expense')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "title": "Expense Name", "default": "Expense"},
                "expense_type": {
                    "type": "string",
                    "enum": ["fixed", "variable", "annual", "seasonal"],
                    "title": "Expense Type",
                    "default": "fixed"
                },
                "category": {
                    "type": "string",
                    "enum": ["childcare", "education", "utilities", "subscription",
                             "healthcare", "transportation", "food", "entertainment", "other"],
                    "title": "Category",
                    "default": "other"
                },
                "monthly_amount": {"type": "number", "title": "Monthly Amount", "default": 0},
                "annual_amount": {"type": "number", "title": "Annual Amount", "default": 0},
                "annual_increase_pct": {"type": "number", "title": "Annual Increase %", "default": 3},
                "active_months": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1, "maximum": 12},
                    "title": "Active Months (1-12)",
                    "default": []
                },
                "is_tax_deductible": {"type": "boolean", "title": "Tax Deductible", "default": False},
                "tax_deduction_type": {
                    "type": "string",
                    "enum": ["childcare_credit", "medical", "education", "none"],
                    "title": "Tax Deduction Type",
                    "default": "none"
                }
            },
            "required": ["name"]
        }

    def _validate_config(self) -> None:
        self.config.setdefault('name', 'Expense')
        self.config.setdefault('expense_type', 'fixed')
        self.config.setdefault('category', 'other')
        self.config.setdefault('monthly_amount', 0)
        self.config.setdefault('annual_amount', 0)
        self.config.setdefault('annual_increase_pct', 3)
        self.config.setdefault('active_months', [])
        self.config.setdefault('is_tax_deductible', False)
        self.config.setdefault('tax_deduction_type', 'none')

        # Auto-detect tax deduction type based on category
        if self.config['is_tax_deductible'] and self.config['tax_deduction_type'] == 'none':
            category = self.config['category']
            if category == 'childcare':
                self.config['tax_deduction_type'] = 'childcare_credit'
            elif category == 'healthcare':
                self.config['tax_deduction_type'] = 'medical'
            elif category == 'education':
                self.config['tax_deduction_type'] = 'education'

    def initialize(self, start_date: str) -> ModuleState:
        state = ExpenseState()
        state.balance = 0
        state.ytd_spent = 0
        state.total_spent = 0
        state.months_active = 0
        self._state = state
        self._simulation_start_year = int(start_date.split('-')[0]) if start_date else 2024
        return state

    def _get_expense_amount(self, month: int, year: int) -> float:
        """Calculate expense amount for the given month with inflation."""
        expense_type = self.config['expense_type']
        annual_increase = self.config['annual_increase_pct'] / 100.0
        years = year - self._simulation_start_year

        # Apply inflation
        inflation_multiplier = (1 + annual_increase) ** years

        if expense_type == 'fixed' or expense_type == 'variable':
            return self.config['monthly_amount'] * inflation_multiplier
        elif expense_type == 'annual':
            # Annual expense paid in a specific month (default January)
            if month == 1:
                return self.config['annual_amount'] * inflation_multiplier
            return 0
        elif expense_type == 'seasonal':
            # Only active during specified months
            active_months = self.config['active_months']
            if not active_months or month in active_months:
                return self.config['monthly_amount'] * inflation_multiplier
            return 0

        return 0

    def _is_active_for_month(self, month: int, year: int) -> bool:
        """Check if expense is active for the given calendar month.

        This only handles seasonal active_months logic.
        The overall start/end date scheduling is handled by the base class
        is_active_for_date method at the graph executor level.
        """
        # Check active months for seasonal expenses (e.g., summer camp only in June-August)
        active_months = self.config.get('active_months', [])
        if active_months and month not in active_months:
            return False

        return True

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        state = self._state if isinstance(self._state, ExpenseState) else ExpenseState()
        result = FlowResult()
        tax_info = TaxInfo()

        # Reset YTD at start of year
        if month == 1:
            state.ytd_spent = 0

        state.months_active += 1

        # Check if expense is active for this calendar month (seasonal check)
        # Note: Overall scheduling (start_year/end_year) is handled by graph executor
        if not self._is_active_for_month(month, year):
            result.new_state = state
            self._state = state
            return result

        # Calculate expense amount
        expense_amount = self._get_expense_amount(month, year)

        # Process payment received
        payment = sum(inflows.values())
        actual_expense = min(payment, expense_amount) if payment > 0 else expense_amount

        # Track spending
        state.ytd_spent += actual_expense
        state.total_spent += actual_expense
        state.balance = -state.total_spent  # Negative to show as expense

        # Tax deductions/credits
        if self.config['is_tax_deductible'] and actual_expense > 0:
            deduction_type = self.config['tax_deduction_type']

            if deduction_type == 'childcare_credit':
                # Child and Dependent Care Credit (up to $3,000 per child, $6,000 max)
                # Credit is 20-35% of expenses based on income
                tax_info.credits['childcare'] = actual_expense
            elif deduction_type == 'medical':
                # Medical expenses deductible if > 7.5% of AGI
                tax_info.deductions['medical'] = actual_expense
            elif deduction_type == 'education':
                # Education credits (American Opportunity, Lifetime Learning)
                tax_info.credits['education'] = actual_expense

        result.amount_received = payment
        result.amount_sent = 0
        result.new_state = state
        result.tax_info = tax_info

        if actual_expense > 0:
            result.events.append(f"Expense: ${actual_expense:,.2f} for {self.config['name']}")

        self._state = state
        return result

    def net_worth_contribution(self) -> float:
        """
        Expenses don't count toward net worth: the balance is a running total
        of money already paid out of other accounts, so counting it would
        subtract twice.
        """
        return 0.0

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        state = self._state if isinstance(self._state, ExpenseState) else ExpenseState()
        return {
            'total_spent_ytd': state.ytd_spent,
            'total_spent_lifetime': state.total_spent,
            'category': self.config['category'],
            'is_tax_deductible': self.config['is_tax_deductible'],
            'tax_deduction_type': self.config['tax_deduction_type']
        }
