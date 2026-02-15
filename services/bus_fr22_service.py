# services/bus_fr22_service.py

from __future__ import annotations
from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Optional

from db_connect import get_connection
from services.timetable_config import TIMETABLE
from services.nearest_stop_service import haversine_km

SCHEMA = "smart_transit2"


# -----------------------------
# Helpers: time parsing
# -----------------------------
def _parse_hhmm(s: str) -> time:
    h, m = s.strip().split(":")
    return time(int(h), int(m), 0)
def _canonical_line_name(name: str) -> str:
    n = (name or "").strip().lower()
    if n.endswith(" line"):
        n = n[:-5].strip()
    for k in TIMETABLE.keys():
        kk = k.lower().strip()
        if kk == n or f"{kk} line" == (name or "").strip().lower():
            return k
    # if not found, return original stripped
    raw = (name or "").strip()
    if raw.lower().endswith(" line"):
        return raw[:-5].strip()
    return raw


def _to_seconds(t: time) -> int:
    return t.hour * 3600 + t.minute * 60 + t.second


def _from_seconds(sec: int) -> time:
    sec = sec % (24 * 3600)
    h = sec // 3600
    sec %= 3600
    m = sec // 60
    s = sec % 60
    return time(h, m, s)


def _in_window(t: time, start: time, end: time) -> bool:
    # assumes windows don't cross midnight (true for your case)
    return start <= t < end


def _is_peak(line_name: str, t: time) -> bool:
    cfg = TIMETABLE.get(line_name)
    if not cfg:
        return False
    for a, b in cfg.get("peak_windows", []):
        if _in_window(t, _parse_hhmm(a), _parse_hhmm(b)):
            return True
    return False


def _is_in_service_window(line_name: str, t: time) -> bool:
    cfg = TIMETABLE.get(line_name, {})
    # Pink uses service_windows; others use first/last
    windows = cfg.get("service_windows")
    if windows:
        for a, b in windows:
            if _in_window(t, _parse_hhmm(a), _parse_hhmm(b)):
                return True
        return False

    first_dep = cfg.get("first_departure")
    last_dep = cfg.get("last_departure")
    if not first_dep or not last_dep:
        return False
    return _parse_hhmm(first_dep) <= t <= _parse_hhmm(last_dep)


def _freq_minutes(line_name: str, t: time) -> int:
    cfg = TIMETABLE.get(line_name, {})
    if cfg.get("service_windows"):
        # Pink: simplest — treat service windows as active windows; use freq_peak_min
        return int(cfg.get("freq_peak_min", 20))

    if _is_peak(line_name, t):
        return int(cfg.get("freq_peak_min", 15))
    return int(cfg.get("freq_offpeak_min", 30))


def _line_is_female_only(line_name: str) -> bool:
    return bool(TIMETABLE.get(line_name, {}).get("female_only", False))


# -----------------------------
# DB fetch
# -----------------------------

def fetch_line_route_ids(line_name: str) -> List[int]:
    q = f"""
        SELECT DISTINCT route_id
        FROM {SCHEMA}.edges
        WHERE LOWER(line_name) = LOWER(%s)
        ORDER BY route_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, [line_name])
            return [int(r[0]) for r in cur.fetchall()]


def fetch_route_edges(route_id: int) -> List[Tuple[int, int, float]]:
    """
    Returns ordered edges NOT guaranteed; just raw u->v with time_min
    """
    q = f"""
        SELECT u_stop_id, v_stop_id, time_min
        FROM {SCHEMA}.edges
        WHERE route_id = %s
        ORDER BY edge_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, [route_id])
            rows = cur.fetchall()
            out = []
            for u, v, tmin in rows:
                out.append((int(u), int(v), float(tmin)))
            return out


