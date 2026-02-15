# services/graph_service.py

import networkx as nx
from db_connect import get_connection
import requests

SCHEMA = "smart_transit2"

GRAPH_CACHE = {}
STOP_META = {}
ROUTE_NAME_BY_ID = {}


# -----------------------------
# DB FETCH
# -----------------------------
def fetch_stops():
    q = f"""
        SELECT stop_id, stop_name, lat, lon
        FROM {SCHEMA}.stops
        ORDER BY stop_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            return cur.fetchall()


def fetch_route_names():
    q = f"""
        SELECT route_id, route_name
        FROM {SCHEMA}.routes
        ORDER BY route_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            return {int(rid): (name or "").strip() for rid, name in cur.fetchall()}

def _fetch_leg_details_bulk(pairs: list):
    """
    pairs = [(u, v, route_id), ...]
    returns dict keyed by (u,v,route_id) -> row dict
    """
    if not pairs:
        return {}

    # Build a set of requested tuples exactly as requested.
    expanded = []
    seen = set()
    for u, v, rid in pairs:
        u = int(u); v = int(v); rid = int(rid)
        if (u, v, rid) not in seen:
            expanded.append((u, v, rid))
            seen.add((u, v, rid))

    values_sql = ",".join(["(%s,%s,%s)"] * len(expanded))
    flat = []
    for u, v, rid in expanded:
        flat.extend([u, v, rid])

    q = f"""
        SELECT u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only
        FROM {SCHEMA}.edges
        WHERE (u_stop_id, v_stop_id, route_id) IN ({values_sql});
    """

    out = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, flat)
            for u, v, rid, ln, dist, tmin, fem in cur.fetchall():
                row = {
                    "route_id": int(rid),
                    "line_name": ln if ln else "UNKNOWN",
                    "distance_km": float(dist),
                    "time_min": float(tmin),
                    "female_only": bool(fem),
                }

                u = int(u); v = int(v); rid = int(rid)
                out[(u, v, rid)] = row

    return out


def fetch_edges(gender: str):
    """
    Female: all edges
    Male: exclude female_only edges
    Returns:
      u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only
    """
    gender = (gender or "male").lower().strip()

    if gender == "male":
        q = f"""
            SELECT u_stop_id, v_stop_id, route_id, line_name,
                   distance_km, time_min, female_only
            FROM {SCHEMA}.edges
            WHERE female_only = FALSE;
        """
    else:
        q = f"""
            SELECT u_stop_id, v_stop_id, route_id, line_name,
                   distance_km, time_min, female_only
            FROM {SCHEMA}.edges;
        """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            return cur.fetchall()


# -----------------------------
# GRAPH BUILDERS
# -----------------------------


def _to_bool(x) -> bool:
    """Robust conversion for female_only coming from CSV/DB."""
    if isinstance(x, bool):
        return x
    if x is None:
        return False
    s = str(x).strip().lower()
    return s in ("1", "true", "t", "yes", "y")


def _upsert_route_edge(G: nx.MultiDiGraph, a: int, b: int, route_id: int, meta: dict):
    """
    Keep one edge per (u, v, route_id) in a MultiDiGraph.
    If the same route appears multiple times for the same pair, keep lower weight.
    """
    key = int(route_id)
    if G.has_edge(a, b, key=key):
        current = G[a][b][key]
        if float(meta["weight"]) < float(current.get("weight", float("inf"))):
            current.update(meta)
    else:
        G.add_edge(a, b, key=key, **meta)


def _best_edge_data(G, a: int, b: int) -> dict:
    """
    Returns the minimum-weight edge metadata for a->b.
    Works for DiGraph and MultiDiGraph.
    """
    if not G.has_edge(a, b):
        raise KeyError(f"Edge not found: {a}->{b}")

    if G.is_multigraph():
        candidates = G[a][b].values()
        return min(candidates, key=lambda d: float(d.get("weight", float("inf"))))
    return G[a][b]


