"""Versioned API contracts for online scoring."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TripRecord(BaseModel):
    driver_id: str
    trip_id: str
    event_ts: str
    store_id: str
    TransactionAmt: float = 0
    dist1: float = 0
    C1: float = 0
    C2: float = 0
    C5: float = 0
    C13: float = 0
    D1: float = 0
    D10: float = 0
    V12: float = 0
    V53: float = 0
    V258: float = 0
    geofence_dist_m: float = Field(default=0, ge=0)
    emulator_flag: int = Field(default=0, ge=0, le=1)
    gps_mock_flag: int = Field(default=0, ge=0, le=1)
    rooted_device_flag: int = Field(default=0, ge=0, le=1)
    incentive_trip_count: int = Field(default=0, ge=0)
    refund_count_30d: int = Field(default=0, ge=0)
    payout_change_72h: int = Field(default=0, ge=0, le=1)
    off_hours_flag: int = Field(default=0, ge=0, le=1)
    trip_distance_km: float = Field(default=1, gt=0)
    trip_duration_min: float = Field(default=10, gt=0)
    new_device_flag: int = Field(default=0, ge=0, le=1)


class ScoreRequest(BaseModel):
    trip: TripRecord
    sql_hits: int = Field(default=0, ge=0)
    graph_flag: int = Field(default=0, ge=0, le=1)
    ring_size: int = Field(default=0, ge=0)


class ScoreResponse(BaseModel):
    driver_id: str
    trip_id: str
    score: int
    band: str
    xgb_probability: float
    is_fatal: bool
    fatal_signal_ids: str


class ModelInfo(BaseModel):
    model_version: str
    trained_at: str
    git_sha: str
    feature_count: int
