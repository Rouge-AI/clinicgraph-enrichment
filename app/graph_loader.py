"""Loads the curated knowledge graph into NetworkX at startup."""
import json
from pathlib import Path

import networkx as nx

_DATA_DIR = Path(__file__).parent.parent / "data" / "kg"


def load_graph() -> nx.DiGraph:
    """Load nodes and edges from JSON files into a directed NetworkX graph.

    Each node carries its full metadata as node attributes.
    Each edge carries relation, confidence, evidence, and sources as edge attributes.
    """
    with open(_DATA_DIR / "nodes.json") as f:
        nodes: list[dict] = json.load(f)
    with open(_DATA_DIR / "edges.json") as f:
        edges: list[dict] = json.load(f)

    g = nx.DiGraph()

    for node in nodes:
        node_id = node["id"]
        g.add_node(node_id, **{k: v for k, v in node.items() if k != "id"})

    for edge in edges:
        g.add_edge(
            edge["source"],
            edge["target"],
            relation=edge["relation"],
            confidence=edge["confidence"],
            evidence=edge["evidence"],
            sources=edge["sources"],
        )

    return g
