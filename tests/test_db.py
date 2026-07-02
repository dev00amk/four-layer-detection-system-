"""DuckDB bridge tests: connection guards, fallbacks, and input alignment."""
from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from sentinel.db import get_connection, get_cross_role_df, get_scored_inputs

CROSS_ROLE_COLUMNS = ["driver_id", "collusion_signal_count", "collusion_flag"]


def test_get_connection_raises_without_silver(monkeypatch, tmp_path):
    monkeypatch.setattr("sentinel.db.SILVER", tmp_path / "absent")
    with pytest.raises(FileNotFoundError):
        get_connection()


def test_get_connection_builds_views(monkeypatch, pipeline_env, tmp_path):
    monkeypatch.setattr("sentinel.db.SILVER", pipeline_env["silver"])
    monkeypatch.setattr("sentinel.db.GOLD", tmp_path)
    with get_connection() as con:
        rows = con.execute("SELECT COUNT(*) FROM spark_trips").fetchone()[0]
        assert rows == len(pipeline_env["silver_df"])
        distance = con.execute(
            "SELECT haversine_km(40.7, -74.0, 40.8, -74.0)"
        ).fetchone()[0]
        assert distance == pytest.approx(11.1, abs=0.5)
        cross_role = get_cross_role_df(con)
        assert set(CROSS_ROLE_COLUMNS) <= set(cross_role.columns)


def test_cross_role_fallback_is_loud(caplog):
    con = duckdb.connect()
    with caplog.at_level("WARNING", logger="sentinel.db"):
        result = get_cross_role_df(con)
    assert result.empty
    assert list(result.columns) == CROSS_ROLE_COLUMNS
    assert any("cross_role_view_unavailable" in r.message for r in caplog.records)


def test_get_scored_inputs_alignment(monkeypatch, synthetic_trips):
    hits = pd.DataFrame(
        {"driver_id": ["D000001"], "hit_count": [3], "triggered_signals": ["01_x"]}
    )
    monkeypatch.setattr("sentinel.signals.run_signals", lambda con: hits)
    feature_df = synthetic_trips.copy()
    feature_df.index = feature_df.index + 1000  # non-default index
    graph_flags, ring_sizes, sql_hits = get_scored_inputs(None, feature_df, None)
    for series in (graph_flags, ring_sizes, sql_hits):
        assert series.index.equals(feature_df.index)
    known = feature_df["driver_id"] == "D000001"
    assert (sql_hits[known] == 3.0).all()
    assert (sql_hits[~known] == 0.0).all()
