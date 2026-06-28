"""Shared-entity graph detection for coordinated fraud rings."""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd

from .config import GRAPH, SILVER, ensure_directories


def build_graph(min_ring_size: int = 3) -> pd.DataFrame:
    ensure_directories()
    df = pd.read_parquet(
        SILVER / "spark_driver_trips.parquet",
        columns=["driver_id", "device_id", "payout_account", "ip_cluster", "store_id", "isFraud"],
    )
    G = nx.Graph()
    for row in df.drop_duplicates(["driver_id", "device_id", "payout_account", "ip_cluster"]).itertuples():
        driver = f"driver:{row.driver_id}"
        G.add_node(driver, kind="driver")
        for kind, value in (("device", row.device_id), ("bank", row.payout_account), ("ip", row.ip_cluster)):
            entity = f"{kind}:{value}"
            G.add_node(entity, kind=kind)
            G.add_edge(driver, entity)
    rings = []
    ring_id = 0
    for component in nx.connected_components(G):
        drivers = sorted(node.split(":", 1)[1] for node in component if node.startswith("driver:"))
        if len(drivers) < min_ring_size:
            continue
        ring_id += 1
        for driver_id in drivers:
            rings.append({"ring_id": f"R{ring_id:05d}", "driver_id": driver_id, "ring_size": len(drivers)})
    result = pd.DataFrame(rings, columns=["ring_id", "driver_id", "ring_size"])
    result.to_csv(GRAPH / "fraud_rings.csv", index=False)
    nx.write_graphml(G, GRAPH / "entity_graph.graphml")
    print(f"Graph: {G.number_of_nodes():,} nodes | {G.number_of_edges():,} edges | {ring_id:,} rings")
    return result


def get_ring_flags(driver_ids, graph_csv=None) -> pd.Series:
    path = Path(graph_csv) if graph_csv else GRAPH / "fraud_rings.csv"
    members = set(pd.read_csv(path)["driver_id"].astype(str)) if path.exists() and path.stat().st_size else set()
    return pd.Series(driver_ids, copy=False).astype(str).isin(members).astype(int)


if __name__ == "__main__":
    build_graph()

