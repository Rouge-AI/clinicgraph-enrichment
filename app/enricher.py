"""Core enrichment logic — KG traversal and full pipeline."""
import time
from typing import Any

import networkx as nx

from app.imo_client import get_imo_suggestion
from app.models import EnrichRequest, EnrichResponse, IMOTerminology
from app.ner import extract_entities

KG_VERSION = "clinicgraph-v0.1-demo"
ONTOLOGY_SOURCES = ["SNOMED-subset", "ICD10-CM-subset", "PrimeKG-subset"]

# Node id prefixes that mark intermediate concept/cluster nodes —
# used during traversal but never surfaced as gap flags.
_CONCEPT_PREFIXES = (
    "E11.65+", "HTN_", "Obesity_", "CAD_", "AFib_", "CHF_",
    "NAFLD_", "Stroke_", "CKD_", "Insulin_", "Metab", "Diabetic_",
)

# Minimum confidence threshold to surface a gap flag
_MIN_CONFIDENCE = 0.30

# ICD-10 codes that are administrative / monitoring concepts, not gap flags
_SKIP_TARGETS = {
    "HbA1c_monitoring", "BNP_monitoring", "insulin_therapy",
    "metformin_ckd_risk", "Insulin_Resistance", "MetabolicSyndrome",
}


def _is_concept_node(node_id: str) -> bool:
    """Return True if the node is an intermediate concept/cluster, not an ICD code."""
    if node_id in _SKIP_TARGETS:
        return True
    if any(node_id.startswith(p) for p in _CONCEPT_PREFIXES):
        return True
    # Concept nodes contain no digit — real ICD codes always do (E11, N18, etc.)
    return not any(c.isdigit() for c in node_id)


