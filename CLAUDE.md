# ClinicalGraph — Claude Code Handoff Document

> **Read this first. This is the single source of truth for the project.**
> All decisions, constraints, and scope are defined here.
> Do not deviate from scope without explicit instruction.

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Repo name** | `clinicgraph-enrichment` |
| **Project name** | ClinicalGraph |
| **Tagline** | *"What ambient AI hears, ClinicalGraph understands."* |
| **Purpose** | Hackathon demo + MVP of a KG-enrichment middleware for ambient AI clinical documentation |
| **Target** | API middleware only — no frontend beyond a basic FastAPI docs page (`/docs`) |

---

## 2. Problem Statement (for context — do not over-engineer)

Ambient AI (Suki, Abridge, Nuance DAX) transcribes doctor-patient conversations into
LOINC-structured clinical notes with ~98.5% transcription accuracy. The gap is **documentation
completeness and coding accuracy** — not transcription.

**The specific gap:**
- Diagnoses discussed in the encounter but not captured as structured ICD-10/HCC codes
- Comorbidities implied by documented conditions (e.g. T2DM + leg edema → likely CKD) not flagged
- $3,000/member/year average HCC undercoding loss (RAAPID 2026)
- $4B+ annual audit recoupments from defensible-but-uncoded diagnoses (HIT Consultant 2026)

**What ClinicalGraph does:**
Takes a Suki-formatted ambient note (LOINC-structured JSON), traverses a lightweight
ontology-grounded knowledge graph, and returns:
1. Validated/confirmed ICD-10 codes with confidence scores
2. Flagged missing diagnoses (gap flags) with KG path evidence
3. A simple audit trail (which ontology node triggered the flag)

**What ClinicalGraph does NOT do:**
- Clinical decision support (no treatment recommendations)
- Auth / HIPAA compliance layers (deferred, not in demo scope)
- Real-time audio processing (Suki handles that)
- Any frontend UI beyond FastAPI `/docs`

---

## 3. Technology Stack

```
Language:       Python 3.11+
Framework:      FastAPI
Graph DB:       NetworkX (in-memory, no Neo4j for demo — latency reason)
NER:            QuickUMLS or simple dictionary lookup (scispaCy is too heavy for demo)
Ontology data:  Curated subset only — see Section 6
Testing:        pytest + pytest-cov (red-green TDD)
Docs:           FastAPI /docs (Swagger UI — this IS the demo interface)
Package mgr:    uv or pip
```

**Why NetworkX instead of Neo4j for demo:**
Neo4j startup + query latency kills a live demo. NetworkX loads a pre-built graph in memory
at startup. Full Neo4j is the MVP upgrade path, documented in FUTURE.md.

---

## 4. Repository Structure

```
clinicgraph-enrichment/
├── CLAUDE.md                  ← This file (agent reads first)
├── README.md                  ← Setup instructions
├── FUTURE.md                  ← Post-demo upgrade path
├── pyproject.toml
├── pytest.ini
│
├── app/
│   ├── __init__.py
│   ├── main.py                ← FastAPI app, /docs is the demo UI
│   ├── models.py              ← Pydantic request/response models
│   ├── enricher.py            ← Core enrichment logic (KG traversal)
│   ├── graph_loader.py        ← Loads KG into NetworkX at startup
│   └── ner.py                 ← Entity extraction from note text
│
├── data/
│   ├── kg/
│   │   ├── nodes.json         ← Curated disease/condition nodes
│   │   ├── edges.json         ← Relationships between nodes
│   │   └── icd_map.json       ← CUI → ICD-10 code mapping
│   └── demo/
│       ├── note_gap.json      ← Demo note 1: has coding gaps (should get enriched)
│       ├── note_clean.json    ← Demo note 2: already well-coded (should pass through)
│       └── note_partial.json  ← Demo note 3: partial gaps (mixed enrichment)
│
├── tests/
│   ├── conftest.py
│   ├── test_models.py         ← Pydantic validation tests
│   ├── test_ner.py            ← Entity extraction tests
│   ├── test_graph.py          ← KG traversal logic tests
│   ├── test_enricher.py       ← Core enrichment pipeline tests
│   └── test_api.py            ← FastAPI endpoint integration tests
│
└── scripts/
    └── build_kg.py            ← One-time script to build nodes/edges from curated data
```

