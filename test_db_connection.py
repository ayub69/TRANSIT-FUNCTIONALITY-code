print("🔥 THIS FILE IS RUNNING 🔥")

from transit_backend import TransitBackend

def main():
    backend = TransitBackend()  # fetch from DB and build graph

    # --- check that stops loaded ---
    print("Stops loaded (first 5):")
    for stop_id, data in list(backend.stops.items())[10:15]:
        print(stop_id, data)

    # --- check road segments ---
    print("\nRoad segments (first 5):")
    print(backend.road_segments[10:15])

    # --- check graph nodes and edges ---
    print("\nGraph info:")
    print("Number of nodes:", backend.graph.number_of_nodes())
    print("Number of edges:", backend.graph.number_of_edges())
    print("Some edges with weights (first 5):")
    for u, v, w in list(backend.graph.edges(data=True))[10:15]:
        print(u, v, w)

if __name__ == "__main__":
    main()
