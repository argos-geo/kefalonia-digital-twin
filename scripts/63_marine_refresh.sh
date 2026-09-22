#!/bin/bash
# T46/T47 prod: CMEMS marine refresh. Runs on the VM via cron, twice daily after the 06:00/20:00 UTC CMEMS updates.
set -a; . ~/.argos_marine_env; set +a
docker exec argos-postgis psql -U argos -d argos -c "\copy (SELECT osm_id, name, ST_Y(ST_Centroid(geom)) lat, ST_X(ST_Centroid(geom)) lon FROM argos.beaches WHERE curated) TO STDOUT CSV HEADER" > /tmp/beaches.csv || exit 1
~/cmems-venv/bin/python ~/61_cmems_fetch.py >> ~/marine_fetch.log 2>&1 || exit 1
[ "$(wc -l < /tmp/marine_forecast.csv)" -gt 1000 ] || { echo "CSV too small, load aborted" >> ~/marine_fetch.log; exit 1; }
docker exec -i argos-postgis psql -U argos -d argos -c 'TRUNCATE argos.marine_forecast;' || exit 1
docker exec -i argos-postgis psql -U argos -d argos -c "COPY argos.marine_forecast (beach_osm_id,valid_time,vhm0,vmxl,vmdr,vtm10,cur_u,cur_v,cur_speed,stokes_x,stokes_y,cell_lon,cell_lat,cell_dist_m) FROM STDIN WITH CSV HEADER" < /tmp/marine_forecast.csv || exit 1
# v0.0.7 particle layer: full currents grid. Runs after the beach load on purpose: a grid failure must never take the beach pipeline down with it.
if [ -f /tmp/marine_grid.csv ] && [ "$(wc -l < /tmp/marine_grid.csv)" -gt 5000 ]; then
  docker exec -i argos-postgis psql -U argos -d argos -c 'TRUNCATE argos.marine_grid;' \
    && docker exec -i argos-postgis psql -U argos -d argos -c "COPY argos.marine_grid (valid_time,lat,lon,uo,vo) FROM STDIN WITH CSV HEADER" < /tmp/marine_grid.csv \
    || echo "$(date -u +%FT%TZ) grid load failed, beach data unaffected" >> ~/marine_fetch.log
else
  echo "$(date -u +%FT%TZ) grid CSV missing or too small, keeping previous grid" >> ~/marine_fetch.log
fi
