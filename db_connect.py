import psycopg2
import psycopg2.extras

DB_NAME = "smart_transit"
DB_USER = "postgres"
DB_PASSWORD = "1234"
DB_HOST = "localhost"
DB_PORT = "5432"
SCHEMA = "smart_transit2"

def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )

def fetch_all_stops():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        f"""
        SELECT
            stop_id,
            stop_name,
            lat AS latitude,
            lon AS longitude
        FROM {SCHEMA}.stops
        ORDER BY stop_id;
        """
    )
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def fetch_all_routes():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        f"""
        SELECT
            r.route_id,
            r.route_name AS route_number,
            COALESCE(NULLIF(e.line_name, ''), r.route_name) AS route_type
        FROM {SCHEMA}.routes r
        LEFT JOIN LATERAL (
            SELECT line_name
            FROM {SCHEMA}.edges e
            WHERE e.route_id = r.route_id
            LIMIT 1
        ) e ON TRUE
        ORDER BY r.route_id;
        """
    )
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def fetch_transfer_stops(route_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT
            rs.seq AS stop_order,
            s.stop_id,
            s.stop_name,
            s.lat AS latitude,
            s.lon AS longitude
        FROM smart_transit2.route_stops rs
        JOIN smart_transit2.stops s ON rs.stop_id = s.stop_id
        WHERE rs.route_id = %s
        ORDER BY rs.seq;
    """, (route_id,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def get_stop_coordinates(self, stop_name):
    query = """
        SELECT lat AS latitude, lon AS longitude
        FROM smart_transit2.stops
        WHERE LOWER(stop_name) = LOWER(%s)
    """
    result = self.fetch_one(query, (stop_name,))
    return result  # returns tuple (lat, lon) or None
