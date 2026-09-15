import os, psycopg2, rasterio, json
from rasterio.features import shapes

JOBS = [
    ("argos.wildfire_risk_v1_1b_class", "wf", {3: "moderate", 4: "high", 5: "very_high"}),
    ("argos.flashflood_risk_class",     "ff", {2: "moderate", 3: "high", 4: "very_high"}),
]
conn = psycopg2.connect(dbname="argos", user="argos",
                        password=os.environ["PGPASSWORD"],
                        host="localhost", port=5432)
for table, tag, mapping in JOBS:
    cur = conn.cursor()
    cur.execute(f"SELECT ST_AsTIFF(ST_Union(rast)) FROM {table};")
    tif = f"work/risk/{tag}_class.tif"
    with open(tif, "wb") as f:
        f.write(bytes(cur.fetchone()[0]))
    with rasterio.open(tif) as src:
        arr, transform = src.read(1), src.transform
    feats = []
    for geom, val in shapes(arr, transform=transform, connectivity=8):
        v = int(val)
        if v in mapping:
            feats.append({"type": "Feature",
                          "properties": {"risk": mapping[v]},
                          "geometry": geom})
    out = f"work/risk/{tag}_risk.geojson"
    with open(out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": feats}, f)
    print(tag, "features:", len(feats))
print("done")
