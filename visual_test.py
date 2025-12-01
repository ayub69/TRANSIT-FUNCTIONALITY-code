from transit_backend import TransitBackend
import time

backend = TransitBackend()


# ============================================================
#  Display all stops
# ============================================================
def print_stops():
    print("\n=== ALL STOPS IN NETWORK ===")
    for stop_id, data in backend.stops.items():
        print(f"{stop_id}: {data['name']}  (lat={data['lat']}, lon={data['lon']})")


# ============================================================
#  FR2.1.1 — Nearest Stop from Coordinates (Map Tap simulation)
# ============================================================
def test_nearest_stop():
    print("\n=== Test FR2.1.1: Nearest Stop ===")
    lat = float(input("Enter latitude (dummy): "))
    lon = float(input("Enter longitude (dummy): "))

    stop, dist = backend.find_nearest_stop(lat, lon)

    print("\n📍 Tap Coordinates:", (lat, lon))
    print("➡️ Nearest Stop:", stop)
    print(f"🧭 Distance (Euclidean dummy): {dist:.6f}")


# ============================================================
#  FR2.1.2 — Text Search (single query)
# ============================================================
def test_text_search_simple():
    print("\n=== Test FR2.1.2 (Simple Text Search) ===")
    query = input("Enter search text: ")

    results = backend.search_stop(query)

    print("\n🔎 You searched for:", query)
    print("➡️ Matches:", results if results else "No matches found")


# ============================================================
#  FR2.1.2 — Origin + Destination Text Input
# ============================================================
def test_text_origin_destination():
    print("\n=== Test FR2.1.2: Origin + Destination ===")

    origin_query = input("Enter ORIGIN text: ")
    dest_query   = input("Enter DESTINATION text: ")

    result = backend.select_origin_destination(origin_query, dest_query)

    print("\n=== ORIGIN RESULTS ===")
    print("Matches:", result["origin_matches"])
    print("Selected Origin:", result["origin_selected"])

    print("\n=== DESTINATION RESULTS ===")
    print("Matches:", result["destination_matches"])
    print("Selected Destination:", result["destination_selected"])


# ============================================================
#  MENU LOOP
# ============================================================
def main_menu():
    while True:
        print("\n===========================")
        print("     TRANSIT TEST MENU     ")
        print("===========================")
        print("1. Show all stops")
        print("2. Test FR2.1.1 — Nearest Stop")
        print("3. Test FR2.1.2 — Simple Text Search")
        print("4. Test FR2.1.2 — Origin + Destination Input")
        print("0. Exit")
        print("===========================")

        choice = input("Select an option: ")

        if choice == "1":
            print_stops()
        elif choice == "2":
            test_nearest_stop()
        elif choice == "3":
            test_text_search_simple()
        elif choice == "4":
            test_text_origin_destination()
        elif choice == "0":
            print("\nExiting tester...")
            time.sleep(0.5)
            break
        else:
            print("Invalid input. Try again.")


if __name__ == "__main__":
    main_menu()