def _build_kg_path(kg: nx.DiGraph, seed: str, target: str) -> str:
    """Return a human-readable traversal path string."""
    try:
        path = nx.shortest_path(kg, seed, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return f"{seed} → {target}"

    parts: list[str] = []
    for i in range(len(path) - 1):
        src, tgt = path[i], path[i + 1]
        relation = kg.edges[src, tgt].get("relation", "related_to")
        parts.append(f"{src} → [{relation}] → {tgt}")

    return " → ".join(parts) if parts else f"{seed} → {target}"


def traverse_from_codes(
    icd_codes: list[str],
    kg: nx.DiGraph,
    max_hops: int = 2,
    barrier_codes: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Traverse the KG from seed ICD codes and return gap flag candidates.

    Uses BFS up to max_hops, multiplying edge confidences cumulatively.
    barrier_codes: submitted codes that block further expansion — paths that pass
    *through* a barrier are considered already covered and are not expanded.
    Returns results sorted by confidence descending.
    """
    if not icd_codes:
        return []

    seeds = [c for c in icd_codes if kg.has_node(c)]
    if not seeds:
        return []

    barriers = barrier_codes or set()

    # visited: node_id → (best_confidence, path_seed)
    visited: dict[str, tuple[float, str]] = {}

    for seed in seeds:
        frontier: list[tuple[str, float, str]] = [(seed, 1.0, seed)]
        for _ in range(max_hops):
            next_frontier: list[tuple[str, float, str]] = []
            for node, cum_conf, path_seed in frontier:
                for neighbor in kg.successors(node):
                    edge_conf: float = kg.edges[node, neighbor].get("confidence", 0.5)
                    new_conf = round(cum_conf * edge_conf, 4)
                    if neighbor in seeds:
                        continue
                    if neighbor not in visited or visited[neighbor][0] < new_conf:
                        visited[neighbor] = (new_conf, path_seed)
                    # Do not expand through barriers (submitted codes) or concept nodes —
                    # they are stepping stones only, not clinical findings to expand from
                    if neighbor not in barriers and not _is_concept_node(neighbor):
                        next_frontier.append((neighbor, new_conf, path_seed))
            frontier = next_frontier

    results: list[dict[str, Any]] = []
    for node_id, (confidence, path_seed) in visited.items():
        if _is_concept_node(node_id):
            continue
        if confidence < _MIN_CONFIDENCE:
            continue
        if node_id in icd_codes:
            continue

        node_data = kg.nodes.get(node_id, {})
        display = node_data.get("display", node_id)
        kg_path = _build_kg_path(kg, path_seed, node_id)

        try:
            path = nx.shortest_path(kg, path_seed, node_id)
            last_edge = kg.edges[path[-2], path[-1]]
            reason = last_edge.get("evidence", f"KG path from {path_seed} to {node_id}")
        except Exception:
            reason = f"KG traversal from {path_seed} to {node_id}"

        results.append({
            "suggested_code": node_id,
            "display": display,
            "confidence": confidence,
            "reason": reason,
            "kg_path": kg_path,
            "action": "Review and document if applicable",
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def _validate_existing_codes(
    icd_codes: list[str],
    kg: nx.DiGraph,
) -> list[dict[str, Any]]:
    """Return validation records for the submitted ICD codes."""
    validated: list[dict[str, Any]] = []
    for code in icd_codes:
        if kg.has_node(code):
            node_data = kg.nodes[code]
            validated.append({
                "code": code,
                "display": node_data.get("display", code),
                "confidence": 0.95,
                "status": "confirmed",
            })
        else:
            validated.append({
                "code": code,
                "display": code,
                "confidence": 0.70,
                "status": "unverified",
            })
    return validated


def _determine_note_quality(gap_flags: list[dict], existing_codes: list[str]) -> str:
    """Assign note_quality based on gap flag count and existing code coverage."""
    if not gap_flags:
        return "complete"
    if len(gap_flags) >= 2:
        return "partial"
    # One flag — partial if at least one existing code was validated
    return "partial"


def enrich_note(request: EnrichRequest, kg: nx.DiGraph) -> EnrichResponse:
    """Run the full enrichment pipeline on a clinical note.

    Steps:
      1. Extract NER entities from all note sections
      2. Merge NER-derived codes with submitted existing_icd_codes
      3. Traverse KG to find gap flag candidates
      4. Filter out codes already submitted by the provider
      5. Validate submitted codes
      6. Determine note_quality
      7. Return EnrichResponse with audit trail
    """
    t_start = time.perf_counter()

    # 1. NER across all sections
    all_text = " ".join(s.text for s in request.note_sections)
    entities = extract_entities(all_text)

    # 2. Gap seeds = NER-confirmed ICD codes that are NOT already submitted.
    #    The gap is between what the note text implies and what the provider coded.
    #    Submitted codes act as traversal barriers — paths through documented
    #    conditions are considered already covered.
    submitted_set = set(request.existing_icd_codes)
    ner_codes = list(dict.fromkeys(
        e["icd"] for e in entities
        if e.get("icd") and kg.has_node(e["icd"])
    ))
    unsubmitted_ner_seeds = [c for c in ner_codes if c not in submitted_set]

    # 3. KG traversal from unsubmitted NER seeds only
    candidates = traverse_from_codes(
        unsubmitted_ner_seeds, kg, max_hops=2, barrier_codes=submitted_set
    )

    # 4. Filter out codes already in the submitted list
    gap_flags = [c for c in candidates if c["suggested_code"] not in submitted_set]

    # 5. Validate submitted codes
    existing_codes_validated = _validate_existing_codes(request.existing_icd_codes, kg)

    # 6. Note quality
    note_quality = _determine_note_quality(gap_flags, request.existing_icd_codes)

    # 7. IMO terminology — collect all CUIs from NER entities and query
    all_cuis = {e["cui"] for e in entities if e.get("cui")}
    imo_raw = get_imo_suggestion(all_cuis)
    imo_terminology = IMOTerminology(**imo_raw) if imo_raw else None

    nodes_traversed = len(unsubmitted_ner_seeds) + len(candidates)
    processing_ms = round((time.perf_counter() - t_start) * 1000, 2)

    return EnrichResponse(
        encounter_id=request.encounter_id,
        status="enriched" if gap_flags else "confirmed",
        existing_codes_validated=existing_codes_validated,
        gap_flags=gap_flags,
        imo_terminology=imo_terminology,
        audit_trail={
            "kg_version": KG_VERSION,
            "nodes_traversed": nodes_traversed,
            "processing_ms": processing_ms,
            "ontology_sources": ONTOLOGY_SOURCES,
        },
        note_quality=note_quality,
    )
