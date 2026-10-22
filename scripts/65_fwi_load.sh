#!/usr/bin/env bash
# Script 65 (load half): append one day's EFFIS FWI tiff into argos.fwi_daily.
# Rerun-safe: DELETEs the day before appending. Usage: bash scripts/65_fwi_load.sh [YYYY-MM-DD]
set -euo pipefail
DAY="${1:-$(date -u +%F)}"
TIF="data/fwi/fwi_${DAY}.tif"
[ -f "$TIF" ] || { echo "FAIL: $TIF missing, run 65_fwi_fetch.sh $DAY first"; exit 1; }
docker exec -i argos-postgis psql -U argos -d argos <<'SQL'
CREATE TABLE IF NOT EXISTS argos.fwi_daily (
  rid serial PRIMARY KEY,
  rast raster,
  filename text,
  fwi_date date
);
CREATE INDEX IF NOT EXISTS fwi_daily_rast_gist ON argos.fwi_daily USING gist (st_convexhull(rast));
CREATE INDEX IF NOT EXISTS fwi_daily_date_idx ON argos.fwi_daily (fwi_date);
SQL
docker exec -i argos-postgis psql -U argos -d argos -c "DELETE FROM argos.fwi_daily WHERE fwi_date = '$DAY';"
raster2pgsql -a -s 4326 -F -t 100x100 "$TIF" argos.fwi_daily | docker exec -i argos-postgis psql -U argos -d argos
docker exec -i argos-postgis psql -U argos -d argos -c \
  "UPDATE argos.fwi_daily SET fwi_date = to_date(substring(filename from 'fwi_([0-9]{4}-[0-9]{2}-[0-9]{2})'), 'YYYY-MM-DD') WHERE fwi_date IS NULL;"
