"""ClinicalGraph FastAPI application — /docs is the demo UI."""
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import networkx as nx
from fastapi import FastAPI, HTTPException

from app.enricher import KG_VERSION, ONTOLOGY_SOURCES, enrich_note
from app.graph_loader import load_graph
from app.models import EnrichRequest, EnrichResponse

# ---------------------------------------------------------------------------
# Startup state
# ---------------------------------------------------------------------------

_DEMO_DIR = Path(__file__).parent.parent / "data" / "demo"

_state: dict[str, Any] = {
    "kg": None,
    "demo_notes": {},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load KG once at startup
    _state["kg"] = load_graph()

    # Pre-load demo notes
    for scenario in ("gap", "clean", "partial"):
        path = _DEMO_DIR / f"note_{scenario}.json"
        with open(path) as f:
            _state["demo_notes"][scenario] = EnrichRequest(**json.load(f))

    yield
    # Nothing to tear down for in-memory graph


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ClinicalGraph",
    description=(
        "**KG-enrichment middleware for ambient clinical AI documentation.**\n\n"
        "Takes a Suki-formatted ambient note (LOINC-structured JSON), traverses a "
        "lightweight ontology-grounded knowledge graph, and returns:\n"
        "- Validated/confirmed ICD-10 codes with confidence scores\n"
        "- Flagged missing diagnoses (gap flags) with KG path evidence\n"
        "- A simple audit trail (which ontology node triggered the flag)\n\n"
        "*What ambient AI hears, ClinicalGraph understands.*"
    ),
    version="0.1.0",
    lifespan=lifespan,
)


def _kg() -> nx.DiGraph:
    if _state["kg"] is None:
        raise HTTPException(status_code=503, detail="Knowledge graph not loaded")
    return _state["kg"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/v1/enrich",
    response_model=EnrichResponse,
    summary="Enrich a clinical note",
    tags=["Enrichment"],
)
def enrich(request: EnrichRequest) -> EnrichResponse:
    """
    Accept a LOINC-structured ambient note and return:
    - Validated existing ICD-10 codes
    - Gap flags for missing diagnoses with KG path evidence
    - Audit trail
    """
    return enrich_note(request, _kg())


@app.get(
    "/v1/health",
    summary="Service health check",
    tags=["Operations"],
)
def health() -> dict[str, Any]:
    """Returns service status and whether the KG is loaded."""
    kg = _state["kg"]
    return {
        "status": "ok",
        "kg_loaded": kg is not None,
        "kg_version": KG_VERSION,
    }


@app.get(
    "/v1/graph/stats",
    summary="Knowledge graph statistics",
    tags=["Operations"],
)
def graph_stats() -> dict[str, Any]:
    """Returns node count, edge count, and ontology sources loaded."""
    kg = _kg()
    domains = sorted({
        data.get("domain", "unknown")
        for _, data in kg.nodes(data=True)
    })
    return {
        "node_count": kg.number_of_nodes(),
        "edge_count": kg.number_of_edges(),
        "kg_version": KG_VERSION,
        "ontology_sources": ONTOLOGY_SOURCES,
        "domains": domains,
    }


@app.post(
    "/v1/demo/{scenario}",
    response_model=EnrichResponse,
    summary="Run a pre-built demo scenario",
    tags=["Demo"],
)
def demo(scenario: str) -> EnrichResponse:
    """
    Run enrichment on a pre-built demo note. Scenarios:

    - **gap** — T2DM + bilateral edema, missing CKD code. Shows gap detection.
    - **clean** — Fully coded T2DM + CKD encounter. Shows zero false positives.
    - **partial** — Obesity + HTN, missing obesity/OSA codes. Shows partial enrichment.
    """
    if scenario not in _state["demo_notes"]:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown scenario '{scenario}'. Choose from: gap, clean, partial",
        )
    return enrich_note(_state["demo_notes"][scenario], _kg())
