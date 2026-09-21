-- T46 marine core: pilot beach curation + rolling forecast table (21 Sep 2026)
BEGIN;

CREATE TABLE IF NOT EXISTS argos.marine_forecast (
  beach_osm_id bigint NOT NULL,
  valid_time  timestamptz NOT NULL,
  vhm0 real,          -- significant wave height, m
  vmxl real,          -- max crest-to-trough height, m
  vmdr real,          -- mean wave direction, deg from
  vtm10 real,         -- mean period, s
  cur_u real,         -- eastward surface current, m/s
  cur_v real,         -- northward surface current, m/s
  cur_speed real,     -- m/s
  stokes_x real,      -- Stokes drift x, m/s
  stokes_y real,      -- Stokes drift y, m/s
  cell_lon double precision,   -- sampled CMEMS cell
  cell_lat double precision,
  cell_dist_m integer,         -- beach centroid to cell distance
  cmems_run timestamptz,       -- model run timestamp
  fetched_at timestamptz DEFAULT now(),
  PRIMARY KEY (beach_osm_id, valid_time)
);
CREATE INDEX IF NOT EXISTS idx_marine_forecast_time ON argos.marine_forecast(valid_time);
GRANT SELECT ON argos.marine_forecast TO argos_read;

UPDATE argos.beaches SET curated=true, name='Myrtos',        local_name='Μύρτος',        notes='marine pilot v1' WHERE osm_id=237382151;
UPDATE argos.beaches SET curated=true, name='Antisamos',     local_name='Αντίσαμος',     notes='marine pilot v1' WHERE osm_id=41427183;
UPDATE argos.beaches SET curated=true, name='Skala',         local_name='Σκάλα',         notes='marine pilot v1' WHERE osm_id=237382152;
UPDATE argos.beaches SET curated=true, name='Xi',            local_name='Ξι',            notes='marine pilot v1' WHERE osm_id=372765845;
UPDATE argos.beaches SET curated=true, name='Petani',        local_name='Πετανή',        notes='marine pilot v1' WHERE osm_id=303062837;
UPDATE argos.beaches SET curated=true, name='Lourdas',       local_name='Λουρδάτα',      notes='marine pilot v1' WHERE osm_id=113231768;
UPDATE argos.beaches SET curated=true, name='Platys Gialos', local_name='Πλατύς Γιαλός', notes='marine pilot v1' WHERE osm_id=500932453;
UPDATE argos.beaches SET curated=true, name='Dafnoudi',      local_name='Δαφνούδι',      notes='marine pilot v1' WHERE osm_id=227295480;
UPDATE argos.beaches SET curated=true, name='Emblisi',       local_name='Εμπλύση',       notes='marine pilot v1' WHERE osm_id=288182036;
UPDATE argos.beaches SET curated=true, name='Makris Gialos', local_name='Μακρύς Γιαλός', notes='marine pilot v1' WHERE osm_id=303071584;
UPDATE argos.beaches SET curated=true, name='Assos',         local_name='Άσσος',         notes='marine pilot v1' WHERE osm_id=237382159;
UPDATE argos.beaches SET curated=true, name='Fiskardo',      local_name='Φισκάρδο',      notes='marine pilot v1' WHERE osm_id=288000459;
UPDATE argos.beaches SET curated=true, name='Kaminia',       local_name='Καμίνια',       notes='marine pilot v1' WHERE osm_id=41427181;
UPDATE argos.beaches SET curated=true, name='Fteri',         local_name='Φτέρη',         notes='marine pilot v1; Natura + Posidonia, anchoring prohibited' WHERE osm_id=501178507;

COMMIT;
