import rioxarray, matplotlib.pyplot as plt
ndvi = rioxarray.open_rasterio("data/kefalonia_ndvi_2026-07.tif", masked=True).squeeze()
fig, ax = plt.subplots(figsize=(12,10), facecolor="#0a1628")
ax.set_facecolor("#0a1628")
ndvi.plot(ax=ax, cmap="RdYlGn", vmin=-0.2, vmax=0.8,
          cbar_kwargs={"label": "NDVI — July 2026"})
ax.set_title("ARGOS — Kefalonia NDVI (Sentinel-2, July 2026)", color="#f4eee0", fontsize=14)
ax.axis("off")
plt.tight_layout()
plt.savefig("argos_ndvi_map.png", dpi=150, facecolor="#0a1628")
print("saved argos_ndvi_map.png")
