# Admin Panel APIs (Frontend Handoff)

Base path: `/admin`  
Content-Type: `application/json`

## 1) Get Route Sequence
**Endpoint**: `GET /admin/routes/sequence?route_name=<ROUTE_NAME>`

**Purpose**
- Returns ordered route stops (`seq`) for a selected route.
- Use before insert/remove operations.

**Example request**
```http
GET /admin/routes/sequence?route_name=R1
```

**Example response**
```json
{
  "route_name": "R1",
  "stops": [
    { "seq": 1, "stop_id": 10, "stop_name": "Stop A", "lat": 24.8, "lon": 67.0 },
    { "seq": 2, "stop_id": 11, "stop_name": "Stop B", "lat": 24.81, "lon": 67.01 }
  ]
}
```

---

## 2) Insert Stop Into Route
**Endpoint**: `POST /admin/routes/stops/insert`

**Purpose**
- Insert stop by name (no IDs required).
- Rebuilds route sequence + route edges.
- Uses OSRM to compute new `distance_km` and `time_min`.

**Body (general)**
```json
{
  "route_name": "R1",
  "stop_name": "New Stop",
  "before_stop_name": "Stop B",
  "after_stop_name": "Stop A",
  "lat": 24.90111,
  "lon": 67.10222
}
```

**Rules**
- Start insertion: only `before_stop_name` (must be current first stop)
- End insertion: only `after_stop_name` (must be current last stop)
- Middle insertion: both `after_stop_name` + `before_stop_name`, and they must be consecutive in current route sequence
- `lat/lon` required only if `stop_name` does not already exist

**Example response**
```json
{
  "message": "Stop added and route edges rebuilt successfully.",
  "route_name": "R1",
  "added_stop_name": "New Stop",
  "route_stop_sequence": {
    "route_name": "R1",
    "stops": []
  }
}
```

---

## 3) Remove Stop From Route
**Endpoint**: `POST /admin/routes/stops/remove`

**Purpose**
- Remove stop by name from route.
- Clears affected edges, reconnects neighbors, and rebuilds route continuity.

**Body**
```json
{
  "route_name": "R1",
  "stop_name": "Stop X"
}
```

**Example response**
```json
{
  "message": "Stop removed, dangling edges cleared, and neighboring stops reconnected.",
  "route_name": "R1",
  "removed_stop_name": "Stop X",
  "route_stop_sequence": {
    "route_name": "R1",
    "stops": []
  }
}
```

---

## 4) Report Delay (Affects Routing Weights)
**Endpoint**: `POST /admin/delays/report`

**Purpose**
- Report delay between two route stops.
- Delay is applied to routing time weights (fastest route behavior).

**Body**
```json
{
  "route_name": "R1",
  "from_stop_name": "Stop A",
  "to_stop_name": "Stop B",
  "delay_min": 8,
  "valid_for_min": 60,
  "reason": "Traffic congestion"
}
```

**Example response**
```json
{
  "message": "Delay reported and applied to routing weights.",
  "delay_id": 12,
  "route_name": "R1",
  "from_stop_name": "Stop A",
  "to_stop_name": "Stop B",
  "delay_min": 8.0,
  "reported_at": "2026-03-12T12:34:56.000000",
  "expires_at": "2026-03-12T13:34:56.000000"
}
```

---

## 5) List Active Delays
**Endpoint**: `GET /admin/delays/active`  
Optional filter: `GET /admin/delays/active?route_name=R1`

**Purpose**
- Returns active, non-expired delay reports.

**Example response**
```json
{
  "active_delays": [
    {
      "delay_id": 12,
      "route_name": "R1",
      "from_stop_name": "Stop A",
      "to_stop_name": "Stop B",
      "delay_min": 8.0,
      "reason": "Traffic congestion",
      "reported_at": "2026-03-12T12:34:56",
      "expires_at": "2026-03-12T13:34:56",
      "active": true
    }
  ]
}
```

---

## 6) Get Dashboard Counts
**Endpoint**: `GET /admin/stats/counts`

**Purpose**
- Returns total stops and total routes for dashboard cards.

**Example response**
```json
{
  "total_stops": 312,
  "total_routes": 14
}
```

---

## Recommended Frontend Integration Flow
1. On admin page load:
   - `GET /admin/stats/counts`
2. On route selection:
   - `GET /admin/routes/sequence?route_name=...`
3. On insert/remove:
   - Call write API
   - Refresh route sequence + counts
4. On delay report:
   - `POST /admin/delays/report`
   - Refresh `GET /admin/delays/active`

---

## Error Handling
- `400`: invalid payload or invalid insertion rule
- `404`: route/stop not found or stop not in selected route
- `409`: ambiguous name or duplicate stop in route
- `500`: unexpected server error
