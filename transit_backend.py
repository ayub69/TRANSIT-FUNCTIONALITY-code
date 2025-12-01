import networkx as nx
import math

class TransitBackend:
    """
    Main backend that will satisfy all routing-related Functional Requirements (FR2.1.x).
    Right now this is only the structural skeleton.
    """

    def __init__(self):
        # =============================
        # DATA STRUCTURES dummy 
        # =============================
        
        # Dictionary of stops: {stop_id: {"name": ..., "lat": ..., "lon": ...}}
        self.stops = {}

        # Dictionary of bus lines: {line_name: {"stops": [...], "color": "..."}}
        self.lines = {}

        # Road connections between stops with distances: [(stopA, stopB, distance_km), ...]
        self.road_segments = []

        # NetworkX graph for routing:
        self.graph = nx.Graph()
        self._build_dummy_data()
        self._build_graph()
        # Build dummy example data (Step 2)
        # Leave empty for now until we build FR2.1.1–FR2.1.2
        # self._build_dummy_data()
        # self._build_graph()
     # ============================================================
    # ==============  BUILDING THE NETWORK  ======================
    # ============================================================

    def _build_dummy_data(self):
        """
        Simple dummy dataset: 10 stops, 4 lines.
        Coordinates are fake but consistent.
        """

        # 10 stops with simple coordinates
        self.stops = {
            "A": {"name": "Stop A", "lat": 24.900, "lon": 67.001},
            "B": {"name": "Stop B", "lat": 24.902, "lon": 67.004},
            "C": {"name": "Stop C", "lat": 24.904, "lon": 67.006},
            "D": {"name": "Stop D", "lat": 24.908, "lon": 67.009},
            "E": {"name": "Stop E", "lat": 24.911, "lon": 67.012},
            "F": {"name": "Stop F", "lat": 24.915, "lon": 67.015},
            "G": {"name": "Stop G", "lat": 24.918, "lon": 67.018},
            "H": {"name": "Stop H", "lat": 24.920, "lon": 67.020},
            "I": {"name": "Stop I", "lat": 24.922, "lon": 67.024},
            "J": {"name": "Stop J", "lat": 24.925, "lon": 67.027},
        }

        # 4 bus lines (each with 3–4 stops)
        self.lines = {
            "Green":  {"stops": ["A", "B", "C", "D"], "color": "green"},
            "Red":    {"stops": ["C", "E", "F"],        "color": "red"},
            "Blue":   {"stops": ["B", "G", "H"],        "color": "blue"},
            "Yellow": {"stops": ["D", "I", "J"],        "color": "yellow"},
        }

        # Physical roads (edges) with dummy distances
        self.road_segments = [
            ("A", "B", 0.4),
            ("B", "C", 0.4),
            ("C", "D", 0.5),
            ("C", "E", 0.6),
            ("E", "F", 0.5),
            ("B", "G", 0.7),
            ("G", "H", 0.6),
            ("D", "I", 0.7),
            ("I", "J", 0.6),
        ]
    def _build_graph(self):
        """
        Build the NetworkX graph from stops + roads
        """
        for stop_id, data in self.stops.items():
            self.graph.add_node(stop_id, **data)

        for s1, s2, dist in self.road_segments:
            self.graph.add_edge(s1, s2, weight=dist)
    # ============================================================
    # ==============  FR2.1.1 Input via Map Tap  =================
    # ============================================================
    
    def find_nearest_stop(self, lat, lon):
        """
        FR2.1.1:
        Input: (lat, lon) from a map tap.
        Output: nearest stop ID.
        """
        closest_stop = None
        min_distance = float("inf")

        for stop_id, data in self.stops.items():
            d = self._euclidean_distance(lat, lon, data["lat"], data["lon"])
            if d < min_distance:
                min_distance = d
                closest_stop = stop_id

        return closest_stop, min_distance

    

    def _euclidean_distance(self, lat1, lon1, lat2, lon2):
        """
        Simple Euclidean (dummy) since we're using fake coords.
        """
        return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)
    # ============================================================
    # ============  FR2.1.2 Input via Text Search  ===============
    # ============================================================

    def select_origin_destination(self, origin_query, destination_query):
        """
        FR2.1.2:
        Takes TWO text inputs:
            - origin_query
            - destination_query

        Returns a dictionary:
            {
                "origin_matches": [...],
                "destination_matches": [...],
                "origin_selected": stop_id or None,
                "destination_selected": stop_id or None
            }
        """

        # Search using the existing function
        origin_matches = self.search_stop(origin_query)
        destination_matches = self.search_stop(destination_query)

        # Determine selected stop if EXACTLY one match exists
        origin_selected = origin_matches[0] if len(origin_matches) == 1 else None
        destination_selected = destination_matches[0] if len(destination_matches) == 1 else None

        return {
            "origin_matches": origin_matches,
            "destination_matches": destination_matches,
            "origin_selected": origin_selected,
            "destination_selected": destination_selected
        }
       # raise NotImplementedError("FR2.1.1 not implemented yet")
        
        raise NotImplementedError("FR2.1.2 not implemented yet")


    # ============================================================
    # =============  FR2.1.3 Route Optimization  =================
    # ============================================================

    def get_shortest_distance_route(self, origin, destination):
        """
        FR2.1.3.a
        Return: route, total_distance
        """
        raise NotImplementedError("Shortest-distance routing not implemented yet")

    def get_fastest_route(self, origin, destination):
        """
        FR2.1.3.b
        Return: route, total_time
        """
        raise NotImplementedError("Fastest routing not implemented yet")

    def get_cheapest_route(self, origin, destination):
        """
        FR2.1.3.c
        Return: route, estimated_fare
        """
        raise NotImplementedError("Cheapest routing not implemented yet")

    def get_least_transfers_route(self, origin, destination):
        """
        FR2.1.3.d
        Return: route, num_transfers
        """
        raise NotImplementedError("Least-transfers routing not implemented yet")


    # ============================================================
    # =========  FR2.1.4 Step-by-Step Instructions  =============
    # ============================================================

    def generate_step_by_step_instructions(self, route):
        """
        FR2.1.4
        Convert a raw list of stops into human-friendly navigation steps.
        """
        raise NotImplementedError("Step-by-step instructions not implemented yet")


    # ============================================================
    # ========  FR2.1.5 Transfers & Walking Directions  ==========
    # ============================================================

    def calculate_walking_distance(self, lat1, lon1, lat2, lon2):
        """
        Helper function (used for FR2.1.5)
        """
        raise NotImplementedError("Walking distance calculation not implemented yet")

    def detect_transfers(self, route):
        """
        FR2.1.5
        Identify transfer points between lines.
        """
        raise NotImplementedError("Transfer detection not implemented yet")
