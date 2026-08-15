-- T16 Stage A: distance-to-drivable-road accessibility score
-- Drivable classes: track, local, service, secondary, tertiary, primary
-- Score: 100 at the doorstep, linear decay to 0 at 2 km
BEGIN;

ALTER TABLE argos.buildings ADD COLUMN IF NOT EXISTS road_dist_m double precision;
ALTER TABLE argos.buildings ADD COLUMN IF NOT EXISTS access_score smallint;
ALTER TABLE argos.pois     ADD COLUMN IF NOT EXISTS road_dist_m double precision;
ALTER TABLE argos.pois     ADD COLUMN IF NOT EXISTS access_score smallint;

-- KNN nearest-road via <-> operator (uses the GiST indexes)
UPDATE argos.buildings b SET road_dist_m = (
  SELECT ST_Distance(r.geom::geography, ST_Centroid(b.geom)::geography)
  FROM argos.roads r
  WHERE r.road_class IN ('track','local','service','secondary','tertiary','primary')
  ORDER BY r.geom <-> ST_Centroid(b.geom)
  LIMIT 1
);

UPDATE argos.pois p SET road_dist_m = (
  SELECT ST_Distance(r.geom::geography, p.geom::geography)
  FROM argos.roads r
  WHERE r.road_class IN ('track','local','service','secondary','tertiary','primary')
  ORDER BY r.geom <-> p.geom
  LIMIT 1
);

UPDATE argos.buildings SET access_score = GREATEST(0, ROUND(100 - road_dist_m / 20.0))::smallint;
UPDATE argos.pois     SET access_score = GREATEST(0, ROUND(100 - road_dist_m / 20.0))::smallint;

CREATE INDEX IF NOT EXISTS idx_buildings_access ON argos.buildings (access_score);
CREATE INDEX IF NOT EXISTS idx_pois_access     ON argos.pois (access_score);

COMMIT;
