import glob
import numpy as np
import rasterio
import geopandas as gpd
import pandas as pd
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt

DB = "postgresql+psycopg://argos:argos_dev_password@localhost:5432/argos"
PX = 20.0  # grid resolution (m), from the NDVI reference grid

# 1. reference grid = NDVI (20m, EPSG:32634)
with rasterio.open("data/kefalonia_ndvi_2026-07.tif") as src:
    ndvi = src.read(1).astype("float32")
    gt, crs = src.transform, src.crs
    H, W = ndvi.shape

def to_grid(path):
    with rasterio.open(path) as src:
        dst = np.empty((H, W), dtype="float32")
        reproject(src.read(1), dst, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=gt, dst_crs=crs, resampling=Resampling.bilinear)
    return dst

slope  = to_grid("data/kefalonia_slope_utm.tif")   # degrees
aspect = to_grid("data/kefalonia_aspect_utm.tif")  # 0=N 90=E 180=S 270=W, -1=flat

# 3. distance to nearest road (m)
roads = gpd.read_postgis("SELECT geom FROM argos.roads", DB, geom_col="geom").to_crs(crs)
road_ras = rasterize(((g, 1) for g in roads.geom), out_shape=(H, W),
                     transform=gt, fill=0, dtype="uint8")
dist_road = distance_transform_edt(road_ras == 0) * PX

# 4. distance to historical fire detections (m)
frames = [pd.read_csv(f, usecols=["latitude", "longitude", "confidence"])
          for f in glob.glob("data/firms/modis_*_Greece.csv")]
fires = pd.concat(frames)
fires = fires[fires.latitude.between(37.95, 38.55)
              & fires.longitude.between(20.30, 20.90)
              & (fires.confidence >= 50)]
print("historical fire detections in bbox:", len(fires))
if len(fires):
    fp = gpd.GeoDataFrame(fires, geometry=gpd.points_from_xy(fires.longitude, fires.latitude),
                          crs=4326).to_crs(crs)
    fire_ras = rasterize(((g, 1) for g in fp.geometry), out_shape=(H, W),
                         transform=gt, fill=0, dtype="uint8")
    dist_fire = distance_transform_edt(fire_ras == 0) * PX
else:
    dist_fire = np.full((H, W), 99999, dtype="float32")

# 5. factor scores (0..1)
s_slope  = np.clip(slope / 40.0, 0, 1)
s_aspect = np.where(aspect < 0, 0.0, (1 - np.cos(np.radians(aspect - 180))) / 2)  # south=1
# v1.2 (T104): fuel base = CLC 2018 land-cover score (pure swap, Option A).
# Grid codes 1..44, VAT-verified. Score table = Panagis draft of 2026-09-21.
CLC_FUEL = {1:0.05, 2:0.05, 3:0.05, 4:0.05, 5:0.05, 6:0.05, 7:0.05,  # artificial
            8:0.05, 9:0.05, 10:0.10, 11:0.10,                        # 141/142 green urban
            12:0.30, 13:0.30, 14:0.30, 15:0.25, 16:0.30, 17:0.35,    # 211..223 (olives 0.35)
            18:0.55, 19:0.45, 20:0.40, 21:0.45, 22:0.40,             # 231..244
            23:0.90, 24:1.00, 25:0.90, 26:0.70, 27:0.75,             # 311..322
            28:0.85, 29:0.80, 30:0.10, 31:0.00, 32:0.15,             # 323, 324, 331, 332=0.00 KARST FIX, 333
            33:0.05, 34:0.05, 35:0.10, 36:0.10}                      # beaches, wetlands; water = nodata
with rasterio.open("data/kefalonia_clc2018_20m.tif") as csrc:
    clc = csrc.read(1)
fuel = np.full((H, W), np.nan, dtype="float32")
for code, score in CLC_FUEL.items():
    fuel[clc == code] = score
# v1.1a curing gate carried over (05c formula), VEGETATED CLASSES ONLY grid 12..29 (CLC 211..324)
# so bare rock stays exactly 0.00 and urban/wetland are not cured upward.
with rasterio.open("data/kefalonia_ndvi_2026-05.tif") as msrc:
    ndvi_may = msrc.read(1).astype("float32")
valid = (ndvi != -9999) & (ndvi_may != -9999) & (ndvi_may > 0.05)
curing = np.where(valid, np.clip(1 - ndvi / np.where(ndvi_may > 0, ndvi_may, np.nan), 0, 1), np.nan)
cured_floor = 0.15 + 0.75 * curing
veg = (clc >= 12) & (clc <= 29)
lift = veg & np.isfinite(cured_floor) & (cured_floor > fuel)
print("v1.2 curing gate: pixels lifted:", int(lift.sum()))
fuel = np.where(lift, cured_floor, fuel)
fuel = np.where((clc == 255) | (clc == 44) | (ndvi == -9999), np.nan, fuel)  # sea/nodata out
print("v1.2 karst check: fuel>0 on grid code 31 (MUST BE 0):",
      int((fuel[clc == 31] > 0).sum()), "/", int((clc == 31).sum()))
for c in [24, 25, 28, 21, 26, 17, 31]:
    m = float(np.nanmean(np.where(clc == c, fuel, np.nan)))
    print(f"v1.2 fuel mean, grid code {c}: {m:.3f}")
# v1.1b altitude / live-fuel-moisture damping: dense LIVE high vegetation only.
# Static proxy: lapse-rate cooling + higher live fuel moisture above ~800 m;
# 800 m -> 1.00, 1600 m -> 0.55 linear. Cured lowland fuel (low July NDVI) is NOT damped.
fuel_before = fuel.copy()
dem = to_grid("data/kefalonia_dem_30m.tif")  # metres, reprojected to engine grid
damp = np.clip(1.0 - np.maximum(dem - 800.0, 0.0) / 800.0 * 0.45, 0.55, 1.0)
dense_live = (ndvi >= 0.60) & (fuel_before >= 0.85) & np.isfinite(fuel_before)
fuel = np.where(dense_live, fuel_before * damp, fuel)
he = dense_live & (dem > 1200)
print("v1.1b dense_live px:", int(dense_live.sum()), "high-elev px:", int(he.sum()))
if int(he.sum()):
    print("v1.2 high-elev dense fuel:", round(float(np.nanmean(fuel_before[he])), 3),
          "->", round(float(np.nanmean(fuel[he])), 3))
s_road   = np.clip(1 - dist_road / 2000.0, 0, 1)
s_fire   = np.clip(1 - dist_fire / 3000.0, 0, 1)

# 6. weighted risk 0..100 + 5 classes
risk = 100 * (0.25 * s_slope + 0.25 * fuel + 0.20 * s_road
              + 0.15 * s_aspect + 0.15 * s_fire)
risk = np.where(np.isnan(fuel), -9999, risk).astype("float32")
klass = np.where(risk < 0, -9999, np.digitize(risk, [20, 40, 60, 80])).astype("int16")

for path, arr, dtype in [("data/kefalonia_wildfire_risk_v1_2.tif", risk, "float32"),
                         ("data/kefalonia_wildfire_risk_v1_2_class.tif", klass, "int16")]:
    with rasterio.open(path, "w", driver="COG", height=H, width=W, count=1,
                       dtype=dtype, crs=crs, transform=gt,
                       nodata=-9999, compress="deflate") as dst:
        dst.write(arr, 1)
print("saved: kefalonia_wildfire_risk_v1_2.tif + kefalonia_wildfire_risk_v1_2_class.tif")
