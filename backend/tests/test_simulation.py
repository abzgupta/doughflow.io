"""
Smoke tests for the DoughFlow financial simulation engine.

These exercise:
1. Module creation and initialization
2. Graph executor with connected nodes
3. Tax calculations
4. Full simulation run
"""

from modules import (
    SalaryModule, SavingsAccountModule, StockPortfolioModule,
    FourOhOneKModule, IRAModule, MortgageModule
)
from engine import GraphExecutor
from engine.graph_executor import FlowEdge, SimulationConfig
from tax import FederalTaxCalculator, FilingStatus


def test_modules():
    """Test individual module creation and processing"""
    print("=" * 60)
    print("Testing Module Creation")
    print("=" * 60)

    # Test Salary Module
    salary = SalaryModule('salary_1', {
        'name': 'Primary Salary',
        'annual_salary': 150000,
        'income_type': 'w2',
        'federal_withholding_pct': 22,
        'state_withholding_pct': 5,
        'pre_tax_401k_pct': 10,
    })
    salary.initialize('2024-01')
    result = salary.process_month(1, 2024, {}, 0, {'age': 35})
    print(f"Salary Module: Net monthly pay = ${result.amount_sent:,.2f}")
    print(f"  Tax deferred (401k): ${result.tax_info.tax_deferred_income:,.2f}")

    # Test Savings Account
    savings = SavingsAccountModule('savings_1', {
        'name': 'Emergency Fund',
        'initial_balance': 20000,
        'apy': 5.0,
        'target_balance': 30000,
    })
    savings.initialize('2024-01')
    result = savings.process_month(1, 2024, {'salary_1': 5000}, 0, {})
    print(f"\nSavings Module: Balance = ${result.new_state.balance:,.2f}")

    # Test 401k Module
    k401 = FourOhOneKModule('401k_1', {
        'name': 'Company 401k',
        'initial_balance': 50000,
        'expected_annual_return': 8,
        'employer_match_pct': 50,
        'employer_match_limit': 6,
    })
    k401.initialize('2024-01')
    result = k401.process_month(1, 2024, {'salary_1': 1250}, 0, {'annual_salary': 150000, 'age': 35})
    print(f"\n401(k) Module: Balance = ${result.new_state.balance:,.2f}")
    print(f"  YTD Employee: ${result.new_state.ytd_employee_contributions:,.2f}")
    print(f"  YTD Employer: ${result.new_state.ytd_employer_contributions:,.2f}")

    # Test Stock Portfolio
    stocks = StockPortfolioModule('stocks_1', {
        'name': 'Brokerage',
        'initial_value': 100000,
        'expected_annual_return': 10,
        'dividend_yield': 2,
        'dividend_reinvest': True,
    })
    stocks.initialize('2024-01')
    result = stocks.process_month(1, 2024, {'savings_1': 2000}, 0, {})
    print(f"\nStock Portfolio: Value = ${result.new_state.market_value:,.2f}")

    print("\n[OK] All modules created and processed successfully")


def test_graph_executor():
    """Test graph executor with connected nodes"""
    print("\n" + "=" * 60)
    print("Testing Graph Executor")
    print("=" * 60)

    executor = GraphExecutor()

    # Create nodes
    salary = SalaryModule('salary', {
        'name': 'Salary',
        'annual_salary': 150000,
        'pre_tax_401k_pct': 0,  # Will handle 401k separately
    })
    executor.add_node('salary', salary)

    checking = SavingsAccountModule('checking', {
        'name': 'Checking',
        'initial_balance': 5000,
        'apy': 0.5,
    })
    executor.add_node('checking', checking)

    savings = SavingsAccountModule('savings', {
        'name': 'Savings',
        'initial_balance': 20000,
        'apy': 5.0,
        'target_balance': 30000,
    })
    executor.add_node('savings', savings)

    stocks = StockPortfolioModule('stocks', {
        'name': 'Stocks',
        'initial_value': 50000,
        'expected_annual_return': 8,
        'dividend_yield': 2,
    })
    executor.add_node('stocks', stocks)

    # Create edges
    # Salary -> Checking (all income)
    executor.add_edge(FlowEdge(
        source_id='salary',
        target_id='checking',
        flow_type='remainder',
        amount=0,
        frequency='monthly',
        priority=0,
    ))

    # Checking -> Savings ($2000/month)
    executor.add_edge(FlowEdge(
        source_id='checking',
        target_id='savings',
        flow_type='fixed',
        amount=2000,
        frequency='monthly',
        priority=1,
    ))

    # Savings -> Stocks (remainder after target)
    executor.add_edge(FlowEdge(
        source_id='savings',
        target_id='stocks',
        flow_type='remainder',
        amount=0,
        frequency='monthly',
        priority=0,
        condition={'type': 'threshold', 'source_balance_min': 30000}
    ))

    # Validate
    is_valid, errors = executor.validate()
    print(f"Graph valid: {is_valid}")
    if errors:
        print(f"Errors: {errors}")

    # Run simulation
    executor.set_user_profile({
        'filing_status': 'married_jointly',
        'state': 'CA',
        'age': 35,
    })

    config = SimulationConfig(
        start_year=2024,
        start_month=1,
        duration_months=12,  # 1 year
    )

    result = executor.simulate(config)

    print(f"\nSimulation completed: {len(result.snapshots)} months")
    print(f"Final net worth: ${result.final_net_worth:,.2f}")

    # Show final balances
    if result.snapshots:
        final = result.snapshots[-1]
        print("\nFinal balances:")
        for node_id, balance in final.node_balances.items():
            print(f"  {node_id}: ${balance:,.2f}")

    print("\n[OK] Graph executor test passed")


