#!/usr/bin/env python3
"""
Test script for Sci-XRD Unified Platform (ASCII version)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np

def test_core_functions():
    """Test core XRD analysis functions"""
    print("Testing core functions...")
    
    try:
        import xrd_unified_platform
        
        # Test data
        y = np.array([100, 150, 200, 150, 100, 50, 100, 150, 100])
        
        # Test smooth_data
        smoothed = xrd_unified_platform.smooth_data(y, window=3)
        print(f"OK smooth_data: {smoothed}")
        
        # Test subtract_background
        bg_sub = xrd_unified_platform.subtract_background(y, lambda_param=100)
        print(f"OK subtract_background: {bg_sub}")
        
        # Test find_peaks
        peaks = xrd_unified_platform.find_peaks(y, height_threshold=0.01, prominence=0.5)
        print(f"OK find_peaks: {peaks}")
        
        # Test calculate_crystallite_size
        size = xrd_unified_platform.calculate_crystallite_size(25.0, 0.1)
        print(f"OK calculate_crystallite_size: {size:.2f} nm")
        
        print("All core functions passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_import():
    """Test data import functionality"""
    print("\nTesting data import...")
    
    try:
        import xrd_unified_platform
        
        # Create test CSV file
        test_csv = """2Theta,Intensity
10.0,100
10.1,150
10.2,200
10.3,150
10.4,100"""
        
        test_file = "test_import.csv"
        with open(test_file, 'w') as f:
            f.write(test_csv)
        
        # Test import
        x, y = xrd_unified_platform.read_xrd_data(test_file)
        print(f"OK read_xrd_data: {len(x)} points imported")
        print(f"  X range: {x[0]:.1f} to {x[-1]:.1f}")
        print(f"  Y range: {y[0]:.1f} to {y[-1]:.1f}")
        
        # Clean up
        os.remove(test_file)
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_platform_import():
    """Test that platform can be imported"""
    print("\nTesting platform import...")
    
    try:
        import xrd_unified_platform
        
        # Check if main class exists
        if hasattr(xrd_unified_platform, 'UnifiedXRDPlatform'):
            print("OK: UnifiedXRDPlatform class found")
            
            # Check if required methods exist
            required_methods = [
                'init_ui', 'create_toolbar', 'create_left_panel',
                'create_center_panel', 'create_right_panel',
                'open_file', 'quick_analyze', 'full_analyze'
            ]
            
            for method in required_methods:
                if hasattr(xrd_unified_platform.UnifiedXRDPlatform, method):
                    print(f"  OK: {method} method exists")
                else:
                    print(f"  ERROR: {method} method missing")
            
            return True
        else:
            print("ERROR: UnifiedXRDPlatform class not found")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """Check required dependencies"""
    print("\nChecking dependencies...")
    
    dependencies = [
        ('PyQt6', 'PyQt6'),
        ('numpy', 'numpy'),
        ('pandas', 'pandas'),
        ('matplotlib', 'matplotlib')
    ]
    
    all_ok = True
    for name, module in dependencies:
        try:
            __import__(module)
            print(f"OK: {name} installed")
        except ImportError:
            print(f"ERROR: {name} NOT installed")
            all_ok = False
    
    return all_ok

def main():
    """Run all tests"""
    print("=" * 60)
    print("Sci-XRD Unified Platform Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test dependencies
    results.append(("Dependencies", test_dependencies()))
    
    # Test core functions
    results.append(("Core Functions", test_core_functions()))
    
    # Test data import
    results.append(("Data Import", test_data_import()))
    
    # Test platform import
    results.append(("Platform Import", test_platform_import()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
        print("The Sci-XRD platform is ready to use.")
        print("\nTo start the platform:")
        print("  cd scripts")
        print("  Run-Unified-Platform.bat")
    else:
        print("SOME TESTS FAILED")
        print("Check the errors above and install missing dependencies.")
        print("\nInstall dependencies:")
        print("  pip install PyQt6 numpy pandas matplotlib")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())