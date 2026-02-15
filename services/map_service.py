# services/map_service.py

from typing import Dict, List, Any, Tuple, Optional
from db_connect import get_connection
import requests
from fastapi import HTTPException
SCHEMA = "smart_transit2"

LINE_COLORS = {
    "Red":   "#E53935",
    "Red Line": "#E53935",
    "Green": "#43A047",
    "Green Line": "#43A047",
    "White": "#FFFFFF",
    "Pink":  "#EC407A",
    "Pink Line": "#EC407A",
    "EV":    "#FFFFFF",
    "EV Line": "#FFFFFF",
    "Double Decker": "#5D4037",
}

MAP_CACHE: Dict[str, Any] = {
    "routes_geojson": None,
    "stops_geojson": None,
    "stop_details": {},
}

# -----------------------------
# DB BULK FETCH (FAST)
# -----------------------------

def fetch_all_stops() -> List[Tuple[int, str, float, float]]:
    q = f"""
        SELECT stop_id, stop_name, lat, lon
        FROM {SCHEMA}.stops
        ORDER BY stop_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            return cur.fetchall()


def fetch_stop_connected_lines_bulk() -> Dict[int, List[str]]:
    """
    Returns {stop_id: [line1, line2, ...]} using ONE query.
    """
    q = f"""
        SELECT stop_id, array_agg(DISTINCT line_name ORDER BY line_name) AS lines
        FROM (
            SELECT u_stop_id AS stop_id, line_name FROM {SCHEMA}.edges
            UNION ALL
            SELECT v_stop_id AS stop_id, line_name FROM {SCHEMA}.edges
        ) t
        GROUP BY stop_id
        ORDER BY stop_id;
    """
    out: Dict[int, List[str]] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            for sid, lines in cur.fetchall():
                out[int(sid)] = list(lines) if lines else []
    return out


def fetch_all_route_edges_with_line() -> List[Tuple[int, str, int, int]]:
    """
    Returns rows: (route_id, line_name, u_stop_id, v_stop_id) for ALL routes in ONE query.
    """
    q = f"""
        SELECT
            e.route_id,
            COALESCE(NULLIF(e.line_name, ''), r.route_name) AS line_name,
            e.u_stop_id,
            e.v_stop_id
        FROM {SCHEMA}.edges e
        LEFT JOIN {SCHEMA}.routes r ON r.route_id = e.route_id
        ORDER BY e.route_id, e.u_stop_id, e.v_stop_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            return cur.fetchall()


# -----------------------------
# HELPERS
# -----------------------------

def _color_for_line(line_name: str) -> str:
    ln = (line_name or "").strip()
    if ln in LINE_COLORS:
        return LINE_COLORS[ln]
    for k, v in LINE_COLORS.items():
        if k.lower() == ln.lower():
            return v
    return "#9E9E9E"


def _build_stop_lookup(stops_rows: List[Tuple[int, str, float, float]]) -> Dict[int, Dict[str, Any]]:
    lookup = {}
    for sid, name, lat, lon in stops_rows:
        lookup[int(sid)] = {
            "stop_id": int(sid),
            "stop_name": name,
            "lat": float(lat),
            "lon": float(lon),
            "services": {
                "ramps": None,
                "shelter": None,
                "accessible": None,
            }
        }
    return lookup


def _build_route_sequence(edges_uv: List[Tuple[int, int]]) -> List[int]:
    """
    Builds a chain order from directed edges u->v.
    If the data has branches, this produces the main forward chain.
    """
    if not edges_uv:
        return []

    next_map: Dict[int, int] = {}
    indeg: Dict[int, int] = {}

    for u, v in edges_uv:
        u = int(u); v = int(v)
        # keep first successor to avoid overwrite chaos
        next_map.setdefault(u, v)
        indeg[v] = indeg.get(v, 0) + 1
        indeg.setdefault(u, indeg.get(u, 0))

    starts = [u for u in next_map.keys() if indeg.get(u, 0) == 0]
    start = starts[0] if starts else list(next_map.keys())[0]

    seq = [start]
    seen = {start}
    cur = start
    while cur in next_map:
        nxt = next_map[cur]
        if nxt in seen:
            break
        seq.append(nxt)
        seen.add(nxt)
        cur = nxt
    return seq