def build_shortest_or_fastest(gender: str, mode: str):
    """
    Stop-level graph
    mode = shortest (weight=distance_km) | fastest (weight=time_min)

    Stores per-edge metadata so compute-trip can return full datapoints:
      - distance_km, time_min, route_id, line_name, female_only, weight
    """
    mode = (mode or "shortest").lower().strip()
    if mode not in ("shortest", "fastest"):
        raise ValueError("mode must be 'shortest' or 'fastest'")

    edges = fetch_edges(gender)

    # Keep directed graph with parallel edges (one per route).
    G = nx.MultiDiGraph()

    # Ensure all stops exist as nodes (important if edges don't cover all stops)
    for stop_id in STOP_META:
        G.add_node(int(stop_id))

    for u, v, route_id, line_name, dist, time, female_only in edges:
        u = int(u)
        v = int(v)
        route_id = int(route_id)

        dist_f = float(dist) if dist is not None else 0.0
        time_f = float(time) if time is not None else 0.0

        # choose weight by mode
        weight = dist_f if mode == "shortest" else time_f

        meta = {
            "weight": float(weight),
            "route_id": route_id,
            "line_name": str(line_name) if line_name else "UNKNOWN",
            "distance_km": float(dist_f),
            "time_min": float(time_f),
            "female_only": _to_bool(female_only),
        }

        # forward u -> v (preserve route-specific parallel edges)
        _upsert_route_edge(G, u, v, route_id, meta)

    return G



def build_least_transfer(gender: str):
    """
    Least-transfer state graph:
      Node = (stop_id, route_id)
      Edge cost:
        - same route movement -> 0
        - route change at same stop -> 1
    """
    edges = fetch_edges(gender)
    G = nx.DiGraph()

    stop_routes = {}

    for u, v, route_id, line_name, dist, time, female_only in edges:
        u = int(u); v = int(v); route_id = int(route_id)
        stop_routes.setdefault(u, set()).add(route_id)
        stop_routes.setdefault(v, set()).add(route_id)

        # Ride along same route in DB-defined direction only.
        G.add_edge((u, route_id), (v, route_id), weight=0)

    # Transfer edges at same stop
    for stop, routes in stop_routes.items():
        routes = list(routes)
        if len(routes) < 2:
            continue
        for r1 in routes:
            for r2 in routes:
                if r1 != r2:
                    G.add_edge((stop, r1), (stop, r2), weight=1)

    return G



# -----------------------------
# PUBLIC API
# -----------------------------
def init_graphs():
    """
    Builds and caches 6 graphs from PostgreSQL.
    Call once on FastAPI startup.
    """
    global STOP_META, GRAPH_CACHE, ROUTE_NAME_BY_ID

    STOP_META = {}
    for sid, name, lat, lon in fetch_stops():
        STOP_META[int(sid)] = {
            "stop_id": int(sid),
            "stop_name": name,
            "lat": float(lat),
            "lon": float(lon),
        }

    ROUTE_NAME_BY_ID = fetch_route_names()
    
    GRAPH_CACHE = {
        "female_shortest": build_shortest_or_fastest("female", "shortest"),
        "male_shortest": build_shortest_or_fastest("male", "shortest"),
        "female_fastest": build_shortest_or_fastest("female", "fastest"),
        "male_fastest": build_shortest_or_fastest("male", "fastest"),
        "female_least_transfers": build_least_transfer("female"),
        "male_least_transfers": build_least_transfer("male"),
    }


def get_graph(gender: str, objective: str):
    gender = (gender or "male").lower().strip()
    objective = (objective or "shortest").lower().strip()
    key = f"{gender}_{objective}"
    return GRAPH_CACHE.get(key)


# -----------------------------
# PATH HELPERS (simple totals)
# -----------------------------
def compute_path_stop_graph(origin_stop_id: int, dest_stop_id: int, gender: str, objective: str):
    """
    Works for objective: shortest | fastest
    Returns: {"path": [stop_ids], "total_cost": float}
    total_cost == sum(weight) where weight is distance_km (shortest) or time_min (fastest)
    """
    objective = (objective or "shortest").lower().strip()
    if objective not in ("shortest", "fastest"):
        raise ValueError("objective must be 'shortest' or 'fastest'")

    G = get_graph(gender, objective)
    if G is None:
        raise ValueError("Graph not found")

    if origin_stop_id not in G or dest_stop_id not in G:
        raise ValueError("Origin or destination stop not in graph")

    path = nx.shortest_path(G, origin_stop_id, dest_stop_id, weight="weight")

    total = 0.0
    for a, b in zip(path, path[1:]):
        ed = _best_edge_data(G, a, b)
        total += float(ed["weight"])

    return {"path": path, "total_cost": float(total)}



