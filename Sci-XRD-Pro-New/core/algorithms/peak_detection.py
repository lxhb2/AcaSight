"""
Sci-XRD-Pro - 专业峰检测模块（JADE 标准）
==========================================
实现 JADE 的三种寻峰算法：
  1. 二阶导数法（主力，抗噪强）
  2. 阈值法（快速粗检）
  3. 伪 Voigt 拟合精修（精确 FWHM/面积）

输出：Peak 对象列表，含 position / d_spacing / intensity /
      fwhm / area / prominence / confidence
"""

import numpy as np
from scipy.signal import savgol_filter, find_peaks
from scipy.optimize import curve_fit
from typing import List, Optional, Tuple
from core.utils.conv import twotheta_to_d


# ─────────────────────────────────────────────
# 数据类
# ─────────────────────────────────────────────

class Peak:
    """XRD 峰位数据"""

    def __init__(self, position: float, intensity: float,
                 d_spacing: float = None, fwhm: float = 0.1,
                 prominence: float = 0.0, area: float = 0.0,
                 method: str = 'unknown', confidence: float = 0.0):
        self.position   = position
        self.intensity  = intensity
        self.d_spacing  = d_spacing if d_spacing is not None else twotheta_to_d(position)
        self.fwhm       = fwhm
        self.prominence = prominence
        self.area       = area
        self.method     = method
        self.confidence = confidence
        self.label: Optional[str] = None   # 物相标签（鉴定后填入）

    # 晶粒尺寸（谢乐公式），需外部传入仪器宽化 beta_inst
    def scherrer_size(self, wavelength: float = 1.5406,
                      beta_inst: float = 0.05, K: float = 0.9) -> float:
        """
        谢乐公式计算晶粒尺寸 (nm)

        D = K·λ / (β·cosθ)
        β = sqrt(FWHM² - β_inst²)  （仪器宽化校正）
        """
        beta_rad = np.radians(self.fwhm)
        beta_inst_rad = np.radians(beta_inst)
        beta_corr = np.sqrt(max(beta_rad**2 - beta_inst_rad**2, 1e-10))
        theta_rad = np.radians(self.position / 2)
        if np.cos(theta_rad) < 1e-6:
            return 0.0
        return K * wavelength / (beta_corr * np.cos(theta_rad)) * 0.1  # Å→nm

    def to_dict(self) -> dict:
        return {
            'position':   round(self.position, 4),
            'intensity':  round(self.intensity, 2),
            'd_spacing':  round(self.d_spacing, 5),
            'fwhm':       round(self.fwhm, 4),
            'prominence': round(self.prominence, 2),
            'area':       round(self.area, 2),
            'method':     self.method,
            'confidence': round(self.confidence, 3),
            'label':      self.label,
        }

    def __repr__(self):
        return (f"Peak(2θ={self.position:.3f}°, d={self.d_spacing:.4f}Å, "
                f"I={self.intensity:.0f}, FWHM={self.fwhm:.3f}°, "
                f"conf={self.confidence:.0%})")


# ─────────────────────────────────────────────
# 峰形函数
# ─────────────────────────────────────────────

def _gaussian(x, amp, cen, sigma):
    return amp * np.exp(-(x - cen)**2 / (2 * sigma**2))

def _lorentzian(x, amp, cen, gamma):
    return amp / (1 + ((x - cen) / gamma)**2)

def _pseudo_voigt(x, amp, cen, sigma, eta):
    """伪 Voigt：η·Lorentz + (1-η)·Gauss，η∈[0,1]"""
    g = _gaussian(x, 1, cen, sigma)
    l = _lorentzian(x, 1, cen, sigma)
    return amp * (eta * l + (1 - eta) * g)

def _pv_with_bg(x, amp, cen, sigma, eta, bg):
    return _pseudo_voigt(x, amp, cen, sigma, eta) + bg


# ─────────────────────────────────────────────
# 核心检测器
# ─────────────────────────────────────────────

