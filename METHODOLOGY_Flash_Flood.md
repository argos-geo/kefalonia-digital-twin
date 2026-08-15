# ARGOS WATCH — Flash-Flood / Post-Fire Debris-Flow Susceptibility v1: Methodology
*Kefalonia Digital Twin · August 2026 · v1.0 (screening layer, not a forecast)*

## Purpose
Island-wide susceptibility to flash flooding and post-fire debris flows at 30 m.
Answers "where does violent water go?", complementing the wildfire layer's "where does
fire go?" Validated against the 13–16 Feb 2025 storm — see Validation.

## Inputs
| Factor | Weight | Source | Logic |
|---|---|---|---|
| Drainage convergence | 45% (gate) | D8 upslope contributing area, Copernicus DEM GLO-30, pysheds | log-scaled 900 m²→10 km². No upslope water = no flood, regardless of other factors |
| Receiving slope | 30% | same DEM, numpy gradient | flat ground (0–10°) ponds and amplifies convergence |
| Upstream burn-scar | 25% | T15 wildfire classes ≥3, weighted flow accumulation | fraction of upslope area burn-prone, full weight at 30% — burned catchments hydrophobe and debris-load runoff |

risk = 100 × (0.45·drainage + 0.30·receiving·drainage + 0.25·burnfrac·drainage),
classes 0–4 at 20/40/60/80. Land mask: OSM municipality polygons (admin_level 7, 780 km²);
sea handled as −5 m so coastal flow drains offshore; 5-cell grid-edge clip (rectangle-cut
accumulation is artifact).

## Validation (16 Feb 2025 in.gr reporting vs model, 600 m radius, max risk)
Τραπεζάκι ("the beach no longer exists") **97.5** — highest on the island ·
Πόρος gap (road became a torrent) **96.9** · Περατάτα (speedboat deployed, worst in 60
years) **94.6** · Βλαχάτα **69.2**. Every article-named flood location carries class 3–4
pixels, and the model's ranking matches the reporting.

## Results
Class distribution (PostGIS): 0=731,666 · 1=90,278 · 2=24,153 · 3=7,890 · 4=3,411 px
→ very-high ≈ **3.0 km²**. Island mean risk 11.3/100. Ainos ridge correctly dark (steep
but no upslope area — different hazard than wildfire, different map).

## Limitations (read before using)
1. **Karst.** Kefalonia's limestone routes water underground (the Katavothres sinkholes at
   Argostoli swallow the sea itself). DEM surface-routing overstates surface convergence in
   karstic catchments.
2. **Fluvial-only v1.** The Feb 2025 plain flooding (Livadi fields under 1.5 m) was largely
   *pluvial* — rain rate overwhelming flat, poorly-drained ground, no large upstream
   catchment needed. Our drainage gate under-reads exactly that geometry. v1.1: pluvial
   ponding term (flat + low-lying + closed-depression). (Caught by local-knowledge review —
   the sanity check working as designed.)
3. No rainfall input — terrain susceptibility, not a forecast. Dynamic coupling with
   Open-Meteo extreme-rain forecasts is Phase 2 (T32).
4. 30 m DEM misses culverts, walls, road drainage — the features that decide street-level floods.
5. Burn-scar proxy uses wildfire *susceptibility* (T15), not observed perimeters, until
   T15.1 lands EFFIS validation.

## Roadmap
- v1.1: pluvial ponding term; EFFIS-informed burn-scar (post-T15.1)
- v1.2: × Open-Meteo extreme-rain forecast → dynamic daily flood outlook (T32)
- v2.0: couple with travel-time layer (T16) → flood-isolation risk per settlement

*License: CC BY 4.0 the layer, MIT the code. Built in the open — if you're a hydrologist
or a local who watched the Feb 2025 floods, open an issue. That's the point.*
