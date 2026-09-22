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
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ARGOS API", version="0.2.0",
              description="Kefalonia Digital Twin — open screening layers. Watching over the places we call home.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://argos-geo.org", "https://www.argos-geo.org",
                   "https://argos-geo.github.io"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
DB = os.environ.get("DATABASE_URL")

VECTOR = {
    "beaches":"beaches", "buildings":"buildings", "pois":"pois",
    "roads":"roads", "trails":"trails", "effis_perimeters":"effis_perimeters",
}
RASTER = {
    "dem":"dem", "slope":"slope", "aspect":"aspect", "ndvi":"ndvi", "ndvi_may":"ndvi_may",
    "wildfire_risk":"wildfire_risk", "wildfire_risk_class":"wildfire_risk_class",
    "wildfire_risk_v1_1b":"wildfire_risk_v1_1b", "wildfire_risk_v1_1b_class":"wildfire_risk_v1_1b_class",
    "wildfire_risk_v1_2":"wildfire_risk_v1_2", "wildfire_risk_v1_2_class":"wildfire_risk_v1_2_class",
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


@app.get("/marine/beaches")
def marine_beaches():
    sql = """
    SELECT b.osm_id, b.name, b.local_name, b.facing_deg,
           round(ST_Y(ST_Centroid(b.geom))::numeric, 5) AS lat,
           round(ST_X(ST_Centroid(b.geom))::numeric, 5) AS lon,
           m.cell_lon, m.cell_lat, m.cell_dist_m
    FROM argos.beaches b
    JOIN (SELECT DISTINCT ON (beach_osm_id) beach_osm_id, cell_lon, cell_lat, cell_dist_m
          FROM argos.marine_forecast ORDER BY beach_osm_id, valid_time) m
      ON m.beach_osm_id = b.osm_id
    WHERE b.curated
    ORDER BY b.name;"""
    with get_pool().connection() as conn:
        rows = conn.execute(sql).fetchall()
    return {"count": len(rows), "beaches": rows}

@app.get("/marine/exposure")
def marine_exposure(osm_id: int = Query(...), hours: int = Query(120, le=240)):
    sql = """
    SELECT beach_osm_id, name, valid_time, vhm0, vmxl, vmdr, vtm10, cur_speed, exposure
    FROM argos.marine_exposure
    WHERE beach_osm_id = %(oid)s AND valid_time > now() - interval '1 hour'
    ORDER BY valid_time
    LIMIT %(h)s;"""
    with get_pool().connection() as conn:
        rows = conn.execute(sql, {"oid": osm_id, "h": hours}).fetchall()
    if not rows:
        raise HTTPException(404, "no marine forecast for this beach (is it one of the curated 14?)")
    with get_pool().connection() as conn:
        meta = conn.execute("SELECT max(cmems_run) AS cmems_run, max(fetched_at) AS fetched_at "
                            "FROM argos.marine_forecast WHERE beach_osm_id = %(oid)s",
                            {"oid": osm_id}).fetchone()
    return {"beach": rows[0]["name"], "count": len(rows),
            "cmems_run": meta["cmems_run"], "fetched_at": meta["fetched_at"],
            "disclaimer": "Modelled offshore conditions (CMEMS 4 km grid, sampled offshore). Regional exposure, not local surf or rip currents. Not a lifeguard-grade forecast.",
            "hours": rows}
