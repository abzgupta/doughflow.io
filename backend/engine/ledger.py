"""
Transaction Ledger for Debugging

Logs all financial flows and state changes during simulation.
Can be cleared/truncated when restarting simulation.
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ledger file path
LEDGER_PATH = os.path.join(os.path.dirname(__file__), '..', 'ledger.log')


def clear_ledger():
    """Clear/truncate the ledger file."""
    with open(LEDGER_PATH, 'w') as f:
        f.write(f"=== LEDGER CLEARED: {datetime.now().isoformat()} ===\n\n")


def log_simulation_start(config: Dict[str, Any], nodes: List[str]):
    """Log simulation start with configuration."""
    with open(LEDGER_PATH, 'a') as f:
        f.write("=" * 80 + "\n")
        f.write(f"SIMULATION STARTED: {datetime.now().isoformat()}\n")
        f.write(f"Config: start={config.get('start_year', 2024)}-{config.get('start_month', 1):02d}, ")
        f.write(f"duration={config.get('duration_months', 120)} months\n")
        f.write(f"Nodes: {', '.join(nodes)}\n")
        f.write("=" * 80 + "\n\n")


def log_month_start(year: int, month: int, month_number: int, node_balances: Dict[str, float]):
    """Log the start of a month with all balances."""
    with open(LEDGER_PATH, 'a') as f:
        f.write("-" * 60 + "\n")
        f.write(f"MONTH {month_number}: {month}/{year}\n")
        f.write("-" * 60 + "\n")
        f.write("Starting Balances:\n")
        for node_id, balance in sorted(node_balances.items()):
            f.write(f"  {node_id:30s}: ${balance:>15,.2f}\n")
        f.write("\n")


def log_node_processing(
    node_id: str,
    inflows: Dict[str, float],
    available: float,
    result_balance: float,
    events: List[str]
):
    """Log processing of a single node."""
    with open(LEDGER_PATH, 'a') as f:
        f.write(f"  Processing: {node_id}\n")
        if inflows:
            total_in = sum(inflows.values())
            f.write(f"    Inflows: ${total_in:,.2f}\n")
            for source, amount in inflows.items():
                f.write(f"      <- {source}: ${amount:,.2f}\n")
        f.write(f"    Available for outflow: ${available:,.2f}\n")
        f.write(f"    Result balance: ${result_balance:,.2f}\n")
        if events:
            for event in events:
                f.write(f"    Event: {event}\n")
        f.write("\n")


def log_flow(source: str, target: str, amount: float, flow_type: str = "edge"):
    """Log a money flow between nodes."""
    with open(LEDGER_PATH, 'a') as f:
        f.write(f"  FLOW [{flow_type}]: {source} -> {target}: ${amount:,.2f}\n")


def log_month_end(year: int, month: int, node_balances: Dict[str, float], net_worth: float):
    """Log the end of a month with final balances."""
    with open(LEDGER_PATH, 'a') as f:
        f.write("\nEnding Balances:\n")
        for node_id, balance in sorted(node_balances.items()):
            f.write(f"  {node_id:30s}: ${balance:>15,.2f}\n")
        f.write(f"\n  NET WORTH: ${net_worth:>15,.2f}\n")
        f.write("\n")


def log_inactive_nodes(inactive_nodes: List[str]):
    """Log which nodes are inactive this month."""
    if inactive_nodes:
        with open(LEDGER_PATH, 'a') as f:
            f.write(f"  Inactive nodes: {', '.join(inactive_nodes)}\n\n")


def log_transaction(
    transaction_type: str,
    params: Dict[str, Any],
    result: Dict[str, Any],
    year: int,
    month: int
):
    """Log a manual transaction."""
    with open(LEDGER_PATH, 'a') as f:
        f.write("\n" + "=" * 40 + "\n")
        f.write(f"MANUAL TRANSACTION: {transaction_type.upper()}\n")
        f.write(f"Date: {month}/{year}\n")
        f.write(f"Params: {params}\n")
        f.write(f"Success: {result.get('success', False)}\n")
        f.write(f"Message: {result.get('message', '')}\n")
        if result.get('updated_balances'):
            f.write("Updated balances:\n")
            for node_id, balance in result['updated_balances'].items():
                f.write(f"  {node_id}: ${balance:,.2f}\n")
        if result.get('tax_implications'):
            f.write(f"Tax implications: {result['tax_implications']}\n")
        f.write("=" * 40 + "\n\n")


def log_simulation_end(final_net_worth: float, total_months: int):
    """Log simulation completion."""
    with open(LEDGER_PATH, 'a') as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"SIMULATION COMPLETE: {datetime.now().isoformat()}\n")
        f.write(f"Total months simulated: {total_months}\n")
        f.write(f"Final net worth: ${final_net_worth:,.2f}\n")
        f.write("=" * 80 + "\n")


def log_error(message: str, context: Optional[Dict[str, Any]] = None):
    """Log an error."""
    with open(LEDGER_PATH, 'a') as f:
        f.write(f"\n!!! ERROR: {message}\n")
        if context:
            f.write(f"    Context: {context}\n")
        f.write("\n")
