"""API tests using FastAPI's TestClient."""

import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'healthy'


def test_modules_lists_all_types(client):
    resp = client.get('/api/modules')
    assert resp.status_code == 200
    assert set(resp.json()) == {
        'salary', 'savings_account', 'stock_portfolio', 'four_oh_one_k',
        'five_twenty_nine', 'ira', 'real_estate', 'mortgage', 'debt', 'expense',
    }


def test_sample_graph_is_valid(client, sample_graph):
    resp = client.post('/api/graph/validate', json={
        'nodes': sample_graph['nodes'],
        'edges': sample_graph['edges'],
    })
    assert resp.status_code == 200
    assert resp.json()['valid'] is True


def test_simulate_sample_graph(client, sample_graph):
    resp = client.post('/api/simulate', json=sample_graph)
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert len(body['snapshots']) == sample_graph['config']['duration_months']
    first = body['snapshots'][0]
    assert (first['year'], first['month']) == (
        sample_graph['config']['start_year'], sample_graph['config']['start_month'])
    assert set(first['node_balances']) == {n['id'] for n in sample_graph['nodes']}


def test_simulate_unknown_module_type_returns_400(client):
    resp = client.post('/api/simulate', json={'nodes': [{'id': 'x', 'type': 'nope'}], 'edges': []})
    assert resp.status_code == 400
    body = resp.json()
    assert body['success'] is False
    assert 'Unknown module type' in body['error']
    assert 'traceback' not in body


def test_tax_calculate(client):
    resp = client.post('/api/tax/calculate', json={
        'income': {'wages': 150000},
        'user_profile': {'filing_status': 'single', 'state': 'CA'},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body['federal']['total_tax'] > 0
    assert body['state']['tax_liability'] > 0


def test_legacy_financial_table(client, sample_graph):
    rental = next(n['config'] for n in sample_graph['nodes'] if n['type'] == 'real_estate')
    resp = client.post('/get_financial_table_summarized',
                       json={'property_list': [dict(rental, holding_length=24)]})
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def _resume_states(snapshot):
    """Node states in the shape the frontend sends after a transaction"""
    return {
        node_id: {'balance': snapshot['node_balances'][node_id], 'state': data.get('state', {})}
        for node_id, data in snapshot['node_states'].items()
    }


def test_continue_from_saved_state(client, sample_graph):
    sim = client.post('/api/simulate', json=sample_graph).json()
    node_states = _resume_states(sim['snapshots'][11])

    resp = client.post('/api/simulate/continue', json={
        **sample_graph, 'resume_from_month': 13, 'node_states': node_states,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    assert len(body['snapshots']) == sample_graph['config']['duration_months'] - 12
    assert body['snapshots'][0]['month_number'] == 13


def test_step_from_saved_state(client, sample_graph):
    sim = client.post('/api/simulate', json=sample_graph).json()
    node_states = _resume_states(sim['snapshots'][11])

    resp = client.post('/api/simulate/step', json={
        'nodes': sample_graph['nodes'], 'edges': sample_graph['edges'],
        'user_profile': sample_graph['user_profile'], 'node_states': node_states,
        'current_year': sample_graph['config']['start_year'] + 1, 'current_month': 1, 'month_number': 13,
    })
    assert resp.status_code == 200
    assert resp.json()['success'] is True