---

## 5. API Design

### POST `/v1/enrich`

**Request:**
```json
{
  "encounter_id": "enc_001",
  "note_sections": [
    {
      "loinc_code": "10164-2",
      "loinc_display": "History of Present Illness",
      "text": "Patient is a 67-year-old male with uncontrolled Type 2 diabetes on metformin 500mg. Presenting with fatigue and bilateral leg swelling for 3 weeks."
    },
    {
      "loinc_code": "11450-4",
      "loinc_display": "Problem List",
      "text": "1. Type 2 Diabetes Mellitus, uncontrolled\n2. Hypertension"
    },
    {
      "loinc_code": "10183-2",
      "loinc_display": "Discharge Medications",
      "text": "Metformin 500mg twice daily\nLisinopril 10mg daily"
    }
  ],
  "existing_icd_codes": ["E11.65", "I10"]
}
```

**Response:**
```json
{
  "encounter_id": "enc_001",
  "status": "enriched",
  "existing_codes_validated": [
    {"code": "E11.65", "display": "T2DM with hyperglycemia", "confidence": 0.95, "status": "confirmed"}
  ],
  "gap_flags": [
    {
      "suggested_code": "N18.3",
      "display": "Chronic kidney disease, stage 3",
      "confidence": 0.78,
      "reason": "T2DM (E11.65) + bilateral edema pattern suggests CKD comorbidity",
      "kg_path": "E11.65 → [associated_with] → Diabetic_Nephropathy → [maps_to] → N18.3",
      "action": "Review and document if applicable"
    },
    {
      "suggested_code": "Z79.4",
      "display": "Long-term use of insulin",
      "confidence": 0.55,
      "reason": "Uncontrolled T2DM on oral agent — insulin transition common",
      "kg_path": "E11.65 + uncontrolled → [treatment_pathway] → insulin_therapy → Z79.4",
      "action": "Verify medication list"
    }
  ],
  "audit_trail": {
    "kg_version": "clinicgraph-v0.1-demo",
    "nodes_traversed": 8,
    "processing_ms": 42,
    "ontology_sources": ["SNOMED-subset", "ICD10-CM-subset", "PrimeKG-subset"]
  },
  "note_quality": "partial"
}
```

### GET `/v1/health`
Returns service status and KG stats.

### GET `/v1/graph/stats`
Returns node count, edge count, ontology sources loaded.

### POST `/v1/demo/{scenario}`
Convenience endpoint for demos. Accepts `gap`, `clean`, `partial`.
Loads pre-built demo notes and runs enrichment. Perfect for live demos.

---

## 6. Knowledge Graph Scope — CRITICAL

**Token/latency constraint: Do NOT load full PrimeKG (17K diseases, 4M edges).**
**This will kill demo latency and exceed memory.**

### Curated Subset Strategy (recommended)

Build a hand-curated graph of ~150 nodes and ~400 edges covering:

**Domain 1: Diabetes + Comorbidities** (highest demo value)
- T2DM → CKD, Diabetic Neuropathy, Diabetic Retinopathy, CAD
- Uncontrolled T2DM → HbA1c monitoring gap, Insulin transition flag
- Metformin contraindication with CKD stage 3b+

**Domain 2: Cardiovascular**
- Hypertension → CKD, Heart Failure, Atrial Fibrillation
- CHF → Edema, BNP monitoring gap

**Domain 3: Obesity/Metabolic**
- Obesity → T2DM, Sleep Apnea, NAFLD
- BMI documentation → HCC E66 capture flag