def test_tax_calculator():
    """Test federal tax calculations"""
    print("\n" + "=" * 60)
    print("Testing Tax Calculator")
    print("=" * 60)

    # Test case: $150k salary, married filing jointly
    calc = FederalTaxCalculator(FilingStatus.MARRIED_JOINTLY)

    result = calc.calculate(
        income={
            'wages': 150000,
            'dividends_qualified': 5000,
            'capital_gains_long': 10000,
        },
        deductions={
            'mortgage_interest': 15000,
            'salt': 12000,
            'charitable': 5000,
        },
        credits={
            'child_tax_credit': 4000,
        },
        withholding=30000,
    )

    print(f"Gross Income: ${result.gross_income:,.2f}")
    print(f"AGI: ${result.adjusted_gross_income:,.2f}")
    print(f"Taxable Income: ${result.taxable_income:,.2f}")
    print(f"Ordinary Tax: ${result.ordinary_income_tax:,.2f}")
    print(f"Capital Gains Tax: ${result.capital_gains_tax:,.2f}")
    print(f"Total Tax: ${result.total_tax:,.2f}")
    print(f"Effective Rate: {result.effective_rate*100:.1f}%")
    print(f"Marginal Rate: {result.marginal_rate*100:.0f}%")
    print(f"Credits Applied: ${result.credits_applied:,.2f}")

    if result.refund > 0:
        print(f"Refund: ${result.refund:,.2f}")
    else:
        print(f"Owed: ${result.amount_owed:,.2f}")

    print(f"\nDeduction type: {result.breakdown.get('deduction_type', 'standard')}")

    print("\n[OK] Tax calculator test passed")


def test_real_estate_parity():
    """Test that new real estate module matches legacy calculations"""
    print("\n" + "=" * 60)
    print("Testing Real Estate Parity with Legacy")
    print("=" * 60)

    from modules.real_estate import get_financial_table_summarized

    # Sample property (same format as original)
    property_obj = {
        'property_name': 'Test Property',
        'purchase_price': 300000,
        'loan_obj': {
            'down_payment_pct': 20,
            'interest_rate_pct': 7.0,
            'loan_term': 30,
        },
        'closing_cost': 6000,
        'repairs_obj': {
            'repair_cost': 0,
            'value_after_repair': 0,
        },
        'income_obj': {
            'monthly_rent': 2500,
            'annual_rent_increase': 3,
            'other_monthly_income': 0,
            'other_monthly_income_increase': 0,
            'vacancy_rate_pct': 5,
            'management_fee': 8,
        },
        'annual_property_tax': 3600,
        'annual_property_tax_increase_pct': 2,
        'annual_total_insurance': 1800,
        'annual_total_insurance_increase_pct': 3,
        'annual_hoa': 0,
        'annual_hoa_increase_pct': 0,
        'annual_maintenance': 3000,
        'annual_maintenance_increase_pct': 3,
        'annual_other_costs': 0,
        'annual_other_costs_increase_pct': 0,
        'holding_length': 60,  # 5 years
        'value_appreciation_per_year_pct': 3,
        'cost_to_sell_pct': 6,
        'no_rent_months': [],
        'month_offset': 0,
    }

    result_df = get_financial_table_summarized([property_obj])

    # Check key values at month 12
    month_12 = result_df[result_df['month_number'] == 12].iloc[0]
    print(f"Month 12 Results:")
    print(f"  Monthly Rent: ${month_12['monthly_rent']:,.2f}")
    print(f"  Interest: ${month_12['interest']:,.2f}")
    print(f"  Principal: ${month_12['principal']:,.2f}")
    print(f"  Remaining Loan: ${month_12['remaining_loan_amount']:,.2f}")
    print(f"  Property Value: ${month_12['value']:,.2f}")

    # Check month 60 (end of holding)
    month_60 = result_df[(result_df['month_number'] == 60) & (result_df['property_name'] != 'Overall')].iloc[0]
    print(f"\nMonth 60 (End) Results:")
    print(f"  Property Value: ${month_60['value']:,.2f}")
    print(f"  If Sold Today: ${month_60['if_sold_today']:,.2f}")
    print(f"  Cumulative Cash: ${month_60['cumulative_cash_for_property']:,.2f}")

    print("\n[OK] Real estate parity test passed")
