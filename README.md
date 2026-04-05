# ClinicalGraph

> *What ambient AI hears, ClinicalGraph understands.*

KG-enrichment middleware for ambient clinical AI documentation. Takes a Suki-formatted ambient note (LOINC-structured JSON), traverses a lightweight ontology-grounded knowledge graph, and returns validated ICD-10 codes, gap flags with KG path evidence, IMO preferred terminology, and a full audit trail.

---

## Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn networkx pydantic httpx
```

### 2. Start the server

```bash
cd clinicgraph-enrichment
uvicorn app.main:app --reload --port 8000
```

### 3. Open the demo UI

```
http://localhost:8000/docs
```

The knowledge graph (120 nodes, 130 edges) loads into memory at startup in < 50ms.

---

## Demo Endpoints

### Check the knowledge graph

```bash
curl http://localhost:8000/v1/graph/stats
```

```json
{
  "node_count": 120,
  "edge_count": 130,
  "kg_version": "clinicgraph-v0.1-demo",
  "ontology_sources": ["SNOMED-subset", "ICD10-CM-subset", "PrimeKG-subset"],
  "domains": ["cardiovascular", "diabetes", "metabolic", "renal", "respiratory", "symptom"]
}
```

---

### Scenario 1 — CLEAN (no false positives)

Fully coded T2DM + CKD encounter. ClinicalGraph confirms — zero flags.

```bash
curl -X POST http://localhost:8000/v1/demo/clean
```

```json
{
  "encounter_id": "enc_demo_clean_001",
  "status": "confirmed",
  "gap_flags": [],
  "note_quality": "complete",
  "imo_terminology": null,
  "audit_trail": { "processing_ms": 2.1 }
}
```

**Demo line:** *"When documentation is already complete, ClinicalGraph confirms it. No false positives."*

---

### Scenario 2 — GAP (the money shot)

T2DM + bilateral edema. Suki coded E11.65 and I10. ClinicalGraph finds the missing CKD code **and** surfaces the IMO preferred terminology to make the documentation stick.

```bash
curl -X POST http://localhost:8000/v1/demo/gap
```

```json
{
  "encounter_id": "enc_demo_gap_001",
  "status": "enriched",
  "gap_flags": [
    {
      "suggested_code": "N18.3",
      "display": "Chronic kidney disease, stage 3",
      "confidence": 0.55,
      "reason": "Peripheral edema can indicate CKD-related fluid retention",
      "kg_path": "R60.0 → [associated_with] → N18.3",
      "action": "Review and document if applicable"
    }
  ],
  "imo_terminology": {
    "imo_term": "Diabetic Nephropathy with Edema",
    "imo_code": "IMO-44210",
    "icd10_suggestion": "E11.65",
    "confidence": 0.78,
    "reasoning": "T2DM + bilateral edema cluster aligns with IMO preferred term for diabetic nephropathy. Ensures documentation specificity for HCC risk adjustment.",
    "source": "mock",
    "matched_cuis": ["C0011860", "C0013604"],
    "action": "Consider updating note to IMO preferred term for coding specificity"
  },
  "note_quality": "partial",
  "audit_trail": {
    "kg_version": "clinicgraph-v0.1-demo",
    "processing_ms": 3.8,
    "ontology_sources": ["SNOMED-subset", "ICD10-CM-subset", "PrimeKG-subset"]
  }
}
```

**Demo line:** *"Two symptoms. The KG finds the clinical relationship — N18.3, a $3,000 HCC gap. IMO gives the right language to document it: 'Diabetic Nephropathy with Edema'. The note, the code, and the terminology are all aligned."*

---

### Scenario 3 — PARTIAL (mixed result)

Obesity + HTN. BMI 36.2 documented but obesity and OSA not coded.

```bash
curl -X POST http://localhost:8000/v1/demo/partial
```

```json
{
  "encounter_id": "enc_demo_partial_001",
  "status": "enriched",
  "gap_flags": [
    {
      "suggested_code": "E11.9",
      "display": "Type 2 diabetes mellitus, unspecified",
      "confidence": 0.85,
      "reason": "Obesity is the primary modifiable risk factor for T2DM via insulin resistance",
      "kg_path": "E66.9 → [risk_factor_for] → E11.9"
    },
    {
      "suggested_code": "G47.33",
      "display": "Obstructive sleep apnea (adult)(pediatric)",
      "confidence": 0.82,
      "reason": "Obesity is the strongest risk factor for obstructive sleep apnea",
      "kg_path": "E66.9 → [associated_with] → G47.33"
    }
  ],
  "imo_terminology": null,
  "note_quality": "partial"
}
```

**Demo line:** *"Partial documentation — ClinicalGraph finds the gaps, not everything."*

---

### Live custom payload

```bash
curl -X POST http://localhost:8000/v1/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "encounter_id": "enc_live_001",
    "note_sections": [
      {
        "loinc_code": "10164-2",
        "loinc_display": "History of Present Illness",
        "text": "67-year-old male with uncontrolled Type 2 diabetes and bilateral leg swelling for 3 weeks. On metformin 500mg. Blood pressure 158/94."
      },
      {
        "loinc_code": "11450-4",
        "loinc_display": "Problem List",
        "text": "1. Type 2 Diabetes Mellitus, uncontrolled\n2. Hypertension"
      }
    ],
    "existing_icd_codes": ["E11.65", "I10"]
  }'
