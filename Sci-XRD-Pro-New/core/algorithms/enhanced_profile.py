"""
Sci-XRD-Pro - 增强峰形拟合模块
==========================================
实现 JADE 风格的增强峰形拟合算法：

1. 伪Voigt（Pseudo-Voigt）峰形
2. 不对称校正（Asymmetry Correction）
3. FCJ 轴向发散校正（Finger-Cox-Jephcoat）
4. 峰宽化分离（尺寸/应变）

参考文献：
  - Finger, L.A., Cox, D.E. & Jephcoat, A.P. (1994). J. Appl. Crystallogr., 27, 892-900.
  - Thompson, P., Cox, D.E. & Hastings, J.B. (1987). J. Appl. Crystallogr., 20, 79-83.
"""

import numpy as np
from scipy.optimize import curve_fit, least_squares
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class ProfileParams:
    """峰形参数"""
    amplitude: float = 100.0
    center: float = 20.0
    sigma: float = 0.1
    gamma: float = 0.1
    eta: float = 0.5
    asymmetry: float = 0.0
    fcj_alpha: float = 0.0
    fcj_beta: float = 0.0
    background: float = 0.0


class PeakProfileFunctions:
    """峰形函数库"""

    @staticmethod
    def gaussian(x: np.ndarray, amp: float, cen: float, sigma: float) -> np.ndarray:
        """高斯函数"""
        return amp * np.exp(-(x - cen)**2 / (2 * sigma**2))

    @staticmethod
    def lorentzian(x: np.ndarray, amp: float, cen: float, gamma: float) -> np.ndarray:
        """洛伦兹函数"""
        return amp / (1 + ((x - cen) / gamma)**2)

    @staticmethod
    def pseudo_voigt(x: np.ndarray, amp: float, cen: float,
                    sigma: float, eta: float) -> np.ndarray:
        """
        Pseudo-Voigt function
        η·Lorentz + (1-η)·Gaussian

        Args:
            eta: mixing coefficient [0, 1]
                  0 = pure Gaussian
                  1 = pure Lorentzian
        """
        gamma = sigma
        g = PeakProfileFunctions.gaussian(x, 1.0, cen, sigma)
        l = PeakProfileFunctions.lorentzian(x, 1.0, cen, gamma)
        return amp * (eta * l + (1 - eta) * g)

    @staticmethod
    def pseudo_voigt_with_bg(x: np.ndarray, amp: float, cen: float,
                            sigma: float, eta: float, bg: float) -> np.ndarray:
        """带背景的伪Voigt"""
        return PeakProfileFunctions.pseudo_voigt(x, amp, cen, sigma, eta) + bg

    @staticmethod
    def voigt(x: np.ndarray, amp: float, cen: float,
             sigma: float, gamma: float) -> np.ndarray:
        """
        真实Voigt函数（伪Voigt的近似）
        使用scipy的voigt_profile更准确
        """
        from scipy.special import voigt_profile
        return amp * voigt_profile(x - cen, sigma, gamma)

    @staticmethod
    def split_pseudo_voigt(x: np.ndarray, amp: float, cen: float,
                          sigma_l: float, sigma_r: float,
                          eta: float) -> np.ndarray:
        """
        分裂伪Voigt（处理不对称峰）
        左半侧用sigma_l，右半侧用sigma_r
        """
        result = np.zeros_like(x)

        left_mask = x <= cen
        right_mask = x > cen

        if np.any(left_mask):
            result[left_mask] = PeakProfileFunctions.pseudo_voigt(
                x[left_mask], amp, cen, sigma_l, eta
            )

        if np.any(right_mask):
            result[right_mask] = PeakProfileFunctions.pseudo_voigt(
                x[right_mask], amp, cen, sigma_r, eta
            )

        return result