def fetch_stop_meta(stop_ids: List[int]) -> Dict[int, dict]:
    if not stop_ids:
        return {}
    q = f"""
        SELECT stop_id, stop_name, lat, lon
        FROM {SCHEMA}.stops
        WHERE stop_id = ANY(%s);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, [stop_ids])
            rows = cur.fetchall()

    meta = {}
    for sid, name, lat, lon in rows:
        meta[int(sid)] = {
            "stop_id": int(sid),
            "stop_name": name,
            "lat": float(lat),
            "lon": float(lon)
        }
    return meta
def fetch_all_stops() -> List[dict]:
    q = f"SELECT stop_id, stop_name, lat, lon FROM {SCHEMA}.stops;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            rows = cur.fetchall()
    return [{"stop_id": int(sid), "stop_name": name, "lat": float(lat), "lon": float(lon)} for sid, name, lat, lon in rows]


def fetch_stop_ids_within_radius(user_lat: float, user_lon: float, radius_km: float) -> List[int]:
    stops = fetch_all_stops()
    near = []
    for s in stops:
        d = haversine_km(user_lat, user_lon, s["lat"], s["lon"])
        if d <= radius_km:
            near.append(int(s["stop_id"]))
    return near
def fetch_routes_for_stop_ids(stop_ids: List[int]) -> List[Tuple[int, str]]:
    """
    Returns [(route_id, line_name), ...] for any route that touches these stops.
    """
    if not stop_ids:
        return []

    q = f"""
        SELECT DISTINCT route_id, line_name
        FROM {SCHEMA}.edges
        WHERE u_stop_id = ANY(%s) OR v_stop_id = ANY(%s)
        ORDER BY route_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q, [stop_ids, stop_ids])
            rows = cur.fetchall()
    return [(int(rid), str(ln)) for rid, ln in rows]

MAX_PER_ROUTE = 5          # show max 5 buses per route_id
MAX_ARRIVALS_PER_ROUTE = 5 # keep arrivals consistent with live

def _pick_evenly_spaced(items, k: int):
    """
    Returns up to k items spread across the list.
    items must already be sorted in meaningful order.
    """
    if not items or k <= 0:
        return []
    if len(items) <= k:
        return items

    last = len(items) - 1
    # k indices between 0..last
    idxs = [round(i * last / (k - 1)) for i in range(k)]
    # remove duplicates caused by rounding
    idxs = sorted(set(int(x) for x in idxs))
    return [items[i] for i in idxs]

# -----------------------------
# Build ordered stop sequence from one-way chain
# -----------------------------
def build_route_sequence(route_id: int):
    edges = fetch_route_edges(route_id)
    if not edges:
        return [], {}, {}

    # allow only ONE successor per u; if multiple exist, keep the smallest time
    next_map = {}
    edge_time = {}
    indeg = {}
    outdeg = {}

    for u, v, tmin in edges:
        u = int(u); v = int(v)
        tsec = int(round(float(tmin) * 60))

        # keep best successor if duplicates
        if u in next_map:
            old_v = next_map[u]
            old_t = edge_time.get((u, old_v), 10**9)
            if tsec < old_t:
                next_map[u] = v
                edge_time[(u, v)] = tsec
        else:
            next_map[u] = v
            edge_time[(u, v)] = tsec

        indeg[v] = indeg.get(v, 0) + 1
        outdeg[u] = outdeg.get(u, 0) + 1
        indeg.setdefault(u, indeg.get(u, 0))
        outdeg.setdefault(v, outdeg.get(v, 0))

    # start: node with outdeg>0 and indeg==0
    starts = [n for n in next_map.keys() if indeg.get(n, 0) == 0]
    start = starts[0] if starts else list(next_map.keys())[0]

    # build sequence + cumulative seconds
    seq = [start]
    cum_sec_by_stop = {start: 0}
    seen = {start}
    cur = start
    total = 0

    while cur in next_map:
        nxt = next_map[cur]
        if nxt in seen:
            break
        seg = edge_time.get((cur, nxt), 0)
        total += int(seg)
        seq.append(nxt)
        cum_sec_by_stop[nxt] = total
        seen.add(nxt)
        cur = nxt

    return seq, edge_time, cum_sec_by_stop




