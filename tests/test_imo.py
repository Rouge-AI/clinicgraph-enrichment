"""RED-36 to RED-40: IMO client tests."""
import pytest
from unittest.mock import patch, MagicMock

from app.imo_client import get_imo_suggestion


# RED-36: get_imo_suggestion with {C0011860, C0013604} returns non-None
def test_known_cui_cluster_returns_suggestion():
    result = get_imo_suggestion({"C0011860", "C0013604"})
    assert result is not None


# RED-37: get_imo_suggestion with unrelated CUIs returns None
def test_unknown_cui_cluster_returns_none():
    result = get_imo_suggestion({"C9999999", "C8888888"})
    assert result is None


# RED-38: returned suggestion contains all required fields
def test_suggestion_has_required_fields():
    result = get_imo_suggestion({"C0011860", "C0013604"})
    assert result is not None
    for field in ("imo_term", "imo_code", "icd10_suggestion",
                  "confidence", "reasoning", "source", "matched_cuis", "action"):
        assert field in result, f"Missing field: {field}"


# RED-39: source is "mock" when IMO_API_KEY not set
def test_source_is_mock_without_api_key():
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("IMO_API_KEY", None)
        result = get_imo_suggestion({"C0011860", "C0013604"})
    assert result is not None
    assert result["source"] == "mock"


# RED-40: API failure falls back to mock
def test_api_failure_falls_back_to_mock():
    with patch.dict("os.environ", {"IMO_API_KEY": "fake-key"}):
        with patch("app.imo_client.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("Connection refused")
            result = get_imo_suggestion({"C0011860", "C0013604"})
    assert result is not None
    assert result["source"] == "mock"
