"""
Sci-XRD-Pro - 微观结构分析模块
==========================================
实现 JADE 标准微观结构分析算法：
  1. 谢乐公式（Scherrer Equation）
  2. Williamson-Hall 法（晶粒/应变分离）
  3. 结晶度计算
  4. 峰宽化分离

参考文献：
  - Williamson, G.K. & Hall, W.H. (1953). Acta Metallurgica, 1, 22-31.
  - Scherrer, P. (1918). Nachr. Ges. Wiss. Göttingen, 2, 98-100.
"""

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit, least_squares
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MicrostructureResult:
    """微观结构分析结果"""
    crystallite_size: float = 0.0
    crystallite_size_error: float = 0.0
    micro_strain: float = 0.0
    micro_strain_error: float = 0.0
    crystallinity: float = 0.0
    method: str = ""
    peaks_used: int = 0
    r_squared: float = 0.0
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict:
        return {
            'crystallite_size_nm': round(self.crystallite_size, 2),
            'crystallite_size_error': round(self.crystallite_size_error, 2),
            'micro_strain': round(self.micro_strain * 1000, 4),
            'micro_strain_10e-3': round(self.micro_strain * 1000, 4),
            'crystallinity_percent': round(self.crystallinity, 1),
            'method': self.method,
            'peaks_used': self.peaks_used,
            'r_squared': round(self.r_squared, 4),
            'details': self.details
        }


class PeakProfile:
    """峰形分析工具类"""

    @staticmethod
    def gaussian_fwhm(sigma: float) -> float:
        """高斯FWHM = 2*sqrt(2*ln2) * sigma ≈ 2.355 * sigma"""
        return 2.35482 * sigma

    @staticmethod
    def lorentzian_fwhm(gamma: float) -> float:
        """洛伦兹FWHM = 2 * gamma"""
        return 2.0 * gamma

    @staticmethod
    def pseudo_voigt_fwhm(sigma: float, gamma: float, eta: float) -> float:
        """
        伪Voigt FWHM 近似公式
        FWHM ≈ 0.5346 * (2*gamma) + sqrt(0.2166*(2*gamma)^2 + (2.35482*sigma)^2)
        """
        fwhm_g = 2.35482 * sigma
        fwhm_l = 2.0 * gamma
        return 0.5346 * fwhm_l + np.sqrt(0.2166 * fwhm_l**2 + fwhm_g**2)

    @staticmethod
    def size_broadening(sigma_size: float, theta: float, wavelength: float) -> float:
        """
        尺寸宽化贡献（高斯假设）
        β_size = K * λ / (D * cos(θ))
        """
        return sigma_size / np.cos(theta)

    @staticmethod
    def strain_broadening(epsilon: float, theta: float) -> float:
        """
        应变宽化贡献（高斯假设）
        β_strain = 4 * ε * tan(θ)
        """
        return 4.0 * epsilon * np.tan(theta)


