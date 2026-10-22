# SPEC v0.2.0 — "It breathes."

**Status:** draft, 22 Oct 2026. Spec-prep scouting complete, all six legs closed, zero build started.
**Scope:** the twin goes from periodically recomputed static layers to live ingestion. Version trigger per Battle Plan: T29-T31 real-time feeds + existing T46-T47 marine. T30 (ADS-B aircraft) is deferred, see section 8.

**Scouting evidence:** every endpoint below was proven by live probe on 22 Oct 2026 from Panagis's machine. Real counts and byte sizes are recorded in ARGOS_Code_Bible.md, v0.2.0 spec prep section. Nothing in this spec is from memory.

---

## 1. Feeds

### 1.1 Open-Meteo weather stream (T29) — PROVEN

- **Forecast:** `https://api.open-meteo.com/v1/forecast?latitude=<lat>&longitude=<lon>&hourly=<vars>&forecast_days=16&timezone=Europe/Athens`. No key, sub-millisecond generation, hourly, 16-day horizon (T32 7-day outlook fits with headroom).
- **Archive:** `https://archive-api.open-meteo.com/v1/archive?...&start_date=...&end_date=...`. ~80 years of history. Feeder for the T33 time slider.
- **Grid points (5):** Argostoli, Sami, Fiskardo, Lixouri, Ainos. Ainos needs the `elevation` parameter or a dedicated point: the plain forecast call snapped our test point to a coastal cell (38.132/20.524, elevation 0.0). Mountain weather is a deliberate choice, not a default.
- **Licence:** CC BY 4.0, free non-commercial up to 10,000 calls/day (5,000/h, 600/min). ARGOS qualifies (non-profit, no ads).
- **Duty:** attribution "Weather data by Open-Meteo.com" next to any display.
- **Cadence:** hourly at :10 past, 5 points x 1 call = 120 calls/day, 1.2% of the free budget.
- **Variables (v0):** temperature_2m, relative_humidity_2m, precipitation, wind_speed_10m, wind_direction_10m, wind_gusts_10m, cloud_cover, surface_pressure, cape, showers, thunderstorms where available. Final list locked at build time against T32 FWI/heat/rain outlook needs.

### 1.2 EFFIS fire-weather + burned-area (T31) — PROVEN

- **WMS:** `https://maps.effis.emergency.copernicus.eu/effis`. GetCapabilities lists 130 layers. (Dead ends recorded: legacy ies-ows.jrc.ec.europa.eu broken-default, GWIS ArcGIS REST 404.)
- **Live families:** `mf010.*` (Météo-France FWI system: fwi, ffmc, dmc, dc, isi, bui, anomaly, ranking); `all.hs | viirs.hs | noaa.hs | modis.hs` hotspots plus `.query` GetFeatureInfo variants; `modis.ba.*` and `effis.nrt.ba.*` burned areas (poly + point, today/week/month/season/year 2016-2025); `fuel_map`.
- **Proof pull:** `LAYERS=mf010.fwi&FORMAT=image/tiff&VERSION=1.1.1&BBOX=20.30,37.95,20.90,38.55&WIDTH=240&HEIGHT=240&TIME=2026-10-22` returned `200 image/tiff`, 230,998 bytes. Loads through the same raster2pgsql pattern as T13/T15.
- **Cadence:** FWI tiff daily, early morning local. Hotspots on demand only (GetFeatureInfo), not polled.
- **Caveats:** ECMWF FWI variant is NOT in this catalogue (mf010 only). Most layers require an explicit `&TIME=`. WMS 1.1.1 EPSG:4326 BBOX order is lon,lat (matches house habit).
- **Gotchas:** wrong layer names die with `200 application/vnd.ogc.se_xml` (a 459-byte Service Exception), always read the catalogue first. Validate content-type before ingest.
- **Design input (from T18/T111 findings):** FIRMS/VIIRS was blind to both small October 2026 fires (0 detections vs 11-12/day elsewhere in W Greece). FIRMS alone is not a detection backbone for this fire class; EFFIS perimeters + local press stay the anchor. FIRMS MAP_KEY sits in the codespace .env if a supplementary feed is ever wanted.

### 1.3 Copernicus EMS activations (T31 companion) — PROVEN

