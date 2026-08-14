# T08 — Dev Environment Quickstart (Codespaces-first)

## Why Codespaces-first?
Your laptop has limited disk space. GitHub Codespaces gives you a full Linux dev box
in the browser (or VS Code) — **60 hours/month free** on personal accounts.
Local WSL2+Podman becomes OPTIONAL (do it later only if you want offline work).

## Step 1 — Put these files in the repo (5 min, web UI)
1. Go to github.com/argos-geo/kefalonia-digital-twin
2. Add file → Upload files → drag the CONTENTS of this folder
   (you should see `.devcontainer/`, `api/`, `docker-compose.yml` at repo root)
3. Commit directly to main.

## Step 2 — Open a Codespace (2 min)
1. Repo page → green **Code** button → **Codespaces** tab → **Create codespace on main**
2. Wait ~2-3 min while it builds (first time only).

## Step 3 — Bring the stack up (1 min)
In the Codespace terminal:
    docker compose up -d
    docker compose ps        # all 4 services should be "running"

## Step 4 — Verify (DoD)
- API:        open the forwarded port 8000 → /health should return PostGIS version
- pgAdmin:    port 5050 (login argos@argos-geo.org / argos_dev_password)
- MinIO:      port 9001 (argos / argos_dev_password)

**DoD met when /health returns {"status":"ok", "postgis": "3.4..."}**

## Step 5 (later, Phase 1.5) — Oracle Always Free VM
cloud.oracle.com/free → Ampere A1 ARM (4 OCPU / 24 GB RAM) = always-on host, €0.
Tip: pick your home region carefully; ARM capacity varies by region.
