from fastapi.testclient import TestClient

from sentinel.model import SentinelModel
from sentinel.model_store import save_model
from service.app import create_app


def test_api_health_readiness_scoring_and_metadata(synthetic_trips, tmp_path):
    model = SentinelModel().fit(
        synthetic_trips,
        synthetic_trips["isFraud"].astype(int),
        metrics_dir=tmp_path,
    )
    save_model(model, tmp_path)
    app = create_app(model_dir=tmp_path, model=model)
    trip = synthetic_trips.iloc[0]
    payload = {
        "trip": {
            field: (trip[field].isoformat() if field == "event_ts" else trip[field].item()
                    if hasattr(trip[field], "item") else trip[field])
            for field in [
                "driver_id", "trip_id", "event_ts", "store_id", "TransactionAmt",
                "dist1", "C1", "C2", "C5", "C13", "D1", "D10", "V12", "V53",
                "V258", "geofence_dist_m", "emulator_flag", "gps_mock_flag",
                "rooted_device_flag", "incentive_trip_count", "refund_count_30d",
                "payout_change_72h", "off_hours_flag", "trip_distance_km",
                "trip_duration_min", "new_device_flag",
            ]
        }
    }
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").json()["status"] == "ready"
        response = client.post("/v1/score", json=payload)
        assert response.status_code == 200
        assert 0 <= response.json()["score"] <= 10
        assert client.get("/v1/model/info").json()["feature_count"] > 20
        assert "auc_roc" in client.get("/v1/model/metrics").json()
        oversized = client.post("/v1/score/batch", json=[payload] * 1001)
        assert oversized.status_code == 413
