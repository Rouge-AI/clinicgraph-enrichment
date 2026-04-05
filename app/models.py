"""Pydantic request/response models for ClinicalGraph API."""
from typing import Any, Optional
from pydantic import BaseModel, field_validator


class NoteSection(BaseModel):
    loinc_code: str
    loinc_display: str
    text: str


class EnrichRequest(BaseModel):
    encounter_id: str
    note_sections: list[NoteSection]
    existing_icd_codes: list[str] = []

    @field_validator("note_sections")
    @classmethod
    def note_sections_not_empty(cls, v: list[NoteSection]) -> list[NoteSection]:
        if not v:
            raise ValueError("note_sections must not be empty")
        return v


class IMOTerminology(BaseModel):
    imo_term: str
    imo_code: str
    icd10_suggestion: str
    confidence: float
    reasoning: str
    source: str  # "mock" or "imo_api"
    matched_cuis: list[str]
    action: str = "Consider updating note to IMO preferred term for coding specificity"


class EnrichResponse(BaseModel):
    encounter_id: str
    status: str
    existing_codes_validated: list[dict[str, Any]]
    gap_flags: list[dict[str, Any]]
    audit_trail: dict[str, Any]
    note_quality: str
    imo_terminology: Optional[IMOTerminology] = None
