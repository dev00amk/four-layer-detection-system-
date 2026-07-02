"""DuckDB connection and typed feature bridges."""
from __future__ import annotations

import duckdb
import pandas as pd

from .config import GOLD, ROOT, SILVER, ensure_directories


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    ensure_directories()
    silver = SILVER / "spark_driver_trips.parquet"
    if not silver.exists():
        raise FileNotFoundError("Silver data missing. Run demo, ingest, and enrich first.")
    con = duckdb.connect(str(GOLD / "sentinel.duckdb"), read_only=read_only)
    # DuckDB does not support prepared-statement parameters inside DDL (CREATE VIEW),
    # so the path must be inlined. It is not attacker-controlled (fixed local config
    # path, never user input); standard SQL single-quote escaping is sufficient here.
    path = silver.as_posix().replace("'", "''")
    con.execute(f"CREATE OR REPLACE VIEW spark_trips AS SELECT * FROM read_parquet('{path}')")
    con.execute(
        """
        CREATE OR REPLACE MACRO haversine_km(lat1, lon1, lat2, lon2) AS
          2 * 6371 * asin(sqrt(
            pow(sin(radians(lat2-lat1)/2), 2) +
            cos(radians(lat1))*cos(radians(lat2))*pow(sin(radians(lon2-lon1)/2), 2)
          ))
        """
    )
    cross_role_sql = ROOT / "sql" / "gold" / "cross_role_risk_join.sql"
    if cross_role_sql.exists():
        con.execute(cross_role_sql.read_text(encoding="utf-8"))
    return con


def get_cross_role_df(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    try:
        return con.execute("SELECT * FROM cross_role_risk").df()
    except duckdb.Error:
        return pd.DataFrame(columns=["driver_id", "collusion_signal_count", "collusion_flag"])


def get_scored_inputs(con, feature_df: pd.DataFrame, graph_csv=None):
    from .graph import get_ring_flags
    from .signals import run_signals

    driver_ids = feature_df["driver_id"] if "driver_id" in feature_df else feature_df.index.to_series()
    sql = run_signals(con).set_index("driver_id")["hit_count"]
    sql_hits = driver_ids.map(sql).fillna(0).astype(float)
    graph_flags, ring_sizes = get_ring_flags(driver_ids, graph_csv)
    sql_hits.index = feature_df.index
    graph_flags.index = feature_df.index
    ring_sizes.index = feature_df.index
    return graph_flags, ring_sizes, sql_hits
