# smart_transit2 Loader

## Install

```bash
pip install psycopg2-binary requests
```

## Run

```bash
python run_main.py --stops stops.csv --order route_sequence.csv
```

Example with your local files:

```bash
python run_main.py --stops "C:\Users\ayubs\OneDrive\Desktop\new beginnings\stops.csv" --order "C:\Users\ayubs\OneDrive\Desktop\new beginnings\route sequnce.csv"
```

## Notes

- The script creates/updates `smart_transit2` core tables from `migration_smart_transit2.sql`.
- It introspects `smart_transit.edges` and recreates `smart_transit2.edges` with matching column names/types if needed.
- It truncates `smart_transit2` load tables before insert.
- OSRM (`https://router.project-osrm.org`) is mandatory for segment distance/time.
