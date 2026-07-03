"""Scoring API tests via fastapi.testclient against a real persisted model."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="api extra not installed")

from fastapi.testclient import TestClient  # noqa: E402

from sentinel.model import SentinelModel  # noqa: E402
from sentinel.model_store import load_metadata, load_model, save_model  # noqa: E402


@pytest.fixture(scope="module")
def api_client(tmp_path_factory):
    """TestClient over an app whose lifespan loads a freshly trained artifact."""
    from tests.conftest import make_synthetic_trips

    model_dir = tmp_path_factory.mktemp("model-store")
    frame = make_synthetic_trips()
    model = SentinelModel().fit(
        frame, frame["isFraud"].astype(int), metrics_path=model_dir / "metrics.json"
    )
    save_model(model, model_dir=model_dir)

    import service.app as service_app

    original_load_model = service_app.load_model
    original_load_metadata = service_app.load_metadata
    service_app.load_model = lambda: load_model(model_dir)
    service_app.load_metadata = lambda: load_metadata(model_dir)
    try:
        with TestClient(service_app.app) as client:
            yield client
    finally:
        service_app.load_model = original_load_model
        service_app.load_metadata = original_load_metadata


def _trip(**overrides) -> dict:
    trip = {"trip_id": "T900001", "driver_id": "D900001"}
    trip.update(overrides)
    return trip


def test_health_and_ready(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}
    assert api_client.get("/ready").json() == {"status": "ready"}


def test_score_single_trip(api_client):
    response = api_client.post("/v1/score", json=_trip())
    assert response.status_code == 200
    (result,) = response.json()["results"]
    assert result["trip_id"] == "T900001"
    assert 0 <= result["score"] <= 10
    assert result["band"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL", "CRITICAL+"}


def test_fatal_telemetry_scores_critical(api_client):
    trip = _trip(trip_distance_km=400.0, trip_duration_min=30.0)  # 800 kph
    (result,) = api_client.post("/v1/score", json=trip).json()["results"]
    assert result["is_fatal"] is True
    assert result["score"] == 10
    assert result["band"] == "CRITICAL+"
    assert "F01" in result["fatal_signal_ids"]


def test_batch_scoring_and_offline_inputs(api_client):
    trips = [
        _trip(trip_id="T1", driver_id="D1"),
        _trip(trip_id="T2", driver_id="D2", sql_hits=10, graph_flag=1, ring_size=5),
    ]
    response = api_client.post("/v1/score/batch", json={"trips": trips})
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 2
    # Precomputed offline-layer inputs must raise the ensemble score.
    assert results[1]["score"] >= results[0]["score"]


def test_batch_size_limit_enforced(api_client):
    trips = [_trip(trip_id=f"T{i}", driver_id=f"D{i}") for i in range(1001)]
    response = api_client.post("/v1/score/batch", json={"trips": trips})
    assert response.status_code == 422


def test_invalid_trip_rejected(api_client):
    response = api_client.post("/v1/score", json=_trip(trip_distance_km=-5))
    assert response.status_code == 422


def test_model_info_and_metrics(api_client):
    info = api_client.get("/v1/model/info").json()
    assert info["feature_count"] == len(SentinelModel.XGB_FEATURES)
    assert set(info["lib_versions"]) == {"python", "xgboost", "sklearn"}
    metrics = api_client.get("/v1/model/metrics").json()
    assert set(metrics) == {"auc_roc", "auc_pr", "rows", "fraud_rate"}


def test_correlation_id_echoed(api_client):
    response = api_client.get("/health", headers={"x-correlation-id": "abc-123"})
    assert response.headers["x-correlation-id"] == "abc-123"
