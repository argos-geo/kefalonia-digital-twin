#!/usr/bin/env python3
"""T17 diagnostic: model values at the Feb 2025 flood locations."""
import numpy as np, rasterio, psycopg

PAT = ['%ερατάτ%','%ραπεζ%','%πόρο%','%αρούζ%','%λαχάτ%','%ιβάδ%','%ειβαθ%']
conn = psycopg.connect('host=localhost dbname=argos user=argos password=argos_dev_password')
rows = conn.execute("""
  SELECT name, ST_X(ST_Transform(way,4326)), ST_Y(ST_Transform(way,4326)), 'place'
  FROM planet_osm_point WHERE name ILIKE ANY(%s) AND place IS NOT NULL
  UNION ALL
  SELECT name, ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom)), 'beach'
  FROM argos.beaches WHERE name ILIKE ANY(%s)
  UNION ALL
  SELECT name, ST_X(geom), ST_Y(geom), 'poi'
  FROM argos.pois WHERE name ILIKE ANY(%s)
  ORDER BY 1""", (PAT, PAT, PAT)).fetchall()

print('--- matches found ---')
for r in rows: print(r)
print('--- model values (600 m radius) ---')
risk = rasterio.open('data/kefalonia_flashflood_risk_4326.tif')
for name, x, y, src in rows:
    w = rasterio.windows.from_bounds(x-0.006, y-0.006, x+0.006, y+0.006, risk.transform)
    a = risk.read(1, window=w).astype('float32')
    a = a[a > -9000]
    if not len(a): print(f'{name:35s} {src:6s} NO DATA'); continue
    print(f'{name:35s} {src:6s} px={len(a):4d} mean={a.mean():5.1f} '
          f'p90={np.percentile(a,90):5.1f} max={a.max():5.1f}')
