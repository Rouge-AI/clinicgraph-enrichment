"""RED-17 to RED-24: Core enrichment pipeline tests."""
import json
import pytest
from pathlib import Path

from app.enricher import enrich_note
from app.graph_loader import load_graph
from app.models import EnrichRequest

DATA_DIR = Path(__file__).parent.parent / "data" / "demo"


@pytest.fixture(scope="module")
def kg():
    return load_graph()


def _load_note(filename: str) -> EnrichRequest:
    with open(DATA_DIR / filename) as f:
        return EnrichRequest(**json.load(f))


# RED-17: note_gap → returns at least 1 gap_flag
def test_note_gap_returns_gap_flags(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    assert len(result.gap_flags) >= 1


# RED-18: note_clean → returns 0 gap_flags, note_quality = "complete"
def test_note_clean_no_gap_flags(kg):
    req = _load_note("note_clean.json")
    result = enrich_note(req, kg)
    assert result.gap_flags == []
    assert result.note_quality == "complete"


# RED-19: note_partial → returns gap_flags, note_quality = "partial"
def test_note_partial_has_flags_and_partial_quality(kg):
    req = _load_note("note_partial.json")
    result = enrich_note(req, kg)
    assert len(result.gap_flags) >= 1
    assert result.note_quality == "partial"


# RED-20: existing codes are present in validated list
def test_existing_codes_in_validated_list(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    validated_codes = [v["code"] for v in result.existing_codes_validated]
    for code in req.existing_icd_codes:
        assert code in validated_codes


# RED-21: confidence scores are sorted descending
def test_gap_flags_sorted_descending(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    scores = [f["confidence"] for f in result.gap_flags]
    assert scores == sorted(scores, reverse=True)


# RED-22: processing_ms is recorded and > 0
def test_processing_ms_recorded(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    assert result.audit_trail["processing_ms"] > 0


# RED-23: gap_flag includes kg_path string
def test_gap_flag_has_kg_path(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    for flag in result.gap_flags:
        assert "kg_path" in flag
        assert isinstance(flag["kg_path"], str)
        assert len(flag["kg_path"]) > 0


# RED-24: gap_flag includes human-readable reason
def test_gap_flag_has_reason(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    for flag in result.gap_flags:
        assert "reason" in flag
        assert isinstance(flag["reason"], str)
        assert len(flag["reason"]) > 0


# RED-25 (IMO): note_gap enrichment returns imo_terminology field that is not None
def test_note_gap_imo_terminology_not_none(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    assert hasattr(result, "imo_terminology")
    assert result.imo_terminology is not None


# RED-26 (IMO): note_clean enrichment — imo_terminology field exists (may be None)
def test_note_clean_imo_terminology_field_exists(kg):
    req = _load_note("note_clean.json")
    result = enrich_note(req, kg)
    assert hasattr(result, "imo_terminology")


# RED-27 (IMO): imo_terminology on note_gap contains all required fields
def test_note_gap_imo_terminology_fields(kg):
    req = _load_note("note_gap.json")
    result = enrich_note(req, kg)
    imo = result.imo_terminology
    assert imo is not None
    assert imo.imo_term == "Diabetic Nephropathy with Edema"
    assert imo.imo_code == "IMO-44210"
    assert imo.icd10_suggestion == "E11.65"
    assert 0.0 <= imo.confidence <= 1.0
    assert isinstance(imo.reasoning, str) and len(imo.reasoning) > 0
    assert imo.source in ("mock", "imo_api")
    assert isinstance(imo.action, str) and len(imo.action) > 0
