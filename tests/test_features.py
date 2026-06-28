import pandas as pd

from sentinel.features import BEHAVIORAL_FEATURES, build_behavioral_features


def test_behavioral_features_are_row_aligned_and_finite():
    frame = pd.DataFrame(
        {
            "driver_id": ["D1", "D1", "D2"],
            "trip_id": ["T1", "T2", "T3"],
            "store_id": ["S1", "S1", "S1"],
            "event_ts": pd.to_datetime(["2025-01-01 23:00", "2025-01-02 12:00", "2025-01-02 01:00"]),
            "payout_change_72h": [0, 1, 0],
            "refund_count_30d": [1, 3, 0],
            "geofence_dist_m": [100.0, 300.0, 200.0],
        }
    )
    result = build_behavioral_features(frame)
    assert len(result) == len(frame)
    assert result[BEHAVIORAL_FEATURES].notna().all().all()
    assert result.loc[0, "night_trip_rate"] == 0.5

