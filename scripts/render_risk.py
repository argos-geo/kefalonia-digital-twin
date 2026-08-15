import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

# --- load class raster ---
with rasterio.open("data/kefalonia_wildfire_risk_class.tif") as src:
    klass = src.read(1).astype(float)
    nd = src.nodata
print("class raster:", klass.shape, "nodata:", nd)
if nd is not None:
    klass = np.where(klass == nd, np.nan, klass)
print("classes present:", np.unique(klass[~np.isnan(klass)]))

# --- sea mask: water has negative NDVI ---
with rasterio.open("data/kefalonia_ndvi_2026-07.tif") as src:
    ndvi = src.read(1).astype(float)
    nd_ndvi = src.nodata
if nd_ndvi is not None:
    ndvi = np.where(ndvi == nd_ndvi, np.nan, ndvi)
klass[ndvi < 0] = np.nan   # sea -> transparent
print("sea pixels masked:", int(np.nansum(ndvi < 0)))

# --- plot: classes 0-4, discrete colors ---
cmap = ListedColormap(["#1a9850", "#91cf60", "#fee08b", "#fc8d59", "#d73027"])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)

fig, ax = plt.subplots(figsize=(10, 12), facecolor="#f4eee0")
ax.set_facecolor("#7fa89b")  # sea = brand sea colour
im = ax.imshow(klass, cmap=cmap, norm=norm, interpolation="nearest")
ax.set_title("ARGOS WATCH — Kefalonia Wildfire Risk Index v1",
             fontsize=15, fontweight="bold", color="#0a1628", pad=14)
ax.set_xticks([]); ax.set_yticks([])

cb = fig.colorbar(im, ax=ax, ticks=[0, 1, 2, 3, 4], fraction=0.035, pad=0.02)
cb.ax.set_yticklabels(["Very low", "Low", "Moderate", "High", "Very high"])

plt.tight_layout()
plt.savefig("argos_wildfire_risk.png", dpi=150, facecolor="#f4eee0")
plt.close()
print("saved argos_wildfire_risk.png")
