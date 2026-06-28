"""Run Project Sentinel end to end."""
from __future__ import annotations

import json
import pandas as pd

from sentinel.case import generate_cases_from_scores
from sentinel.config import GOLD, GRAPH, SILVER
from sentinel.db import get_connection, get_cross_role_df, get_scored_inputs
from sentinel.graph import build_graph
from sentinel.model import SentinelModel
from sentinel.osint import enrich_critical_drivers


def main():
    build_graph()
    con = get_connection()
    df = pd.read_parquet(SILVER / "spark_driver_trips.parquet")
    graph_flags, ring_sizes, sql_hits = get_scored_inputs(con, df, GRAPH / "fraud_rings.csv")
    cross_role_df = get_cross_role_df(con)
    model = SentinelModel().fit(df, df["isFraud"].astype(int))
    scored = model.predict(df, graph_flags, ring_sizes, sql_hits)
    shap_df = model.explain(df)
    scored.to_parquet(GOLD / "scored_trips.parquet", index=False)
    scored.head(50_000).to_csv(GOLD / "tableau_export.csv", index=False)
    n_cases = generate_cases_from_scores(scored, shap_df, cross_role_df)
    osint_packages = enrich_critical_drivers(scored, output_dir=GOLD, max_drivers=25)
    print(json.dumps(model.metrics, indent=2))
    print(f"Trips scored:      {len(scored):,}")
    print(f"CRITICAL+ flagged: {scored['band'].str.startswith('CRITICAL').sum():,}")
    print(f"Case files opened: {n_cases}")
    print(f"OSINT packages:    {len(osint_packages)}")


if __name__ == "__main__":
    main()
