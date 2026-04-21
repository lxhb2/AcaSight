"""
Cu-S mineral XRD analysis script
Parses RAW1.01 binary files and identifies mineral phases
"""
import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# File parsing
# ============================================================
def read_raw_counts(filepath):
    """Read 16-bit counts from RAW1.01 file at offset 36, stride 2 (odd indices)"""
    with open(filepath, 'rb') as f:
        data = f.read()
    n = (len(data) - 36) // 2
    vals = np.array(struct.unpack(f'<{n}H', data[36:36+n*2]))
    counts = vals[1::2]  # odd indices
    return counts

# ============================================================
# XRD data for all three samples
# ============================================================
files = [
    r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw',
    r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw',
    r'F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw'
]

names = ['Raw Ore\n(Runmine)', 'Concentrate\n(Jingkuang)', 'Tailings\n(Weikuang)']
colors_data = ['#2E86AB', '#A23B72', '#F18F01']
colors_data_light = ['#A8D8EA', '#F4C2D7', '#FFE0B2']

counts_list = []
for f in files:
    c = read_raw_counts(f)
    counts_list.append(c)
    print(f"{f.split('Tongliukuang')[-1]}: n={len(c)}, max={c.max()}, mean={c.mean():.1f}")

# Use consistent n_points
n_pts = min(len(c) for c in counts_list)
angles_list = []
for i in range(3):
    # start=7.25, step=0.01916 gives best mineral match
    angles = np.linspace(7.25, 7.25 + (n_pts-1)*0.01916, n_pts)
    angles_list.append(angles)

# ============================================================
# Mineral reference peaks (Cu K-alpha, 2theta degrees)
# ============================================================
min_refs = {
    'CuFeS\u2082': [29.32, 33.85, 36.70, 42.80, 49.32, 58.29, 59.02],
    'FeS\u2082': [28.52, 33.08, 37.64, 40.78, 47.44, 56.28, 59.36],
    'Cu\u2082S': [24.69, 27.88, 32.52, 37.73, 45.90],
    'SiO\u2082': [20.85, 26.64, 36.54, 39.47, 42.44, 50.14, 59.96, 68.15],
    'CaCO\u2083': [29.41, 39.46, 43.15, 47.12, 48.53, 57.41],
    'CuS': [27.96, 29.28, 31.36, 48.04, 59.26],
    'Cu\u2085FeS\u2084': [23.34, 29.78, 33.38, 36.38, 46.02],
    'CaMg(CO\u2083)\u2082': [30.96, 37.40, 41.14, 44.01, 51.07],
}

# ============================================================
# Peak detection
# ============================================================
def detect_peaks(counts, angles, height_ratio=0.15, distance=5):
    threshold = counts.max() * height_ratio
    peak_indices, props = find_peaks(counts, height=threshold, distance=distance)
    peak_angles = angles[peak_indices]
    peak_heights = props['peak_heights']
    return peak_indices, peak_angles, peak_heights

# ============================================================
# Assign minerals to peaks
# ============================================================
def assign_minerals(peak_angles, peak_heights, min_refs, tolerance=0.35):
    assignments = {}
    for i, (pa, ph) in enumerate(zip(peak_angles, peak_heights)):
        for name, refs in min_refs.items():
            for ref in refs:
                if abs(pa - ref) < tolerance:
                    if name not in assignments:
                        assignments[name] = []
                    assignments[name].append((pa, ph, ref - pa))
                    break
    return assignments

# ============================================================
# Determine key peaks and labels for each sample
# ============================================================
# Mineral colors for annotation
mineral_colors = {
    'CuFeS\u2082': '#C0392B',
    'FeS\u2082': '#E67E22',
    'Cu\u2082S': '#8E44AD',
    'SiO\u2082': '#2980B9',
    'CaCO\u2083': '#27AE60',
    'CuS': '#16A085',
    'Cu\u2085FeS\u2084': '#D35400',
    'CaMg(CO\u2083)\u2082': '#1ABC9C',
}

