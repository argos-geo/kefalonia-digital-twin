import time, glob, gc
t0 = time.time()
def log(m): print(f"[{time.time()-t0:6.1f}s] {m}", flush=True)

import numpy as np, xarray as xr, rioxarray
from rasterio.enums import Resampling
log("imports done")

# QC'd 16 Aug 2026: Earth Search raster:bands scale=0.0001 offset=-0.1 nodata=0.
# Drop S2A_34SDH_20260514_0_L2A: bright-cloud p99 ~0.98 + land NDVI depressed (0.494)
# while 05-04/05-20/05-25 land means are 0.689/0.739/0.751.
ids = ["S2A_34SDH_20260504_0_L2A", "S2B_34SDH_20260520_0_L2A", "S2C_34SDH_20260525_0_L2A"]

hits = glob.glob("data/kefalonia_ndvi_2026-07*.tif")
assert hits, "July NDVI tif not found in data/"
july = rioxarray.open_rasterio(hits[0], masked=True).squeeze("band", drop=True).astype("float32")
land = (july > 0); veg = (july >= 0.15)
def mean(x, mask=None):
    y = x.where(np.isfinite(x)) if mask is None else x.where(mask & np.isfinite(x))
    return float(y.mean())
log(f"July grid {hits[0]}: land={mean(july, land):.3f} veg={mean(july, veg):.3f}")

matched = []
for i in ids:
    red = rioxarray.open_rasterio(f"data/s2_may/{i}_red.tif", masked=True).squeeze("band", drop=True)
    nir = rioxarray.open_rasterio(f"data/s2_may/{i}_nir.tif", masked=True).squeeze("band", drop=True)
    red = red.rio.clip_box(20.30, 37.95, 20.90, 38.55, crs="EPSG:4326").load().astype("float32") * 0.0001 - 0.1
    nir = nir.rio.clip_box(20.30, 37.95, 20.90, 38.55, crs="EPSG:4326").load().astype("float32") * 0.0001 - 0.1
    ndvi = (((nir - red) / (nir + red)).where(np.isfinite(red) & np.isfinite(nir) & ((nir + red) != 0))).clip(min=-1, max=1)
    m = ndvi.rio.reproject_match(july, resampling=Resampling.average).astype("float32")  # BEFORE the mean
    log(f"{i}: matched land={mean(m, land):.3f} veg={mean(m, veg):.3f}")
    matched.append(m)
    del red, nir, ndvi, m
    gc.collect()

may = xr.concat(matched, dim="time").mean(dim="time", skipna=True)
may = may.where(np.isfinite(july))  # keep July valid footprint/nodata shape
log(f"MAY v4 land={mean(may, land):.3f} veg={mean(may, veg):.3f} full-valid={mean(may):.3f}")

may = may.clip(min=-1, max=1).fillna(-9999).astype("float32").rio.write_nodata(-9999)
may.rio.to_raster("data/kefalonia_ndvi_2026-05.tif", driver="COG", compress="DEFLATE")
log("saved: data/kefalonia_ndvi_2026-05.tif")
