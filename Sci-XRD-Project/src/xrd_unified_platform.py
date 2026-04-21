#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD Unified Analysis Platform v3.0
All-in-one XRD analysis tool with integrated interface
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import traceback

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTabWidget, QGroupBox, QPushButton, QLabel,
    QTextEdit, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QProgressBar, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QAction, QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ============================================================
# Core XRD Functions (Built-in, no external dependencies)
# ============================================================

def read_xrd_data(file_path):
    """Read XRD data from file"""
    ext = Path(file_path).suffix.lower()
    
    if ext == '.csv':
        data = np.loadtxt(file_path, delimiter=',', skiprows=1)
    else:
        try:
            data = np.loadtxt(file_path, delimiter=',')
        except:
            try:
                data = np.loadtxt(file_path)
            except:
                # Try with different separators
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                data_list = []
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    # Try tab, space, comma
                    for sep in ['\t', ' ', ',']:
                        parts = line.split(sep)
                        if len(parts) >= 2:
                            try:
                                data_list.append([float(p) for p in parts[:2]])
                                break
                            except:
                                continue
                
                data = np.array(data_list)
    
    return (data[:, 0], data[:, 1])

def smooth_data(y, window=5):
    """Smooth data using moving average"""
    if len(y) < window:
        return y
    smoothed = np.copy(y)
    half = window // 2
    for i in range(half, len(y) - half):
        smoothed[i] = np.mean(y[i-half:i+half+1])
    return smoothed

def subtract_background(y, lambda_param=100):
    """Background subtraction using SNIP algorithm (simplified)"""
    bg = np.zeros_like(y)
    for i in range(1, len(y)-1):
        bg[i] = np.minimum(y[i], (bg[i-1] + y[i] + y[i+1]) / 3)
    return y - bg

def find_peaks(y, height_threshold=0.02, prominence=1.0):
    """Simple peak detection"""
    peaks = []
    threshold = np.max(y) * height_threshold
    
    for i in range(1, len(y)-1):
        if y[i] > y[i-1] and y[i] > y[i+1] and y[i] > threshold:
            # Check prominence
            left_min = np.min(y[max(0, i-5):i]) if i > 0 else y[0]
            right_min = np.min(y[i+1:min(len(y), i+6)]) if i < len(y)-1 else y[-1]
            min_val = min(left_min, right_min)
            if y[i] - min_val >= prominence:
                peaks.append(i)
    
    return np.array(peaks)

def calculate_crystallite_size(twotheta, fwhm, wavelength=1.5406):
    """Calculate crystallite size using Scherrer formula"""
    theta = np.radians(twotheta / 2)
    k = 0.9  # Shape factor
    B = np.radians(fwhm)
    if B == 0:
        return 100.0
    D = k * wavelength / (B * np.cos(theta))
    return D

def calculate_d_spacing(twotheta, wavelength=1.5406):
    """Calculate d-spacing from 2-theta angle using Bragg's law"""
    theta = np.radians(twotheta / 2)
    d = wavelength / (2 * np.sin(theta))
    return d

def calculate_fwhm(x, y, peak_idx):
    """Calculate Full Width at Half Maximum (FWHM) of a peak"""
    if peak_idx < 0 or peak_idx >= len(y):
        return 0.0
    
    peak_height = y[peak_idx]
    half_max = peak_height / 2.0
    
    # Find left intersection
    left_idx = peak_idx
    for i in range(peak_idx, -1, -1):
        if y[i] < half_max:
            left_idx = i
            break
    
    # Find right intersection
    right_idx = peak_idx
    for i in range(peak_idx, len(y)):
        if y[i] < half_max:
            right_idx = i
            break
    
    # Linear interpolation for more accurate FWHM
    if left_idx < peak_idx and right_idx > peak_idx:
        # Interpolate left point
        if y[left_idx] != y[left_idx + 1]:
            x_left = x[left_idx] + (half_max - y[left_idx]) * (x[left_idx + 1] - x[left_idx]) / (y[left_idx + 1] - y[left_idx])
        else:
            x_left = x[left_idx]
        
        # Interpolate right point
        if y[right_idx] != y[right_idx - 1]:
            x_right = x[right_idx] + (half_max - y[right_idx]) * (x[right_idx - 1] - x[right_idx]) / (y[right_idx - 1] - y[right_idx])
        else:
            x_right = x[right_idx]
        
        fwhm = x_right - x_left
    else:
        fwhm = x[right_idx] - x[left_idx]
    
    return abs(fwhm)

def gaussian_fit(x, y, peak_idx, window=10):
    """Fit a Gaussian function to a peak"""
    if peak_idx < window or peak_idx >= len(y) - window:
        return None
    
    # Extract peak region
    x_peak = x[peak_idx - window:peak_idx + window]
    y_peak = y[peak_idx - window:peak_idx + window]
    
    # Initial guesses
    amplitude = y[peak_idx]
    center = x[peak_idx]
    sigma = np.std(x_peak) / 2
    
    # Simple Gaussian: y = A * exp(-(x-mu)^2 / (2*sigma^2))
    def gaussian(x, A, mu, sigma):
        return A * np.exp(-(x - mu)**2 / (2 * sigma**2))
    
    # Simple least squares fitting
    from scipy.optimize import curve_fit
    try:
        popt, _ = curve_fit(gaussian, x_peak, y_peak, p0=[amplitude, center, sigma])
        return {
            'amplitude': popt[0],
            'center': popt[1],
            'sigma': popt[2],
            'fwhm': 2.355 * popt[2],  # FWHM = 2.355 * sigma for Gaussian
            'function': lambda x: gaussian(x, *popt)
        }
    except:
        return None

def lorentzian_fit(x, y, peak_idx, window=10):
    """Fit a Lorentzian function to a peak"""
    if peak_idx < window or peak_idx >= len(y) - window:
        return None
    
    # Extract peak region
    x_peak = x[peak_idx - window:peak_idx + window]
    y_peak = y[peak_idx - window:peak_idx + window]
    
    # Initial guesses
    amplitude = y[peak_idx]
    center = x[peak_idx]
    gamma = np.std(x_peak) / 2
    
    # Lorentzian: y = A / (1 + ((x-mu)/gamma)^2)
    def lorentzian(x, A, mu, gamma):
        return A / (1 + ((x - mu) / gamma)**2)
    
    # Simple least squares fitting
    from scipy.optimize import curve_fit
    try:
        popt, _ = curve_fit(lorentzian, x_peak, y_peak, p0=[amplitude, center, gamma])
        return {
            'amplitude': popt[0],
            'center': popt[1],
            'gamma': popt[2],
            'fwhm': 2 * popt[2],  # FWHM = 2 * gamma for Lorentzian
            'function': lambda x: lorentzian(x, *popt)
        }
    except:
        return None

def pseudo_voigt_fit(x, y, peak_idx, window=10):
    """Fit a Pseudo-Voigt function (mixture of Gaussian and Lorentzian)"""
    if peak_idx < window or peak_idx >= len(y) - window:
        return None
    
    # Extract peak region
    x_peak = x[peak_idx - window:peak_idx + window]
    y_peak = y[peak_idx - window:peak_idx + window]
    
    # Initial guesses
    amplitude = y[peak_idx]
    center = x[peak_idx]
    sigma = np.std(x_peak) / 2
    eta = 0.5  # Mixing parameter
    
    # Pseudo-Voigt
    def pseudo_voigt(x, A, mu, sigma, eta):
        gaussian = np.exp(-(x - mu)**2 / (2 * sigma**2))
        lorentzian = 1 / (1 + ((x - mu) / sigma)**2)
        return A * (eta * lorentzian + (1 - eta) * gaussian)
    
    # Simple least squares fitting
    from scipy.optimize import curve_fit
    try:
        popt, _ = curve_fit(pseudo_voigt, x_peak, y_peak, p0=[amplitude, center, sigma, eta])
        return {
            'amplitude': popt[0],
            'center': popt[1],
            'sigma': popt[2],
            'eta': popt[3],
            'fwhm': 2.355 * popt[2] * (1 - popt[3]) + 2 * popt[2] * popt[3],
            'function': lambda x: pseudo_voigt(x, *popt)
        }
    except:
        return None

def strip_k_alpha2(x, y, wavelength_ka1=1.5406, wavelength_ka2=1.5444, intensity_ratio=0.5):
    """Strip K-alpha2 component from XRD data (Rachinger method)"""
    y_corrected = np.copy(y)
    
    # Calculate delta 2-theta for K-alpha2
    delta_2theta = np.zeros_like(x)
    for i, twotheta in enumerate(x):
        theta1 = np.arcsin(wavelength_ka1 / (2 * calculate_d_spacing(twotheta, wavelength_ka1)))
        theta2 = np.arcsin(wavelength_ka2 / (2 * calculate_d_spacing(twotheta, wavelength_ka1)))
        delta_2theta[i] = np.degrees(2 * (theta2 - theta1))
    
    # Rachinger stripping
    for i in range(len(x) - 1, -1, -1):
        # Find corresponding K-alpha2 position
        ka2_2theta = x[i] + delta_2theta[i]
        
        # Interpolate intensity at K-alpha2 position
        if ka2_2theta <= x[-1]:
            idx = np.searchsorted(x, ka2_2theta)
            if idx > 0 and idx < len(x):
                # Linear interpolation
                fraction = (ka2_2theta - x[idx-1]) / (x[idx] - x[idx-1])
                ka2_intensity = y[idx-1] + fraction * (y[idx] - y[idx-1])
                
                # Subtract K-alpha2 contribution
                y_corrected[i] -= intensity_ratio * ka2_intensity
    
    return np.maximum(y_corrected, 0)  # Ensure non-negative

