# FUTURE.md — Post-Demo Upgrade Path

> This file documents what is deliberately deferred from the demo/MVP.
> Do not implement these in the hackathon build.

---

## Phase 2: Real Infrastructure (post-hackathon)

### Replace NetworkX with Neo4j
- Load full PrimeKG (17K diseases, 4M edges) into Neo4j
- Cypher queries replace NetworkX traversal
- Expected latency: 20-80ms per query (acceptable for production)
- Docker Compose setup: `neo4j:5.x` + `clinicgraph-api`

### Replace Dictionary NER with scispaCy
- `en_core_sci_lg` model (~800MB) for proper clinical NER
- QuickUMLS for CUI mapping from full UMLS metathesaurus
- Expected improvement: catch informal language ("sugar problems" → T2DM)

### Add Real Suki Webhook Integration
- Subscribe to Suki `note_complete` webhook (requires Suki Early Access)
- POST from Suki → ClinicalGraph → enriched JSON → back to EHR
- Auth: HMAC webhook signature verification

### HIPAA Compliance Layer
- PHI stripping before KG traversal
- Audit log to append-only store (S3 / CloudWatch)
- BAA with infrastructure providers

### Multi-Ambient-AI Support
- Nuance DAX note format adapter
- Abridge note format adapter
- Generic FHIR DiagnosticReport adapter

---

## Phase 3: Enterprise Features

### Health-System-Specific KG
- Load org's own population data as graph overlay
- "Your diabetic patients over 65 historically miss CKD coding 34% of the time"
- Population-level pattern detection

### Real-Time Confidence Calibration
- Feedback loop: did the clinician accept the gap flag?
- Confidence scores updated from acceptance rates
- Specialty-specific tuning

### Revenue Impact Calculator
- Per encounter: estimated HCC revenue recovered
- Per health system: annualized undercoding gap
- Integration with RCM systems

---

## KG Expansion Roadmap

| Phase | Domains | Nodes | Edges | Source |
|---|---|---|---|---|
| Demo (now) | Diabetes, CV, Obesity | ~150 | ~400 | Curated |
| MVP | + Respiratory, Renal, Mental Health | ~500 | ~2,000 | PrimeKG filtered |
| v1.0 | All major chronic disease clusters | ~5,000 | ~50,000 | PrimeKG full |
| v2.0 | Full biomedical | 17,080 | 4,050,249 | PrimeKG + UMLS |

*Last updated: April 2026*
