#!/usr/bin/env python3
# ARGOS FWI field raster ingestion v2 (v0.3.0)
# Native EFFIS raster (Copernicus EMS, Meteo-France ~10 km) via WMS,
# land-masked: FWI over sea is meaningless, so sea becomes transparent and
# the island shape reads. Cells stay crisp (map renders nearest-neighbour).
# Honesty contract: real EFFIS cells exactly as published, no interpolation.
#
# Usage:  python3 argos_fwi_field.py --outdir /opt/argos/field
# Cron:   daily 03:45 UTC (after fwi_cron 03:30). Same-day miss falls back
#         to yesterday and stamps fwi_date + fallback_to_yesterday.
import argparse, json, os, sys, time, urllib.request, datetime

BBOX = {"lat_min": 38.03, "lat_max": 38.55, "lon_min": 20.28, "lon_max": 20.88}
W, H = 240, 208  # ~4 px per EFFIS cell; no fake detail
WMS = ("https://maps.effis.emergency.copernicus.eu/effis?SERVICE=WMS"
       "&VERSION=1.1.1&REQUEST=GetMap&STYLES=default&FORMAT=image/png"
       "&TRANSPARENT=true&SRS=EPSG:4326"
       "&BBOX=20.28,38.03,20.88,38.55&WIDTH=%d&HEIGHT=%d" % (W, H))
LAYERS = {"fwi": "mf010.fwi", "isi": "mf010.isi", "dc": "mf010.dc"}
MIN_BYTES = 800
MASK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kefalonia_land.geojson")

def fetch(layer, day):
    url = WMS + "&LAYERS=" + layer + "&TIME=" + day
    req = urllib.request.Request(url, headers={"User-Agent": "ARGOS-kefalonia/0.3"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

def load_mask(W, H, bbox):
    from PIL import Image, ImageDraw
    if not os.path.exists(MASK_PATH):
        print("WARN: no mask at %s, rendering without land mask" % MASK_PATH)
        return None
    with open(MASK_PATH) as f:
        gj = json.load(f)
    polys = []
    if gj["type"] == "Polygon":
        polys = [gj["coordinates"]]
    elif gj["type"] == "MultiPolygon":
        polys = gj["coordinates"]
    def px(coord):
        lon, lat = coord[0], coord[1]
        x = (lon - bbox["lon_min"]) / (bbox["lon_max"] - bbox["lon_min"]) * W
        y = (bbox["lat_max"] - lat) / (bbox["lat_max"] - bbox["lat_min"]) * H
        return (x, y)
    m = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(m)
    for poly in polys:
        dr.polygon([px(c) for c in poly[0]], fill=1)
        for hole in poly[1:]:
            dr.polygon([px(c) for c in hole], fill=0)
    return m.load()

def apply_mask(png_path, mask):
    from PIL import Image
    im = Image.open(png_path).convert("RGBA")
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a > 0 and not mask[x, y]:
                px[x, y] = (r, g, b, 0)
    im.save(png_path, optimize=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    mask = load_mask(W, H, BBOX)
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
        p = os.path.join(args.outdir, "fwi_field_%s.png" % name)
        with open(p, "wb") as f:
            f.write(blob)
        if mask is not None:
            apply_mask(p, mask)

    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "fwi_date": used_day,
        "source": "Copernicus EMS / EFFIS (Meteo-France)",
        "grid": "EFFIS ~10 km",
        "bbox": BBOX, "px": {"w": W, "h": H},
        "layers": sorted(LAYERS.keys()),
        "masked": mask is not None,
        "fallback_to_yesterday": used_day != today,
        "fetch_seconds": round(time.time() - t0, 2),
        "bytes": {k: len(v) for k, v in got.items()},
    }
    with open(os.path.join(args.outdir, "fwi_field.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print("OK: fwi/isi/dc masked rasters for %s (%s), %ss" % (
        used_day, ", ".join("%s=%dB" % (k, len(v)) for k, v in got.items()),
        meta["fetch_seconds"]))

if __name__ == "__main__":
    main()
