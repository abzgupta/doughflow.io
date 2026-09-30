"""
Cycle Detection and Node Ranking for Financial Flow Graphs

Handles:
- Detection of cycles in the flow graph
- Computing node execution ranks for topological ordering
- Cycle resolution through iterative convergence
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class Edge:
    """Represents a directed edge in the flow graph"""
    source: str
    target: str
    flow_type: str  # 'fixed', 'percentage', 'remainder'
    amount: float  # Fixed amount or percentage (0-100)
    frequency: str  # 'monthly', 'quarterly', 'annually'
    priority: int  # Execution priority when multiple outflows
    condition: Optional[Dict] = None  # Threshold conditions


@dataclass
class CycleInfo:
    """Information about a detected cycle"""
    nodes: List[str]  # Nodes in the cycle
    edges: List[Edge]  # Edges forming the cycle


class CycleDetector:
    """
    Detects cycles in a directed graph and computes node ranks.

    Uses Tarjan's algorithm for cycle detection and modified
    topological sort for ranking nodes that may contain cycles.
    """

    def __init__(self):
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)
        self.edges: Dict[Tuple[str, str], Edge] = {}

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph"""
        self.graph[edge.source].append(edge.target)
        self.reverse_graph[edge.target].append(edge.source)
        self.edges[(edge.source, edge.target)] = edge

    def clear(self) -> None:
        """Clear the graph"""
        self.graph.clear()
        self.reverse_graph.clear()
        self.edges.clear()

    def build_from_edges(self, edges: List[Edge]) -> None:
        """Build graph from list of edges"""
        self.clear()
        for edge in edges:
            self.add_edge(edge)

    def find_all_cycles(self) -> List[CycleInfo]:
        """
        Find all cycles using Tarjan's strongly connected components algorithm.

        Returns list of CycleInfo for each cycle found.
        """
        index_counter = [0]
        stack = []
        lowlinks = {}
        index = {}
        on_stack = {}
        sccs = []

        def strongconnect(node):
            index[node] = index_counter[0]
            lowlinks[node] = index_counter[0]
            index_counter[0] += 1
            stack.append(node)
            on_stack[node] = True

            for successor in self.graph.get(node, []):
                if successor not in index:
                    strongconnect(successor)
                    lowlinks[node] = min(lowlinks[node], lowlinks[successor])
                elif on_stack.get(successor, False):
                    lowlinks[node] = min(lowlinks[node], index[successor])

            if lowlinks[node] == index[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.append(w)
                    if w == node:
                        break
                if len(scc) > 1:  # Only consider SCCs with more than one node as cycles
                    sccs.append(scc)
                elif len(scc) == 1 and node in self.graph.get(node, []):
                    # Self-loop
                    sccs.append(scc)

        all_nodes = set(self.graph.keys()) | set(self.reverse_graph.keys())
        for node in all_nodes:
            if node not in index:
                strongconnect(node)

        # Convert SCCs to CycleInfo
        cycles = []
        for scc in sccs:
            cycle_edges = []
            for i, node in enumerate(scc):
                for successor in self.graph.get(node, []):
                    if successor in scc:
                        edge = self.edges.get((node, successor))
                        if edge:
                            cycle_edges.append(edge)
            cycles.append(CycleInfo(nodes=scc, edges=cycle_edges))

        return cycles

    def has_cycles(self) -> bool:
        """Check if graph has any cycles"""
        return len(self.find_all_cycles()) > 0

    def compute_node_ranks(self) -> Dict[str, int]:
        """
        Compute execution ranks for nodes.

        Nodes with no incoming edges have rank 0.
        Other nodes have rank = max(predecessor ranks) + 1.
        Nodes in cycles are assigned the same rank and processed together:
        each cycle is collapsed into a single group whose rank is one more than
        the highest rank feeding into it from outside, so every node paying
        into the cycle runs before any of its members.

        Returns dict mapping node_id to rank.
        """
        all_nodes = set(self.graph.keys()) | set(self.reverse_graph.keys())

        # Collapse each cycle into one group; other nodes are groups of one
        group_of: Dict[str, str] = {node: node for node in all_nodes}
        for cycle in self.find_all_cycles():
            for node in cycle.nodes:
                group_of[node] = cycle.nodes[0]

        # Edges between groups form a DAG
        group_preds: Dict[str, Set[str]] = defaultdict(set)
        group_succs: Dict[str, Set[str]] = defaultdict(set)
        for source, targets in self.graph.items():
            for target in targets:
                if group_of[source] != group_of[target]:
                    group_succs[group_of[source]].add(group_of[target])
                    group_preds[group_of[target]].add(group_of[source])

        # Longest-path ranking in topological order (Kahn's algorithm)
        groups = set(group_of.values())
        waiting_on = {g: len(group_preds[g]) for g in groups}
        queue = [g for g in groups if waiting_on[g] == 0]
        group_ranks: Dict[str, int] = {}
        while queue:
            group = queue.pop(0)
            group_ranks[group] = max((group_ranks[p] + 1 for p in group_preds[group]), default=0)
            for successor in group_succs[group]:
                waiting_on[successor] -= 1
                if waiting_on[successor] == 0:
                    queue.append(successor)

        return {node: group_ranks[group_of[node]] for node in all_nodes}

    def get_nodes_by_rank(self) -> List[List[str]]:
        """
        Get nodes grouped by their execution rank.

        Returns list of lists, where each inner list contains
        nodes that can be processed together at that rank.
        """
        ranks = self.compute_node_ranks()
        max_rank = max(ranks.values()) if ranks else 0

        result = [[] for _ in range(max_rank + 1)]
        for node, rank in ranks.items():
            result[rank].append(node)

        return result


def detect_cycles(edges: List[Dict]) -> List[CycleInfo]:
    """
    Utility function to detect cycles from a list of edge dictionaries.

    Args:
        edges: List of dicts with 'source', 'target', and optional flow properties

    Returns:
        List of CycleInfo objects for each cycle found
    """
    detector = CycleDetector()
    for edge_dict in edges:
        edge = Edge(
            source=edge_dict['source'],
            target=edge_dict['target'],
            flow_type=edge_dict.get('flow_type', 'fixed'),
            amount=edge_dict.get('amount', 0),
            frequency=edge_dict.get('frequency', 'monthly'),
            priority=edge_dict.get('priority', 0),
            condition=edge_dict.get('condition')
        )
        detector.add_edge(edge)

    return detector.find_all_cycles()


def compute_node_ranks(edges: List[Dict]) -> Dict[str, int]:
    """
    Utility function to compute node ranks from a list of edge dictionaries.

    Args:
        edges: List of dicts with 'source' and 'target' keys

    Returns:
        Dict mapping node_id to execution rank
    """
    detector = CycleDetector()
    for edge_dict in edges:
        edge = Edge(
            source=edge_dict['source'],
            target=edge_dict['target'],
            flow_type=edge_dict.get('flow_type', 'fixed'),
            amount=edge_dict.get('amount', 0),
            frequency=edge_dict.get('frequency', 'monthly'),
            priority=edge_dict.get('priority', 0),
            condition=edge_dict.get('condition')
        )
        detector.add_edge(edge)

    return detector.compute_node_ranks()
