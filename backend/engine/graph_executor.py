"""
Graph Executor for Financial Flow Simulation

Core simulation engine that:
- Executes financial flow graphs month by month
- Handles cycle resolution through iterative convergence
- Tracks money movement between nodes
- Calculates taxes and net worth
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import copy

from .cycle_detector import CycleDetector, Edge, CycleInfo
from . import ledger


@dataclass
class FlowEdge:
    """Configuration for money flow between nodes"""
    source_id: str
    target_id: str
    flow_type: str  # 'fixed', 'percentage', 'remainder'
    amount: float  # Fixed amount or percentage (0-100)
    frequency: str  # 'monthly', 'quarterly', 'annually'
    priority: int  # Lower = higher priority
    condition: Optional[Dict] = None  # e.g., {"type": "threshold", "source_balance_min": 10000}
    active: bool = True


@dataclass
class SimulationConfig:
    """Configuration for the simulation"""
    start_year: int = 2024
    start_month: int = 1
    duration_months: int = 120  # 10 years default
    convergence_threshold: float = 0.01  # For cycle resolution
    max_iterations: int = 100  # Max iterations for cycle convergence


@dataclass
class MonthlySnapshot:
    """Snapshot of all node states for a single month"""
    year: int
    month: int
    month_number: int  # 1-indexed from simulation start
    node_balances: Dict[str, float] = field(default_factory=dict)
    node_states: Dict[str, Dict] = field(default_factory=dict)
    flows: List[Dict] = field(default_factory=list)  # [{source, target, amount}]
    events: List[str] = field(default_factory=list)
    tax_info: Dict[str, Any] = field(default_factory=dict)
    net_worth: float = 0.0
    inactive_nodes: List[str] = field(default_factory=list)  # Nodes past their end date


@dataclass
class SimulationResult:
    """Complete simulation result"""
    config: SimulationConfig
    snapshots: List[MonthlySnapshot] = field(default_factory=list)
    final_net_worth: float = 0.0
    total_income: float = 0.0
    total_expenses: float = 0.0
    total_taxes: float = 0.0
    annual_summaries: Dict[int, Dict] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class GraphExecutor:
    """
    Executes financial flow graph simulations.

    Usage:
        executor = GraphExecutor()
        executor.add_node('salary', SalaryModule('salary', {...}))
        executor.add_node('checking', AccountModule('checking', {...}))
        executor.add_edge(FlowEdge('salary', 'checking', 'remainder', 0, 'monthly', 0))
        result = executor.simulate(SimulationConfig(duration_months=60))
    """

    def __init__(self):
        self.nodes: Dict[str, Any] = {}  # node_id -> module instance
        self.edges: List[FlowEdge] = []
        self.user_profile: Dict[str, Any] = {}
        self._cycle_detector = CycleDetector()

    def add_node(self, node_id: str, module: Any) -> None:
        """Add a node (financial module) to the graph"""
        self.nodes[node_id] = module

    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its edges"""
        if node_id in self.nodes:
            del self.nodes[node_id]
        self.edges = [e for e in self.edges if e.source_id != node_id and e.target_id != node_id]

    def add_edge(self, edge: FlowEdge) -> None:
        """Add an edge (money flow) to the graph"""
        self.edges.append(edge)

    def remove_edge(self, source_id: str, target_id: str) -> None:
        """Remove an edge"""
        self.edges = [e for e in self.edges if not (e.source_id == source_id and e.target_id == target_id)]

    def set_user_profile(self, profile: Dict[str, Any]) -> None:
        """Set user profile for tax calculations"""
        self.user_profile = profile

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the graph configuration.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check all edge endpoints exist
        for edge in self.edges:
            if edge.source_id not in self.nodes:
                errors.append(f"Edge source '{edge.source_id}' not found in nodes")
            if edge.target_id not in self.nodes:
                errors.append(f"Edge target '{edge.target_id}' not found in nodes")

        # Check for orphan nodes (no connections)
        connected_nodes = set()
        for edge in self.edges:
            connected_nodes.add(edge.source_id)
            connected_nodes.add(edge.target_id)

        orphans = set(self.nodes.keys()) - connected_nodes
        if orphans:
            # Orphans are allowed but we'll note them
            pass

        # Check percentage flows don't exceed 100% from any node
        outflow_percentages: Dict[str, float] = defaultdict(float)
        for edge in self.edges:
            if edge.flow_type == 'percentage':
                outflow_percentages[edge.source_id] += edge.amount

        for node_id, total_pct in outflow_percentages.items():
            if total_pct > 100:
                errors.append(f"Node '{node_id}' has {total_pct}% total outflow (max 100%)")

        # Check for multiple 'remainder' flows from same node
        remainder_counts: Dict[str, int] = defaultdict(int)
        for edge in self.edges:
            if edge.flow_type == 'remainder':
                remainder_counts[edge.source_id] += 1

        for node_id, count in remainder_counts.items():
            if count > 1:
                errors.append(f"Node '{node_id}' has {count} remainder flows (max 1)")

        return len(errors) == 0, errors

    def _build_cycle_detector(self) -> None:
        """Build cycle detector from current edges"""
        self._cycle_detector.clear()
        for edge in self.edges:
            self._cycle_detector.add_edge(Edge(
                source=edge.source_id,
                target=edge.target_id,
                flow_type=edge.flow_type,
                amount=edge.amount,
                frequency=edge.frequency,
                priority=edge.priority,
                condition=edge.condition
            ))

    def _should_execute_edge(self, edge: FlowEdge, month: int, year: int) -> bool:
        """Check if an edge should execute this month based on frequency"""
        if not edge.active:
            return False

        if edge.frequency == 'monthly':
            return True
        elif edge.frequency == 'quarterly':
            return month in [1, 4, 7, 10]
        elif edge.frequency == 'annually':
            return month == 1
        return True

    def _check_condition(self, edge: FlowEdge, node_balances: Dict[str, float]) -> bool:
        """Check if edge condition is met"""
        if not edge.condition:
            return True

        cond_type = edge.condition.get('type')

        if cond_type == 'threshold':
            min_balance = edge.condition.get('source_balance_min', 0)
            return node_balances.get(edge.source_id, 0) >= min_balance

        elif cond_type == 'date_range':
            # Would need current date context
            return True

        elif cond_type == 'target_max':
            max_balance = edge.condition.get('target_balance_max', float('inf'))
            return node_balances.get(edge.target_id, 0) < max_balance

        return True

    def _calculate_flow_amount(
        self,
        edge: FlowEdge,
        available: float,
        node_balances: Dict[str, float]
    ) -> float:
        """Calculate the amount to flow through an edge"""
        if edge.flow_type == 'fixed':
            return min(edge.amount, available)
        elif edge.flow_type == 'percentage':
            return min(available * (edge.amount / 100.0), available)
        elif edge.flow_type == 'remainder':
            return available
        return 0.0

    def _execute_month(
        self,
        month: int,
        year: int,
        month_number: int,
        node_balances: Dict[str, float],
        config: SimulationConfig
    ) -> MonthlySnapshot:
        """Execute one month of simulation"""
        snapshot = MonthlySnapshot(
            year=year,
            month=month,
            month_number=month_number,
            node_balances=copy.deepcopy(node_balances)
        )

        # Log month start
        ledger.log_month_start(year, month, month_number, node_balances)

        # Determine which nodes are inactive for this month
        inactive_nodes = []
        for node_id, module in self.nodes.items():
            if hasattr(module, 'is_active_for_date'):
                if not module.is_active_for_date(year, month):
                    inactive_nodes.append(node_id)
        snapshot.inactive_nodes = inactive_nodes

        # Log inactive nodes
        if inactive_nodes:
            ledger.log_inactive_nodes(inactive_nodes)

        # Get execution order based on ranks
        nodes_by_rank = self._cycle_detector.get_nodes_by_rank()
        # The cycle detector only knows nodes that have edges; unconnected
        # nodes still need to run (interest, growth, rent), so put them first
        ranked = {n for rank in nodes_by_rank for n in rank}
        unconnected = [n for n in self.nodes if n not in ranked]
        if unconnected:
            if not nodes_by_rank:
                nodes_by_rank = [[]]
            nodes_by_rank[0] = unconnected + nodes_by_rank[0]
        cycles = self._cycle_detector.find_all_cycles()
        cycle_node_ids = set()
        for cycle in cycles:
            cycle_node_ids.update(cycle.nodes)

        # Process nodes by rank
        inflows: Dict[str, Dict[str, float]] = defaultdict(dict)  # target -> {source: amount}
        outflows: Dict[str, float] = defaultdict(float)  # source -> total outflow

        for rank_nodes in nodes_by_rank:
            # Check if this rank contains cycle nodes
            has_cycle = any(n in cycle_node_ids for n in rank_nodes)

            if has_cycle:
                # Filter out inactive nodes from cycle processing
                active_rank_nodes = [n for n in rank_nodes if n not in inactive_nodes]
                if active_rank_nodes:
                    # Iterate until convergence
                    self._resolve_cycle_rank(
                        active_rank_nodes, month, year, node_balances, inflows, outflows,
                        snapshot, config, inactive_nodes
                    )
            else:
                # Process normally
                for node_id in rank_nodes:
                    if node_id not in self.nodes:
                        continue
                    # Skip inactive nodes
                    if node_id in inactive_nodes:
                        continue

                    self._process_node(
                        node_id, month, year, node_balances, inflows, outflows, snapshot, inactive_nodes
                    )

        # Update final balances
        snapshot.node_balances = copy.deepcopy(node_balances)

        # Calculate net worth from module balances (debts are negative).
        # Expense nodes are skipped: their balance is a running total of money
        # already paid out of other accounts, so counting it would subtract twice.
        net_worth = 0.0
        for module in self.nodes.values():
            if module.module_type.value == 'expense':
                continue
            net_worth += module.get_state().balance
        snapshot.net_worth = net_worth

        # Log month end
        ledger.log_month_end(year, month, node_balances, net_worth)

        return snapshot

    def _process_node(
        self,
        node_id: str,
        month: int,
        year: int,
        node_balances: Dict[str, float],
        inflows: Dict[str, Dict[str, float]],
        outflows: Dict[str, float],
        snapshot: MonthlySnapshot,
        inactive_nodes: List[str] = None
    ) -> None:
        """Process a single node for one month"""
        if inactive_nodes is None:
            inactive_nodes = []

        module = self.nodes.get(node_id)
        if not module:
            return

        # Calculate available balance (current balance + inflows from active nodes)
        node_inflows = inflows.get(node_id, {})
        # Filter out inflows from inactive nodes
        active_inflows = {k: v for k, v in node_inflows.items() if k not in inactive_nodes}
        total_inflow = sum(active_inflows.values())
        # Informational for the module: what it will hold once inflows land
        available = module.get_state().balance + total_inflow

        # Get outgoing edges, sorted by priority
        # Filter out edges to inactive nodes
        outgoing = [e for e in self.edges if e.source_id == node_id and e.target_id not in inactive_nodes]
        outgoing.sort(key=lambda e: e.priority)

        # Execute the node's monthly processing
        result = module.process_month(
            month=month,
            year=year,
            inflows=node_inflows,
            available_for_outflow=available,
            user_profile=self.user_profile
        )

        # The module's own state is the source of truth for its balance
        new_balance = module.get_state().balance
        node_balances[node_id] = new_balance

        # Log node processing
        ledger.log_node_processing(
            node_id=node_id,
            inflows=active_inflows,
            available=available,
            result_balance=new_balance,
            events=result.events
        )

        # Add events
        snapshot.events.extend(result.events)

        # Process outgoing flows: money leaves the module itself, and the target
        # receives exactly what the module paid out
        remaining = new_balance
        for edge in outgoing:
            if not self._should_execute_edge(edge, month, year):
                continue
            if not self._check_condition(edge, node_balances):
                continue

            flow_amount = self._calculate_flow_amount(edge, remaining, node_balances)
            if flow_amount > 0:
                flow_amount = module.apply_outflow(flow_amount)
                inflows[edge.target_id][node_id] = flow_amount
                outflows[node_id] += flow_amount
                remaining -= flow_amount
                node_balances[node_id] = module.get_state().balance

                # Log the flow
                ledger.log_flow(node_id, edge.target_id, flow_amount, edge.flow_type)

                snapshot.flows.append({
                    'source': node_id,
                    'target': edge.target_id,
                    'amount': flow_amount
                })

        # Store node state after outflows so it matches node_balances
        snapshot.node_states[node_id] = module.to_dict()

        # Aggregate tax info
        if result.tax_info:
            if 'nodes' not in snapshot.tax_info:
                snapshot.tax_info['nodes'] = {}
            snapshot.tax_info['nodes'][node_id] = {
                'taxable_income': result.tax_info.taxable_income,
                'deductions': result.tax_info.deductions,
                'capital_gains_short': result.tax_info.capital_gains_short,
                'capital_gains_long': result.tax_info.capital_gains_long,
            }

    def _resolve_cycle_rank(
        self,
        rank_nodes: List[str],
        month: int,
        year: int,
        node_balances: Dict[str, float],
        inflows: Dict[str, Dict[str, float]],
        outflows: Dict[str, float],
        snapshot: MonthlySnapshot,
        config: SimulationConfig,
        inactive_nodes: List[str] = None
    ) -> None:
        """Resolve cycles through iterative convergence"""
        if inactive_nodes is None:
            inactive_nodes = []

        prev_balances = {n: node_balances.get(n, 0) for n in rank_nodes}

        for iteration in range(config.max_iterations):
            # Process all nodes in the cycle
            for node_id in rank_nodes:
                if node_id in self.nodes:
                    self._process_node(
                        node_id, month, year, node_balances, inflows, outflows, snapshot, inactive_nodes
                    )

            # Check convergence
            max_diff = 0.0
            for node_id in rank_nodes:
                diff = abs(node_balances.get(node_id, 0) - prev_balances.get(node_id, 0))
                max_diff = max(max_diff, diff)
                prev_balances[node_id] = node_balances.get(node_id, 0)

            if max_diff < config.convergence_threshold:
                break

        if iteration >= config.max_iterations - 1:
            snapshot.events.append(f"Cycle convergence warning: max iterations reached")

    def simulate(self, config: Optional[SimulationConfig] = None) -> SimulationResult:
        """
        Run the full simulation.

        Args:
            config: Simulation configuration (uses defaults if not provided)

        Returns:
            SimulationResult with all snapshots and summaries
        """
        if config is None:
            config = SimulationConfig()

        result = SimulationResult(config=config)

        # Validate
        is_valid, errors = self.validate()
        if not is_valid:
            result.errors = errors
            return result

        # Build cycle detector
        self._build_cycle_detector()

        # Initialize all nodes
        start_date = f"{config.start_year}-{config.start_month:02d}"
        node_balances: Dict[str, float] = {}
        for node_id, module in self.nodes.items():
            initial_state = module.initialize(start_date)
            node_balances[node_id] = getattr(initial_state, 'balance', 0)

        # Log simulation start
        ledger.log_simulation_start(
            {'start_year': config.start_year, 'start_month': config.start_month, 'duration_months': config.duration_months},
            list(self.nodes.keys())
        )

        # Run simulation month by month
        current_year = config.start_year
        current_month = config.start_month
        annual_data: Dict[int, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

        for month_number in range(1, config.duration_months + 1):
            snapshot = self._execute_month(
                month=current_month,
                year=current_year,
                month_number=month_number,
                node_balances=node_balances,
                config=config
            )
            result.snapshots.append(snapshot)

            # Track annual data
            for flow in snapshot.flows:
                annual_data[current_year]['total_flow'] += flow['amount']

            # Advance month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

                # Generate annual summary
                result.annual_summaries[current_year - 1] = dict(annual_data[current_year - 1])

        # Final calculations
        if result.snapshots:
            final = result.snapshots[-1]
            result.final_net_worth = final.net_worth

        # Log simulation end
        ledger.log_simulation_end(result.final_net_worth, len(result.snapshots))

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary"""
        return {
            'nodes': {nid: m.to_dict() for nid, m in self.nodes.items()},
            'edges': [
                {
                    'source_id': e.source_id,
                    'target_id': e.target_id,
                    'flow_type': e.flow_type,
                    'amount': e.amount,
                    'frequency': e.frequency,
                    'priority': e.priority,
                    'condition': e.condition,
                    'active': e.active
                }
                for e in self.edges
            ],
            'user_profile': self.user_profile
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], module_factory) -> 'GraphExecutor':
        """
        Deserialize graph from dictionary.

        Args:
            data: Serialized graph data
            module_factory: Function(type, node_id, config) -> module instance
        """
        executor = cls()

        for node_id, node_data in data.get('nodes', {}).items():
            module = module_factory(
                node_data['module_type'],
                node_id,
                node_data['config']
            )
            executor.add_node(node_id, module)

        for edge_data in data.get('edges', []):
            executor.add_edge(FlowEdge(
                source_id=edge_data['source_id'],
                target_id=edge_data['target_id'],
                flow_type=edge_data['flow_type'],
                amount=edge_data['amount'],
                frequency=edge_data['frequency'],
                priority=edge_data['priority'],
                condition=edge_data.get('condition'),
                active=edge_data.get('active', True)
            ))

        executor.user_profile = data.get('user_profile', {})
        return executor
