import psycopg2
import requests
from db_connect import get_connection
OSRM_URL = "https://router.project-osrm.org"  # change if different
ROUTE_ID = 21
LINE_NAME = "Green"

# FORWARD CHAIN ONLY
STOP_CHAIN = [
    171, 170, 169, 168,
    197,  # nagan chowrangi
    198,  # up morr
    199,  # north karachi
    165,
    164
]



def osrm_distance_time(lat1, lon1, lat2, lon2):
    url = f"{OSRM_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    r = requests.get(url, timeout=15).json()
    if r.get("code") != "Ok":
        raise RuntimeError(f"OSRM failed: {r}")
    route = r["routes"][0]
    return route["distance"] / 1000.0, route["duration"] / 60.0

def main():
    conn = get_connection()
    cur = conn.cursor()

    # fetch stop coordinates
    cur.execute("""
        SELECT stop_id, lat, lon
        FROM smart_transit2.stops
        WHERE stop_id = ANY(%s)
    """, (STOP_CHAIN,))
    coords = {sid: (lat, lon) for sid, lat, lon in cur.fetchall()}

    for i in range(len(STOP_CHAIN) - 1):
        u = STOP_CHAIN[i]
        v = STOP_CHAIN[i + 1]

        lat1, lon1 = coords[u]
        lat2, lon2 = coords[v]

        dist_km, time_min = osrm_distance_time(lat1, lon1, lat2, lon2)

        cur.execute("""
            INSERT INTO smart_transit2.edges
            (u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only)
            VALUES (%s,%s,%s,%s,%s,%s,false)
        """, (u, v, ROUTE_ID, LINE_NAME, round(dist_km, 4), round(time_min, 2)))

        print(f"Inserted: {u} -> {v} | {dist_km:.2f} km | {time_min:.1f} min")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Green line forward chain completed.")

if __name__ == "__main__":
    main()
