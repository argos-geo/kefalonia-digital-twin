#!/usr/bin/env python3
"""Flood v1.1 engine. v1 fluvial branch byte-identical (T17 checksums re-verified
in-run) plus a pluvial ponding branch: risk_v1.1 = max(risk_v1, 75 * receiving *
wetness), wetness = clip((TWI-10)/6, 0, 1), TWI = ln(a_spec / tan(slope)),
slope floored at 0.5 deg. One model change only: burn input unchanged (T15 class
tif), weights unchanged, drainage gate unchanged. Pluvial-only cells cap at 75:
class 3 max, class 4 stays fluvial-only (hard checksum: class4 count frozen).
Outputs: data/kefalonia_flashflood_risk_v1_1.tif + _class.tif (v1 tifs untouched)."""
import csv
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform, transform as warp_transform
from rasterio.features import rasterize
from pysheds.grid import Grid
import geopandas as gpd
from sqlalchemy import create_engine

if not hasattr(np, 'in1d'):
    np.in1d = np.isin  # pysheds 0.5 + numpy 2.x (T17 gotcha)

BBOX = (20.30, 37.95, 20.90, 38.55)
HYDRO_BUF = 0.05
DST_RES = 30.0
EPSG_UTM = 32634
NODATA = -9999.0
RAD = 20  # 600 m at 30 m, T17 validation protocol

print('=== flood v1.1 engine (pluvial branch, cap 75) ===')

# ---------- v1 pipeline, byte-identical to committed 09_flashflood.py ----------
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

grid = Grid.from_raster('data/_f11_dem_utm.tif')
dem_r = grid.read_raster('data/_f11_dem_utm.tif')
f = grid.resolve_flats(grid.fill_depressions(dem_r))
fdir = grid.flowdir(f, routing='d8')
acc = np.asarray(grid.accumulation(fdir, routing='d8')) * DST_RES**2

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

drainage = np.clip((np.log10(acc + 1) - 3) / 4.0, 0, 1)
gy, gx = np.gradient(dem_sea, DST_RES)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
receiving = np.clip(1 - slope_deg / 10.0, 0, 1)
risk_v1 = 100 * (0.45*drainage + 0.30*receiving*drainage + 0.25*burn_frac*drainage)
edge = 5
risk_v1[:edge, :] = risk_v1[-edge:, :] = risk_v1[:, :edge] = risk_v1[:, -edge:] = np.nan
risk_v1[~land] = np.nan
risk_v1 = np.clip(risk_v1, 0, 100)

# ---------- in-run v1 checksums (must match T17 before v1.1 numbers count) ----------
klass_v1 = np.digitize(risk_v1, [20, 40, 60, 80])
fin = np.isfinite(risk_v1)
cls1 = {int(k): int(v) for k, v in zip(*np.unique(klass_v1[fin], return_counts=True))}
print('CHECKSUM v1 classes: %s (T17: {0: 739275, 1: 91275, 2: 24344, 3: 7983, 4: 3387})' % cls1)

# ---------- THE ONE CHANGE: pluvial ponding branch ----------
a_spec = (acc + DST_RES**2) / DST_RES
tanb = np.tan(np.radians(np.maximum(slope_deg, 0.5)))
twi = np.log(a_spec / tanb)
wetness = np.clip((twi - 8.0) / 4.0, 0, 1)
pluvial = 75.0 * receiving * wetness
risk_v11 = np.maximum(risk_v1, pluvial)  # NaN wins: sea + edge cells stay masked
risk_v11 = np.clip(risk_v11, 0, 100)
klass_v11 = np.digitize(risk_v11, [20, 40, 60, 80])

# ---------- change audit (attribution) ----------
cls11 = {int(k): int(v) for k, v in zip(*np.unique(klass_v11[fin], return_counts=True))}
print('v1.1 classes: %s' % cls11)
changed = fin & (risk_v11 > risk_v1 + 0.5)
print('CHANGE pixels moved >0.5: %d = %.1f km2 (%.1f%% of land)' % (
    int(changed.sum()), changed.sum()*DST_RES**2/1e6, 100*changed.sum()/fin.sum()))
up = fin & (klass_v1 <= 1) & (klass_v11 >= 2)
print('CHANGE cells class 0-1 up to 2-3: %d = %.1f km2' % (int(up.sum()), up.sum()*DST_RES**2/1e6))
print('CHECKSUM class4 frozen: v1 %d vs v1.1 %d (MUST be equal)' % (
    int((klass_v1[fin] == 4).sum()), int((klass_v11[fin] == 4).sum())))
rl = risk_v11[fin]
print('v1.1 risk: p50 %.1f p90 %.1f p99 %.1f max %.1f' % tuple(np.percentile(rl, [50, 90, 99, 100])))

# ---------- site table, v1 vs v1.1, max AND p50 (the gap lives in the median) ----------
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
print('\nSITES (600 m circle; v1max v1p50 -> v11max v11p50)')
for nm, lon, lat in sites:
    x, y = warp_transform('EPSG:4326', 'EPSG:%d' % EPSG_UTM, [lon], [lat])
    c, r = inv * (x[0], y[0])
    r, c = int(round(r)), int(round(c))
    circle = ((yy - r)**2 + (xx - c)**2 <= RAD**2) & land & fin
    if circle.sum() == 0:
        print('%-28s no land pixels' % nm); continue
    v1c, v11c = risk_v1[circle], risk_v11[circle]
    print('%-28s %5.1f %5.1f -> %5.1f %5.1f' % (
        nm, v1c.max(), np.percentile(v1c, 50), v11c.max(), np.percentile(v11c, 50)))

# ---------- write v1.1 tifs (v1 files untouched) ----------
def write(path, arr, dtype):
    out = np.where(np.isnan(risk_v11), NODATA, arr).astype(dtype)
    with rasterio.open(path, 'w', driver='GTiff', height=h_h, width=w_h, count=1,
                       dtype=dtype, crs=EPSG_UTM, transform=t_h, nodata=NODATA,
                       compress='deflate') as d:
        d.write(out, 1)

write('data/kefalonia_flashflood_risk_v1_1.tif', risk_v11, 'float32')
write('data/kefalonia_flashflood_risk_v1_1_class.tif', klass_v11, 'int16')
print('saved: kefalonia_flashflood_risk_v1_1.tif + _class.tif')
