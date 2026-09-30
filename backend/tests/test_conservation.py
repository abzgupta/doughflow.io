"""
Money conservation: moving money between nodes must not create or destroy it.

With all growth/interest rates at 0, net worth changes only by income earned
minus money paid out to expenses.

The simulation settles income taxes at the end of each tax year (including the
partial final year), which legitimately moves money. These graphs are set up so
that settlement moves nothing: no state income tax, no early withdrawal
penalty, income under the standard deduction and no income tax withheld.
Tax settlement itself is covered in test_taxes.py.
"""

import pytest

from engine import GraphExecutor
from engine.graph_executor import FlowEdge, SimulationConfig
from modules import (
    SavingsAccountModule, StockPortfolioModule, FourOhOneKModule,
    DebtModule, ExpenseModule, SalaryModule,
)

MONTHS = 6
NO_TAX_PROFILE = {'filing_status': 'single', 'state': 'TX', 'age': 65}


def savings(node_id, balance):
    return SavingsAccountModule(node_id, {'name': node_id, 'initial_balance': balance, 'apy': 0})


def run(nodes, edges, months=MONTHS):
    executor = GraphExecutor()
    executor.set_user_profile(NO_TAX_PROFILE)
    for node_id, module in nodes.items():
        executor.add_node(node_id, module)
    for edge in edges:
        executor.add_edge(edge)
    result = executor.simulate(SimulationConfig(start_year=2026, duration_months=months))
    assert not result.errors
    return result


def fixed(source, target, amount, priority=1):
    return FlowEdge(source, target, 'fixed', amount, 'monthly', priority)


def test_transfer_moves_money_without_creating_it():
    result = run({'a': savings('a', 10000), 'b': savings('b', 0)}, [fixed('a', 'b', 1000)])

    for i, snap in enumerate(result.snapshots, start=1):
        assert snap.node_balances['a'] == pytest.approx(10000 - 1000 * i)
        assert snap.node_balances['b'] == pytest.approx(1000 * i)
        assert snap.net_worth == pytest.approx(10000)


def test_transfer_stops_when_source_is_empty():
    result = run({'a': savings('a', 2500), 'b': savings('b', 0)}, [fixed('a', 'b', 1000)])

    last = result.snapshots[-1]
    assert last.node_balances['a'] == pytest.approx(0)
    assert last.node_balances['b'] == pytest.approx(2500)


def test_stock_outflow_uses_cash_then_sells_shares():
    stocks = StockPortfolioModule('stocks', {
        'name': 'stocks', 'initial_value': 10000, 'initial_cash': 500,
        'expected_annual_return': 0, 'dividend_yield': 0, 'expense_ratio': 0,
    })
    result = run({'stocks': stocks, 'checking': savings('checking', 0)}, [fixed('stocks', 'checking', 1000)])

    last = result.snapshots[-1]
    assert last.node_balances['checking'] == pytest.approx(1000 * MONTHS)
    assert last.node_balances['stocks'] == pytest.approx(10500 - 1000 * MONTHS)
    assert last.net_worth == pytest.approx(10500)


def test_401k_outflow_reduces_401k():
    k401 = FourOhOneKModule('401k', {
        'name': '401k', 'initial_balance': 20000, 'expected_annual_return': 0,
    })
    result = run({'401k': k401, 'checking': savings('checking', 0)}, [fixed('401k', 'checking', 1000)])

    last = result.snapshots[-1]
    assert last.node_balances['401k'] == pytest.approx(20000 - 1000 * MONTHS)
    assert last.net_worth == pytest.approx(20000)


def test_debt_payment_leaves_net_worth_unchanged():
    loan = DebtModule('loan', {
        'name': 'loan', 'original_principal': 10000, 'current_balance': 10000,
        'interest_rate_pct': 0, 'minimum_payment': 0,
    })
    result = run({'checking': savings('checking', 5000), 'loan': loan}, [fixed('checking', 'loan', 500)])

    last = result.snapshots[-1]
    assert last.node_balances['checking'] == pytest.approx(5000 - 500 * MONTHS)
    assert last.node_balances['loan'] == pytest.approx(-(10000 - 500 * MONTHS))
    assert last.net_worth == pytest.approx(5000 - 10000)


def test_income_minus_expenses_equals_change_in_net_worth():
    # $12k of wages over the 6 months stays under the standard deduction
    salary = SalaryModule('salary', {
        'name': 'salary', 'annual_salary': 24000, 'annual_raise_pct': 0,
        'federal_withholding_pct': 0, 'state_withholding_pct': 0,
    })
    rent = ExpenseModule('rent', {'name': 'rent', 'monthly_amount': 1500, 'annual_increase_pct': 0})
    result = run(
        {'salary': salary, 'checking': savings('checking', 1000), 'rent': rent},
        [
            FlowEdge('salary', 'checking', 'remainder', 0, 'monthly', 1),
            fixed('checking', 'rent', 1500),
        ],
    )

    income = sum(f['amount'] for s in result.snapshots for f in s.flows if f['source'] == 'salary')
    spent = sum(f['amount'] for s in result.snapshots for f in s.flows if f['target'] == 'rent')
    assert income > 0 and spent == pytest.approx(1500 * MONTHS)
    assert result.snapshots[-1].tax_info['annual']['balance_due'] == pytest.approx(0)
    assert result.snapshots[-1].net_worth == pytest.approx(1000 + income - spent)


def test_unrouted_salary_carries_over():
    salary = SalaryModule('salary', {'name': 'salary', 'annual_salary': 60000, 'annual_raise_pct': 0})
    result = run({'salary': salary}, [], months=3)

    balances = [s.node_balances['salary'] for s in result.snapshots]
    assert balances[1] == pytest.approx(2 * balances[0])
    assert balances[2] == pytest.approx(3 * balances[0])
