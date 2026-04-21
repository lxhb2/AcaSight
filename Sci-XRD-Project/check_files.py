#!/usr/bin/env python3
"""
Check if all required files exist
"""

import os
import sys

def main():
    print("Checking required files...")
    print("=" * 50)
    
    files = [
        ('src/xrd_unified_platform.py', 'Main program'),
        ('Start-XRD-Platform.bat', 'Launch script'),
        ('data/test_xrd_data.csv', 'Test data'),
        ('scripts/Run-Unified-Platform.bat', 'Legacy script'),
        ('README.md', 'Documentation')
    ]
    
    all_exist = True
    for file_path, description in files:
        if os.path.exists(file_path):
            print(f"[OK] {description}: {file_path}")
        else:
            print(f"[MISSING] {description}: {file_path}")
            all_exist = False
    
    print("\n" + "=" * 50)
    print("Testing main program import...")
    try:
        sys.path.insert(0, 'src')
        import xrd_unified_platform
        print("[OK] Main program imports successfully")
        
        # Check if main class exists
        if hasattr(xrd_unified_platform, 'UnifiedXRDPlatform'):
            print("[OK] UnifiedXRDPlatform class found")
        else:
            print("[ERROR] UnifiedXRDPlatform class not found")
            all_exist = False
            
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        all_exist = False
    
    print("\n" + "=" * 50)
    if all_exist:
        print("SUCCESS: All checks passed!")
        print("\nTo start the platform:")
        print("  Option 1: Double-click 'Start-XRD-Platform.bat'")
        print("  Option 2: Run 'scripts/Run-Unified-Platform.bat'")
        print("  Option 3: Run 'python src/xrd_unified_platform.py'")
        return 0
    else:
        print("FAILURE: Some checks failed.")
        print("Please make sure all files are in the correct locations.")
        return 1

if __name__ == "__main__":
    sys.exit(main())