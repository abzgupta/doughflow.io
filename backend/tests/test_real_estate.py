"""Tests for the real estate module's monthly cash flow and sale."""

from modules.real_estate import RealEstateModule


def make_property(**overrides):
    """All-cash rental with no loan, so cash flow is easy to reason about"""
    config = {
        'property_name': 'Test Rental',
        'purchase_price': 200000,
        'closing_cost': 0,
        'loan_obj': {'down_payment_pct': 100, 'interest_rate_pct': 7, 'loan_term': 30},
        'income_obj': {
            'monthly_rent': 2000,
            'annual_rent_increase': 0,
            'other_monthly_income': 0,
            'vacancy_rate_pct': 0,
            'management_fee': 0,
        },
        'holding_length': 120,
        'value_appreciation_per_year_pct': 0,
    }
    config.update(overrides)
    module = RealEstateModule('rental', config)
    module.initialize('2026-01')
    return module


def run_month(module):
    return module.process_month(1, 2026, {}, 0, {})


def monthly_cash_flow(module):
    before = module.get_state().balance
    run_month(module)
    return module.get_state().balance - before


def test_vacancy_reduces_rent():
    module = make_property(income_obj={
        'monthly_rent': 2000, 'annual_rent_increase': 0, 'other_monthly_income': 0,
        'vacancy_rate_pct': 50, 'management_fee': 0,
    })
    assert monthly_cash_flow(module) == 1000


def test_management_fee_charged_once():
    module = make_property(income_obj={
        'monthly_rent': 2000, 'annual_rent_increase': 0, 'other_monthly_income': 0,
        'vacancy_rate_pct': 0, 'management_fee': 10,
    })
    assert monthly_cash_flow(module) == 1800


def test_annual_expenses_spread_across_months():
    module = make_property(annual_property_tax=1200, annual_property_tax_increase_pct=0,
                           annual_total_insurance=600, annual_total_insurance_increase_pct=0)
    flows = [monthly_cash_flow(module) for _ in range(13)]
    # $1,800/year of costs = $150/month, every month including a new year
    assert all(abs(f - 1850) < 1e-9 for f in flows)


def test_property_sells_only_once():
    module = make_property(holding_length=12, cost_to_sell_pct=0)
    events = []
    for _ in range(15):
        events.extend(run_month(module).events)
    balance_at_sale = module.get_state().balance

    assert sum('Property sold' in e for e in events) == 1
    assert module.get_state().is_sold
    # Nothing changes after the sale
    run_month(module)
    assert module.get_state().balance == balance_at_sale
