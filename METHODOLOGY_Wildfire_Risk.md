# ARGOS WATCH — Wildfire Risk Index v1.1: Methodology
*Kefalonia Digital Twin · August 2026 · v1.1 (expert-weighted static baseline + seasonal curing/altitude modifiers; still screening, not forecast)*

## Purpose
A static, island-wide baseline of wildfire ignition & spread susceptibility for Kefalonia
(and incidentally Ithaca), at 20 m resolution. Designed to be read and challenged by
foresters, civil protection, and researchers. **This is a screening layer, not an
operational forecast** — see Limitations.

## Inputs (all layers already in the twin)

| Factor | Weight | Source layer | Source data | Rationale |
|---|---|---|---|---|
| Slope | 25% | `argos.slope` (recomputed on EPSG:32634, 30 m) | Copernicus DEM GLO-30 | Fire spreads faster uphill; rate of spread roughly doubles per 10–20° |
| Fuel (vegetation) | 25% | `argos.ndvi` (July 2026) | Sentinel-2 L2A via Earth Search STAC, 4 scenes @ 0% cloud, mean composite | Dense vegetation = fuel load. Scored linearly from NDVI 0.15→0.7 |
| Road proximity | 20% | `argos.roads` | OpenStreetMap (Geofabrik, Aug 2026) | Most ignitions are human-caused, near the road network. Full weight at road, decaying to 0 at 2 km |
| Aspect | 15% | `argos.aspect` (EPSG:32634) | Copernicus DEM GLO-30 | South-facing slopes are drier/hotter. Cosine curve: south = 1, north = 0, flat = 0 |
| Fire history | 15% | 56 MODIS detections, 2015–2025, confidence ≥ 50, island bbox | NASA FIRMS country archive (Greece CSVs) | Past fire activity indicates recurrence-prone zones. Full weight at detection, decaying to 0 at 3 km |

## Computation
`risk = 100 × (0.25·slope/40 + 0.25·fuel + 0.20·road + 0.15·aspect + 0.15·history)`
(each factor normalized to [0,1] first; sea/outside-coverage pixels = nodata −9999)

Classification: **1 very low (<20) · 2 low (20–40) · 3 moderate (40–60) · 4 high (60–80) · 5 very high (>80)**

Reproduce: `scripts/05_wildfire_risk.py` (requires the T10–T14 layers loaded). Outputs:
`kefalonia_wildfire_risk.tif` (continuous 0–100), `kefalonia_wildfire_risk_class.tif` (1–5).
Stored in PostGIS (`argos.wildfire_risk`, `argos.wildfire_risk_class`) and MinIO (`argos-data/risk/`).

## Sanity checks performed
- Class distribution sane: majority moderate, meaningful high/very-high tail
- Ainos forest spine + dense maquis → high; Argostoli urban core + bare coast → low
- Fire-history halos visible around the 56 historical detections

## Validation — v1.0 vs EFFIS burnt-area perimeters (16 Aug 2026, T15.1)

Harness: EFFIS WFS archive (typename `ms:modis.ba.poly`), **24 perimeters** intersecting the
study envelope, 2017-08 → 2026-08, **2,737 ha** total. Method: zonal statistics of the v1.0
risk raster inside each perimeter vs the island-wide land baseline (sea masked to nodata;
pixel-count areas reproduce EFFIS AREA_HA within ~2%).

| Metric | Island baseline | Burned areas |
|---|---|---|
| Mean risk (0–100) | 58.1 | **62.5** (area-weighted) |
| Pixels in class ≥3 (high + very high) | 46.0% | **64.0%** |
| Pixels in class 4 (very high) | 2.0% | **7.1%** (3.5× enrichment) |
| Fires scoring above island mean | — | **17 of 24** |

**Verdict: directionally validated, not calibrated.** Burned areas concentrate in high-risk
pixels at 1.4–3.5× the island rate, against a strict baseline (the island itself is highly
flammable). But discrimination is imperfect: 7 fires scored below island mean and 26.8% of
burned area sat in merely-moderate pixels.

Caveats, honestly stated:
- **Small N**: 24 perimeters, one island, archive floor 2017 for this bbox; pre-2018 fires
  <~30 ha are invisible (MODIS 250 m source). This is a screening validation, not a
  statistical proof.
