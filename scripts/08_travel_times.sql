BEGIN;

-- destinations, straight from the data
DROP TABLE IF EXISTS argos.dest_vertices;
CREATE TABLE argos.dest_vertices AS
SELECT d.osm_id, d.name, d.poi_type,
  (SELECT v.id FROM argos.road_seg_vertices v
   ORDER BY v.geom <-> ST_Transform(d.geom, 32634) LIMIT 1) AS vid
FROM argos.pois d
WHERE d.poi_type = 'fire_station'
   OR (d.poi_type = 'ferry_terminal'
       AND d.name IN ('Φισκάρδο','Αργοστόλι','Ληξούρι','Πεσσάδα','Σάμη','Πόρος'));

-- per-vertex minutes: from the fire station, and from nearest ferry port
DROP TABLE IF EXISTS argos.vertex_fire_min;
CREATE TABLE argos.vertex_fire_min AS
SELECT node AS vid, min(agg_cost) AS fire_min
FROM pgr_drivingDistance(
  'SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_seg',
  (SELECT vid FROM argos.dest_vertices WHERE poi_type = 'fire_station' LIMIT 1),
  10000, true) dd GROUP BY node;

DROP TABLE IF EXISTS argos.vertex_port_min;
CREATE TABLE argos.vertex_port_min AS
SELECT node AS vid, min(agg_cost) AS port_min
FROM pgr_drivingDistance(
  'SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_seg',
  (SELECT array_agg(vid) FROM argos.dest_vertices WHERE poi_type = 'ferry_terminal'),
  10000, true) dd GROUP BY node;

-- buildings + POIs: nearest junction, plus Stage A last-mile walk (80 m/min)
ALTER TABLE argos.buildings ADD COLUMN IF NOT EXISTS net_vid bigint,
                            ADD COLUMN IF NOT EXISTS fire_min double precision,
                            ADD COLUMN IF NOT EXISTS port_min double precision;
ALTER TABLE argos.pois      ADD COLUMN IF NOT EXISTS net_vid bigint,
                            ADD COLUMN IF NOT EXISTS fire_min double precision,
                            ADD COLUMN IF NOT EXISTS port_min double precision;

UPDATE argos.buildings b SET net_vid = (
  SELECT v.id FROM argos.road_seg_vertices v
  ORDER BY v.geom <-> ST_Transform(ST_Centroid(b.geom), 32634) LIMIT 1);
UPDATE argos.pois p SET net_vid = (
  SELECT v.id FROM argos.road_seg_vertices v
  ORDER BY v.geom <-> ST_Transform(p.geom, 32634) LIMIT 1);

UPDATE argos.buildings b SET fire_min = f.fire_min + b.road_dist_m/80.0,
                             port_min = p.port_min + b.road_dist_m/80.0
FROM argos.vertex_fire_min f, argos.vertex_port_min p
WHERE b.net_vid = f.vid AND b.net_vid = p.vid;

UPDATE argos.pois p SET fire_min = f.fire_min + p.road_dist_m/80.0,
                        port_min = po.port_min + p.road_dist_m/80.0
FROM argos.vertex_fire_min f, argos.vertex_port_min po
WHERE p.net_vid = f.vid AND p.net_vid = po.vid;

COMMIT;
