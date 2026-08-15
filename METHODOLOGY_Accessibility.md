# ARGOS — Road & Travel-Time Accessibility Methodology (T16)
*v1 · 15 Aug 2026 · feeds wildfire v2.0 suppression access + evacuation analysis*

## What this layer answers
Not "is there a road nearby?" (Stage A — almost always yes) but
**"how long until help arrives?"** (Stage B — the real question).

## Stage A — Distance to nearest drivable road
- `road_dist_m`: KNN distance (building centroid / POI point → nearest road segment)
  over drivable classes only: `track, local, service, secondary, tertiary, primary`
  (paths/footways excluded — you can't drive them).
- `access_score`: 100 at the doorstep, linear decay to 0 at 2 km.
- **Finding:** buildings average **20 m** from a drivable road (21,971/22,013 score ≥90).
  Distance is not Kefalonia's accessibility problem — *time* is. Hence Stage B.

## Stage B — Network travel time (pgRouting 3.8)
### Network
- 21,811 segments: OSM ways dumped to simple LineStrings, then **split at every
  junction** — the critical step. OSM junctions are interior nodes of long ways;
  endpoint-only topology shatters the network (largest component was 783 vertices
  before segmentation, 17,468 = 94% after).
- Vertices: endpoints clustered at 1.0 m (UTM 34N) — absorbs coordinate drift.
- Directed: 181 oneway segments carry `reverse_cost = -1`.

### Speeds (km/h — Kefalonia-realistic defaults, open to local correction)
| Source | Value |
|---|---|
| `maxspeed` tag (capped 90) | as tagged |
| primary / secondary / tertiary | 50 / 40 / 30 |
| local / service / track | 20 / 15 / 10 |

### Destinations (from the twin's own POI layer, no hand-typed coordinates)
- **Fire response:** ΠΥ Αργοστολίου fire station (the island's only mapped station)
- **Ports/evacuation:** ferry terminals Φισκάρδο, Αργοστόλι, Ληξούρι, Πεσσάδα, Σάμη, Πόρος

### Computation
- `pgr_drivingDistance` from each destination set, `min(agg_cost)` per network vertex.
- Building time = nearest-junction time + **last-mile walk penalty** (`road_dist_m / 80` m/min).
- Unreachable → NULL, honestly (Ithaca has no bridge; bbox-corner artifacts excluded).

### Headline results (15 Aug 2026)
- 18,484 / 22,013 buildings routed · island mean 37.1 min to fire response
- Worst: **Vardiani islet — 108.1 min** (boat-only lighthouse islet; validated against
  local knowledge — the sanity check is a feature, not a formality)
- Best: Argostoli centre, 2.7 min to its own fire station

## Limitations
1. Speeds are estimates, not measurements; no traffic, no seasonal congestion.
2. Last-mile penalty walks over water for islets (Vardiani's 38-min "walk" is really a boat).
3. Single fire station = single response origin; volunteer posts not yet in OSM.
4. No ferry *schedules* — ports are treated as destinations, not as network edges.
5. 20 m/centroid resolution smoothing, as with all v1 layers.

## Roadmap
- v1.1: volunteer fire posts + ambulances as origins; heliport/sea-rescue modes
- v1.2: ferry crossings as time-cost network edges (Ithaca becomes reachable)
- v2.0: couple with wildfire risk (T15) → suppression-access surface; evacuation
  routing per settlement under ARGOS WATCH

*License: CC BY 4.0 for the layer, MIT for the code. Built in the open — if you're a
traffic engineer or island local and see a wrong number, open an issue. That's the point.*