class WilliamsonHall:
    """
    Williamson-Hall 法晶粒/应变分离

    原理：
        β_total = β_size + β_strain
        β_total * cos(θ) = K * λ / D + 4 * ε * sin(θ)

    Williamson-Hall 方程：
        β_total * cos(θ) = K * λ / D + 4 * ε * sin(θ)
        y = A + B * x
        其中 y = β_total * cos(θ), x = sin(θ)
        A = K * λ / D (尺寸项)
        B = 4 * ε (应变项)

    参考文献：
        Williamson, G.K. & Hall, W.H. (1953). Acta Metallurgica, 1, 22-31.
    """

    def __init__(self, wavelength: float = 1.5406):
        self.wavelength = wavelength
        self.k_scherrer = 0.9

    def analyze(self, peaks: List, instrument_broadening: float = 0.05) -> MicrostructureResult:
        """
        执行 Williamson-Hall 分析

        Args:
            peaks: 峰列表，每个峰需要包含 position (2θ), fwhm, intensity
            instrument_broadening: 仪器宽化 (FWHM, degrees)

        Returns:
            MicrostructureResult
        """
        if len(peaks) < 3:
            return MicrostructureResult(
                method='williamson-hall',
                details={'error': '需要至少3个峰进行W-H分析'}
            )

        x_data = []
        y_data = []

        for peak in peaks:
            if hasattr(peak, 'position'):
                two_theta = peak.position
                fwhm = peak.fwhm
            elif isinstance(peak, dict):
                two_theta = peak.get('position', 0)
                fwhm = peak.get('fwhm', 0)
            else:
                continue

            if two_theta < 1 or fwhm <= 0:
                continue

            theta = np.radians(two_theta / 2)

            if theta <= 0 or np.cos(theta) <= 0:
                continue

            sin_theta = np.sin(theta)
            cos_theta = np.cos(theta)

            beta = np.radians(fwhm)

            if beta <= 0:
                continue

            y = beta * cos_theta
            x = sin_theta

            x_data.append(x)
            y_data.append(y)

        if len(x_data) < 3:
            return MicrostructureResult(
                method='williamson-hall',
                details={'error': '有效峰数不足'}
            )

        x_data = np.array(x_data)
        y_data = np.array(y_data)

        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_data, y_data)

            strain = slope / 4.0
            strain_error = std_err / 4.0 if std_err > 0 else 0

            if intercept > 0:
                size = self.k_scherrer * self.wavelength / intercept
                size_error = size * (std_err / intercept) if intercept > 0 else 0
            else:
                size = 0
                size_error = 0

            crystallinity = self._estimate_crystallinity(peaks)

            result = MicrostructureResult(
                crystallite_size=size,
                crystallite_size_error=size_error,
                micro_strain=abs(strain),
                micro_strain_error=strain_error,
                crystallinity=crystallinity,
                method='williamson-hall',
                peaks_used=len(x_data),
                r_squared=r_value**2,
                details={
                    'intercept': float(intercept),
                    'slope': float(slope),
                    'std_err': float(std_err),
                    'instrument_broadening_deg': instrument_broadening
                }
            )

            return result

        except Exception as e:
            return MicrostructureResult(
                method='williamson-hall',
                details={'error': str(e)}
            )

    def analyze_uniform_strain(self, peaks: List) -> MicrostructureResult:
        """
        统一应变分析（考虑择优取向的改进W-H法）

        使用加权最小二乘法，考虑高角度峰更可靠
        """
        if len(peaks) < 3:
            return MicrostructureResult(method='williamson-hall-uniform')

        x_data = []
        y_data = []
        weights = []

        for peak in peaks:
            if hasattr(peak, 'position'):
                two_theta = peak.position
                fwhm = peak.fwhm
                intensity = getattr(peak, 'intensity', 100)
            elif isinstance(peak, dict):
                two_theta = peak.get('position', 0)
                fwhm = peak.get('fwhm', 0)
                intensity = peak.get('intensity', 100)
            else:
                continue

            if two_theta < 1 or fwhm <= 0:
                continue

            theta = np.radians(two_theta / 2)

            if theta <= 0 or np.cos(theta) <= 0:
                continue

            sin_theta = np.sin(theta)
            cos_theta = np.cos(theta)

            beta = np.radians(fwhm)

            x_data.append(sin_theta)
            y_data.append(beta * cos_theta)
            weights.append(intensity)

        if len(x_data) < 3:
            return MicrostructureResult(method='williamson-hall-uniform')

        x_data = np.array(x_data)
        y_data = np.array(y_data)
        weights = np.array(weights)

        try:
            slope, intercept, r_value, _, std_err = stats.linregress(
                x_data, y_data, w=weights
            )

            strain = slope / 4.0
            strain_error = abs(strain * 0.1) if strain != 0 else 0

            if intercept > 0:
                size = self.k_scherrer * self.wavelength / intercept
                size_error = size * 0.1
            else:
                size = 0
                size_error = 0

            result = MicrostructureResult(
                crystallite_size=size,
                crystallite_size_error=size_error,
                micro_strain=abs(strain),
                micro_strain_error=strain_error,
                method='williamson-hall-uniform',
                peaks_used=len(x_data),
                r_squared=r_value**2,
                details={'slope': float(slope), 'intercept': float(intercept)}
            )

            return result

        except Exception as e:
            return MicrostructureResult(
                method='williamson-hall-uniform',
                details={'error': str(e)}
            )

    @staticmethod
    def _estimate_crystallinity(peaks: List) -> float:
        """估算结晶度（简化方法）"""
        if not peaks:
            return 0.0

        total_intensity = 0
        crystalline_intensity = 0

        for peak in peaks:
            if hasattr(peak, 'intensity'):
                total_intensity += getattr(peak, 'area', peak.intensity)
                crystalline_intensity += peak.intensity
            elif isinstance(peak, dict):
                total_intensity += peak.get('area', peak.get('intensity', 0))
                crystalline_intensity += peak.get('intensity', 0)

        if total_intensity <= 0:
            return 0.0

        return min(100, max(0, crystalline_intensity / total_intensity * 100))


