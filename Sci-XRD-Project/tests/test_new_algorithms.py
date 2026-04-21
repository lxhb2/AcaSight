#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for new XRD algorithms
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from xrd_unified_platform import (
    calculate_d_spacing,
    calculate_fwhm,
    gaussian_fit,
    lorentzian_fit,
    pseudo_voigt_fit,
    strip_k_alpha2,
    calculate_lattice_parameter,
    calculate_strain,
    quantitative_analysis,
    calculate_pattern_similarity,
    find_peaks
)

def test_calculate_d_spacing():
    """Test d-spacing calculation"""
    print("=" * 50)
    print("Testing calculate_d_spacing()")
    print("=" * 50)
    
    # Test with known values
    # For Cu K-alpha (1.5406 A), 2theta = 26.6 degrees (quartz 101)
    twotheta = 26.6
    d = calculate_d_spacing(twotheta)
    print(f"2θ = {twotheta}°")
    print(f"d = {d:.4f} Å")
    print(f"Expected: ~3.34 Å for quartz (101)")
    print()

def test_calculate_fwhm():
    """Test FWHM calculation"""
    print("=" * 50)
    print("Testing calculate_fwhm()")
    print("=" * 50)
    
    # Create a synthetic Gaussian peak
    x = np.linspace(20, 30, 1000)
    center = 25.0
    sigma = 0.5
    y = 100 * np.exp(-(x - center)**2 / (2 * sigma**2))
    
    # Find peak
    peak_idx = np.argmax(y)
    
    # Calculate FWHM
    fwhm = calculate_fwhm(x, y, peak_idx)
    expected_fwhm = 2.355 * sigma  # For Gaussian
    
    print(f"Peak center: {center}°")
    print(f"Calculated FWHM: {fwhm:.4f}°")
    print(f"Expected FWHM: {expected_fwhm:.4f}°")
    print(f"Error: {abs(fwhm - expected_fwhm):.4f}°")
    print()

def test_gaussian_fit():
    """Test Gaussian fitting"""
    print("=" * 50)
    print("Testing gaussian_fit()")
    print("=" * 50)
    
    try:
        from scipy.optimize import curve_fit
        
        # Create synthetic data
        x = np.linspace(20, 30, 100)
        center = 25.0
        sigma = 0.5
        amplitude = 100
        y = amplitude * np.exp(-(x - center)**2 / (2 * sigma**2))
        y += np.random.normal(0, 1, len(y))  # Add noise
        
        # Find peak
        peak_idx = np.argmax(y)
        
        # Fit
        result = gaussian_fit(x, y, peak_idx)
        
        if result:
            print(f"Fitted center: {result['center']:.4f}° (expected: {center}°)")
            print(f"Fitted amplitude: {result['amplitude']:.2f} (expected: {amplitude})")
            print(f"Fitted FWHM: {result['fwhm']:.4f}°")
            print("✓ Gaussian fit successful")
        else:
            print("✗ Gaussian fit failed")
    except ImportError:
        print("⚠ scipy not available, skipping Gaussian fit test")
    print()

def test_strip_k_alpha2():
    """Test K-alpha2 stripping"""
    print("=" * 50)
    print("Testing strip_k_alpha2()")
    print("=" * 50)
    
    # Create synthetic data with K-alpha2 component
    x = np.linspace(20, 60, 1000)
    
    # Main peak (K-alpha1)
    center1 = 40.0
    y1 = 100 * np.exp(-(x - center1)**2 / (2 * 0.3**2))
    
    # K-alpha2 component (slightly shifted)
    # delta_2theta ≈ 0.1 degrees at 40 degrees
    center2 = 40.08
    y2 = 50 * np.exp(-(x - center2)**2 / (2 * 0.3**2))
    
    y = y1 + y2
    
    # Strip K-alpha2
    y_corrected = strip_k_alpha2(x, y)
    
    print(f"Original peak height: {np.max(y):.2f}")
    print(f"Corrected peak height: {np.max(y_corrected):.2f}")
    print(f"Height reduction: {np.max(y) - np.max(y_corrected):.2f}")
    print("✓ K-alpha2 stripping completed")
    print()

