"""Dictionary-based NER for clinical entity extraction."""
from typing import Any

ENTITY_DICTIONARY: dict[str, dict[str, Any]] = {
    # Diabetes
    "type 2 diabetes": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "type 2 diabetes mellitus": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "t2dm": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "uncontrolled diabetes": {"cui": "C0011860", "icd": "E11.65", "domain": "diabetes"},
    "uncontrolled type 2 diabetes": {"cui": "C0011860", "icd": "E11.65", "domain": "diabetes"},
    "diabetes mellitus": {"cui": "C0011860", "icd": "E11.9", "domain": "diabetes"},
    "diabetic nephropathy": {"cui": "C1561335", "icd": "E11.65", "domain": "diabetes"},
    "diabetic neuropathy": {"cui": "C0011882", "icd": "E11.40", "domain": "diabetes"},
    "diabetic retinopathy": {"cui": "C0011884", "icd": "E11.319", "domain": "diabetes"},
    "hba1c": {"cui": "C0392885", "icd": None, "domain": "lab"},
    # Renal
    "chronic kidney disease": {"cui": "C0403447", "icd": "N18.9", "domain": "renal"},
    "ckd": {"cui": "C0403447", "icd": "N18.9", "domain": "renal"},
    "ckd stage 3": {"cui": "C0403447", "icd": "N18.3", "domain": "renal"},
    "renal insufficiency": {"cui": "C0403447", "icd": "N18.9", "domain": "renal"},
    "bilateral leg swelling": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    "leg edema": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    "bilateral edema": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    "edema": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    "leg swelling": {"cui": "C0013604", "icd": "R60.0", "domain": "symptom"},
    # Cardiovascular
    "hypertension": {"cui": "C0020538", "icd": "I10", "domain": "cardiovascular"},
    "high blood pressure": {"cui": "C0020538", "icd": "I10", "domain": "cardiovascular"},
    "heart failure": {"cui": "C0018801", "icd": "I50.9", "domain": "cardiovascular"},
    "chf": {"cui": "C0018801", "icd": "I50.9", "domain": "cardiovascular"},
    "congestive heart failure": {"cui": "C0018801", "icd": "I50.9", "domain": "cardiovascular"},
    "atrial fibrillation": {"cui": "C0004238", "icd": "I48.91", "domain": "cardiovascular"},
    "afib": {"cui": "C0004238", "icd": "I48.91", "domain": "cardiovascular"},
    "coronary artery disease": {"cui": "C0010054", "icd": "I25.10", "domain": "cardiovascular"},
    "cad": {"cui": "C0010054", "icd": "I25.10", "domain": "cardiovascular"},
    # Obesity / Metabolic
    "obesity": {"cui": "C0028754", "icd": "E66.9", "domain": "metabolic"},
    "obese": {"cui": "C0028754", "icd": "E66.9", "domain": "metabolic"},
    "morbid obesity": {"cui": "C0028754", "icd": "E66.01", "domain": "metabolic"},
    "nafld": {"cui": "C0400966", "icd": "K76.0", "domain": "metabolic"},
    "sleep apnea": {"cui": "C0520679", "icd": "G47.33", "domain": "respiratory"},
    "obstructive sleep apnea": {"cui": "C0520679", "icd": "G47.33", "domain": "respiratory"},
    # Medications
    "metformin": {"cui": "C0025598", "icd": None, "domain": "medication"},
    "lisinopril": {"cui": "C0065374", "icd": None, "domain": "medication"},
    "insulin": {"cui": "C0021641", "icd": None, "domain": "medication"},
    "amlodipine": {"cui": "C0051696", "icd": None, "domain": "medication"},
    "atorvastatin": {"cui": "C0286651", "icd": None, "domain": "medication"},
    # Symptoms
    "fatigue": {"cui": "C0015672", "icd": "R53.83", "domain": "symptom"},
    "shortness of breath": {"cui": "C0013404", "icd": "R06.00", "domain": "symptom"},
    "dyspnea": {"cui": "C0013404", "icd": "R06.00", "domain": "symptom"},
    "chest pain": {"cui": "C0008031", "icd": "R07.9", "domain": "symptom"},
    "nausea": {"cui": "C0027497", "icd": "R11.0", "domain": "symptom"},
}

# Sort by length descending so longer phrases match before shorter substrings
_SORTED_TERMS = sorted(ENTITY_DICTIONARY.keys(), key=len, reverse=True)


def extract_entities(text: str) -> list[dict[str, Any]]:
    """Extract medical entities from clinical text using dictionary lookup.

    Returns a list of dicts with keys: term, cui, icd, domain.
    Longer phrases are matched before shorter ones to avoid substring conflicts.
    """
    lower = text.lower()
    found: list[dict[str, Any]] = []
    matched_spans: list[tuple[int, int]] = []

    for term in _SORTED_TERMS:
        start = 0
        while True:
            idx = lower.find(term, start)
            if idx == -1:
                break
            end = idx + len(term)
            # Skip if this span overlaps a previously matched span
            if any(s <= idx < e or s < end <= e for s, e in matched_spans):
                start = end
                continue
            matched_spans.append((idx, end))
            entry = ENTITY_DICTIONARY[term]
            found.append({"term": term, **entry})
            start = end

    return found
