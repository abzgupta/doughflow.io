"""Tests for the real estate module's monthly cash flow, sale, and equity."""

import pytest

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


def financed_property(**overrides):
    """20% down on a 30-year loan at 7%, with closing and repair costs"""
    config = {
        'closing_cost': 5000,
        'repairs_obj': {'repair_cost': 3000, 'value_after_repair': 0},
        'loan_obj': {'down_payment_pct': 20, 'interest_rate_pct': 7, 'loan_term': 30},
    }
    config.update(overrides)
    return make_property(**config)


def equity(module):
    return module.net_worth_contribution() - module.get_state().balance


def test_net_worth_at_purchase_is_only_closing_and_repairs():
    module = financed_property()
    # The cash side still shows everything paid at purchase
    assert module.get_state().balance == -(40000 + 5000 + 3000)
    # But the down payment becomes equity, so only closing and repairs are lost
    assert module.net_worth_contribution() == -(5000 + 3000)


def test_all_cash_purchase_does_not_change_net_worth():
    assert make_property().net_worth_contribution() == 0


def test_equity_grows_with_loan_paydown_and_appreciation():
    module = financed_property(value_appreciation_per_year_pct=3)
    assert equity(module) == 200000 - 160000

    for _ in range(12):
        run_month(module)
    state = module.get_state()

    assert state.remaining_loan < 160000
    assert state.current_value == pytest.approx(200000 * 1.03)
    assert equity(module) == pytest.approx(state.current_value - state.remaining_loan)
    # $6,000 of appreciation plus a year of principal paid down
    assert equity(module) > 40000 + 6000


def test_sale_does_not_double_count_equity():
    sold = financed_property(holding_length=12, cost_to_sell_pct=0)
    held = financed_property(holding_length=120, cost_to_sell_pct=0)
    for _ in range(12):
        run_month(sold)
        run_month(held)

    assert sold.get_state().is_sold
    assert equity(sold) == 0
    # Selling at value with no costs just turns equity into cash
    assert sold.net_worth_contribution() == pytest.approx(held.net_worth_contribution())
    assert sold.get_state().balance == pytest.approx(held.net_worth_contribution())

    # Nothing is counted again after the sale
    run_month(sold)
    assert equity(sold) == 0
