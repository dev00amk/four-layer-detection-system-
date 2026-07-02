"""Shared-entity graph detection for coordinated fraud rings."""
from __future__ import annotations

import logging
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd

from .config import GRAPH, SILVER, ensure_directories

log = logging.getLogger(__name__)


def detect_rings(
    graph: nx.Graph,
    min_size: int = 2,
    min_shared_entity_types: int = 2,
) -> pd.DataFrame:
    """
    Detect coordinated driver components from high-confidence entity overlap.

    IP edges remain available to investigators but are excluded from ring
    formation because carrier NAT can connect unrelated drivers. A driver pair
    must share at least two of device, bank, or store before it creates a ring
    edge; this catches strong two-account coordination without flagging a
    household or common-store coincidence on one entity alone.
    """
    driver_entities: dict[str, dict[str, set[str]]] = {}
    for driver, data in graph.nodes(data=True):
        if data.get("kind") != "driver":
            continue
        entities: dict[str, set[str]] = {"device": set(), "bank": set(), "store": set()}
        for entity in graph.neighbors(driver):
            edge = graph.edges[driver, entity]
            kind = graph.nodes[entity].get("kind")
            if edge.get("primary", True) and kind in entities:
                entities[kind].add(entity)
        driver_entities[driver] = entities

    # Exact two-entity signatures prevent transitive chaining: A sharing a
    # device with B and B sharing a bank with C does not implicate A with C.
    signature_drivers: dict[tuple[str, str], set[str]] = {}
    entity_type_pairs = list(combinations(("device", "bank", "store"), 2))
    for driver, entities in driver_entities.items():
        for left_type, right_type in entity_type_pairs:
            for left in entities[left_type]:
                for right in entities[right_type]:
                    signature = tuple(sorted((left, right)))
                    signature_drivers.setdefault((signature[0], signature[1]), set()).add(driver)

    candidate_groups: dict[frozenset[str], set[str]] = {}
    for signature, drivers in signature_drivers.items():
        if len(drivers) < min_size:
            continue
        entity_types = {graph.nodes[entity].get("kind") for entity in signature}
        if len(entity_types) < min_shared_entity_types:
            continue
        infrastructure = next(
            (entity for entity in signature if graph.nodes[entity].get("kind") in {"device", "bank"}),
            None,
        )
        if infrastructure is None:
            continue
        infrastructure_driver_count = sum(
            1 for node in graph.neighbors(infrastructure) if node.startswith("driver:")
        )
        # Store overlap is corroborating only when the shared device or bank is
        # itself selective. Common infrastructure is not ring-quality evidence.
        if "store" in entity_types and infrastructure_driver_count > 3:
            continue
        candidate_groups.setdefault(frozenset(drivers), set()).update(entity_types)

    rings: list[dict[str, object]] = []
    ordered_groups = sorted(
        candidate_groups.items(),
        key=lambda item: (-len(item[0]), sorted(item[0])),
    )
    for ring_id, (component, shared_type_set) in enumerate(ordered_groups, start=1):
        ring_drivers = sorted(component)
        shared_type_names = sorted(shared_type_set)
        common_stores = set.intersection(
            *(driver_entities[driver]["store"] for driver in ring_drivers)
        )
        shared_stores = sorted(store.split(":", 1)[1] for store in common_stores)
        for driver in ring_drivers:
            rings.append(
                {
                    "ring_id": f"R{ring_id:05d}",
                    "driver_id": driver.split(":", 1)[1],
                    "ring_size": len(ring_drivers),
                    "store_count": len(shared_stores),
                    "store_ids": ", ".join(shared_stores),
                    "shared_entity_type_count": len(shared_type_names),
                    "shared_entity_types": ", ".join(shared_type_names),
                }
            )
    return pd.DataFrame(
        rings,
        columns=[
            "ring_id",
            "driver_id",
            "ring_size",
            "store_count",
            "store_ids",
            "shared_entity_type_count",
            "shared_entity_types",
        ],
    )


def build_graph(min_ring_size: int = 2) -> pd.DataFrame:
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
        ):
            entity = f"{kind}:{value}"
            G.add_node(entity, kind=kind)
            G.add_edge(driver, entity, edge_type=edge_type, weight=1.0, primary=True)
        # Carrier NAT can connect unrelated drivers, so IP is retained only as
        # low-confidence investigator context and never forms primary rings.
        if pd.notna(row.ip_cluster):
            ip = f"ip:{row.ip_cluster}"
            G.add_node(ip, kind="ip", note="carrier NAT FP risk; corroboration only")
            G.add_edge(
                driver,
                ip,
                edge_type="SHARES_IP",
                weight=0.2,
                primary=False,
            )
        # Store nodes expose store-level concentration and potential insider
        # collusion, matching signal 16 and the cross-role risk view.
        if pd.notna(row.store_id):
            store = f"store:{row.store_id}"
            G.add_node(store, kind="store")
            G.add_edge(driver, store, edge_type="DELIVERS_TO", weight=1.0, primary=True)
    result = detect_rings(G, min_size=min_ring_size)
    result.to_csv(GRAPH / "fraud_rings.csv", index=False)
    nx.write_graphml(G, GRAPH / "entity_graph.graphml")
    node_types: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        node_type = data.get("kind", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
    log.info(
        "graph_built",
        extra={
            "nodes": G.number_of_nodes(),
            "node_types": node_types,
            "edges": G.number_of_edges(),
            "rings": result["ring_id"].nunique(),
        },
    )
    return result


def get_ring_flags(driver_ids, graph_csv=None) -> tuple[pd.Series, pd.Series]:
    """Return graph flags and ring sizes aligned to the supplied driver IDs."""
    path = Path(graph_csv) if graph_csv else GRAPH / "fraud_rings.csv"
    if path.exists() and path.stat().st_size:
        rings = pd.read_csv(path)
        sizes = rings.groupby(rings["driver_id"].astype(str))["ring_size"].max()
    else:
        sizes = pd.Series(dtype=int)
    ids = pd.Series(driver_ids, copy=False).astype(str)
    ring_sizes = ids.map(sizes).fillna(0).astype(int)
    return ring_sizes.gt(0).astype(int), ring_sizes


if __name__ == "__main__":
    build_graph()
