# Sci-XRD Unified Analysis Platform

## Overview
All-in-one XRD analysis tool with integrated interface for material science research.

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Required packages: PyQt6, numpy, pandas, matplotlib

### Installation
1. Install Python from [python.org](https://www.python.org/downloads/)
2. Install required packages:
   ```bash
   pip install PyQt6 numpy pandas matplotlib
   ```

### Running the Platform

#### Option 1: Run batch script (Windows)
```bash
cd scripts
Run-Unified-Platform.bat
```

#### Option 2: Run directly with Python
```bash
cd src
python xrd_unified_platform.py
```

## Project Structure
```
Sci-XRD-Project/
├── src/                    # Source code
│   └── xrd_unified_platform.py  # Main application
├── docs/                   # Documentation
│   ├── 一体化平台使用指南.md    # User guide (Chinese)
│   └── Sci-XRD一体化平台完成报告.md  # Project report
├── data/                   # Test data
│   └── test_xrd_data.csv   # Sample XRD data
├── scripts/                # Batch scripts
│   └── Run-Unified-Platform.bat  # Launch script
├── reports/                # Analysis reports
└── tests/                  # Test files
│   └── test_new_algorithms.py   # New algorithm tests
```

## Features

### 1. Data Import
- Supports multiple formats: .txt, .csv, .dat, .xy, .xrd
- Automatic format detection
- Drag-and-drop support

### 2. Preprocessing
- Smoothing (moving average)
- Background subtraction (SNIP algorithm)
- Kα2 stripping (for Cu radiation)

### 3. Analysis
- Peak detection with configurable thresholds
- Phase identification using PDF2 database
- Quantitative analysis
- Crystallite size calculation (Scherrer formula)

### 4. Advanced Algorithms (NEW!)
- **K-alpha2 Stripping**: Remove Cu K-alpha2 radiation contribution
- **Peak Fitting**: Gaussian, Lorentzian, and Pseudo-Voigt functions
- **d-spacing Calculation**: From 2-theta angles using Bragg's law
- **FWHM Calculation**: Full width at half maximum
- **Lattice Parameter Refinement**: For cubic crystal systems
- **Strain/Stress Analysis**: Microstrain calculation from peak shifts
- **Quantitative Phase Analysis**: RIR (Reference Intensity Ratio) method
- **Pattern Similarity**: Compare XRD patterns using correlation

### 5. Visualization
- Real-time XRD pattern display
- Interactive zoom and pan
- Peak markers and labels
- Professional chart styling

### 6. Advanced Algorithms Dialog
Click "高级算法" (Advanced Algorithms) button to access:
- **K-alpha2 Stripping**: Rachinger method for Cu radiation
- **Gaussian Fit**: Peak fitting with Gaussian function
- **Lorentzian Fit**: Peak fitting with Lorentzian function
- **Pseudo-Voigt Fit**: Mixed Gaussian-Lorentzian fitting
- **d-spacing**: Calculate interplanar spacing
- **FWHM**: Measure peak broadening
- **Lattice Parameter**: Calculate unit cell parameters
- **Strain Analysis**: Microstrain from peak shifts
- **Quantitative Analysis**: Phase weight percentages
- **Similarity**: Pattern correlation analysis

### 7. Export
- JSON format (complete analysis results)
- CSV format (tabular data)
- TXT format (human-readable report)
- Chart images (PNG)
- Algorithm results (peak fitting parameters, lattice constants, etc.)

## Troubleshooting

### Common Issues

#### Issue 1: "Module not found" errors
```bash
# Install missing packages
pip install PyQt6 numpy pandas matplotlib
```

#### Issue 2: Batch file shows garbled text
- Use `Run-Unified-Platform.bat` (ASCII version)
- Or run directly: `python src/xrd_unified_platform.py`

#### Issue 3: Application crashes on startup
- Check Python version: `python --version`
- Reinstall dependencies: `pip install --upgrade PyQt6 numpy pandas matplotlib`
- Run from command line to see error messages

#### Issue 4: Data import fails
- Ensure file format is correct (2 columns: angle and intensity)
- Try CSV format first
- Check file encoding (UTF-8 recommended)

#### Issue 5: No peaks detected
- Adjust peak detection parameters:
  - Increase "Peak Height Threshold"
  - Decrease "Peak Prominence"
  - Enable background subtraction

### Error Messages and Solutions

| Error Message | Solution |
|--------------|----------|
| `smooth_data is not defined` | Use the provided `xrd_unified_platform.py` file (all functions are built-in) |
| `PyQt6 module not found` | Run: `pip install PyQt6` |
| `No such file or directory` | Check file path and permissions |
| `Invalid data format` | Use CSV format with "2Theta,Intensity" header |
| `Application freezes during analysis` | Reduce data size or increase timeout in settings |

## Advanced Usage

### Batch Processing
1. Create a folder with multiple XRD files
2. Use the batch processing feature
3. Results are saved in `reports/` folder

### Custom Analysis Parameters
- Peak detection: Adjust height threshold and prominence
- Phase matching: Set tolerance for d-value matching
- Quantitative analysis: Choose calibration method

### Export Options
- **JSON**: Complete data structure for programmatic use
- **CSV**: Tabular data for Excel/SPSS
- **TXT**: Readable report for documentation
- **PNG**: High-resolution chart images

## Development

### Adding New Features
1. Edit `src/xrd_unified_platform.py`
2. Test with sample data
3. Update documentation

### Testing
```bash
cd tests
python test_xrd_analysis.py
```

### Building Executable
```bash
pyinstaller --onefile --windowed src/xrd_unified_platform.py
```

## Support

### Documentation
- User Guide: `docs/一体化平台使用指南.md`
- Project Report: `docs/Sci-XRD一体化平台完成报告.md`

### Getting Help
1. Check the troubleshooting section above
2. Review the user guide
3. Run with command line to see error messages

### Reporting Issues
Include:
1. Error message or screenshot
2. Steps to reproduce
3. Python version: `python --version`
4. Package versions: `pip list`

## License
This project is for academic and research use.

## Acknowledgements
- PDF2 database for phase identification
- PyQt6 for GUI framework
- Matplotlib for visualization

---

**Start analyzing your XRD data with the unified platform today!**