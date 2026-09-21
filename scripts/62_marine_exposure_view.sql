-- T47: beach facing_deg from wet-cell bearing + marine_exposure view (21 Sep 2026)
BEGIN;

ALTER TABLE argos.beaches ADD COLUMN IF NOT EXISTS facing_deg int;

UPDATE argos.beaches b SET facing_deg = s.brng FROM (
  SELECT DISTINCT ON (m.beach_osm_id) m.beach_osm_id,
    ((round(degrees(atan2(
      (m.cell_lon - ST_X(ST_Centroid(bb.geom))) * cos(radians(ST_Y(ST_Centroid(bb.geom)))),
      m.cell_lat - ST_Y(ST_Centroid(bb.geom)))))::int) + 360) % 360 AS brng
  FROM argos.marine_forecast m
  JOIN argos.beaches bb ON bb.osm_id = m.beach_osm_id
  ORDER BY m.beach_osm_id, m.valid_time
) s
WHERE b.osm_id = s.beach_osm_id;

CREATE OR REPLACE VIEW argos.marine_exposure AS
SELECT m.beach_osm_id, b.name, m.valid_time,
       m.vhm0, m.vmxl, m.vmdr, m.vtm10, m.cur_speed, m.stokes_x, m.stokes_y,
       m.cell_dist_m, b.facing_deg,
       round((100 * (0.7 * LEAST(1, m.vhm0 / 2.0) * CASE
           WHEN abs(((m.vmdr - b.facing_deg + 540)::numeric)::int % 360 - 180) <= 45 THEN 1.0
           WHEN abs(((m.vmdr - b.facing_deg + 540)::numeric)::int % 360 - 180) <= 90 THEN 0.6
           ELSE 0.2 END
         + 0.3 * LEAST(1, m.cur_speed / 0.7)))::numeric, 1) AS exposure
FROM argos.marine_forecast m
JOIN argos.beaches b ON b.osm_id = m.beach_osm_id;

GRANT SELECT ON argos.marine_exposure TO argos_read;
COMMIT;