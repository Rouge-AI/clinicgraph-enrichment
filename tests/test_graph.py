"""RED-11 to RED-16: Knowledge graph loading and traversal tests."""
import pytest
import networkx as nx

from app.graph_loader import load_graph
from app.enricher import traverse_from_codes


@pytest.fixture(scope="module")
def kg():
    return load_graph()


# RED-11: graph loads successfully at startup (node count > 0)
def test_graph_loads_with_nodes(kg):
    assert kg.number_of_nodes() > 0


# RED-12: T2DM node has a path to CKD node (direct or via intermediate concept)
def test_t2dm_has_edge_to_ckd(kg):
    assert kg.has_node("E11.65"), "E11.65 node missing from graph"
    assert kg.has_node("N18.3"), "N18.3 node missing from graph"
    assert nx.has_path(kg, "E11.65", "N18.3"), "No path from E11.65 to N18.3 in graph"


# RED-13: 2-hop traversal from E11.65 finds N18.3
def test_two_hop_traversal_finds_ckd(kg):
    results = traverse_from_codes(["E11.65"], kg, max_hops=2)
    suggested = [r["suggested_code"] for r in results]
    assert "N18.3" in suggested


# RED-14: traversal returns confidence score between 0 and 1
def test_traversal_confidence_in_range(kg):
    results = traverse_from_codes(["E11.65"], kg, max_hops=2)
    for r in results:
        assert 0.0 <= r["confidence"] <= 1.0


# RED-15: traversal of unknown node returns empty list (no crash)
def test_traversal_unknown_node_no_crash(kg):
    results = traverse_from_codes(["Z99.999"], kg, max_hops=2)
    assert results == []


# RED-16: audit trail contains kg_path string
def test_traversal_includes_kg_path(kg):
    results = traverse_from_codes(["E11.65"], kg, max_hops=2)
    assert len(results) > 0
    for r in results:
        assert "kg_path" in r
        assert isinstance(r["kg_path"], str)
        assert len(r["kg_path"]) > 0