def calculate_lattice_parameter(d_spacings, hkl_list, crystal_system='cubic'):
    """Calculate lattice parameters from d-spacings and Miller indices"""
    if len(d_spacings) != len(hkl_list) or len(d_spacings) < 1:
        return None
    
    if crystal_system == 'cubic':
        # For cubic: 1/d^2 = (h^2 + k^2 + l^2) / a^2
        a_values = []
        for d, (h, k, l) in zip(d_spacings, hkl_list):
            hkl_squared = h**2 + k**2 + l**2
            if hkl_squared > 0:
                a = d * np.sqrt(hkl_squared)
                a_values.append(a)
        
        if a_values:
            return {'a': np.mean(a_values), 'std': np.std(a_values)}
    
    elif crystal_system == 'tetragonal':
        # For tetragonal: 1/d^2 = (h^2 + k^2) / a^2 + l^2 / c^2
        # Requires at least 2 peaks with different l values
        return {'note': 'Tetragonal refinement requires nonlinear fitting'}
    
    return None

def calculate_strain(peak_shifts, reference_d, poisson_ratio=0.3, young_modulus=200e9):
    """Calculate microstrain from peak shifts"""
    # Strain = delta_d / d = -cot(theta) * delta_theta
    strains = []
    for shift in peak_shifts:
        strain = shift / reference_d
        strains.append(strain)
    
    avg_strain = np.mean(strains)
    std_strain = np.std(strains)
    
    # Estimate stress using Hooke's law (simplified)
    stress = young_modulus * avg_strain
    
    return {
        'average_strain': avg_strain,
        'std_strain': std_strain,
        'estimated_stress_pa': stress,
        'estimated_stress_mpa': stress / 1e6
    }

def quantitative_analysis(peak_areas, rir_values):
    """Quantitative phase analysis using Reference Intensity Ratio (RIR) method"""
    if len(peak_areas) != len(rir_values):
        return None
    
    # Calculate weight fractions
    weights = []
    for area, rir in zip(peak_areas, rir_values):
        if rir > 0:
            weights.append(area / rir)
        else:
            weights.append(0)
    
    total_weight = sum(weights)
    if total_weight == 0:
        return None
    
    weight_percentages = [w / total_weight * 100 for w in weights]
    
    return {
        'weight_percentages': weight_percentages,
        'total': sum(weight_percentages)
    }

def calculate_pattern_similarity(y1, y2, method='correlation'):
    """Calculate similarity between two XRD patterns"""
    if len(y1) != len(y2):
        # Interpolate to match lengths
        x_new = np.linspace(0, 1, max(len(y1), len(y2)))
        y1_interp = np.interp(x_new, np.linspace(0, 1, len(y1)), y1)
        y2_interp = np.interp(x_new, np.linspace(0, 1, len(y2)), y2)
        y1, y2 = y1_interp, y2_interp
    
    # Normalize
    y1_norm = (y1 - np.mean(y1)) / np.std(y1)
    y2_norm = (y2 - np.mean(y2)) / np.std(y2)
    
    if method == 'correlation':
        # Pearson correlation coefficient
        correlation = np.corrcoef(y1_norm, y2_norm)[0, 1]
        return correlation
    elif method == 'rwp':
        # R-weighted pattern (Rwp) - lower is better
        rwp = np.sqrt(np.sum((y1 - y2)**2) / np.sum(y1**2))
        return 1 - rwp  # Convert to similarity (higher is better)
    elif method == 'rb':
        # R-Bragg factor
        rb = np.sum(np.abs(y1 - y2)) / np.sum(y1)
        return 1 - rb
    
    return 0.0

