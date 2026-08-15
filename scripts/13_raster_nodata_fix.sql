-- T15.1 hygiene v2: sea(0) -> nodata(-9999). crop=false: keeps 100x100 tiles (enforce_height_rast!)
BEGIN;
CREATE TEMP TABLE land AS
SELECT ST_Union(ST_Transform(way,4326)) AS geom
FROM public.planet_osm_polygon
WHERE boundary='administrative' AND admin_level='7';

DELETE FROM argos.wildfire_risk r
WHERE NOT EXISTS (SELECT 1 FROM land WHERE ST_Intersects(r.rast, land.geom));
DELETE FROM argos.wildfire_risk_class r
WHERE NOT EXISTS (SELECT 1 FROM land WHERE ST_Intersects(r.rast, land.geom));

UPDATE argos.wildfire_risk r
SET rast = ST_SetBandNoDataValue(ST_Clip(r.rast, 1, land.geom, -9999::double precision, false), 1, -9999::double precision)
FROM land WHERE ST_Intersects(r.rast, land.geom);

UPDATE argos.wildfire_risk_class r
SET rast = ST_SetBandNoDataValue(ST_Clip(r.rast, 1, land.geom, -9999::double precision, false), 1, -9999::double precision)
FROM land WHERE ST_Intersects(r.rast, land.geom);
COMMIT;

SELECT (vc).value AS val, sum((vc).count) AS px
FROM (SELECT ST_ValueCount(rast,1,false) AS vc FROM argos.wildfire_risk) t
GROUP BY 1 ORDER BY 2 DESC LIMIT 5;
SELECT count(*) AS risk_tiles FROM argos.wildfire_risk;
