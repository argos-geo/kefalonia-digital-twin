BEGIN;

-- split every segment at points where ANOTHER segment's endpoint touches its interior
DROP TABLE IF EXISTS argos.road_seg CASCADE;
CREATE TABLE argos.road_seg AS
WITH ends AS (
  SELECT ST_StartPoint(geom) AS p FROM argos.road_net
  UNION ALL SELECT ST_EndPoint(geom) FROM argos.road_net
),
hits AS (
  SELECT e.id, ST_Union(ends.p) AS blade
  FROM argos.road_net e JOIN ends ON ST_DWithin(ends.p, e.geom, 1e-9)
  WHERE NOT (ST_Equals(ends.p, ST_StartPoint(e.geom)) OR ST_Equals(ends.p, ST_EndPoint(e.geom)))
  GROUP BY e.id
),
pieces AS (
  SELECT e.id AS old_id, (ST_Dump(ST_Split(ST_Snap(e.geom, h.blade, 1e-9), h.blade))).geom AS geom
  FROM argos.road_net e JOIN hits h ON h.id = e.id
  UNION ALL
  SELECT e.id, e.geom FROM argos.road_net e LEFT JOIN hits h ON h.id = e.id WHERE h.id IS NULL
)
SELECT row_number() OVER () AS id, old_id, geom FROM pieces;
CREATE INDEX ON argos.road_seg USING gist (geom);

-- attributes + minute costs
ALTER TABLE argos.road_seg ADD COLUMN road_class text, ADD COLUMN oneway boolean,
  ADD COLUMN speed_kmh int, ADD COLUMN cost_m float8, ADD COLUMN rcost_m float8;
UPDATE argos.road_seg s SET road_class=n.road_class, oneway=n.oneway, speed_kmh=n.speed_kmh
FROM argos.road_net n WHERE s.old_id = n.id;
UPDATE argos.road_seg SET
  cost_m  = ST_Length(geom::geography)/1000.0/speed_kmh*60.0,
  rcost_m = CASE WHEN oneway THEN -1 ELSE ST_Length(geom::geography)/1000.0/speed_kmh*60.0 END;

-- topology v2 (our own, 1 m clustering in UTM)
DROP TABLE IF EXISTS argos.road_seg_vertices;
CREATE TABLE argos.road_seg_vertices AS
WITH ep AS (
  SELECT ST_Transform(ST_StartPoint(geom),32634) AS p FROM argos.road_seg
  UNION ALL SELECT ST_Transform(ST_EndPoint(geom),32634) FROM argos.road_seg
),
cl AS (SELECT ST_ClusterDBSCAN(p, 1.0, 1) OVER () AS cid, p FROM ep),
cent AS (SELECT cid, ST_Centroid(ST_Collect(p)) AS cp FROM cl GROUP BY cid)
SELECT row_number() OVER () AS id, cp AS geom FROM cent;
CREATE INDEX ON argos.road_seg_vertices USING gist (geom);

ALTER TABLE argos.road_seg ADD COLUMN source int, ADD COLUMN target int;
UPDATE argos.road_seg e SET source = (SELECT v.id FROM argos.road_seg_vertices v ORDER BY v.geom <-> ST_Transform(ST_StartPoint(e.geom),32634) LIMIT 1);
UPDATE argos.road_seg e SET target = (SELECT v.id FROM argos.road_seg_vertices v ORDER BY v.geom <-> ST_Transform(ST_EndPoint(e.geom),32634) LIMIT 1);

COMMIT;

SELECT count(*) AS segments FROM argos.road_seg;
SELECT count(*) AS vertices FROM argos.road_seg_vertices;
SELECT component, count(*) AS vertices
FROM pgr_connectedComponents('SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_seg')
GROUP BY component ORDER BY 2 DESC LIMIT 6;
