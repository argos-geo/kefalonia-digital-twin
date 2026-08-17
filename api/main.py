"""ARGOS API — T18/T19: health, layer discovery, read-only spatial endpoints."""
import os, json
import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

POOL = None
def get_pool():
    global POOL
    if POOL is None:
        POOL = ConnectionPool(DB, min_size=1, max_size=4, kwargs={"row_factory": dict_row})
    return POOL
from psycopg.rows import dict_row
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="ARGOS API", version="0.2.0",
              description="Kefalonia Digital Twin — open screening layers. Watching over the places we call home.")
DB = os.environ.get("DATABASE_URL")

VECTOR = {
    "beaches":"beaches", "buildings":"buildings", "pois":"pois",
    "roads":"roads", "trails":"trails", "effis_perimeters":"effis_perimeters",
}
RASTER = {
    "dem":"dem", "slope":"slope", "aspect":"aspect", "ndvi":"ndvi", "ndvi_may":"ndvi_may",
    "wildfire_risk":"wildfire_risk", "wildfire_risk_class":"wildfire_risk_class",
    "wildfire_risk_v1_1b":"wildfire_risk_v1_1b", "wildfire_risk_v1_1b_class":"wildfire_risk_v1_1b_class",
    "flashflood_risk":"flashflood_risk", "flashflood_risk_class":"flashflood_risk_class",
}
BBOX = (20.30, 37.95, 20.90, 38.55)  # lonmin, latmin, lonmax, latmax

def check_point(lat: float, lon: float, m: float):
    if not (BBOX[1] <= lat <= BBOX[3] and BBOX[0] <= lon <= BBOX[2]):
        raise HTTPException(400, "point outside Kefalonia study bbox")
    if not (1 <= m <= 50000):
        raise HTTPException(400, "m must be 1..50000")

def geojson_feature(props, gj):
    return {"type":"Feature", "properties": props, "geometry": json.loads(gj) if gj else None}

@app.get("/health")
def health():
    try:
        with get_pool().connection() as conn:
            row = conn.execute("SELECT PostGIS_Version();").fetchone()
        return {"status":"ok", "postgis": row["postgis_version"], "motto":"Watching over the places we call home."}
    except Exception as e:
        return {"status":"db_unreachable", "detail": str(e)}

@app.get("/layers")
def layers():
    sql = """
    SELECT t.table_name AS name,
           CASE WHEN cr.table_name IS NOT NULL THEN 'raster'
                WHEN cg.table_name IS NOT NULL THEN 'vector' ELSE 'table' END AS kind,
           COALESCE(NULLIF(g.srid,0), NULLIF(r.srid,0), 4326) AS srid,
           COALESCE(g.type, 'RASTER') AS geom_type,
           cls.reltuples::bigint AS est_rows
    FROM information_schema.tables t
    JOIN pg_namespace n ON n.nspname=t.table_schema
    JOIN pg_class cls ON cls.relnamespace=n.oid AND cls.relname=t.table_name
    LEFT JOIN information_schema.columns cg ON cg.table_schema=t.table_schema AND cg.table_name=t.table_name AND cg.column_name='geom'
    LEFT JOIN information_schema.columns cr ON cr.table_schema=t.table_schema AND cr.table_name=t.table_name AND cr.column_name='rast'
    LEFT JOIN geometry_columns g ON g.f_table_schema=t.table_schema AND g.f_table_name=t.table_name
    LEFT JOIN raster_columns r ON r.r_table_schema=t.table_schema AND r.r_table_name=t.table_name
    WHERE t.table_schema='argos' AND t.table_type='BASE TABLE'
    ORDER BY t.table_name;"""
    with get_pool().connection() as conn:
        rows = conn.execute(sql).fetchall()
    return {"count": len(rows), "layers": rows}

@app.get("/buffer")
def buffer(lat: float = Query(...), lon: float = Query(...), m: float = Query(10000)):
    check_point(lat, lon, m)
    sql = """SELECT ST_AsGeoJSON(ST_Buffer(ST_SetSRID(ST_MakePoint(%(lon)s,%(lat)s),4326)::geography,%(m)s)::geometry) AS gj"""
    with get_pool().connection() as conn:
        gj = conn.execute(sql, {"lat":lat,"lon":lon,"m":m}).fetchone()[0]
    return geojson_feature({"lat":lat,"lon":lon,"m":m,"note":"API accepts lat,lon; DB stores lon,lat"}, gj)

@app.get("/intersect")
def intersect(layer: str, lat: float, lon: float, m: float = 10000, limit: int = Query(50, le=500)):
    check_point(lat, lon, m)
    if layer not in VECTOR: raise HTTPException(400, f"unknown vector layer; use one of {sorted(VECTOR)}")
    table = VECTOR[layer]
    sql = f"""
    WITH b AS (SELECT ST_Buffer(ST_SetSRID(ST_MakePoint(%(lon)s,%(lat)s),4326)::geography,%(m)s)::geometry AS g)
    SELECT to_jsonb(t)-'geom' AS properties, ST_AsGeoJSON(t.geom) AS gj
    FROM (SELECT a.* FROM argos.{table} a CROSS JOIN b
          WHERE ST_Intersects(geom, b.g)
          ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%(lon)s,%(lat)s),4326)
          LIMIT %(limit)s) t;"""
    with get_pool().connection() as conn:
        rows = conn.execute(sql, {"lat":lat,"lon":lon,"m":m,"limit":limit}).fetchall()
    return {"type":"FeatureCollection", "layer": layer, "returned": len(rows),
            "features":[geojson_feature(p, gj) for p, gj in rows]}

@app.get("/aggregate")
def aggregate(layer: str, lat: float, lon: float, m: float = 10000):
    check_point(lat, lon, m)
    if layer not in RASTER: raise HTTPException(400, f"unknown raster layer; use one of {sorted(RASTER)}")
    table = RASTER[layer]
    sql = f"""
    WITH b AS (SELECT ST_Buffer(ST_SetSRID(ST_MakePoint(%(lon)s,%(lat)s),4326)::geography,%(m)s)::geometry AS g)
    , s AS (SELECT (ST_SummaryStats(ST_Clip(rast, b.g), true)).*
          FROM argos.{table} CROSS JOIN b WHERE ST_Intersects(rast, b.g))
    SELECT sum(count)::bigint AS count, sum(sum) AS sum,
           sum(sum)/nullif(sum(count),0) AS mean,
           sqrt(greatest(0,
             sum(count*(stddev*stddev + mean*mean))/nullif(sum(count),0)
             - power(sum(count*mean)/nullif(sum(count),0), 2))) AS stddev,
           min(min) AS min, max(max) AS max
    FROM s;"""
    with get_pool().connection() as conn:
        row = conn.execute(sql, {"lat":lat,"lon":lon,"m":m}).fetchone()
    if not row or row.get("count") is None:
        return {"layer": layer, "count": 0}
    return {"layer": layer, **row}
