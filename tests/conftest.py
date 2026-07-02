"""Shared fixtures for the Sentinel test suite."""
from __future__ import annotations

import getpass
import os
import tempfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

# pytest places tmp_path under <tempdir>/pytest-of-<user>. If that root has
# broken ACLs (seen on Windows when an elevated process created it), every
# tmp_path test fails with PermissionError before running. Probe the root and
# redirect pytest to a fresh temp root when the default is unusable.
_default_root = Path(tempfile.gettempdir()) / f"pytest-of-{getpass.getuser()}"
if _default_root.exists():
    try:
        _probe = _default_root / ".sentinel-probe"
        _probe.mkdir(exist_ok=True)
        _probe.rmdir()
    except OSError:
        _fallback = Path(tempfile.gettempdir()) / "pytest-sentinel-temproot"
        _fallback.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("PYTEST_DEBUG_TEMPROOT", str(_fallback))

from sentinel.demo import generate_demo  # noqa: E402
from sentinel.enrich import enrich  # noqa: E402
from sentinel.ingest import ingest  # noqa: E402


@pytest.fixture()
def synthetic_trips() -> pd.DataFrame:
    """Small deterministic trip frame covering every SentinelModel feature."""
    rng = np.random.default_rng(7)
    n = 200
    fraud = rng.random(n) < 0.10
    return pd.DataFrame(
        {
            "trip_id": [f"T{i:06d}" for i in range(n)],
            "driver_id": [f"D{i % 40:06d}" for i in range(n)],
            "store_id": [f"S{i % 15:04d}" for i in range(n)],
            "isFraud": fraud.astype(int),
            "event_ts": pd.Timestamp("2025-01-01")
            + pd.to_timedelta(np.arange(n) * 3600, unit="s"),
            # Group A — IEEE-CIS shaped features
            "TransactionAmt": rng.lognormal(4.0 + fraud * 0.5, 0.8),
            "dist1": np.abs(rng.normal(8 + fraud * 30, 15, n)),
            "C1": rng.poisson(3 + fraud * 7, n).astype(float),
            "C2": rng.poisson(2 + fraud * 5, n).astype(float),
            "C5": rng.poisson(1 + fraud * 4, n).astype(float),
            "C13": rng.poisson(4 + fraud * 6, n).astype(float),
            "D1": np.abs(rng.normal(30 - fraud * 15, 20, n)),
            "D10": np.abs(rng.normal(20 - fraud * 8, 14, n)),
            "V12": rng.normal(0.5 + fraud * 0.4, 0.25, n),
            "V53": rng.normal(0.4 + fraud * 0.45, 0.3, n),
            "V258": rng.normal(0.3 + fraud * 0.5, 0.3, n),
            # Group B — delivery telemetry
            "geofence_dist_m": np.maximum(
                0, rng.normal(np.where(fraud, 900, 200), 100, n)
            ),
            "emulator_flag": (rng.random(n) < np.where(fraud, 0.2, 0.02)).astype(int),
            "gps_mock_flag": (rng.random(n) < np.where(fraud, 0.2, 0.02)).astype(int),
            "rooted_device_flag": (rng.random(n) < np.where(fraud, 0.1, 0.01)).astype(
                int
            ),
            "incentive_trip_count": rng.integers(1, 20, n),
            "refund_count_30d": rng.poisson(np.where(fraud, 5.0, 1.0), n),
            "payout_change_72h": (rng.random(n) < 0.05).astype(int),
            "off_hours_flag": (rng.random(n) < 0.10).astype(int),
            "trip_distance_km": np.maximum(0.1, rng.lognormal(1.5, 0.5, n)),
            "trip_duration_min": np.maximum(2.0, rng.normal(25, 8, n)),
            "new_device_flag": np.zeros(n, dtype=int),
        }
    )


@pytest.fixture(scope="session")
def pipeline_env(tmp_path_factory) -> dict[str, object]:
    """Run demo -> ingest -> enrich once into session temp dirs.

    Returns the silver DataFrame plus the bronze/silver directories so
    integration tests can exercise real artifacts without touching data/.
    """
    root = tmp_path_factory.mktemp("pipeline")
    raw, bronze, silver = root / "raw", root / "bronze", root / "silver"
    raw.mkdir()
    txn, identity = generate_demo(rows=2000, seed=42)
    txn.to_csv(raw / "train_transaction.csv", index=False)
    identity.to_csv(raw / "train_identity.csv", index=False)
    ingest(raw_dir=raw, bronze_dir=bronze)
    silver_df = enrich(seed=42, bronze_dir=bronze, silver_dir=silver)
    return {"silver_df": silver_df, "raw": raw, "bronze": bronze, "silver": silver}


@pytest.fixture(scope="session")
def silver_df(pipeline_env) -> pd.DataFrame:
    return pipeline_env["silver_df"]


@pytest.fixture()
def duckdb_con(synthetic_trips):
    """In-memory DuckDB connection exposing synthetic_trips as spark_trips."""
    con = duckdb.connect()
    con.register("trips_source", synthetic_trips)
    con.execute("CREATE VIEW spark_trips AS SELECT * FROM trips_source")
    yield con
    con.close()
