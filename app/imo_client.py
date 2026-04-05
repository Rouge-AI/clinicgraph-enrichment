"""IMO (Intelligent Medical Objects) terminology client.

Environment behaviour:
  - IMO_API_KEY not set  → mock DB only, source: "mock"
  - IMO_API_KEY set, API succeeds → real API, source: "imo_api"
  - IMO_API_KEY set, API fails    → fallback to mock, source: "mock"
"""
import os
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

# ---------------------------------------------------------------------------
# Mock database — keyed by frozenset of CUIs
# ---------------------------------------------------------------------------

IMO_MOCK_DB: dict[frozenset, dict[str, Any]] = {
    frozenset(["C0011860", "C0013604"]): {
        "imo_term": "Diabetic Nephropathy with Edema",
        "imo_code": "IMO-44210",
        "icd10_suggestion": "E11.65",
        "confidence": 0.78,
        "reasoning": (
            "T2DM + bilateral edema cluster aligns with IMO preferred term for diabetic "
            "nephropathy. Ensures documentation specificity for HCC risk adjustment."
        ),
        "source": "mock",
        "matched_cuis": ["C0011860", "C0013604"],
    },
}


def _lookup_mock(cuis: set[str]) -> dict[str, Any] | None:
    """Return the best matching mock entry for a set of CUIs, or None."""
    best: dict[str, Any] | None = None
    best_overlap = 0
    for key, entry in IMO_MOCK_DB.items():
        overlap = len(key & cuis)
        if overlap == len(key) and overlap > best_overlap:
            best = entry
            best_overlap = overlap
    if best is None:
        return None
    result = dict(best)
    result["action"] = "Consider updating note to IMO preferred term for coding specificity"
    return result


def _lookup_api(cuis: set[str], api_key: str) -> dict[str, Any] | None:
    """Call the real IMO API. Returns None on any failure."""
    if httpx is None:
        return None
    try:
        response = httpx.get(
            "https://api.imohealth.com/terminology/v1/suggest",
            params={"cuis": ",".join(sorted(cuis))},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=2.0,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("suggestion"):
            return None
        suggestion = data["suggestion"]
        suggestion["source"] = "imo_api"
        suggestion.setdefault(
            "action",
            "Consider updating note to IMO preferred term for coding specificity",
        )
        return suggestion
    except Exception:
        return None


def get_imo_suggestion(cuis: set[str]) -> dict[str, Any] | None:
    """Return the best IMO terminology suggestion for a set of UMLS CUIs.

    Falls back to mock when the API key is absent or the API call fails.
    Returns None when no matching cluster is found.
    """
    if not cuis:
        return None

    api_key = os.environ.get("IMO_API_KEY")

    if api_key:
        result = _lookup_api(cuis, api_key)
        if result is not None:
            return result

    return _lookup_mock(cuis)
