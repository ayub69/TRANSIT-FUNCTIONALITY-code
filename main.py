from fastapi import FastAPI, Body, HTTPException
from transit_backend import TransitBackend
import re
from db_connect import get_connection

# Graph API (DB-backed graphs)
from routers.graph_router import router as graph_router
from services.graph_service import init_graphs, STOP_META
from services.graph_service import build_path_details_stop_graph, build_path_details_least_transfers, steps_from_route_result
from routers.bus_fr22_router import router as bus_fr22_router
from routers.map_router import router as map_router
from services.map_service import init_map_cache
from routers.nearest_stop_router import router as nearest_stop_router
from services.nearest_stop_service import fetch_all_stops, find_nearest_stop, osrm_walk_route, walk_from_stop_to_pin,walk_to_nearest_stop
from services.map_service import build_road_polyline_from_stops

FARE_POLICY = {
    "GREEN_FLAT_PKR": 55,
    "PBS_UPTO_KM": 15.0,
    "PBS_UPTO_FARE_PKR": 80,
    "PBS_ABOVE_FARE_PKR": 120
}
MALE_ALLOWED_STOP_IDS = None


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
            FROM smart_transit2.edges
            WHERE female_only = FALSE
            UNION
            SELECT v_stop_id AS stop_id
            FROM smart_transit2.edges
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


