#!/usr/bin/env bash
# Script 65 (fetch half): EFFIS mf010.fwi daily tiff for the Kefalonia bbox.
# Usage: bash scripts/65_fwi_fetch.sh [YYYY-MM-DD]   (default: today UTC)
# Gotchas: mf010 layers REQUIRE &STYLES= (empty value), else se_xml MissingParameterValue.
# gdalinfo is dev-only (absent on prod VM host); prod verification = DB union stats.
set -euo pipefail
DAY="${1:-$(date -u +%F)}"
OUT="data/fwi/fwi_${DAY}.tif"
URL="https://maps.effis.emergency.copernicus.eu/effis?SERVICE=WMS&REQUEST=GetMap&VERSION=1.1.1&LAYERS=mf010.fwi&STYLES=&FORMAT=image/tiff&SRS=EPSG:4326&BBOX=20.30,37.95,20.90,38.55&WIDTH=240&HEIGHT=240&TIME=${DAY}"
META=$(curl -sS -o "$OUT" -w "%{http_code} %{content_type}" "$URL")
BYTES=$(stat -c%s "$OUT")
echo "HTTP $META | bytes $BYTES | $OUT"
case "$META" in
  "200 image/tiff"*) ;;
  *) echo "FAIL: not a tiff (probably se_xml service exception). Body head:"; head -c 300 "$OUT"; exit 1;;
esac
if [ "$BYTES" -lt 10000 ]; then echo "FAIL: suspiciously small tiff"; exit 1; fi
if command -v gdalinfo >/dev/null; then
  gdalinfo -stats "$OUT" | grep -E "Size is|Minimum=|Maximum=|Mean=|NoData"
else
  echo "gdalinfo absent; DB union stats are the verification"
fi
