# smart_transit3 Loader

## Install

```bash
pip install psycopg2-binary requests
```

## Run

```bash
python run_main.py --stops stops.csv --order route sequence.csv
```

## Notes

- The script creates/updates `smart_transit3` tables from `migration_smart_transit3.sql`.
- `smart_transit3.edges` is created by introspecting `smart_transit.edges` (no hardcoded edge columns).
- Segment distance/time are fetched only from OSRM (`https://router.project-osrm.org`) with retries + cache.
- to run: python run_main.py --stops ".\graphdata\stops.csv" --order ".\graphdata\route sequence.csv"

