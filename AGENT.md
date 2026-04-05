# AGENT.md — ClinicalGraph Agent Instructions

> Place this file at the root of the `clinicgraph-enrichment` repo.
> Claude Code reads this automatically on every session.

---

## Your Role

You are the implementation agent for **ClinicalGraph**, a KG-enrichment middleware
for ambient clinical AI documentation. You have full context in `CLAUDE.md`.

**Read CLAUDE.md first on every session before writing any code.**

---

## Mandatory Workflow — Never Skip

```
1. READ  → CLAUDE.md (project context)
2. CHECK → which tests are currently red: `pytest tests/ --tb=no -q`
3. PLAN  → state which test(s) you are making green this session
4. CODE  → minimum implementation to pass the target test(s)
5. RUN   → `pytest tests/ --tb=short -q`
6. VERIFY → confirm targeted tests are now green, no regressions
7. REPORT → list what's green, what's still red
```

---

## Hard Rules

### DO
- Write tests before implementation (TDD)
- Keep functions small and single-purpose
- Use type hints on every function signature
- Use Pydantic models for all API I/O
- Load the KG once at startup, reuse in-memory
- Return meaningful error messages in API responses
- Keep `/v1/demo/{scenario}` working at all times — it's the demo

### DO NOT
- Add scispaCy, spaCy, transformers, or any ML model downloads
- Connect to any external database (Neo4j, PostgreSQL, Redis)
- Implement authentication or authorization
- Add HIPAA compliance features (PHI stripping, audit logging to disk)
- Add frontend code (HTML, React, CSS) — FastAPI /docs is the UI
- Import anything not in: fastapi, networkx, pydantic, pytest, httpx
- Load full PrimeKG (too large — use curated subset in data/kg/)
- Skip the red phase — all 32 tests must be written and failing before any implementation

---

## Session Start Checklist

When you begin a new session, run this first:

```bash
# 1. Check Python version
python --version  # needs 3.11+

# 2. Install dependencies
pip install fastapi uvicorn networkx pydantic pytest pytest-cov httpx

# 3. Run all tests to see current state
pytest tests/ --tb=no -q 2>/dev/null || echo "Tests not yet written"

# 4. Check KG data exists
ls data/kg/  # nodes.json edges.json icd_map.json

# 5. Check demo data exists
ls data/demo/  # note_gap.json note_clean.json note_partial.json
```

---

## KG Data Contract

### nodes.json schema
```json
[
  {
    "id": "E11.65",
    "type": "icd10",
    "display": "Type 2 diabetes mellitus with hyperglycemia",
    "cui": "C0011860",
    "domain": "diabetes",
    "hcc_relevant": true,
    "sources": ["icd10cm", "snomed-subset"]
  }
]
```

### edges.json schema
```json
[
  {
    "source": "E11.65",
    "target": "N18.3",
    "relation": "associated_with",
    "confidence": 0.78,
    "evidence": "Diabetic nephropathy comorbidity pattern",
    "sources": ["primekg-subset", "snomed-subset"]
  }
]
```

### icd_map.json schema
```json
{
  "C0011860": "E11.65",
  "C0403447": "N18.3",
  "C0028754": "E66.9"
}
```

---

## NER Dictionary Contract

In `app/ner.py`, maintain a dictionary with these entries at minimum:

```python
ENTITY_DICTIONARY = {
    # Diabetes
    "type 2 diabetes": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "type 2 diabetes mellitus": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "t2dm": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "uncontrolled diabetes": {"cui": "C0011860", "icd": "E11.65", "domain": "diabetes"},
    "metformin": {"cui": "C0025598", "icd": None, "domain": "medication"},
    # Renal
    "chronic kidney disease": {"cui": "C0403447", "icd": "N18.9", "domain": "renal"},
    "ckd": {"cui": "C0403447", "icd": "N18.9", "domain": "renal"},
    "bilateral leg swelling": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    "leg edema": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    "edema": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    # Cardiovascular
    "hypertension": {"cui": "C0020538", "icd": "I10", "domain": "cardiovascular"},
    "heart failure": {"cui": "C0018801", "icd": "I50.9", "domain": "cardiovascular"},
    "atrial fibrillation": {"cui": "C0004238", "icd": "I48.91", "domain": "cardiovascular"},
    # Obesity
    "obesity": {"cui": "C0028754", "icd": "E66.9", "domain": "metabolic"},
    "obese": {"cui": "C0028754", "icd": "E66.9", "domain": "metabolic"},
    # Medications
    "lisinopril": {"cui": "C0065374", "icd": None, "domain": "medication"},
    "insulin": {"cui": "C0021641", "icd": None, "domain": "medication"},
    # Symptoms
    "fatigue": {"cui": "C0015672", "icd": "R53.83", "domain": "symptom"},
    "shortness of breath": {"cui": "C0013404", "icd": "R06.00", "domain": "symptom"},
}
```

---

## Latency Targets

| Endpoint | Target | Fail threshold |
|---|---|---|
| `GET /v1/health` | < 10ms | > 50ms |
| `GET /v1/graph/stats` | < 20ms | > 100ms |
| `POST /v1/enrich` | < 300ms | > 500ms |
| `POST /v1/demo/*` | < 200ms | > 500ms |

Test RED-32 enforces the 500ms threshold. The enricher itself should be < 100ms.

---

## Demo Survival Rules

These must ALWAYS be true before ending any session:

1. `POST /v1/demo/gap` returns `note_quality: "partial"` or `"enriched"` with at least 1 gap_flag
2. `POST /v1/demo/clean` returns `note_quality: "complete"` with 0 gap_flags
3. `POST /v1/demo/partial` returns `note_quality: "partial"` with 1-2 gap_flags
4. `GET /v1/health` returns `{"status": "ok", "kg_loaded": true}`
5. `pytest tests/test_api.py -v` passes all tests

If any of the above break, fix them before ending the session.

---

*Agent version: 0.1 | Project: clinicgraph-enrichment | Scope: Demo + MVP*