# -----------------------------
# Generate departure times (virtual "published timetable")
# -----------------------------
def generate_departures_for_window(line_name: str, start_t: time, end_t: time) -> List[time]:
    """
    Creates departures between start_t and end_t using varying freq
    depending on peak/offpeak (or Pink service windows).
    """
    deps = []
    cur = start_t
    while cur <= end_t:
        if _is_in_service_window(line_name, cur):
            deps.append(cur)
        # step by frequency at this time
        step = _freq_minutes(line_name, cur)
        cur = _from_seconds(_to_seconds(cur) + step * 60)
    return deps


def generate_departures_today(line_name: str) -> List[time]:
    cfg = TIMETABLE.get(line_name)
    if not cfg:
        return []

    # Pink uses service_windows only
    if cfg.get("service_windows"):
        deps = []
        for a, b in cfg["service_windows"]:
            deps.extend(generate_departures_for_window(line_name, _parse_hhmm(a), _parse_hhmm(b)))
        # de-dup + sort
        deps = sorted({d.isoformat(): d for d in deps}.values(), key=lambda x: _to_seconds(x))
        return deps

    first_dep = _parse_hhmm(cfg["first_departure"])
    last_dep = _parse_hhmm(cfg["last_departure"])
    return generate_departures_for_window(line_name, first_dep, last_dep)


# -----------------------------
# Core: arrival predictions (FR2.2.1)
# -----------------------------
from datetime import datetime, timedelta, date

def get_arrival_predictions(
    stop_id: int,
    gender: str = "male",
    minutes_ahead: int = 60,
    line_name: Optional[str] = None
):
    """
    FR2.2.1:
    - Uses timetable rules (published) + avg edge time_min (from DB edges.time_min)
    - Returns upcoming arrivals at the given stop_id
    """
    stop_id = int(stop_id)
    gender = str(gender or "male").lower().strip()
    line_name = _canonical_line_name(line_name) if line_name else None

    now_dt = datetime.now()
    end_dt = now_dt + timedelta(minutes=minutes_ahead)

    results = []
    MAX_ARRIVALS_PER_ROUTE = 5
    per_route_count = {}
    # which lines?
    lines = [line_name] if line_name else list(TIMETABLE.keys())

    for ln in lines:
        # gender filter: male cannot see female-only line (Pink)
        if gender == "male" and _line_is_female_only(ln):
            continue

        route_ids = fetch_line_route_ids(ln)
        if not route_ids:
            continue

        departures = generate_departures_today(ln)
        if not departures:
            continue

        for rid in route_ids:
            route_key = (ln, int(rid))
            # IMPORTANT: build_route_sequence must return cum_sec_by_stop
            # seq: [stop_ids], edge_time_sec: {(u,v): seconds}, cum_sec_by_stop: {stop_id: cum_seconds}
            seq, edge_time_sec, cum_sec_by_stop = build_route_sequence(rid)
            if not seq or not cum_sec_by_stop:
                continue

            # stop not on this route chain
            if stop_id not in cum_sec_by_stop:
                continue

            travel_sec = int(cum_sec_by_stop[stop_id])

            for dep in departures:
                # build real datetime for dep today
                dep_dt = datetime.combine(now_dt.date(), dep)

                # predicted arrival datetime
                arr_dt = dep_dt + timedelta(seconds=travel_sec)

                # filter within [now_dt, end_dt]
                if now_dt <= arr_dt <= end_dt:
                    if per_route_count.get(route_key, 0) >= MAX_ARRIVALS_PER_ROUTE:
                        continue

                    results.append({
                        "line_name": ln,
                        "route_id": int(rid),
                        "stop_id": stop_id,
                        "scheduled_arrival_time": arr_dt.time().isoformat(timespec="minutes"),
                        "reference": True,
                        "note": "Reference ETA (timetable + avg segment durations)"
                    })
                    per_route_count[route_key] = per_route_count.get(route_key, 0) + 1

    # sort by actual time string is ok since times are same-day within window
    results.sort(key=lambda x: x["scheduled_arrival_time"])

    return {
        "stop_id": stop_id,
        "gender": gender,
        "line_name": line_name,
        "as_of": now_dt.isoformat(timespec="minutes"),
        "window_minutes": minutes_ahead,
        "arrivals": results[:50]
    }



