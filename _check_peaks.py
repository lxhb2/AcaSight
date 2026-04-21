"""Quick check of peak positions and raw intensities for all samples."""
from pathlib import Path
import numpy as np

D = Path(r'F:\桌面\王铨毕业论文\xrd数据')

def load(f):
    a, i = [], []
    with open(f, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'): continue
            parts = [p.strip() for p in line.split(',')] if ',' in line else line.split()
            if len(parts) >= 2:
                try: a.append(float(parts[0])); i.append(float(parts[1]))
                except: continue
    return np.array(a), np.array(i)

def nearest_pdf(angle_deg):
    """Find nearest PDF standard peak."""
    pdf = [
        ('CuFeS2', 29.42), ('CuFeS2', 36.63), ('CuFeS2', 48.72), ('CuFeS2', 57.88),
        ('Cu2S',   26.55), ('Cu2S',   31.18), ('Cu2S',   45.92),
        ('CuS',    33.05), ('CuS',    47.92),
        ('FeS2',   33.07), ('FeS2',   56.28),
        ('SiO2',   26.65), ('SiO2',   20.85),
    ]
    best, best_d = None, 999.0
    for name, pos in pdf:
        d = abs(angle_deg - pos)
        if d < best_d:
            best_d = d; best = name
    return best, best_d

files = [
    ('Concentrate', '2cu2jing jingkuang tongliukuang_converted.txt'),
    ('Raw Ore',     'tongliukuang yuankuang.txt'),
    ('Tailings',    '2cu2jing weikuang tongliukuang.txt'),
]

for name, fname in files:
    a, i = load(D / fname)
    a = a[i >= 0]; i = i[i >= 0]
    mask = (a >= 5) & (a <= 80); x, y = a[mask], i[mask]

    # Top 8 by raw intensity
    top_idx = np.argsort(y)[-8:]
    top_idx = np.sort(top_idx)
    peaks_raw = [(x[j], y[j]) for j in top_idx]

    print(f'\n=== {name} top-8 peaks ===')
    for ang, intensity in peaks_raw:
        phase, delta = nearest_pdf(ang)
        flag = 'OK' if delta < 0.5 else ('??' if delta < 1.5 else 'XX')
        print(f'  2θ={ang:6.2f}°  I={intensity:7.0f}  → {phase:8s}  Δ={delta:.2f}°  {flag}')
