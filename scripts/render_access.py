import matplotlib
matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

DB = "postgresql+psycopg://argos:argos_dev_password@localhost:5432/argos"
eng = create_engine(DB)

roads = gpd.read_postgis("SELECT geom FROM argos.roads WHERE road_class IN ('track','local','service','secondary','tertiary','primary')", eng, geom_col="geom")
ok    = gpd.read_postgis("SELECT ST_Centroid(geom) AS geom FROM argos.buildings WHERE access_score >= 90", eng, geom_col="geom")
rem   = gpd.read_postgis("SELECT osm_id, access_score, ST_Centroid(geom) AS geom FROM argos.buildings WHERE access_score < 90", eng, geom_col="geom")
pois  = gpd.read_postgis("SELECT osm_id, name, access_score, geom FROM argos.pois WHERE access_score < 70", eng, geom_col="geom")

fig, ax = plt.subplots(figsize=(10, 12), facecolor="#f4eee0")
ax.set_facecolor("#7fa89b")
roads.plot(ax=ax, color="#0a1628", linewidth=0.25, alpha=0.35)
ok.plot(ax=ax, color="#888888", markersize=0.5, alpha=0.4)
rem.plot(ax=ax, column="access_score", cmap="RdYlGn", markersize=14, vmin=0, vmax=90,
         legend=True, legend_kwds={"label": "Score — remote buildings (<90) & POIs (<70)", "shrink": 0.5})
if len(pois):
    pois.plot(ax=ax, column="access_score", cmap="RdYlGn", marker="D", markersize=20,
              edgecolor="#0a1628", linewidth=0.4, vmin=0, vmax=90)
ax.set_xlim(20.30, 20.90); ax.set_ylim(37.95, 38.55)
ax.set_title("ARGOS — The Hard-to-Reach Kefalonia (Stage A)", fontsize=15, fontweight="bold", color="#0a1628")
ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout()
plt.savefig("argos_accessibility_map.png", dpi=150, facecolor="#f4eee0")
plt.close()
print(f"saved: {len(rem)} remote buildings + {len(pois)} remote POIs spotlighted, {len(ok)} context buildings")
