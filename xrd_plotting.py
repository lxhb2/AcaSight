#!/usr/bin/env python3
"""
XRD Plotting Script for Copper-Sulfur Ore Samples
Generates publication-quality XRD patterns with mineral phase annotations
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path
import re

# Set up publication-quality defaults with Chinese font support
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial Unicode MS', 'DejaVu Sans'],
    'font.size': 10,
    'axes.labelsize': 12,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.dpi': 100,
    'savefig.dpi': 600,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'axes.spines.top': True,
    'axes.spines.right': True,
    'axes.unicode_minus': False,  # Fix minus sign display
})

# Define mineral phases with their characteristic peaks and colors
# Using ASCII formulas for better font compatibility
MINERAL_PHASES = {
    'CuFeS2': {
        'name': 'Chalcopyrite',
        'formula': 'CuFeS$_2$',  # LaTeX style
        'formula_display': 'CuFeS₂',  # Unicode for display
        'peaks': [29.35, 33.75, 37.05, 48.70, 49.00, 57.75, 58.35],
        'color': '#E74C3C'  # Red
    },
    'FeS2': {
        'name': 'Pyrite',
        'formula': 'FeS$_2$',
        'formula_display': 'FeS₂',
        'peaks': [28.50, 33.05, 37.10, 40.75, 47.40, 56.30, 59.05, 61.70],
        'color': '#F39C12'  # Orange
    },
    'SiO2': {
        'name': 'Quartz',
        'formula': 'SiO$_2$',
        'formula_display': 'SiO₂',
        'peaks': [20.85, 26.65, 36.55, 39.45, 40.30, 42.45, 50.15, 54.90, 59.95, 64.05, 68.15],
        'color': '#3498DB'  # Blue
    },
    'CaCO3': {
        'name': 'Calcite',
        'formula': 'CaCO$_3$',
        'formula_display': 'CaCO₃',
        'peaks': [23.00, 29.40, 31.40, 36.00, 39.40, 43.15, 47.50, 48.50, 57.40],
        'color': '#27AE60'  # Green
    },
    'CaMgCO32': {
        'name': 'Dolomite',
        'formula': 'CaMg(CO$_3$)$_2$',
        'formula_display': 'CaMg(CO₃)₂',
        'peaks': [22.00, 24.00, 30.90, 33.55, 35.30, 37.40, 41.10, 44.20, 50.50],
        'color': '#9B59B6'  # Purple
    },
    'Cu2S': {
        'name': 'Chalcocite',
        'formula': 'Cu$_2$S',
        'formula_display': 'Cu₂S',
        'peaks': [26.80, 27.80, 31.80, 32.90, 37.50, 46.40, 54.80, 65.60],
        'color': '#E67E22'  # Dark Orange
    },
    'Cu5FeS4': {
        'name': 'Bornite',
        'formula': 'Cu$_5$FeS$_4$',
        'formula_display': 'Cu₅FeS₄',
        'peaks': [27.80, 30.00, 32.20, 46.40, 47.50, 54.00, 57.50, 65.80],
        'color': '#C0392B'  # Dark Red
    },
}


def parse_bruker_xrd_file(filepath):
    """Parse Bruker XRD RAW format file and extract angle and intensity data."""
    angles = []
    intensities = []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Find the [Data] section
    data_section = False
    for line in content.split('\n'):
        if '[Data]' in line:
            data_section = True
            continue
        
        if data_section:
            line = line.strip()
            if not line or line.startswith('['):
                continue
            
            # Parse data lines (Angle, PSD)
            parts = line.split(',')
            if len(parts) >= 2:
                try:
                    angle = float(parts[0].strip())
                    intensity = float(parts[1].strip())
                    angles.append(angle)
                    intensities.append(intensity)
                except ValueError:
                    continue
    
    return np.array(angles), np.array(intensities)


def identify_peaks(angles, intensities, threshold_ratio=0.08):
    """Identify significant peaks in the XRD pattern."""
    # Smooth the data slightly for peak detection
    from scipy.ndimage import gaussian_filter1d
    
    smoothed = gaussian_filter1d(intensities, sigma=1)
    
    # Calculate threshold based on background
    background = np.percentile(intensities, 10)
    max_intensity = np.max(intensities)
    threshold = background + (max_intensity - background) * threshold_ratio
    
    # Find peaks
    peaks = []
    min_distance = 3  # Minimum distance between peaks (in data points)
    
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] > threshold:
            # Check if it's a local maximum
            is_peak = True
            for j in range(max(1, i - min_distance), min(len(smoothed) - 1, i + min_distance + 1)):
                if j != i and smoothed[j] > smoothed[i]:
                    is_peak = False
                    break
            
            if is_peak:
                # Get the actual maximum near this point
                start_idx = max(0, i - min_distance)
                end_idx = min(len(intensities), i + min_distance + 1)
                local_max_idx = start_idx + np.argmax(intensities[start_idx:end_idx])
                peaks.append((angles[local_max_idx], intensities[local_max_idx]))
    
    return peaks


def match_minerals(peaks, tolerance=0.8):
    """Match peaks to known mineral phases."""
    matched = {}
    
    for mineral_key, mineral_info in MINERAL_PHASES.items():
        matched_peaks = []
        for peak_pos in mineral_info['peaks']:
            for angle, intensity in peaks:
                if abs(angle - peak_pos) < tolerance:
                    matched_peaks.append((angle, intensity, peak_pos))
                    break
        
        if matched_peaks:
            matched[mineral_key] = {
                'peaks': matched_peaks,
                'color': mineral_info['color'],
                'formula': mineral_info['formula'],  # LaTeX style
                'formula_display': mineral_info['formula_display']
            }
    
    return matched


def plot_single_xrd(angles, intensities, title, matched_minerals, save_path):
    """Plot a single XRD pattern with mineral annotations."""
    # Use LaTeX rendering for proper subscript display
    plt.rcParams['text.usetex'] = False  # Don't require LaTeX installation
    plt.rcParams['mathtext.default'] = 'regular'  # Use mathtext
    
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Plot the XRD pattern
    ax.plot(angles, intensities, 'k-', linewidth=0.8)
    
    # Add mineral phase annotations
    y_max = np.max(intensities) * 1.15
    used_positions = []
    
    # Sort minerals by first peak position for better label placement
    sorted_minerals = sorted(matched_minerals.items(), 
                             key=lambda x: min([p[0] for p in x[1]['peaks']]))
    
    for mineral_key, mineral_data in sorted_minerals:
        color = mineral_data['color']
        formula = mineral_data['formula']  # LaTeX style formula
        
        # Annotate each peak for this mineral
        for peak in mineral_data['peaks']:
            angle = peak[0]
            intensity = peak[1]
            
            # Draw vertical line from baseline to peak
            ax.plot([angle, angle], [0, intensity], color=color, 
                   linewidth=1.2, alpha=0.7)
            
            # Place annotation above the peak
            # Avoid overlapping by checking used positions
            label_angle = angle
            label_height = intensity + y_max * 0.05
            
            # Check for nearby labels and adjust
            for used_angle, used_height in used_positions:
                if abs(label_angle - used_angle) < 3:
                    label_height = max(label_height, used_height + y_max * 0.05)
            
            # Use mathtext rendering for subscript
            ax.text(angle, label_height, formula,
                   fontsize=9, color=color, fontweight='bold',
                   ha='center', va='bottom', rotation=45,
                   rotation_mode='anchor')
            
            used_positions.append((angle, label_height))
    
    # Customize axes
    ax.set_xlabel(r'$2\theta$ (°)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Intensity (a.u.)', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=12, fontweight='bold', pad=10)
    ax.set_xlim(5, 80)
    ax.set_ylim(0, y_max)
    
    # Set tick marks
    ax.set_xticks(np.arange(10, 85, 10))
    ax.tick_params(direction='in', length=5)
    
    # Add minor grid
    ax.grid(True, linestyle='--', alpha=0.3, which='major')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def plot_comparison(data_dict, save_path):
    """Plot comparison of multiple XRD patterns."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    colors = ['#E74C3C', '#27AE60', '#3498DB']  # Red, Green, Blue
    offsets = [0, 800, 1600]  # Vertical offsets for each sample
    
    # Collect all matched minerals for annotation
    all_matched = {}
    
    for idx, (sample_name, (angles, intensities)) in enumerate(data_dict.items()):
        # Normalize and offset
        normalized = intensities + offsets[idx]
        ax.plot(angles, normalized, color=colors[idx], linewidth=0.8, 
               label=sample_name, alpha=0.9)
        
        # Identify peaks for this sample
        peaks = identify_peaks(angles, intensities, threshold_ratio=0.08)
        matched = match_minerals(peaks, tolerance=0.8)
        
        # Store for common annotation
        for mineral_key, mineral_data in matched.items():
            if mineral_key not in all_matched:
                all_matched[mineral_key] = mineral_data
    
    # Add mineral annotations for significant peaks (only once)
    y_max = max([np.max(data[1]) for data in data_dict.values()]) + 2400
    
    # Sort by peak position
    annotated_angles = []
    for mineral_key, mineral_data in sorted(all_matched.items(), 
                                            key=lambda x: min([p[0] for p in x[1]['peaks']]) if x[1]['peaks'] else 999):
        color = mineral_data['color']
        formula = mineral_data['formula']
        
        # Annotate only the most significant peak for each mineral
        if mineral_data['peaks']:
            peak = mineral_data['peaks'][0]
            angle = peak[0]
            
            # Check if too close to previous annotation
            skip = False
            for prev_angle in annotated_angles:
                if abs(angle - prev_angle) < 2:
                    skip = True
                    break
            
            if not skip:
                ax.axvline(x=angle, color=color, linestyle='--', linewidth=0.8, alpha=0.6)
                ax.text(angle, y_max * 0.98, formula,
                       fontsize=9, color=color, fontweight='bold',
                       ha='center', va='bottom', rotation=45,
                       rotation_mode='anchor')
                annotated_angles.append(angle)
    
    # Customize axes
    ax.set_xlabel(r'$2\theta$ (°)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Intensity (a.u.)', fontsize=12, fontweight='bold')
    ax.set_title('XRD Patterns Comparison', fontsize=12, fontweight='bold', pad=10)
    ax.set_xlim(5, 80)
    ax.set_ylim(0, y_max)
    
    # Set tick marks
    ax.set_xticks(np.arange(10, 85, 10))
    ax.tick_params(direction='in', length=5)
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.3, which='major')
    
    # Add legend
    ax.legend(loc='upper right', framealpha=0.9, fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=600, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"Saved: {save_path}")


