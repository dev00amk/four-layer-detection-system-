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
    for row in df.drop_duplicates(
        ["driver_id", "device_id", "payout_account", "ip_cluster", "store_id"]
    ).itertuples():
        driver = f"driver:{row.driver_id}"
        G.add_node(driver, kind="driver")
        for kind, value, edge_type in (
            ("device", row.device_id, "USES_DEVICE"),
            ("bank", row.payout_account, "USES_PAYOUT"),
            ("ip", row.ip_cluster, "USES_IP"),
        ):
            entity = f"{kind}:{value}"
            G.add_node(entity, kind=kind)
            G.add_edge(driver, entity, edge_type=edge_type)
        # Store nodes expose store-level concentration and potential insider
        # collusion, matching signal 16 and the cross-role risk view.
        if pd.notna(row.store_id):
            store = f"store:{row.store_id}"
            G.add_node(store, kind="store")
            G.add_edge(driver, store, edge_type="DELIVERS_TO")
    rings = []
    ring_id = 0
    for component in nx.connected_components(G):
        drivers = sorted(node.split(":", 1)[1] for node in component if node.startswith("driver:"))
        if len(drivers) < min_ring_size:
            continue
        stores = sorted(node.split(":", 1)[1] for node in component if node.startswith("store:"))
        ring_id += 1
        for driver_id in drivers:
            rings.append(
                {
                    "ring_id": f"R{ring_id:05d}",
                    "driver_id": driver_id,
                    "ring_size": len(drivers),
                    "store_count": len(stores),
                    "store_ids": ", ".join(stores),
                }
            )
    result = pd.DataFrame(
        rings, columns=["ring_id", "driver_id", "ring_size", "store_count", "store_ids"]
    )
    result.to_csv(GRAPH / "fraud_rings.csv", index=False)
    nx.write_graphml(G, GRAPH / "entity_graph.graphml")
    node_types: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        node_type = data.get("kind", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
    print(
        f"Graph: {G.number_of_nodes():,} nodes ({node_types}) | "
        f"{G.number_of_edges():,} edges | {ring_id:,} rings"
    )
    return result


def get_ring_flags(driver_ids, graph_csv=None) -> pd.Series:
    path = Path(graph_csv) if graph_csv else GRAPH / "fraud_rings.csv"
    members = set(pd.read_csv(path)["driver_id"].astype(str)) if path.exists() and path.stat().st_size else set()
    return pd.Series(driver_ids, copy=False).astype(str).isin(members).astype(int)


if __name__ == "__main__":
    build_graph()