def test_calculate_lattice_parameter():
    """Test lattice parameter calculation"""
    print("=" * 50)
    print("Testing calculate_lattice_parameter()")
    print("=" * 50)
    
    # For cubic system: 1/d^2 = (h^2+k^2+l^2)/a^2
    # Example: Silicon with a = 5.431 Å
    a_true = 5.431
    
    # Calculate d-spacings for some peaks
    hkl_list = [(1,1,1), (2,2,0), (3,1,1)]
    d_spacings = []
    for h, k, l in hkl_list:
        d = a_true / np.sqrt(h**2 + k**2 + l**2)
        d_spacings.append(d)
    
    # Calculate lattice parameter
    result = calculate_lattice_parameter(d_spacings, hkl_list, 'cubic')
    
    if result:
        print(f"Calculated a = {result['a']:.4f} Å")
        print(f"Standard deviation = {result['std']:.4f} Å")
        print(f"Expected a = {a_true} Å")
        print(f"Error = {abs(result['a'] - a_true):.4f} Å")
        print("✓ Lattice parameter calculation successful")
    else:
        print("✗ Lattice parameter calculation failed")
    print()

def test_calculate_strain():
    """Test strain calculation"""
    print("=" * 50)
    print("Testing calculate_strain()")
    print("=" * 50)
    
    # Simulate strain
    reference_d = 3.34  # Quartz (101)
    strain = 0.001  # 0.1% strain
    shifted_d = reference_d * (1 + strain)
    
    result = calculate_strain([shifted_d - reference_d], reference_d)
    
    print(f"Reference d = {reference_d} Å")
    print(f"Shifted d = {shifted_d:.4f} Å")
    print(f"Calculated strain = {result['average_strain']:.6f}")
    print(f"Expected strain = {strain:.6f}")
    print(f"Estimated stress = {result['estimated_stress_mpa']:.2f} MPa")
    print("✓ Strain calculation successful")
    print()

def test_quantitative_analysis():
    """Test quantitative phase analysis"""
    print("=" * 50)
    print("Testing quantitative_analysis()")
    print("=" * 50)
    
    # Simulate two phases
    peak_areas = [1000, 500]  # Phase A and B
    rir_values = [5.0, 3.0]   # RIR for each phase
    
    result = quantitative_analysis(peak_areas, rir_values)
    
    if result:
        print(f"Phase A: {result['weight_percentages'][0]:.2f}%")
        print(f"Phase B: {result['weight_percentages'][1]:.2f}%")
        print(f"Total: {result['total']:.2f}%")
        print("✓ Quantitative analysis successful")
    else:
        print("✗ Quantitative analysis failed")
    print()

def test_pattern_similarity():
    """Test pattern similarity calculation"""
    print("=" * 50)
    print("Testing calculate_pattern_similarity()")
    print("=" * 50)
    
    # Create two similar patterns
    x = np.linspace(0, 1, 100)
    y1 = np.sin(2 * np.pi * 5 * x)
    y2 = np.sin(2 * np.pi * 5 * x) + 0.1 * np.random.normal(0, 1, len(x))
    
    similarity = calculate_pattern_similarity(y1, y2, 'correlation')
    
    print(f"Pattern similarity (correlation): {similarity:.4f}")
    print(f"Expected: close to 1.0 for similar patterns")
    print("✓ Pattern similarity calculation successful")
    print()

def run_all_tests():
    """Run all algorithm tests"""
    print("\n" + "=" * 70)
    print("XRD ALGORITHM TEST SUITE")
    print("=" * 70 + "\n")
    
    test_calculate_d_spacing()
    test_calculate_fwhm()
    test_gaussian_fit()
    test_strip_k_alpha2()
    test_calculate_lattice_parameter()
    test_calculate_strain()
    test_quantitative_analysis()
    test_pattern_similarity()
    
    print("=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_all_tests()
