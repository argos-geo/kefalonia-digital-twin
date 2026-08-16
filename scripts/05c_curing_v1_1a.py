import numpy as np, rioxarray, gc

MAY = "data/kefalonia_ndvi_2026-05.tif"    # UTM engine grid, offset-corrected, 05-14 excluded
JUL = "data/kefalonia_ndvi_2026-07.tif"    # UTM engine reference grid

may = rioxarray.open_rasterio(MAY, masked=True).squeeze("band", drop=True).astype("float32")
jul = rioxarray.open_rasterio(JUL, masked=True).squeeze("band", drop=True).astype("float32")
assert may.shape == jul.shape, (may.shape, jul.shape)
print("shape", may.shape, "crs", may.rio.crs)

land = (jul > 0) & np.isfinite(jul) & np.isfinite(may)
def mean(x, mask):
    return float(x.where(mask & np.isfinite(x)).mean())

# v1 fuel: July NDVI density, linear 0.15 -> 0.70
density = ((jul - 0.15) / (0.70 - 0.15)).clip(min=0, max=1)

# v1.1a curing: spring-green + July-brown = cured fuel.
# Gated so bare/urban (May not green) cannot become "cured".
ratio = (jul / may).where(may > 0.05)
curing = (1 - ratio).where(land & (may >= 0.35) & (jul >= 0) & (jul < may)).clip(min=0, max=1).fillna(0)
cured_fuel = (0.15 + 0.75 * curing).where(curing > 0).fillna(0)   # 0.15..0.90 only where curing proven
fuel_v1_1a = np.maximum(density, cured_fuel)

for name, arr in [("curing", curing), ("fuel_v1_1a", fuel_v1_1a)]:
    out = arr.where(land).rio.write_crs(jul.rio.crs).rio.write_transform(jul.rio.transform())
    out = out.fillna(-9999).astype("float32").rio.write_nodata(-9999)
    out.rio.to_raster(f"data/kefalonia_{name}_2026.tif", driver="COG", compress="DEFLATE")

cured = land & (may >= 0.50) & (jul <= 0.35) & (jul < may)
evergreen = land & (may >= 0.60) & (jul >= 0.60) & (curing < 0.25)
print(f"land mean: may={mean(may, land):.3f} jul={mean(jul, land):.3f}")
print(f"curing mean land={mean(curing, land):.3f} high>0.6={float(((curing > 0.6) & land).sum() / land.sum()):.3f}")
print(f"fuel v1 land={mean(density, land):.3f} -> v1.1a land={mean(fuel_v1_1a, land):.3f}")
print(f"CURED mask n={int(cured.sum())}: fuel {mean(density, cured):.3f} -> {mean(fuel_v1_1a, cured):.3f}")
print(f"EVERGREEN mask n={int(evergreen.sum())}: fuel {mean(density, evergreen):.3f} -> {mean(fuel_v1_1a, evergreen):.3f} (v1.1b damps altitude later)")
print("saved: data/kefalonia_curing_2026.tif + data/kefalonia_fuel_v1_1a_2026.tif")