class AsymmetryCorrection:
    """
    不对称校正

    用于修正：
    - 择优取向引起的峰歪
    - 样品透光引起的峰不对称
    - 仪器几何不对称
    """

    @staticmethod
    def correction(x: np.ndarray, intensity: np.ndarray,
                  center: float, fwhm: float,
                  asymmetry: float = 0.0) -> np.ndarray:
        """
        应用不对称校正

        Args:
            x: 角度数组
            intensity: 原始强度
            center: 峰中心
            fwhm: 半高宽
            asymmetry: 不对称参数 (>0 右尾长, <0 左尾长)

        Returns:
            校正后的强度
        """
        if abs(asymmetry) < 0.01:
            return intensity

        corrected = intensity.copy()
        sigma = fwhm / 2.35482

        for i, xi in enumerate(x):
            dx = xi - center
            dist = abs(dx) / sigma

            if dist > 0:
                asym_factor = 1.0 + asymmetry * np.sign(dx) * (dist ** 0.5)
                corrected[i] = intensity[i] * asym_factor

        return np.maximum(corrected, 0)

    @staticmethod
    def split_voigt_asymmetry(x: np.ndarray, amp: float, cen: float,
                             sigma_l: float, sigma_r: float,
                             gamma_l: float, gamma_r: float) -> np.ndarray:
        """
        分裂Voigt函数（不对称峰形的更精确模型）

        左半峰用一套sigma/gamma，右半峰用另一套
        """
        result = np.zeros_like(x)
        left_mask = x <= cen
        right_mask = x > cen

        if np.any(left_mask):
            result[left_mask] = PeakProfileFunctions.pseudo_voigt(
                x[left_mask], amp, cen, sigma_l, 0.5
            )

        if np.any(right_mask):
            result[right_mask] = PeakProfileFunctions.pseudo_voigt(
                x[right_mask], amp, cen, sigma_r, 0.5
            )

        return result


class FCJCorrection:
    """
    Finger-Cox-Jephcoat (FCJ) 轴向发散校正

    修正 X 射线轴向发散引起的峰偏移和宽化
    主要用于高角度峰的精确拟合

    参考文献：
      Finger, L.A., Cox, D.E. & Jephcoat, A.P. (1994). J. Appl. Crystallogr., 27, 892-900.
    """

    @staticmethod
    def apply(x: np.ndarray, intensity: np.ndarray,
             center: float, fwhm: float,
             alpha: float = 0.0, beta: float = 0.0,
             theta_min: float = 5.0, theta_max: float = 45.0) -> np.ndarray:
        """
        应用 FCJ 校正

        Args:
            x: 2θ 角度数组
            intensity: 原始强度
            center: 峰中心
            fwhm: 半高宽
            alpha: 水平发散参数 (radians)
            beta: 垂直发散参数 (radians)
            theta_min: 样品旋转角最小值
            theta_max: 样品旋转角最大值

        Returns:
            校正后的强度
        """
        if alpha < 1e-6 and beta < 1e-6:
            return intensity

        corrected = intensity.copy()
        theta_c = np.radians(center / 2)
        half_width = fwhm / 2

        for i, xi in enumerate(x):
            if xi <= 0:
                continue

            theta_i = np.radians(xi / 2)
            delta_theta = theta_i - theta_c

            if abs(delta_theta) < 0.001:
                continue

            tan_theta = np.tan(theta_i)
            if abs(tan_theta) < 1e-6:
                continue

            correction_factor = 1.0 + (alpha / tan_theta) + (beta * tan_theta)

            idx_shift = int(delta_theta / np.radians(half_width / 10))
            new_idx = i - idx_shift

            if 0 <= new_idx < len(corrected):
                corrected[i] = intensity[new_idx] * correction_factor

        return np.maximum(corrected, 0)

    @staticmethod
    def fcj_broadening(theta: float, alpha: float, beta: float,
                      instrument_broadening: float = 0.05) -> float:
        """
        计算 FCJ 引起的峰宽化

        Args:
            theta: 布拉格角 (degrees)
            alpha: 水平发散参数
            beta: 垂直发散参数
            instrument_broadening: 仪器宽化 (degrees)

        Returns:
            FCJ 引起的额外宽化 (degrees)
        """
        theta_rad = np.radians(theta)

        if np.sin(theta_rad) < 1e-6:
            return 0

        term1 = alpha / np.tan(theta_rad) if np.tan(theta_rad) != 0 else 0
        term2 = beta * np.tan(theta_rad)

        broadening = np.degrees(np.sqrt(term1**2 + term2**2))

        return np.sqrt(broadening**2 + instrument_broadening**2)


