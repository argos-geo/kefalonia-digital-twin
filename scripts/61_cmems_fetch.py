#!/usr/bin/env python3
# T46: CMEMS waves + currents for the Kefalonia bbox, nearest wet cell per curated beach -> CSV for psql load.
# Particle layer: also dump the full currents grid (all wet cells, all times) -> /tmp/marine_grid.csv for argos.marine_grid.
import csv, datetime as dt
import numpy as np
import copernicusmarine as cm

BBOX = dict(minimum_longitude=20.30, maximum_longitude=20.90,
            minimum_latitude=38.00, maximum_latitude=38.60)
NOW = dt.datetime.now(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
START = (NOW - dt.timedelta(hours=6)).isoformat()
END = (NOW + dt.timedelta(days=5)).isoformat()

print('fetch waves', START, '->', END)
ds_w = cm.open_dataset(dataset_id='cmems_mod_med_wav_anfc_4.2km_PT1H-i',
                 variables=['VHM0', 'VMXL', 'VMDR', 'VTM10', 'VSDX', 'VSDY'],
                 start_datetime=START, end_datetime=END, **BBOX)
print('fetch currents')
ds_c = cm.open_dataset(dataset_id='cmems_mod_med_phy-cur_anfc_4.2km-2D_PT1H-m',
                 variables=['uo', 'vo'],
                 start_datetime=START, end_datetime=END, **BBOX)
print('waves times:', ds_w.sizes['time'], '| currents times:', ds_c.sizes['time'])

# Real CMEMS run cycle: MEDWAM4 runs once daily at 12:00 UTC; the published hourly series starts
# the next day at 01:00 (init + 13 h) and runs +126 h. So the cycle is the most recent 12:00 UTC
# strictly before the first valid time. Documented in the Bible; if CMEMS changes cadence this
# mislabels by at most 24 h and the popup age is still honest.
t0 = dt.datetime.strptime(str(ds_w.time.values[0])[:19], '%Y-%m-%dT%H:%M:%S')
run = t0.replace(hour=12, minute=0)
if run >= t0:
    run -= dt.timedelta(days=1)
RUN_TS = run.isoformat()
print('model run cycle:', RUN_TS)

def nearest(ds, refvar, blat, blon):
    a = ds[refvar].isel(time=0).values
    ok = np.isfinite(a)
    ilat, ilon = np.where(ok)
    if len(ilat) == 0:
        return None
    lat = ds.latitude.values
    lon = ds.longitude.values
    dla = (lat[ilat] - blat) * 111.0
    dlo = (lon[ilon] - blon) * 111.0 * np.cos(np.radians(blat))
    k = int(np.argmin(dla * dla + dlo * dlo))
    return (float(lat[ilat[k]]), float(lon[ilon[k]]),
            int(round(1000 * float(np.hypot(dla[k], dlo[k])))), ilat[k], ilon[k])

def fv(x):
    return '' if not np.isfinite(x) else round(float(x), 4)

rows = 0
with open('/tmp/marine_forecast.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['beach_osm_id', 'valid_time', 'vhm0', 'vmxl', 'vmdr', 'vtm10',
                'cur_u', 'cur_v', 'cur_speed', 'stokes_x', 'stokes_y',
                'cell_lon', 'cell_lat', 'cell_dist_m', 'cmems_run'])
    for b in csv.DictReader(open('/tmp/beaches.csv')):
        blat, blon = float(b['lat']), float(b['lon'])
        cw = nearest(ds_w, 'VHM0', blat, blon)
        cc = nearest(ds_c, 'uo', blat, blon)
        if cw is None or cc is None:
            print('NO WET CELL:', b['name'])
            continue
        for t in range(ds_w.sizes['time']):
            tc = min(t, ds_c.sizes['time'] - 1)
            u = ds_c['uo'].isel(time=tc).values[cc[3], cc[4]]
            v = ds_c['vo'].isel(time=tc).values[cc[3], cc[4]]
            g = lambda var: ds_w[var].isel(time=t).values[cw[3], cw[4]]
            w.writerow([b['osm_id'], str(ds_w.time.values[t])[:19],
                        fv(g('VHM0')), fv(g('VMXL')), fv(g('VMDR')), fv(g('VTM10')),
                        fv(u), fv(v), fv(np.hypot(u, v)),
                        fv(g('VSDX')), fv(g('VSDY')), cw[1], cw[0], cw[2], RUN_TS])
            rows += 1
print('rows written:', rows)

# Particle layer grid dump: every wet currents cell, every forecast hour.
grows = 0
with open('/tmp/marine_grid.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['valid_time', 'lat', 'lon', 'uo', 'vo'])
    glat = ds_c.latitude.values
    glon = ds_c.longitude.values
    for t in range(ds_c.sizes['time']):
        uu = ds_c['uo'].isel(time=t).values
        vv = ds_c['vo'].isel(time=t).values
        ok = np.isfinite(uu) & np.isfinite(vv)
        ilat, ilon = np.where(ok)
        vt = str(ds_c.time.values[t])[:19]
        for k in range(len(ilat)):
            w.writerow([vt, round(float(glat[ilat[k]]), 4), round(float(glon[ilon[k]]), 4),
                        fv(uu[ilat[k], ilon[k]]), fv(vv[ilat[k], ilon[k]])])
        grows += len(ilat)
print('grid rows written:', grows)