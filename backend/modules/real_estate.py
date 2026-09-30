"""
Real Estate Investment Module

Migrated from financial_module.py - preserves all original calculation logic
for rental property income, expenses, appreciation, and selling.
"""

import numpy as np
import pandas as pd
import copy
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .base_module import (
    BaseModule, ModuleType, FlowDirection, ModuleState, FlowResult, TaxInfo,
    register_module
)


@dataclass
class RealEstateState(ModuleState):
    """Extended state for real estate properties"""
    purchase_price: float = 0.0
    current_value: float = 0.0
    remaining_loan: float = 0.0
    cumulative_rent_income: float = 0.0
    cumulative_expenses: float = 0.0
    months_owned: int = 0
    is_sold: bool = False
    # Annual tracking for taxes
    annual_rental_income: float = 0.0
    annual_mortgage_interest: float = 0.0
    annual_property_tax: float = 0.0
    annual_depreciation: float = 0.0


@register_module
class RealEstateModule(BaseModule):
    """
    Real Estate Investment Module

    Models rental properties with:
    - Purchase with down payment and closing costs
    - Mortgage amortization (interest/principal breakdown)
    - Rental income with vacancy and management fees
    - Annual expenses (taxes, insurance, HOA, maintenance)
    - Property appreciation
    - Selling with costs

    Config Parameters:
        property_name: Name of the property
        purchase_price: Purchase price in dollars
        loan_obj: {
            down_payment_pct: Down payment percentage (0-100)
            interest_rate_pct: Annual interest rate percentage
            loan_term: Loan term in years
        }
        closing_cost: Closing costs in dollars
        repairs_obj: {
            repair_cost: Initial repair costs
            value_after_repair: Property value after repairs
        }
        income_obj: {
            monthly_rent: Monthly rent amount
            annual_rent_increase: Annual rent increase percentage
            other_monthly_income: Other monthly income (laundry, parking, etc.)
            other_monthly_income_increase: Annual increase for other income
            vacancy_rate_pct: Expected vacancy rate percentage
            management_fee: Management fee as percentage of rent
        }
        annual_property_tax: Annual property tax
        annual_property_tax_increase_pct: Annual property tax increase %
        annual_total_insurance: Annual insurance cost
        annual_total_insurance_increase_pct: Annual insurance increase %
        annual_hoa: Annual HOA fees
        annual_hoa_increase_pct: Annual HOA increase %
        annual_maintenance: Annual maintenance cost
        annual_maintenance_increase_pct: Annual maintenance increase %
        annual_other_costs: Other annual costs
        annual_other_costs_increase_pct: Other costs increase %
        holding_length: Expected holding period in months
        value_appreciation_per_year_pct: Annual appreciation %
        cost_to_sell_pct: Selling costs as % of sale price
        no_rent_months: List of [start, end] periods with no rent
    """

    @property
    def module_type(self) -> ModuleType:
        return ModuleType.INVESTMENT

    @property
    def flow_direction(self) -> FlowDirection:
        return FlowDirection.BOTH

    @property
    def display_name(self) -> str:
        return self.config.get('property_name', 'Real Estate')

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "property_name": {"type": "string", "title": "Property Name"},
                "purchase_price": {"type": "number", "title": "Purchase Price", "default": 220000},
                "loan_obj": {
                    "type": "object",
                    "title": "Loan Details",
                    "properties": {
                        "down_payment_pct": {"type": "number", "title": "Down Payment %", "default": 20},
                        "interest_rate_pct": {"type": "number", "title": "Interest Rate %", "default": 7.0},
                        "loan_term": {"type": "number", "title": "Loan Term (years)", "default": 30}
                    }
                },
                "closing_cost": {"type": "number", "title": "Closing Cost", "default": 5000},
                "repairs_obj": {
                    "type": "object",
                    "title": "Repairs",
                    "properties": {
                        "repair_cost": {"type": "number", "title": "Repair Cost", "default": 0},
                        "value_after_repair": {"type": "number", "title": "Value After Repair", "default": 0}
                    }
                },
                "income_obj": {
                    "type": "object",
                    "title": "Income",
                    "properties": {
                        "monthly_rent": {"type": "number", "title": "Monthly Rent", "default": 1800},
                        "annual_rent_increase": {"type": "number", "title": "Annual Rent Increase %", "default": 3},
                        "other_monthly_income": {"type": "number", "title": "Other Monthly Income", "default": 0},
                        "other_monthly_income_increase": {"type": "number", "title": "Other Income Increase %", "default": 0},
                        "vacancy_rate_pct": {"type": "number", "title": "Vacancy Rate %", "default": 5},
                        "management_fee": {"type": "number", "title": "Management Fee %", "default": 8}
                    }
                },
                "annual_property_tax": {"type": "number", "title": "Annual Property Tax", "default": 2400},
                "annual_property_tax_increase_pct": {"type": "number", "default": 2},
                "annual_total_insurance": {"type": "number", "title": "Annual Insurance", "default": 1200},
                "annual_total_insurance_increase_pct": {"type": "number", "default": 3},
                "annual_hoa": {"type": "number", "title": "Annual HOA", "default": 0},
                "annual_hoa_increase_pct": {"type": "number", "default": 3},
                "annual_maintenance": {"type": "number", "title": "Annual Maintenance", "default": 2000},
                "annual_maintenance_increase_pct": {"type": "number", "default": 3},
                "annual_other_costs": {"type": "number", "title": "Other Annual Costs", "default": 0},
                "annual_other_costs_increase_pct": {"type": "number", "default": 3},
                "holding_length": {"type": "number", "title": "Holding Period (months)", "default": 60},
                "value_appreciation_per_year_pct": {"type": "number", "title": "Annual Appreciation %", "default": 3},
                "cost_to_sell_pct": {"type": "number", "title": "Cost to Sell %", "default": 6},
                "no_rent_months": {
                    "type": "array",
                    "title": "No Rent Periods",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "default": []
                }
            },
            "required": ["property_name", "purchase_price"]
        }

    def _validate_config(self) -> None:
        """Validate configuration"""
        if 'purchase_price' not in self.config:
            raise ValueError("purchase_price is required")
        if self.config['purchase_price'] <= 0:
            raise ValueError("purchase_price must be positive")

        # Set defaults for optional fields
        self.config.setdefault('loan_obj', {
            'down_payment_pct': 20,
            'interest_rate_pct': 7.0,
            'loan_term': 30
        })
        self.config.setdefault('closing_cost', 5000)
        self.config.setdefault('repairs_obj', {'repair_cost': 0, 'value_after_repair': 0})
        self.config.setdefault('income_obj', {
            'monthly_rent': 0,
            'annual_rent_increase': 3,
            'other_monthly_income': 0,
            'other_monthly_income_increase': 0,
            'vacancy_rate_pct': 5,
            'management_fee': 8
        })
        self.config.setdefault('holding_length', 60)
        self.config.setdefault('value_appreciation_per_year_pct', 3)
        self.config.setdefault('cost_to_sell_pct', 6)
        self.config.setdefault('no_rent_months', [])

        # Set expense defaults
        for exp in ['annual_property_tax', 'annual_total_insurance', 'annual_hoa',
                    'annual_maintenance', 'annual_other_costs']:
            self.config.setdefault(exp, 0)
            self.config.setdefault(f'{exp}_increase_pct', 3)

    def initialize(self, start_date: str) -> ModuleState:
        """Initialize real estate state at purchase"""
        state = RealEstateState()
        state.purchase_price = self.config['purchase_price']
        state.current_value = self._get_initial_value()
        state.remaining_loan = self._calculate_loan_amount()
        state.cost_basis = self._calculate_initial_costs()
        state.balance = -state.cost_basis  # Negative because it's money spent
        state.months_owned = 0
        self._state = state
        return state

    def process_month(
        self,
        month: int,
        year: int,
        inflows: Dict[str, float],
        available_for_outflow: float,
        user_profile: Dict[str, Any]
    ) -> FlowResult:
        """Process one month of real estate ownership"""
        state = self._state if isinstance(self._state, RealEstateState) else RealEstateState()

        # Once sold, the property has no more income, costs, or sale proceeds
        if state.is_sold:
            result = FlowResult()
            result.new_state = state
            return result

        state.months_owned += 1
        current_month = state.months_owned

        result = FlowResult()
        tax_info = TaxInfo()

        # Check if this is a no-rent month
        is_no_rent = self._is_no_rent_month(current_month)

        # Calculate monthly rent income
        rent_income = 0.0
        other_income = 0.0
        management_fee = 0.0

        if not is_no_rent:
            vacancy_pct = self.config['income_obj'].get('vacancy_rate_pct', 0) / 100.0
            rent_income = self._get_monthly_rent(current_month) * (1 - vacancy_pct)
            management_fee_pct = self.config['income_obj']['management_fee'] / 100.0
            management_fee = rent_income * management_fee_pct
            rent_income -= management_fee
            other_income = self._get_other_income(current_month)

        # Calculate mortgage payment breakdown
        interest, principal = self._get_interest_principal(current_month, state.remaining_loan)
        state.remaining_loan = max(0, state.remaining_loan - principal)

        # Calculate monthly expenses (annual costs spread evenly across the year)
        expenses = self._get_monthly_expenses(current_month)

        # Update property value
        state.current_value = self._get_property_value(current_month)

        # Calculate cash flow for this month
        # (rent_income is already net of the management fee)
        total_income = rent_income + other_income
        total_expenses = expenses + interest + principal
        cash_flow = total_income - total_expenses

        # Update cumulative values
        state.cumulative_rent_income += total_income
        state.cumulative_expenses += total_expenses
        state.balance += cash_flow

        # Update annual tracking for taxes
        state.annual_rental_income += rent_income + other_income
        state.annual_mortgage_interest += interest
        if current_month == 1 or current_month % 12 == 1:
            state.annual_property_tax = self._get_annual_expense('annual_property_tax', current_month)

        # Depreciation (for tax purposes - 27.5 year schedule for residential)
        building_value = state.purchase_price * 0.8  # Assume 80% is building, 20% land
        monthly_depreciation = building_value / (27.5 * 12)
        state.annual_depreciation += monthly_depreciation

        # Tax info
        tax_info.taxable_income = rent_income + other_income
        tax_info.deductions = {
            'mortgage_interest': interest,
            'property_tax': self._get_annual_expense('annual_property_tax', current_month) / 12,
            'depreciation': monthly_depreciation,
            'operating_expenses': expenses - self._get_annual_expense('annual_property_tax', current_month) / 12
        }

        # Check if property is being sold this month
        if current_month >= self.config['holding_length']:
            sell_price = state.current_value
            selling_costs = sell_price * (self.config['cost_to_sell_pct'] / 100.0)
            net_proceeds = sell_price - state.remaining_loan - selling_costs
            cash_flow += net_proceeds
            state.balance += net_proceeds
            state.is_sold = True

            # Calculate capital gains
            total_depreciation = monthly_depreciation * current_month
            adjusted_basis = state.cost_basis - total_depreciation
            capital_gain = sell_price - selling_costs - adjusted_basis

            if capital_gain > 0:
                # Depreciation recapture taxed as ordinary income (up to 25%)
                tax_info.taxable_income += min(capital_gain, total_depreciation)
                remaining_gain = max(0, capital_gain - total_depreciation)
                # Long-term capital gains (assuming held > 1 year)
                if current_month > 12:
                    tax_info.capital_gains_long = remaining_gain
                else:
                    tax_info.capital_gains_short = remaining_gain

            result.events.append(f"Property sold for ${sell_price:,.2f}")

        # Set result
        result.amount_received = total_income + sum(inflows.values())
        result.amount_sent = total_expenses
        result.new_state = state
        result.tax_info = tax_info

        self._state = state
        return result

    def get_annual_summary(self, year: int) -> Dict[str, Any]:
        """Get annual summary for tax reporting"""
        state = self._state if isinstance(self._state, RealEstateState) else RealEstateState()
        return {
            'rental_income': state.annual_rental_income,
            'mortgage_interest': state.annual_mortgage_interest,
            'property_tax': state.annual_property_tax,
            'depreciation': state.annual_depreciation,
            'property_value': state.current_value,
            'remaining_loan': state.remaining_loan,
            'cumulative_cash_flow': state.balance
        }

    # ============= Preserved calculation methods from financial_module.py =============

    def _calculate_down_payment(self) -> float:
        """Calculate down payment amount"""
        purchase_price = self.config['purchase_price']
        down_payment_pct = self.config['loan_obj']['down_payment_pct'] / 100.0
        return purchase_price * down_payment_pct

    def _calculate_initial_costs(self) -> float:
        """Calculate initial costs (down payment + closing + repairs)"""
        down_payment = self._calculate_down_payment()
        repair_costs = self.config['repairs_obj'].get('repair_cost', 0)
        closing_costs = self.config['closing_cost']
        return down_payment + repair_costs + closing_costs

    def _calculate_loan_amount(self) -> float:
        """Calculate loan amount"""
        purchase_price = self.config['purchase_price']
        down_payment = self._calculate_down_payment()
        return purchase_price - down_payment

    def _calculate_monthly_payment(self) -> float:
        """Calculate monthly mortgage payment using amortization formula"""
        loan_amount = self._calculate_loan_amount()
        rate = self.config['loan_obj']['interest_rate_pct'] / 100
        loan_term = self.config['loan_obj']['loan_term']

        if loan_amount <= 0 or rate <= 0:
            return 0

        c = rate / 12.0  # Monthly interest rate
        n = loan_term * 12  # Total number of payments

        # Standard amortization formula: L * (c * (1 + c)^n) / ((1 + c)^n - 1)
        monthly_payment = loan_amount * (c * (1 + c) ** n) / ((1 + c) ** n - 1)
        return monthly_payment

    def _get_interest_principal(self, month: int, remaining_loan: float) -> tuple:
        """Calculate interest and principal for a given month"""
        loan_term_months = self.config['loan_obj']['loan_term'] * 12

        if month > loan_term_months or remaining_loan <= 0:
            return 0.0, 0.0

        rate = self.config['loan_obj']['interest_rate_pct'] / 100
        monthly_payment = self._calculate_monthly_payment()

        interest = (remaining_loan * rate) / 12.0
        principal = monthly_payment - interest

        return interest, principal

    def _get_initial_value(self) -> float:
        """Get initial property value (considering repairs)"""
        purchase_price = self.config['purchase_price']
        value_after_repair = self.config['repairs_obj'].get('value_after_repair', 0)
        return max(purchase_price, value_after_repair)

    def _get_property_value(self, month: int) -> float:
        """Calculate property value at given month"""
        base_value = self._get_initial_value()
        value_increase = self.config['value_appreciation_per_year_pct'] / 100.0
        years = month // 12
        return base_value * ((1 + value_increase) ** years)

    def _is_no_rent_month(self, month: int) -> bool:
        """Check if this is a no-rent month"""
        no_rent_periods = self.config.get('no_rent_months', [])
        for period in no_rent_periods:
            if len(period) >= 2:
                start, end = period[0], period[1]
                if start <= month <= end:
                    return True
        return False

    def _get_monthly_rent(self, month: int) -> float:
        """Calculate monthly rent for given month (with annual increases)"""
        base_rent = self.config['income_obj']['monthly_rent']
        annual_increase = self.config['income_obj']['annual_rent_increase'] / 100.0

        # Rent increases at start of each year
        years = (month - 1) // 12
        return base_rent * ((1 + annual_increase) ** years)

    def _get_other_income(self, month: int) -> float:
        """Calculate other monthly income for given month"""
        base_income = self.config['income_obj']['other_monthly_income']
        annual_increase = self.config['income_obj'].get('other_monthly_income_increase', 0) / 100.0

        years = (month - 1) // 12
        return base_income * ((1 + annual_increase) ** years)

    def _get_annual_expense(self, expense_type: str, month: int) -> float:
        """Calculate annual expense for given month (with annual increases)"""
        base_amount = self.config.get(expense_type, 0)
        increase_pct = self.config.get(f'{expense_type}_increase_pct', 0) / 100.0

        years = (month - 1) // 12
        return base_amount * ((1 + increase_pct) ** years)

    def _get_monthly_expenses(self, month: int) -> float:
        """Calculate total monthly expenses (one twelfth of each annual expense)"""
        expenses = 0.0
        for exp_type in ['annual_property_tax', 'annual_total_insurance', 'annual_hoa',
                         'annual_maintenance', 'annual_other_costs']:
            expenses += self._get_annual_expense(exp_type, month) / 12

        return expenses


