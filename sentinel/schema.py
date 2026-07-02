"""Pydantic contracts for bronze and enriched trip records."""
from __future__ import annotations

from typing import Any, TypeVar

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .exceptions import DataValidationError

T = TypeVar("T", bound=BaseModel)


SchemaValidationError = DataValidationError


class BronzeTransaction(BaseModel):
    """Minimum IEEE-CIS record required by the ingestion boundary."""

    model_config = ConfigDict(extra="allow")
    TransactionID: int
    isFraud: int = Field(ge=0, le=1)
    TransactionDT: int | float
    TransactionAmt: float


class EnrichedTrip(BaseModel):
    """Operational fields required by detection, graph, and case generation."""

    model_config = ConfigDict(extra="allow")
    trip_id: str
    driver_id: str
    customer_id: str
    store_id: str
    device_id: str
    payout_account: str
    event_ts: Any
    trip_start_ts: Any
    trip_end_ts: Any
    geofence_dist_m: float = Field(ge=0)
    emulator_flag: int = Field(ge=0, le=1)
    gps_mock_flag: int = Field(ge=0, le=1)
    rooted_device_flag: int = Field(ge=0, le=1)
    payout_change_72h: int = Field(ge=0, le=1)
    trip_distance_km: float = Field(gt=0)
    trip_duration_min: float = Field(gt=0)


def validate_dataframe(
    df: pd.DataFrame,
    model: type[T],
    sample_size: int | None = None,
) -> None:
    """Validate required columns, rows, and cross-column invariants."""
    required = set(model.model_fields)
    missing = sorted(required - set(df.columns))
    if missing:
        raise SchemaValidationError(f"{model.__name__}: missing columns: {', '.join(missing)}")
    sample = df if sample_size is None else df.head(sample_size)
    errors: list[str] = []
    for index, record in sample.iterrows():
        try:
            model.model_validate(record.to_dict())
        except ValidationError as exc:
            errors.append(f"row {index}: {exc.errors()[0]['msg']}")
            if len(errors) == 5:
                break
    if errors:
        raise SchemaValidationError(f"{model.__name__} validation failed: {'; '.join(errors)}")
    if "driver_id" in df and df["driver_id"].isna().any():
        raise DataValidationError(f"{model.__name__}: driver_id contains null values")
    if {"trip_start_ts", "trip_end_ts"}.issubset(df.columns):
        start = pd.to_datetime(df["trip_start_ts"], errors="coerce")
        end = pd.to_datetime(df["trip_end_ts"], errors="coerce")
        if start.isna().any() or end.isna().any() or (end < start).any():
            raise DataValidationError(
                f"{model.__name__}: trip timestamps are missing or out of order"
            )
