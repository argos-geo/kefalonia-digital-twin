\o /tmp/q4_stats.json
WITH o AS (
  SELECT ST_Transform(p.way,4326) AS g, p.name AS nm FROM public.planet_osm_point p
  WHERE p.name LIKE '%ισκάρδ%' AND p.place IS NOT NULL LIMIT 1
),
anchor AS (
  SELECT v.id AS vid FROM argos.road_seg_vertices v, o
  ORDER BY ST_Transform(v.geom,4326) <-> o.g LIMIT 1
),
ports AS (
  SELECT p.net_vid FROM argos.pois p, o
  WHERE p.poi_type IN ('ferry_terminal','marina') AND p.net_vid IS NOT NULL
    AND ST_Distance(p.geom::geography, o.g::geography) > 2000
),
d0 AS (SELECT * FROM pgr_dijkstra('SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_seg',
        (SELECT vid FROM anchor), (SELECT array_agg(net_vid) FROM ports), true)),
tot AS (SELECT end_vid, max(agg_cost) AS total_min FROM d0 GROUP BY end_vid),
best AS (SELECT end_vid, total_min FROM tot ORDER BY total_min LIMIT 1),
r AS (SELECT d.seq, d.cost, rn.geom FROM d0 d JOIN argos.road_seg rn ON rn.id=d.edge
      WHERE d.end_vid=(SELECT end_vid FROM best) AND d.edge>0)
SELECT jsonb_build_object(
  'port', (SELECT p.name FROM argos.pois p WHERE p.net_vid=(SELECT end_vid FROM best)
           AND p.poi_type IN ('ferry_terminal','marina')
           ORDER BY (p.name IS NULL OR p.name=''), p.poi_type LIMIT 1),
  'port_type', (SELECT p.poi_type FROM argos.pois p WHERE p.net_vid=(SELECT end_vid FROM best)
           AND p.poi_type IN ('ferry_terminal','marina')
           ORDER BY (p.name IS NULL OR p.name=''), p.poi_type LIMIT 1),
  'dist_km', round((SELECT sum(ST_Length(geom::geography))/1000 FROM r)::numeric, 1),
  'est_min', round((SELECT sum(cost) FROM r)::numeric),
  'edges', (SELECT count(*) FROM r));
\o /tmp/q4.geojson
WITH o AS (
  SELECT ST_Transform(p.way,4326) AS g, p.name AS nm FROM public.planet_osm_point p
  WHERE p.name LIKE '%ισκάρδ%' AND p.place IS NOT NULL LIMIT 1
),
anchor AS (
  SELECT v.id AS vid FROM argos.road_seg_vertices v, o
  ORDER BY ST_Transform(v.geom,4326) <-> o.g LIMIT 1
),
ports AS (
  SELECT p.net_vid FROM argos.pois p, o
  WHERE p.poi_type IN ('ferry_terminal','marina') AND p.net_vid IS NOT NULL
    AND ST_Distance(p.geom::geography, o.g::geography) > 2000
),
d0 AS (SELECT * FROM pgr_dijkstra('SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_seg',
        (SELECT vid FROM anchor), (SELECT array_agg(net_vid) FROM ports), true)),
tot AS (SELECT end_vid, max(agg_cost) AS total_min FROM d0 GROUP BY end_vid),
best AS (SELECT end_vid FROM tot ORDER BY total_min LIMIT 1)
SELECT jsonb_build_object('type','FeatureCollection','features',COALESCE(jsonb_agg(f),'[]'::jsonb))
FROM (SELECT jsonb_build_object('type','Feature','geometry',ST_AsGeoJSON(rn.geom)::jsonb,
      'properties',jsonb_build_object('seq',d.seq,'road_class',rn.road_class)) f
      FROM d0 d JOIN argos.road_seg rn ON rn.id=d.edge
      WHERE d.end_vid=(SELECT end_vid FROM best) AND d.edge>0 ORDER BY d.seq) a;
\o /tmp/q4_points.geojson
WITH o AS (
  SELECT ST_Transform(p.way,4326) AS g, p.name AS nm FROM public.planet_osm_point p
  WHERE p.name LIKE '%ισκάρδ%' AND p.place IS NOT NULL LIMIT 1
),
anchor AS (
  SELECT v.id AS vid FROM argos.road_seg_vertices v, o
  ORDER BY ST_Transform(v.geom,4326) <-> o.g LIMIT 1
),
ports AS (
  SELECT p.net_vid FROM argos.pois p, o
  WHERE p.poi_type IN ('ferry_terminal','marina') AND p.net_vid IS NOT NULL
    AND ST_Distance(p.geom::geography, o.g::geography) > 2000
),
d0 AS (SELECT * FROM pgr_dijkstra('SELECT id, source, target, cost_m AS cost, rcost_m AS reverse_cost FROM argos.road_seg',
        (SELECT vid FROM anchor), (SELECT array_agg(net_vid) FROM ports), true)),
tot AS (SELECT end_vid, max(agg_cost) AS total_min FROM d0 GROUP BY end_vid),
best AS (SELECT end_vid FROM tot ORDER BY total_min LIMIT 1),
pts AS (SELECT g, 'origin' AS role, nm FROM o),
dst AS (SELECT p.geom AS g, p.name AS nm FROM argos.pois p
        WHERE p.net_vid=(SELECT end_vid FROM best) AND p.poi_type IN ('ferry_terminal','marina')
        ORDER BY (p.name IS NULL OR p.name=''), p.poi_type LIMIT 1)
SELECT jsonb_build_object('type','FeatureCollection','features',jsonb_agg(f)) FROM (
  SELECT jsonb_build_object('type','Feature','geometry',ST_AsGeoJSON(g)::jsonb,
         'properties',jsonb_build_object('role',role,'name',nm)) f FROM pts
  UNION ALL
  SELECT jsonb_build_object('type','Feature','geometry',ST_AsGeoJSON(g)::jsonb,
         'properties',jsonb_build_object('role','dest','name',nm)) f FROM dst
) a;