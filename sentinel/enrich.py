"""Add deterministic Spark Driver telemetry to the IEEE-CIS base."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import BRONZE, SILVER, ensure_directories


def enrich(seed: int = 42) -> pd.DataFrame:
    ensure_directories()
    source = BRONZE / "train_transaction.parquet"
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
        device_id=pd.Series((driver_num * 7 + rng.integers(0, 5, n)) % max(400, n // 15)).map(lambda x: f"DEV{x:06d}"),
        payout_account=pd.Series((driver_num * 3) % max(350, n // 20)).map(lambda x: f"BANK{x:06d}"),
        campaign_id=pd.Series(rng.integers(1, 9, n)).map(lambda x: f"CMP{x:02d}"),
        event_ts=pd.Timestamp("2025-01-01") + pd.to_timedelta(df["TransactionDT"], unit="s"),
        pickup_lat=base_lat,
        pickup_lon=base_lon,
        dropoff_lat=base_lat + rng.normal(0, 0.03 + fraud * 0.09, n),
        dropoff_lon=base_lon + rng.normal(0, 0.03 + fraud * 0.09, n),
        geofence_dist_m=np.maximum(0, rng.normal(np.where(fraud, 900, 200), np.where(fraud, 380, 100), n)),
        emulator_flag=(rng.random(n) < np.where(fraud, 0.18, 0.02)).astype(int),
        gps_mock_flag=(rng.random(n) < np.where(fraud, 0.22, 0.015)).astype(int),
        rooted_device_flag=(rng.random(n) < np.where(fraud, 0.14, 0.01)).astype(int),
        incentive_trip_count=np.where(fraud, rng.choice([18, 19, 20, 21], n), rng.integers(1, 18, n)),
        refund_count_30d=rng.poisson(np.where(fraud, 5.5, 0.8), n),
        payout_change_72h=(rng.random(n) < np.where(fraud, 0.20, 0.015)).astype(int),
        off_hours_flag=(rng.random(n) < np.where(fraud, 0.35, 0.08)).astype(int),
        shift_id=pd.Series(np.arange(n) // 8).map(lambda x: f"SHIFT{x:07d}"),
        trip_distance_km=np.maximum(0.1, rng.lognormal(np.where(fraud, 2.4, 1.5), 0.55, n)),
        trip_duration_min=np.maximum(2, rng.normal(np.where(fraud, 42, 24), 10, n)),
        ip_cluster=pd.Series((driver_num * 11 + rng.integers(0, 4, n)) % max(250, n // 25)).map(lambda x: f"IP{x:06d}"),
    )
    # Seed one small, explainable coordination pattern for the reviewer-facing CASE_001.
    case_drivers = sorted(df["driver_id"].unique())[:2]
    case_mask = df["driver_id"].isin(case_drivers)
    df.loc[case_mask, ["device_id", "payout_account", "campaign_id"]] = [
        "DEV_CASE001",
        "BANK_CASE001",
        "CMP_CASE001",
    ]
    output = SILVER / "spark_driver_trips.parquet"
    df.to_parquet(output, index=False)
    print(f"Silver written: {output} shape={df.shape} fraud_rate={df.isFraud.mean():.3%} emulator_rate={df.emulator_flag.mean():.3%}")
    return df


if __name__ == "__main__":
    enrich()
