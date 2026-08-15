#!/usr/bin/env python3
"""T17 portrait: argos_flashflood_map.png — brand-styled class map."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np, rasterio
from matplotlib.colors import ListedColormap, BoundaryNorm
from PIL import Image

NAVY='#0a1628'; GOLD='#c9a227'; PARCH='#f4eee0'; SEA='#7fa89b'; MUT='#8a9ab0'

src = rasterio.open('data/kefalonia_flashflood_risk_class_4326.tif')
cls = src.read(1).astype('float32')
cls[cls == -9999] = np.nan
b = src.bounds

cmap = ListedColormap(['#16233a', '#24507f', '#3580b8', '#4fb3d9', '#aef3fb'])
norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)

fig, ax = plt.subplots(figsize=(10, 10), facecolor=NAVY)
ax.set_facecolor(NAVY)
ax.imshow(cls, cmap=cmap, norm=norm,
          extent=[b.left, b.right, b.bottom, b.top], interpolation='nearest')
ax.set_xlim(20.30, 20.90); ax.set_ylim(37.95, 38.55)   # NEVER autoscale (T12 gotcha)
ax.axis('off')

ax.set_title('ARGOS WATCH — Flash-Flood Susceptibility v1',
             color=GOLD, fontsize=15, fontweight='bold', pad=14)
ax.text(0.5, 1.005, 'drainage convergence x receiving slope x upstream burn-scar',
        transform=ax.transAxes, ha='center', color=MUT, fontsize=9)
ax.text(0.5, -0.02, 'argos-geo.org — Watching over the places we call home.',
        transform=ax.transAxes, ha='center', color=SEA, fontsize=8, style='italic')

labels = ['0 very low', '1 low', '2 moderate', '3 high', '4 very high']
handles = [mpatches.Patch(color=c, label=l) for c, l in zip(cmap.colors, labels)]
leg = ax.legend(handles=handles, loc='lower left', fontsize=8, frameon=True,
                facecolor=NAVY, edgecolor='#8a7a3a', labelcolor=PARCH)

plt.savefig('argos_flashflood_map.png', dpi=160, bbox_inches='tight', facecolor=NAVY)
Image.open('argos_flashflood_map.png').load()   # T15 gotcha: verify, don't trust "saved"
print('portrait OK:', Image.open('argos_flashflood_map.png').size)