def compute_path_least_transfers(origin_stop_id: int, dest_stop_id: int, gender: str):
    """
    Least transfers uses state graph nodes: (stop_id, route_id)

    Returns:
      {"path": [stop_ids], "transfers": int}
    """
    origin_stop_id = int(origin_stop_id)
    dest_stop_id = int(dest_stop_id)
    gender = str(gender or "male").lower().strip()

    G = get_graph(gender, "least_transfers")
    if G is None:
        raise ValueError("Graph not found")

    start_states = [n for n in G.nodes() if isinstance(n, tuple) and int(n[0]) == origin_stop_id]
    end_states = [n for n in G.nodes() if isinstance(n, tuple) and int(n[0]) == dest_stop_id]

    if not start_states or not end_states:
        raise ValueError("No route states for origin/destination")

    super_src = ("__SRC__", -1)

    G2 = G.copy()
    for s in start_states:
        G2.add_edge(super_src, s, weight=0)

    dist, paths = nx.single_source_dijkstra(G2, super_src, weight="weight")

    best_t = None
    best_cost = float("inf")
    for t in end_states:
        if t in dist and dist[t] < best_cost:
            best_cost = dist[t]
            best_t = t

    if best_t is None:
        raise ValueError("No path found")

    state_path = paths[best_t]  # includes super_src at start

    # Convert to stop path (ignore super_src)
    stop_path = []
    for node in state_path:
        if node == super_src:
            continue
        if isinstance(node, tuple) and len(node) == 2:
            sid = node[0]
            # sid must be int-able (real stop ids), skip anything else
            if isinstance(sid, int):
                stop_path.append(sid)
            else:
                # if it somehow comes as string digits, allow it
                try:
                    stop_path.append(int(sid))
                except Exception:
                    continue

    # stop ids + compress duplicates
    stop_path = [node[0] for node in state_path if isinstance(node, tuple) and node[0] != "__SRC__"]

    # Build state path without super_src
    clean_state_path = [n for n in state_path if isinstance(n, tuple) and n[0] != "__SRC__"]

    # Compress stop ids for display (optional)
    compressed = []
    for sid in stop_path:
        if not compressed or compressed[-1] != sid:
            compressed.append(sid)

    return {
        "path": compressed,              # stop ids only (nice for UI)
        "state_path": clean_state_path,  # full (stop_id, route_id) sequence (needed for legs)
        "transfers": int(best_cost)
    }



# -----------------------------
# PATH DETAILS (what compute-trip needs)
# -----------------------------
def build_path_details_stop_graph(origin_stop_id: int, dest_stop_id: int, gender: str, objective: str):
    """
    objective: shortest | fastest

    Returns:
      {
        "path_stop_ids": [...],
        "stops": [{stop_id, stop_name, lat, lon}, ...],
        "legs": [
          {
            from_stop_id, to_stop_id,
            from_stop_name, to_stop_name,
            distance_km, time_min, weight,
            route_id, line_name, female_only
          }, ...
        ],
        "totals": {distance_km, time_min, weight}
      }
    """
    objective = (objective or "shortest").lower().strip()
    if objective not in ("shortest", "fastest"):
        raise ValueError("objective must be 'shortest' or 'fastest'")

    G = get_graph(gender, objective)
    if G is None:
        raise ValueError("Graph not found")

    if origin_stop_id not in G or dest_stop_id not in G:
        raise ValueError("Origin or destination stop not in graph")

    path = nx.shortest_path(G, origin_stop_id, dest_stop_id, weight="weight")

    stops = []
    for sid in path:
        meta = STOP_META.get(sid) or {"stop_id": sid, "stop_name": None, "lat": None, "lon": None}
        stops.append(meta)

    legs = []
    total_distance = 0.0
    total_time = 0.0
    total_weight = 0.0

    for a, b in zip(path, path[1:]):
        ed = _best_edge_data(G, a, b)

        distance_km = float(ed.get("distance_km", 0.0))
        time_min = float(ed.get("time_min", 0.0))
        weight = float(ed.get("weight", 0.0))

        leg = {
            "from_stop_id": a,
            "to_stop_id": b,
            "from_stop_name": STOP_META.get(a, {}).get("stop_name"),
            "to_stop_name": STOP_META.get(b, {}).get("stop_name"),
            "distance_km": distance_km,
            "time_min": time_min,
            "weight": weight,
            "route_id": ed.get("route_id"),
            "route_name": ROUTE_NAME_BY_ID.get(ed.get("route_id")),
            "line_name": ed.get("line_name"),
            "female_only": bool(ed.get("female_only", False)),
        }

        legs.append(leg)
        total_distance += distance_km
        total_time += time_min
        total_weight += weight

    return {
        "path_stop_ids": path,
        "stops": stops,
        "legs": legs,
        "totals": {
            "distance_km": round(total_distance, 4),
            "time_min": round(total_time, 4),
            "weight": round(total_weight, 4),
        },
    }


