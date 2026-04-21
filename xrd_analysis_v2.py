#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copper-Sulfide Ore XRD Phase Analysis
Analyzes raw ore, concentrate, and tailings XRD data
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from pathlib import Path
import json

# Font settings
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11

def parse_bruker_raw(filepath):
    """Parse Bruker RAW format"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    data_section = content.split('[Data]')[-1]
    angles, intensities = [], []
    
    for line in data_section.strip().split('\n'):
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                angles.append(float(parts[0].strip()))
                intensities.append(float(parts[1].strip()))
            except:
                continue
    
    return np.array(angles), np.array(intensities)

# Standard mineral database (based on ICDD PDF cards)
MINERAL_DATABASE = {
    "Chalcopyrite (CuFeS2)": {
        "peaks": [29.42, 34.84, 36.63, 39.05, 49.25, 52.48, 58.72],
        "d_values": [3.03, 2.57, 2.45, 2.30, 1.85, 1.74, 1.57],
        "hkl": ["(112)", "(200)", "(004)", "(204)", "(312)", "(224)", "(400)"],
        "color": "#E74C3C",
        "pdf_card": "PDF#37-0475"
    },
    "Pyrite (FeS2)": {
        "peaks": [28.51, 33.08, 37.09, 40.77, 47.43, 56.28, 59.02],
        "d_values": [3.13, 2.71, 2.42, 2.21, 1.92, 1.63, 1.56],
        "hkl": ["(111)", "(200)", "(210)", "(211)", "(220)", "(311)", "(222)"],
        "color": "#F39C12",
        "pdf_card": "PDF#42-1340"
    },
    "Quartz (SiO2)": {
        "peaks": [20.85, 26.65, 36.54, 39.50, 42.47, 50.14, 54.90, 60.00, 64.05, 68.15],
        "d_values": [4.26, 3.34, 2.46, 2.28, 2.13, 1.82, 1.67, 1.54, 1.45, 1.38],
        "hkl": ["(100)", "(101)", "(110)", "(102)", "(200)", "(112)", "(211)", "(203)", "(301)", "(212)"],
        "color": "#3498DB",
        "pdf_card": "PDF#46-1045"
    },
    "Chalcocite (Cu2S)": {
        "peaks": [26.55, 32.05, 37.95, 46.28, 47.87, 55.20, 62.40],
        "d_values": [3.36, 2.79, 2.37, 1.96, 1.90, 1.66, 1.49],
        "hkl": ["(102)", "(110)", "(200)", "(212)", "(114)", "(220)", "(310)"],
        "color": "#9B59B6",
        "pdf_card": "PDF#33-0490"
    },
    "Covellite (CuS)": {
        "peaks": [27.50, 29.65, 31.90, 33.05, 48.10, 52.40, 59.60],
        "d_values": [3.24, 3.01, 2.80, 2.71, 1.89, 1.75, 1.55],
        "hkl": ["(006)", "(102)", "(104)", "(105)", "(110)", "(116)", "(205)"],
        "color": "#1ABC9C",
        "pdf_card": "PDF#06-0464"
    },
    "Bornite (Cu5FeS4)": {
        "peaks": [26.10, 32.20, 38.20, 46.50, 55.80, 58.50],
        "d_values": [3.41, 2.78, 2.36, 1.95, 1.65, 1.58],
        "hkl": ["(112)", "(200)", "(204)", "(220)", "(312)", "(224)"],
        "color": "#E67E22",
        "pdf_card": "PDF#42-1409"
    }
}

def match_phase(peak_angle, tolerance=0.4):
    """Match peak to known phases"""
    matches = []
    for mineral, data in MINERAL_DATABASE.items():
        for i, std_peak in enumerate(data["peaks"]):
            if abs(peak_angle - std_peak) <= tolerance:
                matches.append({
                    "mineral": mineral,
                    "std_peak": std_peak,
                    "d_value": data["d_values"][i],
                    "hkl": data["hkl"][i],
                    "pdf_card": data["pdf_card"],
                    "delta": abs(peak_angle - std_peak)
                })
    return sorted(matches, key=lambda x: x["delta"])

# Data paths
data_dir = Path(r"F:\桌面\王铨毕业论文\xrd数据")
files = {
    'Raw Ore': data_dir / "tongliukuang yuankuang.txt",
    'Concentrate': data_dir / "2cu2jing jingkuang tongliukuang.txt",
    'Tailings': data_dir / "2cu2jing weikuang tongliukuang.txt"
}

# Parse and analyze
datasets = {}
analysis_results = {}

print("="*70)
print("Copper-Sulfide Ore XRD Phase Analysis Report")
print("="*70)
print(f"\nInstrument: Cu Ka, lambda = 1.5406 A, 40kV/40mA")
print(f"Scan range: 5 - 80 deg 2Theta")
print()

for name, path in files.items():
    if not path.exists():
        print(f"[Warning] File not found: {path}")
        continue
    
    angle, intensity = parse_bruker_raw(path)
    
    # Simple smoothing without aggressive background removal
    smoothed = savgol_filter(intensity, 11, 3)
    
    # Subtract simple linear baseline
    baseline = np.polyfit(angle, smoothed, 1)
    baseline_curve = np.polyval(baseline, angle)
    bg_removed = smoothed - baseline_curve
    bg_removed = np.maximum(bg_removed, 0)
    
    datasets[name] = (angle, bg_removed, intensity)
    
    # Peak detection with lower threshold
    max_int = np.max(bg_removed)
    peaks, properties = find_peaks(
        bg_removed, 
        height=0.03 * max_int,  # Lower threshold
        prominence=0.02 * max_int,
        distance=20,
        width=2
    )
    
    peak_angles = angle[peaks]
    peak_intensities = bg_removed[peaks]
    
    # Sort by intensity
    sorted_idx = np.argsort(peak_intensities)[::-1]
    
    print(f"\n{'='*70}")
    print(f"[{name}]")
    print(f"File: {path.name}")
    print(f"Data points: {len(angle)}, Range: {angle[0]:.1f} - {angle[-1]:.1f} deg")
    print(f"Detected {len(peaks)} diffraction peaks")
    print("-"*70)
    
    analysis_results[name] = {
        'peaks': [],
        'identified_minerals': set()
    }
    
    # Output main peaks and phase matching
    print(f"{'Peak(2th)':<12} {'Intensity':<12} {'d(A)':<10} {'Phase Match':<30} {'hkl':<10}")
    print("-"*70)
    
    for i, idx in enumerate(sorted_idx[:15]):  # Top 15 peaks
        pa = peak_angles[idx]
        pi = peak_intensities[idx]
        d_value = 1.5406 / (2 * np.sin(np.radians(pa / 2)))
        
        matches = match_phase(pa)
        
        if matches:
            best_match = matches[0]
            mineral_short = best_match['mineral'].split('(')[0].strip()
            print(f"{pa:<12.2f} {pi:<12.0f} {d_value:<10.3f} {mineral_short:<30} {best_match['hkl']:<10}")
            analysis_results[name]['identified_minerals'].add(best_match['mineral'])
            analysis_results[name]['peaks'].append({
                'angle': float(pa),
                'intensity': float(pi),
                'd_value': float(d_value),
                'match': best_match
            })
        else:
            print(f"{pa:<12.2f} {pi:<12.0f} {d_value:<10.3f} {'No match':<30} {'-':<10}")
            analysis_results[name]['peaks'].append({
                'angle': float(pa),
                'intensity': float(pi),
                'd_value': float(d_value),
                'match': None
            })

# Phase summary
print(f"\n{'='*70}")
print("Phase Identification Summary")
print("="*70)

for name in ['Raw Ore', 'Concentrate', 'Tailings']:
    minerals = analysis_results.get(name, {}).get('identified_minerals', set())
    print(f"\n{name} Main Phases:")
    if minerals:
        for m in minerals:
            print(f"  - {m}")
    else:
        print("  - (No phases identified)")

# Generate comparison plot
fig, ax = plt.subplots(figsize=(16, 10))

colors = {'Raw Ore': '#2C3E50', 'Concentrate': '#E74C3C', 'Tailings': '#27AE60'}
offsets = {'Raw Ore': 0, 'Concentrate': 400, 'Tailings': 800}

# Plot spectra
for name, (angle, bg_removed, raw_intensity) in datasets.items():
    ax.plot(angle, bg_removed + offsets[name], color=colors[name], 
            linewidth=0.7, label=name, alpha=0.9)

# Annotate mineral peaks
annotation_y = max(offsets.values()) + 150

for mineral, data in MINERAL_DATABASE.items():
    for i, peak in enumerate(data['peaks'][:2]):  # First 2 peaks only
        ax.axvline(x=peak, color=data['color'], linestyle='--', alpha=0.3, linewidth=0.8)
    
    # Label at first peak
    short_name = mineral.split('(')[0].strip()
    ax.text(data['peaks'][0], annotation_y, short_name, fontsize=8, ha='center',
           color=data['color'], fontweight='bold', rotation=90, va='bottom')

ax.set_xlabel('2Theta (degrees)', fontsize=14, fontweight='bold')
ax.set_ylabel('Intensity (a.u.)', fontsize=14, fontweight='bold')
ax.set_title('XRD Patterns of Copper-Sulfide Ore Flotation Products\nCu Ka radiation, lambda = 1.5406 A', 
            fontsize=16, fontweight='bold', pad=20)
ax.legend(loc='upper right', fontsize=12, framealpha=0.95)
ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_xlim(5, 80)
ax.set_ylim(-20, annotation_y + 80)

# Add phase identification box
textstr = 'Phase Identification:\n'
textstr += 'Chalcopyrite (CuFeS2) - PDF#37-0475\n'
textstr += 'Pyrite (FeS2) - PDF#42-1340\n'
textstr += 'Quartz (SiO2) - PDF#46-1045\n'
textstr += 'Chalcocite (Cu2S) - PDF#33-0490'

props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray')
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
       verticalalignment='top', bbox=props, family='monospace')

plt.tight_layout()

# Save
output_path = data_dir / "XRD_Phase_Analysis_Report.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n[OK] Saved: {output_path}")

output_pdf = data_dir / "XRD_Phase_Analysis_Report.pdf"
plt.savefig(output_pdf, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[OK] Saved: {output_pdf}")

# Save JSON results
for name in analysis_results:
    analysis_results[name]['identified_minerals'] = list(analysis_results[name]['identified_minerals'])

json_output = data_dir / "XRD_Analysis_Results.json"
with open(json_output, 'w', encoding='utf-8') as f:
    json.dump(analysis_results, f, ensure_ascii=False, indent=2)
print(f"[OK] Saved: {json_output}")

print("\n" + "="*70)
print("Analysis Complete!")
print("="*70)
