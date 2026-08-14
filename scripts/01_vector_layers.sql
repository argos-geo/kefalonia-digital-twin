-- ARGOS T11 — Vector layers: raw OSM -> clean argos schema
BEGIN;

CREATE SCHEMA IF NOT EXISTS argos;

-- ================= ROADS =================
DROP TABLE IF EXISTS argos.roads;
CREATE TABLE argos.roads AS
SELECT
  osm_id,
  name,
  ref,
  highway AS osm_highway,
  CASE
    WHEN highway IN ('primary','primary_link')     THEN 'primary'
    WHEN highway IN ('secondary','secondary_link') THEN 'secondary'
    WHEN highway IN ('tertiary','tertiary_link')   THEN 'tertiary'
    WHEN highway IN ('residential','living_street','unclassified') THEN 'local'
    WHEN highway = 'track'    THEN 'track'
    WHEN highway IN ('path','footway','cycleway','bridleway','steps','pedestrian') THEN 'path'
    WHEN highway = 'service'  THEN 'service'
    ELSE 'other'
  END AS road_class,
  surface,
  tags->'maxspeed' AS maxspeed,
  (oneway = 'yes') AS oneway,
  round(ST_Length(ST_Transform(way,4326)::geography))::int AS length_m,
  ST_Transform(way,4326) AS geom
FROM planet_osm_line
WHERE highway IS NOT NULL;

CREATE INDEX idx_roads_geom  ON argos.roads USING GIST(geom);
CREATE INDEX idx_roads_class ON argos.roads(road_class);

-- ================= BUILDINGS =================
DROP TABLE IF EXISTS argos.buildings;
CREATE TABLE argos.buildings AS
SELECT
  osm_id,
  name,
  building AS building_type,
  tags->'building:levels' AS levels,
  tags->'addr:street' AS street,
  tags->'addr:housenumber' AS housenumber,
  round((ST_Area(ST_Transform(way,4326)::geography))::numeric,1) AS area_m2,
  ST_Transform(way,4326) AS geom
FROM planet_osm_polygon
WHERE building IS NOT NULL;

CREATE INDEX idx_buildings_geom ON argos.buildings USING GIST(geom);
CREATE INDEX idx_buildings_type ON argos.buildings(building_type);

-- ================= POIS =================
DROP TABLE IF EXISTS argos.pois;
CREATE TABLE argos.pois AS
SELECT
  osm_id,
  name,
  COALESCE(amenity, shop, tourism, leisure, historic) AS poi_type,
  CASE
    WHEN amenity IN ('restaurant','cafe','bar','fast_food') THEN 'food_drink'
    WHEN amenity IN ('pharmacy','doctors','hospital','clinic','dentist') THEN 'health'
    WHEN amenity IN ('school','kindergarten','university') THEN 'education'
    WHEN amenity IN ('fuel','parking','atm','bank','post_office') THEN 'services'
    WHEN shop IS NOT NULL     THEN 'shop'
    WHEN tourism IS NOT NULL  THEN 'tourism'
    WHEN leisure IS NOT NULL  THEN 'leisure'
    WHEN historic IS NOT NULL THEN 'heritage'
    ELSE 'other'
  END AS category,
  ST_Transform(way,4326) AS geom
FROM planet_osm_point
WHERE amenity IS NOT NULL OR shop IS NOT NULL OR tourism IS NOT NULL
   OR leisure IS NOT NULL OR historic IS NOT NULL;

CREATE INDEX idx_pois_geom     ON argos.pois USING GIST(geom);
CREATE INDEX idx_pois_category ON argos.pois(category);

ANALYZE argos.roads;
ANALYZE argos.buildings;
ANALYZE argos.pois;

COMMIT;