def build_path_details_least_transfers(origin_stop_id: int, dest_stop_id: int, gender: str):
    """
    Least transfers returns:
      {
        "path_stop_ids": [...],
        "stops": [...],
        "legs": [...],
        "transfers": int,
        "totals": {"distance_km": x, "time_min": y, "transfers": int}
      }
    """
    res = compute_path_least_transfers(origin_stop_id, dest_stop_id, gender)

    stop_path = res["path"]
    state_path = res.get("state_path", [])
    transfers = int(res["transfers"])

    # Build stop objects
    stops = []
    for sid in stop_path:
        stops.append(STOP_META.get(sid) or {"stop_id": sid, "stop_name": None, "lat": None, "lon": None})

    # --- Build legs using state_path ---
    # state_path contains transfer steps too: (same stop_id, different route_id)
    # We only create a "ride leg" when stop_id changes.
    ride_pairs = []   # (u, v, route_id)
    ride_steps = []   # keep for reconstruction

    for i in range(len(state_path) - 1):
        (s1, r1) = state_path[i]
        (s2, r2) = state_path[i + 1]

        # transfer edge: same stop, route changes -> no ride leg
        if int(s1) == int(s2):
            continue

        # movement edge should keep same route_id
        route_id = int(r1)
        ride_pairs.append((int(s1), int(s2), route_id))
        ride_steps.append((int(s1), int(s2), route_id))

    # Fetch edge info for all legs in one query
    leg_info = _fetch_leg_details_bulk(ride_pairs)

    legs = []
    total_km = 0.0
    total_min = 0.0

    for (u, v, rid) in ride_steps:
        info = leg_info.get((u, v, rid))
        if info is None:
            info = leg_info.get((v, u, rid))

        # fallback (rare): if missing exact tuple, try ANY edge u->v (same line) - keeps system from crashing

        if info is None:
            info = {"route_id": rid, "line_name": "UNKNOWN", "distance_km": 0.0, "time_min": 0.0, "female_only": False}

        total_km += float(info["distance_km"])
        total_min += float(info["time_min"])

        legs.append({
            "from_stop_id": u,
            "to_stop_id": v,
            "from_stop_name": (STOP_META.get(u, {}) or {}).get("stop_name"),
            "to_stop_name": (STOP_META.get(v, {}) or {}).get("stop_name"),
            "distance_km": round(float(info["distance_km"]), 4),
            "time_min": round(float(info["time_min"]), 4),
            "route_id": int(info["route_id"]),
            "route_name": ROUTE_NAME_BY_ID.get(int(info["route_id"])),
            "line_name": info["line_name"],
            "female_only": bool(info["female_only"]),
        })

    return {
        "path_stop_ids": stop_path,
        "stops": stops,
        "legs": legs,
        "transfers": transfers,
        "totals": {
            "distance_km": round(total_km, 4),
            "time_min": round(total_min, 4),
            "transfers": transfers
        }
    }



