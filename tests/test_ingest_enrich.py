"""Bronze ingest and silver enrichment integration tests."""
from __future__ import annotations

import json

import pandas as pd
import pytest

from sentinel.demo import generate_demo
from sentinel.enrich import enrich
from sentinel.graph import build_graph, get_ring_flags
from sentinel.ingest import ingest
from sentinel.schema import SchemaValidationError, validate_trip_invariants


def test_ingest_requires_raw_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest(raw_dir=tmp_path / "empty", bronze_dir=tmp_path / "bronze")


def test_ingest_writes_bronze_and_lineage(pipeline_env):
    bronze = pipeline_env["bronze"]
    assert (bronze / "train_transaction.parquet").exists()
    lineage = json.loads((bronze / "lineage.json").read_text(encoding="utf-8"))
    assert set(lineage["sources"]) == {"train_transaction.csv", "train_identity.csv"}
    for source in lineage["sources"].values():
        assert len(source["sha256"]) == 64
    assert lineage["output"]["rows"] == 2000
    assert 0.0 < lineage["fraud_rate"] < 0.10


def test_enrich_preserves_rows_and_adds_telemetry(pipeline_env):
    silver_df = pipeline_env["silver_df"]
    assert len(silver_df) == 2000
    for column in (
        "trip_id", "driver_id", "geofence_dist_m", "emulator_flag",
        "trip_start_ts", "trip_end_ts", "new_device_flag",
    ):
        assert column in silver_df.columns
    assert (silver_df["trip_end_ts"] >= silver_df["trip_start_ts"]).all()
    assert (pipeline_env["silver"] / "spark_driver_trips.parquet").exists()


def test_enrich_is_deterministic_per_seed(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    txn, identity = generate_demo(rows=400, seed=11)
    txn.to_csv(raw / "train_transaction.csv", index=False)
    identity.to_csv(raw / "train_identity.csv", index=False)
    bronze = tmp_path / "bronze"
    ingest(raw_dir=raw, bronze_dir=bronze)
    first = enrich(seed=11, bronze_dir=bronze, silver_dir=tmp_path / "s1")
    second = enrich(seed=11, bronze_dir=bronze, silver_dir=tmp_path / "s2")
    pd.testing.assert_frame_equal(first, second)


def test_build_graph_detects_seeded_case001_ring(monkeypatch, pipeline_env, tmp_path):
    monkeypatch.setattr("sentinel.graph.SILVER", pipeline_env["silver"])
    monkeypatch.setattr("sentinel.graph.GRAPH", tmp_path)
    rings = build_graph()
    assert (tmp_path / "fraud_rings.csv").exists()
    assert (tmp_path / "entity_graph.graphml").exists()
    # enrich() seeds two drivers sharing DEV_CASE001 + BANK_CASE001.
    seeded = pipeline_env["silver_df"]
    case_drivers = set(
        seeded.loc[seeded["device_id"] == "DEV_CASE001", "driver_id"].unique()
    )
    assert len(case_drivers) == 2
    assert case_drivers <= set(rings["driver_id"])


def _invariant_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trip_id": ["T1", "T2"],
            "driver_id": ["D1", "D2"],
            "trip_start_ts": pd.to_datetime(["2025-01-01 10:00", "2025-01-01 11:00"]),
            "trip_end_ts": pd.to_datetime(["2025-01-01 10:30", "2025-01-01 11:30"]),
        }
    )


def test_trip_invariants_pass_on_clean_frame():
    validate_trip_invariants(_invariant_frame())


def test_trip_invariants_reject_inverted_timestamps():
    frame = _invariant_frame()
    frame.loc[0, "trip_end_ts"] = pd.Timestamp("2025-01-01 09:00")
    with pytest.raises(SchemaValidationError, match="end before they start"):
        validate_trip_invariants(frame)


def test_trip_invariants_reject_duplicate_trip_ids():
    frame = _invariant_frame()
    frame.loc[1, "trip_id"] = "T1"
    with pytest.raises(SchemaValidationError, match="duplicate trip_id"):
        validate_trip_invariants(frame)


def test_trip_invariants_reject_null_driver():
    frame = _invariant_frame()
    frame.loc[0, "driver_id"] = None
    with pytest.raises(SchemaValidationError, match="null driver_id"):
        validate_trip_invariants(frame)


def test_get_ring_flags_with_and_without_csv(tmp_path):
    ids = pd.Series(["D000001", "D000002", "D000003"])
    flags, sizes = get_ring_flags(ids, tmp_path / "missing.csv")
    assert flags.tolist() == [0, 0, 0]
    assert sizes.tolist() == [0, 0, 0]

    csv = tmp_path / "rings.csv"
    pd.DataFrame(
        {
            "ring_id": ["R00001", "R00001"],
            "driver_id": ["D000001", "D000002"],
            "ring_size": [2, 2],
        }
    ).to_csv(csv, index=False)
    flags, sizes = get_ring_flags(ids, csv)
    assert flags.tolist() == [1, 1, 0]
    assert sizes.tolist() == [2, 2, 0]