**Why these 3 domains:**
- Covers the demo note scenarios
- Highest HCC revenue impact conditions
- Well-documented in open ontology sources
- All representable in ~150 nodes

### Data Sources (all free, no download account needed)

| Source | What to use | URL |
|---|---|---|
| ICD-10-CM tabular | Condition → code mapping | https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2025/ |
| SNOMED CT relationships (subset) | Condition relationships | https://browser.ihtsdotools.org/ (browse, don't download full) |
| PrimeKG disease relationships | Disease-disease edges | https://github.com/mims-harvard/PrimeKG — use `kg.csv`, filter to your 3 domains |
| UMLS CUI browser | CUI lookups | https://uts.nlm.nih.gov/uts/umls/home (free account required) |

**Practical approach:** Hand-code `nodes.json` and `edges.json` from the above sources.
This takes ~2 hours but gives you full control over latency and accuracy.
`scripts/build_kg.py` documents the schema for future automated loading.

---

## 7. Demo Notes — Sources for LOINC-Structured Notes

### Where to Get Real LOINC-Structured Clinical Note Examples

| Source | URL | What's there |
|---|---|---|
| MIMIC-III (requires credentialing) | https://physionet.org/content/mimiciii/1.4/ | Real de-identified notes |
| MIMIC-IV Clinical Notes | https://physionet.org/content/mimic-iv-note/2.2/ | Newer, structured notes |
| MTSamples | https://www.mtsamples.com/ | Free transcription samples by specialty |
| NLP4Clinical GitHub | https://github.com/ncats/ncats-common-cold | LOINC-mapped examples |
| Suki API docs example | https://developer.suki.ai/documentation/ambient-documentation | Suki output format |

### Recommended Approach for Your 3 Demo Notes

Do NOT use real patient data. Build synthetic notes using MTSamples as language reference,
structured into Suki's LOINC JSON format. See `data/demo/` files.

**Note 1 — `note_gap.json` (HAS GAPS — should be enriched)**
- T2DM uncontrolled + bilateral leg edema + Metformin
- ICD codes submitted: E11.65, I10
- Expected KG output: flags N18.3 (CKD), suggests E11.649 specificity upgrade
- Demo story: "Suki captured the conversation perfectly. ClinicalGraph found $3,000 in missing HCC codes."

**Note 2 — `note_clean.json` (ALREADY GOOD — should pass through)**
- T2DM with CKD stage 3, properly coded, metformin reviewed and held
- ICD codes submitted: E11.65, N18.3, Z79.4, I10
- Expected KG output: all validated, no gaps, `note_quality: "complete"`
- Demo story: "When the documentation is already complete, ClinicalGraph confirms it. No false positives."

**Note 3 — `note_partial.json` (PARTIAL — mixed result)**
- Hypertension + obesity + fatigue, BMI documented but E66 not coded
- ICD codes submitted: I10, R53.83
- Expected KG output: flags E66.9 (obesity), Z68.x (BMI), possible sleep apnea flag
- Demo story: "Partial documentation — ClinicalGraph finds the gaps, not everything."

---

## 8. TDD Plan — Red-Green Cycle

**Philosophy:** Write the test first. Watch it fail (red). Implement minimum code to pass (green).
Refactor only after green. Every function has a test before it has an implementation.

### Test File Execution Order

```
pytest tests/test_models.py      # 1. Data shapes first
pytest tests/test_ner.py         # 2. Entity extraction
pytest tests/test_graph.py       # 3. KG traversal logic
pytest tests/test_enricher.py    # 4. Core pipeline
pytest tests/test_api.py         # 5. Full integration
pytest --cov=app tests/          # 6. Coverage check
```

### Test Cases — Designed for Maximum Demo Value

#### `test_models.py`
```python
# RED-01: valid note request parses correctly
# RED-02: missing encounter_id raises ValidationError
# RED-03: empty note_sections raises ValidationError
# RED-04: invalid loinc_code format is accepted (no strict validation — demo simplicity)
# RED-05: response model contains all required fields
```