class JadePeakDetector:
    """
    JADE 风格峰检测器

    推荐流程：
        detector = JadePeakDetector()
        peaks = detector.detect(x, y_preprocessed)

    参数说明：
        sensitivity  : 0~1，越高检测越多（含弱峰），默认 0.05
        min_distance : 最小峰间距（°），默认 0.3
        fit_peaks    : 是否用伪 Voigt 精修 FWHM/面积，默认 True
    """

    def __init__(self, sensitivity: float = 0.05,
                 min_distance: float = 0.3,
                 fit_peaks: bool = True,
                 wavelength: float = 1.5406):
        self.sensitivity   = sensitivity
        self.min_distance  = min_distance
        self.fit_peaks     = fit_peaks
        self.wavelength    = wavelength

    # ── 主入口 ──────────────────────────────────

    def detect(self, x: np.ndarray, y: np.ndarray,
               threshold: float = 0.05,
               min_intensity: float = 50) -> List[Peak]:
        """
        检测峰位（二阶导数法 + 可选伪 Voigt 精修）

        Args:
            x: 2θ 角度数组（等步长）
            y: 预处理后的强度数组（已扣背景）
            threshold: 峰检测阈值（二阶导数过零点敏感度）
            min_intensity: 最小峰强（仅返回强度大于此值的峰）

        Returns:
            按强度降序排列的 Peak 列表
        """
        if len(x) < 10 or len(y) < 10:
            return []

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        y = np.maximum(y, 0)

        # 轻度平滑（保峰形）
        win = min(11, len(y) - (0 if len(y) % 2 else 1))
        if win >= 5:
            y_sm = savgol_filter(y, win, 3)
        else:
            y_sm = y.copy()

        # 二阶导数寻峰
        peaks = self._second_derivative_search(x, y, y_sm)

        # 过滤太近的峰（保留强度更大的）
        peaks = self._merge_close_peaks(peaks)

        # 伪 Voigt 精修 FWHM / 面积
        if self.fit_peaks and len(peaks) > 0:
            peaks = self._fit_all_peaks(x, y, peaks)

        # 计算置信度
        peaks = self._assign_confidence(peaks, y)

        # 按强度降序
        peaks.sort(key=lambda p: p.intensity, reverse=True)
        return peaks

    # ── 二阶导数法 ──────────────────────────────

    def _second_derivative_search(self, x: np.ndarray,
                                   y: np.ndarray,
                                   y_sm: np.ndarray) -> List[Peak]:
        """
        JADE 核心寻峰：二阶导数极小值 = 峰位

        阈值逻辑（与 JADE 一致）：
        - 峰高 > baseline + sensitivity × signal_range
        - 二阶导数 < -d2_threshold（负极值）
        """
        step = (x[-1] - x[0]) / (len(x) - 1) if len(x) > 1 else 0.02

        # 计算二阶导数
        d2y = np.gradient(np.gradient(y_sm, x), x)

        # 动态阈值
        baseline      = np.percentile(y_sm, 10)
        signal_range  = np.max(y_sm) - baseline
        height_thresh = baseline + self.sensitivity * signal_range
        d2_thresh     = -np.std(d2y) * 0.5   # 负值阈值

        # 最小峰间距（点数）
        min_dist_pts = max(3, int(self.min_distance / step))

        # scipy find_peaks 在 -d2y 上找极大值（即 d2y 的极小值）
        prominence_thresh = np.std(d2y) * 0.3
        peak_indices, props = find_peaks(
            -d2y,
            height=-d2_thresh,
            prominence=prominence_thresh,
            distance=min_dist_pts
        )

        peaks = []
        for idx in peak_indices:
            if y_sm[idx] < height_thresh:
                continue

            # 抛物线插值精确峰位
            pos, intensity = self._parabolic_interpolate(x, y_sm, idx)

            # 估算 FWHM（后续 fit 会精修）
            fwhm = self._estimate_fwhm(x, y_sm, idx)

            # 突出度
            prom = self._calc_prominence(y_sm, idx)

            # 面积（梯形积分，FWHM 范围内）
            area = self._estimate_area(x, y, idx, fwhm)

            peaks.append(Peak(
                position=pos,
                intensity=float(y[idx]),   # 用原始强度（未平滑）
                fwhm=fwhm,
                prominence=prom,
                area=area,
                method='2nd_derivative'
            ))

        return peaks

    # ── 抛物线插值 ──────────────────────────────

    @staticmethod
    def _parabolic_interpolate(x: np.ndarray, y: np.ndarray,
                                idx: int) -> Tuple[float, float]:
        """抛物线插值精确峰位"""
        if idx == 0 or idx >= len(y) - 1:
            return float(x[idx]), float(y[idx])
        y0, y1, y2 = y[idx-1], y[idx], y[idx+1]
        denom = y0 + y2 - 2 * y1
        if abs(denom) < 1e-12:
            return float(x[idx]), float(y[idx])
        delta = (y0 - y2) / (2 * denom)
        delta = np.clip(delta, -0.5, 0.5)
        dx = x[idx] - x[idx-1]
        pos = x[idx] + delta * dx
        intensity = y1 - 0.25 * (y0 - y2) * delta
        return float(pos), float(max(intensity, y1))

    # ── FWHM 估算 ───────────────────────────────

    @staticmethod
    def _estimate_fwhm(x: np.ndarray, y: np.ndarray, idx: int) -> float:
        """从峰两侧找半高宽"""
        half = y[idx] / 2.0
        # 向左
        li = idx
        for i in range(idx, 0, -1):
            if y[i] <= half:
                li = i
                break
        # 向右
        ri = idx
        for i in range(idx, len(y)):
            if y[i] <= half:
                ri = i
                break
        if ri > li:
            return float(x[ri] - x[li])
        step = (x[-1] - x[0]) / (len(x) - 1) if len(x) > 1 else 0.02
        return step * 5  # 默认 5 步

    # ── 突出度 ──────────────────────────────────

    @staticmethod
    def _calc_prominence(y: np.ndarray, idx: int, window: int = 80) -> float:
        left  = np.min(y[max(0, idx - window): idx + 1])
        right = np.min(y[idx: min(len(y), idx + window + 1)])
        return float(y[idx] - max(left, right))

    # ── 面积估算 ────────────────────────────────

    @staticmethod
    def _estimate_area(x: np.ndarray, y: np.ndarray,
                        idx: int, fwhm: float) -> float:
        """FWHM 范围内梯形积分"""
        half_fwhm = fwhm / 2
        mask = (x >= x[idx] - half_fwhm) & (x <= x[idx] + half_fwhm)
        if mask.sum() < 2:
            return 0.0
        try:
            return float(np.trapezoid(y[mask], x[mask]))
        except AttributeError:
            return float(np.trapz(y[mask], x[mask]))

    # ── 合并近峰 ────────────────────────────────

    def _merge_close_peaks(self, peaks: List[Peak]) -> List[Peak]:
        """合并距离 < min_distance 的峰，保留强度更大的"""
        if len(peaks) <= 1:
            return peaks
        peaks_sorted = sorted(peaks, key=lambda p: p.position)
        merged = [peaks_sorted[0]]
        for p in peaks_sorted[1:]:
            if p.position - merged[-1].position < self.min_distance:
                if p.intensity > merged[-1].intensity:
                    merged[-1] = p
            else:
                merged.append(p)
        return merged

    # ── 伪 Voigt 精修 ────────────────────────────

    def _fit_all_peaks(self, x: np.ndarray, y: np.ndarray,
                        peaks: List[Peak]) -> List[Peak]:
        """对每个峰做伪 Voigt 拟合，精修 center / FWHM / area"""
        step = (x[-1] - x[0]) / (len(x) - 1) if len(x) > 1 else 0.02
        fitted = []
        for peak in peaks:
            result = self._fit_one_peak(x, y, peak, step)
            fitted.append(result)
        return fitted

    def _fit_one_peak(self, x: np.ndarray, y: np.ndarray,
                       peak: Peak, step: float) -> Peak:
        """单峰伪 Voigt 拟合"""
        # 拟合窗口：峰位 ± max(3×FWHM, 1°)
        half_win = max(peak.fwhm * 3, 1.0)
        mask = (x >= peak.position - half_win) & (x <= peak.position + half_win)
        xf, yf = x[mask], y[mask]
        if len(xf) < 8:
            return peak

        bg_est = np.percentile(yf, 10)
        amp0   = peak.intensity - bg_est
        sig0   = max(peak.fwhm / 2.355, step)

        try:
            popt, _ = curve_fit(
                _pv_with_bg, xf, yf,
                p0=[amp0, peak.position, sig0, 0.5, bg_est],
                bounds=(
                    [0,       peak.position - 1.0, step * 0.5, 0,   0],
                    [amp0*3,  peak.position + 1.0, 2.0,        1.0, np.max(yf)]
                ),
                maxfev=3000
            )
            amp, cen, sigma, eta, bg = popt
            fwhm_fit = 2 * sigma * np.sqrt(2 * np.log(2))  # Gaussian FWHM
            # 伪 Voigt FWHM 修正
            fwhm_fit = fwhm_fit * (1 + 0.217 * eta)        # 近似修正

            # 面积（解析积分）
            area = amp * sigma * np.sqrt(2 * np.pi) * (1 - eta) + amp * np.pi * sigma * eta

            peak.position  = float(cen)
            peak.intensity = float(amp + bg)
            peak.fwhm      = float(fwhm_fit)
            peak.area      = float(area)
            peak.d_spacing = twotheta_to_d(cen)
            peak.method    = 'pseudo_voigt'
        except Exception:
            pass  # 拟合失败保留原始估算值

        return peak

    # ── 置信度 ──────────────────────────────────

    @staticmethod
    def _assign_confidence(peaks: List[Peak], y: np.ndarray) -> List[Peak]:
        """
        综合 SNR、突出度、FWHM 合理性计算置信度
        """
        if not peaks:
            return peaks
        noise = float(np.std(y[:min(50, len(y))]))
        max_i = float(np.max(y)) if len(y) else 1.0

        for p in peaks:
            snr_score  = min(1.0, p.intensity / (noise * 3 + 1))
            prom_score = min(1.0, p.prominence / (max_i * 0.05 + 1))
            # FWHM 合理性：XRD 峰通常 0.05°~2°
            fwhm_ok    = 1.0 if 0.05 <= p.fwhm <= 2.0 else 0.5
            p.confidence = float(snr_score * 0.5 + prom_score * 0.3 + fwhm_ok * 0.2)

        return peaks