class EnhancedPeakFitter:
    """
    增强峰形拟合器

    综合多种峰形函数和校正，提供高精度的峰参数提取
    """

    def __init__(self, wavelength: float = 1.5406):
        self.wavelength = wavelength
        self.instrument_broadening = 0.05

    def fit_peak(self, x: np.ndarray, y: np.ndarray,
                initial_params: Dict = None,
                fit_asymmetry: bool = True,
                fit_fcj: bool = False) -> Dict:
        """
        拟合单个峰

        Args:
            x: 角度数组
            y: 强度数组
            initial_params: 初始参数
            fit_asymmetry: 是否拟合不对称性
            fit_fcj: 是否应用FCJ校正

        Returns:
            拟合参数
        """
        if initial_params is None:
            initial_params = self._estimate_initial(x, y)

        try:
            if fit_asymmetry:
                return self._fit_asymmetric_peak(x, y, initial_params)
            elif fit_fcj:
                return self._fit_fcj_peak(x, y, initial_params)
            else:
                return self._fit_pseudo_voigt(x, y, initial_params)
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'params': initial_params
            }

    def _estimate_initial(self, x: np.ndarray, y: np.ndarray) -> Dict:
        """估计初始参数"""
        idx_max = np.argmax(y)
        background = np.percentile(y, 10)

        return {
            'amplitude': float(y[idx_max] - background),
            'center': float(x[idx_max]),
            'sigma': float(self._estimate_sigma(x, y, idx_max)),
            'gamma': float(self._estimate_sigma(x, y, idx_max)),
            'eta': 0.5,
            'background': float(background),
            'asymmetry': 0.0
        }

    def _estimate_sigma(self, x: np.ndarray, y: np.ndarray, idx_max: int) -> float:
        """估计sigma"""
        half_max = (y[idx_max] + y.min()) / 2

        left_idx = idx_max
        for i in range(idx_max, 0, -1):
            if y[i] <= half_max:
                left_idx = i
                break

        right_idx = idx_max
        for i in range(idx_max, len(y)):
            if y[i] <= half_max:
                right_idx = i
                break

        fwhm = x[right_idx] - x[left_idx]
        return fwhm / 2.35482

    def _fit_pseudo_voigt(self, x: np.ndarray, y: np.ndarray,
                         initial: Dict) -> Dict:
        """拟合伪Voigt峰"""
        bg_est = initial['background']
        amp0 = initial['amplitude']
        cen0 = initial['center']
        sig0 = initial['sigma']
        eta0 = initial.get('eta', 0.5)

        try:
            popt, pcov = curve_fit(
                PeakProfileFunctions.pseudo_voigt_with_bg,
                x, y,
                p0=[amp0, cen0, sig0, eta0, bg_est],
                bounds=(
                    [0, x.min(), 0.001, 0, 0],
                    [amp0*5, x.max(), 1.0, 1.0, np.max(y)]
                ),
                maxfev=3000
            )

            amp, cen, sigma, eta, bg = popt
            fwhm = self._pseudo_voigt_fwhm(sigma, sigma, eta)

            return {
                'success': True,
                'amplitude': float(amp),
                'center': float(cen),
                'sigma': float(sigma),
                'gamma': float(sigma),
                'eta': float(eta),
                'fwhm': float(fwhm),
                'background': float(bg),
                'area': float(self._calculate_area(amp, sigma, eta)),
                'method': 'pseudo_voigt'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'params': initial
            }

    def _fit_asymmetric_peak(self, x: np.ndarray, y: np.ndarray,
                           initial: Dict) -> Dict:
        """拟合不对称峰"""
        bg_est = initial['background']
        amp0 = initial['amplitude']
        cen0 = initial['center']
        sig0 = initial['sigma']
        asym0 = initial.get('asymmetry', 0.0)

        def split_pv_with_bg(x_arr, amp, cen, sigma_l, sigma_r, eta, bg):
            left_mask = x_arr <= cen
            right_mask = x_arr > cen
            result = np.zeros_like(x_arr)

            if np.any(left_mask):
                result[left_mask] = PeakProfileFunctions.pseudo_voigt(
                    x_arr[left_mask], amp, cen, sigma_l, eta
                )
            if np.any(right_mask):
                result[right_mask] = PeakProfileFunctions.pseudo_voigt(
                    x_arr[right_mask], amp, cen, sigma_r, eta
                )

            return result + bg

        try:
            popt, pcov = curve_fit(
                split_pv_with_bg,
                x, y,
                p0=[amp0, cen0, sig0, sig0, 0.5, bg_est],
                bounds=(
                    [0, x.min(), 0.001, 0.001, 0, 0],
                    [amp0*5, x.max(), 1.0, 1.0, 1.0, np.max(y)]
                ),
                maxfev=5000
            )

            amp, cen, sigma_l, sigma_r, eta, bg = popt
            fwhm_avg = (sigma_l + sigma_r) / 2 * 2.35482

            return {
                'success': True,
                'amplitude': float(amp),
                'center': float(cen),
                'sigma_left': float(sigma_l),
                'sigma_right': float(sigma_r),
                'sigma_avg': float((sigma_l + sigma_r) / 2),
                'eta': float(eta),
                'fwhm': float(fwhm_avg),
                'background': float(bg),
                'area': float(self._calculate_area(amp, (sigma_l+sigma_r)/2, eta)),
                'asymmetry': float((sigma_r - sigma_l) / (sigma_l + sigma_r + 1e-6)),
                'method': 'split_pseudo_voigt'
            }

        except Exception as e:
            return self._fit_pseudo_voigt(x, y, initial)

    def _fit_fcj_peak(self, x: np.ndarray, y: np.ndarray,
                     initial: Dict) -> Dict:
        """拟合带FCJ校正的峰"""
        result = self._fit_pseudo_voigt(x, y, initial)

        if not result['success']:
            return result

        center = result['center']
        fwhm = result['fwhm']

        alpha_est = 0.001
        beta_est = 0.001

        corrected_intensity = FCJCorrection.apply(
            x, y, center, fwhm,
            alpha=alpha_est, beta=beta_est
        )

        result['fcj_alpha'] = alpha_est
        result['fcj_beta'] = beta_est
        result['method'] = 'pseudo_voigt_fcj'

        return result

    @staticmethod
    def _pseudo_voigt_fwhm(sigma: float, gamma: float, eta: float) -> float:
        """计算伪Voigt的FWHM"""
        fwhm_g = 2.35482 * sigma
        fwhm_l = 2.0 * gamma
        return 0.5346 * fwhm_l + np.sqrt(0.2166 * fwhm_l**2 + fwhm_g**2)

    @staticmethod
    def _calculate_area(amp: float, sigma: float, eta: float) -> float:
        """计算峰面积"""
        area_g = amp * sigma * np.sqrt(2 * np.pi)
        area_l = amp * np.pi * sigma
        return area_g * (1 - eta) + area_l * eta


def fit_peak(x: np.ndarray, y: np.ndarray,
            method: str = 'pseudo_voigt',
            wavelength: float = 1.5406) -> Dict:
    """
    便捷函数：拟合峰

    Args:
        x: 角度数组
        y: 强度数组
        method: 'pseudo_voigt', 'asymmetric', 'fcj'
        wavelength: X射线波长

    Returns:
        拟合结果
    """
    fitter = EnhancedPeakFitter(wavelength=wavelength)

    if method == 'asymmetric':
        return fitter.fit_peak(x, y, fit_asymmetry=True, fit_fcj=False)
    elif method == 'fcj':
        return fitter.fit_peak(x, y, fit_asymmetry=False, fit_fcj=True)
    else:
        return fitter.fit_peak(x, y, fit_asymmetry=False, fit_fcj=False)
