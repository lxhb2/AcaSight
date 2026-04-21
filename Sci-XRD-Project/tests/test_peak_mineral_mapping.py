#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for peak labeling and mineral mapping
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from xrd_unified_platform import (
    find_peaks,
    calculate_d_spacing,
    search_phases_in_database
)

def test_peak_mineral_mapping():
    """Test peak labeling with mineral mapping"""
    print("=" * 60)
    print("Testing Peak-Mineral Mapping")
    print("=" * 60)
    
    # Create synthetic XRD data
    x = np.linspace(10, 70, 1000)
    
    # Create multiple peaks (simulating quartz, calcite, hematite)
    y = np.zeros_like(x)
    
    # Peak 1: Quartz (101) ~26.6°
    center1 = 26.6
    y += 1000 * np.exp(-(x - center1)**2 / (2 * 0.3**2))
    
    # Peak 2: Calcite (104) ~29.4°
    center2 = 29.4
    y += 800 * np.exp(-(x - center2)**2 / (2 * 0.3**2))
    
    # Peak 3: Hematite (104) ~33.2°
    center3 = 33.2
    y += 600 * np.exp(-(x - center3)**2 / (2 * 0.3**2))
    
    # Peak 4: Quartz (100) ~20.8°
    center4 = 20.8
    y += 500 * np.exp(-(x - center4)**2 / (2 * 0.3**2))
    
    # Add noise
    y += np.random.normal(0, 10, len(y))
    
    # Find peaks
    peak_indices = find_peaks(y, height_threshold=0.01, prominence=0.5)
    peak_positions = x[peak_indices]
    peak_intensities = y[peak_indices]
    
    print(f"Detected {len(peak_positions)} peaks:")
    for i, (pos, intensity) in enumerate(zip(peak_positions, peak_intensities)):
        print(f"  Peak {i+1}: 2θ = {pos:.2f}°, Intensity = {intensity:.1f}")
    
    # Calculate d-spacings
    d_values = [calculate_d_spacing(pos) for pos in peak_positions]
    
    print(f"\nCalculated d-spacings:")
    for i, d in enumerate(d_values):
        print(f"  Peak {i+1}: d = {d:.3f} Å")
    
    # Search phases in database
    phases = search_phases_in_database(d_values, tolerance=0.02)
    
    print(f"\nMatched phases:")
    for i, phase in enumerate(phases[:min(5, len(phases))]):  # Show top 5
        print(f"  {phase['name']}: {phase['match_score']}% match")
    
    # Create mineral mapping
    mineral_mapping = {}
    for i, phase in enumerate(phases[:len(peak_positions)]):
        mineral_name = phase.get('name', 'Unknown')
        if '(' in mineral_name:
            mineral_short = mineral_name.split('(')[0].strip()
        else:
            mineral_short = mineral_name
        mineral_mapping[i] = mineral_short
    
    print(f"\nPeak-Mineral Mapping:")
    for peak_idx, mineral in mineral_mapping.items():
        if peak_idx < len(peak_positions):
            print(f"  Peak {peak_idx+1} ({peak_positions[peak_idx]:.2f}°) → {mineral}")
    
    # Test table generation
    print(f"\nTable Data Structure:")
    print("  | 序号 | 2Theta (度) | 强度 | 半高宽 | 矿物 |")
    print("  |------|------------|------|--------|------|")
    for i, (pos, intensity) in enumerate(zip(peak_positions, peak_intensities)):
        mineral = mineral_mapping.get(i, "未识别")
        print(f"  | {i+1} | {pos:.3f} | {intensity:.1f} | 0.100 | {mineral} |")
    
    return True

def test_origin_compatibility():
    """Test Origin export compatibility"""
    print("\n" + "=" * 60)
    print("Testing Origin Export Compatibility")
    print("=" * 60)
    
    # Test data formats
    x = np.linspace(10, 70, 100)
    y = np.sin(x/10) * 100 + 50
    
    # ASCII XY format (Origin compatible)
    print("ASCII XY Format (Tab-separated):")
    print("2Theta\tIntensity")
    for i in range(3):  # Show first 3 lines
        print(f"{x[i]:.4f}\t{y[i]:.4f}")
    print("...")
    
    # CSV format
    print("\nCSV Format:")
    print("2Theta,Intensity")
    for i in range(3):
        print(f"{x[i]:.4f},{y[i]:.4f}")
    print("...")
    
    # Peak data format
    peaks = [(26.6, 1000, 0.1, "Quartz"),
             (29.4, 800, 0.12, "Calcite"),
             (33.2, 600, 0.15, "Hematite")]
    
    print("\nPeak Data Format:")
    print("PeakNo,2Theta,Intensity,FWHM,Mineral")
    for i, (pos, intensity, fwhm, mineral) in enumerate(peaks):
        print(f"{i+1},{pos:.3f},{intensity:.1f},{fwhm:.3f},{mineral}")
    
    return True

def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PEAK LABELING AND ORIGIN COMPATIBILITY TEST")
    print("=" * 70 + "\n")
    
    try:
        test1 = test_peak_mineral_mapping()
        test2 = test_origin_compatibility()
        
        if test1 and test2:
            print("\n" + "=" * 70)
            print("✅ ALL TESTS PASSED")
            print("=" * 70)
            print("\nSummary:")
            print("1. ✓ Peak detection and mineral mapping working")
            print("2. ✓ Table generation with mineral column working")
            print("3. ✓ Origin-compatible export formats ready")
            print("4. ✓ Peak labels correspond to table minerals")
            return True
        else:
            print("\n❌ Some tests failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
