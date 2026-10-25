#!/usr/bin/env python3
# ARGOS FWI field raster ingestion (v0.3.0 candidate)
# Pulls the native EFFIS raster (Copernicus EMS, Meteo-France ~10 km grid)
# for Kefalonia via WMS GetMap: headline FWI plus ISI and DC sub-indices.
# Honesty contract: we proxy the real EFFIS cells, no interpolation. Blocky
# IS honest; the UI vnote must state the ~10 km grid and the EFFIS class
# legend, and that FWI is a weather-fire index, not ignition probability.
#
# Usage:  python3 argos_fwi_field.py --outdir /opt/argos/field
# Cron:   daily 03:45 UTC (after fwi_cron at 03:30). EFFIS publishes the new
#         model day in the afternoon UTC; a same-day miss falls back to
#         yesterday's raster and stamps fwi_date accordingly.
import argparse, json, os, sys, time, urllib.request, datetime

BBOX = {"lat_min": 38.03, "lat_max": 38.55, "lon_min": 20.28, "lon_max": 20.88}
W, H = 240, 208  # ~4 px per EFFIS cell; no fake detail
WMS = ("https://maps.effis.emergency.copernicus.eu/effis?SERVICE=WMS"
       "&VERSION=1.1.1&REQUEST=GetMap&STYLES=default&FORMAT=image/png"
       "&TRANSPARENT=true&SRS=EPSG:4326"
       "&BBOX=20.28,38.03,20.88,38.55&WIDTH=%d&HEIGHT=%d" % (W, H))
LAYERS = {"fwi": "mf010.fwi", "isi": "mf010.isi", "dc": "mf010.dc"}
MIN_BYTES = 800  # an empty transparent frame is ~300 bytes; real data > 1 KB

def fetch(layer, day):
    url = WMS + "&LAYERS=" + layer + "&TIME=" + day
    req = urllib.request.Request(url, headers={"User-Agent": "ARGOS-kefalonia/0.3"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    got = {}
    used_day = today
    t0 = time.time()
    for name, layer in LAYERS.items():
        blob = fetch(layer, today)
        if len(blob) < MIN_BYTES:
            blob = fetch(layer, yesterday)
            used_day = yesterday
        if len(blob) < MIN_BYTES:
            print("FAIL: %s empty for %s and %s" % (name, today, yesterday)); sys.exit(1)
        got[name] = blob

    for name, blob in got.items():
        with open(os.path.join(args.outdir, "fwi_field_%s.png" % name), "wb") as f:
            f.write(blob)

    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fwi_date": used_day,
        "source": "Copernicus EMS / EFFIS (Meteo-France)",
        "grid": "EFFIS ~10 km",
        "bbox": BBOX, "px": {"w": W, "h": H},
        "layers": sorted(LAYERS.keys()),
        "fallback_to_yesterday": used_day != today,
        "fetch_seconds": round(time.time() - t0, 2),
        "bytes": {k: len(v) for k, v in got.items()},
    }
    with open(os.path.join(args.outdir, "fwi_field.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("OK: fwi/isi/dc rasters for %s (%s), %ss" % (
        used_day, ", ".join("%s=%dB" % (k, len(v)) for k, v in got.items()),
        meta["fetch_seconds"]))

if __name__ == "__main__":
    main()
