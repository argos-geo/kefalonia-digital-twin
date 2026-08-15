BEGIN;

-- vertices = endpoints clustered at 1.0 m in UTM meters
DROP TABLE IF EXISTS argos.road_net_vertices;
CREATE TABLE argos.road_net_vertices AS
WITH ep AS (
  SELECT ST_Transform(ST_StartPoint(geom), 32634) AS p FROM argos.road_net
  UNION ALL SELECT ST_Transform(ST_EndPoint(geom), 32634) FROM argos.road_net
),
cl AS (SELECT ST_ClusterDBSCAN(p, 1.0, 1) OVER () AS cid, p FROM ep),
cent AS (SELECT cid, ST_Centroid(ST_Collect(p)) AS cp FROM cl GROUP BY cid)
SELECT row_number() OVER () AS id, cp AS geom FROM cent;
CREATE INDEX ON argos.road_net_vertices USING gist (geom);

-- source/target = nearest clustered vertex (KNN, indexed)
UPDATE argos.road_net e SET source = (
  SELECT v.id FROM argos.road_net_vertices v
  ORDER BY v.geom <-> ST_Transform(ST_StartPoint(e.geom), 32634) LIMIT 1);
UPDATE argos.road_net e SET target = (
  SELECT v.id FROM argos.road_net_vertices v
  ORDER BY v.geom <-> ST_Transform(ST_EndPoint(e.geom), 32634) LIMIT 1);

COMMIT;

-- connectivity report, take two: we want ONE giant component
SELECT component, count(*) AS vertices
FROM pgr_connectedComponents(
  'SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_net')
GROUP BY component ORDER BY 2 DESC LIMIT 6;
