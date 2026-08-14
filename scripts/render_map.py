import geopandas as gpd
import matplotlib.pyplot as plt

DB = "postgresql+psycopg://argos:argos_dev_password@localhost:5432/argos"

kef   = gpd.read_postgis("SELECT name, way AS geom FROM planet_osm_polygon WHERE boundary='administrative' AND admin_level='7'", DB, geom_col="geom")
beach = gpd.read_postgis("SELECT name, geom FROM argos.beaches", DB, geom_col="geom")
trail = gpd.read_postgis("SELECT name, geom FROM argos.trails", DB, geom_col="geom")

fig, ax = plt.subplots(figsize=(12, 10), facecolor="#0a1628")
ax.set_facecolor("#0a1628")
kef.plot(ax=ax, color="#14304d", edgecolor="#c9a227", linewidth=1.2)
trail.plot(ax=ax, color="#7fa89b", linewidth=0.8)
beach.plot(ax=ax, color="#f4eee0", markersize=22)
ax.set_xlim(20.30, 20.90)   # frame the island, ignore broken geometries
ax.set_ylim(37.95, 38.55)
ax.set_title("ARGOS — Kefalonia Digital Twin: beaches & trails (T12)", color="#f4eee0", fontsize=14)
ax.axis("off")
plt.tight_layout()
plt.savefig("argos_first_map.png", dpi=150, facecolor="#0a1628")
print("saved argos_first_map.png")