def make_ascii_safe(text):
    """Convert Unicode subscripts to ASCII for Windows console output."""
    subscript_map = {
        '\u2080': '0', '\u2081': '1', '\u2082': '2', '\u2083': '3',
        '\u2084': '4', '\u2085': '5', '\u2086': '6', '\u2087': '7',
        '\u2088': '8', '\u2089': '9',
    }
    for u, a in subscript_map.items():
        text = text.replace(u, a)
    return text


def main():
    """Main function to process XRD data and generate plots."""
    # File paths
    base_path = Path(r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04")
    files = {
        'Original Ore (原矿)': base_path / "tongliukuang yuankuang.txt",
        'Concentrate (精矿)': base_path / "2cu2jing jingkuang tongliukuang.txt",
        'Tailings (尾矿)': base_path / "2cu2jing weikuang tongliukuang.txt"
    }
    
    # Output directory
    output_dir = Path(r"C:\Users\Administrator\Desktop")
    
    # Load and process each sample
    data_dict = {}
    
    # Chinese names for output files
    output_names = {
        'Original Ore (原矿)': '原矿',
        'Concentrate (精矿)': '精矿',
        'Tailings (尾矿)': '尾矿'
    }
    
    for sample_name, filepath in files.items():
        ascii_name = make_ascii_safe(sample_name)
        print(f"\nProcessing: {ascii_name}")
        print(f"File: {filepath}")
        
        # Parse XRD data
        angles, intensities = parse_bruker_xrd_file(filepath)
        data_dict[sample_name] = (angles, intensities)
        
        print(f"Data points: {len(angles)}")
        print(f"Angle range: {angles.min():.1f} - {angles.max():.1f} deg")
        
        # Identify peaks and match minerals
        peaks = identify_peaks(angles, intensities, threshold_ratio=0.08)
        matched = match_minerals(peaks, tolerance=0.8)
        
        print(f"Identified mineral phases:")
        for mineral, data in matched.items():
            ascii_mineral = make_ascii_safe(mineral)
            print(f"  - {ascii_mineral}")
        
        # Generate individual plot with Chinese filename
        chinese_name = output_names.get(sample_name, sample_name.split('(')[0].strip())
        output_path = output_dir / f"XRD_{chinese_name}.png"
        plot_single_xrd(angles, intensities, 
                       f"XRD Pattern - {sample_name}", 
                       matched, output_path)
    
    # Generate comparison plot
    comparison_path = output_dir / "XRD_对比图.png"
    plot_comparison(data_dict, comparison_path)
    
    print(f"\n{'='*60}")
    print("All plots generated successfully!")
    print(f"Output directory: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
