from fastapi import FastAPI, Body, HTTPException, Query

from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import re
import time
from datetime import datetime, timedelta
from db_connect import get_connection

# Graph API (DB-backed graphs)
from routers.graph_router import router as graph_router
from services.graph_service import init_graphs, STOP_META
from services.graph_service import build_path_details_stop_graph, build_path_details_least_transfers, steps_from_route_result
from services.bus_fr22_service import get_arrival_predictions
from routers.bus_fr22_router import router as bus_fr22_router
from routers.map_router import router as map_router
from services.map_service import init_map_cache
from routers.nearest_stop_router import router as nearest_stop_router
from services.nearest_stop_service import fetch_all_stops, find_nearest_stop, osrm_walk_route, walk_from_stop_to_pin,walk_to_nearest_stop
from services.map_service import build_road_polyline_from_stops
from routers.admin_router import router as admin_router
from services.admin_service import ensure_admin_tables
from transit_backend import TransitBackend
FARE_POLICY = {
    "GREEN_FLAT_PKR": 55,
    "PBS_UPTO_KM": 15.0,
    "PBS_UPTO_FARE_PKR": 80,
    "PBS_ABOVE_FARE_PKR": 120
}
TRANSFER_PENALTY_MIN = 3.0
MALE_ALLOWED_STOP_IDS = None
LOGGER = logging.getLogger("compute_trip_timing")