def compute_fare_pkr(route_result: dict) -> dict:
    """
    Updated Fare:
    - Green-only trip -> flat 55
    - Green + other lines -> 55 + PBS(distance of NON-green legs)
    - No green -> PBS(total distance)

    PBS slab:
    - <= 15 km -> 80
    - > 15 km  -> 120

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

    green_km = 0.0
    nongreen_km = 0.0
    lines_used = set()

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

    for leg in legs:
        if not isinstance(leg, dict):
            continue
        ln = str(leg.get("line_name", "") or "").strip().lower()
        if not ln:
            continue

        line_key = "green" if _is_green_line(ln) else ln
        lines_used.add(line_key)
        km = float(leg.get("distance_km", 0) or 0)

        if _is_green_line(ln):
            green_km += km
        else:
            nongreen_km += km

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

    has_green = "green" in lines_used
    has_other = any(l != "green" for l in lines_used)

    # Helper: PBS fare based on a distance
    def _pbs_fare(distance_km: float) -> int:
        return int(FARE_POLICY["PBS_UPTO_FARE_PKR"]) if distance_km <= float(FARE_POLICY["PBS_UPTO_KM"]) else int(FARE_POLICY["PBS_ABOVE_FARE_PKR"])

    # Case 1: Green only
    if has_green and not has_other:
        green_fare = int(FARE_POLICY["GREEN_FLAT_PKR"])
        return {
            "fare_pkr": green_fare,
            "fare_rule": "GREEN_ONLY_FLAT",
            "fare_breakdown": {
                "green_component_pkr": green_fare,
                "pbs_component_pkr": 0,
                "green_distance_km": round(green_km, 4),
                "pbs_distance_km": 0.0
            }
        }

    # Case 2: Green + other lines
    if has_green and has_other:
        green_fare = int(FARE_POLICY["GREEN_FLAT_PKR"])
        pbs_fare = _pbs_fare(nongreen_km)
        return {
            "fare_pkr": green_fare + pbs_fare,
            "fare_rule": "GREEN_PLUS_PBS",
            "fare_breakdown": {
                "green_component_pkr": green_fare,
                "pbs_component_pkr": pbs_fare,
                "green_distance_km": round(green_km, 4),
                "pbs_distance_km": round(nongreen_km, 4)
            }
        }

    # Case 3: No green -> PBS on total distance
    pbs_fare = _pbs_fare(total_km)
    return {
        "fare_pkr": pbs_fare,
        "fare_rule": "PBS_ONLY_TOTAL_DISTANCE",
        "fare_breakdown": {
            "green_component_pkr": 0,
            "pbs_component_pkr": pbs_fare,
            "green_distance_km": 0.0,
            "pbs_distance_km": round(total_km, 4)
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

app = FastAPI(
    title="Smart Transit Assistant API",
    description="",
    version="1.0"
)
app.include_router(bus_fr22_router, tags=["Bus ETA & Tracking"])
backend = TransitBackend()


@app.on_event("startup")
def startup():
    global STOPS_CACHE
    STOPS_CACHE = fetch_all_stops()

    # Builds and caches 6 graphs from PostgreSQL
    init_graphs()
    init_map_cache()
    
    

app.include_router(graph_router, tags=["Graphs"])
app.include_router(map_router, tags=["Map"])
app.include_router(nearest_stop_router, tags=["Nearest Stop + Walking"])

#@app.get("/stops",tags=["all bus stops"])
def get_stops():
    return list(STOP_META.values())


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
            o_text = str(payload["origin"]["text"])
            origin_matches = _search_stop_ids_db(o_text)
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
            d_text = str(payload["destination"]["text"])
            dest_matches = _search_stop_ids_db(d_text)
            if not dest_matches:
                raise HTTPException(status_code=400, detail="No matching destination stop found for text input.")
            dest_stop_id = dest_matches[0]
        else:
            raise HTTPException(status_code=400, detail="Invalid destination format for selected input_mode.")

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
        if objective in ("shortest", "fastest"):
            route_result = build_path_details_stop_graph(
                origin_stop_id, dest_stop_id, gender, objective
            )

            # If shortest/fastest and least_transfers produce the same stop
            # sequence, keep only one result and prefer least_transfers.
            if objective in ("shortest", "fastest"):
                least_transfer_result = build_path_details_least_transfers(
                    origin_stop_id, dest_stop_id, gender
                )

                shortest_path = [int(s) for s in route_result.get("path_stop_ids", [])]
                least_transfer_path = [int(s) for s in least_transfer_result.get("path_stop_ids", [])]

                if shortest_path and shortest_path == least_transfer_path:
                    route_result = least_transfer_result
                    route_result["objective_selected"] = "least_transfers"
                    route_result["objective_requested"] = objective
                    route_result["merged_reason"] = f"same_path_as_{objective}"

            # -----------------------------
            # ADD FARE
            # -----------------------------
            if isinstance(route_result, dict):
                route_result.setdefault("totals", {})
                fare_info = compute_fare_pkr(route_result)
                route_result["totals"]["fare_pkr"] = fare_info["fare_pkr"]
                route_result["totals"]["fare_rule"] = fare_info["fare_rule"]
                route_result["totals"]["fare_breakdown"] = fare_info["fare_breakdown"]
                route_path = route_result["path_stop_ids"]

        elif objective == "least_transfers":
            route_result = build_path_details_least_transfers(
                origin_stop_id, dest_stop_id, gender
            )
             # -----------------------------
        # ADD FARE (Option A)
        # -----------------------------
            if isinstance(route_result, dict):
                route_result.setdefault("totals", {})
                fare_info = compute_fare_pkr(route_result)
                route_result["totals"]["fare_pkr"] = fare_info["fare_pkr"]
                route_result["totals"]["fare_rule"] = fare_info["fare_rule"]
                route_result["totals"]["fare_breakdown"] = fare_info["fare_breakdown"]
            if has_tap_origin or has_tap_destination:
                route_result['totals']["distance_km"]+=origin_walking["distance_km"]
                route_result['totals']["time_min"]+=origin_walking["time_min"]
                
                route_result['totals']["distance_km"]+=destination_walking["distance_km"]
                route_result['totals']["time_min"]+=destination_walking["time_min"]
            route_path = route_result["path_stop_ids"]

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
        
        # --------------------------------------------------------
        # STEP 4: Step-by-step instructions (FR2.1.4)
        # --------------------------------------------------------
        steps = steps_from_route_result(route_result)
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
        profile="driving"   # or "bus" if you run custom OSRM
        )

        if road_poly:
            route_result["road_polyline"] = road_poly
        else:
            route_result["road_polyline"] = None
        # --------------------------------------------------------
        # FINAL RESPONSE (EXPO-FRIENDLY)
        # --------------------------------------------------------
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
            "steps": steps
        }

        # add only in map mode
        

        return response


    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