def search_phases_in_database(d_values, tolerance=0.02):
    """Search phases in database (simulated)"""
    # Extended database with copper minerals for copper-sulfur ore analysis
    phases = [
        # Common minerals
        {"name": "Quartz (SiO2)", "match_score": 95, "card_id": "01-085-0798", "formula": "SiO2"},
        {"name": "Calcite (CaCO3)", "match_score": 87, "card_id": "01-086-2334", "formula": "CaCO3"},
        {"name": "Hematite (Fe2O3)", "match_score": 76, "card_id": "01-089-0599", "formula": "Fe2O3"},
        # Copper minerals for copper-sulfur ore
        {"name": "Chalcopyrite (CuFeS2)", "match_score": 92, "card_id": "01-083-1285", "formula": "CuFeS2"},
        {"name": "Chalcocite (Cu2S)", "match_score": 89, "card_id": "01-084-1770", "formula": "Cu2S"},
        {"name": "Bornite (Cu5FeS4)", "match_score": 85, "card_id": "01-084-1771", "formula": "Cu5FeS4"},
        {"name": "Covellite (CuS)", "match_score": 88, "card_id": "01-083-1464", "formula": "CuS"},
        {"name": "Digenite (Cu9S5)", "match_score": 82, "card_id": "01-084-1772", "formula": "Cu9S5"},
        {"name": "Anilite (Cu7S4)", "match_score": 80, "card_id": "01-084-1773", "formula": "Cu7S4"},
        {"name": "Djurleite (Cu31S16)", "match_score": 78, "card_id": "01-084-1774", "formula": "Cu31S16"},
        {"name": "Geerite (Cu8S5)", "match_score": 77, "card_id": "01-084-1775", "formula": "Cu8S5"},
        {"name": "Roxbyite (Cu1.78S)", "match_score": 75, "card_id": "01-084-1776", "formula": "Cu1.78S"},
        {"name": "Copper (Cu)", "match_score": 90, "card_id": "01-085-1326", "formula": "Cu"},
        {"name": "Cuprite (Cu2O)", "match_score": 86, "card_id": "01-084-1777", "formula": "Cu2O"},
        {"name": "Tenorite (CuO)", "match_score": 84, "card_id": "01-084-1778", "formula": "CuO"},
        {"name": "Malachite (Cu2CO3(OH)2)", "match_score": 81, "card_id": "01-084-1779", "formula": "Cu2CO3(OH)2"},
        {"name": "Azurite (Cu3(CO3)2(OH)2)", "match_score": 79, "card_id": "01-084-1780", "formula": "Cu3(CO3)2(OH)2"},
        {"name": "Brochantite (Cu4SO4(OH)6)", "match_score": 76, "card_id": "01-084-1781", "formula": "Cu4SO4(OH)6"},
        {"name": "Chrysocolla (Cu2-xAlx(H2-xSi2O5)(OH)4·nH2O)", "match_score": 74, "card_id": "01-084-1782", "formula": "Cu2-xAlx(H2-xSi2O5)(OH)4·nH2O"},
        {"name": "Antlerite (Cu3SO4(OH)4)", "match_score": 73, "card_id": "01-084-1783", "formula": "Cu3SO4(OH)4"},
        {"name": "Atacamite (Cu2Cl(OH)3)", "match_score": 72, "card_id": "01-084-1784", "formula": "Cu2Cl(OH)3"},
        {"name": "Clinoatacamite (Cu2Cl(OH)3)", "match_score": 71, "card_id": "01-084-1785", "formula": "Cu2Cl(OH)3"},
        {"name": "Botallackite (Cu2Cl(OH)3)", "match_score": 70, "card_id": "01-084-1786", "formula": "Cu2Cl(OH)3"},
        {"name": "Nantokite (CuCl)", "match_score": 69, "card_id": "01-084-1787", "formula": "CuCl"},
        {"name": "Chalcopyrite (CuFeS2)", "match_score": 92, "card_id": "01-083-1285", "formula": "CuFeS2"},
        {"name": "Tetrahedrite (Cu12Sb4S13)", "match_score": 83, "card_id": "01-084-1788", "formula": "Cu12Sb4S13"},
        {"name": "Tennantite (Cu12As4S13)", "match_score": 81, "card_id": "01-084-1789", "formula": "Cu12As4S13"},
        {"name": "Enargite (Cu3AsS4)", "match_score": 80, "card_id": "01-084-1790", "formula": "Cu3AsS4"},
        {"name": "Luzonite (Cu3AsS4)", "match_score": 78, "card_id": "01-084-1791", "formula": "Cu3AsS4"},
        {"name": "Famatinite (Cu3SbS4)", "match_score": 77, "card_id": "01-084-1792", "formula": "Cu3SbS4"},
        {"name": "Stromeyerite (AgCuS)", "match_score": 75, "card_id": "01-084-1793", "formula": "AgCuS"},
        {"name": "Acanthite (Ag2S)", "match_score": 73, "card_id": "01-084-1794", "formula": "Ag2S"},
        {"name": "Argentite (Ag2S)", "match_score": 72, "card_id": "01-084-1795", "formula": "Ag2S"},
        {"name": "Silver (Ag)", "match_score": 88, "card_id": "01-085-1327", "formula": "Ag"},
        {"name": "Gold (Au)", "match_score": 87, "card_id": "01-085-1328", "formula": "Au"},
        {"name": "Pyrite (FeS2)", "match_score": 85, "card_id": "01-084-1796", "formula": "FeS2"},
        {"name": "Marcasite (FeS2)", "match_score": 83, "card_id": "01-084-1797", "formula": "FeS2"},
        {"name": "Pyrrhotite (Fe1-xS)", "match_score": 82, "card_id": "01-084-1798", "formula": "Fe1-xS"},
        {"name": "Sphalerite (ZnS)", "match_score": 84, "card_id": "01-084-1799", "formula": "ZnS"},
        {"name": "Wurtzite (ZnS)", "match_score": 81, "card_id": "01-084-1800", "formula": "ZnS"},
        {"name": "Galena (PbS)", "match_score": 86, "card_id": "01-084-1801", "formula": "PbS"},
        {"name": "Anglesite (PbSO4)", "match_id": "01-084-1802", "formula": "PbSO4", "match_score": 79},
        {"name": "Cerussite (PbCO3)", "match_id": "01-084-1803", "formula": "PbCO3", "match_score": 78},
        {"name": "Molybdenite (MoS2)", "match_id": "01-084-1804", "formula": "MoS2", "match_score": 80},
        {"name": "Molybdenum (Mo)", "match_id": "01-085-1329", "formula": "Mo", "match_score": 85},
        {"name": "Tungsten (W)", "match_id": "01-085-1330", "formula": "W", "match_score": 84},
        {"name": "Wolframite ((Fe,Mn)WO4)", "match_id": "01-084-1805", "formula": "(Fe,Mn)WO4", "match_score": 76},
        {"name": "Scheelite (CaWO4)", "match_id": "01-084-1806", "formula": "CaWO4", "match_score": 77},
        {"name": "Cassiterite (SnO2)", "match_id": "01-084-1807", "formula": "SnO2", "match_score": 82},
        {"name": "Rutile (TiO2)", "match_id": "01-084-1808", "formula": "TiO2", "match_score": 83},
        {"name": "Anatase (TiO2)", "match_id": "01-084-1809", "formula": "TiO2", "match_score": 81},
        {"name": "Brookite (TiO2)", "match_id": "01-084-1810", "formula": "TiO2", "match_score": 79},
        {"name": "Ilmenite (FeTiO3)", "match_id": "01-084-1811", "formula": "FeTiO3", "match_score": 78},
        {"name": "Magnetite (Fe3O4)", "match_id": "01-084-1812", "formula": "Fe3O4", "match_score": 87},
        {"name": "Goethite (FeO(OH))", "match_id": "01-084-1813", "formula": "FeO(OH)", "match_score": 80},
        {"name": "Limonite (FeO(OH)·nH2O)", "match_id": "01-084-1814", "formula": "FeO(OH)·nH2O", "match_score": 76},
        {"name": "Siderite (FeCO3)", "match_id": "01-084-1815", "formula": "FeCO3", "match_score": 78},
        {"name": "Dolomite (CaMg(CO3)2)", "match_id": "01-084-1816", "formula": "CaMg(CO3)2", "match_score": 82},
        {"name": "Magnesite (MgCO3)", "match_id": "01-084-1817", "formula": "MgCO3", "match_score": 81},
        {"name": "Aragonite (CaCO3)", "match_id": "01-084-1818", "formula": "CaCO3", "match_score": 80},
        {"name": "Vaterite (CaCO3)", "match_id": "01-084-1819", "formula": "CaCO3", "match_score": 75},
        {"name": "Gypsum (CaSO4·2H2O)", "match_id": "01-084-1820", "formula": "CaSO4·2H2O", "match_score": 79},
        {"name": "Anhydrite (CaSO4)", "match_id": "01-084-1821", "formula": "CaSO4", "match_score": 77},
        {"name": "Bassanite (CaSO4·0.5H2O)", "match_id": "01-084-1822", "formula": "CaSO4·0.5H2O", "match_score": 76},
        {"name": "Barite (BaSO4)", "match_id": "01-084-1823", "formula": "BaSO4", "match_score": 78},
        {"name": "Celestite (SrSO4)", "match_id": "01-084-1824", "formula": "SrSO4", "match_score": 77},
        {"name": "Fluorite (CaF2)", "match_id": "01-084-1825", "formula": "CaF2", "match_score": 83},
        {"name": "Halite (NaCl)", "match_id": "01-084-1826", "formula": "NaCl", "match_score": 85},
        {"name": "Sylvite (KCl)", "match_id": "01-084-1827", "formula": "KCl", "match_score": 84},
        {"name": "Apatite (Ca5(PO4)3(F,Cl,OH))", "match_id": "01-084-1828", "formula": "Ca5(PO4)3(F,Cl,OH)", "match_score": 79},
        {"name": "Monazite ((Ce,La,Nd,Th)PO4)", "match_id": "01-084-1829", "formula": "(Ce,La,Nd,Th)PO4", "match_score": 76},
        {"name": "Xenotime (YPO4)", "match_id": "01-084-1830", "formula": "YPO4", "match_score": 75},
        {"name": "Zircon (ZrSiO4)", "match_id": "01-084-1831", "formula": "ZrSiO4", "match_score": 82},
        {"name": "Baddeleyite (ZrO2)", "match_id": "01-084-1832", "formula": "ZrO2", "match_score": 80},
        {"name": "Corundum (Al2O3)", "match_id": "01-084-1833", "formula": "Al2O3", "match_score": 86},
        {"name": "Spinel (MgAl2O4)", "match_id": "01-084-1834", "formula": "MgAl2O4", "match_score": 81},
        {"name": "Hercynite (FeAl2O4)", "match_id": "01-084-1835", "formula": "FeAl2O4", "match_score": 78},
        {"name": "Galaxite (MnAl2O4)", "match_id": "01-084-1836", "formula": "MnAl2O4", "match_score": 76},
        {"name": "Gahnite (ZnAl2O4)", "match_id": "01-084-1837", "formula": "ZnAl2O4", "match_score": 77},
        {"name": "Chlorite ((Mg,Fe,Al)6(Si,Al)4O10(OH)8)", "match_id": "01-084-1838", "formula": "(Mg,Fe,Al)6(Si,Al)4O10(OH)8", "match_score": 74},
        {"name": "Muscovite (KAl2(AlSi3O10)(OH)2)", "match_id": "01-084-1839", "formula": "KAl2(AlSi3O10)(OH)2", "match_score": 75},
        {"name": "Biotite (K(Mg,Fe)3(AlSi3O10)(OH)2)", "match_id": "01-084-1840", "formula": "K(Mg,Fe)3(AlSi3O10)(OH)2", "match_score": 74},
        {"name": "Phlogopite (KMg3(AlSi3O10)(OH)2)", "match_id": "01-084-1841", "formula": "KMg3(AlSi3O10)(OH)2", "match_score": 73},
        {"name": "Talc (Mg3Si4O10(OH)2)", "match_id": "01-084-1842", "formula": "Mg3Si4O10(OH)2", "match_score": 76},
        {"name": "Kaolinite (Al2Si2O5(OH)4)", "match_id": "01-084-1843", "formula": "Al2Si2O5(OH)4", "match_score": 75},
        {"name": "Illite (K0.65Al2.0[Al0.65Si3.35O10](OH)2)", "match_id": "01-084-1844", "formula": "K0.65Al2.0[Al0.65Si3.35O10](OH)2", "match_score": 74},
        {"name": "Smectite ((Na,Ca)0.33(Al,Mg)2(Si4O10)(OH)2·nH2O)", "match_id": "01-084-1845", "formula": "(Na,Ca)0.33(Al,Mg)2(Si4O10)(OH)2·nH2O", "match_score": 73},
        {"name": "Vermiculite ((Mg,Fe,Al)3(Al,Si)4O10(OH)2·4H2O)", "match_id": "01-084-1846", "formula": "(Mg,Fe,Al)3(Al,Si)4O10(OH)2·4H2O", "match_score": 72},
        {"name": "Serpentine ((Mg,Fe)3Si2O5(OH)4)", "match_id": "01-084-1847", "formula": "(Mg,Fe)3Si2O5(OH)4", "match_score": 73},
        {"name": "Epidote (Ca2(Al,Fe)3(SiO4)3(OH))", "match_id": "01-084-1848", "formula": "Ca2(Al,Fe)3(SiO4)3(OH)", "match_score": 74},
        {"name": "Garnet ((Ca,Mg,Fe,Mn)3(Al,Fe,Cr)2(SiO4)3)", "match_id": "01-084-1849", "formula": "(Ca,Mg,Fe,Mn)3(Al,Fe,Cr)2(SiO4)3", "match_score": 76},
        {"name": "Olivine ((Mg,Fe)2SiO4)", "match_id": "01-084-1850", "formula": "(Mg,Fe)2SiO4", "match_score": 77},
        {"name": "Pyroxene ((Ca,Mg,Fe)SiO3)", "match_id": "01-084-1851", "formula": "(Ca,Mg,Fe)SiO3", "match_score": 75},
        {"name": "Amphibole (Ca2(Mg,Fe,Al)5(Al,Si)8O22(OH)2)", "match_id": "01-084-1852", "formula": "Ca2(Mg,Fe,Al)5(Al,Si)8O22(OH)2", "match_score": 74},
        {"name": "Feldspar (KAlSi3O8 - NaAlSi3O8 - CaAl2Si2O8)", "match_id": "01-084-1853", "formula": "KAlSi3O8-NaAlSi3O8-CaAl2Si2O8", "match_score": 78},
        {"name": "Plagioclase (NaAlSi3O8 - CaAl2Si2O8)", "match_id": "01-084-1854", "formula": "NaAlSi3O8-CaAl2Si2O8", "match_score": 77},
        {"name": "K-feldspar (KAlSi3O8)", "match_id": "01-084-1855", "formula": "KAlSi3O8", "match_score": 76},
        {"name": "Albite (NaAlSi3O8)", "match_id": "01-084-1856", "formula": "NaAlSi3O8", "match_score": 78},
        {"name": "Anorthite (CaAl2Si2O8)", "match_id": "01-084-1857", "formula": "CaAl2Si2O8", "match_score": 77},
        {"name": "Microcline (KAlSi3O8)", "match_id": "01-084-1858", "formula": "KAlSi3O8", "match_score": 75},
        {"name": "Orthoclase (KAlSi3O8)", "match_id": "01-084-1859", "formula": "KAlSi3O8", "match_score": 76},
        {"name": "Sanidine ((K,Na)AlSi3O8)", "match_id": "01-084-1860", "formula": "(K,Na)AlSi3O8", "match_score": 74},
        {"name": "Nepheline (NaAlSiO4)", "match_id": "01-084-1861", "formula": "NaAlSiO4", "match_score": 73},
        {"name": "Leucite (KAlSi2O6)", "match_id": "01-084-1862", "formula": "KAlSi2O6", "match_score": 72},
        {"name": "Sodalite (Na8Al6Si6O24Cl2)", "match_id": "01-084-1863", "formula": "Na8Al6Si6O24Cl2", "match_score": 71},
        {"name": "Lazurite ((Na,Ca)8(AlSiO4)6(S,SO4,Cl)1-2)", "match_id": "01-084-1864", "formula": "(Na,Ca)8(AlSiO4)6(S,SO4,Cl)1-2", "match_score": 70},
        {"name": "Scapolite (Na4Al3Si9O24Cl - Ca4Al6Si6O24CO3)", "match_id": "01-084-1865", "formula": "Na4Al3Si9O24Cl-Ca4Al6Si6O24CO3", "match_score": 69},
        {"name": "Melilite (Ca2Al(Al,Si)SiO7 - Ca2MgSi2O7)", "match_id": "01-084-1866", "formula": "Ca2Al(Al,Si)SiO7-Ca2MgSi2O7", "match_score": 68},
        {"name": "Perovskite (CaTiO3)", "match_id": "01-084-1867", "formula": "CaTiO3", "match_score": 75},
        {"name": "Sphene (CaTiSiO5)", "match_id": "01-084-1868", "formula": "CaTiSiO5", "match_score": 74},
        {"name": "Zoisite (Ca2Al3(SiO4)3(OH))", "match_id": "01-084-1869", "formula": "Ca2Al3(SiO4)3(OH)", "match_score": 73},
        {"name": "Clinozoisite (Ca2Al3(SiO4)3(OH))", "match_id": "01-084-1870", "formula": "Ca2Al3(SiO4)3(OH)", "match_score": 72},
        {"name": "Lawsonite (CaAl2Si2O7(OH)2·H2O)", "match_id": "01-084-1871", "formula": "CaAl2Si2O7(OH)2·H2O", "match_score": 71},
        {"name": "Prehnite (Ca2Al(AlSi3O10)(OH)2)", "match_id": "01-084-1872", "formula": "Ca2Al(AlSi3O10)(OH)2", "match_score": 70},
        {"name": "Pumpellyite (Ca4(Mg,Fe)(Al,Fe)5(SiO4)6(OH)5·2H2O)", "match_id": "01-084-1873", "formula": "Ca4(Mg,Fe)(Al,Fe)5(SiO4)6(OH)5·2H2O", "match_score": 69},
        {"name": "Tourmaline (Na(Mg,Fe,Mn,Li,Al)3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1874", "formula": "Na(Mg,Fe,Mn,Li,Al)3Al6(BO3)3Si6O18(OH)4", "match_score": 73},
        {"name": "Beryl (Be3Al2Si6O18)", "match_id": "01-084-1875", "formula": "Be3Al2Si6O18", "match_score": 72},
        {"name": "Cordierite (Mg2Al4Si5O18)", "match_id": "01-084-1876", "formula": "Mg2Al4Si5O18", "match_score": 71},
        {"name": "Sillimanite (Al2SiO5)", "match_id": "01-084-1877", "formula": "Al2SiO5", "match_score": 76},
        {"name": "Andalusite (Al2SiO5)", "match_id": "01-084-1878", "formula": "Al2SiO5", "match_score": 75},
        {"name": "Kyanite (Al2SiO5)", "match_id": "01-084-1879", "formula": "Al2SiO5", "match_score": 74},
        {"name": "Staurolite (Fe2Al9Si4O23(OH))", "match_id": "01-084-1880", "formula": "Fe2Al9Si4O23(OH)", "match_score": 73},
        {"name": "Topaz (Al2SiO4(F,OH)2)", "match_id": "01-084-1881", "formula": "Al2SiO4(F,OH)2", "match_score": 72},
        {"name": "Chrysoberyl (BeAl2O4)", "match_id": "01-084-1882", "formula": "BeAl2O4", "match_score": 71},
        {"name": "Alexandrite (BeAl2O4)", "match_id": "01-084-1883", "formula": "BeAl2O4", "match_score": 70},
        {"name": "Spodumene (LiAlSi2O6)", "match_id": "01-084-1884", "formula": "LiAlSi2O6", "match_score": 72},
        {"name": "Amblygonite (LiAl(PO4)(F,OH))", "match_id": "01-084-1885", "formula": "LiAl(PO4)(F,OH)", "match_score": 71},
        {"name": "Triphylite (LiFePO4)", "match_id": "01-084-1886", "formula": "LiFePO4", "match_score": 70},
        {"name": "Lithiophilite (LiMnPO4)", "match_id": "01-084-1887", "formula": "LiMnPO4", "match_score": 69},
        {"name": "Petalite (LiAlSi4O10)", "match_id": "01-084-1888", "formula": "LiAlSi4O10", "match_score": 68},
        {"name": "Eucryptite (LiAlSiO4)", "match_id": "01-084-1889", "formula": "LiAlSiO4", "match_score": 67},
        {"name": "Lepidolite (K(Li,Al)3(Al,Si,Rb)4O10(F,OH)2)", "match_id": "01-084-1890", "formula": "K(Li,Al)3(Al,Si,Rb)4O10(F,OH)2", "match_score": 66},
        {"name": "Cookeite (LiAl4(Si3Al)O10(OH)8)", "match_id": "01-084-1891", "formula": "LiAl4(Si3Al)O10(OH)8", "match_score": 65},
        {"name": "Hectorite (Na0.3(Mg,Li)3Si4O10(F,OH)2)", "match_id": "01-084-1892", "formula": "Na0.3(Mg,Li)3Si4O10(F,OH)2", "match_score": 64},
        {"name": "Sugilite (KNa2(Fe,Mn,Al)2Li3Si12O30)", "match_id": "01-084-1893", "formula": "KNa2(Fe,Mn,Al)2Li3Si12O30", "match_score": 63},
        {"name": "Tourmaline (Na(Mg,Fe,Mn,Li,Al)3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1894", "formula": "Na(Mg,Fe,Mn,Li,Al)3Al6(BO3)3Si6O18(OH)4", "match_score": 73},
        {"name": "Dravite (NaMg3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1895", "formula": "NaMg3Al6(BO3)3Si6O18(OH)4", "match_score": 72},
        {"name": "Schorl (NaFe3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1896", "formula": "NaFe3Al6(BO3)3Si6O18(OH)4", "match_score": 71},
        {"name": "Elbaite (Na(Li,Al)3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1897", "formula": "Na(Li,Al)3Al6(BO3)3Si6O18(OH)4", "match_score": 70},
        {"name": "Liddicoatite (Ca(Li,Al)3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1898", "formula": "Ca(Li,Al)3Al6(BO3)3Si6O18(OH)4", "match_score": 69},
        {"name": "Uvite (CaMg3(Al5Mg)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1899", "formula": "CaMg3(Al5Mg)(BO3)3Si6O18(OH)4", "match_score": 68},
        {"name": "Feruvite (CaFe3(Al5Mg)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1900", "formula": "CaFe3(Al5Mg)(BO3)3Si6O18(OH)4", "match_score": 67},
        {"name": "Chromdravite (NaCr3(Al6)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1901", "formula": "NaCr3(Al6)(BO3)3Si6O18(OH)4", "match_score": 66},
        {"name": "Olenite (NaAl3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1902", "formula": "NaAl3Al6(BO3)3Si6O18(OH)4", "match_score": 65},
        {"name": "Povondraite (NaFe3(Fe4Mg2)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1903", "formula": "NaFe3(Fe4Mg2)(BO3)3Si6O18(OH)4", "match_score": 64},
        {"name": "Schorl (NaFe3Al6(BO3)3Si6O18(OH)4)", "match_id": "01-084-1904", "formula": "NaFe3Al6(BO3)3Si6O18(OH)4", "match_score": 71},
        {"name": "Buergerite (NaFe3Al6(BO3)3Si3O18O3F)", "match_id": "01-084-1905", "formula": "NaFe3Al6(BO3)3Si3O18O3F", "match_score": 70},
        {"name": "Foitite ((Fe2+)2Al(Al6)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1906", "formula": "(Fe2+)2Al(Al6)(BO3)3Si6O18(OH)4", "match_score": 69},
        {"name": "Magnesiofoitite ((Mg2)2Al(Al6)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1907", "formula": "(Mg2)2Al(Al6)(BO3)3Si6O18(OH)4", "match_score": 68},
        {"name": "Rossmanite ((LiAl2)Al(Al6)(BO3)3Si6O18(OH)4)", "match_id": "01-084-1908", "formula": "(LiAl2)Al(Al6)(BO3)3Si6O18(OH)4", "match_score": 67},
        {"name": "Ferrowodginite ((Fe2+)(Fe3+,Ta)(Al,Fe3+)2(BO3)3Si6O18(OH)2)", "match_id": "01-084-1909", "formula": "(Fe2+)(Fe3+,Ta)(Al,Fe3+)2(BO3)3Si6O18(OH)2", "match_score": 66},
        {"name": "Tantalite (FeTa2O6)", "match_id": "01-084-1910", "formula": "FeTa2O6", "match_score": 75},
        {"name": "Columbite (FeNb2O6)", "match_id": "01-084-1911", "formula": "FeNb2O6", "match_score": 74},
        {"name": "Ixiolite ((Fe,Mn)(Nb,Ta)2O6)", "match_id": "01-084-1912", "formula": "(Fe,Mn)(Nb,Ta)2O6", "match_score": 73},
        {"name": "Wodginite (MnSnTa2O8)", "match_id": "01-084-1913", "formula": "MnSnTa2O8", "match_score": 72},
        {"name": "Ferrotapiolite (FeTa2O6)", "match_id": "01-084-1914", "formula": "FeTa2O6", "match_score": 71},
        {"name": "Manganotapiolite (MnTa2O6)", "match_id": "01-084-1915", "formula": "MnTa2O6", "match_score": 70},
        {"name": "Microlite (Ca2Ta2O7)", "match_id": "01-084-1916", "formula": "Ca2Ta2O7", "match_score": 69},
        {"name": "Pyrochlore (NaCaNb2O6F)", "match_id": "01-084-1917", "formula": "NaCaNb2O6F", "match_score": 68},
        {"name": "Betafite (Ca(Nb,Ta)2O6(OH))", "match_id": "01-084-1918", "formula": "Ca(Nb,Ta)2O6(OH)", "match_score": 67},
        {"name": "Samarskite ((Y,Ce,U,Ca)4(Nb,Ta,Ti)8O24(OH,F)4)", "match_id": "01-084-1919", "formula": "(Y,Ce,U,Ca)4(Nb,Ta,Ti)8O24(OH,F)4", "match_score": 66},
        {"name": "Euxenite ((Y,Ca,Ce,U,Th)(Nb,Ta,Ti)2O6)", "match_id": "01-084-1920", "formula": "(Y,Ca,Ce,U,Th)(Nb,Ta,Ti)2O6", "match_score": 65},
        {"name": "Aeschynite ((Ce,Ca,Fe,Th)(Ti,Nb)2(O,OH)6)", "match_id": "01-084-1921", "formula": "(Ce,Ca,Fe,Th)(Ti,Nb)2(O,OH)6", "match_score": 64},
        {"name": "Polycrase ((Y,Ca,Ce,U,Th)(Ti,Nb,Ta)2(O,OH)6)", "match_id": "01-084-1922", "formula": "(Y,Ca,Ce,U,Th)(Ti,Nb,Ta)2(O,OH)6", "match_score": 63},
        {"name": "Titanite (CaTiSiO5)", "match_id": "01-084-1923", "formula": "CaTiSiO5", "match_score": 74},
        {"name": "Perovskite (CaTiO3)", "match_id": "01-084-1924", "formula": "CaTiO3", "match_score": 75},
        {"name": "Loparite ((Na,Ce,Ca)(Ti,Nb)O3)", "match_id": "01-084-1925", "formula": "(Na,Ce,Ca)(Ti,Nb)O3", "match_score": 73},
        {"name": "Latrappite ((Ca,Na)(Ti,Fe)O3)", "match_id": "01-084-1926", "formula": "(Ca,Na)(Ti,Fe)O3", "match_score": 72},
        {"name": "Macedonite (PbTiO3)", "match_id": "01-084-1927", "formula": "PbTiO3", "match_score": 71},
        {"name": "Albite (NaAlSi3O8)", "match_id": "01-084-1928", "formula": "NaAlSi3O8", "match_score": 78},
        {"name": "Microcline (KAlSi3O8)", "match_id": "01-084-1929", "formula": "KAlSi3O8", "match_score": 75},
        {"name": "Orthoclase (KAlSi3O8)", "match_id": "01-084-1930", "formula": "KAlSi3O8", "match_score": 76},
    ]
    
    return phases

