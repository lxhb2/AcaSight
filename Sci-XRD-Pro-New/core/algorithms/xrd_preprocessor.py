"""
Sci-XRD-Pro - XRD 专业预处理模块
=====================================
基于 JADE 标准流程实现：
  1. Savitzky-Golay 平滑（保峰形）
  2. SNIP 背景扣除（Sonneveld-Visser 迭代剥离）
  3. Rachinger Kα2 剥离
  4. 2θ 角度校准（标样多项式修正）
"""

import numpy as np
from scipy.signal import savgol_filter
from scipy.ndimage import minimum_filter1d
from typing import Tuple, Optional, List


# ─────────────────────────────────────────────
# 1. 平滑
# ─────────────────────────────────────────────

def smooth_savgol(y: np.ndarray, window: int = 11, polyorder: int = 3) -> np.ndarray:
    """
    Savitzky-Golay 卷积平滑（JADE 默认方法）

    原则：
    - window 越大平滑越强，但会宽化峰
    - 推荐 window=11~21，polyorder=3
    - 不改变峰位与积分强度

    Args:
        y: 强度数组
        window: 窗口点数（奇数）
        polyorder: 多项式阶数

    Returns:
        平滑后的强度数组
    """
    if len(y) < window:
        return y.copy()
    if window % 2 == 0:
        window += 1
    window = min(window, len(y) - (1 if len(y) % 2 == 0 else 0))
    if window < polyorder + 2:
        window = polyorder + 3
        if window % 2 == 0:
            window += 1
    return savgol_filter(y, window_length=window, polyorder=polyorder)


# ─────────────────────────────────────────────
# 2. 背景扣除
# ─────────────────────────────────────────────

def background_snip(y: np.ndarray, max_half_window: int = 40,
                    decreasing: bool = True,
                    smooth_half_window: int = 3) -> np.ndarray:
    """
    SNIP 背景估计（Statistics-sensitive Non-linear Iterative Peak-clipping）
    JADE 内置的专业背景扣除算法，适合高荧光、矿物样品。

    算法原理：
    - 从小窗口到大窗口迭代，每步用两侧均值替换当前点（若当前点更高）
    - 最终得到"只含背景"的基线

    Args:
        y: 强度数组
        max_half_window: 最大半窗口（越大背景越平滑）
        decreasing: True=从大到小迭代（更稳定）
        smooth_half_window: 最终平滑半窗口

    Returns:
        背景数组（与 y 等长）
    """
    n = len(y)
    # 对数变换使算法更稳定（SNIP 标准做法）
    y_log = np.log(np.log(np.sqrt(np.maximum(y, 1) + 1) + 1) + 1)
    background = y_log.copy()

    half_windows = range(1, max_half_window + 1)
    if decreasing:
        half_windows = reversed(list(half_windows))

    for hw in half_windows:
        left  = np.roll(background,  hw)
        right = np.roll(background, -hw)
        left[:hw]  = background[:hw]
        right[-hw:] = background[-hw:]
        avg = (left + right) / 2.0
        background = np.minimum(background, avg)

    # 反变换
    bg = (np.exp(np.exp(background) - 1) - 1) ** 2 - 1
    bg = np.maximum(bg, 0)

    # 轻微平滑背景
    if smooth_half_window > 0:
        sw = smooth_half_window * 2 + 1
        if sw < len(bg):
            bg = savgol_filter(bg, sw, 2)

    return bg


def subtract_background(x: np.ndarray, y: np.ndarray,
                         method: str = 'snip',
                         **kwargs) -> Tuple[np.ndarray, np.ndarray]:
    """
    背景扣除统一接口

    Args:
        x: 角度数组
        y: 强度数组
        method: 'snip'（推荐）| 'rubberband' | 'linear'
        **kwargs: 传递给具体算法的参数

    Returns:
        (y_corrected, background)
    """
    if method == 'snip':
        bg = background_snip(y, **kwargs)
    elif method == 'rubberband':
        bg = _rubberband(x, y)
    else:
        bg = np.linspace(y[0], y[-1], len(y))

    y_corr = np.maximum(y - bg, 0)
    return y_corr, bg


