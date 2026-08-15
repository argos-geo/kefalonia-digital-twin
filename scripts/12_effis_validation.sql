\echo '=== 1. ISLAND BASELINE (continuous risk 0-100) ==='
SELECT (s).count AS px, round((s).mean::numeric,2) AS island_mean,
       round((s).stddev::numeric,2) AS stddev, (s).min, (s).max
FROM (SELECT ST_SummaryStats(ST_Union(rast), true) AS s FROM argos.wildfire_risk) t;

\echo '=== 2. PER-PERIMETER RISK (the publishable table core) ==='
SELECT effis_id, fire_date, area_ha, (s).count AS px,
       round((s).mean::numeric,1) AS mean_risk,
       round((s).max::numeric,0) AS max_risk,
       (fire_date >= DATE '2025-01-01') AS recent_scar
FROM (
  SELECT p.effis_id, p.fire_date, p.area_ha,
         ST_SummaryStats(ST_Union(ST_Clip(r.rast, p.geom)), true) AS s
  FROM argos.effis_perimeters p
  JOIN argos.wildfire_risk r ON ST_Intersects(r.rast, p.geom)
  GROUP BY p.effis_id, p.fire_date, p.area_ha
) t ORDER BY fire_date;

\echo '=== 3. CLASS MIX: island vs burned (skill score ingredients) ==='
WITH island AS (
  SELECT (vc).value AS cls, sum((vc).count)::float AS px
  FROM (SELECT ST_ValueCount(rast,1,true) AS vc FROM argos.wildfire_risk_class) t GROUP BY 1
), burned AS (
  SELECT (vc).value AS cls, sum((vc).count)::float AS px
  FROM (SELECT ST_ValueCount(ST_Union(ST_Clip(c.rast,p.geom)),1,true) AS vc
        FROM argos.effis_perimeters p
        JOIN argos.wildfire_risk_class c ON ST_Intersects(c.rast,p.geom)
        GROUP BY p.effis_id) t GROUP BY 1
)
SELECT i.cls AS class,
       round((100*i.px/sum(i.px) OVER ())::numeric,1) AS island_pct,
       coalesce(round((100*b.px/sum(b.px) OVER ())::numeric,1),0) AS burned_pct
FROM island i LEFT JOIN burned b ON b.cls=i.cls ORDER BY i.cls;
