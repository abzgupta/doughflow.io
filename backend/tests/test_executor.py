"""Tests for the graph executor's scheduling of nodes."""

from engine import GraphExecutor
from engine.graph_executor import FlowEdge, SimulationConfig
from modules import SavingsAccountModule


def savings(node_id, balance, apy=0):
    return SavingsAccountModule(node_id, {'name': node_id, 'initial_balance': balance, 'apy': apy})


def test_unconnected_node_is_simulated():
    executor = GraphExecutor()
    executor.add_node('savings', savings('savings', 10000, apy=12))

    result = executor.simulate(SimulationConfig(duration_months=3))

    assert result.snapshots[-1].node_balances['savings'] > 10000


def test_unconnected_node_runs_alongside_connected_ones():
    executor = GraphExecutor()
    executor.add_node('a', savings('a', 1000))
    executor.add_node('b', savings('b', 0))
    executor.add_node('lonely', savings('lonely', 10000, apy=12))
    executor.add_edge(FlowEdge('a', 'b', 'fixed', 100, 'monthly', 1))

    result = executor.simulate(SimulationConfig(duration_months=2))

    assert result.snapshots[-1].node_balances['lonely'] > 10000
    assert result.snapshots[-1].node_balances['b'] > 0