#### `test_ner.py`
```python
# RED-06: "Type 2 diabetes" → extracts CUI C0011860
# RED-07: "bilateral leg swelling" → extracts CUI C0013604 (edema)
# RED-08: "metformin 500mg" → extracts drug entity metformin
# RED-09: text with no medical entities → returns empty list (no crash)
# RED-10: mixed text extracts multiple entities correctly
```

#### `test_graph.py`
```python
# RED-11: graph loads successfully at startup (node count > 0)
# RED-12: T2DM node has edges to CKD node
# RED-13: 2-hop traversal from E11.65 finds N18.3
# RED-14: traversal returns confidence score between 0 and 1
# RED-15: traversal of unknown node returns empty list (no crash)
# RED-16: audit trail contains kg_path string
```

#### `test_enricher.py`
```python
# RED-17: note_gap → returns at least 1 gap_flag
# RED-18: note_clean → returns 0 gap_flags, note_quality = "complete"
# RED-19: note_partial → returns gap_flags, note_quality = "partial"
# RED-20: existing codes are present in validated list
# RED-21: confidence scores are sorted descending
# RED-22: processing_ms is recorded and > 0
# RED-23: gap_flag includes kg_path string
# RED-24: gap_flag includes human-readable reason
```

#### `test_api.py`
```python
# RED-25: POST /v1/enrich with valid payload returns 200
# RED-26: POST /v1/enrich with invalid payload returns 422
# RED-27: GET /v1/health returns 200 and kg_loaded: true
# RED-28: GET /v1/graph/stats returns node_count and edge_count
# RED-29: POST /v1/demo/gap returns enriched result with gap_flags
# RED-30: POST /v1/demo/clean returns complete result with no gap_flags
# RED-31: POST /v1/demo/partial returns partial result
# RED-32: response time for /v1/demo/* under 500ms (latency test)
```

**Total: 32 test cases. All red before any implementation.**

---

## 9. Implementation Order (for Claude Code)

Follow this order strictly. Do not skip ahead.

```
Step 1:  Write ALL tests (they will all fail — that's correct)
Step 2:  Implement models.py (makes RED-01 to RED-05 green)
Step 3:  Implement ner.py with dictionary-based lookup (makes RED-06 to RED-10 green)
Step 4:  Build data/kg/nodes.json and edges.json manually (curated subset)
Step 5:  Implement graph_loader.py (makes RED-11 green)
Step 6:  Implement graph traversal in enricher.py (makes RED-12 to RED-16 green)
Step 7:  Implement full enrichment pipeline (makes RED-17 to RED-24 green)
Step 8:  Build demo notes in data/demo/
Step 9:  Implement main.py with all endpoints (makes RED-25 to RED-32 green)
Step 10: Run full coverage report — target 85%+
Step 11: Write README.md with curl examples for demo
```

---

## 10. Agent Instructions for Claude Code

When Claude Code reads this file, follow these rules:

1. **Always run tests before implementing** — write the test file completely, run it, confirm all red, then implement.

2. **NER strategy — use dictionary lookup, NOT scispaCy** — scispaCy model download is 800MB and kills demo setup. Use a curated dictionary in `ner.py` with ~100 key medical terms mapped to CUIs. Extendable later.

3. **KG loading — NetworkX only** — Load `nodes.json` and `edges.json` at FastAPI startup using `@app.on_event("startup")`. No external DB connections.

4. **Latency target** — `/v1/enrich` must respond in under 500ms on a laptop. If any function takes > 100ms, flag it.

5. **Demo endpoint is critical** — `/v1/demo/{scenario}` is what gets shown live. It must be bulletproof. Load fixtures from `data/demo/` at startup too.

6. **Do not implement auth** — skip all authentication, token management, rate limiting. Out of scope.

7. **Do not implement HIPAA compliance features** — no PHI stripping, no audit logging to disk. Out of scope for demo.

8. **FastAPI /docs IS the frontend** — configure the app with a good title, description, and tags so the Swagger UI looks professional for the demo.

