\set ON_ERROR_STOP on
CREATE TEMP TABLE fmean AS
SELECT * FROM (
  SELECT 'v1' AS t, q.effis_id, q.fire_date, q.area_ha, (q.s).count AS px, (q.s).mean AS mean
  FROM (SELECT p.effis_id,p.fire_date,p.area_ha,
               ST_SummaryStats(ST_Union(ST_Clip(r.rast,p.geom)),true) AS s
        FROM argos.effis_perimeters p JOIN argos.wildfire_risk r ON ST_Intersects(r.rast,p.geom)
        GROUP BY p.effis_id,p.fire_date,p.area_ha) q
  UNION ALL
  SELECT 'v1_1b', q.effis_id, q.fire_date, q.area_ha, (q.s).count, (q.s).mean
  FROM (SELECT p.effis_id,p.fire_date,p.area_ha,
               ST_SummaryStats(ST_Union(ST_Clip(r.rast,p.geom)),true) AS s
        FROM argos.effis_perimeters p JOIN argos.wildfire_risk_v1_1b r ON ST_Intersects(r.rast,p.geom)
        GROUP BY p.effis_id,p.fire_date,p.area_ha) q
) z;

CREATE TEMP TABLE base AS
SELECT 'v1' AS t, (s).mean FROM (SELECT ST_SummaryStats(ST_Union(rast),true) s FROM argos.wildfire_risk) q
UNION ALL
SELECT 'v1_1b', (s).mean FROM (SELECT ST_SummaryStats(ST_Union(rast),true) s FROM argos.wildfire_risk_v1_1b) q;

\echo '=== burned area-weighted mean + fires above island mean ==='
SELECT f.t, round((sum(f.px*f.mean)/sum(f.px))::numeric,1) AS burned_wmean,
       round(((SELECT mean FROM base WHERE base.t=f.t))::numeric,1) AS island_mean,
       sum((f.mean > (SELECT mean FROM base WHERE base.t=f.t))::int) AS fires_above, count(*) AS n
FROM fmean f GROUP BY f.t ORDER BY f.t;

\echo '=== per-fire means (worst v1 misses first) ==='
SELECT v.effis_id, v.fire_date, v.area_ha, round(v.mean::numeric,1) v1, round(a.mean::numeric,1) v1_1b, round((a.mean-v.mean)::numeric,1) AS d
FROM (SELECT * FROM fmean WHERE t='v1') v JOIN (SELECT * FROM fmean WHERE t='v1_1b') a USING(effis_id)
ORDER BY d ASC;

\echo '=== class mix: island vs burned ==='
WITH icls AS (
  SELECT 'v1' t,(vc).value cls,sum((vc).count) px FROM (SELECT ST_ValueCount(rast,1,true) vc FROM argos.wildfire_risk_class) q WHERE (vc).value>=0 GROUP BY 1,2
  UNION ALL
  SELECT 'v1_1b',(vc).value,sum((vc).count) FROM (SELECT ST_ValueCount(rast,1,true) vc FROM argos.wildfire_risk_v1_1b_class) q WHERE (vc).value>=0 GROUP BY 1,2
), bcls AS (
  SELECT 'v1' t,(vc).value cls,sum((vc).count) px
  FROM (SELECT ST_ValueCount(ST_Union(ST_Clip(c.rast,p.geom)),1,true) vc
        FROM argos.effis_perimeters p JOIN argos.wildfire_risk_class c ON ST_Intersects(c.rast,p.geom) GROUP BY p.effis_id) q
  WHERE (vc).value>=0 GROUP BY 1,2
  UNION ALL
  SELECT 'v1_1b',(vc).value,sum((vc).count)
  FROM (SELECT ST_ValueCount(ST_Union(ST_Clip(c.rast,p.geom)),1,true) vc
        FROM argos.effis_perimeters p JOIN argos.wildfire_risk_v1_1b_class c ON ST_Intersects(c.rast,p.geom) GROUP BY p.effis_id) q
  WHERE (vc).value>=0 GROUP BY 1,2
)
SELECT b.t,b.cls,
       round((100.0*b.px/sum(b.px) OVER (PARTITION BY b.t))::numeric,1) burned_pct,
       round((100.0*i.px/sum(i.px) OVER (PARTITION BY i.t))::numeric,1) island_pct
FROM bcls b JOIN icls i ON i.t=b.t AND i.cls=b.cls
ORDER BY b.t,b.cls;
