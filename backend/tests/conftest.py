import json
import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DIR = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

from engine import ledger  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch):
    """Write the ledger to a temp file so tests don't clobber backend/ledger.log"""
    monkeypatch.setattr(ledger, 'LEDGER_PATH', str(tmp_path / 'ledger.log'))


@pytest.fixture
def sample_graph():
    """The example graph the frontend loads on startup, in API request format"""
    with open(os.path.join(REPO_DIR, 'src', 'examples', 'sampleGraph.json')) as f:
        graph = json.load(f)

    nodes = [
        {'id': n['id'], 'type': n['data']['moduleType'], 'config': n['data']['config']}
        for n in graph['nodes']
    ]
    edges = [
        {
            'source': e['source'],
            'target': e['target'],
            'flow_type': e['data'].get('flowType') or 'remainder',
            'amount': e['data'].get('amount') or 0,
            'frequency': e['data'].get('frequency') or 'monthly',
            'priority': e['data'].get('priority') or 0,
            'condition': e['data'].get('condition'),
        }
        for e in graph['edges']
    ]
    return {
        'nodes': nodes,
        'edges': edges,
        'user_profile': graph['userProfile'],
        'config': graph['simulationConfig'],
    }
