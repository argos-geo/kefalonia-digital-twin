"""ARGOS API — T08 health-check placeholder. Real endpoints land in Phase 1."""
import os
import psycopg
from fastapi import FastAPI

app = FastAPI(title="ARGOS API", version="0.0.1")

DB = os.environ.get("DATABASE_URL", "postgresql://argos:argos_dev_password@localhost:5432/argos")

@app.get("/health")
def health():
    try:
        with psycopg.connect(DB) as conn:
            row = conn.execute("SELECT PostGIS_Version();").fetchone()
        return {"status": "ok", "postgis": row[0], "motto": "Watching over the places we call home."}
    except Exception as e:
        return {"status": "db_unreachable", "detail": str(e)}
