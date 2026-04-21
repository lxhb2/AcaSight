# Sci-XRD Platform Troubleshooting Guide

## Common Problems and Solutions

### 1. Application Won't Start

#### Symptom:
- Double-clicking batch file does nothing
- Command window flashes and disappears
- Error messages appear briefly

#### Solutions:
**Option A: Run from Command Line**
```bash
cd C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Project
cd scripts
Run-Unified-Platform.bat
```

**Option B: Run Python Directly**
```bash
cd C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Project\src
python xrd_unified_platform.py
```

**Option C: Check Python Installation**
```bash
python --version
# Should show Python 3.8 or higher
```

### 2. Import Errors

#### Symptom:
```
ModuleNotFoundError: No module named 'PyQt6'
ImportError: cannot import name 'smooth_data'
```

#### Solutions:
**Install Missing Packages:**
```bash
pip install PyQt6 numpy pandas matplotlib
```

**If `smooth_data` error occurs:**
The fixed version `xrd_unified_platform.py` includes all necessary functions.
Make sure you're using the file from `src/` folder.

### 3. Garbled Text in Batch Files

#### Symptom:
- Batch file shows strange characters
- Chinese text appears as boxes or question marks

#### Solution:
Use the ASCII-only batch file: `scripts/Run-Unified-Platform.bat`

### 4. GUI Crashes on Startup

#### Symptom:
- Application starts but immediately closes
- Error: `'QLayout' object has no attribute 'insertWidget'`

#### Solution:
This bug has been fixed in the current version.
Make sure you're using `src/xrd_unified_platform.py`.

### 5. Data Import Problems

#### Symptom:
- "Failed to load file" message
- No data appears in chart
- Wrong data displayed

#### Solutions:
**Check File Format:**
- Use CSV format with "2Theta,Intensity" header
- Ensure 2 columns (angle and intensity)
- Remove extra headers or comments

**Sample Format:**
```
2Theta,Intensity
10.00,150
10.05,155
10.10,160
```

**Test with Sample Data:**
Use `data/test_xrd_data.csv` to verify the application works.

### 6. No Peaks Detected

#### Symptom:
- Analysis runs but finds no peaks
- Chart shows no peak markers

#### Solutions:
**Adjust Parameters:**
1. Lower "Peak Height Threshold" (e.g., 0.01%)
2. Lower "Peak Prominence" (e.g., 0.5)
3. Disable background subtraction temporarily

**Check Data Quality:**
- Ensure intensity values are reasonable
- Check for very noisy data
- Try smoothing with larger window

### 7. Phase Identification Issues

#### Symptom:
- No phases matched
- Wrong phases identified

#### Solutions:
**Adjust Tolerance:**
- Increase "Match Tolerance" (e.g., 0.05°)
- The platform uses a simulated database

**For Real Database:**
Install the full PDF2 database module if available.

### 8. Performance Issues

#### Symptom:
- Slow analysis
- Application freezes
- High memory usage

#### Solutions:
**Reduce Data Size:**
- Use fewer data points
- Skip unnecessary preprocessing steps

**Adjust Settings:**
- Disable Kα2 stripping
- Use smaller smoothing window
- Disable real-time updates during analysis

### 9. Export Problems

#### Symptom:
- Can't save results
- Exported files are empty
- Wrong format exported

#### Solutions:
**Check Permissions:**
- Ensure write permission to target folder
- Try saving to Desktop or Documents folder

**Choose Correct Format:**
- JSON: Complete results
- CSV: Tabular data for Excel
- TXT: Readable report

### 10. Chart Display Issues

#### Symptom:
- Chart doesn't update
- Wrong axis labels
- No grid or labels

#### Solutions:
**Reset View:**
Click "Reset View" button in chart controls.

**Check Data:**
Ensure data has been properly loaded and analyzed.

## Diagnostic Steps

### Step 1: Check Environment
```bash
python --version
pip list | findstr PyQt
```

### Step 2: Test Core Functions
```bash
cd src
python -c "
import xrd_unified_platform
import numpy as np
y = np.array([1, 2, 3, 2, 1])
print('Smooth test:', xrd_unified_platform.smooth_data(y, 3))
print('Peak test:', xrd_unified_platform.find_peaks(y))
print('All functions work!')
"
```

### Step 3: Run Minimal Test
```bash
cd src
python -c "
from PyQt6.QtWidgets import QApplication
import sys
import xrd_unified_platform

app = QApplication(sys.argv)
window = xrd_unified_platform.UnifiedXRDPlatform()
print('Application created successfully')
window.show()
print('Ready to run')
# Don't actually run app.exec() in test
"
```

### Step 4: Test Data Import
```bash
cd src
python -c "
import xrd_unified_platform
import numpy as np

# Create test file
test_data = '''2Theta,Intensity
10.0,100
10.1,150
10.2,200
10.3,150
10.4,100'''
with open('test_import.csv', 'w') as f:
    f.write(test_data)

# Test import
x, y = xrd_unified_platform.read_xrd_data('test_import.csv')
print(f'Import successful: {len(x)} points')
import os
os.remove('test_import.csv')
"
```

## Getting Help

### If Problems Persist:

1. **Take Screenshot** of the error message
2. **Note the Steps** that caused the error
3. **Check Python Version**: `python --version`
4. **Check File Locations**:
   - Main program: `src/xrd_unified_platform.py`
   - Launch script: `scripts/Run-Unified-Platform.bat`
   - Test data: `data/test_xrd_data.csv`

### Common Error Messages:

| Error | Cause | Solution |
|-------|-------|----------|
| `AttributeError: 'QLayout' object has no attribute 'insertWidget'` | PyQt6 compatibility issue | Use the fixed version in `src/` |
| `NameError: name 'smooth_data' is not defined` | Missing function import | Use the self-contained version |
| `ModuleNotFoundError: No module named 'PyQt6'` | Missing dependency | `pip install PyQt6` |
| `UnicodeDecodeError` | File encoding issue | Save data as UTF-8 or ASCII |
| `ValueError: could not convert string to float` | Data format error | Check CSV file format |

## Quick Fix Checklist

1. [ ] Python 3.8+ installed
2. [ ] Dependencies installed: `pip install PyQt6 numpy pandas matplotlib`
3. [ ] Using `src/xrd_unified_platform.py` (fixed version)
4. [ ] Using `scripts/Run-Unified-Platform.bat` (ASCII version)
5. [ ] Test data `data/test_xrd_data.csv` loads correctly
6. [ ] Running from correct directory

## Emergency Solutions

### If Nothing Works:

**Option A: Clean Reinstall**
```bash
# 1. Install fresh Python
# 2. Install dependencies
pip install PyQt6 numpy pandas matplotlib
# 3. Copy only these files:
#    - src/xrd_unified_platform.py
#    - scripts/Run-Unified-Platform.bat
#    - data/test_xrd_data.csv
```

**Option B: Use Minimal Version**
A simplified version without advanced features may work.

**Option C: Web Interface Alternative**
Check if the web interface works: `web_interface/app.py`

---

**Remember:** The platform has been tested and fixed. Most issues can be resolved by:
1. Using the correct files from the `Sci-XRD-Project` folder
2. Installing required dependencies
3. Running from command line to see error messages

Good luck with your XRD analysis!