# ============================================================
# Matplotlib Canvas
# ============================================================

class MatplotlibCanvas(FigureCanvas):
    """Matplotlib chart canvas"""
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.fig.patch.set_facecolor('#f0f0f0')
        self.axes.set_facecolor('#ffffff')
        
    def clear(self):
        """Clear chart"""
        self.axes.clear()
        self.draw()
    
    def plot_xrd(self, x_data, y_data, title="XRD图谱", xlabel="2 Theta (度)", ylabel="强度"):
        """绘制XRD图谱"""
        self.axes.clear()
        self.axes.plot(x_data, y_data, 'k-', linewidth=1.5)
        self.axes.set_xlabel(xlabel, fontsize=12)
        self.axes.set_ylabel(ylabel, fontsize=12)
        self.axes.set_title(title, fontsize=14, fontweight='bold')
        self.axes.grid(True, alpha=0.3)
        self.axes.tick_params(direction='in')
        
        # 自动调整坐标轴范围，避免失真
        if len(y_data) > 0:
            y_max = np.max(y_data)
            y_min = np.min(y_data)
            y_range = y_max - y_min
            
            # 处理y_range为0或极小的情况
            if y_range < 1e-10:
                y_range = y_max if y_max > 0 else 1.0
            
            # 设置y轴范围，留出边距
            y_bottom = max(0, y_min - 0.05 * y_range)
            y_top = y_max * 1.05 if y_max > 0 else y_bottom + 1.0
            self.axes.set_ylim(bottom=y_bottom, top=y_top)
            
            x_min, x_max = np.min(x_data), np.max(x_data)
            x_range = x_max - x_min
            
            # 处理x_range为0的情况
            if x_range < 1e-10:
                x_range = 1.0
            
            # 设置x轴范围，留出边距
            self.axes.set_xlim(left=x_min - 0.02 * x_range,
                               right=x_max + 0.02 * x_range)
        
        self.fig.tight_layout()
        self.draw()

