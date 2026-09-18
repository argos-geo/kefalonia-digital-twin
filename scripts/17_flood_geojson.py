#!/usr/bin/env python3
"""Regenerate docs/tiles/src/flood_risk.geojson from the deployed class raster.
Source: data/kefalonia_flashflood_risk_v1_1_class_4326.tif, the exact raster
loaded into argos.flashflood_risk_class. Dissolve by pixel connectivity via
rasterio.features.shapes (no GEOS union: ST_Union on pixel dumps throws
TopologyException even after ST_SnapToGrid, banked gotcha 18 Sep 2026).
Class map: 2=moderate, 3=high, 4=very_high. Prints census for verification."""
import json, collections
import numpy as np
import rasterio
from rasterio.features import shapes

SRC = "data/kefalonia_flashflood_risk_v1_1_class_4326.tif"
LABEL = {2: "moderate", 3: "high", 4: "very_high"}

with rasterio.open(SRC) as ds:
    arr = ds.read(1)
    transform = ds.transform

mask = np.isin(arr, [2, 3, 4])
feats = []
for geom, val in shapes(arr.astype("int16"), mask=mask, transform=transform):
    v = int(val)
    if v in LABEL:
        feats.append({"type": "Feature", "properties": {"risk": LABEL[v]}, "geometry": geom})

with open("docs/tiles/src/flood_risk.geojson", "w") as f:
    json.dump({"type": "FeatureCollection", "features": feats}, f)
census = collections.Counter(ft["properties"]["risk"] for ft in feats)
gtypes = collections.Counter(ft["geometry"]["type"] for ft in feats)
print("features:", len(feats), dict(census), dict(gtypes))