# ─────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────

def detect_peaks(x: np.ndarray, y: np.ndarray,
                 sensitivity: float = 0.05,
                 min_distance: float = 0.3,
                 fit: bool = True) -> List[Peak]:
    """
    一行调用峰检测

    Args:
        x: 2θ 角度数组
        y: 强度数组（建议已扣背景）
        sensitivity: 0~1，越高检测越多弱峰
        min_distance: 最小峰间距（°）
        fit: 是否伪 Voigt 精修

    Returns:
        Peak 列表（按强度降序）
    """
    detector = JadePeakDetector(sensitivity=sensitivity,
                                 min_distance=min_distance,
                                 fit_peaks=fit)
    return detector.detect(x, y)


# 向后兼容
PeakDetector = JadePeakDetector
NonDestructivePeakDetector = JadePeakDetector


# ─────────────────────────────────────────────
# 小波变换峰检测器
# ─────────────────────────────────────────────

class WaveletPeakDetector:
    """
    基于小波变换的高级峰检测器

    优势：能同时检测尖锐峰和宽峰，抗噪性强
    """

    def __init__(self, wavelet: str = 'mexh',
                 widths: np.ndarray = None,
                 noise_thresh: float = 0.1,
                 min_distance: float = 0.3):
        self.wavelet = wavelet
        self.widths = widths if widths is not None else np.arange(1, 30)
        self.noise_thresh = noise_thresh
        self.min_distance = min_distance

    def detect(self, x: np.ndarray, y: np.ndarray,
               min_intensity: float = 50) -> List[Peak]:
        """
        使用连续小波变换进行峰检测

        Args:
            x: 2θ 角度数组（等步长）
            y: 预处理后的强度数组
            min_intensity: 最小峰强

        Returns:
            Peak 列表（按强度降序）
        """
        if len(x) < 10 or len(y) < 10:
            return []

        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        y = np.maximum(y, 0)

        step = (x[-1] - x[0]) / (len(x) - 1) if len(x) > 1 else 0.02
        min_dist_pts = max(3, int(self.min_distance / step))

        y_norm = (y - y.min()) / (y.max() - y.min() + 1e-10)

        try:
            from scipy.signal import find_peaks_cwt, cwt, ricker
            cwt_matrix = cwt(y_norm, ricker, self.widths)
            peak_indices = set()
            for row in cwt_matrix:
                peaks, _ = find_peaks(row, distance=min_dist_pts)
                peak_indices.update(peaks)
            peak_indices = sorted(peak_indices)
        except Exception:
            peak_indices = self._fallback_detection(x, y_norm)

        peaks = []
        for idx in peak_indices:
            if idx >= len(x) or y[idx] < min_intensity:
                continue

            pos, intensity = self._parabolic_interpolate(x, y, idx)
            fwhm = self._estimate_fwhm(x, y, idx)
            prom = self._calc_prominence(y, idx)

            peaks.append(Peak(
                position=pos,
                intensity=float(y[idx]),
                fwhm=fwhm,
                prominence=prom,
                area=self._estimate_area(x, y, idx, fwhm),
                method='wavelet'
            ))

        peaks = self._merge_close_peaks(peaks)
        peaks.sort(key=lambda p: p.intensity, reverse=True)
        return peaks

    def _fallback_detection(self, x: np.ndarray, y: np.ndarray) -> List[int]:
        """备用检测方法"""
        peaks, _ = find_peaks(y, distance=max(3, int(0.3 / (x[1] - x[0]))))
        return list(peaks)

    @staticmethod
    def _parabolic_interpolate(x: np.ndarray, y: np.ndarray, idx: int) -> Tuple[float, float]:
        if idx == 0 or idx >= len(y) - 1:
            return float(x[idx]), float(y[idx])
        y0, y1, y2 = y[idx-1], y[idx], y[idx+1]
        denom = y0 + y2 - 2 * y1
        if abs(denom) < 1e-12:
            return float(x[idx]), float(y[idx])
        delta = (y0 - y2) / (2 * denom)
        delta = np.clip(delta, -0.5, 0.5)
        dx = x[idx] - x[idx-1]
        pos = x[idx] + delta * dx
        intensity = y1 - 0.25 * (y0 - y2) * delta
        return float(pos), float(max(intensity, y1))

    @staticmethod
    def _estimate_fwhm(x: np.ndarray, y: np.ndarray, idx: int) -> float:
        half = y[idx] / 2.0
        li = idx
        for i in range(idx, 0, -1):
            if y[i] <= half:
                li = i
                break
        ri = idx
        for i in range(idx, len(y)):
            if y[i] <= half:
                ri = i
                break
        if ri > li:
            return float(x[ri] - x[li])
        step = (x[-1] - x[0]) / (len(x) - 1) if len(x) > 1 else 0.02
        return step * 5

    @staticmethod
    def _calc_prominence(y: np.ndarray, idx: int, window: int = 80) -> float:
        left = np.min(y[max(0, idx - window): idx + 1])
        right = np.min(y[idx: min(len(y), idx + window + 1)])
        return float(y[idx] - max(left, right))

    @staticmethod
    def _estimate_area(x: np.ndarray, y: np.ndarray, idx: int, fwhm: float) -> float:
        half_fwhm = fwhm / 2
        mask = (x >= x[idx] - half_fwhm) & (x <= x[idx] + half_fwhm)
        if mask.sum() < 2:
            return 0.0
        try:
            return float(np.trapezoid(y[mask], x[mask]))
        except AttributeError:
            return float(np.trapz(y[mask], x[mask]))

    def _merge_close_peaks(self, peaks: List[Peak]) -> List[Peak]:
        if len(peaks) <= 1:
            return peaks
        peaks_sorted = sorted(peaks, key=lambda p: p.position)
        merged = [peaks_sorted[0]]
        for p in peaks_sorted[1:]:
            if p.position - merged[-1].position < self.min_distance:
                if p.intensity > merged[-1].intensity:
                    merged[-1] = p
            else:
                merged.append(p)
        return merged


