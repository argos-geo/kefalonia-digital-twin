#!/usr/bin/env python3
# ARGOS weather field grid ingestion (v0.3.0 candidate)
# Fetches a ~2 km lattice of current weather over Kefalonia from Open-Meteo
# (one HTTP call), stores JSON metadata + a colorized RGBA PNG field.
# Honesty contract: PNG resolution = sampled lattice resolution. The vnote in
# the UI must state the ~2 km model-downscaled cell size. No smoothing beyond
# bilinear upscaling for display.
#
# Usage:  python3 argos_weather_field.py --outdir /opt/argos/field
# Cron:   hourly. Output: weather_field.png + weather_field.json in outdir.
import argparse, json, os, sys, time, urllib.request

BBOX = {"lat_min": 38.03, "lat_max": 38.58, "lon_min": 20.28, "lon_max": 20.88}
STEP = 0.025  # ~2 km; Open-Meteo downscales to ~1-2 km so this is native-ish
VARS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
TZ = "Europe/Athens"

# temperature ramp (C): stops chosen for Ionian range -5..40
T_STOPS = [(-5, (49, 54, 149)), (0, (67, 106, 190)), (5, (90, 160, 210)),
           (10, (140, 200, 160)), (15, (230, 230, 130)), (20, (245, 190, 80)),
           (25, (240, 140, 60)), (30, (220, 90, 50)), (35, (190, 50, 50)),
           (40, (140, 20, 60))]

def ramp(v, stops):
    if v is None:
        return (0, 0, 0, 0)
    if v <= stops[0][0]:
        r, g, b = stops[0][1]; return (r, g, b, 200)
    if v >= stops[-1][0]:
        r, g, b = stops[-1][1]; return (r, g, b, 200)
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]; v1, c1 = stops[i + 1]
        if v0 <= v <= v1:
            f = (v - v0) / (v1 - v0)
            r = round(c0[0] + f * (c1[0] - c0[0]))
            g = round(c0[1] + f * (c1[1] - c0[1]))
            b = round(c0[2] + f * (c1[2] - c0[2]))
            return (r, g, b, 200)
    return (0, 0, 0, 0)

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
        print("FAIL: Pillow not installed (pip install pillow)"); sys.exit(1)
    img = Image.new("RGBA", (W, H))
    px = img.load()
    for iy, la in enumerate(lats):
        for ix, lo in enumerate(lons):
            cur = cells["%.3f,%.3f" % (la, lo)]
            # PNG row 0 = top (max lat)
            px[ix, H - 1 - iy] = ramp(cur.get("temperature_2m"), T_STOPS)

    png_path = os.path.join(args.outdir, "weather_field.png")
    img.save(png_path, optimize=True)

    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "Open-Meteo forecast API (CC BY 4.0)",
        "model": "ECMWF IFS / ICON blend, downscaled ~2 km",
        "cell_deg": STEP,
        "bbox": BBOX,
        "grid": {"w": W, "h": H, "lats": lats, "lons": lons},
        "fetch_seconds": round(time.time() - t0, 2),
        "temp_min": min(temps) if temps else None,
        "temp_max": max(temps) if temps else None,
        "cells": len(pts),
    }
    json_path = os.path.join(args.outdir, "weather_field.json")
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=1)
    print("OK: %d cells, %dx%d grid, temp %s..%s C, fetch %ss" % (
        len(pts), W, H, meta["temp_min"], meta["temp_max"], meta["fetch_seconds"]))
    print("wrote:", png_path, json_path)

if __name__ == "__main__":
    main()
