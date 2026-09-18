#!/usr/bin/env python3
"""Flood v1.1 diagnostic v3. Mirrors committed scripts/09_flashflood.py exactly
(polygon land mask, nan_to_num inside land, temp-tif weights, sea = -5 m),
verifies the T17 checksums, then computes candidate pluvial fields (TWI,
depression depth, TPI 1km) and samples them at known sites. Measurement only."""
import csv
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform, transform as warp_transform
from rasterio.features import rasterize
from pysheds.grid import Grid
from scipy.ndimage import uniform_filter
import geopandas as gpd
from sqlalchemy import create_engine

if not hasattr(np, 'in1d'):
    np.in1d = np.isin  # pysheds 0.5 + numpy 2.x (T17 gotcha)

BBOX = (20.30, 37.95, 20.90, 38.55)
HYDRO_BUF = 0.05
DST_RES = 30.0
EPSG_UTM = 32634
NODATA = -9999.0
RAD = 20  # 600 m at 30 m, same protocol as the T17 storm validation

print('=== flood v1.1 diagnostic v3 (polygon land mask) ===')

# ---------- 1-2. DEM + REAL land mask (committed engine route) ----------
src = rasterio.open('data/kefalonia_dem_30m.tif')
hb = (BBOX[0]-HYDRO_BUF, BBOX[1]-HYDRO_BUF, BBOX[2]+HYDRO_BUF, BBOX[3]+HYDRO_BUF)
t_h, w_h, h_h = calculate_default_transform(src.crs, EPSG_UTM, src.width, src.height, *hb, resolution=DST_RES)
dem = np.full((h_h, w_h), np.nan, 'float32')
reproject(rasterio.band(src, 1), dem, src_transform=src.transform, src_crs=src.crs,
          dst_transform=t_h, dst_crs=EPSG_UTM, resampling=Resampling.bilinear)

eng = create_engine('postgresql+psycopg://argos:argos_dev_password@localhost:5432/argos')
isl = gpd.read_postgis(
    "SELECT ST_Transform(ST_UnaryUnion(ST_Collect(ST_MakeValid(way))), 32634) AS geom "
    "FROM planet_osm_polygon WHERE boundary='administrative' AND admin_level='7'",
    eng, geom_col='geom')
land = rasterize(isl.geometry, out_shape=(h_h, w_h), transform=t_h,
                 fill=0, default_value=1, dtype='uint8').astype(bool)

dem_sea = np.where(land, np.nan_to_num(dem, nan=0.0), -5.0).astype('float32')

with rasterio.open('data/_f11_dem_utm.tif', 'w', driver='GTiff', height=h_h, width=w_h,
                   count=1, dtype='float32', crs=EPSG_UTM, transform=t_h, nodata=NODATA) as d:
    d.write(dem_sea, 1)

# ---------- 3. Hydrology ----------
grid = Grid.from_raster('data/_f11_dem_utm.tif')
dem_r = grid.read_raster('data/_f11_dem_utm.tif')
filled = grid.fill_depressions(dem_r)  # kept this time: depression-depth source
f = grid.resolve_flats(filled)
fdir = grid.flowdir(f, routing='d8')
acc = np.asarray(grid.accumulation(fdir, routing='d8')) * DST_RES**2

# ---------- 4. Burn term (same input tif as v1: no EFFIS swap) ----------
risk_cls = rasterio.open('data/kefalonia_wildfire_risk_class.tif')
burn_src = (risk_cls.read(1) >= 3).astype('float32')
burn = np.zeros((h_h, w_h), 'float32')
reproject(burn_src, burn, src_transform=risk_cls.transform, src_crs=risk_cls.crs,
          dst_transform=t_h, dst_crs=EPSG_UTM, resampling=Resampling.nearest)
with rasterio.open('data/_f11_burn.tif', 'w', driver='GTiff', height=h_h, width=w_h,
                   count=1, dtype='float32', crs=EPSG_UTM, transform=t_h, nodata=NODATA) as d:
    d.write(burn, 1)
burn_r = grid.read_raster('data/_f11_burn.tif')  # weights must be Raster too
acc_burn = np.asarray(grid.accumulation(fdir, routing='d8', weights=burn_r)) * DST_RES**2
burn_frac = np.divide(acc_burn, acc, out=np.zeros_like(acc), where=acc > 0)
burn_frac = np.clip(burn_frac / 0.30, 0, 1)

# ---------- 5-6. Factors + v1 risk, verbatim ----------
drainage = np.clip((np.log10(acc + 1) - 3) / 4.0, 0, 1)
gy, gx = np.gradient(dem_sea, DST_RES)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
receiving = np.clip(1 - slope_deg / 10.0, 0, 1)
risk_v1 = 100 * (0.45*drainage + 0.30*receiving*drainage + 0.25*burn_frac*drainage)
edge = 5
risk_v1[:edge, :] = risk_v1[-edge:, :] = risk_v1[:, :edge] = risk_v1[:, -edge:] = np.nan
risk_v1[~land] = np.nan
risk_v1 = np.clip(risk_v1, 0, 100)

