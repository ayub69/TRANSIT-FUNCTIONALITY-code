from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import re

import requests
from fastapi import HTTPException

from db_connect import get_connection
from services.graph_service import init_graphs
from services.map_service import init_map_cache

SCHEMA = "smart_transit3"
OSRM_BASE_URL = "https://router.project-osrm.org"


def ensure_admin_tables() -> None:
    q = f"""
    CREATE TABLE IF NOT EXISTS {SCHEMA}.delay_reports (
        delay_id BIGSERIAL PRIMARY KEY,
        route_id INTEGER NOT NULL REFERENCES {SCHEMA}.routes(route_id) ON DELETE CASCADE,
        from_stop_id INTEGER NOT NULL REFERENCES {SCHEMA}.stops(stop_id) ON DELETE CASCADE,
        to_stop_id INTEGER NOT NULL REFERENCES {SCHEMA}.stops(stop_id) ON DELETE CASCADE,
        delay_min DOUBLE PRECISION NOT NULL CHECK (delay_min > 0),
        reason TEXT,
        reported_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        expires_at TIMESTAMP WITHOUT TIME ZONE,
        active BOOLEAN NOT NULL DEFAULT TRUE
    );
    CREATE INDEX IF NOT EXISTS idx_delay_reports_active
      ON {SCHEMA}.delay_reports (active, route_id, reported_at, expires_at);
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(q)
        conn.commit()


def _norm_spaces(x: str) -> str:
    return re.sub(r"\s+", " ", (x or "").strip())


def _line_name_key(x: str) -> str:
    s = _norm_spaces(x).lower()
    s = re.sub(r"\s+line$", "", s)
    s = re.sub(r"[\s_-]+", "", s)
    return s


def _resolve_route_id_by_name(cur, route_name: str) -> tuple[int, str]:
    needle = _norm_spaces(route_name)
    if not needle:
        raise HTTPException(status_code=400, detail="route_name is required")

    cur.execute(
        f"""
        SELECT route_id, route_name
        FROM {SCHEMA}.routes
        WHERE LOWER(route_name) = LOWER(%s)
        ORDER BY route_id;
        """,
        (needle,),
    )
    exact = cur.fetchall()
    if len(exact) == 1:
        rid, rname = exact[0]
        return int(rid), str(rname)
    if len(exact) > 1:
        raise HTTPException(
            status_code=409,
            detail=f"Multiple routes matched '{route_name}'. Please use a unique route name.",
        )

    cur.execute(
        f"""
        SELECT route_id, route_name
        FROM {SCHEMA}.routes
        WHERE LOWER(route_name) LIKE LOWER(%s)
        ORDER BY route_id
        LIMIT 5;
        """,
        (f"%{needle}%",),
    )
    fuzzy = cur.fetchall()
    if not fuzzy:
        raise HTTPException(status_code=404, detail=f"Route '{route_name}' not found.")
    if len(fuzzy) > 1:
        names = [r[1] for r in fuzzy]
        raise HTTPException(
            status_code=409,
            detail=f"Route name is ambiguous. Matches: {names}",
        )
    rid, rname = fuzzy[0]
    return int(rid), str(rname)


def _resolve_stop_by_name(cur, stop_name: str) -> tuple[int, str, float, float]:
    needle = _norm_spaces(stop_name)
    if not needle:
        raise HTTPException(status_code=400, detail="stop_name is required")

    cur.execute(
        f"""
        SELECT stop_id, stop_name, lat, lon
        FROM {SCHEMA}.stops
        WHERE LOWER(stop_name) = LOWER(%s)
        ORDER BY stop_id;
        """,
        (needle,),
    )
    exact = cur.fetchall()
    if len(exact) == 1:
        sid, sname, lat, lon = exact[0]
        return int(sid), str(sname), float(lat), float(lon)
    if len(exact) > 1:
        raise HTTPException(
            status_code=409,
            detail=f"Multiple stops matched '{stop_name}'. Please refine the name.",
        )

    cur.execute(
        f"""
        SELECT stop_id, stop_name, lat, lon
        FROM {SCHEMA}.stops
        WHERE LOWER(stop_name) LIKE LOWER(%s)
        ORDER BY stop_name
        LIMIT 5;
        """,
        (f"%{needle}%",),
    )
    fuzzy = cur.fetchall()
    if not fuzzy:
        raise HTTPException(status_code=404, detail=f"Stop '{stop_name}' not found.")
    if len(fuzzy) > 1:
        names = [r[1] for r in fuzzy]
        raise HTTPException(
            status_code=409,
            detail=f"Stop name is ambiguous. Matches: {names}",
        )
    sid, sname, lat, lon = fuzzy[0]
    return int(sid), str(sname), float(lat), float(lon)


def _get_or_create_stop(cur, stop_name: str, lat: float | None, lon: float | None) -> tuple[int, str]:
    try:
        sid, sname, _, _ = _resolve_stop_by_name(cur, stop_name)
        return sid, sname
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        if lat is None or lon is None:
            raise HTTPException(
                status_code=400,
                detail=f"Stop '{stop_name}' does not exist. Provide lat/lon to create it.",
            )

    clean_name = _norm_spaces(stop_name)
    cur.execute(f"SELECT COALESCE(MAX(stop_id), 0) + 1 FROM {SCHEMA}.stops;")
    sid = int(cur.fetchone()[0])
    cur.execute(
        f"""
        INSERT INTO {SCHEMA}.stops (stop_id, stop_name, lat, lon)
        VALUES (%s, %s, %s, %s);
        """,
        (sid, clean_name, float(lat), float(lon)),
    )
    return sid, clean_name


def _fetch_route_stop_ids(cur, route_id: int) -> list[int]:
    cur.execute(
        f"""
        SELECT stop_id
        FROM {SCHEMA}.route_stops
        WHERE route_id = %s
        ORDER BY seq;
        """,
        (route_id,),
    )
    return [int(r[0]) for r in cur.fetchall()]


def _osrm_metrics(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=false"
    )
    last_err = None
    for _ in range(3):
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            payload = r.json()
            if payload.get("code") != "Ok":
                raise RuntimeError(f"OSRM code={payload.get('code')}")
            route0 = payload["routes"][0]
            dist_km = float(route0["distance"]) / 1000.0
            time_min = float(route0["duration"]) / 60.0
            return dist_km, time_min
        except Exception as exc:
            last_err = exc
    raise HTTPException(status_code=502, detail=f"OSRM routing failed: {last_err}")


def _route_line_name(cur, route_id: int, route_name: str) -> str:
    cur.execute(
        f"""
        SELECT line_name
        FROM {SCHEMA}.edges
        WHERE route_id = %s
          AND line_name IS NOT NULL
          AND TRIM(line_name) <> ''
        LIMIT 1;
        """,
        (route_id,),
    )
    row = cur.fetchone()
    if row and row[0]:
        return str(row[0]).strip()

    key = _line_name_key(route_name)
    if "pink" in key:
        return "Pink Line"
    if "green" in key:
        return "Green Line"
    if "red" in key:
        return "Red Line"
    if "ev" in key:
        return "EV Line"
    if "doubledecker" in key:
        return "Double Decker"
    return route_name


def _is_female_only_line(line_name: str) -> bool:
    return "pink" in _line_name_key(line_name)


def _rebuild_route_stops_and_edges(cur, route_id: int, route_name: str, stop_ids: list[int]) -> None:
    if len(stop_ids) < 2:
        raise HTTPException(status_code=400, detail="A route must contain at least 2 stops.")
    line_name = _route_line_name(cur, route_id, route_name)
    female_only = _is_female_only_line(line_name)

    # Rewrite sequence atomically.
    cur.execute(f"DELETE FROM {SCHEMA}.route_stops WHERE route_id = %s;", (route_id,))
    for idx, sid in enumerate(stop_ids, start=1):
        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.route_stops (route_id, seq, stop_id)
            VALUES (%s, %s, %s);
            """,
            (route_id, idx, sid),
        )

    # Delete old route edges and rebuild from adjacency.
    cur.execute(f"DELETE FROM {SCHEMA}.edges WHERE route_id = %s;", (route_id,))

    cur.execute(
        f"""
        SELECT stop_id, lat, lon
        FROM {SCHEMA}.stops
        WHERE stop_id = ANY(%s);
        """,
        (stop_ids,),
    )
    rows = cur.fetchall()
    coords = {int(sid): (float(lat), float(lon)) for sid, lat, lon in rows}

    for i in range(len(stop_ids) - 1):
        u = int(stop_ids[i])
        v = int(stop_ids[i + 1])
        if u not in coords or v not in coords:
            raise HTTPException(status_code=400, detail=f"Missing coordinates for stop ids {u}->{v}.")

        lat1, lon1 = coords[u]
        lat2, lon2 = coords[v]
        dist_km, time_min = _osrm_metrics(lat1, lon1, lat2, lon2)

        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.edges
            (route_id, u_stop_id, v_stop_id, line_name, distance_km, time_min, female_only)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (route_id, u, v, line_name, dist_km, time_min, female_only),
        )
        cur.execute(
            f"""
            INSERT INTO {SCHEMA}.edges
            (route_id, u_stop_id, v_stop_id, line_name, distance_km, time_min, female_only)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (route_id, v, u, line_name, dist_km, time_min, female_only),
        )

    first_sid = int(stop_ids[0])
    last_sid = int(stop_ids[-1])
    cur.execute(
        f"""
        UPDATE {SCHEMA}.routes r
        SET start_stop_name = s1.stop_name,
            end_stop_name = s2.stop_name
        FROM {SCHEMA}.stops s1, {SCHEMA}.stops s2
        WHERE r.route_id = %s
          AND s1.stop_id = %s
          AND s2.stop_id = %s;
        """,
        (route_id, first_sid, last_sid),
    )


def add_stop_to_route(
    route_name: str,
    stop_name: str,
    before_stop_name: str | None = None,
    after_stop_name: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            route_id, resolved_route_name = _resolve_route_id_by_name(cur, route_name)
            stop_id, resolved_stop_name = _get_or_create_stop(cur, stop_name, lat, lon)

            stop_ids = _fetch_route_stop_ids(cur, route_id)
            if stop_id in stop_ids:
                raise HTTPException(
                    status_code=409,
                    detail=f"Stop '{resolved_stop_name}' already exists in route '{resolved_route_name}'.",
                )

            before_given = bool(_norm_spaces(before_stop_name or ""))
            after_given = bool(_norm_spaces(after_stop_name or ""))
            if not before_given and not after_given:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Provide insertion anchors: before_stop_name and/or after_stop_name. "
                        "Start: only before_stop_name. End: only after_stop_name. "
                        "Middle: both before_stop_name and after_stop_name."
                    ),
                )

            if before_given and not after_given:
                # Start insertion only.
                before_id, _, _, _ = _resolve_stop_by_name(cur, before_stop_name or "")
                if before_id not in stop_ids:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stop '{before_stop_name}' is not part of route '{resolved_route_name}'.",
                    )
                if stop_ids[0] != before_id:
                    raise HTTPException(
                        status_code=400,
                        detail="For start insertion with only before_stop_name, it must match the current first stop.",
                    )
                insert_idx = 0
            elif after_given and not before_given:
                # End insertion only.
                after_id, _, _, _ = _resolve_stop_by_name(cur, after_stop_name)
                if after_id not in stop_ids:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stop '{after_stop_name}' is not part of route '{resolved_route_name}'.",
                    )
                if stop_ids[-1] != after_id:
                    raise HTTPException(
                        status_code=400,
                        detail="For end insertion with only after_stop_name, it must match the current last stop.",
                    )
                insert_idx = len(stop_ids)
            else:
                # Middle insertion: after and before are both required and must be adjacent.
                after_id, _, _, _ = _resolve_stop_by_name(cur, after_stop_name or "")
                before_id, _, _, _ = _resolve_stop_by_name(cur, before_stop_name or "")
                if after_id not in stop_ids:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stop '{after_stop_name}' is not part of route '{resolved_route_name}'.",
                    )
                if before_id not in stop_ids:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stop '{before_stop_name}' is not part of route '{resolved_route_name}'.",
                    )

                idx_after = stop_ids.index(after_id)
                idx_before = stop_ids.index(before_id)
                if idx_before != idx_after + 1:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "For middle insertion, after_stop_name must be immediately before before_stop_name "
                            "in current route sequence."
                        ),
                    )
                insert_idx = idx_before

            stop_ids.insert(insert_idx, stop_id)
            _rebuild_route_stops_and_edges(cur, route_id, resolved_route_name, stop_ids)
        conn.commit()

    init_graphs()
    init_map_cache()
    return {
        "message": "Stop added and route edges rebuilt successfully.",
        "route_name": resolved_route_name,
        "added_stop_name": resolved_stop_name,
        "route_stop_sequence": get_route_sequence_by_name(resolved_route_name),
    }


def remove_stop_from_route(route_name: str, stop_name: str) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            route_id, resolved_route_name = _resolve_route_id_by_name(cur, route_name)
            stop_id, resolved_stop_name, _, _ = _resolve_stop_by_name(cur, stop_name)
            stop_ids = _fetch_route_stop_ids(cur, route_id)
            if stop_id not in stop_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Stop '{resolved_stop_name}' is not in route '{resolved_route_name}'.",
                )

            if len(stop_ids) <= 2:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot remove stop: route would have fewer than 2 stops.",
                )

            stop_ids = [sid for sid in stop_ids if sid != stop_id]
            _rebuild_route_stops_and_edges(cur, route_id, resolved_route_name, stop_ids)
        conn.commit()

    init_graphs()
    init_map_cache()
    return {
        "message": "Stop removed, dangling edges cleared, and neighboring stops reconnected.",
        "route_name": resolved_route_name,
        "removed_stop_name": resolved_stop_name,
        "route_stop_sequence": get_route_sequence_by_name(resolved_route_name),
    }


def get_route_sequence_by_name(route_name: str) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            route_id, resolved_route_name = _resolve_route_id_by_name(cur, route_name)
            cur.execute(
                f"""
                SELECT rs.seq, s.stop_id, s.stop_name, s.lat, s.lon
                FROM {SCHEMA}.route_stops rs
                JOIN {SCHEMA}.stops s ON s.stop_id = rs.stop_id
                WHERE rs.route_id = %s
                ORDER BY rs.seq;
                """,
                (route_id,),
            )
            rows = cur.fetchall()
    return {
        "route_name": resolved_route_name,
        "stops": [
            {
                "seq": int(seq),
                "stop_id": int(sid),
                "stop_name": str(sname),
                "lat": float(lat),
                "lon": float(lon),
            }
            for seq, sid, sname, lat, lon in rows
        ],
    }


def report_delay(
    route_name: str,
    from_stop_name: str,
    to_stop_name: str,
    delay_min: float,
    reason: str | None = None,
    valid_for_min: int | None = 60,
) -> dict[str, Any]:
    if float(delay_min) <= 0:
        raise HTTPException(status_code=400, detail="delay_min must be greater than 0.")

    expires_at = None
    if valid_for_min is not None:
        if int(valid_for_min) <= 0:
            raise HTTPException(status_code=400, detail="valid_for_min must be positive.")
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=int(valid_for_min))

    with get_connection() as conn:
        with conn.cursor() as cur:
            route_id, resolved_route_name = _resolve_route_id_by_name(cur, route_name)
            from_id, from_name, _, _ = _resolve_stop_by_name(cur, from_stop_name)
            to_id, to_name, _, _ = _resolve_stop_by_name(cur, to_stop_name)

            cur.execute(
                f"""
                INSERT INTO {SCHEMA}.delay_reports
                (route_id, from_stop_id, to_stop_id, delay_min, reason, expires_at, active)
                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                RETURNING delay_id, reported_at;
                """,
                (route_id, from_id, to_id, float(delay_min), reason, expires_at),
            )
            delay_id, reported_at = cur.fetchone()
        conn.commit()

    init_graphs()
    return {
        "message": "Delay reported and applied to routing weights.",
        "delay_id": int(delay_id),
        "route_name": resolved_route_name,
        "from_stop_name": from_name,
        "to_stop_name": to_name,
        "delay_min": float(delay_min),
        "reported_at": reported_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


def list_active_delays(route_name: str | None = None) -> dict[str, Any]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            route_filter_sql = ""
            params: list[Any] = []
            if route_name:
                route_id, _ = _resolve_route_id_by_name(cur, route_name)
                route_filter_sql = "AND d.route_id = %s"
                params.append(route_id)

            cur.execute(
                f"""
                SELECT
                    d.delay_id,
                    r.route_name,
                    s1.stop_name,
                    s2.stop_name,
                    d.delay_min,
                    d.reason,
                    d.reported_at,
                    d.expires_at,
                    d.active
                FROM {SCHEMA}.delay_reports d
                JOIN {SCHEMA}.routes r ON r.route_id = d.route_id
                JOIN {SCHEMA}.stops s1 ON s1.stop_id = d.from_stop_id
                JOIN {SCHEMA}.stops s2 ON s2.stop_id = d.to_stop_id
                WHERE d.active = TRUE
                  AND (d.expires_at IS NULL OR d.expires_at > NOW())
                  {route_filter_sql}
                ORDER BY d.reported_at DESC;
                """,
                params,
            )
            rows = cur.fetchall()
    return {
        "active_delays": [
            {
                "delay_id": int(did),
                "route_name": rname,
                "from_stop_name": s1,
                "to_stop_name": s2,
                "delay_min": float(dmin),
                "reason": reason,
                "reported_at": rpt.isoformat() if rpt else None,
                "expires_at": exp.isoformat() if exp else None,
                "active": bool(active),
            }
            for did, rname, s1, s2, dmin, reason, rpt, exp, active in rows
        ]
    }


def get_system_counts() -> dict[str, int]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.stops;")
            total_stops = int(cur.fetchone()[0])
            cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.routes;")
            total_routes = int(cur.fetchone()[0])
    return {
        "total_stops": total_stops,
        "total_routes": total_routes,
    }


def admin_panel_html() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Transit Admin Panel</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --accent: #0d9488;
    }
    body { margin: 0; padding: 24px; font-family: "Segoe UI", Tahoma, sans-serif; background: linear-gradient(180deg, #eef5ff, var(--bg)); color: var(--ink); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
    .card { background: var(--card); border-radius: 14px; padding: 16px; box-shadow: 0 6px 20px rgba(15,23,42,.08); }
    h1 { margin: 0 0 16px; }
    h2 { margin: 0 0 10px; font-size: 18px; }
    label { display: block; margin: 8px 0 4px; color: var(--muted); font-size: 13px; }
    input { width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 8px; }
    button { margin-top: 10px; padding: 9px 12px; border: 0; border-radius: 8px; background: var(--accent); color: #fff; cursor: pointer; }
    pre { background: #0b1220; color: #dbeafe; padding: 10px; border-radius: 8px; overflow: auto; min-height: 120px; }
  </style>
</head>
<body>
  <h1>Transit Admin Panel</h1>
    <div class="grid">
    <div class="card">
      <h2>Insert Stop In Route</h2>
      <label>Route Name</label><input id="ins_route" />
      <label>Stop Name</label><input id="ins_stop" />
      <label>Before Stop Name (start/middle)</label><input id="ins_before" />
      <label>After Stop Name (optional)</label><input id="ins_after" />
      <label>Lat (only if stop is new)</label><input id="ins_lat" type="number" step="any" />
      <label>Lon (only if stop is new)</label><input id="ins_lon" type="number" step="any" />
      <button onclick="insertStop()">Insert Stop</button>
    </div>
    <div class="card">
      <h2>Remove Stop From Route</h2>
      <label>Route Name</label><input id="del_route" />
      <label>Stop Name</label><input id="del_stop" />
      <button onclick="removeStop()">Remove Stop</button>
    </div>
    <div class="card">
      <h2>Report Delay</h2>
      <label>Route Name</label><input id="d_route" />
      <label>From Stop</label><input id="d_from" />
      <label>To Stop</label><input id="d_to" />
      <label>Delay Minutes</label><input id="d_min" type="number" step="any" />
      <label>Valid For Minutes</label><input id="d_valid" type="number" value="60" />
      <label>Reason</label><input id="d_reason" />
      <button onclick="reportDelay()">Report Delay</button>
    </div>
  </div>
  <h2>Response</h2>
  <pre id="out"></pre>
  <script>
    const out = document.getElementById("out");
    async function callApi(url, method, body) {
      const res = await fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      out.textContent = JSON.stringify(data, null, 2);
    }
    function clean(v) { return (v ?? "").toString().trim(); }
    async function insertStop() {
      const lat = clean(document.getElementById("ins_lat").value);
      const lon = clean(document.getElementById("ins_lon").value);
      await callApi("/admin/routes/stops/insert", "POST", {
        route_name: clean(document.getElementById("ins_route").value),
        stop_name: clean(document.getElementById("ins_stop").value),
        before_stop_name: clean(document.getElementById("ins_before").value) || null,
        after_stop_name: clean(document.getElementById("ins_after").value) || null,
        lat: lat ? Number(lat) : null,
        lon: lon ? Number(lon) : null
      });
    }
    async function removeStop() {
      await callApi("/admin/routes/stops/remove", "POST", {
        route_name: clean(document.getElementById("del_route").value),
        stop_name: clean(document.getElementById("del_stop").value)
      });
    }
    async function reportDelay() {
      await callApi("/admin/delays/report", "POST", {
        route_name: clean(document.getElementById("d_route").value),
        from_stop_name: clean(document.getElementById("d_from").value),
        to_stop_name: clean(document.getElementById("d_to").value),
        delay_min: Number(clean(document.getElementById("d_min").value)),
        valid_for_min: Number(clean(document.getElementById("d_valid").value)),
        reason: clean(document.getElementById("d_reason").value) || null
      });
    }
  </script>
</body>
</html>
"""