- **List API:** `https://mapping.emergency.copernicus.eu/activations/api/activations/`. HTTP 200 application/json, no key, paged (limit/offset). Worldwide 1,068 records, Greece 113 (22 Oct 2026).
- **Country filter:** `?countries=GR`, ISO-2 ONLY. `?countries=Greece` and `?countries=GRC` return HTTP 200 with `count:0` silently. Never trust a count without a known-positive control.
- **Detail endpoint:** `/activations/api/activations/EMSR<code>/`.
- **Sibling feed:** `https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations-info/` (268 records, codes + centroids + n_aois/n_products).
- **RSS:** `https://mapping.emergency.copernicus.eu/latest/feed/` (~8.6 KB, newest first). Cheapest poll.
- **Cadence:** RSS 4x/day; on a new GR activation, pull the detail JSON and (if within or near the Ionian) the activation AOI.
- **Greek census:** 96 fire / 16 flood / 1 other. v0.2.0 renders fire + flood only.
- **Honesty note:** Kefalonia is historically under-served by EMS. The island's only brush with the service was Ianos 2020, whose official mapping was EMSR465 (Thessaly/Karditsa leg only, confirmed by the NASA GEER report); there was never a Cephalonia activation. Nearest neighbour anchor: Zakynthos activations 2017 (EMSR180, joint with NE Attika), 2019, 2025. This layer is a national/Ionian awareness feed, not a local-history replay. UI copy must say so.
- **Gotcha:** pagination `next` links come back `http://`. Force https in the fetcher.
- **Licence:** Copernicus free-and-open with attribution. Record exact wording in ARGOS_Data_Sources.md at build time.

### 1.4 Marine (T46/T47) — ALREADY LIVE

- CMEMS MEDSEA analysis-forecast, 14 pilot beaches, 1,778 rows/refresh, full marine_refresh 43.4s with run-key cache. Unchanged by v0.2.0; it is the template the new feeds copy (cron + cache + freshness chips).
- Known structural lag: MEDSEA publishes one run daily on the 12:00 UTC cycle, materialising ~24h late. Freshness chips show both fetch age and run age. New feeds adopt the same two-number honesty pattern.

### 1.5 TEE telemetry — WATCH ITEM, not a feed

- The TEE υδατορέματα early-warning network exists (150 water-level telemetry stations + 250 met stations nationally, real-time, wired to Civil Protection, Greece 2.0 funded). No public API or portal found; Kefalonia station coverage unknown.
- Action: quarterly re-check (tee.gr, data.gov.gr). Candidate for v0.3.0+ flood nowcasting. Carries zero weight in this spec.

---

## 2. Schema — DECIDED: partitioned Postgres, no TimescaleDB

- Volume math: weather ~2-3k rows/day (~1M/yr), FWI 231 KB/day (~85 MB/yr archived), EMS a handful/yr. This does not justify TimescaleDB.
- Decision: native declarative partitioning (monthly RANGE) on the weather table only. Plain tables elsewhere. Zero new extensions, dev/prod identical, pg_dump unchanged. Migration to TimescaleDB stays open if v0.3.0 time-slider volumes ever demand it.

**Proposed tables (final DDL at build time, schema `argos`):**

```
argos.weather_hourly        -- PARTITION BY RANGE (ts); monthly partitions
  (point_id smallint, ts timestamptz, temp_c real, rh_pct real, precip_mm real,
   wind_ms real, wind_dir smallint, gust_ms real, cloud_pct smallint,
   pressure_hpa real, cape real, fetched_at timestamptz)
argos.weather_points        -- 5 rows: id, name_en, name_el, lat, lon, elevation_m
argos.fwi_daily             -- date, raster rid (raster2pgsql pattern), source layer, fetched_at
argos.ems_activations       -- code pk, name, category, countries, centroid geometry,
                            -- activation_time, last_update, closed, n_aois, n_products, raw jsonb
```

---

## 3. Capacity — VERDICT: FITS on argos-core-1 (1 OCPU / 6 GB aarch64)

Measured 22 Oct 2026: RAM 985 MB used / 4.9 GB available; containers idle ~390 MB combined (postgis 172, minio 150, api 46, caddy 21); disk 33% of 45 GB (30 GB free, daily report WARNs at 75%); DB 220 MB total.

