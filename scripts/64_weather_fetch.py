# T29 / v0.2.0: Open-Meteo hourly fetch -> CSV stdout (spec section 1.1)
# Attribution duty: "Weather data by Open-Meteo.com" wherever displayed.
import json, sys, urllib.request
POINTS = [(1,38.181,20.489),(2,38.253,20.646),(3,38.461,20.576),(4,38.202,20.437),(5,38.140,20.665)]
HOURLY = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,surface_pressure,cape"
for pid,lat,lon in POINTS:
    elev = "&elevation=1628" if pid==5 else ""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly={HOURLY}&forecast_days=16&timezone=UTC{elev}"
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)
    h = d["hourly"]
    for i,t in enumerate(h["time"]):
        row = [pid, t+":00+00"] + [h[k][i] for k in h if k!="time"]
        print(",".join("" if v is None else str(v) for v in row))
