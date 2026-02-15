import requests
import time
from db_connect import get_connection

# OpenStreetMap free API endpoint
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# All Karachi bus stops will use this as a hint
CITY_HINT = "Karachi Pakistan"

def get_lat_lon(stop_name):
    """Fetch latitude and longitude for a stop using OpenStreetMap."""
    params = {
        "q": f"{stop_name}, {CITY_HINT}",
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "Karachi-BRT-Student-Project"
    }

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers)
        data = response.json()

        if len(data) == 0:
            print(f"❌ Not found: {stop_name}")
            return None, None

        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        print(f"✓ Found {stop_name} → {lat}, {lon}")
        return lat, lon

    except Exception as e:
        print(f"Error fetching {stop_name}: {e}")
        return None, None


def update_all_coordinates():
    """Fetch and update coordinates for all stops in database."""
    conn = get_connection()
    cur = conn.cursor()

    # Get all stops that do not have coordinates yet
    cur.execute("""
        SELECT stop_id, stop_name 
        FROM bus_stops
        WHERE latitude IS NULL OR longitude IS NULL
        ORDER BY stop_id;
    """)
    stops = cur.fetchall()

    print(f"🔍 Total stops to process: {len(stops)}")

    for stop_id, stop_name in stops:
        lat, lon = get_lat_lon(stop_name)

        if lat is not None and lon is not None:
            cur.execute("""
                UPDATE bus_stops
                SET latitude = %s, longitude = %s
                WHERE stop_id = %s;
            """, (lat, lon, stop_id))
            conn.commit()
        else:
            print(f"⚠ Skipping {stop_name} (no coordinates found)")

        time.sleep(1)  # REQUIRED because OSM rate-limit is 1 request/second

    cur.close()
    conn.close()
    print("\n🎉 All done!")


if __name__ == "__main__":
    update_all_coordinates()