# ============= Legacy compatibility functions =============

def calculate_rental_income(rental_obj: Dict, month_offset: int = 0) -> pd.DataFrame:
    """
    Legacy function for backward compatibility.
    Wraps the RealEstateModule to produce the same DataFrame output.
    """
    module = RealEstateModule('legacy', rental_obj)
    module.initialize('')

    rows = {}
    holding_length = rental_obj['holding_length']

    for month in range(1, holding_length + 1):
        result = module.process_month(month, 2024, {}, 0, {})
        state = result.new_state

        rows[month] = {
            'month_number': month + month_offset,
            'purchase_price': rental_obj['purchase_price'],
            'initial_costs': module._calculate_initial_costs() if month == 1 else 0,
            'monthly_rent': module._get_monthly_rent(month),
            'monthly_rent_income': module._get_monthly_rent(month) * (1 - rental_obj['income_obj']['management_fee'] / 100) if not module._is_no_rent_month(month) else 0,
            'other_income': module._get_other_income(month) if not module._is_no_rent_month(month) else 0,
            'management_fee': module._get_monthly_rent(month) * (rental_obj['income_obj']['management_fee'] / 100) if not module._is_no_rent_month(month) else 0,
            'is_occupied': 0 if module._is_no_rent_month(month) else 1,
            'value': state.current_value if hasattr(state, 'current_value') else module._get_property_value(month),
        }

        # Add annual expenses
        for exp in ['annual_hoa', 'annual_maintenance', 'annual_other_costs',
                    'annual_property_tax', 'annual_total_insurance']:
            rows[month][exp] = module._get_annual_expense(exp, month) if month % 12 == 1 else 0

    # Calculate interest/principal breakdown
    remaining_loan = module._calculate_loan_amount()
    for month in range(1, holding_length + 1):
        interest, principal = module._get_interest_principal(month, remaining_loan)
        remaining_loan = max(0, remaining_loan - principal)
        rows[month]['interest'] = interest
        rows[month]['principal'] = principal
        rows[month]['remaining_loan_amount'] = remaining_loan

    rental_df = pd.DataFrame(list(rows.values()))
    rental_df['is_sold'] = rental_df['month_number'] == (holding_length + month_offset)
    rental_df['holding_length'] = holding_length
    rental_df['cost_to_sell_pct'] = rental_obj['cost_to_sell_pct']

    column_order = ['month_number', 'purchase_price', 'initial_costs', 'monthly_rent',
                    'monthly_rent_income', 'other_income', 'management_fee', 'is_occupied',
                    'annual_hoa', 'annual_maintenance', 'annual_other_costs',
                    'annual_property_tax', 'annual_total_insurance',
                    'interest', 'principal', 'remaining_loan_amount', 'value',
                    'is_sold', 'holding_length', 'cost_to_sell_pct']

    return rental_df[column_order]