# -----------------------------
# Core: live bus tracking (FR2.2.2)
# -----------------------------
def get_live_bus_positions(
    gender: str,
    line_name: str,
    max_buses: int = 100,
    user_lat: float | None = None,
    user_lon: float | None = None,
    nearest_k: int = 10,
):


    """
    FR2.2.2:
    - Simulates buses progressing along timetable
    - Uses departure list + route sequence + time_min edges
    - Interpolates bus position between two stops
    """
    if line_name == "pink":
        gender="female"
    gender = str(gender or "male").lower().strip()
    line_name = _canonical_line_name(line_name)
    if line_name == "double decker":
        max_buses=5
    if line_name == "red":
        max_buses = 100
    
    if gender == "male" and _line_is_female_only(line_name):
        return {
            "gender": gender,
            "line_name": line_name,
            "as_of": datetime.now().isoformat(timespec="seconds"),
            "buses": [],
            "note": "Male users cannot access female-only line tracking."
        }

    now_dt = datetime.now()
    now_t = now_dt.time()
    now_sec = _to_seconds(now_t)

    route_ids = fetch_line_route_ids(line_name)
    departures = generate_departures_today(line_name)

    buses_out = []
    
    
    MAX_BUSES_PER_ROUTE = 5

    for rid in route_ids:
        seq, edge_time_sec, cum_sec_by_stop = build_route_sequence(rid)
        
        if not seq or len(seq) < 2:
            continue

        # Build cumulative seconds aligned with seq
        cum_sec = []
        for sid in seq:
            if sid not in cum_sec_by_stop:
                cum_sec = []
                break
            cum_sec.append(int(cum_sec_by_stop[sid]))
        if not cum_sec:
            continue

        stop_meta = fetch_stop_meta(seq)

        # -------------------------------------------------------
        # NEW: collect active departures first (timetable-based)
        # -------------------------------------------------------
        active = []
        for dep in departures:
            dep_sec = _to_seconds(dep)
            trip_start = dep_sec
            trip_end = dep_sec + cum_sec[-1]

            if trip_start <= now_sec <= trip_end:
                t_into = now_sec - trip_start
                active.append((dep, dep_sec, t_into))

        if not active:
            continue

        active.sort(key=lambda x: x[2])
        chosen = _pick_evenly_spaced(active, MAX_PER_ROUTE)

        # -------------------------------------------------------
        # Now build bus objects only for the chosen ones
        # -------------------------------------------------------
        for dep, dep_sec, t_into in chosen:
            trip_start = dep_sec

            # Find segment i such that cum_sec[i] <= t_into < cum_sec[i+1]
            seg_i = None
            for i in range(len(cum_sec) - 1):
                if cum_sec[i] <= t_into < cum_sec[i + 1]:
                    seg_i = i
                    break
            if seg_i is None:
                continue

            a_id = seq[seg_i]
            b_id = seq[seg_i + 1]
            a = stop_meta.get(a_id)
            b = stop_meta.get(b_id)
            if not a or not b:
                continue

            seg_start = cum_sec[seg_i]
            seg_end = cum_sec[seg_i + 1]
            seg_len = max(1, seg_end - seg_start)

            progress = (t_into - seg_start) / seg_len
            progress = max(0.0, min(1.0, progress))

            lat = a["lat"] + (b["lat"] - a["lat"]) * progress
            lon = a["lon"] + (b["lon"] - a["lon"]) * progress

            eta_sec = trip_start + seg_end

            buses_out.append({
                "bus_id": f"{line_name}-{rid}-{dep.isoformat(timespec='minutes')}",
                "line_name": line_name,
                "route_id": int(rid),
                "departure_time": dep.isoformat(timespec="minutes"),
                "from_stop": {"stop_id": a_id, "stop_name": a["stop_name"]},
                "to_stop": {"stop_id": b_id, "stop_name": b["stop_name"]},
                "progress_0_to_1": round(progress, 3),
                "position": {"lat": round(lat, 6), "lon": round(lon, 6)},
                "next_stop_eta_time": _from_seconds(eta_sec).isoformat(timespec="seconds"),
                "note": "Simulated timetable-based progression"
            })

            if len(buses_out) >= max_buses:
                break

        if len(buses_out) >= max_buses:
            break
        # NEW: if user location provided, return nearest buses
    if user_lat is not None and user_lon is not None and buses_out:
        ulat = float(user_lat)
        ulon = float(user_lon)

        for b in buses_out:
            blat = float(b["position"]["lat"])
            blon = float(b["position"]["lon"])
            b["distance_to_user_km"] = round(haversine_km(ulat, ulon, blat, blon), 4)

        buses_out.sort(key=lambda x: x.get("distance_to_user_km", 1e9))
        buses_out = buses_out[:int(nearest_k)]


    return {
        "gender": gender,
        "line_name": line_name,
        "as_of": now_dt.isoformat(timespec="seconds"),
        "buses": buses_out
    }

