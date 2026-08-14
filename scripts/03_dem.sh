#!/usr/bin/env bash
# ARGOS T13 — DEM pipeline: Copernicus 30m -> clip -> slope/aspect -> PostGIS + MinIO
set -e
cd "$(dirname "$0")/.."
mkdir -p data && cd data
wget -nc -q https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N38_00_E020_00_DEM/Copernicus_DSM_COG_10_N38_00_E020_00_DEM.tif
wget -nc -q https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N37_00_E020_00_DEM/Copernicus_DSM_COG_10_N37_00_E020_00_DEM.tif
gdalwarp -te 20.30 37.95 20.90 38.55 -of COG -co COMPRESS=DEFLATE \
  Copernicus_DSM_COG_10_N38_00_E020_00_DEM.tif \
  Copernicus_DSM_COG_10_N37_00_E020_00_DEM.tif kefalonia_dem_30m.tif
gdaldem slope  kefalonia_dem_30m.tif kefalonia_slope.tif  -of COG
gdaldem aspect kefalonia_dem_30m.tif kefalonia_aspect.tif -of COG
cd ..
docker exec argos-postgis psql -U argos -d argos -c "CREATE EXTENSION IF NOT EXISTS postgis_raster SCHEMA public;"
for layer in dem slope aspect; do
  raster2pgsql -s 4326 -I -C -t 100x100 data/kefalonia_${layer}*.tif argos.${layer} \
    | docker exec -i argos-postgis psql -U argos -d argos
done
echo "DEM pipeline complete. Verify: SELECT max((ST_SummaryStats(rast)).max) FROM argos.dem; -- expect ~1621"