9. **Keep imports minimal** — only `fastapi`, `networkx`, `pydantic`, `pytest`. Do not add heavy ML libraries.

10. **If a test is failing for the wrong reason** — fix the test, not the implementation, if the test is wrong. Tests are the spec.

---

## 11. KG Feasibility Answer

> "Is it feasible to create multiple knowledge graphs for all the KG layers?"

**Short answer: No, not for the demo. One curated graph, three domains.**

**Reasoning:**
- Full PrimeKG = 4M edges. NetworkX in-memory = ~2GB RAM. Demo machine will struggle.
- Multiple graphs = multiple query paths = latency compounds. Each hop adds ~10-50ms.
- For the demo, one graph with 3 domain clusters (~150 nodes, ~400 edges) loads in <50ms and queries in <10ms per traversal.

**What you CAN do that looks like multiple graphs:**
- Tag nodes with `source: ["primekg", "snomed", "icd10cm"]`
- The audit trail shows `ontology_sources: ["SNOMED-subset", "ICD10-CM-subset", "PrimeKG-subset"]`
- Visually, judges see three ontology sources contributing. Architecturally, it's one graph.
- This is honest — PrimeKG itself is a merged graph of 20 sources.

---

## 12. What I Need From You (the human)

Before Claude Code can complete the demo data:

1. **UMLS account** — Free at https://uts.nlm.nih.gov/uts/signup-login
   Needed to verify CUI mappings. Takes 1-2 days for approval.
   Workaround: use the curated CUI dictionary in `ner.py` (already provided in skeleton).

2. **Python 3.11+ installed** — confirm with `python --version`

3. **Nothing else** — all data is either hand-curated or from free sources.
   No API keys needed for the demo. Suki API access is mocked.

---

## 13. Demo Script (for the live presentation)

```
1. Open browser to http://localhost:8000/docs

2. Show GET /v1/graph/stats
   → "Our knowledge graph has 147 nodes and 389 edges across 3 clinical domains,
      sourced from SNOMED CT, ICD-10-CM, and PrimeKG subsets."

3. Show POST /v1/demo/clean
   → "When documentation is already complete, ClinicalGraph confirms it.
      No false positives. note_quality: complete."

4. Show POST /v1/demo/gap
   → "This is Suki's output for a diabetic patient with leg swelling.
      Transcription was perfect. But ClinicalGraph found N18.3 — CKD stage 3 —
      missing from the coding. That's a $3,000 per year HCC gap."
   → Point to kg_path in response. "This is traceable. Not a black-box guess."

5. Show POST /v1/demo/partial
   → "Partial documentation. Two gaps found, one confirmed.
      note_quality: partial."

6. Show POST /v1/enrich with custom payload
   → "Any ambient AI that outputs LOINC-structured JSON can plug in here.
      One endpoint. Platform neutral."
```

---

## 14. File Checklist for Claude Code to Generate

- [ ] `pyproject.toml`
- [ ] `pytest.ini`
- [ ] `app/__init__.py`
- [ ] `app/main.py`
- [ ] `app/models.py`
- [ ] `app/enricher.py`
- [ ] `app/graph_loader.py`
- [ ] `app/ner.py`
- [ ] `tests/conftest.py`
- [ ] `tests/test_models.py`
- [ ] `tests/test_ner.py`
- [ ] `tests/test_graph.py`
- [ ] `tests/test_enricher.py`
- [ ] `tests/test_api.py`
- [ ] `data/kg/nodes.json`
- [ ] `data/kg/edges.json`
- [ ] `data/kg/icd_map.json`
- [ ] `data/demo/note_gap.json`
- [ ] `data/demo/note_clean.json`
- [ ] `data/demo/note_partial.json`
- [ ] `scripts/build_kg.py`
- [ ] `README.md`
- [ ] `FUTURE.md`

---

*Last updated: April 2026 | Scope: Hackathon Demo + MVP | Version: 0.1*
