-- ARGOS T12 — Curated layers: beaches + trails (OSM base, local knowledge on top)
BEGIN;

-- ================= BEACHES =================
DROP TABLE IF EXISTS argos.beaches;
CREATE TABLE argos.beaches AS
SELECT osm_id, name, surface, tags->'blue_flag' AS blue_flag,
       'polygon' AS source_form, ST_Transform(way,4326) AS geom
FROM planet_osm_polygon
WHERE "natural" IN ('beach','sand')
UNION ALL
SELECT osm_id, name, surface, tags->'blue_flag',
       'point', ST_Transform(way,4326)
FROM planet_osm_point
WHERE "natural" IN ('beach','sand');

ALTER TABLE argos.beaches
  ADD COLUMN curated boolean DEFAULT false,
  ADD COLUMN local_name text,
  ADD COLUMN access_type text,   -- car / hike / boat
  ADD COLUMN notes text;

CREATE INDEX idx_beaches_geom ON argos.beaches USING GIST(geom);

-- ================= TRAILS =================
DROP TABLE IF EXISTS argos.trails;
CREATE TABLE argos.trails AS
SELECT osm_id, name,
       route AS route_type,
       tags->'sac_scale' AS sac_scale,
       round(ST_Length(ST_Transform(way,4326)::geography))::int AS length_m,
       ST_Transform(way,4326) AS geom
FROM planet_osm_line
WHERE route IN ('hiking','foot')
   OR (highway = 'path' AND name IS NOT NULL);

ALTER TABLE argos.trails
  ADD COLUMN curated boolean DEFAULT false,
  ADD COLUMN local_name text,
  ADD COLUMN difficulty text,
  ADD COLUMN notes text;

CREATE INDEX idx_trails_geom ON argos.trails USING GIST(geom);

ANALYZE argos.beaches;
ANALYZE argos.trails;

COMMIT;
