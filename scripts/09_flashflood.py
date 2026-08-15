#!/usr/bin/env python3
"""T17 — Flash-flood / post-fire debris-flow susceptibility v1.
Inputs : data/kefalonia_dem_30m.tif (T13), data/kefalonia_wildfire_risk_class.tif (T15),
         municipality polygons from PostGIS (the REAL land mask — see gotcha below)
Outputs: data/kefalonia_flashflood_risk.tif (0-100 float32),
         data/kefalonia_flashflood_risk_class.tif (1-5 int16), nodata=-9999

GOTCHAS already banked (don't rediscover):
- pysheds 0.5: Grid.from_raster/read_raster ONLY — numpy arrays die with
  "data must be a Raster instance". Everything goes through temp tifs.
- Copernicus DEM encodes SEA AS 0 m, NOT NaN. An elevation-threshold land mask
  silently includes the ocean. Land mask = rasterized municipality polygons.
- NaN sea creates coastal fill-plateaus; sea must be a real elevation (-5 m).
- Rectangle bbox pollutes hydrology at the edges -> buffered grid + clip 5 cells.
"""
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.features import rasterize
from pysheds.grid import Grid
import geopandas as gpd
from sqlalchemy import create_engine
if not hasattr(np, 'in1d'): np.in1d = np.isin  # pysheds 0.5 calls np.in1d, removed in numpy 2.x

BBOX      = (20.30, 37.95, 20.90, 38.55)   # island bbox (all our layers)
HYDRO_BUF = 0.05                            # ~5 km buffer for the hydrology grid
DST_RES   = 30.0                            # m, native DEM res
EPSG_UTM  = 32634
NODATA    = -9999.0

# ---------- 1. DEM -> UTM 30m, buffered grid ----------
src = rasterio.open('data/kefalonia_dem_30m.tif')
hb  = (BBOX[0]-HYDRO_BUF, BBOX[1]-HYDRO_BUF, BBOX[2]+HYDRO_BUF, BBOX[3]+HYDRO_BUF)
t_h, w_h, h_h = calculate_default_transform(src.crs, EPSG_UTM, src.width, src.height,
                                            *hb, resolution=DST_RES)
dem = np.full((h_h, w_h), np.nan, 'float32')
reproject(rasterio.band(src, 1), dem, src_transform=src.transform, src_crs=src.crs,
          dst_transform=t_h, dst_crs=EPSG_UTM, resampling=Resampling.bilinear)
print('grid: %d x %d px, DEM peak %.0f m (expect 1619-1621 = Ainos checksum)'
      % (w_h, h_h, np.nanmax(dem)))

# ---------- 2. REAL land mask from the twin's own municipality polygons ----------
eng = create_engine('postgresql+psycopg://argos:argos_dev_password@localhost:5432/argos')
isl = gpd.read_postgis(
    "SELECT ST_Transform(ST_UnaryUnion(ST_Collect(ST_MakeValid(way))), 32634) AS geom "
    "FROM planet_osm_polygon WHERE boundary='administrative' AND admin_level='7'",
    eng, geom_col='geom')
land = rasterize(isl.geometry, out_shape=(h_h, w_h), transform=t_h,
                 fill=0, default_value=1, dtype='uint8').astype(bool)
print('land cells: %d (%.0f km2 — expect ~780)' % (land.sum(), land.sum()*DST_RES**2/1e6))

dem_sea = np.where(land, np.nan_to_num(dem, nan=0.0), -5.0).astype('float32')

with rasterio.open('data/_t17_dem_utm.tif', 'w', driver='GTiff', height=h_h, width=w_h,
                   count=1, dtype='float32', crs=EPSG_UTM, transform=t_h,
                   nodata=NODATA) as d:
    d.write(dem_sea, 1)