def steps_from_route_result(route_result: dict):
    """
    Builds human-readable instructions using the exact legs/lines selected by the graph.

    FIX:
      - Detect transfers based on route_id change (primary)
      - Fallback to line_name change if route_id missing
      - Avoid duplicate "Continue" right after "Take"
    """

    stops = route_result.get("stops", [])
    legs = route_result.get("legs", [])

    if not stops or len(stops) < 2:
        return ["Invalid route"]

    # Stop name helper (route_result already contains stop_name)
    stop_index = {int(s.get("stop_id")): s for s in stops}

    def sname(stop_id: int):
        s = stop_index.get(int(stop_id), {})
        return s.get("stop_name") or f"Stop {stop_id}"

    steps = []
    start_id = int(stops[0]["stop_id"])
    end_id = int(stops[-1]["stop_id"])

    def fmt_line(line_name: str) -> str:
        ln = (line_name or "Unknown").strip()
        if ln.lower().endswith(" line"):
            return ln
        return f"{ln} Line"

    def fmt_route(route_id, route_name=None):
        if route_name:
            return route_name
        return f"Route {route_id}" if route_id is not None else "Unknown Route"

    # If no legs exist, fallback
    if not legs:
        steps.append(f"Start at {sname(start_id)}.")
        for sid in route_result.get("path_stop_ids", [])[1:]:
            steps.append(f"Continue to {sname(int(sid))}.")
        steps.append(f"Arrive at {sname(end_id)}.")
        return steps

    leg_route_id_start = legs[0].get("route_id", None)
    leg_route_id_start = int(leg_route_id_start) if leg_route_id_start is not None else None
    leg_route_name_start = legs[0].get("route_name")
    leg_line_start = fmt_line(legs[0].get("line_name"))
    steps.append(f"Start at {sname(start_id)}.")
    steps.append(
        f"Take {leg_line_start} ({fmt_route(leg_route_id_start, leg_route_name_start)}) from {sname(start_id)}."
    )
    current_route_id = None
    current_line = None

    for i, leg in enumerate(legs):
        a = int(leg["from_stop_id"])
        b = int(leg["to_stop_id"])

        leg_route_id = leg.get("route_id", None)
        leg_route_id = int(leg_route_id) if leg_route_id is not None else None
        leg_route_name = leg.get("route_name")

        leg_line = fmt_line(leg.get("line_name"))

        # First movement leg
        if current_route_id is None and current_line is None:
            current_route_id = leg_route_id
            current_line = leg_line
            steps.append(f"Ride to {sname(b)}.")
            continue

        # Detect transfer:
        # Primary: route_id change
        route_changed = (leg_route_id is not None and current_route_id is not None and leg_route_id != current_route_id)

        # Secondary fallback: line_name change (if route_id missing or unreliable)
        line_changed = (leg_line != current_line)

        if route_changed or (leg_route_id is None and current_route_id is None and line_changed) or (leg_route_id is None and line_changed):
            # Show transfer at the boarding stop of the new leg (a).
            if leg_line == current_line and leg_route_id is not None:
                steps.append(
                    f"Transfer at {sname(a)} to {fmt_route(leg_route_id, leg_route_name)} on {leg_line}."
                )
            else:
                steps.append(
                    f"Transfer at {sname(a)} to {leg_line} ({fmt_route(leg_route_id, leg_route_name)})."
                )
            current_route_id = leg_route_id
            current_line = leg_line
            steps.append(f"Ride to {sname(b)}.")
        else:
            steps.append(f"Continue to {sname(b)}.")

    steps.append(f"Arrive at {sname(end_id)}.")
    return steps



# def steps_from_route_result(route_result: dict):
#     """
#     Builds human-readable instructions using the exact legs/lines selected by the graph.
#     Works best for shortest/fastest where 'legs' exist.
#     """

#     stops = route_result.get("stops", [])
#     legs = route_result.get("legs", [])

#     if not stops or len(stops) < 2:
#         return ["Invalid route"]

#     # Stop name helper (route_result already contains stop_name)
#     def sname(stop_id: int):
#         for s in stops:
#             if s.get("stop_id") == stop_id:
#                 return s.get("stop_name") or f"Stop {stop_id}"
#         return f"Stop {stop_id}"

#     steps = []
#     start_id = stops[0]["stop_id"]
#     end_id = stops[-1]["stop_id"]

#     steps.append(f"Start at {sname(start_id)}")

#     if not legs:
#         # For least_transfers you may not have legs; fallback basic
#         for sid in route_result.get("path_stop_ids", [])[1:]:
#             steps.append(f"Continue to {sname(sid)}")
#         steps.append(f"Arrive at {sname(end_id)}")
#         return steps

#     current_line = None

#     for i, leg in enumerate(legs):
#         a = leg["from_stop_id"]
#         b = leg["to_stop_id"]
#         line = leg.get("line_name") or "UNKNOWN"

#         if current_line is None:
#             current_line = line
#             steps.append(f"Take {line} Line from {sname(a)} to {sname(b)}")
#         else:
#             if line != current_line:
#                 steps.append(f"Transfer to {line} Line at {sname(a)}")
#                 current_line = line
#             steps.append(f"Continue on {line} Line to {sname(b)}")

#     steps.append(f"Arrive at {sname(end_id)}")
#     return steps

