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
        Nodes in cycles are assigned the same rank and processed together.

        Returns dict mapping node_id to rank.
        """
        all_nodes = set(self.graph.keys()) | set(self.reverse_graph.keys())
        ranks: Dict[str, int] = {}

        # Find nodes with no incoming edges (sources)
        in_degree = defaultdict(int)
        for node in all_nodes:
            for target in self.graph.get(node, []):
                in_degree[target] += 1

        # Initialize sources with rank 0
        sources = [node for node in all_nodes if in_degree[node] == 0]
        for source in sources:
            ranks[source] = 0

        # Find cycles to handle specially
        cycles = self.find_all_cycles()
        cycle_nodes = set()
        for cycle in cycles:
            cycle_nodes.update(cycle.nodes)

        # BFS to assign ranks
        queue = list(sources)
        while queue:
            node = queue.pop(0)
            current_rank = ranks[node]

            for successor in self.graph.get(node, []):
                if successor in cycle_nodes and node in cycle_nodes:
                    # Same cycle - assign same rank
                    if successor not in ranks:
                        ranks[successor] = current_rank
                        queue.append(successor)
                else:
                    # Normal case - increment rank
                    new_rank = current_rank + 1
                    if successor not in ranks or ranks[successor] < new_rank:
                        ranks[successor] = new_rank
                        if successor not in queue:
                            queue.append(successor)

        # Handle any remaining unranked nodes (in cycles with no external inputs)
        for node in all_nodes:
            if node not in ranks:
                # Find minimum rank of predecessors, or use 0
                pred_ranks = [ranks.get(p, 0) for p in self.reverse_graph.get(node, [])]
                ranks[node] = max(pred_ranks) + 1 if pred_ranks else 0

        return ranks

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
