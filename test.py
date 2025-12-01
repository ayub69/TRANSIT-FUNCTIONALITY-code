from transit_backend import TransitBackend

backend = TransitBackend()

print("Nearest:", backend.find_nearest_stop(24.903, 67.005))
print("Search 'stop':", backend.search_stop("stop"))
print("Search 'c':", backend.search_stop("c"))
