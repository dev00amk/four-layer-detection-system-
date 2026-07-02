"""Add deterministic Spark Driver telemetry to the IEEE-CIS base."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .config import BRONZE, SILVER, ensure_directories
from .schema import EnrichedTrip, validate_dataframe

log = logging.getLogger(__name__)


def enrich(
    seed: int = 42, bronze_dir: Path = BRONZE, silver_dir: Path = SILVER
) -> pd.DataFrame:
    ensure_directories()
    source = bronze_dir / "train_transaction.parquet"
    if not source.exists():
        raise FileNotFoundError("Run `python -m sentinel.ingest` first.")
    df = pd.read_parquet(source)
    rng = np.random.default_rng(seed)
    n = len(df)
    fraud = df["isFraud"].astype(bool).to_numpy()
    driver_num = (df["card1"].fillna(0).astype(int).to_numpy() % max(500, n // 12))
    base_lat = 40.72 + rng.normal(0, 0.08, n)
    base_lon = -74.00 + rng.normal(0, 0.08, n)
    df = df.assign(
        trip_id="T" + df["TransactionID"].astype(str),
        driver_id=pd.Series(driver_num).map(lambda x: f"D{x:06d}"),
        customer_id=pd.Series(df["addr1"].fillna(0).astype(int)).map(lambda x: f"C{x:05d}"),
        store_id=pd.Series(df["card2"].fillna(0).astype(int) % 120).map(lambda x: f"S{x:04d}"),
        device_id=pd.Series((driver_num * 7 + rng.integers(0, 5, n)) % max(400, n // 15)).map(
            lambda x: f"DEV{x:06d}"
        ),
        payout_account=pd.Series((driver_num * 3) % max(350, n // 20)).map(
            lambda x: f"BANK{x:06d}"
        ),
        campaign_id=pd.Series(rng.integers(1, 9, n)).map(lambda x: f"CMP{x:02d}"),
        event_ts=pd.Timestamp("2025-01-01") + pd.to_timedelta(df["TransactionDT"], unit="s"),
        pickup_lat=base_lat,
        pickup_lon=base_lon,
        dropoff_lat=base_lat + rng.normal(0, 0.03 + fraud * 0.09, n),
        dropoff_lon=base_lon + rng.normal(0, 0.03 + fraud * 0.09, n),
        geofence_dist_m=np.maximum(
            0, rng.normal(np.where(fraud, 900, 200), np.where(fraud, 380, 100), n)
        ),
        emulator_flag=(rng.random(n) < np.where(fraud, 0.18, 0.02)).astype(int),
        gps_mock_flag=(rng.random(n) < np.where(fraud, 0.22, 0.015)).astype(int),
        rooted_device_flag=(rng.random(n) < np.where(fraud, 0.14, 0.01)).astype(int),
        incentive_trip_count=np.where(
            fraud, rng.choice([18, 19, 20, 21], n), rng.integers(1, 18, n)
        ),
        refund_count_30d=rng.poisson(np.where(fraud, 5.5, 0.8), n),
        payout_change_72h=(rng.random(n) < np.where(fraud, 0.20, 0.015)).astype(int),
        off_hours_flag=(rng.random(n) < np.where(fraud, 0.35, 0.08)).astype(int),
        shift_id=pd.Series(np.arange(n) // 8).map(lambda x: f"SHIFT{x:07d}"),
        trip_distance_km=np.maximum(0.1, rng.lognormal(np.where(fraud, 2.4, 1.5), 0.55, n)),
        trip_duration_min=np.maximum(2, rng.normal(np.where(fraud, 42, 24), 10, n)),
        ip_cluster=pd.Series((driver_num * 11 + rng.integers(0, 4, n)) % max(250, n // 25)).map(
            lambda x: f"IP{x:06d}"
        ),
    )
    accept_latency_ms = np.maximum(
        40,
        rng.normal(np.where(fraud & (df["emulator_flag"].to_numpy() == 1), 280, 4_500), 900, n),
    ).astype(int)
    df["trip_start_ts"] = df["event_ts"]
    df["trip_end_ts"] = df["event_ts"] + pd.to_timedelta(df["trip_duration_min"], unit="m")
    df["offer_sent_ts"] = df["trip_start_ts"] - pd.to_timedelta(accept_latency_ms, unit="ms")
    df["accept_ts"] = df["trip_start_ts"]
    df["pickup_confirm_ts"] = df["trip_start_ts"] + pd.to_timedelta(
        np.maximum(1, df["trip_duration_min"] * 0.2), unit="m"
    )
    df["gps_accuracy_m"] = np.maximum(2, rng.normal(np.where(fraud, 22, 15), 8, n))
    df["root_flag"] = df["rooted_device_flag"]
    # Seed one small, explainable coordination pattern for the reviewer-facing CASE_001.
    case_drivers = sorted(df["driver_id"].unique())[:2]
    case_mask = df["driver_id"].isin(case_drivers)
    df.loc[case_mask, ["device_id", "payout_account", "campaign_id"]] = [
        "DEV_CASE001",
        "BANK_CASE001",
        "CMP_CASE001",
    ]
    for case_driver in case_drivers:
        bot_indices = df.index[df["driver_id"].eq(case_driver)][:5]
        df.loc[bot_indices, "emulator_flag"] = 1
        df.loc[bot_indices, "offer_sent_ts"] = (
            df.loc[bot_indices, "accept_ts"] - pd.to_timedelta(200, unit="ms")
        )
    gps_indices = df.index[df["driver_id"].eq(case_drivers[0])][:3]
    gps_times = pd.Timestamp("2025-02-01T12:00:00") + pd.to_timedelta(
        np.arange(len(gps_indices)) * 30, unit="s"
    )
    df.loc[gps_indices, "trip_start_ts"] = gps_times
    df.loc[gps_indices, "trip_end_ts"] = gps_times + pd.to_timedelta(10, unit="s")
    df.loc[gps_indices, "pickup_lat"] = 40.0 + np.arange(len(gps_indices))
    df.loc[gps_indices, "dropoff_lat"] = 40.0 + np.arange(len(gps_indices))
    df.loc[gps_indices, ["pickup_lon", "dropoff_lon"]] = -74.0
    df.loc[gps_indices, "gps_accuracy_m"] = 10.0
    df.loc[gps_indices, "gps_mock_flag"] = 1
    device_sequence = df.sort_values(["driver_id", "event_ts"]).groupby(
        "driver_id", observed=True
    )["device_id"]
    df["new_device_flag"] = (
        device_sequence.transform(lambda values: values.ne(values.shift()).astype(int))
        .reindex(df.index)
        .fillna(1)
        .astype(int)
    )
    validate_dataframe(df, EnrichedTrip)
    silver_dir.mkdir(parents=True, exist_ok=True)
    output = silver_dir / "spark_driver_trips.parquet"
    df.to_parquet(output, index=False)
    log.info(
        "silver_written",
        extra={"path": output, "rows": len(df), "fraud_rate": float(df.isFraud.mean())},
    )
    return df


if __name__ == "__main__":
    enrich()