# -----------------------------
# BUILD GEOJSON (FAST)
# -----------------------------

def build_routes_geojson() -> Dict[str, Any]:
    stops_rows = fetch_all_stops()
    stop_lookup = _build_stop_lookup(stops_rows)

    rows = fetch_all_route_edges_with_line()

    # group edges by route_id
    route_edges: Dict[int, Dict[str, Any]] = {}
    for rid, ln, u, v in rows:
        rid = int(rid)
        route_edges.setdefault(rid, {"line_name": ln, "edges": []})
        route_edges[rid]["edges"].append((int(u), int(v)))

    features = []

    for rid, info in route_edges.items():
        ln = info["line_name"]
        seq = _build_route_sequence(info["edges"])
        if len(seq) < 2:
            continue

        coords = []
        for sid in seq:
            s = stop_lookup.get(int(sid))
            if not s:
                continue
            coords.append([s["lon"], s["lat"]])

        if len(coords) < 2:
            continue

        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "line_name": ln,
                "route_id": rid,
                "color": _color_for_line(ln),
                "stop_count": len(coords),
            }
        })

    return {"type": "FeatureCollection", "features": features}


def build_stops_geojson() -> Dict[str, Any]:
    stops_rows = fetch_all_stops()
    stop_lookup = _build_stop_lookup(stops_rows)

    connected_map = fetch_stop_connected_lines_bulk()

    features = []
    for sid, s in stop_lookup.items():
        connected = connected_map.get(sid, [])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {
                "stop_id": s["stop_id"],
                "stop_code": str(s["stop_id"]),
                "stop_name": s["stop_name"],
                "connected_lines": connected,
                "services": s["services"],
            }
        })

    return {"type": "FeatureCollection", "features": features}


def build_stop_details_from_cache(stop_id: int) -> Dict[str, Any]:
    stop_id = int(stop_id)
    cached = MAP_CACHE.get("stop_details", {}).get(stop_id)
    if not cached:
        raise ValueError("Stop not found")
    return cached


# -----------------------------
# PUBLIC CACHE API
# -----------------------------

def init_map_cache():
    """
    FAST startup: uses only 3 bulk queries total.
    """
    routes_geojson = build_routes_geojson()
    stops_geojson = build_stops_geojson()

    # Build stop_details dict from stops_geojson (no extra DB calls)
    stop_details = {}
    for feat in stops_geojson.get("features", []):
        props = feat["properties"]
        sid = int(props["stop_id"])
        lon, lat = feat["geometry"]["coordinates"]
        stop_details[sid] = {
            "stop_id": sid,
            "stop_code": props.get("stop_code"),
            "stop_name": props.get("stop_name"),
            "lat": float(lat),
            "lon": float(lon),
            "connected_lines": props.get("connected_lines", []),
            "services": props.get("services", {}),
        }

    MAP_CACHE["routes_geojson"] = routes_geojson
    MAP_CACHE["stops_geojson"] = stops_geojson
    MAP_CACHE["stop_details"] = stop_details


def get_routes_geojson() -> Dict[str, Any]:
    return MAP_CACHE["routes_geojson"] or build_routes_geojson()


def get_stops_geojson() -> Dict[str, Any]:
    return MAP_CACHE["stops_geojson"] or build_stops_geojson()


def get_stop_details(stop_id: int) -> Dict[str, Any]:
    return build_stop_details_from_cache(stop_id)

#polyline for road path 
OSRM_BASE_URL = "https://router.project-osrm.org"  # or your own OSRM

def build_road_polyline_from_stops(stops: list, profile: str = "driving"):
    if not stops or len(stops) < 2:
        return None

    coords = ";".join(
        f"{s['lon']},{s['lat']}"
        for s in stops
        if s.get("lat") is not None and s.get("lon") is not None
    )

    if coords.count(";") < 1:
        return None

    url = (
        f"{OSRM_BASE_URL}/route/v1/{profile}/{coords}"
        f"?overview=full&geometries=geojson"
    )

    r = requests.get(url, timeout=20).json()
    if r.get("code") != "Ok":
        return None

    route0 = r["routes"][0]
    return {
        "geometry": route0["geometry"],     # GeoJSON LineString
    }
