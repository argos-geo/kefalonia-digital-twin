\set ON_ERROR_STOP on
BEGIN;
CREATE TEMP TABLE land_fix AS
SELECT ST_Union(ST_Transform(way,4326)) AS geom
FROM planet_osm_polygon
WHERE boundary='administrative' AND admin_level='7';
SELECT round(sum(ST_Area(geom::geography)/1000000)::numeric,1) AS land_km2 FROM land_fix;

DELETE FROM argos.wildfire_risk_v1_1b r WHERE NOT ST_Intersects(r.rast, (SELECT geom FROM land_fix));
UPDATE argos.wildfire_risk_v1_1b r
SET rast = ST_SetBandNoDataValue(ST_Clip(r.rast,1,(SELECT geom FROM land_fix),-9999,false),1,-9999);

DELETE FROM argos.wildfire_risk_v1_1b_class r WHERE NOT ST_Intersects(r.rast, (SELECT geom FROM land_fix));
UPDATE argos.wildfire_risk_v1_1b_class r
SET rast = ST_SetBandNoDataValue(ST_Clip(r.rast,1,(SELECT geom FROM land_fix),-9999,false),1,-9999);
ANALYZE argos.wildfire_risk_v1_1b;
ANALYZE argos.wildfire_risk_v1_1b_class;
COMMIT;
