"""Request/response contracts for the Sentinel scoring API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TripRecord(BaseModel):
    """One trip to score.

    Carries the delivery-telemetry and behavioral raw fields the model
    consumes. IEEE-CIS benchmark features (Group A) default to 0 because a
    live caller has no equivalent; the persisted model tolerates the
    imputation marker semantics.
    """

    trip_id: str
    driver_id: str
    store_id: str = "UNKNOWN"
    event_ts: str = Field(
        default="2025-01-01T00:00:00Z", description="ISO-8601 trip event timestamp"
    )
    # Group B — delivery telemetry
    geofence_dist_m: float = Field(default=0, ge=0)
    emulator_flag: int = Field(default=0, ge=0, le=1)
    gps_mock_flag: int = Field(default=0, ge=0, le=1)
    rooted_device_flag: int = Field(default=0, ge=0, le=1)
    incentive_trip_count: int = Field(default=0, ge=0)
    refund_count_30d: int = Field(default=0, ge=0)
    payout_change_72h: int = Field(default=0, ge=0, le=1)
    off_hours_flag: int = Field(default=0, ge=0, le=1)
    trip_distance_km: float = Field(default=1.0, gt=0)
    trip_duration_min: float = Field(default=15.0, gt=0)
    new_device_flag: int = Field(default=0, ge=0, le=1)
    # Group A — IEEE-CIS benchmark surface (absent in live traffic)
    TransactionAmt: float = 0.0
    dist1: float = 0.0
    C1: float = 0.0
    C2: float = 0.0
    C5: float = 0.0
    C13: float = 0.0
    D1: float = 0.0
    D10: float = 0.0
    V12: float = 0.0
    V53: float = 0.0
    V258: float = 0.0
    # Offline-layer context, precomputed by the batch pipeline when available.
    # SQL signals and entity graphs need the full trip corpus in DuckDB, so
    # the online path accepts them as inputs and degrades gracefully to the
    # XGBoost + IsolationForest layers when absent (0). This mirrors a real
    # online/offline feature-store split.
    sql_hits: float = Field(default=0, ge=0)
    graph_flag: int = Field(default=0, ge=0, le=1)
    ring_size: int = Field(default=0, ge=0)


class ScoreRequest(BaseModel):
    trips: list[TripRecord] = Field(min_length=1, max_length=1000)


class TripScore(BaseModel):
    trip_id: str
    driver_id: str
    score: int = Field(ge=0, le=10)
    band: str
    xgb_probability: float
    iforest_score: float
    is_fatal: bool
    fatal_signal_ids: str


class ScoreResponse(BaseModel):
    results: list[TripScore]


class ModelInfo(BaseModel):
    artifact_version: int
    trained_at_utc: str
    git_sha: str
    feature_count: int
    lib_versions: dict[str, str]


class HealthResponse(BaseModel):
    status: str
