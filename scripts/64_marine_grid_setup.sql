-- v0.0.7 particle current layer: full CMEMS currents grid (all wet cells, all forecast hours).
-- Loaded by scripts/63_marine_refresh.sh from /tmp/marine_grid.csv written by scripts/61_cmems_fetch.py.
CREATE TABLE IF NOT EXISTS argos.marine_grid (
    valid_time timestamptz NOT NULL,
    lat double precision NOT NULL,
    lon double precision NOT NULL,
    uo real,
    vo real,
    PRIMARY KEY (valid_time, lat, lon)
);
GRANT SELECT ON argos.marine_grid TO argos_read;
