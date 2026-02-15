import requests
import psycopg2
from db_connect import get_connection 
OSRM = "https://router.project-osrm.org"
SCHEMA = "smart_transit2"
ROUTE_ID = 22
LINE_NAME = "Double Decker"
FEMALE_ONLY = False

STOP_ORDER = [
    "malir halt",
    "airport",
    "colony gate",
    "nata khan bridge",
    "drigh road station",
    "nursery",
    "baloch colony",
    "ftc",
    "zainab market",
]

def osrm_car_km_min(lat1, lon1, lat2, lon2):
    url = f"{OSRM}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    r = requests.get(url, timeout=20).json()
    if r.get("code") != "Ok":
        raise RuntimeError(r.get("message", "OSRM failed"))
    dist_m = r["routes"][0]["distance"]
    dur_s = r["routes"][0]["duration"]
    return dist_m / 1000.0, dur_s / 60.0

def main():
    # conn = psycopg2.connect(
    #     host="localhost",
    #     dbname="YOUR_DB",
    #     user="YOUR_USER",
    #     password="YOUR_PASS",
    #     port=5432
    # )
    conn=get_connection()
    conn.autocommit = False

    with conn.cursor() as cur:
        # Get stop ids + coords using trigram-ish matching
        stop_rows = []
        for name in STOP_ORDER:
            cur.execute(f"""
                SELECT stop_id, stop_name, lat, lon
                FROM {SCHEMA}.stops
                ORDER BY similarity(lower(stop_name), lower(%s)) DESC
                LIMIT 1;
            """, (name,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Stop not found for: {name}")
            stop_rows.append(row)

        # Insert edges consecutive
        for (u_id, u_name, u_lat, u_lon), (v_id, v_name, v_lat, v_lon) in zip(stop_rows, stop_rows[1:]):
            dist_km, time_min = osrm_car_km_min(u_lat, u_lon, v_lat, v_lon)

            cur.execute(f"""
                INSERT INTO {SCHEMA}.edges (u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT DO NOTHING;
            """, (u_id, v_id, ROUTE_ID, LINE_NAME, dist_km, time_min, FEMALE_ONLY))

            

    conn.commit()
    conn.close()
    print("✅ Route 22 edges inserted (forward.")

if __name__ == "__main__":
    main()
