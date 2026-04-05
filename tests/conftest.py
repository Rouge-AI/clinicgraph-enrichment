import pytest
from fastapi.testclient import TestClient


VALID_NOTE_PAYLOAD = {
    "encounter_id": "enc_001",
    "note_sections": [
        {
            "loinc_code": "10164-2",
            "loinc_display": "History of Present Illness",
            "text": (
                "Patient is a 67-year-old male with uncontrolled Type 2 diabetes on "
                "metformin 500mg. Presenting with fatigue and bilateral leg swelling for 3 weeks."
            ),
        },
        {
            "loinc_code": "11450-4",
            "loinc_display": "Problem List",
            "text": "1. Type 2 Diabetes Mellitus, uncontrolled\n2. Hypertension",
        },
        {
            "loinc_code": "10183-2",
            "loinc_display": "Discharge Medications",
            "text": "Metformin 500mg twice daily\nLisinopril 10mg daily",
        },
    ],
    "existing_icd_codes": ["E11.65", "I10"],
}


@pytest.fixture
def valid_payload() -> dict:
    return VALID_NOTE_PAYLOAD


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c
