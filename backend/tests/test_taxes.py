"""
Yearly income tax settlement inside the simulation (#9).

Profiles use a no-income-tax state so the expected tax can be hand-checked
against FederalTaxCalculator alone.
"""

import pytest

from engine import GraphExecutor
from engine.graph_executor import FlowEdge, SimulationConfig
from modules import SalaryModule, SavingsAccountModule, FourOhOneKModule
from tax import FederalTaxCalculator, FilingStatus

PROFILE = {'filing_status': 'single', 'state': 'TX', 'age': 40}


def savings(node_id, balance=0):
    return SavingsAccountModule(node_id, {'name': node_id, 'initial_balance': balance, 'apy': 0})


def salary(annual=60000, federal_pct=5):
    return SalaryModule('salary', {
        'name': 'salary', 'annual_salary': annual, 'annual_raise_pct': 0,
        'federal_withholding_pct': federal_pct, 'state_withholding_pct': 0,
    })


def run(nodes, edges, months=12, profile=PROFILE, **config):
    executor = GraphExecutor()
    executor.set_user_profile(profile)
    for node_id, module in nodes.items():
        executor.add_node(node_id, module)
    for edge in edges:
        executor.add_edge(edge)
    result = executor.simulate(SimulationConfig(start_year=2026, duration_months=months, **config))
    assert not result.errors
    return result


def to_checking(source='salary'):
    return FlowEdge(source, 'checking', 'remainder', 0, 'monthly', 1)


def inflows(result, target):
    return sum(f['amount'] for s in result.snapshots for f in s.flows if f['target'] == target)


def federal_tax(**income):
    return FederalTaxCalculator(FilingStatus.SINGLE).calculate(income).total_tax


def settlements(result):
    return [s for s in result.snapshots if 'annual' in s.tax_info]


def test_salary_settles_once_in_december():
    result = run({'salary': salary(federal_pct=5), 'checking': savings('checking')}, [to_checking()])

    settled = settlements(result)
    assert [(s.year, s.month) for s in settled] == [(2026, 12)]
    annual = settled[0].tax_info['annual']

    expected_tax = federal_tax(wages=60000)
    withheld = 60000 * 0.05
    assert annual['federal_tax'] == pytest.approx(expected_tax)
    assert annual['state_tax'] == 0
    assert annual['withholding'] == pytest.approx(withheld)
    assert annual['amount_owed'] == pytest.approx(expected_tax - withheld, abs=0.01)
    assert annual['paid'] == pytest.approx(expected_tax - withheld, abs=0.01)
    assert annual['paid_from'] == 'checking'

    # Checking holds every paycheck minus what settlement took
    final = result.snapshots[-1]
    assert final.node_balances['checking'] == pytest.approx(inflows(result, 'checking') - annual['paid'])
    assert any(e.startswith('2026 taxes: owed') and 'from checking' in e for e in final.events)


def test_over_withholding_refunds_into_tax_account():
    result = run({'salary': salary(federal_pct=30), 'checking': savings('checking')}, [to_checking()])

    annual = settlements(result)[0].tax_info['annual']
    refund = 60000 * 0.30 - federal_tax(wages=60000)
    assert refund > 0
    assert annual['refund'] == pytest.approx(refund, abs=0.01)
    assert annual['refunded'] == pytest.approx(refund, abs=0.01)
    assert result.snapshots[-1].node_balances['checking'] == pytest.approx(
        inflows(result, 'checking') + refund, abs=0.01)


def test_early_401k_withdrawal_is_taxed_with_penalty():
    k401 = FourOhOneKModule('401k', {'name': '401k', 'initial_balance': 50000, 'expected_annual_return': 0})
    result = run(
        {'salary': salary(federal_pct=5), '401k': k401, 'checking': savings('checking')},
        [to_checking(), FlowEdge('401k', 'checking', 'fixed', 1000, 'monthly', 1)],
    )

    annual = settlements(result)[0].tax_info['annual']
    expected_tax = federal_tax(wages=60000, other_income=12000)
    assert annual['gross_income'] == pytest.approx(72000)
    assert annual['federal_tax'] == pytest.approx(expected_tax)
    assert annual['penalties'] == pytest.approx(1200)
    assert annual['total_tax'] == pytest.approx(expected_tax + 1200)
    assert annual['paid'] == pytest.approx(expected_tax + 1200 - 3000, abs=0.01)


def test_401k_withdrawal_after_59_and_a_half_has_no_penalty():
    k401 = FourOhOneKModule('401k', {'name': '401k', 'initial_balance': 50000, 'expected_annual_return': 0})
    result = run(
        {'401k': k401, 'checking': savings('checking', 10000)},
        [FlowEdge('401k', 'checking', 'fixed', 2000, 'monthly', 1)],
        profile={**PROFILE, 'age': 62},
    )

    annual = settlements(result)[0].tax_info['annual']
    assert annual['penalties'] == 0
    assert annual['federal_tax'] == pytest.approx(federal_tax(other_income=24000))


def test_partial_final_year_settles_at_end():
    result = run({'salary': salary(), 'checking': savings('checking')}, [to_checking()], months=15)

    settled = settlements(result)
    assert [(s.year, s.month) for s in settled] == [(2026, 12), (2027, 3)]
    last = settled[-1].tax_info['annual']
    assert last['year'] == 2027 and last['months'] == 3
    assert last['federal_tax'] == pytest.approx(federal_tax(wages=15000))


def test_configured_tax_payment_node():
    result = run(
        {'salary': salary(), 'checking': savings('checking'), 'reserve': savings('reserve', 20000)},
        [to_checking()],
        tax_payment_node='reserve',
    )

    annual = settlements(result)[0].tax_info['annual']
    assert annual['paid_from'] == 'reserve'
    assert result.snapshots[-1].node_balances['reserve'] == pytest.approx(20000 - annual['paid'])
    assert result.snapshots[-1].node_balances['checking'] == pytest.approx(inflows(result, 'checking'))


def test_unpaid_tax_is_reported_not_created():
    # Everything leaves checking before settlement, so it can't pay the bill
    result = run(
        {'salary': salary(), 'checking': savings('checking'), 'spent': savings('spent')},
        [to_checking(), FlowEdge('checking', 'spent', 'remainder', 0, 'monthly', 1)],
        tax_payment_node='checking',
    )

    final = result.snapshots[-1]
    annual = final.tax_info['annual']
    assert annual['paid'] == 0
    assert annual['unpaid'] == pytest.approx(annual['amount_owed'])
    assert final.node_balances['checking'] == pytest.approx(0)
    assert any("couldn't be paid" in e for e in final.events)


def test_no_tax_account_skips_payment():
    result = run({'salary': salary()}, [])

    final = result.snapshots[-1]
    assert final.tax_info['annual']['paid_from'] is None
    assert any('no savings or checking account' in e for e in final.events)


def test_withdrawal_inside_a_cycle_is_taxed_once():
    # 401(k) <-> checking is a cycle, which is resolved over several trial passes
    k401 = FourOhOneKModule('401k', {'name': '401k', 'initial_balance': 50000, 'expected_annual_return': 0})
    result = run(
        {'401k': k401, 'checking': savings('checking', 10000)},
        [
            FlowEdge('401k', 'checking', 'fixed', 1000, 'monthly', 1),
            FlowEdge('checking', '401k', 'fixed', 500, 'monthly', 1),
        ],
    )

    annual = settlements(result)[0].tax_info['annual']
    assert annual['penalties'] == pytest.approx(1200)
