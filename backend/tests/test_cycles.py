"""
Cycle resolution: nodes in a cycle (e.g. checking -> savings -> checking) must
get exactly one month of activity per month, however many passes it takes to
converge, and money must be conserved.
"""

import pytest

from engine import GraphExecutor
from engine.graph_executor import FlowEdge, SimulationConfig
from modules import SavingsAccountModule

MONTHS = 6


def savings(node_id, balance, apy=0):
    return SavingsAccountModule(node_id, {'name': node_id, 'initial_balance': balance, 'apy': apy})


def run(nodes, edges, months=MONTHS, **config):
    executor = GraphExecutor()
    for node_id, module in nodes.items():
        executor.add_node(node_id, module)
    for edge in edges:
        executor.add_edge(edge)
    result = executor.simulate(SimulationConfig(start_year=2026, duration_months=months, **config))
    assert not result.errors
    return result


def edge(source, target, flow_type, amount=0, priority=1):
    return FlowEdge(source, target, flow_type, amount, 'monthly', priority)


def test_two_account_cycle_moves_each_flow_once():
    result = run(
        {'a': savings('a', 10000), 'b': savings('b', 10000)},
        [edge('a', 'b', 'fixed', 100), edge('b', 'a', 'fixed', 50)],
    )

    for i, snap in enumerate(result.snapshots, start=1):
        assert snap.node_balances['a'] == pytest.approx(10000 - 50 * i)
        assert snap.node_balances['b'] == pytest.approx(10000 + 50 * i)
        assert snap.net_worth == pytest.approx(20000)

        # Exactly one flow per edge per month
        pairs = sorted((f['source'], f['target']) for f in snap.flows)
        assert pairs == [('a', 'b'), ('b', 'a')]
        amounts = {(f['source'], f['target']): f['amount'] for f in snap.flows}
        assert amounts == {('a', 'b'): pytest.approx(100), ('b', 'a'): pytest.approx(50)}


def pass_through_balances(apy, months=MONTHS):
    """Balances of an account outside any cycle that receives 100 and pays out 100 a month"""
    result = run(
        {'src': savings('src', 100000), 'x': savings('x', 10000, apy=apy), 'sink': savings('sink', 0)},
        [edge('src', 'x', 'fixed', 100), edge('x', 'sink', 'fixed', 100)],
        months=months,
    )
    return [snap.node_balances['x'] for snap in result.snapshots]


def test_cycle_node_earns_one_month_of_interest():
    # 'a' receives 100 and pays out 100 each month, like the pass-through account
    result = run(
        {'a': savings('a', 10000, apy=5), 'b': savings('b', 1000)},
        [edge('a', 'b', 'fixed', 100), edge('b', 'a', 'fixed', 100)],
    )
    expected = pass_through_balances(apy=5)

    for snap, balance in zip(result.snapshots, expected):
        assert snap.node_balances['a'] == pytest.approx(balance)
        assert snap.node_balances['b'] == pytest.approx(1000)


def test_cycle_with_external_inflow_is_processed_after_it():
    # 'src' feeds both cycle members, one of them through an intermediate node,
    # so the whole cycle must run after 'mid'
    result = run(
        {
            'src': savings('src', 10000),
            'mid': savings('mid', 0),
            'a': savings('a', 0),
            'b': savings('b', 0),
        },
        [
            edge('src', 'a', 'fixed', 100),
            edge('src', 'mid', 'fixed', 100, priority=2),
            edge('mid', 'b', 'remainder'),
            edge('a', 'b', 'fixed', 30),
            edge('b', 'a', 'fixed', 10),
        ],
    )

    for i, snap in enumerate(result.snapshots, start=1):
        assert snap.net_worth == pytest.approx(10000)
        assert snap.node_balances['a'] == pytest.approx(80 * i)
        assert snap.node_balances['b'] == pytest.approx(120 * i)


@pytest.mark.parametrize('ab, ba', [
    (('percentage', 50), ('percentage', 50)),
    (('fixed', 200), ('percentage', 25)),
    (('remainder', 0), ('percentage', 10)),
    (('percentage', 30), ('remainder', 0)),
])
def test_percentage_and_remainder_cycles_converge(ab, ba):
    result = run(
        {'a': savings('a', 5000), 'b': savings('b', 3000)},
        [edge('a', 'b', *ab), edge('b', 'a', *ba)],
        months=12,
    )

    for snap in result.snapshots:
        assert snap.net_worth == pytest.approx(8000)
        assert snap.node_balances['a'] >= -0.01 and snap.node_balances['b'] >= -0.01
        assert not any('convergence warning' in e for e in snap.events)
        assert len(snap.flows) <= 2


def test_non_converging_cycle_terminates_and_conserves_money():
    # Remainder both ways keeps growing on every pass, so it never converges
    result = run(
        {'a': savings('a', 5000), 'b': savings('b', 3000)},
        [edge('a', 'b', 'remainder'), edge('b', 'a', 'remainder')],
        months=3,
        max_iterations=10,
    )

    for snap in result.snapshots:
        assert snap.net_worth == pytest.approx(8000)
        assert any('convergence warning' in e for e in snap.events)
        assert len(snap.flows) <= 2


def test_three_node_cycle_with_interest_conserves_flows():
    # checking -> savings -> brokerage -> checking, each 100/month, apy on all:
    # every account matches one outside a cycle that passes 100 through
    nodes = {n: savings(n, 10000, apy=4) for n in ('checking', 'savings', 'brokerage')}
    result = run(nodes, [
        edge('checking', 'savings', 'fixed', 100),
        edge('savings', 'brokerage', 'fixed', 100),
        edge('brokerage', 'checking', 'fixed', 100),
    ])
    expected = pass_through_balances(apy=4)

    for snap, balance in zip(result.snapshots, expected):
        for n in nodes:
            assert snap.node_balances[n] == pytest.approx(balance)
        assert len(snap.flows) == 3