def _get_male_allowed_stop_ids() -> set[int]:
    """
    Stops that have at least one non-female-only edge.
    Used so male map input avoids pink-only stops.
    """
    global MALE_ALLOWED_STOP_IDS
    if MALE_ALLOWED_STOP_IDS is not None:
        return MALE_ALLOWED_STOP_IDS

    q = """
        SELECT DISTINCT stop_id
        FROM (
            SELECT u_stop_id AS stop_id
            FROM smart_transit3.edges
            WHERE female_only = FALSE
            UNION
            SELECT v_stop_id AS stop_id
            FROM smart_transit3.edges
            WHERE female_only = FALSE
        ) t
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            MALE_ALLOWED_STOP_IDS = {int(r[0]) for r in cur.fetchall()}
    return MALE_ALLOWED_STOP_IDS


def _find_nearest_stop_gender_aware(lat: float, lon: float, gender: str):
    nearest_any = find_nearest_stop(lat, lon, STOPS_CACHE)
    if gender != "male":
        return nearest_any, False

    allowed = _get_male_allowed_stop_ids()
    if int(nearest_any["stop_id"]) in allowed:
        return nearest_any, False

    candidates = [s for s in STOPS_CACHE if int(s["stop_id"]) in allowed]
    if not candidates:
        return nearest_any, False

    nearest_allowed = find_nearest_stop(lat, lon, candidates)
    return nearest_allowed, True


def _walk_to_specific_stop(user_lat: float, user_lon: float, stop_id: int):
    sid = int(stop_id)
    stop = None
    for s in STOPS_CACHE:
        if int(s.get("stop_id")) == sid:
            stop = s
            break
    if stop is None:
        raise HTTPException(status_code=404, detail=f"Stop id {sid} not found")

    osrm = osrm_walk_route(user_lat, user_lon, float(stop["lat"]), float(stop["lon"]), 0)
    walking = {
        "distance_m": round(osrm["distance_m"], 1),
        "duration_s": round(osrm["duration_s"], 1),
        "distance_km": round(osrm["distance_m"] / 1000.0, 3),
        "time_min": round((osrm["distance_m"] / 1000.0) / 4.5 * 60.0, 2),
    }
    return {
        "origin": {"lat": user_lat, "lon": user_lon},
        "nearest_stop": stop,
        "walking": walking,
        "route_geometry": osrm["geometry"],
        "walking_steps": osrm["steps_text"],
        "walking_steps_raw": osrm["steps_raw"],
    }


def _search_stop_ids_db(query: str, max_results: int = 10) -> list[int]:
    """
    DB-based stop search using STOPS_CACHE (not backend.stops).
    Returns a list of stop_ids sorted by best match.
    """
    q = (query or "").strip().lower()
    if not q:
        return []

    scored = []
    for s in STOPS_CACHE:
        name = str(s.get("stop_name", "")).strip().lower()
        if not name:
            continue

        # simple matching: exact > startswith > contains
        if name == q:
            score = 0
        elif name.startswith(q):
            score = 1
        elif q in name:
            score = 2
        else:
            continue

        scored.append((score, len(name), int(s["stop_id"])))

    scored.sort(key=lambda x: (x[0], x[1]))
    return [sid for _, _, sid in scored[:max_results]]


def _stop_latlon_db(stop_id: int) -> tuple[float, float]:
    """
    Returns (lat, lon) from STOP_META (preferred) or STOPS_CACHE fallback.
    """
    s = STOP_META.get(int(stop_id))
    if s and s.get("lat") is not None and s.get("lon") is not None:
        return float(s["lat"]), float(s["lon"])

    for row in STOPS_CACHE:
        if int(row.get("stop_id")) == int(stop_id):
            return float(row["lat"]), float(row["lon"])

    raise HTTPException(status_code=400, detail=f"Stop id {stop_id} not found in DB cache.")

def count_transfers_from_steps(steps: list[str]) -> int:
    """
    Counts how many times a transfer occurs in human-readable steps.
    Looks for the word 'transfer' (case-insensitive).
    """
    if not steps:
        return 0

    count = 0
    for step in steps:
        if isinstance(step, str) and "transfer" in step.lower():
            count += 1
    return count


def _normalize_line_token(name: str) -> str:
    txt = str(name or "").strip().lower()
    txt = re.sub(r"\s+line\s*$", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"[\s_-]+", "", txt)
    return txt


def _route_changed(prev_leg: dict, cur_leg: dict) -> bool:
    if not isinstance(prev_leg, dict) or not isinstance(cur_leg, dict):
        return False

    prev_route = prev_leg.get("route_id")
    cur_route = cur_leg.get("route_id")
    try:
        prev_route = int(prev_route) if prev_route is not None else None
    except Exception:
        prev_route = None
    try:
        cur_route = int(cur_route) if cur_route is not None else None
    except Exception:
        cur_route = None

    # Primary: route_id change
    if prev_route is not None and cur_route is not None:
        return prev_route != cur_route

    # Fallback: line_name change
    prev_line = _normalize_line_token(prev_leg.get("line_name"))
    cur_line = _normalize_line_token(cur_leg.get("line_name"))
    if not prev_line and not cur_line:
        return False
    return prev_line != cur_line


def _fmt_12h(dt_obj: datetime) -> str:
    return dt_obj.strftime("%I:%M %p").lstrip("0")


def _minutes_ahead_from_earliest(earliest_dt: datetime, now_dt: datetime | None = None) -> int:
    now_ref = now_dt or datetime.now()
    delta_min = max(0, int((earliest_dt - now_ref).total_seconds() // 60))
    return min(24 * 60, max(180, delta_min + 180))


def _best_departure_from_payload(payload: dict | None, earliest_dt: datetime) -> dict | None:
    arrivals = payload.get("arrivals", []) if isinstance(payload, dict) else []
    if not isinstance(arrivals, list) or not arrivals:
        return None

    best_dt = None
    for item in arrivals:
        if not isinstance(item, dict):
            continue
        raw_t = str(item.get("scheduled_arrival_time") or "").strip()
        if not raw_t:
            continue
        try:
            t_obj = datetime.strptime(raw_t[:5], "%H:%M").time()
        except Exception:
            continue
        candidate_dt = datetime.combine(earliest_dt.date(), t_obj)
        if candidate_dt < earliest_dt:
            continue
        if best_dt is None or candidate_dt < best_dt:
            best_dt = candidate_dt

    if best_dt is None:
        return None

    return {
        "departure_dt": best_dt,
        "departure_time_str": _fmt_12h(best_dt),
        "wait_min": round((best_dt - earliest_dt).total_seconds() / 60.0, 2),
    }


def _fetch_arrival_payload(stop_id: int, line_name: str, minutes_ahead: int) -> dict | None:
    try:
        return get_arrival_predictions(
            stop_id=int(stop_id),
            gender="female",  # avoid hiding female-only lines at this lookup layer
            minutes_ahead=int(minutes_ahead),
            line_name=str(line_name),
        )
    except Exception:
        return None


def _batch_next_departures(requests: list[dict]) -> dict[int, dict | None]:
    """
    requests item:
      {
        "event_index": int,
        "stop_id": int,
        "line_name": str,
        "earliest_dt": datetime
      }
    returns: event_index -> departure dict|None
    """
    if not requests:
        return {}

    now_dt = datetime.now()
    keyed_requests = []
    unique_query_keys = set()
    for req in requests:
        stop_id = int(req["stop_id"])
        line_name = str(req["line_name"])
        earliest_dt = req["earliest_dt"]
        minutes_ahead = _minutes_ahead_from_earliest(earliest_dt, now_dt=now_dt)
        query_key = (stop_id, line_name, minutes_ahead)
        keyed_requests.append((req["event_index"], earliest_dt, query_key))
        unique_query_keys.add(query_key)

    payload_by_key: dict[tuple[int, str, int], dict | None] = {}
    max_workers = min(8, max(1, len(unique_query_keys)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(_fetch_arrival_payload, stop_id, line_name, minutes_ahead): (stop_id, line_name, minutes_ahead)
            for (stop_id, line_name, minutes_ahead) in unique_query_keys
        }
        for future in as_completed(future_map):
            key = future_map[future]
            try:
                payload_by_key[key] = future.result()
            except Exception:
                payload_by_key[key] = None

    out: dict[int, dict | None] = {}
    for event_index, earliest_dt, query_key in keyed_requests:
        payload = payload_by_key.get(query_key)
        out[event_index] = _best_departure_from_payload(payload, earliest_dt)
    return out


def get_next_departure_for_stop_line(stop_id: int, line_name: str, earliest_dt: datetime) -> dict | None:
    if stop_id is None or not line_name:
        return None

    minutes_ahead = _minutes_ahead_from_earliest(earliest_dt)
    payload = _fetch_arrival_payload(int(stop_id), str(line_name), minutes_ahead)
    return _best_departure_from_payload(payload, earliest_dt)


def build_boarding_times(
    route_result: dict,
    origin_walking: dict | None = None,
    transfer_buffer_min: float = 1.0
) -> list[dict]:
    if not isinstance(route_result, dict):
        return []

    legs = route_result.get("legs", [])
    if not isinstance(legs, list) or not legs:
        return []

    walk_min = 0.0
    if isinstance(origin_walking, dict):
        try:
            walk_min = max(0.0, float(origin_walking.get("time_min") or 0.0))
        except Exception:
            walk_min = 0.0

    now_dt = datetime.now()
    current_stop_dt = now_dt + timedelta(minutes=walk_min)

    boarding_events: list[dict] = []
    departure_requests: list[dict] = []
    prev_leg = None
    transfer_buffer = max(0.0, float(transfer_buffer_min or 0.0))

    for leg in legs:
        if not isinstance(leg, dict):
            continue

        is_initial = prev_leg is None
        is_transfer = (prev_leg is not None and _route_changed(prev_leg, leg))

        if is_initial or is_transfer:
            boarding_type = "initial" if is_initial else "transfer"
            try:
                stop_id = int(leg.get("from_stop_id")) if leg.get("from_stop_id") is not None else None
            except Exception:
                stop_id = None

            earliest_dt = current_stop_dt
            if is_transfer:
                earliest_dt = earliest_dt + timedelta(minutes=transfer_buffer)

            line_name = str(leg.get("line_name") or "").strip()
            route_id_raw = leg.get("route_id")
            try:
                route_id = int(route_id_raw) if route_id_raw is not None else None
            except Exception:
                route_id = None

            event = {
                "type": boarding_type,
                "stop_id": stop_id,
                "stop_name": leg.get("from_stop_name"),
                "line_name": line_name,
                "route_id": route_id,
                "route_name": leg.get("route_name"),
                "service_available": False,
            }

            boarding_events.append(event)
            event_index = len(boarding_events) - 1

            if stop_id is not None and line_name:
                departure_requests.append(
                    {
                        "event_index": event_index,
                        "stop_id": stop_id,
                        "line_name": line_name,
                        "earliest_dt": earliest_dt,
                    }
                )

        try:
            leg_time_min = max(0.0, float(leg.get("time_min") or 0.0))
        except Exception:
            leg_time_min = 0.0
        current_stop_dt = current_stop_dt + timedelta(minutes=leg_time_min)
        prev_leg = leg

    departure_by_event = _batch_next_departures(departure_requests)
    for idx, dep in departure_by_event.items():
        if dep is None:
            continue
        boarding_events[idx]["service_available"] = True
        boarding_events[idx]["departure_time_str"] = dep["departure_time_str"]
        boarding_events[idx]["departure_time_iso"] = dep["departure_dt"].isoformat(timespec="minutes")
        boarding_events[idx]["wait_min"] = dep["wait_min"]

    return boarding_events


def attach_boarding_times_to_steps(steps: list[str], boarding_events: list[dict]) -> list[str]:
    if not isinstance(steps, list) or not steps:
        return steps
    if not isinstance(boarding_events, list) or not boarding_events:
        return steps

    out = list(steps)

    initial_time = None
    transfer_times = []
    for ev in boarding_events:
        if not isinstance(ev, dict):
            continue
        tstr = ev.get("departure_time_str")
        if not tstr:
            continue
        if ev.get("type") == "initial" and initial_time is None:
            initial_time = tstr
        elif ev.get("type") == "transfer":
            transfer_times.append(tstr)

    if initial_time:
        for i, step in enumerate(out):
            if isinstance(step, str) and step.startswith("Take "):
                base = step.rstrip()
                if base.endswith("."):
                    base = base[:-1]
                out[i] = f"{base} at {initial_time}."
                break

    transfer_idx = 0
    for i, step in enumerate(out):
        if not (isinstance(step, str) and step.startswith("Transfer at ")):
            continue
        if transfer_idx >= len(transfer_times):
            break

        tstr = transfer_times[transfer_idx]
        transfer_idx += 1

        m = re.match(r"^(Transfer at .+?) to (.+?)\.?$", step.strip())
        if m:
            out[i] = f"{m.group(1)} and take {m.group(2)} at {tstr}."
        else:
            base = step.rstrip()
            if base.endswith("."):
                base = base[:-1]
            out[i] = f"{base} at {tstr}."

    return out


def build_bus_activity_message(boarding_events: list[dict]) -> str:
    if not isinstance(boarding_events, list) or not boarding_events:
        return "Route steps are shown, but live timetable activity is unavailable right now."

    missing = [
        ev for ev in boarding_events
        if isinstance(ev, dict) and not ev.get("service_available", False)
    ]
    if not missing:
        return "Buses are active for this route."

    missing_initial = any(ev.get("type") == "initial" for ev in missing)
    if missing_initial:
        return "Route steps are shown, but the first bus is not active at this time."

    return "Route steps are shown, but one or more transfer buses are not active at this time."


def compute_fare_pkr(route_result: dict) -> dict:
    """
    Fare computation per boarded route bucket (in leg order):
    - Consecutive legs on same route bucket are accumulated and charged once
    - Green bucket -> flat fare
    - Non-green bucket -> PBS slab by that bucket distance

    Returns:
      {
        "fare_pkr": int,
        "fare_rule": str,
        "fare_breakdown": {...}
      }
    """
    legs = route_result.get("legs", []) if isinstance(route_result, dict) else []
    totals = route_result.get("totals", {}) if isinstance(route_result, dict) else {}

    # If legs are missing, fall back to totals distance
    total_km = float(totals.get("distance_km", 0) or 0)

    def _is_green_line(raw_line_name: str) -> bool:
        """
        Accepts variants like:
        - Green
        - Green Line
        - green-line
        """
        ln = str(raw_line_name or "").strip().lower()
        if not ln:
            return False
        ln = re.sub(r"[\s_-]+", " ", ln)
        return bool(re.search(r"\bgreen\b", ln))

    # If we couldn't read legs, treat whole as non-green PBS
    if not legs:
        pbs_fare = int(FARE_POLICY["PBS_UPTO_FARE_PKR"]) if total_km <= float(FARE_POLICY["PBS_UPTO_KM"]) else int(FARE_POLICY["PBS_ABOVE_FARE_PKR"])
        return {
            "fare_pkr": pbs_fare,
            "fare_rule": "PBS_FALLBACK_TOTAL_DISTANCE",
            "fare_breakdown": {
                "green_component_pkr": 0,
                "pbs_component_pkr": pbs_fare,
                "pbs_distance_km": round(total_km, 4)
            }
        }

    # Helper: PBS fare based on a distance
    def _pbs_fare(distance_km: float) -> int:
        return int(FARE_POLICY["PBS_UPTO_FARE_PKR"]) if distance_km <= float(FARE_POLICY["PBS_UPTO_KM"]) else int(FARE_POLICY["PBS_ABOVE_FARE_PKR"])

    # Build ordered route buckets from valid leg records only.
    # A new bucket starts when route key changes.
    buckets = []
    current_bucket = None
    for leg in legs:
        if not isinstance(leg, dict):
            continue

        line_name_raw = leg.get("line_name")
        line_name = str(line_name_raw or "").strip()
        if not line_name:
            continue

        try:
            km = float(leg.get("distance_km") or 0)
        except (TypeError, ValueError):
            continue
        if km <= 0:
            continue

        route_id = leg.get("route_id")
        route_id_str = str(route_id).strip() if route_id is not None else ""
        line_name_norm = re.sub(r"[\s_-]+", " ", line_name.lower()).strip()
        route_key = route_id_str if route_id_str else line_name_norm
        is_green = _is_green_line(line_name)

        if current_bucket and current_bucket["route_key"] == route_key:
            current_bucket["distance_km"] += km
            continue

        current_bucket = {
            "route_key": route_key,
            "line_name": line_name,
            "distance_km": km,
            "is_green": is_green
        }
        buckets.append(current_bucket)

    total_fare = 0
    green_component = 0
    pbs_component = 0
    green_km = 0.0
    nongreen_km = 0.0
    routes_breakdown = []

    for bucket in buckets:
        bucket_km = float(bucket["distance_km"])
        if bucket["is_green"]:
            route_fare = int(FARE_POLICY["GREEN_FLAT_PKR"])
            route_rule = "GREEN_FLAT"
            green_component += route_fare
            green_km += bucket_km
        else:
            route_fare = _pbs_fare(bucket_km)
            route_rule = "PBS_UPTO_15" if bucket_km <= float(FARE_POLICY["PBS_UPTO_KM"]) else "PBS_ABOVE_15"
            pbs_component += route_fare
            nongreen_km += bucket_km

        total_fare += route_fare
        routes_breakdown.append(
            {
                "route_id": bucket["route_key"],
                "line_name": bucket["line_name"],
                "distance_km": round(bucket_km, 4),
                "route_fare_pkr": route_fare,
                "route_rule": route_rule
            }
        )

    return {
        "fare_pkr": total_fare,
        "fare_rule": "PER_ROUTE_ACCUMULATED",
        "fare_breakdown": {
            "green_component_pkr": green_component,
            "pbs_component_pkr": pbs_component,
            "green_distance_km": round(green_km, 4),
            "pbs_distance_km": round(nongreen_km, 4),
            "routes": routes_breakdown,
            "num_route_boardings": len(buckets),
            "num_transfers": max(0, len(buckets) - 1)
        }
    }

def _stop_name_db(stop_id: int) -> str:
    sid = int(stop_id)

    s = STOP_META.get(sid)
    if s and s.get("stop_name"):
        return str(s["stop_name"])

    for row in STOPS_CACHE:
        if int(row.get("stop_id")) == sid:
            return str(row.get("stop_name") or f"Stop {sid}")

    return f"Stop {sid}"


def _fmt_delay_minutes(value: float) -> str:
    v = float(value or 0.0)
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _compute_active_delay_messages(route_obj: dict) -> list[str]:
    """
    Build human-readable active-delay messages for the currently selected route legs.
    Additive helper used by /compute-trip response only.
    """
    if not isinstance(route_obj, dict):
        return []

    legs = route_obj.get("legs", [])
    if not isinstance(legs, list) or not legs:
        return []

    requested = []
    seen = set()
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        rid = leg.get("route_id")
        a = leg.get("from_stop_id")
        b = leg.get("to_stop_id")
        if rid is None or a is None or b is None:
            continue
        rid_i = int(rid)
        a_i = int(a)
        b_i = int(b)
        key = (rid_i, min(a_i, b_i), max(a_i, b_i))
        if key in seen:
            continue
        seen.add(key)
        requested.append(key)

    if not requested:
        return []

    values_sql = ",".join(["(%s,%s,%s)"] * len(requested))
    flat_params = []
    for rid_i, min_sid, max_sid in requested:
        flat_params.extend([rid_i, min_sid, max_sid])

    q = f"""
        SELECT
            d.route_id,
            LEAST(d.from_stop_id, d.to_stop_id) AS min_stop_id,
            GREATEST(d.from_stop_id, d.to_stop_id) AS max_stop_id,
            SUM(d.delay_min) AS total_delay_min
        FROM smart_transit3.delay_reports d
        WHERE d.active = TRUE
          AND (d.expires_at IS NULL OR d.expires_at > NOW())
          AND d.reported_at <= NOW()
          AND (d.route_id, LEAST(d.from_stop_id, d.to_stop_id), GREATEST(d.from_stop_id, d.to_stop_id))
              IN ({values_sql})
        GROUP BY
            d.route_id,
            LEAST(d.from_stop_id, d.to_stop_id),
            GREATEST(d.from_stop_id, d.to_stop_id);
    """

    delay_map = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(q, flat_params)
            except Exception:
                return []
            for rid, min_sid, max_sid, dmin in cur.fetchall():
                delay_map[(int(rid), int(min_sid), int(max_sid))] = float(dmin or 0.0)

    out = []
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        rid = leg.get("route_id")
        a = leg.get("from_stop_id")
        b = leg.get("to_stop_id")
        if rid is None or a is None or b is None:
            continue

        key = (int(rid), min(int(a), int(b)), max(int(a), int(b)))
        delay_min = float(delay_map.get(key, 0.0))
        if delay_min <= 0:
            continue

        from_name = str(leg.get("from_stop_name") or _stop_name_db(int(a)))
        to_name = str(leg.get("to_stop_name") or _stop_name_db(int(b)))

        route_name = (leg.get("route_name") or "").strip()
        route_label = route_name if route_name else str(leg.get("route_id"))

        out.append(
            f"There is a delay of {_fmt_delay_minutes(delay_min)} minutes between "
            f"{from_name} and {to_name} stop on route {route_label}."
        )

    return out

app = FastAPI(
    title="Smart Transit Assistant API",
    description="",
    version="1.0"
)
app.include_router(bus_fr22_router, tags=["Bus ETA & Tracking"])
backend = TransitBackend()


@app.on_event("startup")
def startup():
    refresh_all_runtime_caches()
    ensure_admin_tables()
    
    

app.include_router(graph_router, tags=["Graphs"])
app.include_router(map_router, tags=["Map"])
app.include_router(nearest_stop_router, tags=["Nearest Stop + Walking"])
app.include_router(admin_router)

#@app.get("/stops",tags=["all bus stops"])
def get_stops():
    return list(STOP_META.values())


def refresh_all_runtime_caches():
    """
    Refresh all in-memory runtime caches used by compute-trip and map endpoints.
    """
    global STOPS_CACHE
    STOPS_CACHE = fetch_all_stops()
    init_graphs()
    init_map_cache()


def _norm_str(x, default: str) -> str:
    """
    Normalize payload values that might accidentally come as:
    - list (e.g., ["least_transfers"])
    - None
    - number
    Always returns a lowercase stripped string.
    """
    if isinstance(x, list):
        x = x[0] if len(x) > 0 else default
    if x is None:
        x = default
    return str(x).lower().strip()


# ============================================================
# SINGLE CONTROLLER: COMPUTE TRIP
# ============================================================

@app.get("/stop-suggestions", tags=["stop search"])
def stop_suggestions(
    q: str = Query("", description="Partial stop name"),
):
    query = str(q or "").strip()
    if not query:
        return {"query": query, "suggestions": []}

    stop_ids = _search_stop_ids_db(query, max_results=5)
    suggestions = [
        {"stop_id": sid, "stop_name": _stop_name_db(sid)}
        for sid in stop_ids
    ]

    return {"query": query, "suggestions": suggestions}


@app.post("/compute-trip", tags=["complete trip API"])
def compute_trip(payload: dict = Body(
    ...,
    examples={
        "text_to_text": {
            "summary": "Text + Text",
            "value": {
                "input_mode": "text",
                "origin": {"text": "Numaish Chowrangi"},
                "destination": {"text": "Malir Halt"},
                "gender": "female",
                "objective": "least_transfers"
            }
        },
        "tap_to_tap": {
            "summary": "Tap + Tap",
            "value": {
                "input_mode": "map",
                "origin": {"lat": 24.813490, "lon": 67.005407},
                "destination": {"lat": 24.8844268, "lon": 67.1745528},
                "gender": "male",
                "objective": "shortest"
            }
        },
        "tap_to_text": {
            "summary": "Tap + Text",
            "value": {
                "input_mode": "tap+text",
                "origin": {"lat": 24.813490, "lon": 67.005407},
                "destination": {"text": "Malir Halt"},
                "gender": "male",
                "objective": "fastest"
            }
        },
        "text_to_tap": {
            "summary": "Text + Tap",
            "value": {
                "input_mode": "text+tap",
                "origin": {"text": "Numaish Chowrangi"},
                "destination": {"lat": 24.8844268, "lon": 67.1745528},
                "gender": "female",
                "objective": "least_transfers"
            }
        }
    }
)):
    """
    {
  "input_mode": "text",
  "origin": { "text": "Numaish Chowrangi" },
  "destination": { "text": "Malir Halt" },
  "gender": "male",
  "objective": "least_transfers"
    }
    or

    {
  "input_mode": "map",
  "origin": { "lat": 24.813490, "lon": 67.005407 },
  "destination": { "lat": 24.8844268, "lon": 67.1745528 },
  "gender": "male",
  "objective": "shortest"
    }
    or

    {
  "input_mode": "tap+text",
  "origin": { "lat": 24.813490, "lon": 67.005407 },
  "destination": { "text": "Malir Halt" },
  "gender": "male",
  "objective": "fastest"
    }
    or
    
    {
  "input_mode": "text+tap",
  "origin": { "text": "Numaish Chowrangi" },
  "destination": { "lat": 24.8844268, "lon": 67.1745528 },
  "gender": "male",
  "objective": "least_transfers"
    }
    """
    req_started = time.perf_counter()
    stage_started = req_started
    timings: list[tuple[str, float]] = []

    def _mark(stage_name: str):
        nonlocal stage_started
        now = time.perf_counter()
        timings.append((stage_name, (now - stage_started) * 1000.0))
        stage_started = now

    try:
        input_mode = _norm_str(payload.get("input_mode"), "")
        normalized_input_mode = input_mode.replace(" ", "")
        has_tap_origin = normalized_input_mode in ("map", "tap+text")
        has_tap_destination = normalized_input_mode in ("map", "text+tap")
        has_text_origin = normalized_input_mode in ("text", "text+tap")
        has_text_destination = normalized_input_mode in ("text", "tap+text")
        if normalized_input_mode not in ("text", "map", "tap+text", "text+tap"):
            raise HTTPException(
                status_code=400,
                detail="Invalid input_mode. Use 'text', 'map', 'tap+text', or 'text+tap'."
            )

        # legacy / backward-compatible
        route_mode = _norm_str(payload.get("route_mode"), None)

        # NEW params (frontend selects which graph)
        gender = _norm_str(payload.get("gender"), "male")

        # objective falls back to route_mode if missing
        raw_objective = payload.get("objective", None)
        if raw_objective is None or (isinstance(raw_objective, str) and raw_objective.strip() == "") or (
            isinstance(raw_objective, list) and len(raw_objective) == 0
        ):
            objective = route_mode
        else:
            objective = _norm_str(raw_objective, route_mode)

        if gender not in ("female", "male"):
            raise HTTPException(status_code=400, detail="gender must be 'female' or 'male'")

        if objective not in ("shortest", "fastest", "least_transfers", "cheapest"):
            raise HTTPException(
                status_code=400,
                detail="objective must be one of: shortest | fastest | least_transfers | cheapest"
            )

        origin_obj = payload.get("origin", {}) or {}
        dest_obj = payload.get("destination", {}) or {}

        origin_text = str(origin_obj.get("text", "")).strip()
        dest_text = str(dest_obj.get("text", "")).strip()

        origin_matches = _search_stop_ids_db(origin_text) if origin_text else []
        dest_matches = _search_stop_ids_db(dest_text) if dest_text else []
        _mark("input_validation_and_text_search")

        # --------------------------------------------------------
        # STEP 1: Resolve origin & destination to coordinates
        # --------------------------------------------------------
        walk1 = None
        walk2 = None
        walk1_summary = None
        walk2_summary = None
        origin_walking = {"distance_km": 0, "distance_m": 0, "time_min": 0}
        destination_walking = {"distance_km": 0, "distance_m": 0, "time_min": 0}
        walk_to_origin = None
        walk_from_dest = None

        if has_tap_origin:
            o_lat = float(payload["origin"]["lat"])
            o_lon = float(payload["origin"]["lon"])
            origin_nearest, origin_fallback_used = _find_nearest_stop_gender_aware(o_lat, o_lon, gender)
            origin_stop_id = int(origin_nearest["stop_id"])
            walk_to_origin = _walk_to_specific_stop(o_lat, o_lon, origin_stop_id)
            if origin_fallback_used:
                walk_to_origin["note"] = "Nearest stop was female-only for male user; used next best eligible stop."
            origin_walking = walk_to_origin["walking"]
        elif has_text_origin:
            if not origin_matches:
                raise HTTPException(status_code=400, detail="No matching origin stop found for text input.")
            origin_stop_id = origin_matches[0]
        else:
            raise HTTPException(status_code=400, detail="Invalid origin format for selected input_mode.")

        if has_tap_destination:
            d_lat = float(payload["destination"]["lat"])
            d_lon = float(payload["destination"]["lon"])
            dest_nearest, dest_fallback_used = _find_nearest_stop_gender_aware(d_lat, d_lon, gender)
            dest_stop_id = int(dest_nearest["stop_id"])
            walk_from_dest = walk_from_stop_to_pin(dest_stop_id, d_lat, d_lon)
            if dest_fallback_used:
                walk_from_dest["note"] = "Nearest stop was female-only for male user; used next best eligible stop."
            destination_walking = walk_from_dest["walking"]
        elif has_text_destination:
            if not dest_matches:
                raise HTTPException(status_code=400, detail="No matching destination stop found for text input.")
            dest_stop_id = dest_matches[0]
        else:
            raise HTTPException(status_code=400, detail="Invalid destination format for selected input_mode.")
        _mark("resolve_origin_destination_and_walking")

        # Coordinates from selected stops
        o_lat, o_lon = _stop_latlon_db(origin_stop_id)
        d_lat, d_lon = _stop_latlon_db(dest_stop_id)

        # TEMP override (your current testing preference)
        # origin_walking = {"distance_km": 0, "distance_m": 0, "time_min": 0}
        # destination_walking = {"distance_km": 0, "distance_m": 0, "time_min": 0}

        # # --------------------------------------------------------
        # # STEP 2: Walking distances (FR2.1.5)
        # # --------------------------------------------------------
        # origin_walking = backend.calculate_walking_distance(
        #     o_lat, o_lon,
        #     backend.stops[origin_stop_id]["lat"],
        #     backend.stops[origin_stop_id]["lon"]
        # )

        # destination_walking = backend.calculate_walking_distance(
        #     backend.stops[dest_stop_id]["lat"],
        #     backend.stops[dest_stop_id]["lon"],
        #     d_lat, d_lon
        # )

        # TEMP override (your current testing preference)
        # origin_walking = {"distance_km": 0, "distance_m": 0, "time_min": 0}
        # destination_walking = {"distance_km": 0, "distance_m": 0, "time_min": 0}

        # --------------------------------------------------------
        # STEP 3: Route Planning (FR2.1.3)
        # --------------------------------------------------------
        def _attach_fare(route_obj: dict) -> dict:
            if isinstance(route_obj, dict):
                route_obj.setdefault("totals", {})
                fare_info_local = compute_fare_pkr(route_obj)
                route_obj["totals"]["fare_pkr"] = fare_info_local["fare_pkr"]
                route_obj["totals"]["fare_rule"] = fare_info_local["fare_rule"]
                route_obj["totals"]["fare_breakdown"] = fare_info_local["fare_breakdown"]
            return route_obj

        def _route_transfer_count(route_obj: dict) -> int:
            """
            Preferred source: explicit transfers in payload.
            Fallback: count route/line changes across legs.
            """
            if not isinstance(route_obj, dict):
                return 0

            totals = route_obj.get("totals", {})
            if isinstance(totals, dict) and totals.get("transfers") is not None:
                try:
                    return int(totals.get("transfers"))
                except Exception:
                    pass

            if route_obj.get("transfers") is not None:
                try:
                    return int(route_obj.get("transfers"))
                except Exception:
                    pass

            legs = route_obj.get("legs", [])
            if not isinstance(legs, list) or not legs:
                return 0

            transfers = 0
            prev_key = None
            for leg in legs:
                if not isinstance(leg, dict):
                    continue

                route_id = leg.get("route_id")
                line_name = leg.get("line_name")

                if route_id is not None:
                    current_key = ("route", int(route_id))
                elif line_name:
                    current_key = ("line", str(line_name).strip().lower())
                else:
                    continue

                if prev_key is None:
                    prev_key = current_key
                    continue

                if current_key != prev_key:
                    transfers += 1
                prev_key = current_key

            return transfers

        if objective in ("shortest", "fastest"):
            route_result = build_path_details_stop_graph(
                origin_stop_id, dest_stop_id, gender, objective
            )

            # If shortest/fastest and least_transfers produce the same stop
            # sequence, keep only one result and prefer least_transfers.
            least_transfer_result = build_path_details_least_transfers(
                origin_stop_id, dest_stop_id, gender
            )

            objective_path = [int(s) for s in route_result.get("path_stop_ids", [])]
            least_transfer_path = [int(s) for s in least_transfer_result.get("path_stop_ids", [])]

            if objective_path and objective_path == least_transfer_path:
                route_result = least_transfer_result
                route_result["objective_selected"] = "least_transfers"
                route_result["objective_requested"] = objective
                route_result["merged_reason"] = f"same_path_as_{objective}"

            route_result = _attach_fare(route_result)
            route_path = route_result["path_stop_ids"]
            _mark("route_planning_shortest_or_fastest")

        elif objective == "least_transfers":
            route_result = build_path_details_least_transfers(
                origin_stop_id, dest_stop_id, gender
            )

            # Tie-break:
            # If least_transfers and shortest have the same number of transfers,
            # return shortest for least_transfers objective.
            try:
                shortest_result = build_path_details_stop_graph(
                    origin_stop_id, dest_stop_id, gender, "shortest"
                )

                least_transfers = _route_transfer_count(route_result)
                shortest_transfers = _route_transfer_count(shortest_result)

                if least_transfers == shortest_transfers:
                    route_result = shortest_result
                    route_result["objective_requested"] = "least_transfers"
                    route_result["objective_selected"] = "shortest"
                    route_result["merged_reason"] = "same_transfer_count_as_shortest"
            except Exception:
                # Keep default least_transfers behavior if tie-break check cannot be evaluated.
                pass

            route_result = _attach_fare(route_result)
            if has_tap_origin or has_tap_destination:
                route_result['totals']["distance_km"]+=origin_walking["distance_km"]
                route_result['totals']["time_min"]+=origin_walking["time_min"]

                route_result['totals']["distance_km"]+=destination_walking["distance_km"]
                route_result['totals']["time_min"]+=destination_walking["time_min"]
            route_path = route_result["path_stop_ids"]
            _mark("route_planning_least_transfers")
        
        elif objective == "cheapest":
            candidate_routes = []

            shortest_candidate = build_path_details_stop_graph(
                origin_stop_id, dest_stop_id, gender, "shortest"
            )
            candidate_routes.append(("shortest", _attach_fare(shortest_candidate)))

            fastest_candidate = build_path_details_stop_graph(
                origin_stop_id, dest_stop_id, gender, "fastest"
            )
            candidate_routes.append(("fastest", _attach_fare(fastest_candidate)))

            least_transfers_candidate = build_path_details_least_transfers(
                origin_stop_id, dest_stop_id, gender
            )
            candidate_routes.append(("least_transfers", _attach_fare(least_transfers_candidate)))

            objective_selected, route_result = min(
                candidate_routes,
                key=lambda x: float(x[1].get("totals", {}).get("fare_pkr", 10**9))
            )

            route_result["objective_requested"] = "cheapest"
            route_result["objective_selected"] = objective_selected
            route_result["cheapest_candidates"] = {
                name: {
                    "fare_pkr": int(result.get("totals", {}).get("fare_pkr", 0)),
                    "distance_km": float(result.get("totals", {}).get("distance_km", 0)),
                    "time_min": float(result.get("totals", {}).get("time_min", 0)),
                    "transfers": int(result.get("totals", {}).get("transfers", 0))
                }
                for name, result in candidate_routes
            }

            if has_tap_origin or has_tap_destination:
                route_result['totals']["distance_km"] += origin_walking["distance_km"]
                route_result['totals']["time_min"] += origin_walking["time_min"]
                route_result['totals']["distance_km"] += destination_walking["distance_km"]
                route_result['totals']["time_min"] += destination_walking["time_min"]

            route_path = route_result["path_stop_ids"]
            _mark("route_planning_cheapest")

        else:
            # fallback to your existing backend logic (cheapest etc.)
            if route_mode == "cheapest":
                route_result = backend.get_cheapest_route(origin_stop_id, dest_stop_id)
            elif route_mode == "shortest":
                route_result = backend.get_shortest_distance_route(origin_stop_id, dest_stop_id)
            elif route_mode == "fastest":
                route_result = backend.get_fastest_route(origin_stop_id, dest_stop_id)
            elif route_mode == "least_transfers":
                route_result = backend.get_least_transfers_route(origin_stop_id, dest_stop_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid route_mode selected.")

            route_path = route_result["path"]
            _mark("route_planning_legacy_backend")
        
        # --------------------------------------------------------
        # STEP 4: Step-by-step instructions (FR2.1.4)
        # --------------------------------------------------------
        steps = steps_from_route_result(route_result, gender=gender)
        boarding_events = build_boarding_times(
            route_result,
            origin_walking=origin_walking,
            transfer_buffer_min=1.0
        )
        steps = attach_boarding_times_to_steps(steps, boarding_events)
        bus_activity_message = build_bus_activity_message(boarding_events)
        _mark("steps_and_boarding")
        # Prefer DB stop names if available, else fall back to backend stop names
        origin_name = _stop_name_db(origin_stop_id)
        dest_name = _stop_name_db(dest_stop_id)


        # If route_result came from DB graphs, add a convenience list of stop names along the path
        if isinstance(route_result, dict) and "path_stop_ids" in route_result:
            path_stop_names = []
            for sid in route_result["path_stop_ids"]:
                path_stop_names.append(_stop_name_db(sid))

            route_result["path_stop_names"] = path_stop_names

        if (has_tap_origin or has_tap_destination) and objective in ("shortest" ,"fastest"):
            route_result['totals']["distance_km"]+=origin_walking["distance_km"]
            route_result['totals']["time_min"]+=origin_walking["time_min"]
            
            route_result['totals']["distance_km"]+=destination_walking["distance_km"]
            route_result['totals']["time_min"]+=destination_walking["time_min"]

        transfer_count_from_steps = count_transfers_from_steps(steps)
        if isinstance(route_result, dict):
            route_result.setdefault("totals", {})
            current_time_min = float(route_result["totals"].get("time_min", 0) or 0)
            transfer_penalty_total_min = float(transfer_count_from_steps) * float(TRANSFER_PENALTY_MIN)
            route_result["totals"]["time_min"] = round(current_time_min + transfer_penalty_total_min, 4)
        
        walking_routes = None
        if has_tap_origin or has_tap_destination:
            walking_routes = {}
            if has_tap_origin and walk_to_origin is not None:
                walking_routes["to_origin_stop"] = {
                    "origin": walk_to_origin["origin"],
                    "nearest_stop": walk_to_origin["nearest_stop"],
                    "walking": walk_to_origin["walking"],
                    "geometry": walk_to_origin["route_geometry"],
                    "steps": walk_to_origin["walking_steps"],
                }
            if has_tap_destination and walk_from_dest is not None:
                walking_routes["from_dest_stop"] = {
                    "stop": walk_from_dest["end_stop"],
                    "pin": walk_from_dest["pinned_destination"],
                    "walking": walk_from_dest["walking"],
                    "geometry": walk_from_dest["route_geometry"],
                    "steps": walk_from_dest["walking_steps"],
                }
            if not walking_routes:
                walking_routes = None
        #drawing polyline of roads from stop data
        road_poly = build_road_polyline_from_stops(
        route_result.get("stops", []),
        transit_legs=route_result.get("legs", []),
        profile="driving"   # or "bus" if you run custom OSRM
        )

        if road_poly:
            route_result["road_polyline"] = road_poly
        else:
            route_result["road_polyline"] = None
        _mark("post_processing_and_polyline")
        # --------------------------------------------------------
        # FINAL RESPONSE (EXPO-FRIENDLY)
        # --------------------------------------------------------
        delay_messages = _compute_active_delay_messages(route_result)
        delay_message_text = "No delay reported."
        if delay_messages:
            delay_message_text = " ".join(delay_messages)

        response = {
            "input_mode": input_mode,
            "route_mode": route_mode,
            "gender": gender,
            "objective": objective,
            "walking_routes": walking_routes,

            "origin": {
                "stop_id": origin_stop_id,
                "stop_name": origin_name,
                "walking": origin_walking
            },
            "destination": {
                "stop_id": dest_stop_id,
                "stop_name": dest_name,
                "walking": destination_walking
            },
            "route": route_result,
            "transfer_count": transfer_count_from_steps,
            "steps": steps,
            "boarding_plan": boarding_events,
            "bus_activity_message": bus_activity_message,
            "delay_message": delay_message_text
        }

        response["origin_suggestions"] = [
            {
                "stop_id": sid,
                "stop_name": _stop_name_db(sid)
            }
            for sid in origin_matches[:5]
        ]

        response["destination_suggestions"] = [
            {
                "stop_id": sid,
                "stop_name": _stop_name_db(sid)
            }
            for sid in dest_matches[:5]
        ]
        _mark("delay_and_response_build")

        total_ms = (time.perf_counter() - req_started) * 1000.0
        stages_str = ", ".join([f"{name}={ms:.1f}ms" for name, ms in timings])
        LOGGER.warning(
            "compute_trip_timing total=%.1fms input_mode=%s objective=%s route_mode=%s stages=[%s]",
            total_ms,
            input_mode,
            objective,
            route_mode,
            stages_str,
        )

        # add only in map mode
        

        return response


    except HTTPException:
        total_ms = (time.perf_counter() - req_started) * 1000.0
        stages_str = ", ".join([f"{name}={ms:.1f}ms" for name, ms in timings])
        LOGGER.warning(
            "compute_trip_timing http_error total=%.1fms input_mode=%s objective=%s route_mode=%s stages=[%s]",
            total_ms,
            locals().get("input_mode"),
            locals().get("objective"),
            locals().get("route_mode"),
            stages_str,
        )
        raise
    except Exception as e:
        total_ms = (time.perf_counter() - req_started) * 1000.0
        stages_str = ", ".join([f"{name}={ms:.1f}ms" for name, ms in timings])
        LOGGER.exception(
            "compute_trip_timing unhandled_error total=%.1fms input_mode=%s objective=%s route_mode=%s stages=[%s]",
            total_ms,
            locals().get("input_mode"),
            locals().get("objective"),
            locals().get("route_mode"),
            stages_str,
        )
        raise HTTPException(status_code=500, detail=str(e))
