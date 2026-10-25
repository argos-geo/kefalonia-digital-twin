#!/usr/bin/env python3
# ARGOS weather field grid ingestion v2 (v0.3.0)
# ~2 km Open-Meteo lattice over Kefalonia -> land-masked, colorized PNG.
# v2: island land mask (land full colour, sea dimmed) + high-contrast ramp
# tuned for the Ionian 5-30 C band. Mask comes from argos.municipalities
# union, exported once to kefalonia_land.geojson (see Bible).
# Honesty contract: ~2 km model-downscaled cells, no interpolation; the sea
# is dimmed but still shown (air temperature over sea is real model data).
#
# Usage:  python3 argos_weather_field.py --outdir /opt/argos/field
# Cron:   hourly at :15 UTC. Output: weather_field.png + weather_field.json
import argparse, json, os, sys, time, urllib.request

BBOX = {"lat_min": 38.03, "lat_max": 38.58, "lon_min": 20.28, "lon_max": 20.88}
STEP = 0.025  # ~2 km, Open-Meteo native downscaled resolution
VARS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
TZ = "Europe/Athens"
MASK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kefalonia_land.geojson")
LAND_ALPHA = 215
SEA_ALPHA = 70

# v2 ramp (C): perceptual blue-teal-green-gold-orange-red, contrast where
# Kefalonia actually lives (10-28 C)
T_STOPS = [(-5, (56, 76, 168)), (0, (74, 116, 202)), (5, (96, 158, 222)),
           (10, (110, 190, 205)), (13, (130, 205, 155)), (16, (185, 215, 110)),
           (19, (235, 215, 85)), (22, (242, 185, 65)), (25, (238, 145, 50)),
           (28, (225, 105, 48)), (32, (205, 65, 55)), (36, (175, 40, 70)),
           (40, (140, 20, 90))]

def ramp(v, stops):
    if v is None:
        return (0, 0, 0, 0)
    if v <= stops[0][0]:
        r, g, b = stops[0][1]; return (r, g, b, LAND_ALPHA)
    if v >= stops[-1][0]:
        r, g, b = stops[-1][1]; return (r, g, b, LAND_ALPHA)
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]; v1, c1 = stops[i + 1]
        if v0 <= v <= v1:
            f = (v - v0) / (v1 - v0)
            return (round(c0[0] + f * (c1[0] - c0[0])),
                    round(c0[1] + f * (c1[1] - c0[1])),
                    round(c0[2] + f * (c1[2] - c0[2])), LAND_ALPHA)
    return (0, 0, 0, 0)

def load_mask(W, H, bbox):
    # rasterize land polygon to a W x H mask (1 = land). Missing mask = all land.
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    lats, lat = [], BBOX["lat_min"]
    while lat <= BBOX["lat_max"] + 1e-9:
        lats.append(round(lat, 3)); lat += STEP
    lons, lon = [], BBOX["lon_min"]
    while lon <= BBOX["lon_max"] + 1e-9:
        lons.append(round(lon, 3)); lon += STEP
    pts = [(la, lo) for la in lats for lo in lons]

    url = ("https://api.open-meteo.com/v1/forecast?latitude="
           + ",".join(str(p[0]) for p in pts)
           + "&longitude=" + ",".join(str(p[1]) for p in pts)
           + "&current=" + VARS + "&timezone=" + TZ)
    t0 = time.time()
    with urllib.request.urlopen(url, timeout=120) as r:
        data = json.loads(r.read().decode())
    if not isinstance(data, list):
        data = [data]
    if len(data) != len(pts):
        print("FAIL: cells mismatch %d vs %d" % (len(data), len(pts))); sys.exit(1)

    W, H = len(lons), len(lats)
    mask = load_mask(W, H, BBOX)
    temps = []
    cells = {}
    for i, d in enumerate(data):
        cur = d.get("current", {})
        la, lo = pts[i]
        cells["%.3f,%.3f" % (la, lo)] = cur
        t = cur.get("temperature_2m")
        if t is not None:
            temps.append(t)

    try:
        from PIL import Image
    except ImportError:
        print("FAIL: Pillow not installed"); sys.exit(1)
    img = Image.new("RGBA", (W, H))
    px = img.load()
    land_cells = 0
    for iy, la in enumerate(lats):
        for ix, lo in enumerate(lons):
            cur = cells["%.3f,%.3f" % (la, lo)]
            r, g, b, a = ramp(cur.get("temperature_2m"), T_STOPS)
            if mask is not None and not mask[ix, H - 1 - iy]:
                a = SEA_ALPHA
            else:
                land_cells += 1
            px[ix, H - 1 - iy] = (r, g, b, a)

    png_path = os.path.join(args.outdir, "weather_field.png")
    img.save(png_path, optimize=True)

    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "Open-Meteo forecast API (CC BY 4.0)",
        "model": "ECMWF IFS / ICON blend, downscaled ~2 km",
        "cell_deg": STEP,
        "bbox": BBOX,
        "grid": {"w": W, "h": H},
        "masked": mask is not None,
        "land_cells": land_cells,
        "fetch_seconds": round(time.time() - t0, 2),
        "temp_min": min(temps) if temps else None,
        "temp_max": max(temps) if temps else None,
        "cells": len(pts),
    }
    json_path = os.path.join(args.outdir, "weather_field.json")
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=1)
    print("OK: %d cells (%d land), %dx%d, temp %s..%s C, fetch %ss" % (
        len(pts), land_cells, W, H, meta["temp_min"], meta["temp_max"], meta["fetch_seconds"]))

if __name__ == "__main__":
    main()
