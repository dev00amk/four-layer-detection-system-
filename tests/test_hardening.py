import pandas as pd

from sentinel.anomaly import ensemble_score, evaluate_fatal_signals
from sentinel.features import ROLLING_FEATURES, build_behavioral_features
from sentinel.schema import EnrichedTrip, SchemaValidationError, validate_dataframe


def test_impossible_speed_is_fatal_and_overrides_score():
    fatal = evaluate_fatal_signals({"trip_distance_km": 100, "trip_duration_min": 10})
    score, is_fatal = ensemble_score(0, 0, 0, 0, fatal_signals=fatal)
    assert (score, is_fatal) == (10, True)


def test_rolling_features_are_finite():
    trips = pd.DataFrame(
        {
            "driver_id": ["D1", "D1", "D1"],
            "trip_id": ["T1", "T2", "T3"],
            "store_id": ["S1", "S1", "S2"],
            "event_ts": pd.to_datetime(["2025-01-01", "2025-01-08", "2025-02-10"]),
            "payout_change_72h": [0, 1, 0],
            "refund_count_30d": [0, 2, 1],
            "geofence_dist_m": [10.0, 20.0, 30.0],
        }
    )
    featured = build_behavioral_features(trips)
    assert set(ROLLING_FEATURES).issubset(featured.columns)
    assert featured[ROLLING_FEATURES].notna().all().all()


def test_schema_reports_missing_columns():
    try:
        validate_dataframe(pd.DataFrame([{"trip_id": "T1"}]), EnrichedTrip)
    except SchemaValidationError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("Expected schema validation to fail")
