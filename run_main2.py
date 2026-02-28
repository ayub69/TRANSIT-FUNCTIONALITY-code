import argparse
import csv
import datetime as dt
import os
import random
import re
import time
from collections import defaultdict

import psycopg2
import requests
from psycopg2.extras import execute_values

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "smart_transit")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "1234")

SOURCE_SCHEMA = "smart_transit"
TARGET_SCHEMA = "smart_transit2"
OSRM_BASE_URL = "https://router.project-osrm.org"


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )


def normalize_key(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())


def normalize_stop_name(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def execute_sql_file(cur, sql_path):
    with open(sql_path, "r", encoding="utf-8") as f:
        cur.execute(f.read())


def ensure_edges_compatibility(cur):
    cur.execute(
        """
        SELECT to_regclass(%s), to_regclass(%s)
        """,
        (f"{SOURCE_SCHEMA}.edges", f"{TARGET_SCHEMA}.edges"),
    )
    source_reg, target_reg = cur.fetchone()
    if source_reg is None:
        raise RuntimeError(f"Source table {SOURCE_SCHEMA}.edges does not exist.")

    if target_reg is None:
        cur.execute(
            f"""
            SELECT
              a.attname AS column_name,
              pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
              a.attnotnull AS not_null,
              pg_get_expr(d.adbin, d.adrelid) AS default_expr
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
            WHERE n.nspname = %s
              AND c.relname = 'edges'
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
            """,
            (SOURCE_SCHEMA,),
        )
        src_cols = cur.fetchall()
        if not src_cols:
            raise RuntimeError("Could not introspect source edges columns.")

        col_defs = []
        for col_name, data_type, not_null, _default_expr in src_cols:
            nn = " NOT NULL" if not_null else ""
            col_defs.append(f'"{col_name}" {data_type}{nn}')
        cur.execute(
            f'CREATE TABLE IF NOT EXISTS {TARGET_SCHEMA}.edges ({", ".join(col_defs)});'
        )

    source_cols = fetch_edge_columns(cur, SOURCE_SCHEMA)
    target_cols = fetch_edge_columns(cur, TARGET_SCHEMA)
    source_sig = [(c["column_name"], c["data_type"]) for c in source_cols]
    target_sig = [(c["column_name"], c["data_type"]) for c in target_cols]
    if source_sig != target_sig:
        raise RuntimeError(
            f"{TARGET_SCHEMA}.edges columns/types do not match {SOURCE_SCHEMA}.edges."
        )

    for idx_col in ("u_stop_id", "v_stop_id", "route_id"):
        if any(c["column_name"] == idx_col for c in target_cols):
            cur.execute(
                f'CREATE INDEX IF NOT EXISTS idx_edges_{idx_col} ON {TARGET_SCHEMA}.edges ("{idx_col}");'
            )

    return target_cols


def fetch_edge_columns(cur, schema):
    cur.execute(
        """
        SELECT
          c.column_name,
          c.data_type,
          c.udt_name,
          c.is_nullable,
          c.column_default
        FROM information_schema.columns c
        WHERE c.table_schema = %s
          AND c.table_name = 'edges'
        ORDER BY c.ordinal_position
        """,
        (schema,),
    )
    out = []
    for name, data_type, udt_name, is_nullable, col_default in cur.fetchall():
        out.append(
            {
                "column_name": name,
                "data_type": data_type,
                "udt_name": udt_name,
                "is_nullable": is_nullable == "YES",
                "column_default": col_default,
            }
        )
    return out


def truncate_target_tables(cur):
    cur.execute(
        f"""
        TRUNCATE TABLE
          {TARGET_SCHEMA}.route_stops,
          {TARGET_SCHEMA}.edges,
          {TARGET_SCHEMA}.routes,
          {TARGET_SCHEMA}.stops;
        """
    )


def pick_field(row, required_aliases):
    norm_map = {normalize_key(k): k for k in row.keys()}
    for alias in required_aliases:
        k = norm_map.get(normalize_key(alias))
        if k:
            return row.get(k, "")
    return ""


def parse_coordinates(raw):
    parts = [p.strip() for p in (raw or "").split(",")]
    if len(parts) != 2:
        raise ValueError(f"Invalid coordinates '{raw}'")
    lat = float(parts[0])
    lon = float(parts[1])
    return lat, lon


def load_stops(cur, stops_csv):
    anomalies = []
    rows = []
    stop_name_to_id = {}

    with open(stops_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            stop_id_raw = pick_field(row, ["stop_id", "stopid"])
            stop_name = pick_field(row, ["stop_name", "stop name"]).strip()
            coord_raw = pick_field(row, ["coordinates", "coordinate"])

            if not stop_id_raw or not stop_name or not coord_raw:
                anomalies.append(f"stops.csv line {line_no}: missing required value(s).")
                continue

            try:
                stop_id = int(str(stop_id_raw).strip())
                lat, lon = parse_coordinates(coord_raw)
            except Exception as exc:
                anomalies.append(f"stops.csv line {line_no}: {exc}")
                continue

            rows.append((stop_id, stop_name, lat, lon))

    if rows:
        execute_values(
            cur,
            f"""
            INSERT INTO {TARGET_SCHEMA}.stops (stop_id, stop_name, lat, lon)
            VALUES %s
            ON CONFLICT (stop_id) DO UPDATE
            SET stop_name = EXCLUDED.stop_name,
                lat = EXCLUDED.lat,
                lon = EXCLUDED.lon
            """,
            rows,
            page_size=1000,
        )

    for stop_id, stop_name, _lat, _lon in rows:
        n = normalize_stop_name(stop_name)
        if n in stop_name_to_id and stop_name_to_id[n] != stop_id:
            anomalies.append(
                f"Duplicate normalized stop name maps to different IDs: '{stop_name}'."
            )
        stop_name_to_id[n] = stop_id

    print(f"Inserted/updated stops: {len(rows)}")
    return stop_name_to_id, anomalies


def infer_line_name_by_position(non_empty_col_pos):
    if non_empty_col_pos < 10:
        return "Red Line"
    if non_empty_col_pos < 15:
        return "EV Line"
    if non_empty_col_pos < 16:
        return "Green Line"
    if non_empty_col_pos < 21:
        return "Pink Line"
    if non_empty_col_pos < 22:
        return "Double Decker"
    return "Other Line"


def load_routes_and_route_stops(cur, order_csv, stop_name_to_id):
    anomalies = []
    with open(order_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        raise RuntimeError("route_sequence CSV is empty.")

    headers = rows[0]
    data_rows = rows[1:]
    max_cols = max(len(r) for r in rows)

    non_empty_cols = []
    for c in range(max_cols):
        non_empty = False
        for r in data_rows:
            cell = r[c].strip() if c < len(r) and r[c] is not None else ""
            if cell:
                non_empty = True
                break
        if non_empty:
            non_empty_cols.append(c)

    routes = []
    route_stops = []
    route_line = {}
    route_names = {}
    route_id = 1

    for pos, col_idx in enumerate(non_empty_cols):
        line_name = infer_line_name_by_position(pos)
        raw_header = headers[col_idx].strip() if col_idx < len(headers) else ""
        route_name = raw_header if raw_header else f"Route {route_id}"
        if not route_name:
            route_name = f"Route {route_id}"

        routes.append((route_id, route_name))
        route_line[route_id] = line_name
        route_names[route_id] = route_name

        seq = 1
        seen_stop_ids = set()
        prev_stop_id = None
        for row_idx, r in enumerate(data_rows, start=2):
            raw_stop = r[col_idx].strip() if col_idx < len(r) and r[col_idx] is not None else ""
            if not raw_stop:
                continue
            norm = normalize_stop_name(raw_stop)
            stop_id = stop_name_to_id.get(norm)
            if stop_id is None:
                anomalies.append(
                    f"route_sequence line {row_idx}, column {col_idx + 1}: stop '{raw_stop}' not found in stops.csv."
                )
                continue
            if stop_id in seen_stop_ids:
                anomalies.append(
                    f"route_id {route_id} ({route_name}): duplicate stop '{raw_stop}' appears more than once."
                )
                continue
            if prev_stop_id == stop_id:
                anomalies.append(
                    f"route_id {route_id} ({route_name}): consecutive duplicate stop '{raw_stop}'."
                )
                continue
            route_stops.append((route_id, seq, stop_id))
            seq += 1
            seen_stop_ids.add(stop_id)
            prev_stop_id = stop_id

        if seq <= 2:
            anomalies.append(
                f"route_id {route_id} ({route_name}): has fewer than 2 valid stops."
            )
        route_id += 1

    if routes:
        execute_values(
            cur,
            f"""
            INSERT INTO {TARGET_SCHEMA}.routes (route_id, route_name)
            VALUES %s
            ON CONFLICT (route_id) DO UPDATE
            SET route_name = EXCLUDED.route_name
            """,
            routes,
            page_size=1000,
        )

    if route_stops:
        execute_values(
            cur,
            f"""
            INSERT INTO {TARGET_SCHEMA}.route_stops (route_id, seq, stop_id)
            VALUES %s
            """,
            route_stops,
            page_size=2000,
        )

    print(f"Inserted/updated routes: {len(routes)}")
    print(f"Inserted route_stops: {len(route_stops)}")
    return route_line, route_names, anomalies


def osrm_route_metrics(lat1, lon1, lat2, lon2, cache):
    key = (lat1, lon1, lat2, lon2)
    if key in cache:
        return cache[key]

    url = (
        f"{OSRM_BASE_URL}/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}"
        f"?overview=false"
    )
    last_error = None
    for attempt in range(1, 4):
        try:
            time.sleep(random.uniform(0.05, 0.10))
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("code") != "Ok":
                raise RuntimeError(f"OSRM response code {payload.get('code')}")
            route0 = payload["routes"][0]
            dist_km = float(route0["distance"]) / 1000.0
            time_min = float(route0["duration"]) / 60.0
            cache[key] = (dist_km, time_min)
            return cache[key]
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                time.sleep(0.2 * attempt)

    raise RuntimeError(f"OSRM failed after 3 retries for {url}: {last_error}")


def pick_special_edge_columns(edge_cols):
    names = {c["column_name"].lower(): c["column_name"] for c in edge_cols}

    def find_by_contains(keywords):
        for c in edge_cols:
            n = c["column_name"].lower()
            if any(k in n for k in keywords):
                return c["column_name"]
        return None

    route_col = names.get("route_id")
    u_col = names.get("u_stop_id")
    v_col = names.get("v_stop_id")
    dist_col = (
        names.get("distance_km")
        or names.get("distance")
        or find_by_contains(["distance", "dist"])
    )
    time_col = (
        names.get("time_min")
        or names.get("duration_min")
        or names.get("time")
        or find_by_contains(["time", "duration"])
    )
    female_col = names.get("female_only") or find_by_contains(["female"])
    line_col = names.get("line_name") or names.get("route_name") or find_by_contains(["line"])

    required = {
        "route_id": route_col,
        "u_stop_id": u_col,
        "v_stop_id": v_col,
        "distance": dist_col,
        "time": time_col,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(f"Could not map required edges columns: {missing}")

    return {
        "route_col": route_col,
        "u_col": u_col,
        "v_col": v_col,
        "dist_col": dist_col,
        "time_col": time_col,
        "female_col": female_col,
        "line_col": line_col,
    }


def default_for_required_column(col):
    n = col["column_name"].lower()
    t = col["data_type"].lower()
    u = col["udt_name"].lower()

    if "edge_id" == n:
        return None
    if n in ("fare", "headway", "headway_min"):
        return 0
    if n in ("created_at", "updated_at"):
        return dt.datetime.utcnow()
    if n in ("active", "is_active"):
        return True
    if "boolean" in t or u == "bool":
        return False
    if any(k in t for k in ("integer", "numeric", "double precision", "real", "bigint", "smallint")):
        return 0
    if "timestamp" in t:
        return dt.datetime.utcnow()
    if t == "date":
        return dt.date.today()
    if any(k in t for k in ("character", "text")):
        return ""
    if u in ("json", "jsonb"):
        return "{}"
    return None


def generate_edges_from_route_stops(cur, edge_cols, route_line, route_names):
    anomalies = []
    mapped = pick_special_edge_columns(edge_cols)

    cur.execute(
        f"""
        SELECT rs.route_id, rs.seq, rs.stop_id, s.lat, s.lon
        FROM {TARGET_SCHEMA}.route_stops rs
        JOIN {TARGET_SCHEMA}.stops s ON s.stop_id = rs.stop_id
        ORDER BY rs.route_id, rs.seq
        """
    )
    by_route = defaultdict(list)
    for route_id, seq, stop_id, lat, lon in cur.fetchall():
        by_route[route_id].append((seq, stop_id, float(lat), float(lon)))

    pairs = {}
    for route_id, seq_stops in by_route.items():
        if len(seq_stops) < 2:
            anomalies.append(f"route_id {route_id}: fewer than 2 stops, no edges generated.")
            continue
        for i in range(len(seq_stops) - 1):
            _s1, u_stop, u_lat, u_lon = seq_stops[i]
            _s2, v_stop, v_lat, v_lon = seq_stops[i + 1]
            if u_stop == v_stop:
                anomalies.append(f"route_id {route_id}: self-loop at stop {u_stop} skipped.")
                continue
            pairs[(route_id, u_stop, v_stop)] = (u_lat, u_lon, v_lat, v_lon)
            pairs[(route_id, v_stop, u_stop)] = (v_lat, v_lon, u_lat, u_lon)

    osrm_cache = {}
    edge_rows = []

    edge_id_col = None
    for c in edge_cols:
        if c["column_name"].lower() == "edge_id" and not c["is_nullable"] and not c["column_default"]:
            edge_id_col = c["column_name"]
            break

    next_edge_id = None
    if edge_id_col:
        cur.execute(f'SELECT COALESCE(MAX("{edge_id_col}"), 0) FROM {TARGET_SCHEMA}.edges')
        next_edge_id = int(cur.fetchone()[0]) + 1

    ordered_cols = [c["column_name"] for c in edge_cols]

    for (route_id, u_stop, v_stop), (lat1, lon1, lat2, lon2) in pairs.items():
        dist_km, time_min = osrm_route_metrics(lat1, lon1, lat2, lon2, osrm_cache)
        line_name = route_line.get(route_id, "Other Line")
        route_name = route_names.get(route_id, f"Route {route_id}")
        female_only = line_name.strip().lower() == "pink line"

        row = {
            mapped["route_col"]: route_id,
            mapped["u_col"]: u_stop,
            mapped["v_col"]: v_stop,
            mapped["dist_col"]: dist_km,
            mapped["time_col"]: time_min,
        }
        if mapped["female_col"]:
            row[mapped["female_col"]] = female_only
        if mapped["line_col"]:
            row[mapped["line_col"]] = line_name if "line" in mapped["line_col"].lower() else route_name

        for c in edge_cols:
            col = c["column_name"]
            if col in row:
                continue

            if edge_id_col and col == edge_id_col:
                row[col] = next_edge_id
                next_edge_id += 1
                continue

            if (not c["is_nullable"]) and (c["column_default"] is None):
                dv = default_for_required_column(c)
                if dv is None:
                    raise RuntimeError(
                        f"Cannot infer required value for non-null edges column '{col}'."
                    )
                row[col] = dv

        edge_rows.append(tuple(row.get(cn) for cn in ordered_cols))

    if edge_rows:
        insert_cols = ", ".join([f'"{c}"' for c in ordered_cols])
        execute_values(
            cur,
            f"""
            INSERT INTO {TARGET_SCHEMA}.edges ({insert_cols})
            VALUES %s
            """,
            edge_rows,
            page_size=500,
        )

    print(f"Inserted edges (forward + reverse): {len(edge_rows)}")
    print(f"Unique OSRM calls (with cache): {len(osrm_cache)}")
    return anomalies


def print_transfer_stops(cur):
    cur.execute(
        f"""
        SELECT
          s.stop_id,
          s.stop_name,
          COUNT(*) AS incident_edges,
          COUNT(DISTINCT e.route_id) AS route_count
        FROM {TARGET_SCHEMA}.stops s
        JOIN {TARGET_SCHEMA}.edges e
          ON e.u_stop_id = s.stop_id OR e.v_stop_id = s.stop_id
        GROUP BY s.stop_id, s.stop_name
        HAVING COUNT(*) > 2 OR COUNT(DISTINCT e.route_id) > 1
        ORDER BY route_count DESC, incident_edges DESC, s.stop_id
        """
    )
    rows = cur.fetchall()
    print("\nTransfer stops (multiple edges / multi-route):")
    for stop_id, stop_name, incident_edges, route_count in rows:
        print(
            f"  stop_id={stop_id}, stop_name={stop_name}, "
            f"incident_edges={incident_edges}, routes={route_count}"
        )
    if not rows:
        print("  (none)")


def print_post_load_anomalies(cur, collected_anomalies):
    cur.execute(
        f"""
        SELECT s.stop_id, s.stop_name
        FROM {TARGET_SCHEMA}.stops s
        LEFT JOIN {TARGET_SCHEMA}.edges e
          ON e.u_stop_id = s.stop_id OR e.v_stop_id = s.stop_id
        WHERE e.u_stop_id IS NULL
        ORDER BY s.stop_id
        """
    )
    isolated = cur.fetchall()
    if isolated:
        for stop_id, stop_name in isolated:
            collected_anomalies.append(
                f"Isolated stop (no edges): stop_id={stop_id}, stop_name={stop_name}"
            )

    print("\nAnomalies that may affect output:")
    if not collected_anomalies:
        print("  (none detected)")
        return
    for a in collected_anomalies:
        print(f"  - {a}")


def main():
    parser = argparse.ArgumentParser(description="Load smart_transit2 schema from CSV + OSRM.")
    parser.add_argument("--stops", required=True, help="Path to stops.csv")
    parser.add_argument("--order", required=True, help="Path to route sequence CSV")
    parser.add_argument(
        "--migration",
        default="migration_smart_transit2.sql",
        help="Path to migration SQL file",
    )
    args = parser.parse_args()

    if not os.path.exists(args.stops):
        raise FileNotFoundError(args.stops)
    if not os.path.exists(args.order):
        raise FileNotFoundError(args.order)
    if not os.path.exists(args.migration):
        raise FileNotFoundError(args.migration)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            execute_sql_file(cur, args.migration)
            edge_cols = ensure_edges_compatibility(cur)
            truncate_target_tables(cur)

            stop_map, anomalies1 = load_stops(cur, args.stops)
            route_line, route_names, anomalies2 = load_routes_and_route_stops(cur, args.order, stop_map)
            anomalies3 = generate_edges_from_route_stops(cur, edge_cols, route_line, route_names)

            print_transfer_stops(cur)
            print_post_load_anomalies(cur, anomalies1 + anomalies2 + anomalies3)

        conn.commit()
        print("\nDone: transaction committed.")
    except Exception as exc:
        conn.rollback()
        print("\nERROR: transaction rolled back.")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
