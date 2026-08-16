"""ARGOS API — T18 skeleton: health + layer discovery from PostGIS catalogs."""
import os
import psycopg
from psycopg.rows import dict_row
from fastapi import FastAPI

app = FastAPI(
    title="ARGOS API",
    version="0.1.0",
    description="Kefalonia Digital Twin — open screening layers. Watching over the places we call home.",
)
DB = os.environ.get("DATABASE_URL", "postgresql://argos:argos_dev_password@localhost:5432/argos")

@app.get("/health")
def health():
    try:
        with psycopg.connect(DB) as conn:
            row = conn.execute("SELECT PostGIS_Version();").fetchone()
        return {"status": "ok", "postgis": row[0], "motto": "Watching over the places we call home."}
    except Exception as e:
        return {"status": "db_unreachable", "detail": str(e)}

@app.get("/layers")
def layers():
    sql = """
    SELECT t.table_name AS name,
           CASE WHEN cr.table_name IS NOT NULL THEN 'raster'
                WHEN cg.table_name IS NOT NULL THEN 'vector'
                ELSE 'table' END AS kind,
           COALESCE(g.srid, r.srid) AS srid,
           COALESCE(g.type, 'RASTER') AS geom_type,
           cls.reltuples::bigint AS est_rows
    FROM information_schema.tables t
    JOIN pg_namespace n ON n.nspname = t.table_schema
    JOIN pg_class cls ON cls.relnamespace = n.oid AND cls.relname = t.table_name
    LEFT JOIN information_schema.columns cg
      ON cg.table_schema=t.table_schema AND cg.table_name=t.table_name AND cg.column_name='geom'
    LEFT JOIN information_schema.columns cr
      ON cr.table_schema=t.table_schema AND cr.table_name=t.table_name AND cr.column_name='rast'
    LEFT JOIN geometry_columns g
      ON g.f_table_schema=t.table_schema AND g.f_table_name=t.table_name
    LEFT JOIN raster_columns r
      ON r.r_table_schema=t.table_schema AND r.r_table_name=t.table_name
    WHERE t.table_schema='argos' AND t.table_type='BASE TABLE'
    ORDER BY t.table_name;
    """
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        rows = conn.execute(sql).fetchall()
    return {"count": len(rows), "layers": rows}