def get_financial_table(property_list: List[Dict]) -> pd.DataFrame:
    """Legacy function for backward compatibility"""
    expenses_list = ['annual_property_tax', 'annual_total_insurance', 'annual_hoa',
                     'annual_other_costs', 'annual_maintenance', 'initial_costs', 'management_fee']

    rental_df_list = []
    for i, purchase_obj in enumerate(property_list):
        month_offset = purchase_obj.get('month_offset', 0)
        current_df = calculate_rental_income(purchase_obj, month_offset)
        current_df['property_number'] = i + 1
        current_df['property_name'] = purchase_obj.get('property_name', f'Property {i+1}')
        current_df = current_df.sort_values(by=['month_number', 'property_number'])
        current_df['mortgage_due'] = current_df['interest'] + current_df['principal']
        current_df['total_income_for_month'] = current_df['monthly_rent_income'] + current_df['other_income']
        current_df['total_cost_for_month'] = sum([current_df[x] for x in expenses_list])
        current_df['selling_costs'] = current_df['value'] * current_df['cost_to_sell_pct'] / 100.0
        current_df['if_sold_today'] = current_df['value'] - current_df['remaining_loan_amount'] - current_df['selling_costs']
        current_df['cash_flow'] = current_df['total_income_for_month'] - (current_df['total_cost_for_month'] + current_df['mortgage_due'])
        current_df.loc[current_df['is_sold'], 'cash_flow'] = current_df.loc[current_df['is_sold'], 'if_sold_today']
        current_df['cumulative_cash_for_property'] = current_df.groupby('property_number')['cash_flow'].cumsum()
        current_df['cumulative_expenses'] = current_df['total_cost_for_month'].cumsum()
        current_df['cumulative_cash_for_property_if_sold_today'] = current_df['cumulative_cash_for_property'] + current_df['if_sold_today']
        current_df['multiplier'] = float("inf")
        current_df['adj_hypothetical_cost_to_purchase_next_property'] = float("inf")
        current_df['cash_on_cash_return'] = current_df['cumulative_cash_for_property'] / current_df['cumulative_expenses']
        current_df['cash_on_cash_return_if_sold_today'] = (current_df['cumulative_cash_for_property'] + current_df['if_sold_today']) / current_df['cumulative_expenses']
        rental_df_list.append(current_df)

    rental_df = pd.concat(rental_df_list)
    rental_df['hypothetical_cost_to_purchase_next_property'] = float('inf')

    overall_df = rental_df.groupby('month_number').sum().reset_index()
    overall_df['property_number'] = len(rental_df_list) + 1
    overall_df['multiplier'] = 1
    overall_df['adj_hypothetical_cost_to_purchase_next_property'] = 1
    overall_df['property_name'] = 'Overall'

    final_df = pd.concat([rental_df, overall_df])
    final_df = final_df.sort_values(by=['month_number', 'property_number'])

    return final_df


def get_financial_table_summarized(property_list: List[Dict]) -> pd.DataFrame:
    """Legacy function for backward compatibility"""
    return get_financial_table(property_list)
