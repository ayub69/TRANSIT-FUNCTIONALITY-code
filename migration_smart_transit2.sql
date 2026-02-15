BEGIN;

CREATE SCHEMA IF NOT EXISTS smart_transit2;

CREATE TABLE IF NOT EXISTS smart_transit2.stops (
  stop_id    INTEGER PRIMARY KEY,
  stop_name  TEXT NOT NULL,
  lat        DOUBLE PRECISION NOT NULL,
  lon        DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS smart_transit2.routes (
  route_id    INTEGER PRIMARY KEY,
  route_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS smart_transit2.route_stops (
  route_id  INTEGER NOT NULL,
  seq       INTEGER NOT NULL CHECK (seq > 0),
  stop_id   INTEGER NOT NULL,
  PRIMARY KEY (route_id, seq),
  UNIQUE (route_id, stop_id),
  CONSTRAINT fk_route_stops_route
    FOREIGN KEY (route_id) REFERENCES smart_transit2.routes(route_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_route_stops_stop
    FOREIGN KEY (stop_id) REFERENCES smart_transit2.stops(stop_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_stops_name
  ON smart_transit2.stops (stop_name);

CREATE INDEX IF NOT EXISTS idx_route_stops_stop
  ON smart_transit2.route_stops (stop_id);

CREATE INDEX IF NOT EXISTS idx_route_stops_route_seq
  ON smart_transit2.route_stops (route_id, seq);

-- NOTE:
-- smart_transit2.edges is intentionally NOT declared here with fixed columns.
-- It must be created at runtime by introspecting smart_transit.edges so
-- column names/types stay exactly compatible with your current database.

COMMIT;