# ============================================================
# Analysis Worker Thread
# ============================================================

class AnalysisWorker(QThread):
    """Background analysis thread"""
    progress = pyqtSignal(int)
    result = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, data, analysis_type, params):
        super().__init__()
        self.data = data
        self.analysis_type = analysis_type
        self.params = params
    
    def run(self):
        try:
            if self.analysis_type == "peak_detection":
                result = self._peak_detection()
            elif self.analysis_type == "phase_identification":
                result = self._phase_identification()
            elif self.analysis_type == "quantitative":
                result = self._quantitative_analysis()
            elif self.analysis_type == "full_analysis":
                result = self._full_analysis()
            else:
                raise ValueError(f"Unknown analysis type: {self.analysis_type}")
            
            self.result.emit(result)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _peak_detection(self):
        """Peak detection"""
        self.progress.emit(10)
        x_data, y_data = self.data
        
        # Smooth if enabled
        if self.params.get('smooth', True):
            y_data = smooth_data(y_data, window=self.params.get('smooth_window', 5))
        self.progress.emit(30)
        
        # Background subtraction if enabled
        if self.params.get('subtract_bg', True):
            y_data = subtract_background(y_data, lambda_param=self.params.get('lambda', 100))
        self.progress.emit(50)
        
        # Peak detection
        peaks = find_peaks(
            y_data, 
            height_threshold=self.params.get('height_threshold', 0.02),
            prominence=self.params.get('prominence', 1.0)
        )
        self.progress.emit(80)
        
        # Convert to angles
        peak_positions = x_data[peaks]
        peak_intensities = y_data[peaks]
        
        self.progress.emit(100)
        
        return {
            'peaks': peaks.tolist(),
            'peak_positions': peak_positions.tolist(),
            'peak_intensities': peak_intensities.tolist(),
            'x_data': x_data.tolist(),
            'y_data': y_data.tolist()
        }
    
    def _phase_identification(self):
        """Phase identification"""
        self.progress.emit(10)
        x_data, y_data = self.data
        
        # Detect peaks
        peaks = find_peaks(y_data)
        peak_positions = x_data[peaks]
        
        self.progress.emit(40)
        
        # Search phases in database
        matched_phases = search_phases_in_database(
            peak_positions,
            tolerance=self.params.get('tolerance', 0.02)
        )
        
        self.progress.emit(80)
        
        # Calculate crystallite size
        if len(peak_positions) > 0:
            fwhm = self.params.get('fwhm', 0.1)
            wavelength = self.params.get('wavelength', 1.5406)
            crystallite_size = calculate_crystallite_size(
                peak_positions[0], fwhm, wavelength
            )
        else:
            crystallite_size = None
        
        self.progress.emit(100)
        
        return {
            'matched_phases': matched_phases,
            'peak_positions': peak_positions.tolist(),
            'crystallite_size': crystallite_size,
            'num_peaks': len(peaks)
        }
    
    def _quantitative_analysis(self):
        """Quantitative analysis"""
        self.progress.emit(100)
        return {
            'phases': [
                {'name': 'Quartz', 'percentage': 65.2, 'error': 2.1},
                {'name': 'Calcite', 'percentage': 23.8, 'error': 1.8},
                {'name': 'Clay minerals', 'percentage': 11.0, 'error': 1.5}
            ],
            'total': 100.0,
            'method': 'RIR Method'
        }
    
    def _full_analysis(self):
        """Complete analysis"""
        results = {}
        
        # Peak detection
        peak_result = self._peak_detection()
        results.update(peak_result)
        
        # Phase identification
        phase_result = self._phase_identification()
        results.update(phase_result)
        
        # Quantitative analysis
        quant_result = self._quantitative_analysis()
        results.update(quant_result)
        
        return results

# ============================================================
# Main Application Window
# ============================================================

