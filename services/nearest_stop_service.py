# services/nearest_stop_service.py

from typing import Dict, Any, List
import math
import requests
from fastapi import HTTPException
from db_connect import get_connection

SCHEMA = "smart_transit2"
OSRM_BASE_URL = "https://router.project-osrm.org"


# -----------------------------
# DB FETCH
# -----------------------------
def fetch_all_stops() -> List[Dict[str, Any]]:
    q = f"""
        SELECT stop_id, stop_name, lat, lon
        FROM {SCHEMA}.stops
        ORDER BY stop_id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
            rows = cur.fetchall()

    stops = []
    for sid, name, lat, lon in rows:
        stops.append({
            "stop_id": int(sid),
            "stop_name": str(name),
            "lat": float(lat),
            "lon": float(lon),
        })
    return stops


# -----------------------------
# GEO HELPERS
# -----------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_stop(lat: float, lon: float, stops: List[Dict[str, Any]]) -> Dict[str, Any]:
    best = None
    best_d = float("inf")

    for s in stops:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d < best_d:
            best_d = d
            best = s

    if not best:
        raise HTTPException(status_code=500, detail="No stops found in DB.")

    return {
        **best,
        "approx_straightline_km": round(best_d, 4)
    }


# -----------------------------
# OSRM WALK ROUTE
# -----------------------------
def osrm_walk_route(lat1: float, lon1: float, lat2: float, lon2: float,origin_or_dest:int) -> Dict[str, Any]:
    """
    Returns:
      - distance_m, duration_s
      - geometry (GeoJSON LineString)
      - steps_raw: structured steps
      - steps_text: human-readable instructions (requested format)
    """

    def _fmt_m(m: float) -> str:
        return f"{int(round(m))} m"

    def _bearing_to_compass(b: float) -> str:
        # 0=N, 90=E, 180=S, 270=W
        dirs = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"]
        idx = int((b % 360) / 45.0 + 0.5) % 8
        return dirs[idx]

    def _roundabout_exit_number(step: dict) -> int | None:
        """
        OSRM gives intersections list; exit index is usually intersections[-1]["out"] (0-based).
        We'll convert to 1-based (1st exit, 2nd exit...).
        """
        inters = step.get("intersections") or []
        if not inters:
            return None
        last = inters[-1]
        out = last.get("out")
        if out is None:
            return None
        try:
            return int(out) + 1
        except Exception:
            return None

    def _build_step_text(step: dict, origin_or_dest:int) -> str:
        maneuver = step.get("maneuver", {}) or {}
        m_type = (maneuver.get("type") or "").lower()
        m_mod = (maneuver.get("modifier") or "").lower()
        dist_m = float(step.get("distance", 0) or 0)
        way_name = (step.get("name") or "").strip()

        # ARRIVE
        if m_type == "arrive" and origin_or_dest == 0:
            return "You have arrived at the station."
        elif m_type == "arrive" and origin_or_dest == 1:
            return "You have arrived at your destination."

        # DEPART (make it Google-like)
        if m_type == "depart":
            bearing = maneuver.get("bearing_after")
            if bearing is not None:
                head = _bearing_to_compass(float(bearing))
                # Prefer "Head <dir>" instead of "Start walking left"
                if way_name:
                    return f"Head {head} on {way_name} for {_fmt_m(dist_m)}."
                return f"Head {head} for {_fmt_m(dist_m)}."
            # fallback
            if way_name:
                return f"Start on {way_name} for {_fmt_m(dist_m)}."
            return f"Start walking for {_fmt_m(dist_m)}." if dist_m > 0 else "Start walking."

        # ROUNDABOUT / ROTARY handling
        if m_type in ("rotary", "roundabout", "exit rotary"):
            exit_n = _roundabout_exit_number(step)
            if exit_n is not None:
                # Example: "At the roundabout, take the 2nd exit onto Khayaban-e-Bedil"
                if way_name:
                    return f"At the roundabout, take the {exit_n} exit onto {way_name}."
                return f"At the roundabout, take the {exit_n} exit."
            # fallback
            if way_name:
                return f"Continue through the roundabout on {way_name}."
            return "Continue through the roundabout."

        # TURN
        if m_type == "turn":
            # Prefer "Turn left onto <road>" like Google
            if way_name:
                return f"Turn {m_mod} onto {way_name}, then continue for {_fmt_m(dist_m)}."
            return f"Turn {m_mod}, then continue for {_fmt_m(dist_m)}."

        # CONTINUE / NEW NAME
        if m_type in ("continue", "new name"):
            if way_name:
                # Google style: "Continue on <road> for 274 m"
                return f"Continue on {way_name} for {_fmt_m(dist_m)}."
            if m_mod == "straight":
                return f"Continue straight for {_fmt_m(dist_m)}."
            return f"Continue for {_fmt_m(dist_m)}." if dist_m > 0 else "Continue."

        # FALLBACK
        if way_name and dist_m > 0:
            return f"Continue on {way_name} for {_fmt_m(dist_m)}."
        return f"Walk for {_fmt_m(dist_m)}." if dist_m > 0 else "Walk."


    try:
        url = (
            f"{OSRM_BASE_URL}/route/v1/walking/"
            f"{lon1},{lat1};{lon2},{lat2}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        r = requests.get(url, timeout=15).json()

        if r.get("code") != "Ok":
            raise HTTPException(status_code=502, detail=f"OSRM error: {r.get('message', 'unknown')}")

        route0 = r["routes"][0]
        leg0 = route0["legs"][0]

        steps_raw = []
        steps_text = []

        for st in leg0.get("steps", []):
            maneuver = st.get("maneuver", {}) or {}
            m_type = maneuver.get("type") or ""
            m_mod = maneuver.get("modifier") or ""
            dist_m = float(st.get("distance", 0) or 0)
            dur_s = float(st.get("duration", 0) or 0)

            way_name = (st.get("name") or "").strip()

            text = _build_step_text(st,origin_or_dest)
            # -------------------------
            # NEW: dedupe / simplify
            # -------------------------
            MIN_DIST_M = 20.0  # tune: 15–30m works well

            m_type_l = (maneuver.get("type") or "").lower()
            dist_m = float(st.get("distance", 0) or 0)
            way_name = (st.get("name") or "").strip().lower()

            def _is_important_step(t: str) -> bool:
                # keep key events even if tiny
                return m_type_l in ("depart", "arrive", "turn", "roundabout", "rotary", "exit rotary")

            # 1) drop tiny "continue" noise
            if dist_m < MIN_DIST_M and not _is_important_step(text):
                continue
            #colapse at consecutive roundabouts
            if steps_text:
                prev = steps_text[-1].lower()
                cur = text.lower()

                prev_is_round = prev.startswith("at the roundabout")
                cur_is_round = cur.startswith("at the roundabout")

                if prev_is_round and cur_is_round:
                    # replace previous roundabout instruction with current one
                    # (keeps only the latest/most relevant exit)
                    steps_text[-1] = text
                    continue
            # 2) exact duplicate text
            if steps_text and text == steps_text[-1]:
                continue

            # 3) consecutive "Continue on SAME road" duplicates:
            # If both last and current start with "Continue on <same road>", keep the one with larger distance.
            if steps_text:
                last = steps_text[-1].lower()
                cur = text.lower()

                # crude but effective: same road name appears in both
                if last.startswith("continue on") and cur.startswith("continue on"):
                    # if road name is same, treat as duplicate
                    # (works because your formatter includes the road name)
                    if way_name and way_name in last and way_name in cur:
                        # replace previous with current if current distance is bigger
                        # extract distance by using current st distance (we prefer current)
                        steps_text[-1] = text
                        continue

            steps_text.append(text)

            steps_raw.append({
                "instruction": text,
                "distance_m": dist_m,
                "duration_s": dur_s,
                "maneuver": {
                    "type": m_type,
                    "modifier": m_mod,
                    "location": maneuver.get("location"),  # [lon, lat]
                },
                "way_name": way_name
            })

        return {
            "distance_m": float(route0.get("distance", 0) or 0),
            "duration_s": float(route0.get("duration", 0) or 0),
            "geometry": route0.get("geometry"),
            "steps_raw": steps_raw,
            "steps_text": steps_text
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OSRM request failed: {str(e)}")


# -----------------------------
# MAIN SERVICE FUNCTION (ONE API)
# -----------------------------
def walk_to_nearest_stop(lat: float, lon: float) -> Dict[str, Any]:
    """
    FRs satisfied:
    - Capture selected coordinates (lat/lon from device)
    - Identify nearest stop
    - Provide walking directions (OSRM walking) from user -> stop
    """
    stops = fetch_all_stops()
    nearest = find_nearest_stop(lat, lon, stops)

    osrm = osrm_walk_route(lat, lon, nearest["lat"], nearest["lon"],0)
    walking = {
        "distance_m": round(osrm["distance_m"], 1),
        "duration_s": round(osrm["duration_s"], 1),
        "distance_km": round(osrm["distance_m"] / 1000.0, 3),
        "time_min": round((osrm["distance_m"] / 1000.0) / 4.5 * 60.0, 2),
    }

    return {
        "origin": {"lat": lat, "lon": lon},
        "nearest_stop": nearest,
        "walking": walking,
        "route_geometry": osrm["geometry"],          # GeoJSON LineString
        "walking_steps": osrm["steps_text"],         # human-readable list
        "walking_steps_raw": osrm["steps_raw"],      # optional: structured steps for UI icons
        "note": "Frontend must obtain GPS/network location; backend computes nearest stop + OSRM walking route."
    }

def walk_from_stop_to_pin(stop_id: int, pin_lat: float, pin_lon: float) -> Dict[str, Any]:
    """
    Used after bus journey ends:
      end_stop (stop_id) -> pinned coordinates (pin_lat, pin_lon)

    Returns OSRM walking route, geometry, and human-readable steps.
    """
    stop_id = int(stop_id)
    pin_lat = float(pin_lat)
    pin_lon = float(pin_lon)

    # Fetch stop coords from DB cache
    stops = fetch_all_stops()
    stop_map = {int(s["stop_id"]): s for s in stops}

    if stop_id not in stop_map:
        raise HTTPException(status_code=404, detail=f"Stop id {stop_id} not found")

    end_stop = stop_map[stop_id]

    osrm = osrm_walk_route(end_stop["lat"], end_stop["lon"], pin_lat, pin_lon,1)
    

    walking = {
        "distance_m": round(osrm["distance_m"], 1),
        "duration_s": round(osrm["duration_s"], 1),
        "distance_km": round(osrm["distance_m"] / 1000.0, 3),
        "time_min": round((osrm["distance_m"] / 1000.0) / 4.5 * 60.0, 2),

    }

    return {
        "end_stop": end_stop,
        "pinned_destination": {"lat": pin_lat, "lon": pin_lon},
        "walking": walking,
        "route_geometry": osrm["geometry"],        # GeoJSON LineString
        "walking_steps": osrm["steps_text"],       # human-readable
        "walking_steps_raw": osrm["steps_raw"],    # optional
        "note": "Walking route from journey end stop to pinned destination."
    }
