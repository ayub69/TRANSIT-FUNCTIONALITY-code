from transit_backend import TransitBackend
import time

backend = TransitBackend()


# ============================================================
#  Print all stops in the network
# ============================================================
def print_stops():
    print("\n=== ALL STOPS IN NETWORK (10 dummy stops) ===")
    for stop_id, data in backend.stops.items():
        print(f"{stop_id}: {data['name']}   (lat={data['lat']}, lon={data['lon']})")


# ============================================================
#  FR2.1.1 — Nearest Stop from Map Tap (simulated)
# ============================================================
def test_nearest_stop():
    print("\n=== FR2.1.1 — Nearest Stop to Tap ===")
    print("This simulates a user tapping on a map using dummy latitude/longitude.\n")

    lat = float(input("Enter tap latitude  (dummy): "))
    lon = float(input("Enter tap longitude (dummy): "))

    stop, dist = backend.find_nearest_stop(lat, lon)

    print("\n📍 Tap location:", (lat, lon))
    print("➡️ Nearest Stop:", stop)
    print(f"🧭 Distance (Euclidean dummy units): {dist:.6f}")


# ============================================================
#  FR2.1.2 — Single Text Search (searching any stop)
# ============================================================
def test_text_search_simple():
    print("\n=== FR2.1.2 — Simple Text Search ===")
    print("Type part of a stop name or stop ID (e.g., 'A', 'sto', 'Stop B')")

    query = input("Search query: ")

    results = backend.search_stop(query)

    print("\n🔎 You searched for:", query)
    print("➡️ Matching Stops:", results if results else "❌ No matches found")


# ============================================================
#  FR2.1.2 — Origin + Destination resolution via text search
# ============================================================
def test_text_origin_destination():
    print("\n=== FR2.1.2 — Origin + Destination Selection ===")
    print("Enter text for BOTH origin and destination.\n"
          "Backend will search, match, and select if exactly 1 match exists.\n")

    origin_query = input("Enter ORIGIN text: ")
    dest_query   = input("Enter DESTINATION text: ")

    result = backend.select_origin_destination(origin_query, dest_query)

    print("\n=== ORIGIN ===")
    print("Matches:", result["origin_matches"])
    print("Selected Origin:", result["origin_selected"])

    print("\n=== DESTINATION ===")
    print("Matches:", result["destination_matches"])
    print("Selected Destination:", result["destination_selected"])

    if result["origin_selected"] is None or result["destination_selected"] is None:
        print("\n⚠️ Routing not possible until both queries match exactly ONE stop.")
    else:
        print("\n✔ Both origin and destination successfully resolved!")


# ============================================================
#  FR2.1.3.a — Shortest Distance Route (Dijkstra)
# ============================================================
def test_shortest_route():
    print("\n=== FR2.1.3.a — Shortest Distance Route ===")
    print("Enter valid stop IDs (A–J). Example: A → F\n")

    origin = input("Enter ORIGIN stop ID: ").strip().upper()
    dest   = input("Enter DESTINATION stop ID: ").strip().upper()

    try:
        result = backend.get_shortest_distance_route(origin, dest)
    except Exception as e:
        print("\n❌ Error:", e)
        return

    print("\n✔ Shortest route found!")
    print("➡️ Path:", " -> ".join(result["path"]))
    print(f"➡️ Total Distance: {result['total_distance']:.3f} (dummy units)")

def test_least_transfers_route():
    print("\n=== FR2.1.3.d — Least Transfers Route ===")
    
    origin = input("Enter ORIGIN stop ID: ").strip().upper()
    dest   = input("Enter DESTINATION stop ID: ").strip().upper()

    try:
        result = backend.get_least_transfers_route(origin, dest)
    except Exception as e:
        print("\n❌ Error:", e)
        return

    print("\n✔ Least-transfers route found!")
    print("➡️ Path:", " -> ".join(result["path"]))
    print("➡️ Transfers:", result["num_transfers"])

# ============================================================
#  MAIN MENU
# ============================================================
def main_menu():
    while True:
        print("\n===================================")
        print("    TRANSIT BACKEND TEST MENU")
        print("===================================")
        print("1. Show all stops (data inspection)")
        print("2. Test FR2.1.1 — Nearest Stop (Map Tap Simulation)")
        print("3. Test FR2.1.2 — Simple Stop Text Search")
        print("4. Test FR2.1.2 — Origin + Destination Text Input")
        print("5. Test FR2.1.3.a — Shortest Distance Route")
        print("6. Test FR2.1.3.d -- least bus changes")
        print("0. Exit")
        print("===================================")

        choice = input("Choose an option: ")

        if choice == "1":
            print_stops()
        elif choice == "2":
            test_nearest_stop()
        elif choice == "3":
            test_text_search_simple()
        elif choice == "4":
            test_text_origin_destination()
        elif choice == "5":
            test_shortest_route()
        elif choice == "6":
            test_least_transfers_route()
        elif choice == "0":
            print("\nExiting tester...")
            time.sleep(0.4)
            break
        else:
            print("Invalid choice. Try again.\n")


if __name__ == "__main__":
    main_menu()
