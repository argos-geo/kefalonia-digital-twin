#!/usr/bin/env python3
# Script 66: regenerate site/map.html (Wrangler/CF door) from docs/index.html (canonical master).
# Rule after 23 Oct regression: docs/ is the single source, site/ is generated, never hand-edited or zip-restored.
import pathlib
BASE = 'https://argos-geo.github.io/kefalonia-digital-twin'
root = pathlib.Path(__file__).resolve().parent.parent
src = (root / 'docs' / 'index.html').read_text(encoding='utf-8')
out = (src
    .replace('src="./assets/', f'src="{BASE}/assets/')
    .replace('href="./assets/', f'href="{BASE}/assets/')
    .replace("'./assets/", f"'{BASE}/assets/")
    .replace("'./tiles/", f"'{BASE}/tiles/")
    .replace("data: './kefalonia_land.geojson'", f"data: '{BASE}/kefalonia_land.geojson'")
    .replace("data: './bathymetry_contours.geojson'", f"data: '{BASE}/bathymetry_contours.geojson'")
    .replace('id="home-pill" href="https://argos-geo.org"', 'id="home-pill" href="/"'))
residual = sum(out.count(t) for t in ("'./assets/", "'./tiles/", "data: './", 'src="./', 'href="./'))
assert residual == 0, f"FAIL: {residual} residual relative refs"
for token in ('zoomtoast', 'webgl-fallback', 'marine-on'):
    assert out.count(token) >= 1, f"FAIL: {token} missing from generated master"
(root / 'site' / 'map.html').write_text(out, encoding='utf-8')
print(f"OK site/map.html regenerated: {len(out)} chars, 0 residual refs, token checks passed")