- **Conservative bias for recent scars** (7 fires, 2025+): their burns appear as low-NDVI
  ground in the July 2026 fuel layer, dragging their scores DOWN (worst case: 278276,
  344 ha, 86% sclerophyllous per EFFIS, scores 39.8). The model is graded on its own wound.
- **Agricultural burns undervalued** (e.g. 13807, 2017, 100% agri, scores 43.7) — the
  cured-grass blind spot of limitation 7.
- EFFIS dates are detection/last-update dates, not ignition/extinction dates.
- Local-knowledge review (16 Aug 2026): roster green-lit, no missing or false fires flagged.


## v1.1 update (16 Aug 2026) — seasonal curing + altitude/live-fuel-moisture damping

Fuel is no longer July NDVI density alone. v1.1a adds a gated curing term from May vs July
Sentinel-2 (Earth Search local COGs with STAC `scale=0.0001, offset=-0.1` applied; 2026-05-14
QC-excluded): where spring was green (May NDVI ≥0.35) and July browned (July < May),
`curing = clip(1 - NDVI_jul/NDVI_may, 0, 1)` and `cured_fuel = 0.15 + 0.75·curing`;
fuel becomes `max(July-density, cured_fuel)`. v1.1b then damps only dense live high fuel
(July NDVI ≥0.60 and fuel ≥0.85) with elevation: 800 m → factor 1.00, linear to 1600 m → 0.55,
as a static lapse-rate/live-fuel-moisture proxy. Cured lowland fuel is not damped.

Same-harness validation vs EFFIS (24 perimeters): v1 reproduced burned **62.5** vs island
**58.1**, 17/24 above island, ≥3 **64.0% vs 46.0%**, class 4 **7.1% vs 2.0%**. v1.1b:
burned **63.6** vs island **59.1**, **19/24** above island, ≥3 **66.9% vs 47.2%**, class 4
**7.1% vs 1.9% ≈ 3.7×**. This is a real but modest discrimination gain; the known fuel blind
spots improved without crossing island mean (278276 39.8→42.0; 13807 43.7→44.9), and the model
remains **directionally validated, not calibrated**.

## Limitations (read before using)
1. **Static baseline** — no live fuel moisture, no wind, no weather. This is *where* fire is
   likely to be severe, not *when*.
2. **Weights are expert judgment** — now *directionally validated* against 24 EFFIS
   perimeters (see Validation), but not yet refit against them; v1.1 keeps or adjusts them
   based on the re-validation table.
3. **Fuel seasonality is only partially modelled.** v1.1 adds May→July curing and an altitude/live-moisture damper, but it is still a static 2026 snapshot, not live fuel moisture.
4. **MODIS fire detections are ~1 km resolution** and 2015–2025 only; small/agricultural
   fires are undercounted; detection ≠ burned area.
5. **No suppression-access modelling** (firefighting access, water points) — planned v2
   with the curated trails layer (T12) and electricity-network ignition sources (FAQ Q20).
6. 20 m grid smooths fine terrain detail.
7. **No fuel-moisture or altitude effect.** NDVI-as-fuel measures vegetation *density*,
   not *flammability*. Dense high-altitude fir (Mt Ainos) scores maximum fuel although
   its live fuel moisture, cooler temperatures, and distance from ignition sources make
   it harder to ignite than cured lowland grass/maquis — which the model correspondingly
   undervalues. v1 reads as *severity if burned* more than *likelihood of burning*.
   (Raised by local-knowledge review, 15 Aug 2026 — the sanity check working as designed.)

## Roadmap
- v1.1 (**DONE 16 Aug 2026**, T15.1 — validation above):
  cured-grass + altitude/live-moisture modifiers landed; re-validation improved
  discrimination modestly and is published honestly. Next credibility rungs: benchmark
  against EFFIS FWI/Copernicus EMS where comparable, technical validation report,
  preprint, then fire-season case study.
- v1.2: live Fuel Moisture / FWI from ECMWF open data → daily dynamic risk
- v2.0: suppression access + utility-infrastructure ignition points + community-reported fuel breaks (ARGOS COMMONS)

*License: CC BY 4.0 for the layer, MIT for the code. Built in the open — if you're a
forester or fire scientist and see a flaw, open an issue. That's the point.*