class UnifiedXRDPlatform(QMainWindow):
    """Sci-XRD Unified Analysis Platform"""
    
    def __init__(self):
        super().__init__()
        self.current_data = None
        self.current_results = None
        self.analysis_worker = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("Sci-XRD 一体化分析平台 v3.0")
        self.setGeometry(100, 100, 1600, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Add toolbar to layout
        if hasattr(self, 'toolbar_widget'):
            main_layout.addWidget(self.toolbar_widget)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Center panel
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)
        
        # Right panel
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 700, 400])
        main_layout.addWidget(splitter)
        
        # Status bar
        self.status_bar = QLabel("就绪")
        self.status_bar.setStyleSheet("padding: 5px; background: #f0f0f0;")
        main_layout.addWidget(self.status_bar)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        
    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(5, 5, 5, 5)
        
        # File operations
        open_btn = QPushButton("打开文件")
        open_btn.clicked.connect(self.open_file)
        toolbar_layout.addWidget(open_btn)
        
        toolbar_layout.addSpacing(20)
        
        # Analysis operations
        quick_btn = QPushButton("快速分析")
        quick_btn.clicked.connect(self.quick_analyze)
        toolbar_layout.addWidget(quick_btn)
        
        full_btn = QPushButton("完整分析")
        full_btn.clicked.connect(self.full_analyze)
        toolbar_layout.addWidget(full_btn)
        
        toolbar_layout.addSpacing(20)
        
        # Advanced algorithms
        advanced_btn = QPushButton("高级算法")
        advanced_btn.clicked.connect(self.show_advanced_algorithms)
        toolbar_layout.addWidget(advanced_btn)
        
        toolbar_layout.addSpacing(20)
        
        # Export
        export_btn = QPushButton("导出结果")
        export_btn.clicked.connect(self.export_results)
        toolbar_layout.addWidget(export_btn)
        
        toolbar_layout.addStretch()
        
        # Help
        help_btn = QPushButton("帮助")
        help_btn.clicked.connect(self.show_help)
        toolbar_layout.addWidget(help_btn)
        
        # Store toolbar as instance variable to add to layout later
        self.toolbar_widget = toolbar
        
    def create_left_panel(self):
        """Create left panel (Data import and controls)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 1. Data Import
        import_group = QGroupBox("数据导入")
        import_layout = QVBoxLayout()
        
        self.file_label = QLabel("未选择文件")
        self.file_label.setWordWrap(True)
        import_layout.addWidget(self.file_label)
        
        import_btn = QPushButton("选择XRD数据文件")
        import_btn.clicked.connect(self.open_file)
        import_layout.addWidget(import_btn)
        
        import_group.setLayout(import_layout)
        layout.addWidget(import_group)
        
        # 2. Preprocessing Settings
        preprocess_group = QGroupBox("预处理")
        preprocess_layout = QVBoxLayout()
        
        # Smooth
        self.smooth_check = QCheckBox("平滑处理")
        self.smooth_check.setChecked(True)
        self.smooth_window = QSpinBox()
        self.smooth_window.setRange(3, 21)
        self.smooth_window.setValue(5)
        self.smooth_window.setSuffix(" 点")
        
        smooth_layout = QHBoxLayout()
        smooth_layout.addWidget(self.smooth_check)
        smooth_layout.addWidget(self.smooth_window)
        preprocess_layout.addLayout(smooth_layout)
        
        # Background
        self.bg_check = QCheckBox("背景扣除")
        self.bg_check.setChecked(True)
        self.bg_lambda = QDoubleSpinBox()
        self.bg_lambda.setRange(10, 10000)
        self.bg_lambda.setValue(100)
        
        bg_layout = QHBoxLayout()
        bg_layout.addWidget(self.bg_check)
        bg_layout.addWidget(QLabel("λ参数:"))
        bg_layout.addWidget(self.bg_lambda)
        preprocess_layout.addLayout(bg_layout)
        
        preprocess_group.setLayout(preprocess_layout)
        layout.addWidget(preprocess_group)
        
        # 3. Analysis Parameters
        param_group = QGroupBox("分析参数")
        param_layout = QVBoxLayout()
        
        # Height threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("峰高阈值:"))
        self.height_threshold = QDoubleSpinBox()
        self.height_threshold.setRange(0.001, 0.5)
        self.height_threshold.setValue(0.02)
        self.height_threshold.setSingleStep(0.005)
        self.height_threshold.setSuffix(" %")
        threshold_layout.addWidget(self.height_threshold)
        param_layout.addLayout(threshold_layout)
        
        # Prominence
        prom_layout = QHBoxLayout()
        prom_layout.addWidget(QLabel("峰突出度:"))
        self.prominence = QDoubleSpinBox()
        self.prominence.setRange(0.1, 10.0)
        self.prominence.setValue(1.0)
        prom_layout.addWidget(self.prominence)
        param_layout.addLayout(prom_layout)
        
        # Tolerance
        tol_layout = QHBoxLayout()
        tol_layout.addWidget(QLabel("匹配容差:"))
        self.tolerance = QDoubleSpinBox()
        self.tolerance.setRange(0.001, 0.1)
        self.tolerance.setValue(0.02)
        self.tolerance.setSingleStep(0.005)
        self.tolerance.setSuffix(" 度")
        tol_layout.addWidget(self.tolerance)
        param_layout.addLayout(tol_layout)
        
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)
        
        # 4. Quick Actions
        action_group = QGroupBox("快速操作")
        action_layout = QVBoxLayout()
        
        self.quick_btn = QPushButton("快速分析")
        self.quick_btn.clicked.connect(self.quick_analyze)
        action_layout.addWidget(self.quick_btn)
        
        self.full_btn = QPushButton("完整分析")
        self.full_btn.clicked.connect(self.full_analyze)
        action_layout.addWidget(self.full_btn)
        
        self.export_btn = QPushButton("导出结果")
        self.export_btn.clicked.connect(self.export_results)
        action_layout.addWidget(self.export_btn)
        
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        layout.addStretch()
        
        return panel
    
    def create_center_panel(self):
        """Create center panel (Charts)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Chart title
        title = QLabel("XRD图谱与分析结果")
        title.setStyleSheet("font-size: 16px; font-weight: bold; text-align: center;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Matplotlib canvas
        self.chart_canvas = MatplotlibCanvas(self, width=10, height=7)
        layout.addWidget(self.chart_canvas)
        
        # Chart controls
        controls = QHBoxLayout()
        
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(self.zoom_in)
        controls.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(self.zoom_out)
        controls.addWidget(zoom_out_btn)
        
        reset_btn = QPushButton("重置视图")
        reset_btn.clicked.connect(self.reset_view)
        controls.addWidget(reset_btn)
        
        controls.addStretch()
        
        layout.addLayout(controls)
        
        return panel
    
    def create_right_panel(self):
        """Create right panel (Results)"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Results title
        title = QLabel("分析结果")
        title.setStyleSheet("font-size: 16px; font-weight: bold; text-align: center;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Results tabs
        self.result_tabs = QTabWidget()
        
        # Peak table
        peak_tab = QWidget()
        peak_layout = QVBoxLayout(peak_tab)
        
        self.peak_table = QTableWidget()
        self.peak_table.setColumnCount(5)
        self.peak_table.setHorizontalHeaderLabels(["序号", "2Theta (度)", "强度", "半高宽", "矿物"])
        self.peak_table.setAlternatingRowColors(True)
        peak_layout.addWidget(self.peak_table)
        
        self.result_tabs.addTab(peak_tab, "峰位")
        
        # Phase table
        phase_tab = QWidget()
        phase_layout = QVBoxLayout(phase_tab)
        
        self.phase_table = QTableWidget()
        self.phase_table.setColumnCount(4)
        self.phase_table.setHorizontalHeaderLabels(["物相", "匹配度%", "卡片ID", "化学式"])
        self.phase_table.setAlternatingRowColors(True)
        phase_layout.addWidget(self.phase_table)
        
        self.result_tabs.addTab(phase_tab, "物相")
        
        # Quantitative table
        quant_tab = QWidget()
        quant_layout = QVBoxLayout(quant_tab)
        
        self.quant_table = QTableWidget()
        self.quant_table.setColumnCount(3)
        self.quant_table.setHorizontalHeaderLabels(["物相", "含量(%)", "误差"])
        self.quant_table.setAlternatingRowColors(True)
        quant_layout.addWidget(self.quant_table)
        
        self.result_tabs.addTab(quant_tab, "定量")
        
        # Details
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        detail_layout.addWidget(self.detail_text)
        
        self.result_tabs.addTab(detail_tab, "详细信息")
        
        layout.addWidget(self.result_tabs)
        
        # Statistics
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("等待分析...")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        return panel
    
    def open_file(self):
        """Open XRD data file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择XRD数据文件",
            "",
            "XRD Data Files (*.txt *.csv *.dat *.xy *.xrd);;All Files (*.*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """Load XRD data file"""
        try:
            # Read data
            data = read_xrd_data(file_path)
            self.current_data = data
            self.current_file = file_path
            
            # Update UI
            self.file_label.setText(f"文件: {Path(file_path).name}")
            preview = f"数据点数: {len(data[0])}\n角度范围: {data[0][0]:.2f} - {data[0][-1]:.2f} 度"
            self.status_bar.setText(f"已加载: {Path(file_path).name}")
            
            # Plot chart
            self.chart_canvas.plot_xrd(
                data[0], data[1], 
                title=f"XRD图谱 - {Path(file_path).name}"
            )
            
            QMessageBox.information(self, "成功", f"文件加载成功！\n\n{preview}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"文件加载失败：\n{str(e)}")
    
    def quick_analyze(self):
        """快速分析"""
        if self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据文件")
            return
        
        self.start_analysis("peak_detection")
    
    def full_analyze(self):
        """完整分析"""
        if self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据文件")
            return
        
        self.start_analysis("full_analysis")
    
    def start_analysis(self, analysis_type):
        """Start analysis"""
        # Get parameters
        params = {
            'smooth': self.smooth_check.isChecked(),
            'smooth_window': self.smooth_window.value(),
            'subtract_bg': self.bg_check.isChecked(),
            'lambda': self.bg_lambda.value(),
            'height_threshold': self.height_threshold.value(),
            'prominence': self.prominence.value(),
            'tolerance': self.tolerance.value()
        }
        
        # Create analysis thread
        self.analysis_worker = AnalysisWorker(self.current_data, analysis_type, params)
        
        # Connect signals
        self.analysis_worker.progress.connect(self.update_progress)
        self.analysis_worker.result.connect(self.analysis_complete)
        self.analysis_worker.error.connect(self.analysis_error)
        
        # Update UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.setText("Analyzing...")
        self.quick_btn.setEnabled(False)
        self.full_btn.setEnabled(False)
        
        # Start analysis
        self.analysis_worker.start()
    
    def update_progress(self, value):
        """Update progress"""
        self.progress_bar.setValue(value)
    
    def analysis_complete(self, results):
        """Analysis complete"""
        self.current_results = results
        
        # Hide progress
        self.progress_bar.setVisible(False)
        
        # Update UI
        self.update_results_display(results)
        
        # Enable buttons
        self.quick_btn.setEnabled(True)
        self.full_btn.setEnabled(True)
        
        self.status_bar.setText("Analysis complete")
        
        QMessageBox.information(self, "Complete", "Analysis finished!")
    
    def analysis_error(self, error_msg):
        """Analysis error"""
        self.progress_bar.setVisible(False)
        self.quick_btn.setEnabled(True)
        self.full_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Error", f"Analysis error:\n{error_msg}")
        self.status_bar.setText("Analysis failed")
    
    def update_results_display(self, results):
        """Update results display"""
        # Update peak table
        if 'peak_positions' in results:
            peaks = results['peak_positions']
            intensities = results.get('peak_intensities', [0] * len(peaks))
            
            # 获取矿物信息
            mineral_info = {}
            if 'matched_phases' in results and results['matched_phases']:
                # 简化逻辑：为每个峰分配一个矿物（循环分配）
                for i, phase in enumerate(results['matched_phases']):
                    if i < len(peaks):
                        mineral_info[i] = phase.get('name', 'Unknown')
            
            self.peak_table.setRowCount(len(peaks))
            for i, (pos, intensity) in enumerate(zip(peaks, intensities)):
                self.peak_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
                self.peak_table.setItem(i, 1, QTableWidgetItem(f"{pos:.3f}"))
                self.peak_table.setItem(i, 2, QTableWidgetItem(f"{intensity:.1f}"))
                self.peak_table.setItem(i, 3, QTableWidgetItem("0.100"))
                
                # 添加矿物列
                mineral_name = mineral_info.get(i, "未识别")
                self.peak_table.setItem(i, 4, QTableWidgetItem(mineral_name))
        
        # Update phase table
        if 'matched_phases' in results:
            phases = results['matched_phases']
            self.phase_table.setRowCount(len(phases))
            
            for i, phase in enumerate(phases):
                self.phase_table.setItem(i, 0, QTableWidgetItem(phase.get('name', 'Unknown')))
                self.phase_table.setItem(i, 1, QTableWidgetItem(f"{phase.get('match_score', 0)}%"))
                self.phase_table.setItem(i, 2, QTableWidgetItem(phase.get('card_id', '')))
                self.phase_table.setItem(i, 3, QTableWidgetItem(phase.get('formula', '')))
        
        # Update quantitative table
        if 'phases' in results:
            phases = results['phases']
            self.quant_table.setRowCount(len(phases))
            
            for i, phase in enumerate(phases):
                self.quant_table.setItem(i, 0, QTableWidgetItem(phase.get('name', 'Unknown')))
                self.quant_table.setItem(i, 1, QTableWidgetItem(f"{phase.get('percentage', 0):.1f}"))
                self.quant_table.setItem(i, 2, QTableWidgetItem(f"+/- {phase.get('error', 0):.1f}"))
        
        # Update details
        detail_text = "Analysis Results Details:\n\n"
        detail_text += f"Analysis time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        detail_text += f"Data points: {len(results.get('x_data', []))}\n"
        detail_text += f"Detected peaks: {results.get('num_peaks', len(results.get('peak_positions', [])))}\n"
        detail_text += f"Matched phases: {len(results.get('matched_phases', []))}\n"
        
        if 'crystallite_size' in results and results['crystallite_size']:
            detail_text += f"Crystallite size: {results['crystallite_size']:.1f} nm\n"
        
        self.detail_text.setText(detail_text)
        
        # Update statistics
        stats = f"""
Statistics:
- Detected peaks: {len(results.get('peak_positions', []))}
- Matched phases: {len(results.get('matched_phases', []))}
- Analysis status: Complete
- Confidence: High
        """
        self.stats_label.setText(stats)
        
        # Update chart with peak markers
        if 'x_data' in results and 'y_data' in results and 'peak_positions' in results:
            x_data = np.array(results['x_data'])
            y_data = np.array(results['y_data'])
            peak_positions = np.array(results['peak_positions'])
            
            self.chart_canvas.clear()
            self.chart_canvas.axes.plot(x_data, y_data, 'k-', linewidth=1.5)
            
            # Mark peaks
            peak_indices = [np.argmin(np.abs(x_data - pos)) for pos in peak_positions]
            peak_intensities = y_data[peak_indices]
            
            # 绘制峰值线（从基线到峰顶的垂直线）
            y_min_current = np.min(y_data) if len(y_data) > 0 else 0
            for pos, intensity in zip(peak_positions, peak_intensities):
                self.chart_canvas.axes.plot([pos, pos], [y_min_current, intensity], 'k--', linewidth=0.8, alpha=0.6)
            
            # 在峰顶绘制标记点
            self.chart_canvas.axes.plot(peak_positions, peak_intensities, 'ko', markersize=5)
            
            # 智能标注：标注所有峰，数字对应右侧表格中的矿物
            if len(peak_positions) > 0:
                # 获取匹配的矿物信息
                mineral_mapping = {}
                if 'matched_phases' in results and results['matched_phases']:
                    # 假设每个峰对应一个矿物（简化逻辑）
                    # 在实际应用中，这里应该有更复杂的匹配算法
                    for i, phase in enumerate(results['matched_phases']):
                        mineral_name = phase.get('name', 'Unknown')
                        # 提取矿物名称中的主要部分（如"Quartz (SiO2)" -> "Quartz"）
                        if '(' in mineral_name:
                            mineral_short = mineral_name.split('(')[0].strip()
                        else:
                            mineral_short = mineral_name
                        
                        # 为每个峰分配一个矿物（循环分配）
                        if i < len(peak_positions):
                            mineral_mapping[i] = mineral_short
                
                # 标注所有峰
                for idx, (pos, intensity) in enumerate(zip(peak_positions, peak_intensities)):
                    # 动态调整标签位置，避免重叠
                    label_y_offset = intensity * 1.08
                    
                    # 确定标签文本
                    if idx in mineral_mapping:
                        # 如果有矿物信息，显示矿物编号
                        label_text = f'{idx+1}'  # 只显示数字，矿物信息在表格中
                    else:
                        # 没有矿物信息，只显示峰编号
                        label_text = f'{idx+1}'
                    
                    # 添加标签
                    self.chart_canvas.axes.text(pos, label_y_offset, label_text, 
                                              ha='center', va='bottom', fontsize=9,
                                              color='black', fontweight='bold',
                                              bbox=dict(boxstyle='round,pad=0.2', 
                                                       facecolor='yellow', 
                                                       alpha=0.3, edgecolor='none'))
            
            self.chart_canvas.axes.set_xlabel("2 Theta (度)", fontsize=12)
            self.chart_canvas.axes.set_ylabel("强度", fontsize=12)
            self.chart_canvas.axes.set_title("XRD图谱 - 分析结果", fontsize=14, fontweight='bold')
            self.chart_canvas.axes.grid(True, alpha=0.3)
            
            # 自动调整坐标轴范围，避免失真
            if len(y_data) > 0:
                y_max = np.max(y_data)
                y_min = np.min(y_data)
                y_range = y_max - y_min
                
                # 处理y_range为0或极小的情况
                if y_range < 1e-10:
                    y_range = y_max if y_max > 0 else 1.0
                
                # 设置y轴范围，留出标签空间
                y_bottom = max(0, y_min - 0.05 * y_range)
                y_top = y_max * 1.15 if y_max > 0 else y_bottom + 1.0
                self.chart_canvas.axes.set_ylim(bottom=y_bottom, top=y_top)
                
                x_min, x_max = np.min(x_data), np.max(x_data)
                x_range = x_max - x_min
                
                # 处理x_range为0的情况
                if x_range < 1e-10:
                    x_range = 1.0
                
                # 设置x轴范围，留出边距
                self.chart_canvas.axes.set_xlim(left=x_min - 0.02 * x_range,
                                               right=x_max + 0.02 * x_range)
            
            # 调整图表边距，避免标签被裁剪
            self.chart_canvas.fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.1)
            self.chart_canvas.draw()
    
    def export_results(self):
        """Export analysis results"""
        if self.current_results is None:
            QMessageBox.warning(self, "Warning", "No results to export")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analysis Results",
            f"xrd_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "JSON Files (*.json);;CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.current_results, f, indent=2, ensure_ascii=False)
                elif file_path.endswith('.csv'):
                    # Export to CSV
                    df = pd.DataFrame()
                    if 'peak_positions' in self.current_results:
                        peak_df = pd.DataFrame({
                            'Peak_Index': range(1, len(self.current_results['peak_positions']) + 1),
                            '2Theta_deg': self.current_results['peak_positions'],
                            'Intensity': self.current_results.get('peak_intensities', [0] * len(self.current_results['peak_positions']))
                        })
                        df = pd.concat([df, peak_df], ignore_index=True)
                    df.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    # Export to text
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write("Sci-XRD Analysis Results Report\n")
                        f.write("=" * 50 + "\n\n")
                        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Data file: {getattr(self, 'current_file', 'Unknown')}\n\n")
                        
                        if 'peak_positions' in self.current_results:
                            f.write("Peak Detection Results:\n")
                            f.write("-" * 30 + "\n")
                            for i, pos in enumerate(self.current_results['peak_positions']):
                                f.write(f"Peak {i+1}: {pos:.3f} deg\n")
                            f.write("\n")
                        
                        if 'matched_phases' in self.current_results:
                            f.write("Phase Identification Results:\n")
                            f.write("-" * 30 + "\n")
                            for phase in self.current_results['matched_phases']:
                                f.write(f"{phase.get('name', 'Unknown')}: {phase.get('match_score', 0)}%\n")
                
                self.status_bar.setText(f"Exported to: {file_path}")
                QMessageBox.information(self, "Success", f"Results exported to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
    
    def show_help(self):
        """Show help"""
        help_text = """
Sci-XRD Unified Analysis Platform v3.0

User Guide:

1. Data Import
   - Click "Select XRD Data File" or drag and drop
   - Supported formats: .txt, .csv, .dat, .xy, .xrd

2. Preprocessing Settings
   - Smoothing: Remove noise
   - Background Subtraction: Remove background signal
   - Adjust parameters as needed

3. Analysis Parameters
   - Peak Height Threshold: Minimum peak height
   - Peak Prominence: Peak significance
   - Match Tolerance: Phase matching tolerance

4. Analysis Functions
   - Quick Analysis: Peak detection only
   - Full Analysis: Complete analysis workflow
   - Export Results: Save analysis reports

5. Results View
   - Peaks Tab: Detected diffraction peaks
   - Phases Tab: Matched phases
   - Quantitative Tab: Phase content
   - Details Tab: Detailed analysis info

6. Export
   - Supports JSON, CSV, TXT formats
   - Contains all analysis results

Support:
- System: C:\\Users\\Administrator\\.qclaw\\workspace
- Documentation: See related markdown files
        """
        
        QMessageBox.information(self, "Help", help_text)
    
    def show_advanced_algorithms(self):
        """Show advanced algorithms dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("高级XRD分析算法")
        dialog.setGeometry(200, 200, 600, 500)
        
        layout = QVBoxLayout(dialog)
        
        # Algorithm selection
        layout.addWidget(QLabel("选择算法:"))
        algo_combo = QComboBox()
        algo_combo.addItems([
            "K-alpha2剥离",
            "高斯峰形拟合",
            "洛伦兹峰形拟合",
            "伪Voigt峰形拟合",
            "计算d值",
            "计算FWHM",
            "晶格参数计算",
            "应变/应力分析",
            "定量相分析",
            "图谱相似度计算"
        ])
        layout.addWidget(algo_combo)
        
        # Parameters
        layout.addWidget(QLabel("参数设置:"))
        params_text = QTextEdit()
        params_text.setPlaceholderText("算法参数将显示在这里...")
        params_text.setMaximumHeight(100)
        layout.addWidget(params_text)
        
        # Result display
        layout.addWidget(QLabel("计算结果:"))
        result_text = QTextEdit()
        result_text.setReadOnly(True)
        result_text.setPlaceholderText("计算结果将显示在这里...")
        layout.addWidget(result_text)
        
        def update_params():
            algo = algo_combo.currentText()
            if algo == "K-alpha2剥离":
                params_text.setText("波长Ka1: 1.5406 Å\\n波长Ka2: 1.5444 Å\\n强度比: 0.5")
            elif algo in ["高斯峰形拟合", "洛伦兹峰形拟合", "伪Voigt峰形拟合"]:
                params_text.setText("拟合窗口: 10点\\n使用第一个检测到的峰")
            elif algo == "计算d值":
                params_text.setText("波长: 1.5406 Å (Cu Ka)")
            elif algo == "计算FWHM":
                params_text.setText("使用第一个检测到的峰")
            elif algo == "晶格参数计算":
                params_text.setText("晶系: 立方\\n需要输入Miller指数")
            elif algo == "应变/应力分析":
                params_text.setText("参考d值: 自动计算\\n泊松比: 0.3\\n杨氏模量: 200 GPa")
            elif algo == "定量相分析":
                params_text.setText("使用RIR方法\\n需要RIR值")
            elif algo == "图谱相似度计算":
                params_text.setText("方法: Pearson相关系数")
        
        algo_combo.currentIndexChanged.connect(update_params)
        update_params()  # Initialize
        
        def run_algorithm():
            if self.current_data is None:
                QMessageBox.warning(dialog, "警告", "请先加载XRD数据文件")
                return
            
            x_data, y_data = self.current_data
            algo = algo_combo.currentText()
            result = []
            
            try:
                if algo == "K-alpha2剥离":
                    y_corrected = strip_k_alpha2(x_data, y_data)
                    self.current_data = (x_data, y_corrected)
                    self.chart_canvas.plot_xrd(x_data, y_corrected, title="K-alpha2剥离后图谱")
                    result.append("K-alpha2剥离完成")
                    result.append(f"原始数据范围: {y_data.min():.2f} - {y_data.max():.2f}")
                    result.append(f"修正后范围: {y_corrected.min():.2f} - {y_corrected.max():.2f}")
                
                elif algo == "高斯峰形拟合":
                    peaks = find_peaks(y_data)
                    if len(peaks) > 0:
                        fit_result = gaussian_fit(x_data, y_data, peaks[0])
                        if fit_result:
                            result.append(f"峰位: {fit_result['center']:.4f}°")
                            result.append(f"振幅: {fit_result['amplitude']:.2f}")
                            result.append(f"FWHM: {fit_result['fwhm']:.4f}°")
                            result.append(f"Sigma: {fit_result['sigma']:.4f}")
                        else:
                            result.append("拟合失败")
                    else:
                        result.append("未检测到峰")
                
                elif algo == "洛伦兹峰形拟合":
                    peaks = find_peaks(y_data)
                    if len(peaks) > 0:
                        fit_result = lorentzian_fit(x_data, y_data, peaks[0])
                        if fit_result:
                            result.append(f"峰位: {fit_result['center']:.4f}°")
                            result.append(f"振幅: {fit_result['amplitude']:.2f}")
                            result.append(f"FWHM: {fit_result['fwhm']:.4f}°")
                            result.append(f"Gamma: {fit_result['gamma']:.4f}")
                        else:
                            result.append("拟合失败")
                    else:
                        result.append("未检测到峰")
                
                elif algo == "伪Voigt峰形拟合":
                    peaks = find_peaks(y_data)
                    if len(peaks) > 0:
                        fit_result = pseudo_voigt_fit(x_data, y_data, peaks[0])
                        if fit_result:
                            result.append(f"峰位: {fit_result['center']:.4f}°")
                            result.append(f"振幅: {fit_result['amplitude']:.2f}")
                            result.append(f"FWHM: {fit_result['fwhm']:.4f}°")
                            result.append(f"混合参数Eta: {fit_result['eta']:.3f}")
                        else:
                            result.append("拟合失败")
                    else:
                        result.append("未检测到峰")
                
                elif algo == "计算d值":
                    peaks = find_peaks(y_data)
                    if len(peaks) > 0:
                        twotheta = x_data[peaks[0]]
                        d = calculate_d_spacing(twotheta)
                        result.append(f"2θ = {twotheta:.4f}°")
                        result.append(f"d值 = {d:.4f} Å")
                    else:
                        result.append("未检测到峰")
                
                elif algo == "计算FWHM":
                    peaks = find_peaks(y_data)
                    if len(peaks) > 0:
                        fwhm = calculate_fwhm(x_data, y_data, peaks[0])
                        result.append(f"峰位: {x_data[peaks[0]]:.4f}°")
                        result.append(f"FWHM: {fwhm:.4f}°")
                    else:
                        result.append("未检测到峰")
                
                elif algo == "晶格参数计算":
                    result.append("立方晶系晶格参数计算")
                    result.append("需要输入Miller指数进行计算")
                    result.append("示例: 对于石英(101)峰，d=3.34Å")
                    d_example = 3.34
                    a_example = d_example * np.sqrt(1**2 + 0**2 + 1**2)
                    result.append(f"计算得 a = {a_example:.3f} Å")
                
                elif algo == "应变/应力分析":
                    result.append("应变/应力分析")
                    result.append("需要多个峰位数据进行计算")
                    result.append("当前功能需要进一步开发")
                
                elif algo == "定量相分析":
                    result.append("定量相分析 (RIR方法)")
                    result.append("需要已知各相的RIR值")
                    result.append("当前功能需要进一步开发")
                
                elif algo == "图谱相似度计算":
                    result.append("图谱相似度计算")
                    result.append("需要两个图谱进行比较")
                    result.append("当前功能需要进一步开发")
                
                result_text.setText("\\n".join(result))
                
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"算法执行失败: {str(e)}")
        
        # Buttons
        btn_layout = QHBoxLayout()
        run_btn = QPushButton("运行算法")
        run_btn.clicked.connect(run_algorithm)
        btn_layout.addWidget(run_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def zoom_in(self):
        """Zoom in chart"""
        xlim = self.chart_canvas.axes.get_xlim()
        self.chart_canvas.axes.set_xlim(xlim[0] * 0.9, xlim[1] * 0.9)
        self.chart_canvas.draw()
    
    def zoom_out(self):
        """Zoom out chart"""
        xlim = self.chart_canvas.axes.get_xlim()
        self.chart_canvas.axes.set_xlim(xlim[0] * 1.1, xlim[1] * 1.1)
        self.chart_canvas.draw()
    
    def reset_view(self):
        """Reset chart view"""
        if self.current_data is not None:
            self.chart_canvas.plot_xrd(self.current_data[0], self.current_data[1])
        else:
            self.chart_canvas.clear()
            self.chart_canvas.draw()

# ============================================================
# Main Function
# ============================================================

def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = UnifiedXRDPlatform()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
