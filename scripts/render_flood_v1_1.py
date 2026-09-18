#!/usr/bin/env python3
"""Flood v1.1 review render: v1 vs v1.1 classes, island + Livadi + Argostoli
insets. Brand colors, warm flood ramp (batch2c), explicit bbox (autoscale gotcha)."""
import numpy as np
import rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

NAVY = '#0a1628'
PARCH = '#f4eee0'
CMAP = ListedColormap([PARCH, '#f9d9a8', '#E67E22', '#E74C3C', '#FF3333'])
NORM = BoundaryNorm([0, 1, 2, 3, 4, 5], CMAP.N)
ISLAND = (20.30, 37.95, 20.90, 38.55)

def load(path):
    with rasterio.open(path) as s:
        a = s.read(1).astype('float32')
        a[a == -9999] = np.nan
        return a, (s.bounds.left, s.bounds.right, s.bounds.bottom, s.bounds.top)

v1, e1 = load('data/kefalonia_flashflood_risk_class_4326.tif')
v11, e2 = load('data/kefalonia_flashflood_risk_v1_1_class_4326.tif')

panels = [
    ('Island v1', v1, e1, ISLAND), ('Island v1.1', v11, e2, ISLAND),
    ('Livadi v1', v1, e1, (20.40, 38.24, 20.45, 38.275)),
    ('Livadi v1.1', v11, e2, (20.40, 38.24, 20.45, 38.275)),
    ('Argostoli plain v1', v1, e1, (20.47, 38.15, 20.53, 38.19)),
    ('Argostoli plain v1.1', v11, e2, (20.47, 38.15, 20.53, 38.19)),
]
fig, axes = plt.subplots(3, 2, figsize=(16, 18))
for ax, (title, arr, ext, (x0, y0, x1, y1)) in zip(axes.flat, panels):
    ax.set_facecolor('#dce8f0')
    ax.imshow(arr, extent=ext, cmap=CMAP, norm=NORM, interpolation='nearest', origin='upper')
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title(title, color=NAVY, fontsize=13)
    ax.tick_params(colors=NAVY, labelsize=7)
fig.suptitle('ARGOS WATCH flood: v1 vs v1.1 (pluvial term, cap 75)', color=NAVY, fontsize=15)
fig.patch.set_facecolor('white')
fig.tight_layout()
fig.savefig('argos_flood_v1_1_review.png', dpi=150)
import PIL.Image
PIL.Image.open('argos_flood_v1_1_review.png').load()
print('saved + verified: argos_flood_v1_1_review.png')