# ---------- checksums vs T17 (ALL must match before any field is believed) ----------
print('CHECKSUM grid: %dx%d px (T17: 2053x2599, axis order swapped)' % (h_h, w_h))
print('CHECKSUM DEM peak: %.0f m (T17: 1619-1621)' % np.nanmax(dem))
print('CHECKSUM land cells: %d = %.0f km2 (T17: 866264 = 780)' % (int(land.sum()), land.sum()*DST_RES**2/1e6))
am = acc[land]
print('CHECKSUM upslope m2: p50 %.0f p90 %.0f p99 %.0f (T17: 3600 / 27900 / 1780000)' % tuple(np.percentile(am, [50, 90, 99])))
rl = risk_v1[np.isfinite(risk_v1)]
print('CHECKSUM v1 risk: p50 %.1f p90 %.1f p99 %.1f max %.1f (T17: 7.6 / 24.8 / 64.4 / 100.0)' % tuple(np.percentile(rl, [50, 90, 99, 100])))
klass = np.digitize(risk_v1, [20, 40, 60, 80])
cls = {int(k): int(v) for k, v in zip(*np.unique(klass[np.isfinite(risk_v1)], return_counts=True))}
print('CHECKSUM v1 classes: %s (T17: {0: 739275, 1: 91275, 2: 24344, 3: 7983, 4: 3387})' % cls)

# ---------- candidate pluvial fields ----------
a_spec = (acc + DST_RES**2) / DST_RES                      # specific catchment area, m
tanb = np.tan(np.radians(np.maximum(slope_deg, 0.5)))      # slope floor 0.5 deg
twi = np.log(a_spec / tanb)
twi[~land] = np.nan

dep = np.asarray(filled) - dem_sea                         # 0 where the DEM drains freely
dep = np.where(land & (dep > 0), dep, 0.0)
dep[:edge, :] = dep[-edge:, :] = dep[:, :edge] = dep[:, -edge:] = 0.0

dem0 = np.nan_to_num(dem, nan=0.0)
win = 33                                                   # ~1 km window
wsum = uniform_filter(land.astype('float32'), size=win, mode='nearest')
dsum = uniform_filter(np.where(land, dem0, 0.0).astype('float32'), size=win, mode='nearest')
tpi = np.where(wsum > 0, dem0 - dsum / np.maximum(wsum, 1e-6), np.nan)  # negative = locally low
tpi[~land] = np.nan

for nm, arr in [('TWI', twi), ('dep_depth', dep), ('TPI_1km', tpi)]:
    v = arr[np.isfinite(arr)]
    print('FIELD %-9s land p50 %6.2f p90 %6.2f p99 %6.2f max %7.2f' % (nm, *np.percentile(v, [50, 90, 99, 100])))
print('FIELD dep_depth cells >0.3 m: %d (%.2f%% of land)' % (int((dep > 0.3).sum()), 100 * float((dep > 0.3).mean())))

# ---------- site sampling (600 m circles; dem=min, tpi=min, rest=max) ----------
sites = [
    ('Livadi wetland (Paliki)', 20.424360, 38.257592),
    ('Koutavos head (Argostoli)', 20.508508, 38.164807),
    ('Omala valley', 20.587092, 38.168156),
    ('Ainos summit', 20.671000, 38.136800),
]
with open('data/_flood_sites.csv') as fh:
    for row in csv.reader(fh):
        if len(row) >= 4:
            sites.append(('db: %s/%s' % (row[0], row[1]), float(row[2]), float(row[3])))

inv = ~t_h
yy, xx = np.ogrid[:h_h, :w_h]
print('\nSITES (600 m circle; dem=min, tpi=min, rest=max)')
for nm, lon, lat in sites:
    x, y = warp_transform('EPSG:4326', 'EPSG:%d' % EPSG_UTM, [lon], [lat])
    c, r = inv * (x[0], y[0])
    r, c = int(round(r)), int(round(c))
    if not (edge <= r < h_h - edge and edge <= c < w_h - edge):
        print('%-28s %.6f,%.6f OUT OF GRID' % (nm, lon, lat)); continue
    circle = ((yy - r)**2 + (xx - c)**2 <= RAD**2) & land
    if circle.sum() == 0:
        print('%-28s %.6f,%.6f OFF LAND (sea/lagoon mask)' % (nm, lon, lat)); continue
    def mx(a): return float(np.nanmax(np.where(circle, a, np.nan)))
    def mn(a): return float(np.nanmin(np.where(circle, a, np.nan)))
    print('%-28s dem %6.1f recv %4.2f acc_km2 %6.3f twi %5.1f dep %4.2f tpi %6.1f v1risk %5.1f' % (
        nm, mn(dem), mx(receiving), mx(acc)/1e6, mx(twi), mx(dep), mn(tpi), mx(risk_v1)))