# ---------- 3. Hydrology ----------
grid  = Grid.from_raster('data/_t17_dem_utm.tif')
dem_r = grid.read_raster('data/_t17_dem_utm.tif')
f     = grid.resolve_flats(grid.fill_depressions(dem_r))
fdir  = grid.flowdir(f, routing='d8')
acc   = np.asarray(grid.accumulation(fdir, routing='d8')) * DST_RES**2   # m2 upslope
am = acc[land]
print('upslope km2 over land: p50 %.3f p90 %.3f p99 %.2f (expect ~0.004 / ~0.03 / ~1.8)')
      % tuple(np.percentile(am, [50, 90, 99])/1e6)))

# ---------- 4. Upstream burn-scar fraction (weighted accumulation) ----------
risk_cls = rasterio.open('data/kefalonia_wildfire_risk_class.tif')  # 20m UTM from T15
burn_src = (risk_cls.read(1) >= 3).astype('float32')                # classes 3-5 = burn-prone
burn = np.zeros((h_h, w_h), 'float32')
reproject(burn_src, burn, src_transform=risk_cls.transform, src_crs=risk_cls.crs,
          dst_transform=t_h, dst_crs=EPSG_UTM, resampling=Resampling.nearest)
with rasterio.open('data/_t17_burn.tif', 'w', driver='GTiff', height=h_h, width=w_h,
                   count=1, dtype='float32', crs=EPSG_UTM, transform=t_h,
                   nodata=NODATA) as d:
    d.write(burn, 1)
burn_r    = grid.read_raster('data/_t17_burn.tif')          # weights must be Raster too
acc_burn  = np.asarray(grid.accumulation(fdir, routing='d8', weights=burn_r)) * DST_RES**2
burn_frac = np.divide(acc_burn, acc, out=np.zeros_like(acc), where=acc > 0)
burn_frac = np.clip(burn_frac / 0.30, 0, 1)        # full weight at 30% burned upstream

# ---------- 5. Factors ----------
drainage = np.clip((np.log10(acc + 1) - 3) / (7 - 3), 0, 1)   # 900 m2 .. 10 km2 -> 0..1

gy, gx = np.gradient(dem_sea, DST_RES)
slope_deg = np.degrees(np.arctan(np.hypot(gx, gy)))
receiving = np.clip(1 - slope_deg / 10.0, 0, 1)    # flat ground ponds: 0deg=1, >=10deg=0

risk = 100 * (0.45*drainage + 0.30*receiving*drainage + 0.25*burn_frac*drainage)
# drainage is the GATE: no upslope water, no flood; flatness and burn-scar amplify.

# ---------- 6. Clip rectangle artifacts + sea, classify ----------
edge = 5                                            # cells near hydro-grid edge = artifacts
risk[:edge, :] = risk[-edge:, :] = risk[:, :edge] = risk[:, -edge:] = np.nan
risk[~land] = np.nan
risk = np.clip(risk, 0, 100)
klass = np.digitize(risk, [20, 40, 60, 80]).astype('int16')   # classes 0..4 (T15 gotcha)

# ---------- 7. Write tifs ----------
def write(path, arr, dtype):
    out = np.where(np.isnan(risk), NODATA, arr).astype(dtype)
    with rasterio.open(path, 'w', driver='GTiff', height=h_h, width=w_h, count=1,
                       dtype=dtype, crs=EPSG_UTM, transform=t_h, nodata=NODATA,
                       compress='deflate') as d:
        d.write(out, 1)

write('data/kefalonia_flashflood_risk.tif', risk, 'float32')
write('data/kefalonia_flashflood_risk_class.tif', klass, 'int16')
print('saved: kefalonia_flashflood_risk.tif + _class.tif')
print('risk stats: p50 %.1f p90 %.1f p99 %.1f max %.1f' % tuple(
      np.nanpercentile(risk, [50, 90, 99, 100])))
print('class pixels:', {int(k): int(v) for k, v in
      zip(*np.unique(klass[np.isfinite(risk)], return_counts=True))})
