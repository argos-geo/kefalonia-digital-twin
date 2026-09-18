# ARGOS WATCH — Flash-Flood / Post-Fire Debris-Flow Susceptibility v1: Methodology
*Kefalonia Digital Twin · September 2026 · v1.1 (screening layer, not a forecast)*

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
| Pluvial ponding (v1.1) | capped override | topographic wetness index (TWI), same DEM | flat, low-lying ground ponds with no upstream catchment; raises risk to 75 × receiving × wetness, capped at class 3 |


risk = 100 × (0.45·drainage + 0.30·receiving·drainage + 0.25·burnfrac·drainage),
classes 0–4 at 20/40/60/80. v1.1 (18 Sep 2026): risk = max(v1, 75 · receiving · wetness), wetness = clip((TWI − 8)/4, 0, 1), TWI = ln(a_spec / tan(max(slope, 0.5°))), a_spec = (upslope_m² + 900)/30; pluvial-only cells cap at 75, so class 4 stays fluvial-only (count frozen at 3,387 px). Land mask: OSM municipality polygons (admin_level 7, 780 km²);
sea handled as −5 m so coastal flow drains offshore; 5-cell grid-edge clip (rectangle-cut
accumulation is artifact).

## Validation (16 Feb 2025 in.gr reporting vs model, 600 m radius, max risk)
Τραπεζάκι ("the beach no longer exists") **97.5** — highest on the island ·
Πόρος gap (road became a torrent) **96.9** · Περατάτα (speedboat deployed, worst in 60
years) **94.6** · Βλαχάτα **69.2**. Every article-named flood location carries class 3–4
pixels, and the model's ranking matches the reporting.
v1.1 cross-checks (18 Sep 2026): storm-site maxes identical to v1 (97.5 / 96.9 / 94.6 / 71.6 across the pins), Ainos ridge unchanged (38.0); the pluvial term moves medians, not maxes: Livadi 10.0 → 12.8, Koutavos 5.9 → 7.6, Omala 23.0 → 27.5 (600 m circles, max + p50 protocol). Independent corroboration: the ΓΓΠΠ historical-flood map (Sep 2022, pre-storm) places recorded flood points and high-risk zones on v1.1 lit ground: Lixouri bay head (Livadi), Argostoli waterfront, the south-coast Livatho villages, Omala, Πόρος/Σκάλα.

## Results
Class distribution (PostGIS): 0=731,666 · 1=90,278 · 2=24,153 · 3=7,890 · 4=3,411 px
→ very-high ≈ **3.0 km²**. Island mean risk 11.3/100. Ainos ridge correctly dark (steep
but no upslope area — different hazard than wildfire, different map).
v1.1 (dev rasters, 18 Sep 2026): 0=736,557 · 1=89,629 · 2=25,326 · 3=11,365 · 4=3,387 px; 23,563 px changed (21.2 km², 2.7% of land), 4,364 cells promoted class 0-1 → 2-3, class 4 frozen (3,387 = 3,387).

## Limitations (read before using)
1. **Karst.** Kefalonia's limestone routes water underground (the Katavothres sinkholes at
   Argostoli swallow the sea itself). DEM surface-routing overstates surface convergence in
   karstic catchments.
2. **Pluvial term is terrain-only (v1.1).** A TWI ponding term now covers the Livadi-style
   gap (flat fields, no upstream catchment), capped at class 3. But it is static terrain
   wetness: with no rainfall or soil input, field-cell medians move modestly (Livadi
   10.0 → 12.8) and plain flooding still reads weaker than the Feb 2025 event. A
   closed-depression gate was tested and rejected: karst sinks (Omala, 39 m deep) are
   drainage features, not ponds.
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