from bisect import bisect_left, bisect_right

def get_live_buses_within_radius(
    gender: str,
    user_lat: float,
    user_lon: float,
    radius_km: float = 1.5,
    nearest_k: int = 15,
    max_buses: int = 200,
):
    gender = str(gender or "male").lower().strip()
    ulat = float(user_lat)
    ulon = float(user_lon)
    radius_km = float(radius_km)
    nearest_k = int(nearest_k)

    # HARD CAPS (tune for performance)
    MAX_BUSES_PER_ROUTE = 5
    MAX_ROUTES_TO_SIMULATE = 25  # <- hard route cap (increase/decrease)

    now_dt = datetime.now()
    now_sec = _to_seconds(now_dt.time())

    # 1) find nearby stops
    nearby_stop_ids = fetch_stop_ids_within_radius(ulat, ulon, radius_km)
    if not nearby_stop_ids:
        return {
            "gender": gender,
            "as_of": now_dt.isoformat(timespec="seconds"),
            "center": {"lat": ulat, "lon": ulon},
            "radius_km": radius_km,
            "buses": [],
            "note": "No stops found within radius."
        }

    # 2) find candidate routes that touch these stops
    route_pairs = fetch_routes_for_stop_ids(nearby_stop_ids)  # [(rid, line_name)]
    if not route_pairs:
        return {
            "gender": gender,
            "as_of": now_dt.isoformat(timespec="seconds"),
            "center": {"lat": ulat, "lon": ulon},
            "radius_km": radius_km,
            "buses": [],
            "note": "No routes found near this location."
        }

    # ✅ HARD ROUTE CAP (prevents huge loops)
    route_pairs = route_pairs[:MAX_ROUTES_TO_SIMULATE]

    buses_out = []

    # 3) simulate buses only for those routes
    for rid, ln in route_pairs:
        ln = _canonical_line_name(ln)

        # gender restriction
        if gender == "male" and _line_is_female_only(ln):
            continue

        departures = generate_departures_today(ln)
        if not departures:
            continue

        seq, edge_time_sec, cum_sec_by_stop = build_route_sequence(rid)
        if not seq or len(seq) < 2 or not cum_sec_by_stop:
            continue

        # Build cumulative seconds aligned with seq
        cum_sec = []
        ok = True
        for sid in seq:
            if sid not in cum_sec_by_stop:
                ok = False
                break
            cum_sec.append(int(cum_sec_by_stop[sid]))
        if not ok or not cum_sec:
            continue

        stop_meta = fetch_stop_meta(seq)

        # ---------------------------------------------------------
        # FAST ACTIVE FILTER:
        # bus is active if dep_sec <= now_sec <= dep_sec + trip_dur
        # => now_sec - trip_dur <= dep_sec <= now_sec
        # ---------------------------------------------------------
        trip_dur = int(cum_sec[-1])

        # convert departures to seconds-of-day and sort (small list)
        dep_secs = [_to_seconds(d) for d in departures]
        dep_secs.sort()

        lo = now_sec - trip_dur
        hi = now_sec

        i0 = bisect_left(dep_secs, lo)
        i1 = bisect_right(dep_secs, hi)
        active_dep_secs = dep_secs[i0:i1]

        if not active_dep_secs:
            continue

        # ✅ HARD ENFORCE: NEVER generate more than 5 per route
        chosen_dep_secs = _pick_evenly_spaced(active_dep_secs, MAX_BUSES_PER_ROUTE)

        for dep_sec in chosen_dep_secs:
            t_into = now_sec - dep_sec  # seconds since departure

            # find segment i such that cum_sec[i] <= t_into < cum_sec[i+1]
            seg_i = None
            for i in range(len(cum_sec) - 1):
                if cum_sec[i] <= t_into < cum_sec[i + 1]:
                    seg_i = i
                    break
            if seg_i is None:
                continue

            a_id = seq[seg_i]
            b_id = seq[seg_i + 1]
            a = stop_meta.get(a_id)
            b = stop_meta.get(b_id)
            if not a or not b:
                continue

            seg_start = cum_sec[seg_i]
            seg_end = cum_sec[seg_i + 1]
            seg_len = max(1, seg_end - seg_start)

            progress = (t_into - seg_start) / seg_len
            progress = max(0.0, min(1.0, progress))

            lat = a["lat"] + (b["lat"] - a["lat"]) * progress
            lon = a["lon"] + (b["lon"] - a["lon"]) * progress

            # distance to user + radius filter
            d_km = haversine_km(ulat, ulon, lat, lon)
            if d_km > radius_km:
                continue

            remaining_sec = max(0, int(seg_end - t_into))
            eta_dt = now_dt + timedelta(seconds=remaining_sec)

            # Build a clean departure_time string (seconds -> time)
            dep_time_obj = _from_seconds(dep_sec)

            buses_out.append({
                "bus_id": f"{ln}-{rid}-{dep_time_obj.isoformat(timespec='minutes')}",
                "line_name": ln,
                "route_id": int(rid),
                "departure_time": dep_time_obj.isoformat(timespec="minutes"),
                "from_stop": {"stop_id": a_id, "stop_name": a["stop_name"]},
                "to_stop": {"stop_id": b_id, "stop_name": b["stop_name"]},
                "progress_0_to_1": round(progress, 3),
                "position": {"lat": round(lat, 6), "lon": round(lon, 6)},
                "distance_to_user_km": round(d_km, 4),
                "next_stop_eta_time": eta_dt.time().isoformat(timespec="seconds"),
                "note": "Simulated timetable-based progression (nearby radius)"
            })

            if len(buses_out) >= max_buses:
                break

        if len(buses_out) >= max_buses:
            break

    # 4) sort nearest + return nearest_k
    buses_out.sort(key=lambda x: x.get("distance_to_user_km", 1e9))
    buses_out = buses_out[:nearest_k]

    return {
        "gender": gender,
        "as_of": now_dt.isoformat(timespec="seconds"),
        "center": {"lat": ulat, "lon": ulon},
        "radius_km": radius_km,
        "routes_considered": len(route_pairs),  # helpful for debugging performance
        "buses": buses_out
    }
