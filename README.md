# ClinicalGraph

> *What ambient AI hears, ClinicalGraph understands.*

KG-enrichment middleware for ambient clinical AI documentation. Takes a Suki-formatted ambient note (LOINC-structured JSON), traverses a lightweight ontology-grounded knowledge graph, and returns validated ICD-10 codes, gap flags with KG path evidence, and an audit trail.

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

### Scenario 1 — GAP (the money shot)

T2DM + bilateral edema. Suki coded E11.65 and I10. ClinicalGraph finds missing CKD code.

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
  "note_quality": "partial",
  "audit_trail": {
    "kg_version": "clinicgraph-v0.1-demo",
    "processing_ms": 3.2,
    "ontology_sources": ["SNOMED-subset", "ICD10-CM-subset", "PrimeKG-subset"]
  }
}
```

**Demo line:** *"Suki captured the conversation perfectly. ClinicalGraph found N18.3 — CKD stage 3 — missing from the coding. That's a $3,000 per year HCC gap. And it's traceable — not a black-box guess."*

---

### Scenario 2 — CLEAN (no false positives)

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
  "audit_trail": { "processing_ms": 2.1 }
}
```

**Demo line:** *"When documentation is already complete, ClinicalGraph confirms it. No false positives."*

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

Expected: **32 passed**.

Coverage report:

```bash
python -m coverage run -m pytest tests/ -q
python -m coverage report --include="app/*" --show-missing
```

Expected: **94% coverage**.

---

## Project Structure

```
clinicgraph-enrichment/
├── app/
│   ├── main.py          ← FastAPI app + all endpoints
│   ├── models.py        ← Pydantic request/response models
│   ├── enricher.py      ← KG traversal + enrichment pipeline
│   ├── graph_loader.py  ← Loads NetworkX graph at startup
│   └── ner.py           ← Dictionary-based clinical NER
├── data/
│   ├── kg/
│   │   ├── nodes.json   ← 120 curated disease/condition nodes
│   │   ├── edges.json   ← 130 relationships (3 clinical domains)
│   │   └── icd_map.json ← CUI → ICD-10 mappings
│   └── demo/
│       ├── note_gap.json     ← T2DM + edema, missing CKD
│       ├── note_clean.json   ← Fully coded, zero false positives
│       └── note_partial.json ← Obesity + HTN, missing E66.9/G47.33
├── tests/               ← 32 TDD tests, 94% coverage
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

## How It Works

```
Note text (LOINC JSON)
        ↓
   NER extraction          ← dictionary lookup, ~50 medical terms
        ↓
 Unsubmitted NER codes     ← gap = what note implies vs. what's coded
        ↓
   KG traversal (BFS)      ← up to 2 hops, confidence × confidence
        ↓
   Filter + rank           ← remove submitted codes, sort by confidence
        ↓
   Gap flags + audit trail ← kg_path shows exactly which edge fired
```

Submitted ICD codes act as **traversal barriers** — paths through already-documented conditions are not expanded, eliminating false positives on well-coded notes.

---

*Version 0.1 — Hackathon Demo | See FUTURE.md for Neo4j upgrade path*
