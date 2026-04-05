"""RED-01 to RED-05: Pydantic model validation tests."""
import pytest
from pydantic import ValidationError

from app.models import EnrichRequest, EnrichResponse, NoteSection


# RED-01: valid note request parses correctly
def test_valid_note_request_parses(valid_payload):
    req = EnrichRequest(**valid_payload)
    assert req.encounter_id == "enc_001"
    assert len(req.note_sections) == 3
    assert req.existing_icd_codes == ["E11.65", "I10"]


# RED-02: missing encounter_id raises ValidationError
def test_missing_encounter_id_raises():
    with pytest.raises(ValidationError):
        EnrichRequest(
            note_sections=[
                {"loinc_code": "10164-2", "loinc_display": "HPI", "text": "Some text"}
            ],
            existing_icd_codes=["E11.65"],
        )


# RED-03: empty note_sections raises ValidationError
def test_empty_note_sections_raises():
    with pytest.raises(ValidationError):
        EnrichRequest(
            encounter_id="enc_001",
            note_sections=[],
            existing_icd_codes=[],
        )


# RED-04: invalid loinc_code format is accepted (no strict validation — demo simplicity)
def test_non_standard_loinc_code_accepted():
    req = EnrichRequest(
        encounter_id="enc_test",
        note_sections=[
            {"loinc_code": "CUSTOM-99", "loinc_display": "Custom Section", "text": "Some text"}
        ],
        existing_icd_codes=[],
    )
    assert req.note_sections[0].loinc_code == "CUSTOM-99"


# RED-05: response model contains all required fields
def test_response_model_required_fields():
    response = EnrichResponse(
        encounter_id="enc_001",
        status="enriched",
        existing_codes_validated=[],
        gap_flags=[],
        audit_trail={
            "kg_version": "clinicgraph-v0.1-demo",
            "nodes_traversed": 0,
            "processing_ms": 10,
            "ontology_sources": [],
        },
        note_quality="complete",
    )
    assert response.encounter_id == "enc_001"
    assert response.status == "enriched"
    assert response.note_quality == "complete"
    assert "kg_version" in response.audit_trail
    assert "processing_ms" in response.audit_trail
