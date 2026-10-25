#!/usr/bin/env python3
# ARGOS earthquake feed ingestion (v0.3.0)
# EMSC-CSEM SeismicPortal FDSNWS-event, rolling 30-day window, M>=2.5,
# Ionian box around Kefalonia. Writes ONE JSON served via Caddy /field/.
# Honesty contract: informational layer, NOT official warning; events are
# agency-reported (auth field: NOA, THE, EMSC...). Attribution mandatory:
# Credit: EMSC-CSEM SeismicPortal, https://www.seismicportal.eu (CC BY 4.0).
#
# Usage:  python3 argos_quakes_fetch.py --outdir /opt/argos/field
# Cron:   */10 * * * * UTC. Output: quakes.json
import argparse, json, os, sys, time, urllib.request, datetime

BOX = {"lat_min": 36.8, "lat_max": 39.5, "lon_min": 19.3, "lon_max": 21.9}
MIN_MAG = 2.5
DAYS = 30

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    end = datetime.date.today() + datetime.timedelta(days=1)
    start = end - datetime.timedelta(days=DAYS)
    url = ("https://www.seismicportal.eu/fdsnws/event/1/query"
           "?starttime=%s&endtime=%s&minmagnitude=%s"
           "&minlatitude=%s&maxlatitude=%s&minlongitude=%s&maxlongitude=%s"
           "&format=json&limit=500&orderby=time-desc" % (
               start.isoformat(), end.isoformat(), MIN_MAG,
               BOX["lat_min"], BOX["lat_max"], BOX["lon_min"], BOX["lon_max"]))
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "ARGOS-kefalonia/0.3"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())

    feats = []
    for f in d.get("features", []):
        p = f.get("properties", {})
        c = f.get("geometry", {}).get("coordinates", [None, None])
        if c[0] is None or p.get("mag") is None:
            continue
        feats.append({
            "id": p.get("unid") or f.get("id"),
            "time": p.get("time"),
            "mag": p.get("mag"),
            "magtype": p.get("magtype"),
            "depth_km": p.get("depth"),
            "lon": c[0], "lat": c[1],
            "region": p.get("flynn_region"),
            "auth": p.get("auth"),
        })
    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "window_days": DAYS, "min_mag": MIN_MAG, "bbox": BOX,
        "count": len(feats),
        "source": "EMSC-CSEM SeismicPortal (CC BY 4.0)",
        "events": feats,
    }
    path = os.path.join(args.outdir, "quakes.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print("OK: %d events (%d days, M>=%s), %ss, wrote %s" % (
        len(feats), DAYS, MIN_MAG, round(time.time() - t0, 2), path))

if __name__ == "__main__":
    main()
