"""
build_kg.py — Documents the schema for the ClinicalGraph knowledge graph data files.

This script is NOT run at startup. It is a reference/documentation script showing
how nodes.json, edges.json, and icd_map.json were constructed and how they could be
regenerated from raw ontology sources in the future.

Future upgrade path (see FUTURE.md):
  - Replace hand-curated nodes/edges with automated PrimeKG ingestion
  - Filter PrimeKG kg.csv to the 3 clinical domains
  - Map UMLS CUIs to ICD-10-CM codes via UMLS API

Usage (dry-run schema validation):
    python scripts/build_kg.py
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "kg"

NODE_SCHEMA = {
    "id":           "str  — ICD-10 code or concept identifier (primary key)",
    "type":         "str  — 'icd10' | 'concept' | 'snomed'",
    "display":      "str  — Human-readable label for Swagger UI and audit trail",
    "cui":          "str  — UMLS Concept Unique Identifier",
    "domain":       "str  — 'diabetes' | 'cardiovascular' | 'renal' | 'metabolic' | 'respiratory' | 'symptom' | ...",
    "hcc_relevant": "bool — True if this code is relevant for HCC risk adjustment coding",
    "sources":      "list[str] — Ontology sources: 'icd10cm' | 'snomed-subset' | 'primekg-subset'",
}

EDGE_SCHEMA = {
    "source":     "str   — Node id (source of the directed edge)",
    "target":     "str   — Node id (target of the directed edge)",
    "relation":   "str   — Relationship type: 'associated_with' | 'complication_of' | 'risk_factor_for' | ...",
    "confidence": "float — 0.0–1.0 confidence score for this edge",
    "evidence":   "str   — Human-readable evidence string shown in audit trail",
    "sources":    "list[str] — Ontology sources supporting this edge",
}

ICD_MAP_SCHEMA = {
    "<UMLS CUI>": "<ICD-10-CM code>  — Primary ICD code for this concept",
}

RELATION_TYPES = [
    "associated_with",
    "complication_of",
    "risk_factor_for",
    "maps_to",
    "suggests",
    "progression_to",
    "specificity_upgrade",
    "treatment_pathway",
    "requires_monitoring",
    "triggers_flag",
    "pattern_match",
    "comorbidity_cluster",
    "component_of",
    "causes",
    "requires",
    "symptom_pattern",
]


def validate_kg() -> None:
    """Validate the existing KG data files against the schema."""
    print("ClinicalGraph KG Schema Validator\n" + "=" * 40)

    nodes_path = DATA_DIR / "nodes.json"
    edges_path = DATA_DIR / "edges.json"
    icd_map_path = DATA_DIR / "icd_map.json"

    with open(nodes_path) as f:
        nodes: list[dict] = json.load(f)
    with open(edges_path) as f:
        edges: list[dict] = json.load(f)
    with open(icd_map_path) as f:
        icd_map: dict = json.load(f)

    node_ids = {n["id"] for n in nodes}
    errors: list[str] = []

    # Validate nodes
    for i, node in enumerate(nodes):
        for field in NODE_SCHEMA:
            if field not in node:
                errors.append(f"Node[{i}] '{node.get('id', '?')}' missing field: {field}")

    # Validate edges
    for i, edge in enumerate(edges):
        for field in EDGE_SCHEMA:
            if field not in edge:
                errors.append(f"Edge[{i}] missing field: {field}")
        if edge.get("source") not in node_ids:
            errors.append(f"Edge[{i}] source '{edge.get('source')}' not in nodes")
        if edge.get("target") not in node_ids:
            errors.append(f"Edge[{i}] target '{edge.get('target')}' not in nodes")
        if not (0.0 <= edge.get("confidence", -1) <= 1.0):
            errors.append(f"Edge[{i}] confidence out of range: {edge.get('confidence')}")
        if edge.get("relation") not in RELATION_TYPES:
            errors.append(f"Edge[{i}] unknown relation type: '{edge.get('relation')}'")

    print(f"Nodes:   {len(nodes)}")
    print(f"Edges:   {len(edges)}")
    print(f"ICD map: {len(icd_map)} entries")
    print(f"Domains: {sorted({n['domain'] for n in nodes})}")

    if errors:
        print(f"\n{len(errors)} validation error(s):")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("\nAll schema checks passed.")


if __name__ == "__main__":
    validate_kg()