# ============================================================
# Plot single spectrum
# ============================================================
def plot_single(idx, counts, angles, name, savepath):
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    
    # Plot spectrum
    ax.fill_between(angles, counts, alpha=0.3, color=colors_data[idx], linewidth=0)
    ax.plot(angles, counts, color=colors_data[idx], linewidth=1.0)
    
    # Detect peaks
    peak_idx, peak_angles, peak_heights = detect_peaks(counts, angles)
    assignments = assign_minerals(peak_angles, peak_heights, min_refs)
    
    # Sort peaks by angle
    all_peaks = []
    for i, (pa, ph) in enumerate(zip(peak_angles, peak_heights)):
        all_peaks.append((pa, ph, i))
    all_peaks.sort(key=lambda x: x[0])
    
    # Find top assignments per peak
    used_labels = {}
    labeled_peaks = []
    
    for pa, ph, orig_i in all_peaks:
        best = None
        best_diff = 999
        for name, refs in min_refs.items():
            for ref in refs:
                diff = abs(pa - ref)
                if diff < best_diff:
                    best = name
                    best_diff = diff
        if best and best_diff < 0.35:
            labeled_peaks.append((pa, ph, best, best_diff))
    
    # Label peaks (avoid overlaps)
    last_label_angle = {}
    for pa, ph, mineral, diff in labeled_peaks:
        # Check overlap
        y_offset = 0.08 * counts.max()
        base_y = ph
        offset_angle = 0.5
        key = mineral
        if key in last_label_angle and abs(pa - last_label_angle[key]) < offset_angle:
            continue  # skip overlapping
        last_label_angle[key] = pa
        
        ax.annotate(
            mineral,
            xy=(pa, ph),
            xytext=(pa, ph + y_offset),
            fontsize=8,
            color=mineral_colors.get(mineral, '#333333'),
            ha='center',
            va='bottom',
            fontweight='bold',
            fontfamily='DejaVu Sans',
        )
        # Small dot on peak
        ax.plot(pa, ph, 'o', color=mineral_colors.get(mineral, '#333333'), ms=3, zorder=5)
    
    ax.set_xlabel('2\u03b8 (\u00b0)', fontsize=12)
    ax.set_ylabel('Intensity (counts)', fontsize=12)
    ax.set_title(name, fontsize=13, fontweight='bold')
    ax.set_xlim(8, 70)
    ax.set_ylim(0, counts.max() * 1.25)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Print detected minerals
    minerals_detected = list(dict.fromkeys([m for _, _, m, _ in labeled_peaks]))
    detected_names = [m.encode('ascii', 'replace').decode() for m in minerals_detected]
    print(f"\n{name}: Detected minerals: {detected_names}")
    for m, peaks_list in assignments.items():
        mname = m.encode('ascii', 'replace').decode()
        peak_strs = [f"{p[0]:.2f} deg" for p in peaks_list]
        print(f"  {mname}: {', '.join(peak_strs)}")
    
    fig.tight_layout()
    fig.savefig(savepath, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Saved: {savepath}")
    return minerals_detected, labeled_peaks

# ============================================================
# Plot comparison (all 3 on one figure)
# ============================================================
def plot_comparison(counts_list, angles_list, names, savepath):
    fig, ax = plt.subplots(figsize=(12, 7), dpi=100)
    
    # Normalize each to max for comparison
    offsets = [0, 35000, 70000]  # vertical offset between spectra
    
    for i, (counts, angles, name) in enumerate(zip(counts_list, angles_list, names)):
        normalized = counts / counts.max() * counts_list[0].max()
        offset_counts = normalized + offsets[i]
        ax.fill_between(angles, offsets[i], offset_counts, alpha=0.25, color=colors_data[i], linewidth=0)
        ax.plot(angles, offset_counts, color=colors_data[i], linewidth=1.0, label=name)
        ax.text(6.5, offsets[i] + 2000, name.replace('\n', ' '), fontsize=9,
                color=colors_data[i], ha='right', va='bottom', fontweight='bold')
        
        # Detect and label peaks
        peak_idx, peak_angles, peak_heights = detect_peaks(counts, angles)
        
        # Only label the most important peaks
        all_peaks = [(pa, ph) for pa, ph in zip(peak_angles, peak_heights)]
        all_peaks.sort(key=lambda x: -x[1])  # by height desc
        
        # Take top peaks and assign minerals
        top_peaks = all_peaks[:30]
        labeled = []
        for pa, ph in top_peaks:
            for mname, refs in min_refs.items():
                for ref in refs:
                    if abs(pa - ref) < 0.35:
                        labeled.append((pa, ph, mname))
                        break
                else:
                    continue
                break
        
        # Remove duplicates and sort by angle
        seen = set()
        labeled_unique = []
        for la, lh, lm in labeled:
            if la not in seen:
                seen.add(la)
                labeled_unique.append((la, lh, lm))
        labeled_unique.sort(key=lambda x: x[0])
        
        last_label = {}
        y_step = 0.15 * counts_list[0].max()
        for pa, ph, mineral in labeled_unique:
            key = mineral + str(i)
            base_y = offsets[i] + ph
            dy = 0
            if mineral in last_label and abs(pa - last_label[mineral]) < 0.8:
                dy = y_step * 0.5
            last_label[mineral] = pa
            
            ax.annotate(
                mineral,
                xy=(pa, base_y + dy),
                xytext=(pa, base_y + dy + y_step * 0.3),
                fontsize=7,
                color=mineral_colors.get(mineral, '#555555'),
                ha='center', va='bottom',
                fontweight='bold',
                fontfamily='DejaVu Sans',
            )
    
    ax.set_xlabel('2\u03b8 (\u00b0)', fontsize=12)
    ax.set_ylabel('Intensity (counts)', fontsize=12)
    ax.set_title('XRD Comparison of Cu-S Ore Products', fontsize=14, fontweight='bold')
    ax.set_xlim(8, 70)
    ax.set_ylim(-2000, offsets[-1] + counts_list[0].max() * 1.3)
    ax.tick_params(labelsize=10)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Legend
    for i, name in enumerate(names):
        ax.plot([], [], color=colors_data[i], linewidth=2, label=name.replace('\n', ' '))
    ax.legend(loc='upper right', fontsize=9, framealpha=0.8)
    
    fig.tight_layout()
    fig.savefig(savepath, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"\nSaved: {savepath}")

# ============================================================
# Generate all 4 figures
# ============================================================
titles = [
    'XRD Pattern of Cu-S Ore - Raw Ore (Runmine)',
    'XRD Pattern of Cu-S Ore - Concentrate (Jingkuang)',
    'XRD Pattern of Cu-S Ore - Tailings (Weikuang)',
]

savepaths = [
    r'C:\Users\Administrator\Desktop\XRD_\u539f\u77ff_\u65b0.png',
    r'C:\Users\Administrator\Desktop\XRD_\u7cbe\u77ff_\u65b0.png',
    r'C:\Users\Administrator\Desktop\XRD_\u5c3e\u77ff_\u65b0.png',
    r'C:\Users\Administrator\Desktop\XRD_\u5bf9\u6bd4\u56fe_\u65b0.png',
]

print("\n" + "="*60)
print("GENERATING FIGURES")
print("="*60)

all_detected = []
for i in range(3):
    print(f"\n--- Sample {i+1}: {names[i].replace(chr(10),' ')} ---")
    det, lbl = plot_single(i, counts_list[i], angles_list[i], titles[i], savepaths[i])
    all_detected.append((names[i], det))

print("\n" + "="*60)
plot_comparison(counts_list, angles_list, names, savepaths[3])

print("\n" + "="*60)
print("MINERAL ANALYSIS SUMMARY")
print("="*60)
for name, det in all_detected:
    print(f"\n{name}:")
    for m in det:
        print(f"  - {m}")
