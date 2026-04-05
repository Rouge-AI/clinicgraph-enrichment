"""Pydantic request/response models for ClinicalGraph API."""
from typing import Any
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


class EnrichResponse(BaseModel):
    encounter_id: str
    status: str
    existing_codes_validated: list[dict[str, Any]]
    gap_flags: list[dict[str, Any]]
    audit_trail: dict[str, Any]
    note_quality: str