- Streams add ~100-200 MB/yr worst case. No VM upgrade, no new services.
- marine_refresh 43.4s is a CPU/network burst, not contention.
- Cron plan (staggered): weather hourly :10; FWI daily 06:30 local; EMS RSS 4x/day at :45; marine unchanged on its existing slot.

---

## 4. Public API surface (FastAPI, api.argos-geo.org)

Existing: `/health` (canonical), marine endpoints.

Proposed additions, all read-only, all bbox-hygienic:

```
GET /weather/current          -- latest row per weather point (5 rows)
GET /weather/forecast         -- hourly forecast per point, 16-day
GET /fire/fwi                 -- latest FWI raster summary + class stats over bbox
GET /ems/activations          -- GR activations, newest first, closed flag
GET /ems/activations/{code}   -- single activation detail
```

- Every response carries `fetched_at` and, where a model run exists, `run_at`. Same two-number freshness honesty as marine.
- Attribution strings ship inside responses AND in UI: "Weather data by Open-Meteo.com", "Copernicus Emergency Management Service / EFFIS".
- No auth changes. Rate limiting deferred until abuse appears; Caddy access logs are the tripwire.

---

## 5. UI (site, no redesign)

- New "Live" group in the layer panel: weather (per-town chips), FWI raster overlay, EMS activations (national context card, Ionian highlighted).
- Every live element carries freshness chips (fetch age + run age where applicable).
- Honesty vnotes follow the established pattern: EMS card states the under-served-by-EMS fact; weather states model grid snap and the Ainos elevation choice; FWI states mf010 (Météo-France) source, not ECMWF.
- Bilingual from day one (EN/ΕΛ), no em-dashes anywhere (house rule 14).

---

## 6. Costs

| Item | Cost |
|---|---|
| Open-Meteo | €0 (CC BY 4.0 non-commercial, attribution duty) |
| EFFIS WMS | €0 (Copernicus open) |
| EMS Mapping API/RSS | €0 (Copernicus open, attribution duty) |
| VM | €0 change (Oracle free tier, fits with headroom) |
| DB schema | €0 (no new extensions) |
| **Total new spend** | **€0** |

---

## 7. Limitations (honest, for the credibility ladder)

1. Weather is model output snapped to ~10 km grid cells; Ainos conditions differ from coast. The 5-point grid is a deliberate compromise, not station data.
2. FWI is the Météo-France mf010 variant. The ECMWF variant is not exposed by the EFFIS WMS catalogue probed.
3. FIRMS/VIIRS-class satellite detection misses small fast-contained fires on pass timing (proven: 0 detections on both Oct 2026 Kefalonia fires). EFFIS perimeters + press remain the anchor for local fire truth.
4. EMS activations are civil-protection-requested products, not a complete disaster catalogue. Kefalonia has never had its own activation; the EMS layer is awareness context.
5. Marine CMEMS run is structurally 24-48h old (one daily 12:00 UTC run, materialising late). Freshness chips disclose this.

---

## 8. Deferred

- **T30 ADS-B aircraft stream (OpenSky/ADSB.lol):** NOT scouted in this round. No endpoint has been probed; nothing is proven. Candidate sources per Battle Plan: OpenSky, ADSB.lol. Scouting is its own block before any build. Ships in v0.2.0 only if scouting lands clean; otherwise it slips without blocking the version.
- TEE telemetry: watch item, section 1.5.
- FIRMS supplementary feed: key in hand, value unproven for this fire class, parked.

---

## 9. Definition of Done for v0.2.0 (the version, not this spec)

1. All four feeds (weather, FWI, EMS, marine) refreshing on cron on prod with staggered schedules.
2. API endpoints of section 4 live and returning `fetched_at`/`run_at`.
3. UI Live group bilingual with freshness chips and honesty vnotes.
4. Attribution strings visible wherever feed data displays.
5. vm_daily_report extended with per-feed freshness lines and WARN on stale.
6. ARGOS_Data_Sources.md rows for Open-Meteo, EFFIS WMS, EMS API on ingest day.
7. Bible entries per build task before any tick.
8. Panagis sanity pass on the live site, phone included (QR traffic is real).

---

*This spec is scouting-hardened: every endpoint PROVEN 22 Oct 2026, every volume measured, every dead end recorded in the Bible. What it promises is buildable with what the box and the budget already have.*
