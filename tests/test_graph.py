import networkx as nx

from sentinel.graph import detect_rings


def _add_edge(graph, driver, entity, kind, primary=True):
    graph.add_node(driver, kind="driver")
    graph.add_node(entity, kind=kind)
    graph.add_edge(driver, entity, primary=primary)


def test_multi_entity_pair_forms_ring_but_ip_only_pair_does_not():
    graph = nx.Graph()
    for driver in ("driver:D1", "driver:D2"):
        _add_edge(graph, driver, "device:shared", "device")
        _add_edge(graph, driver, "bank:shared", "bank")
    for driver in ("driver:D3", "driver:D4"):
        _add_edge(graph, driver, "ip:carrier-nat", "ip", primary=False)

    rings = detect_rings(graph)

    assert set(rings["driver_id"]) == {"D1", "D2"}
    assert rings["ring_size"].eq(2).all()
    assert rings["shared_entity_types"].eq("bank, device").all()


def test_single_shared_entity_does_not_form_ring():
    graph = nx.Graph()
    for driver in ("driver:D1", "driver:D2"):
        _add_edge(graph, driver, "device:household", "device")

    assert detect_rings(graph).empty
