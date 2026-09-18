#!/usr/bin/env python3
"""Flood v1.1 box diagnostic. The pluvial branch moved 108 px because wetness =
clip((TWI-10)/6) was dead for its target population: zero-upslope flat cells cap
at TWI ~8.1. Measures slope/TWI/TPI/dep in three boxes over all land cells and
over field cells (acc < 0.5 km2), plus island flat-land TWI calibration.
Measurement only, no model change."""
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform, transform as warp_transform
from rasterio.features import rasterize
from rasterio.transform import rowcol
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

print('=== flood v1.1 box diagnostic ===')

# ---------- v1 pipeline, byte-identical ----------
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
gy, gx = np.gradient(dem_sea, DST_RES)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
receiving = np.clip(1 - slope_deg / 10.0, 0, 1)
a_spec = (acc + DST_RES**2) / DST_RES
tanb = np.tan(np.radians(np.maximum(slope_deg, 0.5)))
twi = np.log(a_spec / tanb)
dem0 = np.nan_to_num(dem, nan=0.0)
edge = 5

# gate stays armed: land checksum must match T17
print('CHECKSUM land cells: %d (T17: 866264)' % int(land.sum()))
print('ANALYTIC zero-upslope flat-cell TWI cap: %.2f (a_spec 30 m, slope floor 0.5 deg)'
      % np.log(30.0 / np.tan(np.radians(0.5))))

# island flat-land TWI calibration (the pluvial target population)
fin = land.copy()
flat = fin & (receiving > 0.8)
print('ISLAND flat land (recv>0.8): %.1f%% of land; TWI p50 %.2f p90 %.2f p99 %.2f' % (
    100*flat.sum()/fin.sum(), *np.percentile(twi[flat], [50, 90, 99])))

# local lowness over a ~1 km masked window (same as before)
from scipy.ndimage import uniform_filter
wsum = uniform_filter(land.astype('float32'), size=33, mode='nearest')
dsum = uniform_filter(np.where(land, dem0, 0.0).astype('float32'), size=33, mode='nearest')
tpi = np.where(wsum > 0, dem0 - dsum / np.maximum(wsum, 1e-6), np.nan)

# distance to nearest drain (channels >=0.1 km2 upslope, or the sea)
from scipy.ndimage import distance_transform_edt
drain = (acc >= 1e5) | (~land)
dist_m = distance_transform_edt(np.where(drain, 0, 1)) * DST_RES

boxes = [
    ('Livadi fields+marsh', (20.418, 38.252, 20.430, 38.263)),
    ('Argostoli waterfront', (20.484, 38.168, 20.496, 38.180)),
    ('Ainos upper slopes', (20.655, 38.125, 20.680, 38.145)),
]
print('\nBOXES: per box, all land cells then FIELD cells (acc < 0.5 km2)')
for nm, (lon0, lat0, lon1, lat1) in boxes:
    xs, ys = warp_transform('EPSG:4326', 'EPSG:%d' % EPSG_UTM, [lon0, lon1], [lat0, lat1])
    rr, cc = rowcol(t_h, xs, ys)
    r0, r1 = max(0, min(rr)), min(h_h, max(rr) + 1)
    c0, c1 = max(0, min(cc)), min(w_h, max(cc) + 1)
    sub = np.s_[r0:r1, c0:c1]
    m = land[sub]
    for label, mm in [('all  ', m), ('field', m & (acc[sub] < 4.5e5))]:
        if mm.sum() < 10:
            print('%-22s %s n=%d (too few)' % (nm, label, int(mm.sum()))); continue
        print('%-22s %s n=%5d slope50 %4.1f slope90 %4.1f | twi50 %4.1f twi90 %4.1f twi99 %4.1f | tpi10 %6.1f tpi50 %6.1f | dep90 %4.2f | dist50 %4.0f dist90 %4.0f' % (
            nm, label, int(mm.sum()),
            *np.percentile(slope_deg[sub][mm], [50, 90]),
            *np.percentile(twi[sub][mm], [50, 90, 99]),
            *np.percentile(tpi[sub][mm], [10, 50]),
            np.percentile((np.asarray(grid.fill_depressions(dem_r)) - dem_sea)[sub][mm], 90),
            *np.percentile(dist_m[sub][mm], [50, 90])))