```

**Demo line:** *"Any ambient AI that outputs LOINC-structured JSON can plug in here. One endpoint. Platform neutral."*

---

### Health check

```bash
curl http://localhost:8000/v1/health
```

```json
{"status": "ok", "kg_loaded": true, "kg_version": "clinicgraph-v0.1-demo"}
```

---

## Run Tests

```bash
pip install pytest httpx
pytest tests/ -v
```

Expected: **43 passed**.

Coverage report:

```bash
python -m coverage run -m pytest tests/ -q
python -m coverage report --include="app/*" --show-missing
```

Expected: **94%+ coverage**.

---

## Project Structure

```
clinicgraph-enrichment/
├── app/
│   ├── main.py          ← FastAPI app + all endpoints
│   ├── models.py        ← Pydantic models (incl. IMOTerminology)
│   ├── enricher.py      ← KG traversal + enrichment pipeline
│   ├── graph_loader.py  ← Loads NetworkX graph at startup
│   ├── ner.py           ← Dictionary-based clinical NER
│   └── imo_client.py    ← IMO terminology client (mock + real API)
├── data/
│   ├── kg/
│   │   ├── nodes.json        ← 120 curated disease/condition nodes
│   │   ├── edges.json        ← 130 relationships (3 clinical domains)
│   │   └── icd_map.json      ← CUI → ICD-10 mappings
│   └── demo/
│       ├── note_gap.json     ← T2DM + edema, missing CKD + IMO match
│       ├── note_clean.json   ← Fully coded, zero false positives
│       └── note_partial.json ← Obesity + HTN, missing E66.9/G47.33
├── tests/
│   ├── conftest.py
│   ├── test_models.py   ← RED-01 to RED-05
│   ├── test_ner.py      ← RED-06 to RED-10
│   ├── test_graph.py    ← RED-11 to RED-16
│   ├── test_enricher.py ← RED-17 to RED-27
│   ├── test_api.py      ← RED-25 to RED-35
│   └── test_imo.py      ← RED-36 to RED-40
└── scripts/
    └── build_kg.py      ← KG schema validator + future build reference
```

---

## Knowledge Graph

One in-memory graph, three clinical domains:

| Domain | Key relationships |
|---|---|
| **Diabetes** | T2DM → CKD, Neuropathy, Retinopathy, Nephropathy; edema pattern → CKD flag |
| **Cardiovascular** | HTN → CKD, CHF, AFib, CAD; AFib → stroke risk |
| **Obesity/Metabolic** | Obesity → T2DM, OSA, NAFLD; BMI documentation → E66.9 flag |

Nodes tagged with `sources: ["icd10cm", "snomed-subset", "primekg-subset"]` — three ontology sources, one low-latency in-memory graph. Startup: **< 50ms**. Per-query: **< 10ms**.

---

## IMO Terminology Integration

After KG traversal, ClinicalGraph queries for the IMO preferred term that best matches the CUI cluster extracted from the note.

| Condition | Behaviour |
|---|---|
| `IMO_API_KEY` not set | Uses mock DB, `source: "mock"` |
| `IMO_API_KEY` set, API succeeds | Uses real API, `source: "imo_api"` |
| `IMO_API_KEY` set, API fails | Falls back to mock, `source: "mock"` |

To enable the real IMO API:

```bash
export IMO_API_KEY=your_key_here
uvicorn app.main:app --reload --port 8000
```

The `imo_terminology` field is `null` when no matching CUI cluster is found (e.g. the clean note scenario).

---

## How It Works

```
Note text (LOINC JSON)
        ↓
   NER extraction          ← dictionary lookup, ~50 medical terms → CUIs + ICD codes
        ↓
 Unsubmitted NER codes     ← gap = what note implies vs. what's coded
        ↓
   KG traversal (BFS)      ← up to 2 hops, confidence × confidence
        ↓
   Filter + rank           ← remove submitted codes, sort by confidence
        ↓
   IMO terminology lookup  ← CUI cluster → preferred term + ICD suggestion
        ↓
   Gap flags + IMO term    ← kg_path shows which edge fired; IMO adds clinical language
      + audit trail
```

Submitted ICD codes act as **traversal barriers** — paths through already-documented conditions are not expanded, eliminating false positives on well-coded notes.

---

## Demo Script

| Step | Action | What to say |
|---|---|---|
| 1 | `GET /v1/graph/stats` | "120 nodes, 130 edges across 3 clinical domains — SNOMED, ICD-10-CM, PrimeKG." |
| 2 | `POST /v1/demo/clean` | "Fully coded note — ClinicalGraph confirms it. Zero false positives." |
| 3 | `POST /v1/demo/gap` | "Two symptoms. The KG finds N18.3 — a $3,000 HCC gap. IMO surfaces 'Diabetic Nephropathy with Edema' — the right language to document it. Traceable via `kg_path`." |
| 4 | `POST /v1/demo/partial` | "Obesity patient — E66.9 and G47.33 not coded. ClinicalGraph finds the gaps." |
| 5 | `POST /v1/enrich` | "Any LOINC-structured ambient AI output. One endpoint. Platform neutral." |

---

*Version 0.1 — Hackathon Demo | See FUTURE.md for Neo4j upgrade path*
