import matplotlib
matplotlib.use("Agg")
import geopandas as gpd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

DB = "postgresql+psycopg://argos:argos_dev_password@localhost:5432/argos"
eng = create_engine(DB)

b = gpd.read_postgis("SELECT osm_id, fire_min, ST_Centroid(geom) AS geom FROM argos.buildings WHERE fire_min IS NOT NULL", eng, geom_col="geom")
d = gpd.read_postgis("SELECT name, poi_type, geom FROM argos.pois WHERE poi_type='fire_station' OR (poi_type='ferry_terminal' AND name IN ('Φισκάρδο','Αργοστόλι','Ληξούρι','Πεσσάδα','Σάμη','Πόρος'))", eng, geom_col="geom")
r = gpd.read_postgis("SELECT geom FROM argos.roads WHERE road_class IN ('primary','secondary','tertiary')", eng, geom_col="geom")

fig, ax = plt.subplots(figsize=(10, 12), facecolor="#f4eee0")
ax.set_facecolor("#7fa89b")
r.plot(ax=ax, color="#0a1628", linewidth=0.5, alpha=0.4)
b.plot(ax=ax, column="fire_min", cmap="RdYlGn_r", markersize=2, vmin=0, vmax=60,
       legend=True, legend_kwds={"label": "Minutes to ΠΥ Αργοστολίου fire station (driving + last-mile walk)", "shrink": 0.55})
d.plot(ax=ax, marker="*", color="#c9a227", edgecolor="#0a1628", markersize=200, zorder=5)
ax.set_xlim(20.30, 20.90); ax.set_ylim(37.95, 38.55)
ax.set_title("ARGOS — Travel Time to Fire Response (T16 Stage B)", fontsize=15, fontweight="bold", color="#0a1628")
ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout()
plt.savefig("argos_travel_fire_map.png", dpi=150, facecolor="#f4eee0")
plt.close()
print("saved argos_travel_fire_map.png —", len(b), "routed buildings")
