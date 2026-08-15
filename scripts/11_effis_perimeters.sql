-- T15.1 — EFFIS burnt-area perimeters: typed columns, hygiene envelope, GIST index
DROP TABLE IF EXISTS argos.effis_perimeters;
CREATE TABLE argos.effis_perimeters AS
SELECT
  id::int                          AS effis_id,
  firedate::timestamp::date        AS fire_date,
  finaldate::timestamp::date       AS final_date,
  NULLIF(area_ha,'')::numeric      AS area_ha,
  NULLIF(broadlea,'')::numeric     AS broadleaf_pct,
  NULLIF(conifer,'')::numeric      AS conifer_pct,
  NULLIF(mixed,'')::numeric        AS mixed_pct,
  NULLIF(scleroph,'')::numeric     AS scleroph_pct,
  NULLIF(agriareas,'')::numeric    AS agri_pct,
  NULLIF(artifsurf,'')::numeric    AS artif_pct,
  class                            AS effis_class,
  ST_MakeValid(ST_SetSRID(geom,4326))::geometry(MultiPolygon,4326) AS geom
FROM argos.effis_perimeters_raw
WHERE ST_Intersects(ST_SetSRID(geom,4326),
                    ST_MakeEnvelope(20.30,37.95,20.90,38.55,4326));

CREATE INDEX effis_perimeters_geom_idx ON argos.effis_perimeters USING GIST (geom);

-- Summary
SELECT count(*) AS perimeters, sum(area_ha)::int AS total_ha,
       min(fire_date) AS first_fire, max(fire_date) AS last_fire
FROM argos.effis_perimeters;

-- By year
SELECT extract(year FROM fire_date)::int AS yr, count(*) AS fires,
       sum(area_ha)::int AS ha
FROM argos.effis_perimeters GROUP BY 1 ORDER BY 1;

-- Roster (centroids as lat,lon — Google Maps order, never lon,lat)
SELECT effis_id, fire_date, area_ha,
       round(ST_Y(ST_Centroid(geom))::numeric,4) AS lat,
       round(ST_X(ST_Centroid(geom))::numeric,4) AS lon,
       round(scleroph_pct) AS sclero, round(agri_pct) AS agri, round(conifer_pct) AS conif
FROM argos.effis_perimeters ORDER BY fire_date, area_ha DESC;