def _rubberband(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """橡皮筋法背景（Origin 常用）"""
    from scipy.spatial import ConvexHull
    pts = np.column_stack([x, y])
    try:
        hull = ConvexHull(pts)
        # 取下凸包
        hull_pts = pts[hull.vertices]
        hull_pts = hull_pts[hull_pts[:, 0].argsort()]
        bg = np.interp(x, hull_pts[:, 0], hull_pts[:, 1])
        bg = np.minimum(bg, y)
    except Exception:
        bg = np.linspace(np.min(y), np.min(y), len(y))
    return bg


# ─────────────────────────────────────────────
# 3. Kα2 剥离（Rachinger 算法）
# ─────────────────────────────────────────────

def strip_kalpha2(x: np.ndarray, y: np.ndarray,
                  wavelength_ka1: float = 1.54056,
                  wavelength_ka2: float = 1.54439,
                  ratio: float = 0.5) -> np.ndarray:
    """
    Rachinger Kα2 剥离

    原理：
    - Cu Kα1 (1.54056 Å) 与 Kα2 (1.54439 Å) 强度比约 2:1
    - 对每个 Kα1 峰，在对应 Kα2 位置减去 ratio 倍强度

    Args:
        x: 2θ 角度数组（等步长）
        y: 强度数组
        wavelength_ka1: Kα1 波长 (Å)
        wavelength_ka2: Kα2 波长 (Å)
        ratio: Kα2/Kα1 强度比（默认 0.5）

    Returns:
        剥离 Kα2 后的强度数组
    """
    if len(x) < 2:
        return y.copy()

    step = (x[-1] - x[0]) / (len(x) - 1)
    y_stripped = y.copy().astype(float)

    for i in range(len(x)):
        theta_ka1 = np.radians(x[i] / 2)
        sin_theta = np.sin(theta_ka1)
        if sin_theta <= 0:
            continue

        # Kα2 对应的 2θ
        sin_ka2 = sin_theta * wavelength_ka2 / wavelength_ka1
        if sin_ka2 >= 1:
            continue
        two_theta_ka2 = 2 * np.degrees(np.arcsin(sin_ka2))

        # 找对应索引
        j = int(round((two_theta_ka2 - x[0]) / step))
        if 0 <= j < len(y_stripped):
            y_stripped[j] = max(0, y_stripped[j] - ratio * y_stripped[i])

    return y_stripped


# ─────────────────────────────────────────────
# 4. 角度校准
# ─────────────────────────────────────────────

def calibrate_angles(x: np.ndarray,
                     standard_peaks_measured: List[float],
                     standard_peaks_reference: List[float],
                     degree: int = 2) -> np.ndarray:
    """
    2θ 角度校准（多项式修正）

    使用标样（Si、LaB6、Al2O3 等）的实测峰位与标准峰位，
    拟合多项式修正函数，应用到全谱。

    Args:
        x: 原始 2θ 数组
        standard_peaks_measured: 标样实测峰位列表
        standard_peaks_reference: 标样标准峰位列表
        degree: 多项式阶数（默认 2）

    Returns:
        校准后的 2θ 数组
    """
    if len(standard_peaks_measured) < 2:
        return x.copy()

    measured = np.array(standard_peaks_measured)
    reference = np.array(standard_peaks_reference)
    corrections = reference - measured

    # 多项式拟合修正量
    coeffs = np.polyfit(measured, corrections, min(degree, len(measured) - 1))
    correction_func = np.poly1d(coeffs)

    return x + correction_func(x)


# ─────────────────────────────────────────────
# 5. 完整预处理流水线
# ─────────────────────────────────────────────

class XRDPreprocessor:
    """
    JADE 标准预处理流水线

    使用方法：
        pre = XRDPreprocessor()
        result = pre.process(x, y)
        # result.smoothed, result.background, result.corrected
    """

    def __init__(self,
                 smooth_window: int = 11,
                 smooth_order: int = 3,
                 bg_method: str = 'snip',
                 bg_half_window: int = 40,
                 strip_ka2: bool = True,
                 wavelength: float = 1.5406):
        self.smooth_window  = smooth_window
        self.smooth_order   = smooth_order
        self.bg_method      = bg_method
        self.bg_half_window = bg_half_window
        self.strip_ka2      = strip_ka2
        self.wavelength     = wavelength

        # 结果缓存
        self.original:   Optional[np.ndarray] = None
        self.smoothed:   Optional[np.ndarray] = None
        self.background: Optional[np.ndarray] = None
        self.corrected:  Optional[np.ndarray] = None  # 扣背景后
        self.final:      Optional[np.ndarray] = None  # 剥 Kα2 后

    def process(self, x: np.ndarray, y: np.ndarray,
                calibration: Optional[Tuple[List, List]] = None) -> 'XRDPreprocessor':
        """
        执行完整预处理

        Args:
            x: 2θ 角度数组
            y: 原始强度数组
            calibration: (measured_peaks, reference_peaks) 用于角度校准，None 则跳过

        Returns:
            self（链式调用）
        """
        self.original = y.copy()

        # Step 1: 角度校准
        if calibration is not None:
            x = calibrate_angles(x, calibration[0], calibration[1])

        # Step 2: Savitzky-Golay 平滑
        self.smoothed = smooth_savgol(y, self.smooth_window, self.smooth_order)

        # Step 3: SNIP 背景扣除
        self.corrected, self.background = subtract_background(
            x, self.smoothed,
            method=self.bg_method,
            max_half_window=self.bg_half_window
        )

        # Step 4: Kα2 剥离（可选）
        if self.strip_ka2:
            self.final = strip_kalpha2(x, self.corrected)
        else:
            self.final = self.corrected.copy()

        # 确保非负
        self.final = np.maximum(self.final, 0)

        return self

    def summary(self) -> dict:
        """返回预处理统计信息"""
        if self.original is None:
            return {}
        return {
            'original_max':   float(np.max(self.original)),
            'original_min':   float(np.min(self.original)),
            'background_avg': float(np.mean(self.background)) if self.background is not None else 0,
            'snr_estimate':   float(np.max(self.final) / (np.std(self.final[:20]) + 1))
                              if self.final is not None else 0,
        }
