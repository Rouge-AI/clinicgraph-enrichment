"""RED-06 to RED-10: NER / entity extraction tests."""
from app.ner import extract_entities


# RED-06: "Type 2 diabetes" → extracts CUI C0011860
def test_extract_type2_diabetes():
    entities = extract_entities("Patient has Type 2 diabetes.")
    cuis = [e["cui"] for e in entities]
    assert "C0011860" in cuis


# RED-07: "bilateral leg swelling" → extracts CUI C0013604 (edema)
def test_extract_bilateral_leg_swelling():
    entities = extract_entities("Patient presents with bilateral leg swelling.")
    cuis = [e["cui"] for e in entities]
    assert "C0013604" in cuis


# RED-08: "metformin 500mg" → extracts drug entity metformin
def test_extract_metformin():
    entities = extract_entities("Patient is on metformin 500mg twice daily.")
    terms = [e["term"] for e in entities]
    assert any("metformin" in t for t in terms)


# RED-09: text with no medical entities → returns empty list (no crash)
def test_no_entities_returns_empty():
    entities = extract_entities("The weather is nice today.")
    assert entities == []


# RED-10: mixed text extracts multiple entities correctly
def test_mixed_text_multiple_entities():
    text = "Patient has hypertension and obesity. On lisinopril 10mg."
    entities = extract_entities(text)
    assert len(entities) >= 2
    cuis = [e["cui"] for e in entities]
    assert "C0020538" in cuis   # hypertension
    assert "C0028754" in cuis   # obesity
