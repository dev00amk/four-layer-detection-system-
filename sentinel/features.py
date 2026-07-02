"""Behavioral segmentation features for driver-level fraud propensity."""
from __future__ import annotations

import numpy as np
import pandas as pd

BEHAVIORAL_FEATURES = [
    "night_trip_rate",
    "zone_concentration",
    "payout_change_rate",
    "refund_velocity",
    "peer_geofence_deviation",
]
WINDOWS = ("7d", "30d", "90d")
ROLLING_FEATURES = [
    f"{feature}_{window}" for feature in BEHAVIORAL_FEATURES for window in WINDOWS
] + [
    f"{feature}_trend_7d_90d" for feature in BEHAVIORAL_FEATURES
]


def _group_transform(df: pd.DataFrame, column: str, operation: str) -> pd.Series:
    return df.groupby("driver_id", observed=True)[column].transform(operation)


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    hour = pd.to_datetime(result["event_ts"]).dt.hour
    result["_night_trip"] = ((hour < 6) | (hour >= 22)).astype(float)
    result["night_trip_rate"] = _group_transform(result, "_night_trip", "mean")
    return result.drop(columns="_night_trip")


def add_zone_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    pair_count = result.groupby(["driver_id", "store_id"], observed=True)["trip_id"].transform(
        "count"
    )
    driver_count = result.groupby("driver_id", observed=True)["trip_id"].transform("count")
    result["zone_concentration"] = (pair_count / driver_count.clip(lower=1)).clip(0, 1)
    return result


def add_payout_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["payout_change_rate"] = _group_transform(result, "payout_change_72h", "mean")
    return result


def add_interaction_rate_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["refund_velocity"] = _group_transform(result, "refund_count_30d", "mean")
    return result


def add_cohort_deviation_features(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    store_mean = result.groupby("store_id", observed=True)["geofence_dist_m"].transform("mean")
    store_std = (
        result.groupby("store_id", observed=True)["geofence_dist_m"].transform("std").fillna(1.0)
    )
    result["peer_geofence_deviation"] = (
        (result["geofence_dist_m"] - store_mean) / store_std.replace(0, 1)
    ).replace([np.inf, -np.inf], 0).fillna(0)
    return result


def build_behavioral_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return row-aligned temporal, zone, payout, interaction, and peer features."""
    result = add_temporal_features(df)
    result = add_zone_features(result)
    result = add_payout_velocity_features(result)
    result = add_interaction_rate_features(result)
    result = add_cohort_deviation_features(result)
    return add_rolling_features(result)


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add leakage-resistant, row-aligned 7/30/90-day driver windows and trends."""
    result = df.copy()
    timestamps = pd.to_datetime(result["event_ts"], errors="coerce")
    order = pd.DataFrame(
        {
            "driver_id": result["driver_id"],
            "event_ts": timestamps,
            "_position": np.arange(len(result)),
        }
    ).sort_values(["driver_id", "event_ts", "_position"])
    for feature in BEHAVIORAL_FEATURES:
        ordered_values = result.loc[order.index, feature].astype(float)
        work = order.assign(_value=ordered_values.to_numpy())
        for window in WINDOWS:
            rolled = (
                work.set_index("event_ts")
                .groupby("driver_id", observed=True)["_value"]
                .rolling(window, min_periods=1)
                .mean()
                .reset_index(level=0, drop=True)
                .to_numpy()
            )
            aligned = pd.Series(rolled, index=work["_position"]).sort_index()
            result[f"{feature}_{window}"] = aligned.to_numpy()
        result[f"{feature}_trend_7d_90d"] = (
            result[f"{feature}_7d"] - result[f"{feature}_90d"]
        )
    return result
