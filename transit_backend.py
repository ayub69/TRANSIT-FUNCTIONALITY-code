import networkx as nx
import math
import datetime
from typing import List, Dict, Any, Optional
import requests
from osrm import osrm_road_distance, osrm_steps , osrm_duration_min#new 
# import your DB helper functions:
from db_connect import fetch_all_stops, fetch_all_routes, fetch_transfer_stops

class TransitBackend:
    """
    Main backend that will satisfy all routing-related Functional Requirements (FR2.1.x).    """

    def __init__(self,google_api_key=None):
        # =============================
        # DATA STRUCTURES dummy 
        # =============================
        
        # Dictionary of stops: {stop_id: {"name": ..., "lat": ..., "lon": ...}}
        self.google_api_key = "AIzaSyAwk8mVtSZoWJje_RiC8B9GaBJARZo6ODo"
        self.stops = {}

        # Dictionary of bus lines: {line_name: {"stops": [...], "color": "..."}}
        self.lines = {}

        # Road connections between stops with distances: [(stopA, stopB, distance_km), ...]
        self.road_segments = []

        # NetworkX graph for routing:
        self.graph = nx.Graph()
        # self._build_dummy_data()
        # self._build_graph()

        self.stops = {}
        stops_data = fetch_all_stops()
        print("DEBUG: stops_data =", stops_data[:5])  # check stops
        for stop in stops_data:
            self.stops[int(stop["stop_id"])] = {
                "name": stop["stop_name"],
                "lat": stop["latitude"],
                "lon": stop["longitude"]
            }

        #old code:
        # self.lines = {} #edittt this code (16 jan)
        # routes_data = fetch_all_routes()
        # for route in routes_data:
        #     route_id = route["route_id"]
        #     transfer_stops = fetch_transfer_stops(route_id)
        #     self.lines[route_id] = [int(ts["stop_id"]) for ts in transfer_stops]
            
        #new code:
        self.lines = {}
        # map route_type -> color
        COLOR_MAP = {
            "Green": "green",
            "Red": "red",
            "EV": "white",
            "Pink": "pink"
        }

        routes_data = fetch_all_routes()

        for route in routes_data:
            line_name = route["route_type"]  # e.g. "Red", "Green"
            route_id = route["route_id"]

            # initialize line if not already present
            if line_name not in self.lines:
                self.lines[line_name] = {
                    "stops": [],
                    "color": COLOR_MAP.get(line_name, "black")
                }

            transfer_stops = fetch_transfer_stops(route_id)

            # append ordered stop names
            for ts in transfer_stops:
                self.lines[line_name]["stops"].append(int(ts["stop_id"]))

        print("DEBUG: self.lines =", self.lines)

        #old code:
        # self.road_segments = []
        # for stops_list in self.lines.values():
        #     for i in range(len(stops_list)-1):
        #         self.road_segments.append((stops_list[i], stops_list[i+1]))

        #new code:
        for route in routes_data:
            route_id = route["route_id"]
            transfer_stops = fetch_transfer_stops(route_id)

            stop_ids = [int(ts["stop_id"]) for ts in transfer_stops]

            for i in range(len(stop_ids) - 1):
                self.road_segments.append((stop_ids[i], stop_ids[i + 1]))

        #print("DEBUG: self.road_segments =", self.road_segments[:5])

        #print("DEBUG: building graph...")
        #self._build_graph()
        #print("DEBUG: graph built!")

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

        # 10 stops with REAL Karachi coordinates
        self.stops = {
            "A": {"name": "Numaish Chowrangi",        "lat": 24.8759, "lon": 67.0397},
            "B": {"name": "MAJ Road Mobile Market",   "lat": 24.8786, "lon": 67.0361},
            "C": {"name": "Guru Mandir",              "lat": 24.8808, "lon": 67.0304},
            "D": {"name": "Jail Chowrangi",            "lat": 24.8850, "lon": 67.0245},
            "E": {"name": "PIB Colony",                "lat": 24.8891, "lon": 67.0189},
            "F": {"name": "NIPA Chowrangi",             "lat": 24.8906, "lon": 67.0216},
            "G": {"name": "Johar Mor",                 "lat": 24.8974, "lon": 67.0866},
            "H": {"name": "Gulshan Chowrangi",         "lat": 24.9200, "lon": 67.0910},
            "I": {"name": "Safoora Chowrangi",          "lat": 24.9456, "lon": 67.1234},
            "J": {"name": "Malir Halt",                "lat": 24.9435, "lon": 67.1917},
        }

        # 4 bus lines (structure unchanged)
        self.lines = {
            "Green":  {"stops": ["A", "B", "C", "D"], "color": "green"},
            "Red":    {"stops": ["C", "E", "F"],      "color": "red"},
            "Blue":   {"stops": ["B", "G", "H"],      "color": "blue"},
            "Yellow": {"stops": ["D", "I", "J"],      "color": "yellow"},
        }

        # Physical roads (edges) with REALISTIC Karachi distances (KM)
        self.road_segments = [
            ("A", "B"),   # Numaish → MAJ Road
            ("B", "C"),   # MAJ Road → Guru Mandir
            ("C", "D"),   # Guru Mandir → Jail Chowrangi
            ("C", "E"),   # Guru Mandir → PIB Colony
            ("E", "F"),   # PIB Colony → NIPA
            ("B", "G"),   # MAJ Road → Johar Moro
            ("G", "H"),   # Johar Mor → Gulshan Chowrangi
            ("D", "I"),   # Jail Chowrangi → Safoora
            ("I", "J"),   # Safoora → Malir Halt
        ]
    
    def _build_graph(self):
        for stop_id, data in self.stops.items():
            self.graph.add_node(stop_id, **data)

        for s1, s2 in self.road_segments:
            lat1, lon1 = self.stops[s1]["lat"], self.stops[s1]["lon"]
            lat2, lon2 = self.stops[s2]["lat"], self.stops[s2]["lon"]

            
            dist_km = self._road_distance(lat1, lon1, lat2, lon2, profile="driving")

            self.graph.add_edge(s1, s2, weight=dist_km)
    
    # ============================================================
    # ==============  FR2.1.1 Input via Map Tap  =================
    # ============================================================
    
    def find_nearest_stop(self, lat, lon):
        
        """
        Fast nearest stop:
        - Use haversine (no API calls) to find the closest stop.
        """
        closest_stop = None
        min_distance = float("inf")

        for stop_id, data in self.stops.items():
            d = self.haversine(lat, lon, data["lat"], data["lon"])  # <-- NO OSRM here
            if d < min_distance:
                min_distance = d
                closest_stop = stop_id

        return closest_stop, min_distance

    

    def _euclidean_distance(self, lat1, lon1, lat2, lon2):
        """
        Simple Euclidean (dummy) since we're using fake coords.
        """
        return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)
    
    def haversine(self,lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (
            math.sin(dlat/2)**2 +
            math.cos(math.radians(lat1)) *
            math.cos(math.radians(lat2)) *
            math.sin(dlon/2)**2
        )
        return 2 * R * math.asin(math.sqrt(a))
        
    # ============================================================
    # ============  FR2.1.2 Input via Text Search  ===============
    # ============================================================

    def search_stop(self, query):
        
        """
        Case-insensitive substring search.
        Works even if stop_id is int.
        """
        query = str(query).lower().strip()

        results = []
        for stop_id, data in self.stops.items():
            stop_id_str = str(stop_id).lower()
            stop_name = str(data.get("name", "")).lower()

            if query in stop_id_str or query in stop_name:
                results.append(stop_id)

        return results
    

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
        
       # raise NotImplementedError("FR2.1.2 not implemented yet")


    # ============================================================
    # =============  FR2.1.3 Route Optimization  =================
    # ============================================================
    
    """ def _road_distance(self, lat1, lon1, lat2, lon2):
        
    # Uses OpenRouteService to compute walking distance on real roads.
       # Returns distance in KM.
        
        url = "https://api.openrouteservice.org/v2/directions/foot-walking"

        headers = {
            "Authorization": self.ors_api_key,
            "Content-Type": "application/json"
        }

        body = {
            "coordinates": [
                [lon1, lat1],
                [lon2, lat2]
            ]
        }

        try:
            r = requests.post(url, json=body, headers=headers, timeout=10).json()
            meters = r["features"][0]["properties"]["segments"][0]["distance"]
            return meters / 1000.0

        except Exception as e:
            print("ORS failed:", e)
            return None """
    #fo real road distance or else it can switch to eucladian if not working
    
    def _road_distance(self, lat1, lon1, lat2, lon2, profile="driving"):
        """
    Uses OSRM first, falls back to haversine.
    profile: driving | walking
    """
        d = osrm_road_distance(lat1, lon1, lat2, lon2, profile=profile)

        if d is None:
            return self.haversine(lat1, lon1, lat2, lon2)
        return d
        
    def get_shortest_distance_route(self, origin, destination):
        if origin not in self.stops:
            raise ValueError(f"Invalid origin stop ID: {origin}")
        if destination not in self.stops:
            raise ValueError(f"Invalid destination stop ID: {destination}")

        path = nx.dijkstra_path(self.graph, origin, destination, weight="weight")
        total_distance = nx.dijkstra_path_length(
            self.graph, origin, destination, weight="weight"
        )

        return {
            "path": path,
            "total_distance": round(total_distance, 3)
        }    
    
    def get_fastest_route(self, origin, destination):
        if origin not in self.stops or destination not in self.stops:
            raise ValueError("Invalid stop ID.")

        base = self.get_shortest_distance_route(origin, destination)
        path = base["path"]

        total_time = 0.0
        total_dist = 0.0

        for i in range(len(path) - 1):
            a, b = path[i], path[i+1]
            lat1, lon1 = self.stops[a]["lat"], self.stops[a]["lon"]
            lat2, lon2 = self.stops[b]["lat"], self.stops[b]["lon"]

            seg_time = osrm_duration_min(lat1, lon1, lat2, lon2, profile="driving")
            seg_dist = self._road_distance(lat1, lon1, lat2, lon2, profile="driving")

            if seg_time is None:
                seg_time = (seg_dist / 25.0) * 60.0  # fallback

            total_time += seg_time
            total_dist += seg_dist

        return {
            "path": path,
            "total_time_min": round(total_time, 1),
            "distance_km": round(total_dist, 3)
        }

        raise NotImplementedError("Fastest routing not implemented yet")

    def get_cheapest_route(self, origin, destination):
        """
        FR2.1.3.c
        Return: route, estimated_fare
        """
        # Validate
        if origin not in self.stops or destination not in self.stops:
            raise ValueError("Invalid stop ID.")

        # Fare model (dummy for demo)
        BASE_FARE = 20
        PER_KM = 5
        TRANSFER_FARE = 10

        # Use shortest-distance route
        result = self.get_shortest_distance_route(origin, destination)
        path = result["path"]
        dist = result["total_distance"]

        transfers = self._count_line_changes(path)

        fare = BASE_FARE + (dist * PER_KM) + (transfers * TRANSFER_FARE)

        return {
            "path": path,
            "estimated_fare": round(fare, 2),
            "transfers": transfers,
            "distance_km": dist
        }
        raise NotImplementedError("Cheapest routing not implemented yet")
    #helper for 2.1.3d 
    # def _stop_to_lines_map(self):
    #     """
    #     Returns a dictionary mapping stop_id → list of line names.
    #     Example: {'B': ['Green', 'Blue'], ...}
    #     """
    #     mapping = {s: [] for s in self.stops.keys()}

    #     for line_name, line_data in self.lines.items():
    #         for stop in line_data["stops"]:
    #             mapping[stop].append(line_name)

    #     return mapping
    def _stop_to_lines_map(self):
        stop_to_lines = {}
        for line_name, line_data in self.lines.items():
            for stop_id in line_data.get("stops", []):
                stop_to_lines.setdefault(stop_id, []).append(line_name)
        return stop_to_lines


    def get_least_transfers_route(self, origin, destination):
        """
        FR2.1.3.d
        Compute the route with the minimum number of bus line transfers.

        Strategy:
        - Assign heavy penalties when switching between lines.
        - Run Dijkstra on the modified weighted graph.
        - Count number of line changes in the resulting path.
        """

        if origin not in self.stops or destination not in self.stops:
            raise ValueError("Invalid stop ID.")

        # Map stop -> lines (e.g., A: ['Green'], B: ['Green','Blue'])
        line_map = self._stop_to_lines_map()

        # Build a temporary weighted graph where line changes cost extra
        G = nx.Graph()

        TRANSFER_PENALTY = 100  # large penalty to avoid switching lines

        # Add nodes
        for stop_id, data in self.stops.items():
            G.add_node(stop_id)

        # Add modified edges
        for (s1, s2) in self.road_segments:
            lat1, lon1 = self.stops[s1]["lat"], self.stops[s1]["lon"]
            lat2, lon2 = self.stops[s2]["lat"], self.stops[s2]["lon"]

            dist = self._road_distance(lat1, lon1, lat2, lon2, profile="driving")

            lines_s1 = set(line_map[s1])
            lines_s2 = set(line_map[s2])

            penalty = 0 if (lines_s1 & lines_s2) else TRANSFER_PENALTY
            G.add_edge(s1, s2, weight=dist + penalty)


        # Shortest path on modified graph
        path = nx.dijkstra_path(G, origin, destination, weight="weight")

        # Count actual transfers (line changes)
        num_transfers = self._count_line_changes(path)

        return {
            "path": path,
            "num_transfers": num_transfers
        }
    #helper2 for 2.1.3d
    def _count_line_changes(self, path):
        """
        Given a path (list of stops), return number of line changes.
        """

        line_map = self._stop_to_lines_map()
        current_line = None
        transfers = 0

        # Iterate through stop pairs
        for i in range(len(path) - 1):
            stop_a = path[i]
            stop_b = path[i + 1]

            # lines serving the two stops
            common = set(line_map[stop_a]) & set(line_map[stop_b])

            if not common:
                # no common line, must transfer
                transfers += 1
            else:
                # pick the first common line
                new_line = list(common)[0]
                if current_line is None:
                    current_line = new_line
                elif new_line != current_line:
                    transfers += 1
                    current_line = new_line

        return transfers

    # ============================================================
    # =========  FR2.1.4 Step-by-Step Instructions  =============
    # ============================================================

    def generate_step_by_step_instructions(self, route):
        """
        route = [1, 2, 3, 5, 6]   # stop_ids

        Output:
        [
            "Start at Khokrapar",
            "Take Red Line from Khokrapar to Saudabad",
            "Continue on Red Line to RCD Ground",
            "Transfer to Green Line at RCD Ground",
            "Continue on Green Line to Malir Halt",
            "Arrive at Malir Halt"
        ]
        """

        if not route or len(route) < 2:
            return ["Invalid route"]

        # Map stop_id → stop_name
        stop_name = lambda sid: self.stops[sid]["name"]

        steps = []
        steps.append(f"Start at {stop_name(route[0])}")

        line_map = self._stop_to_lines_map()
        current_line = None

        # Loop over each segment
        for i in range(len(route) - 1):
            a, b = route[i], route[i + 1]

            # Lines common between consecutive stops
            common_lines = set(line_map.get(a, [])) & set(line_map.get(b, []))

            line = list(common_lines)[0] if common_lines else "UNKNOWN"

            # First segment
            if current_line is None:
                current_line = line
                steps.append(
                    f"Take {line} Line from {stop_name(a)} to {stop_name(b)}"
                )
            else:
                # Line change → transfer
                if line != current_line:
                    steps.append(
                        f"Transfer to {line} Line at {stop_name(a)}"
                    )
                    current_line = line

                steps.append(
                    f"Continue on {line} Line to {stop_name(b)}"
                )

        steps.append(f"Arrive at {stop_name(route[-1])}")
        return steps

        raise NotImplementedError("Step-by-step instructions not implemented yet")


    # ============================================================
    # ========  FR2.1.5 Transfers & Walking Directions  ==========
    # ============================================================

    def calculate_walking_distance(self, lat1, lon1, lat2, lon2):
       
        d_km = self._road_distance(lat1, lon1, lat2, lon2, profile="walking")

        meters = d_km * 1000
        WALK_SPEED_KMPH = 4.5
        time_min = (d_km / WALK_SPEED_KMPH) * 60
       
        return {
            "distance_km": round(d_km, 3),
            "distance_m": round(meters, 1),
            "time_min": round(time_min, 1)
        }
        raise NotImplementedError("Walking distance calculation not implemented yet")


    def detect_transfers(self, route):
        """
        Returns list of stops where a line change occurs.
        Example:
        route = ["A","B","C","E","F"]
        output = ["C"]  (transfer point)
        """

        if not route or len(route) < 2:
            return []

        line_map = self._stop_to_lines_map()
        transfer_points = []

        current_line = None

        for i in range(len(route)-1):
            a = route[i]
            b = route[i+1]

            common = set(line_map[a]) & set(line_map[b])
            if not common:
                continue

            new_line = list(common)[0]

            if current_line is None:
                current_line = new_line
            elif new_line != current_line:
                transfer_points.append(a)
                current_line = new_line

        return transfer_points


  # =====================================================================
    # 2.2 STATIC INFORMATION (ESTIMATES)
    # =====================================================================

    # -------------------------------
    # FR2.2.1: Bus Arrival Predictions
    # -------------------------------
    def get_bus_arrival_predictions(self, line_name: str, stop_id: str,
                                    current_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        """
        FR2.2.1
        Provide estimated arrival times based on static timetable + average travel durations.

        Returns a list like:
        [
            {"arrival_time": "12:15", "status": "on_time"},
            {"arrival_time": "12:30", "status": "on_time"},
            ...
        ]
        """
        raise NotImplementedError("FR2.2.1 bus arrival predictions not implemented yet")

    # -------------------------------
    # FR2.2.2: Live Bus Tracking (simulated)
    # -------------------------------
    def get_simulated_bus_positions(self, line_name: str,
                                    current_time: Optional[datetime.time] = None) -> List[Dict[str, Any]]:
        """
        FR2.2.2
        Display simulated/estimated bus positions along a route using timetable progression.

        Returns:
        [
            {"bus_id": "Green-1", "current_stop": "B", "progress_between": ("B", "C"), "eta_next_stop_min": 3},
            ...
        ]
        """
        raise NotImplementedError("FR2.2.2 simulated bus positions not implemented yet")

    # -------------------------------
    # FR2.2.3: Service Alerts & Delay Notifications
    # -------------------------------
    def add_service_alert(self, line_name: str, message: str) -> None:
        """
        FR2.2.3
        Manually add a service alert (admin use).
        """
        self.service_alerts.append({
            "line": line_name,
            "message": message,
            "timestamp": datetime.datetime.now()
        })

    def get_service_alerts(self) -> List[Dict[str, Any]]:
        """
        FR2.2.3
        Return all current service alerts.
        """
        return self.service_alerts

    # -------------------------------
    # FR2.2.4: User-Reported Delays
    # -------------------------------
    def report_delay(self, line_name: str, stop_id: str, comment: str) -> None:
        """
        FR2.2.4
        Allow users to report delays/issues for specific routes.
        """
        self.user_reports.append({
            "line": line_name,
            "stop": stop_id,
            "comment": comment,
            "timestamp": datetime.datetime.now()
        })

    def get_user_reports(self) -> List[Dict[str, Any]]:
        """Return list of user-reported delays/issues."""
        return self.user_reports

    # =====================================================================
    # 2.3 FARE AND SCHEDULE INFORMATION
    # =====================================================================

    # -------------------------------
    # FR2.3.1: Fare Calculation
    # -------------------------------
    def calculate_fare(self, path: List[str]) -> float:
        """
        FR2.3.1
        Calculate fare between two points, using defined pricing structure.

        For example: base fare + per-km + per-transfer.
        """
        raise NotImplementedError("FR2.3.1 fare calculation not implemented yet")

    # -------------------------------
    # FR2.3.2: Travel Time Estimation
    # -------------------------------
    def estimate_total_travel_time(self, path: List[str], num_transfers: int,
                                   walking_segments: List[Dict[str, Any]]) -> float:
        """
        FR2.3.2
        Estimate total travel time including:
        - in-vehicle time (dist / speed)
        - waiting time (based on schedule)
        - walking time
        - transfer penalties

        Returns time in minutes.
        """
        raise NotImplementedError("FR2.3.2 travel time estimation not implemented yet")

    # -------------------------------
    # FR2.3.3: Bus Schedule Display
    # -------------------------------
    def get_route_schedule(self, line_name: str) -> Dict[str, Any]:
        """
        FR2.3.3
        Display complete schedule for a bus route.

        Return example:
        {
            "line": "Green",
            "first_departure": "06:00",
            "last_departure": "22:00",
            "frequency_min": 10,
            "stops": ["A","B","C","D"]
        }
        """
        raise NotImplementedError("FR2.3.3 bus schedule display not implemented yet")

    # -------------------------------
    # FR2.3.4: Operating Hours Information
    # -------------------------------
    def get_operating_hours(self, line_name: str) -> Dict[str, str]:
        """
        FR2.3.4
        Display operating hours for each bus line.

        Return example:
        {
            "line": "Green",
            "first_bus": "06:00",
            "last_bus": "22:00"
        }
        """
        raise NotImplementedError("FR2.3.4 operating hours not implemented yet")

    # =====================================================================
    # 2.4 MAP INTEGRATION
    # =====================================================================

    # -------------------------------
    # FR2.4.1: Interactive Karachi Map with BRT Routes
    # (Backend side: provide map geometry & route shapes)
    # -------------------------------
    def get_map_routes_geometry(self) -> Dict[str, Any]:
        """
        FR2.4.1
        Return all BRT routes with color codes and paths, for frontend mapping.

        Example:
        {
            "Green": {"color": "green", "polyline": [...]},
            "Red":   {"color": "red", "polyline": [...]},
            ...
        }
        """
        raise NotImplementedError("FR2.4.1 map geometry not implemented yet")

    # -------------------------------
    # FR2.4.2: Bus Stop Locations and Details
    # -------------------------------
    def get_all_stop_markers(self) -> List[Dict[str, Any]]:
        """
        FR2.4.2
        Return all bus stop markers for map display.

        Example:
        [
            {"id": "A", "name": "Stop A", "lat": ..., "lon": ..., "routes": [...], "services": [...]},
            ...
        ]
        """
        raise NotImplementedError("FR2.4.2 bus stop locations not implemented yet")

    def get_stop_details(self, stop_id: str) -> Dict[str, Any]:
        """
        FR2.4.2 (on tap)
        Return details for a single stop.
        """
        raise NotImplementedError("FR2.4.2 single stop details not implemented yet")

    # -------------------------------
    # FR2.4.3: User Current Location Detection
    # (Backend: accepts coordinates, finds nearest stops)
    # -------------------------------
    def find_nearest_stops_to_location(self, lat: float, lon: float,
                                       max_results: int = 3) -> List[Dict[str, Any]]:
        """
        FR2.4.3
        Use detected location to find nearest stops.

        Returns a sorted list of dicts:
        [
            {"stop_id": "A", "distance": 0.23},
            {"stop_id": "B", "distance": 0.45},
            ...
        ]
        """
        raise NotImplementedError("FR2.4.3 nearest stops from GPS not implemented yet")

    # -------------------------------
    # FR2.4.4: Navigation To/From Bus Stops
    # -------------------------------
    def get_walking_route_user_to_stop(self, user_lat: float, user_lon: float,
                                       stop_id: str) -> Dict[str, Any]:
        """
        FR2.4.4
        Turn-by-turn walking directions from user to a stop.
        (Can be simulated / static for demo.)
        """
        raise NotImplementedError("FR2.4.4 walking route not implemented yet")

    def get_walking_route_stop_to_user(self, stop_id: str,
                                       user_lat: float, user_lon: float) -> Dict[str, Any]:
        """
        FR2.4.4 (reverse)
        """
        raise NotImplementedError("FR2.4.4 reverse walking route not implemented yet")

    # =====================================================================
    # 2.5 MULTI-LANGUAGE AND ACCESSIBILITY
    # =====================================================================

    # -------------------------------
    # FR2.5.1 & FR2.5.2: Urdu + English Interfaces
    # (Backend: language selection + label packs)
    # -------------------------------
    def set_language(self, lang_code: str) -> None:
        """
        FR2.5.1 & FR2.5.2
        Set the active language code ('en' or 'ur').
        """
        raise NotImplementedError("FR2.5.x language switching not implemented yet")

    def get_text_labels(self, lang_code: Optional[str] = None) -> Dict[str, str]:
        """
        Return UI text labels in the requested language.
        """
        raise NotImplementedError("FR2.5.x language labels not implemented yet")

    # -------------------------------
    # FR2.5.3: Icon-Based Navigation
    # (Backend: supply icon metadata)
    # -------------------------------
    def get_icon_metadata(self) -> Dict[str, Any]:
        """
        FR2.5.3
        Provide config for icons (bus, stop, walking, alert, etc.).
        """
        raise NotImplementedError("FR2.5.3 icon metadata not implemented yet")

    # -------------------------------
    # FR2.5.4: Voice-Assisted Interface
    # (May be simulated as command parsing)
    # -------------------------------
    def process_voice_command(self, transcript: str) -> Dict[str, Any]:
        """
        FR2.5.4
        Basic voice commands such as:
            "find nearest bus stop"
            "show route to city center"
        For demo, we accept a text transcript and return an action.
        """
        raise NotImplementedError("FR2.5.4 voice commands not implemented yet")

    # -------------------------------
    # FR2.5.5: Text-to-Speech for Instructions
    # -------------------------------
    def get_tts_payload_for_instructions(self, steps: List[str],
                                         lang_code: str = "en") -> str:
        """
        FR2.5.5
        Return a concatenated text string that could be sent to a TTS engine.
        """
        raise NotImplementedError("FR2.5.5 TTS payload not implemented yet")

    # =====================================================================
    # 2.6 USER FEEDBACK AND REPORTING
    # =====================================================================

    # -------------------------------
    # FR2.6.1: Anonymous In-App Feedback
    # -------------------------------
    def submit_feedback(self, route_name: str, rating: int,
                        comments: str) -> None:
        """
        FR2.6.1
        Store anonymous feedback entries.
        """
        self.feedback.append({
            "route_name": route_name,
            "rating": rating,
            "comments": comments,
            "timestamp": datetime.datetime.now()
        })

    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """Return all feedback entries (for admin)."""
        return self.feedback

    # -------------------------------
    # FR2.6.2: Report Service Issues Without Account
    # -------------------------------
    def report_service_issue(self, description: str,
                             route_name: Optional[str] = None) -> None:
        """
        FR2.6.2
        Allow users to report issues (missing stops, signage problems, etc.)
        without logging in.
        """
        self.user_reports.append({
            "route": route_name,
            "description": description,
            "timestamp": datetime.datetime.now()
        })

    # =====================================================================
    # 2.7 USER ACCESS CONTROL
    # =====================================================================

    # -------------------------------
    # FR2.7.1: User-Level Access
    # (Backend side: most features available without login)
    # -------------------------------
    def is_user_action_allowed(self, action_name: str, is_admin: bool) -> bool:
        """
        FR2.7.1 & FR2.7.2
        For demo: simple rule-based permission checking.

        Example:
            - general users can 'search_route', 'view_fare', 'submit_feedback'
            - admin users needed for 'update_routes', 'add_alert', etc.
        """
        raise NotImplementedError("FR2.7 access control not implemented yet")

    # -------------------------------
    # FR2.7.2: Admin-Level Access
    # -------------------------------
    def register_admin(self, username: str, password: str) -> None:
        """
        Demo-only: add an admin account.
        """
        self.admin_accounts[username] = password  # DO NOT use in production

    def admin_login(self, username: str, password: str) -> bool:
        """
        Check admin credentials (DEMO ONLY).
        """
        stored = self.admin_accounts.get(username)
        return stored is not None and stored == password
    

    # # Fetch all stops from DB
    #     self.stops = {}  # key: stop_id, value: dict with name, lat, lon
    #     stops_data = fetch_all_stops()
    #     for stop in stops_data:
    #         self.stops[stop["stop_id"]] = {
    #             "name": stop["stop_name"],
    #             "lat": stop["latitude"],
    #             "lon": stop["longitude"]
    #         }

    #     # Fetch all routes from DB
    #     self.lines = {}  # key: route_id, value: list of stop_ids in order
    #     routes_data = fetch_all_routes()
    #     for route in routes_data:
    #         route_id = route["route_id"]
    #         # fetch ordered transfer stops for this route
    #         transfer_stops = fetch_transfer_stops(route_id)
    #         self.lines[route_id] = [ts["stop_id"] for ts in transfer_stops]

    #     self._build_graph()


    # def _build_graph(self):
    #     # Add all stops as nodes
    #     for stop_id, data in self.stops.items():
    #         self.graph.add_node(stop_id, **data)

    #     # Add edges along routes
    #     for route_stops in self.lines.values():
    #         for i in range(len(route_stops) - 1):
    #             s1, s2 = route_stops[i], route_stops[i + 1]
    #             lat1, lon1 = self.stops[s1]["lat"], self.stops[s1]["lon"]
    #             lat2, lon2 = self.stops[s2]["lat"], self.stops[s2]["lon"]

    #             dist_km = self._road_distance(lat1, lon1, lat2, lon2, profile="driving")
    #             self.graph.add_edge(s1, s2, weight=dist_km)