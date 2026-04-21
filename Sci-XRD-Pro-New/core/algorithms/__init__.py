"""
Sci-XRD-Pro - 算法模块导出
===========================

核心算法：
  - peak_detection: 峰检测（JADE二阶导数法 + 伪Voigt拟合）
  - phase_matching: 物相匹配（FOM/HANAWALT/WPF）
  - phase_matching_v2: 高精准度物相匹配
  - xrd_preprocessor: 预处理（平滑/背景/Kα2剥离）
  - microstructure: 微观结构分析（Williamson-Hall/Scherrer）
  - rietveld: Le Bail / Rietveld 精修
  - element_constrained_search: 元素限定检索
  - enhanced_profile: 增强峰形拟合（不对称/FCJ校正）
  - whole_pattern_fit: 全谱拟合匹配(WPF)
  - advanced_analysis: 高级分析（FOM/导数峰检测/拟合/晶格参数）
"""

from core.algorithms.peak_detection import (
    Peak,
    JadePeakDetector,
    PeakDetector,
    detect_peaks
)

from core.algorithms.phase_matching import (
    Phase,
    MatchResult,
    JadePhaseMatcher
)

from core.algorithms.phase_matching_v2 import (
    HighAccuracyPhaseMatcher,
    match_with_high_accuracy
)

from core.algorithms.xrd_preprocessor import (
    XRDPreprocessor,
    smooth_savgol,
    background_snip,
    subtract_background,
    strip_kalpha2,
    calibrate_angles
)

from core.algorithms.microstructure import (
    MicrostructureResult,
    WilliamsonHall,
    ScherrerAnalysis,
    CrystallinityAnalyzer,
    analyze_microstructure
)

from core.algorithms.rietveld import (
    CellParameters,
    RefinementResult,
    LeBail,
    RietveldRefinement,
    le_bail_refine,
    rietveld_refine
)

Rietveld = RietveldRefinement

from core.algorithms.element_constrained_search import (
    ElementInfo,
    ElementConstraintResult,
    ElementExtractor,
    ElementConstraintSearch,
    ElementConstrainedMatcher,
    extract_elements_from_formula,
    calculate_formula_weight,
    check_element_compatibility
)

from core.algorithms.enhanced_profile import (
    ProfileParams,
    PeakProfileFunctions,
    AsymmetryCorrection,
    FCJCorrection,
    EnhancedPeakFitter,
    fit_peak
)

from core.algorithms.whole_pattern_fit import (
    WPFResult,
    WholePatternFitting,
    DirectDerivationMethod,
    WPFMatcher,
    wpf_match,
    ddm_quantify
)

from core.algorithms.advanced_analysis import (
    Peak,
    MatchResult,
    XRDAnalyzer,
    derivative_peak_detection,
    calculate_fom,
    pattern_similarity,
    scherrer_crystallite_size,
    scherrer_analysis,
    hanawalt_search,
    gaussian_fit,
    lorentzian_fit,
    pseudo_voigt_fit,
    strip_k_alpha2,
    calculate_lattice_parameter,
    d_to_twotheta,
    twotheta_to_d
)

from core.algorithms.task_manager import (
    TaskManager,
    TaskState,
    TaskResult,
    AsyncTask,
    ProgressTracker,
    ProgressCallback,
    get_task_manager,
    submit_task,
    cancel_task,
    create_progress_callback
)

__all__ = [
    # Peak Detection
    'Peak',
    'JadePeakDetector',
    'PeakDetector',
    'detect_peaks',

    # Phase Matching
    'Phase',
    'MatchResult',
    'JadePhaseMatcher',
    'HighAccuracyPhaseMatcher',
    'match_with_high_accuracy',

    # Preprocessing
    'XRDPreprocessor',
    'smooth_savgol',
    'background_snip',
    'subtract_background',
    'strip_kalpha2',
    'calibrate_angles',

    # Microstructure
    'MicrostructureResult',
    'WilliamsonHall',
    'ScherrerAnalysis',
    'CrystallinityAnalyzer',
    'analyze_microstructure',

    # Rietveld
    'CellParameters',
    'RefinementResult',
    'LeBail',
    'Rietveld',
    'le_bail_refine',
    'rietveld_refine',

    # Element Constrained Search
    'ElementInfo',
    'ElementConstraintResult',
    'ElementExtractor',
    'ElementConstraintSearch',
    'ElementConstrainedMatcher',
    'extract_elements_from_formula',
    'calculate_formula_weight',
    'check_element_compatibility',

    # Enhanced Profile
    'ProfileParams',
    'PeakProfileFunctions',
    'AsymmetryCorrection',
    'FCJCorrection',
    'EnhancedPeakFitter',
    'fit_peak',

    # Whole Pattern Fitting
    'WPFResult',
    'WholePatternFitting',
    'DirectDerivationMethod',
    'WPFMatcher',
    'wpf_match',
    'ddm_quantify',

    # Task Manager
    'TaskManager',
    'TaskState',
    'TaskResult',
    'AsyncTask',
    'ProgressTracker',
    'ProgressCallback',
    'get_task_manager',
    'submit_task',
    'cancel_task',
    'create_progress_callback',
]
