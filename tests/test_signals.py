"""SQL signal runner tests: aggregation, isolation, and monitoring exclusion."""
from __future__ import annotations

import duckdb
import pytest

from sentinel.exceptions import SignalExecutionError
from sentinel.signals import run_signals

ALL_DRIVERS_SQL = "SELECT DISTINCT driver_id FROM spark_trips"


def test_monitoring_signals_excluded_from_hits(tmp_path, duckdb_con):
    (tmp_path / "01_everyone.sql").write_text(ALL_DRIVERS_SQL, encoding="utf-8")
    (tmp_path / "04_emulator_device.sql").write_text(ALL_DRIVERS_SQL, encoding="utf-8")
    hits = run_signals(duckdb_con, signals_dir=tmp_path)
    assert (hits["hit_count"] == 1).all()
    assert (hits["triggered_signals"] == "01_everyone").all()


def test_broken_signal_is_isolated(tmp_path, duckdb_con, caplog):
    (tmp_path / "01_everyone.sql").write_text(ALL_DRIVERS_SQL, encoding="utf-8")
    (tmp_path / "02_broken.sql").write_text(
        "SELECT no_such_column FROM spark_trips", encoding="utf-8"
    )
    with caplog.at_level("WARNING", logger="sentinel.signals"):
        hits = run_signals(duckdb_con, signals_dir=tmp_path)
    assert not hits.empty
    assert (hits["hit_count"] == 1).all()
    assert any("signal_failed" in r.message for r in caplog.records)


def test_all_signals_failing_raises(tmp_path, duckdb_con):
    (tmp_path / "01_broken.sql").write_text("SELECT * FROM nope", encoding="utf-8")
    (tmp_path / "02_broken.sql").write_text("SELECT * FROM nada", encoding="utf-8")
    with pytest.raises(SignalExecutionError) as excinfo:
        run_signals(duckdb_con, signals_dir=tmp_path)
    assert excinfo.value.failed_signals == ["01_broken", "02_broken"]


def test_signal_without_driver_id_is_skipped(tmp_path, duckdb_con):
    (tmp_path / "01_everyone.sql").write_text(ALL_DRIVERS_SQL, encoding="utf-8")
    (tmp_path / "02_count_only.sql").write_text(
        "SELECT COUNT(*) AS n FROM spark_trips", encoding="utf-8"
    )
    hits = run_signals(duckdb_con, signals_dir=tmp_path)
    assert (hits["hit_count"] == 1).all()


def test_empty_signal_dir_returns_empty_frame(tmp_path, duckdb_con):
    hits = run_signals(duckdb_con, signals_dir=tmp_path)
    assert hits.empty
    assert list(hits.columns) == ["driver_id", "hit_count", "triggered_signals"]


def test_real_signal_library_runs_on_silver(silver_df):
    con = duckdb.connect()
    con.register("silver_source", silver_df)
    con.execute("CREATE VIEW spark_trips AS SELECT * FROM silver_source")
    con.execute(
        """
        CREATE OR REPLACE MACRO haversine_km(lat1, lon1, lat2, lon2) AS
          2 * 6371 * asin(sqrt(
            pow(sin(radians(lat2-lat1)/2), 2) +
            cos(radians(lat1))*cos(radians(lat2))*pow(sin(radians(lon2-lon1)/2), 2)
          ))
        """
    )
    hits = run_signals(con)
    con.close()
    assert not hits.empty
    assert (hits["hit_count"] >= 1).all()
    assert hits["driver_id"].is_unique
