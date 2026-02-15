from transit_backend import TransitBackend
b = TransitBackend()
# print("FEMALE fastest D->J:", b.get_fastest_route("D", "J", user_gender="female"))
# print("MALE fastest D->J:", b.get_fastest_route("D", "J", user_gender="male"))
# print("\nArrivals (Red @ E):")
# print(b.get_bus_arrival_predictions("Red", "E"))

# print("\nLive buses (Red):")
# print(b.get_simulated_bus_positions("Red"))

# print("\nArrivals (Pink @ D):")
# print(b.get_bus_arrival_predictions("Pink", "D"))

# print("\nLive buses (Pink):")
# print(b.get_simulated_bus_positions("Pink"))



# cli_8tests.py
from pprint import pprint

# Import the compute_trip controller and the backend instance from main.py
from main import compute_trip, backend


def make_map_payload(origin_stop_id: str, dest_stop_id: str, route_mode: str, gender: str):
    """
    Uses exact stop coordinates so nearest-stop snapping is deterministic.
    """
    o = backend.stops[origin_stop_id]
    d = backend.stops[dest_stop_id]

    return {
        "input_mode": "map",
        "origin": {"lat": o["lat"], "lon": o["lon"]},
        "destination": {"lat": d["lat"], "lon": d["lon"]},
        "route_mode": route_mode,
        "user": {"gender": gender}
    }


def run_one_test(gender: str, route_mode: str, origin_id: str = "D", dest_id: str = "J"):
    payload = make_map_payload(origin_id, dest_id, route_mode, gender)

    print("\n" + "=" * 70)
    print(f"TEST | gender={gender} | route_mode={route_mode} | {origin_id}->{dest_id}")
    print("=" * 70)
    print("Payload:")
    pprint(payload)

    try:
        result = compute_trip(payload)

        print("\nReturned Output:")
        pprint(result)

        # Quick visibility checks
        print("\n[Quick Checks]")
        print("estimated_fare_pkr:", result.get("estimated_fare_pkr"))
        print("route.path_ids:", result.get("route", {}).get("path_ids"))
        print("route.path_names:", result.get("route", {}).get("path_names"))
        print("origin.stop_name:", result.get("origin", {}).get("stop_name"))
        print("destination.stop_name:", result.get("destination", {}).get("stop_name"))

    except Exception as e:
        print("\nReturned ERROR:")
        print(type(e).__name__, "-", str(e))


def main():
    route_modes = ["shortest", "fastest", "least_transfers"]
    genders = ["female", "male"]

    # 8 tests total:
    for gender in genders:
        for mode in route_modes:
            run_one_test(gender, mode, origin_id="1", dest_id="16")


if __name__ == "__main__":
    main()
