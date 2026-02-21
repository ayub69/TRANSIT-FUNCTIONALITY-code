import networkx as nx

from services.graph_service import _transfer_aware_state_path


def _add_edge(g, u, v, route_id, distance_km, time_min):
    g.add_edge(
        int(u),
        int(v),
        key=int(route_id),
        route_id=int(route_id),
        line_name=f"Route {route_id}",
        distance_km=float(distance_km),
        time_min=float(time_min),
        female_only=False,
        weight=float(distance_km),
    )


def test_shortest_avoids_route_bounce_by_default_penalty():
    # route 9: A->B->C->D (base path, no transfer)
    # route 12: B->C (tiny shortcut) causing 9->12->9 bounce.
    g = nx.MultiDiGraph()
    _add_edge(g, 1, 2, 9, 1.0, 2.0)
    _add_edge(g, 2, 3, 9, 1.0, 2.0)
    _add_edge(g, 3, 4, 9, 1.0, 2.0)
    # Slightly shorter alternate segment; should still lose once switch+bounce penalties apply.
    _add_edge(g, 2, 3, 12, 0.95, 1.9)

    path, edges, _ = _transfer_aware_state_path(g, 1, 4, "shortest")
    route_seq = [e["route_id"] for e in edges]

    assert path == [1, 2, 3, 4]
    assert route_seq == [9, 9, 9]


def test_shortest_allows_switch_when_tradeoff_is_large():
    g = nx.MultiDiGraph()
    _add_edge(g, 1, 2, 9, 10.0, 10.0)
    _add_edge(g, 2, 3, 9, 10.0, 10.0)
    _add_edge(g, 1, 2, 12, 1.0, 1.0)
    _add_edge(g, 2, 3, 12, 1.0, 1.0)

    path, edges, _ = _transfer_aware_state_path(g, 1, 3, "shortest")
    route_seq = [e["route_id"] for e in edges]

    assert path == [1, 2, 3]
    assert route_seq == [12, 12]
