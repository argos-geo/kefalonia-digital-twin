-- T29 / v0.2.0: weather stream schema (SPEC_v0.2.0.md section 2)
BEGIN;
CREATE TABLE IF NOT EXISTS argos.weather_points (
  point_id smallint PRIMARY KEY,
  name_en text NOT NULL,
  name_el text NOT NULL,
  lat double precision NOT NULL,
  lon double precision NOT NULL,
  elevation_m smallint
);
INSERT INTO argos.weather_points VALUES
  (1,'Argostoli','Αργοστόλι',38.181,20.489,20),
  (2,'Sami','Σάμη',38.253,20.646,15),
  (3,'Fiskardo','Φισκάρδο',38.461,20.576,10),
  (4,'Lixouri','Ληξούρι',38.202,20.437,15),
  (5,'Ainos','Αίνος',38.140,20.665,1628)
ON CONFLICT (point_id) DO NOTHING;
CREATE TABLE IF NOT EXISTS argos.weather_hourly (
  point_id smallint NOT NULL REFERENCES argos.weather_points,
  ts timestamptz NOT NULL,
  temp_c real, rh_pct real, precip_mm real,
  wind_ms real, wind_dir smallint, gust_ms real,
  cloud_pct smallint, pressure_hpa real, cape real,
  fetched_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (point_id, ts)
) PARTITION BY RANGE (ts);
CREATE TABLE IF NOT EXISTS argos.weather_hourly_2026_10 PARTITION OF argos.weather_hourly
  FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE IF NOT EXISTS argos.weather_hourly_2026_11 PARTITION OF argos.weather_hourly
  FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
COMMIT;
