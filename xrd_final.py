# -*- coding: utf-8 -*-
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import struct, numpy as np, warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from scipy.signal import find_peaks

# ============================================================
# RAW1.01 file parser
# ============================================================
def read_raw_counts(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    n = (len(data) - 36) // 2
    vals = np.array(struct.unpack(f'<{n}H', data[36:36+n*2]))
    return vals[1::2]  # odd indices

# ============================================================
# Data loading
# ============================================================
files = [
    (r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw', '\u94dc\u786b\u77ff\u539f\u77ff', 'Raw Ore'),
    (r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw', '\u94dc\u786b\u77ff\u7cbe\u77ff', 'Concentrate'),
    (r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw', '\u94dc\u786b\u77ff\u5c3e\u77ff', 'Tailings'),
]

counts_list = []
for fpath, name_cn, name_en in files:
    c = read_raw_counts(fpath)
    counts_list.append(c)
    print(f"Loaded: {name_en} ({name_cn}), n={len(c)}, max={c.max()}")

n_pts = min(len(c) for c in counts_list)
print(f"Using n_pts={n_pts}")

# Angle calibration: start=7.25, step=0.01916 (validated by mineral matching)
angles = np.linspace(7.25, 7.25 + (n_pts-1)*0.01916, n_pts)
print(f"Angle range: {angles[0]:.2f} - {angles[-1]:.2f}")

# ============================================================
# Mineral reference peaks (Cu K-alpha, 2theta deg)
# ============================================================
min_refs = {
    'CuFeS2': {'name': 'Chalcopyrite', 'peaks': [29.32, 33.85, 36.70, 42.80, 49.32, 58.29, 59.02], 'color': '#C0392B'},
    'FeS2':   {'name': 'Pyrite',       'peaks': [28.52, 33.08, 37.64, 40.78, 47.44, 56.28, 59.36], 'color': '#E67E22'},
    'Cu2S':   {'name': 'Chalcocite',   'peaks': [24.69, 27.88, 32.52, 37.73, 45.90],                'color': '#8E44AD'},
    'SiO2':   {'name': 'Quartz',       'peaks': [20.85, 26.64, 36.54, 39.47, 42.44, 50.14, 59.96, 68.15], 'color': '#2980B9'},
    'CaCO3':  {'name': 'Calcite',      'peaks': [29.41, 39.46, 43.15, 47.12, 48.53, 57.41],         'color': '#27AE60'},
    'CuS':    {'name': 'Covellite',    'peaks': [27.96, 29.28, 31.36, 48.04, 59.26],                'color': '#16A085'},
    'Cu5FeS4':{'name': 'Bornite',      'peaks': [23.34, 29.78, 33.38, 36.38, 46.02],                'color': '#D35400'},
    'CaMg(CO3)2': {'name': 'Dolomite', 'peaks': [30.96, 37.40, 41.14, 44.01, 51.07],               'color': '#1ABC9C'},
}

# ============================================================
# Peak detection + mineral assignment
# ============================================================
def get_peak_assignments(counts, angles, tolerance=0.4, height_ratio=0.12, min_distance=8):
    threshold = counts.max() * height_ratio
    peak_idx, props = find_peaks(counts, height=threshold, distance=min_distance)
    peak_angles = angles[peak_idx]
    peak_heights = props['peak_heights']

    assignments = []  # list of (angle, height, mineral_key)
    for pa, ph in zip(peak_angles, peak_heights):
        best = None
        best_diff = 999
        for mkey, minfo in min_refs.items():
            for ref in minfo['peaks']:
                diff = abs(pa - ref)
                if diff < best_diff:
                    best = mkey
                    best_diff = diff
        if best and best_diff < tolerance:
            assignments.append((pa, ph, best, best_diff))

    return peak_idx, peak_angles, peak_heights, assignments

# ============================================================
# Configure fonts (use DejaVu which supports Unicode subscripts)
# ============================================================
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# Plot single spectrum
# ============================================================
def plot_single(idx, counts, angles, name_en, name_cn, savepath):
    print(f"\n--- Plotting: {name_en} ---")
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=100)

    ax.fill_between(angles, counts, alpha=0.25, color='#4472C4', linewidth=0)
    ax.plot(angles, counts, color='#1F3864', linewidth=0.8)

    _, _, _, assignments = get_peak_assignments(counts, angles)

    # Group by mineral
    by_mineral = {}
    for pa, ph, mkey, diff in assignments:
        if mkey not in by_mineral:
            by_mineral[mkey] = []
        by_mineral[mkey].append((pa, ph, diff))

    detected = list(by_mineral.keys())
    print(f"  Detected minerals: {detected}")

    # Print peaks per mineral
    for mkey, peaks_data in by_mineral.items():
        peak_angles_str = ', '.join([f"{p[0]:.2f}" for p in peaks_data])
        print(f"  {mkey} ({min_refs[mkey]['name']}): {peak_angles_str}")

    # Annotate peaks - label the most prominent peaks
    labeled = {}  # mineral -> last angle (to avoid overlap)
    y_max = counts.max()

    for pa, ph, mkey, diff in sorted(assignments, key=lambda x: -x[1]):
        mcolor = min_refs[mkey]['color']
        # Only label if this is within tolerance
        if diff >= 0.4:
            continue
        # Offset to avoid overlap
        y_off = y_max * 0.08
        dy = 0
        if mkey in labeled:
            if abs(pa - labeled[mkey]) < 1.0:
                dy = y_max * 0.12
        labeled[mkey] = pa

        ax.annotate(
            mkey,
            xy=(pa, ph),
            xytext=(pa, ph + y_off + dy),
            fontsize=8,
            color=mcolor,
            ha='center', va='bottom',
            fontweight='bold',
        )
        ax.plot(pa, ph, 's', color=mcolor, ms=4, zorder=6, markeredgecolor='white', markeredgewidth=0.5)

    # Build label text with detected minerals
    label_text = 'Detected: ' + ', '.join(detected)

    ax.set_xlabel(r'2$\theta$ ($^\circ$)', fontsize=12)
    ax.set_ylabel('Intensity (counts)', fontsize=12)
    ax.set_title(f'{name_en} XRD Pattern', fontsize=13, fontweight='bold', pad=10)
    ax.set_xlim(8, 70)
    ax.set_ylim(0, y_max * 1.28)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.25, linestyle=':', color='gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add detected minerals as text box
    ax.text(0.98, 0.97, label_text, transform=ax.transAxes,
            fontsize=8, va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'))

    fig.tight_layout()
    fig.savefig(savepath, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {savepath}")
    return detected

# ============================================================
# Plot comparison
# ============================================================
def plot_comparison(counts_list, angles, names_en, names_cn, savepath):
    print(f"\n--- Plotting Comparison ---")
    fig, ax = plt.subplots(figsize=(13, 7.5), dpi=100)

    y_max_global = max(c.max() for c in counts_list)
    colors = ['#1F3864', '#C0392B', '#27AE60']
    offsets = [0, y_max_global * 0.55, y_max_global * 1.1]

    for i, (counts, name_en, name_cn) in enumerate(zip(counts_list, names_en, names_cn)):
        # Normalize to first sample's max for visual comparison
        norm_counts = counts / counts.max() * y_max_global
        y_offset = offsets[i]
        plot_counts = norm_counts + y_offset

        ax.fill_between(angles, y_offset, plot_counts, alpha=0.15, color=colors[i], linewidth=0)
        ax.plot(angles, plot_counts, color=colors[i], linewidth=1.2,
                label=f'{name_en} ({name_cn})')

        # Add sample label on left
        ax.text(7.8, y_offset + y_max_global * 0.05,
                f'{name_en}\n({name_cn})',
                fontsize=9, color=colors[i], ha='left', va='bottom', fontweight='bold')

        # Label peaks
        _, _, _, assignments = get_peak_assignments(counts, angles)
        last_y_for_m = {}
        y_step = y_max_global * 0.10

        for pa, ph, mkey, diff in sorted(assignments, key=lambda x: -x[1]):
            if diff >= 0.4:
                continue
            base_y = y_offset + ph / counts.max() * y_max_global
            dy = 0
            if mkey in last_y_for_m:
                if abs(pa - last_y_for_m[mkey]) < 1.2:
                    dy = y_step
            last_y_for_m[mkey] = pa
            ax.annotate(
                mkey,
                xy=(pa, base_y + dy),
                xytext=(pa, base_y + dy + y_step * 0.3),
                fontsize=7,
                color=min_refs[mkey]['color'],
                ha='center', va='bottom', fontweight='bold',
            )
            ax.plot(pa, base_y + dy, '_', color=min_refs[mkey]['color'], ms=8, mew=1.5)

    ax.set_xlabel(r'2$\theta$ ($^\circ$)', fontsize=12)
    ax.set_ylabel('Intensity (counts, offset for clarity)', fontsize=12)
    ax.set_title('XRD Comparison of Cu-S Ore Products', fontsize=14, fontweight='bold', pad=10)
    ax.set_xlim(8, 70)
    ax.set_ylim(-y_max_global*0.08, offsets[-1] + y_max_global * 1.35)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.2, linestyle=':', color='gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    ax.legend(loc='upper right', fontsize=9, framealpha=0.9)

    fig.tight_layout()
    fig.savefig(savepath, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  Saved: {savepath}")

# ============================================================
# Run
# ============================================================
y_max_global = max(c.max() for c in counts_list)

# Save paths (explicit Unicode)
desktop = r'C:\Users\Administrator\Desktop'
desktop = r'C:\Users\Administrator\Desktop'
savepaths = [
    os.path.join(desktop, 'XRD_yuankuang.png'),      # raw ore
    os.path.join(desktop, 'XRD_jingkuang.png'),     # concentrate
    os.path.join(desktop, 'XRD_weikuang.png'),      # tailings
    os.path.join(desktop, 'XRD_comparison.png'),    # comparison
]

names_en = ['Raw Ore', 'Concentrate', 'Tailings']
names_cn = ['\u539f\u77ff', '\u7cbe\u77ff', '\u5c3e\u77ff']

print("\n" + "="*60)
print("GENERATING XRD FIGURES")
print("="*60)

all_detected = []
for i in range(3):
    det = plot_single(i, counts_list[i], angles, names_en[i], names_cn[i], savepaths[i])
    all_detected.append((names_en[i], det))

plot_comparison(counts_list, angles, names_en, names_cn, savepaths[3])

print("\n" + "="*60)
print("MINERAL ANALYSIS SUMMARY")
print("="*60)
for name_en, det in all_detected:
    print(f"\n{name_en}:")
    for m in det:
        print(f"  - {m} ({min_refs[m]['name']})")

print("\nAll figures saved successfully!")