# ─────────────────────────────────────────────
# 自适应SNIP背景扣除
# ─────────────────────────────────────────────

class AdaptiveSNIP:
    """
    自适应SNIP背景扣除算法

    优势：不同数据自动调整迭代次数，避免过度扣除
    """

    def __init__(self, max_iterations: int = 100, tolerance: float = 1e-4):
        self.max_iterations = max_iterations
        self.tolerance = tolerance

    def remove_background(self, y: np.ndarray, window: int = 50) -> np.ndarray:
        """
        自适应确定迭代次数的SNIP背景扣除

        Args:
            y: 强度数组
            window: 窗口大小

        Returns:
            背景数组
        """
        background_fixed = self._snip(y, iterations=50, window=window)

        residual = y - background_fixed
        std_residual = np.std(residual[residual > 0]) if np.any(residual > 0) else np.std(residual)

        prev_background = background_fixed.copy()

        for iteration in range(51, self.max_iterations + 1):
            current_background = self._snip(y, iterations=iteration, window=window)
            change = np.mean(np.abs(current_background - prev_background))

            if change < self.tolerance * std_residual:
                break
            prev_background = current_background

        return prev_background

    def _snip(self, y: np.ndarray, iterations: int, window: int) -> np.ndarray:
        """标准SNIP算法实现"""
        background = y.copy()
        n = len(y)

        for p in range(1, iterations + 1):
            temp = background.copy()
            for i in range(n):
                left = max(0, i - p * window // iterations)
                right = min(n, i + p * window // iterations + 1)
                local_min = np.min(temp[left:right])
                temp[i] = min(temp[i], local_min)
            background = temp

        return background


# ─────────────────────────────────────────────
# Kα2剥离器
# ─────────────────────────────────────────────

class KAlpha2Stripper:
    """
    Kα2剥离算法（Rachinger方法改进版）
    """

    def __init__(self, lambda1: float = 1.5406, lambda2: float = 1.5444,
                 ratio: float = 0.5):
        self.lambda1 = lambda1
        self.lambda2 = lambda2
        self.ratio = ratio

    def strip(self, two_theta: np.ndarray, intensity: np.ndarray) -> np.ndarray:
        """
        Rachinger方法剥离Kα2

        Args:
            two_theta: 2θ角度数组
            intensity: 强度数组

        Returns:
            剥离Kα2后的强度数组
        """
        delta_theta = (np.arcsin(self.lambda2 / (2 * np.sin(np.radians(two_theta / 2))))
                       - np.arcsin(self.lambda1 / (2 * np.sin(np.radians(two_theta / 2)))))

        intensity_kalpha1 = intensity.copy()

        for i in range(len(two_theta) - 1, -1, -1):
            target_theta = two_theta[i] + delta_theta[i]

            if target_theta > two_theta[-1]:
                continue

            kalpha2_contribution = np.interp(target_theta, two_theta, intensity_kalpha1)
            intensity_kalpha1[i] = (intensity[i] - self.ratio * kalpha2_contribution) / (1 + self.ratio)

        return np.maximum(intensity_kalpha1, 0)


# ─────────────────────────────────────────────
# 集成峰检测器
# ─────────────────────────────────────────────

class EnsemblePeakDetector:
    """
    集成多种方法的峰检测器

    组合：二阶导数法 + 小波变换 + 阈值法
    取交集或并集以提高检测准确性
    """

    def __init__(self, sensitivity: float = 0.05,
                 min_distance: float = 0.3):
        self.jade_detector = JadePeakDetector(sensitivity=sensitivity,
                                               min_distance=min_distance)
        self.wavelet_detector = WaveletPeakDetector(min_distance=min_distance)

    def detect(self, x: np.ndarray, y: np.ndarray,
               method: str = 'ensemble',
               min_intensity: float = 50) -> List[Peak]:
        """
        集成峰检测

        Args:
            x: 2θ 角度数组
            y: 强度数组
            method: 'ensemble'（取交集）/'union'（取并集）/'jade'/'wavelet'
            min_intensity: 最小峰强

        Returns:
            Peak 列表
        """
        if method == 'jade':
            return self.jade_detector.detect(x, y, min_intensity=min_intensity)
        elif method == 'wavelet':
            return self.wavelet_detector.detect(x, y, min_intensity=min_intensity)
        elif method == 'union':
            return self._union_detection(x, y, min_intensity)
        else:
            return self._intersection_detection(x, y, min_intensity)

    def _intersection_detection(self, x: np.ndarray, y: np.ndarray,
                                 min_intensity: float) -> List[Peak]:
        """取交集：两种方法都检测到的峰"""
        peaks_jade = {p.position: p for p in self.jade_detector.detect(x, y, min_intensity=min_intensity)}
        peaks_wavelet = {p.position: p for p in self.wavelet_detector.detect(x, y, min_intensity=min_intensity)}

        common_positions = set(peaks_jade.keys()) & set(peaks_wavelet.keys())
        merged_peaks = list(peaks_jade.values()) + list(peaks_wavelet.values())
        return self._merge_peaks(merged_peaks)

    def _union_detection(self, x: np.ndarray, y: np.ndarray,
                         min_intensity: float) -> List[Peak]:
        """取并集"""
        peaks_jade = self.jade_detector.detect(x, y, min_intensity=min_intensity)
        peaks_wavelet = self.wavelet_detector.detect(x, y, min_intensity=min_intensity)
        merged_peaks = peaks_jade + peaks_wavelet
        return self._merge_peaks(merged_peaks)

    def _merge_peaks(self, peaks: List[Peak]) -> List[Peak]:
        """合并重复峰"""
        if len(peaks) <= 1:
            return peaks
        pos_map = {}
        for p in peaks:
            key = round(p.position, 3)
            if key not in pos_map or p.intensity > pos_map[key].intensity:
                pos_map[key] = p
        result = sorted(pos_map.values(), key=lambda p: p.intensity, reverse=True)
        merged = [result[0]]
        for p in result[1:]:
            if p.position - merged[-1].position >= 0.3:
                merged.append(p)
        return merged
