"""RED-25 to RED-32: FastAPI endpoint integration tests."""
import time
import pytest


# RED-25: POST /v1/enrich with valid payload returns 200
def test_enrich_valid_payload_returns_200(client, valid_payload):
    response = client.post("/v1/enrich", json=valid_payload)
    assert response.status_code == 200


# RED-26: POST /v1/enrich with invalid payload returns 422
def test_enrich_invalid_payload_returns_422(client):
    response = client.post("/v1/enrich", json={"bad": "data"})
    assert response.status_code == 422


# RED-27: GET /v1/health returns 200 and kg_loaded: true
def test_health_returns_ok_and_kg_loaded(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["kg_loaded"] is True


# RED-28: GET /v1/graph/stats returns node_count and edge_count
def test_graph_stats_has_counts(client):
    response = client.get("/v1/graph/stats")
    assert response.status_code == 200
    body = response.json()
    assert "node_count" in body
    assert "edge_count" in body
    assert body["node_count"] > 0


# RED-29: POST /v1/demo/gap returns enriched result with gap_flags
def test_demo_gap_returns_gap_flags(client):
    response = client.post("/v1/demo/gap")
    assert response.status_code == 200
    body = response.json()
    assert len(body["gap_flags"]) >= 1


# RED-30: POST /v1/demo/clean returns complete result with no gap_flags
def test_demo_clean_returns_complete(client):
    response = client.post("/v1/demo/clean")
    assert response.status_code == 200
    body = response.json()
    assert body["note_quality"] == "complete"
    assert body["gap_flags"] == []


# RED-31: POST /v1/demo/partial returns partial result
def test_demo_partial_returns_partial(client):
    response = client.post("/v1/demo/partial")
    assert response.status_code == 200
    body = response.json()
    assert body["note_quality"] == "partial"
    assert len(body["gap_flags"]) >= 1


# RED-32: response time for /v1/demo/* under 500ms (latency test)
def test_demo_endpoints_under_500ms(client):
    for scenario in ("gap", "clean", "partial"):
        start = time.perf_counter()
        response = client.post(f"/v1/demo/{scenario}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200, f"/v1/demo/{scenario} returned {response.status_code}"
        assert elapsed_ms < 500, f"/v1/demo/{scenario} took {elapsed_ms:.0f}ms (> 500ms limit)"