class ScherrerAnalysis:
    """
    谢乐公式晶粒尺寸分析

    公式：D = K * λ / (β * cos(θ))

    适用于：纳米晶（<100nm），粗晶的宽化主要由仪器和应变贡献
    """

    def __init__(self, wavelength: float = 1.5406, k_constant: float = 0.9):
        self.wavelength = wavelength
        self.k_constant = k_constant

    def analyze(self, peaks: List, instrument_broadening: float = 0.05,
                strain: float = None) -> MicrostructureResult:
        """
        执行谢乐公式分析

        Args:
            peaks: 峰列表
            instrument_broadening: 仪器宽化 (FWHM, degrees)
            strain: 如果已知应变，可提供以精修尺寸

        Returns:
            MicrostructureResult
        """
        if len(peaks) < 1:
            return MicrostructureResult(method='scherrer')

        sizes = []
        errors = []

        for peak in peaks:
            if hasattr(peak, 'position'):
                two_theta = peak.position
                fwhm = peak.fwhm
            elif isinstance(peak, dict):
                two_theta = peak.get('position', 0)
                fwhm = peak.get('fwhm', 0)
            else:
                continue

            if two_theta < 1 or fwhm <= instrument_broadening:
                continue

            theta = np.radians(two_theta / 2)

            if np.cos(theta) <= 0:
                continue

            beta_obs = np.radians(fwhm)
            beta_inst = np.radians(instrument_broadening)

            if strain is not None and strain > 0:
                beta_strain = 4.0 * strain * np.tan(theta)
                beta_size = np.sqrt(max(beta_obs**2 - beta_inst**2 - beta_strain**2, 0))
            else:
                beta_size = np.sqrt(max(beta_obs**2 - beta_inst**2, 0))

            if beta_size <= 0:
                continue

            size_nm = self.k_constant * self.wavelength / (beta_size * np.cos(theta))

            if 0 < size_nm < 1000:
                sizes.append(size_nm)
                errors.append(size_nm * 0.1)

        if not sizes:
            return MicrostructureResult(
                method='scherrer',
                details={'error': '无法计算有效晶粒尺寸'}
            )

        avg_size = np.mean(sizes)
        avg_error = np.sqrt(np.sum(np.array(errors)**2)) / len(errors)

        result = MicrostructureResult(
            crystallite_size=avg_size,
            crystallite_size_error=avg_error,
            method='scherrer',
            peaks_used=len(sizes),
            details={
                'individual_sizes': [round(s, 2) for s in sizes],
                'instrument_broadening_deg': instrument_broadening,
                'k_constant': self.k_constant
            }
        )

        return result


class CrystallinityAnalyzer:
    """
    结晶度分析

    方法：
    1. 分峰法：分离晶相峰和非晶散射
    2. 面积比法：晶相峰面积 / 总面积
    """

    def __init__(self, wavelength: float = 1.5406):
        self.wavelength = wavelength

    def analyze(self, x: np.ndarray, y: np.ndarray,
                peaks: List = None) -> MicrostructureResult:
        """
        计算结晶度

        Args:
            x: 2θ 数组
            y: 强度数组
            peaks: 峰列表（可选）

        Returns:
            MicrostructureResult
        """
        if len(x) < 10 or len(y) < 10:
            return MicrostructureResult(method='crystallinity')

        try:
            background = self._estimate_background(y)
            crystalline_y = np.maximum(y - background, 0)

            crystalline_area = np.trapz(crystalline_y, x)
            total_area = np.trapz(np.maximum(y - background.min(), 0), x)

            if total_area <= 0:
                crystallinity = 0
            else:
                crystallinity = min(100, crystalline_area / total_area * 100)

            return MicrostructureResult(
                crystallinity=crystallinity,
                method='crystallinity',
                details={
                    'crystalline_area': float(crystalline_area),
                    'total_area': float(total_area),
                    'background_min': float(background.min())
                }
            )

        except Exception as e:
            return MicrostructureResult(
                method='crystallinity',
                details={'error': str(e)}
            )

    @staticmethod
    def _estimate_background(y: np.ndarray, window: int = 51) -> np.ndarray:
        """使用最小滤波器估计背景"""
        from scipy.ndimage import minimum_filter1d
        return minimum_filter1d(y, size=window)


def analyze_microstructure(peaks: List, method: str = 'auto',
                          wavelength: float = 1.5406) -> MicrostructureResult:
    """
    便捷函数：执行微观结构分析

    Args:
        peaks: 峰列表
        method: 'auto', 'scherrer', 'williamson-hall', 'crystallinity'
        wavelength: X射线波长 (Angstrom)

    Returns:
        MicrostructureResult
    """
    if method == 'scherrer':
        analyzer = ScherrerAnalysis(wavelength=wavelength)
        return analyzer.analyze(peaks)
    elif method == 'williamson-hall':
        analyzer = WilliamsonHall(wavelength=wavelength)
        return analyzer.analyze(peaks)
    elif method == 'crystallinity':
        return MicrostructureResult(method='crystallinity')
    else:
        if len(peaks) >= 3:
            wh = WilliamsonHall(wavelength=wavelength)
            result = wh.analyze(peaks)
            if result.crystallite_size > 0:
                return result

        sch = ScherrerAnalysis(wavelength=wavelength)
        return sch.analyze(peaks)
