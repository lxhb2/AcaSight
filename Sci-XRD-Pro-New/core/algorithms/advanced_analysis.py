"""
Sci-XRD Pro - 高级 XRD 分析算法模块
整合 Sci-XRD-Project 高级算法与现有算法增强
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Peak:
    """峰数据类"""
    d: float
    intensity: float
    fwhm: Optional[float] = None


@dataclass
class MatchResult:
    """匹配结果类"""
    card_num: int
    name: str
    formula: str
    matched_peaks: int
    total_peaks: int
    match_score: float
    d_errors: List[float]


def d_to_twotheta(d: float, wavelength: float = 1.5406) -> float:
    """d-spacing 转 2θ 角度"""
    sin_theta = wavelength / (2 * d)
    if sin_theta >= 1.0:
        return 180.0
    return math.degrees(2 * math.asin(sin_theta))


def twotheta_to_d(twotheta: float, wavelength: float = 1.5406) -> float:
    """2θ 角度转 d-spacing"""
    theta_rad = math.radians(twotheta / 2)
    return wavelength / (2 * math.sin(theta_rad))


def _adaptive_tolerance(d: float, wavelength: float = 1.5406) -> float:
    """自适应容差"""
    try:
        sin_theta = wavelength / (2 * d)
        if sin_theta >= 1.0:
            return 0.02
        two_theta = math.degrees(2 * math.asin(sin_theta))
        if two_theta >= 80:
            return 0.008
        elif two_theta >= 60:
            return 0.01
        elif two_theta >= 40:
            return 0.015
        elif two_theta >= 20:
            return 0.02
        else:
            return 0.025
    except:
        return 0.02


def derivative_peak_detection(
    x: np.ndarray,
    y: np.ndarray,
    smooth_window: int = 5,
    min_prominence: float = 0.02,
    min_distance: int = 10,
) -> List[Dict]:
    """
    导数峰位检测 — 抗噪声能力强

    Parameters
    ----------
    x : array — 2θ 角度数组
    y : array — 强度数组
    smooth_window : int — 平滑窗口大小
    min_prominence : float — 最小突出度
    min_distance : int — 最小峰间距

    Returns
    -------
    list of dict — 峰位列表
    """
    x = np.asarray(x)
    y = np.asarray(y)

    y_norm = y / (np.max(y) or 1)

    n = len(y_norm)
    half_w = smooth_window // 2

    dy = np.zeros(n)
    dy[half_w:-half_w] = np.diff(y_norm[half_w:-half_w + 1]) / np.diff(x[half_w:-half_w + 1])

    d2y = np.zeros(n)
    d2y[half_w:-half_w] = np.diff(dy[half_w:-half_w + 1]) / np.diff(x[half_w:-half_w + 1])

    peaks = []
    for i in range(half_w, n - half_w - 1):
        if dy[i] > 0 and dy[i + 1] < 0:
            if d2y[i] < 0:
                twotheta = x[i]
                intensity = y[i]
                prominence = y_norm[i] - np.min(y_norm[max(0, i - min_distance):i + min_distance])

                if prominence >= min_prominence:
                    half_max = y_norm[i] / 2
                    fwhm = _estimate_fwhm(x, y_norm, i, half_max)

                    peaks.append({
                        'twotheta': round(twotheta, 4),
                        'd': round(twotheta_to_d(twotheta), 5),
                        'intensity': round(intensity, 2),
                        'norm_intensity': round(y_norm[i] * 100, 1),
                        'fwhm': round(fwhm, 4),
                        'prominence': round(prominence * 100, 2),
                        'derivative': '1st_order_zero',
                    })

    peaks.sort(key=lambda p: p['intensity'], reverse=True)
    return peaks


def _estimate_fwhm(x: np.ndarray, y: np.ndarray, peak_idx: int, half_max: float) -> float:
    """估计半高宽 FWHM"""
    n = len(y)
    left_idx = peak_idx
    for i in range(peak_idx, -1, -1):
        if y[i] <= half_max:
            left_idx = i
            break

    right_idx = peak_idx
    for i in range(peak_idx, n):
        if y[i] <= half_max:
            right_idx = i
            break

    if right_idx > left_idx:
        return abs(x[right_idx - 1] - x[left_idx])
    return 0.0


def calculate_fom(
    exp_peaks: List[Tuple[float, float]],
    ref_peaks: List[Tuple[float, float]],
    wavelength: float = 1.5406,
) -> Dict:
    """
    计算 FOM 综合匹配度

    FOM 综合考虑：
      1. d-FOM：d-spacing 匹配质量（权重 40%）
      2. Δd/d：相对偏差（权重 20%）
      3. I-FOM：相对强度吻合度（权重 20%）
      4. M-FOM：多峰匹配因子（权重 20%）

    Parameters
    ----------
    exp_peaks : [(d, I), ...] 实验峰
    ref_peaks : [(d, I), ...] 参考峰
    wavelength : float — 辐射波长

    Returns
    -------
    dict — 包含各分项分数和总分
    """
    if not exp_peaks or not ref_peaks:
        return _empty_fom_result()

    exp_max = max(I for d, I in exp_peaks) or 1
    ref_max = max(I for d, I in ref_peaks) or 1

    d_fom_scores = []
    delta_d_scores = []
    i_fom_scores = []
    matched_refs = set()

    for exp_d, exp_I in exp_peaks:
        exp_norm_I = exp_I / exp_max
        best_score = 0
        best_delta = 0
        best_i_score = 0
        best_ref_idx = -1

        for idx, (ref_d, ref_I) in enumerate(ref_peaks):
            tol = _adaptive_tolerance(ref_d, wavelength) * ref_d
            diff = abs(exp_d - ref_d)

            if diff <= max(tol, 0.03):
                d_score = 1.0 - (diff / max(tol, 0.03))
                d_score = max(0, min(1, d_score))

                delta = diff / ref_d

                ref_norm_I = ref_I / ref_max
                i_score = 1.0 - abs(exp_norm_I - ref_norm_I)
                i_score = max(0, min(1, i_score))

                combined = 0.7 * d_score + 0.3 * i_score

                if combined > best_score:
                    best_score = combined
                    best_delta = delta
                    best_i_score = i_score
                    best_ref_idx = idx

        if best_ref_idx >= 0:
            d_fom_scores.append(best_score)
            delta_d_scores.append(best_delta)
            i_fom_scores.append(best_i_score)
            matched_refs.add(best_ref_idx)

    match_ratio = len(d_fom_scores) / max(len(exp_peaks), len(ref_peaks))

    avg_delta = sum(delta_d_scores) / len(delta_d_scores) if delta_d_scores else 1.0
    delta_score = 1.0 / (1.0 + avg_delta * 100)

    d_fom = sum(d_fom_scores) / len(d_fom_scores) if d_fom_scores else 0
    i_fom = sum(i_fom_scores) / len(i_fom_scores) if i_fom_scores else 0
    m_fom = match_ratio

    total_fom = (
        d_fom * 0.40 +
        delta_score * 0.20 +
        i_fom * 0.20 +
        m_fom * 0.20
    )

    icdd_score = total_fom * 100

    return {
        'd_fom': round(d_fom * 100, 1),
        'delta_fom': round(delta_score * 100, 1),
        'i_fom': round(i_fom * 100, 1),
        'm_fom': round(m_fom * 100, 1),
        'total_fom': round(icdd_score, 1),
        'n_matched': len(d_fom_scores),
        'avg_delta_d': round(avg_delta * 100, 3),
        'matched_ref_indices': list(matched_refs),
    }


def _empty_fom_result() -> Dict:
    return {
        'd_fom': 0.0, 'delta_fom': 0.0, 'i_fom': 0.0,
        'm_fom': 0.0, 'total_fom': 0.0, 'n_matched': 0,
        'avg_delta_d': 0.0, 'matched_ref_indices': [],
    }


def pattern_similarity(
    x1: np.ndarray, y1: np.ndarray,
    x2: np.ndarray, y2: np.ndarray,
    n_peaks: int = 5,
) -> float:
    """
    计算两条 XRD 图谱的相似度 — 归一化互相关
    """
    from scipy.signal import find_peaks

    peaks1, _ = find_peaks(y1, prominence=0.05)
    peaks2, _ = find_peaks(y2, prominence=0.05)

    if len(peaks1) == 0 or len(peaks2) == 0:
        return 0.0

    idx1 = np.argsort(y1[peaks1])[-n_peaks:]
    idx2 = np.argsort(y2[peaks2])[-n_peaks:]
    p1 = peaks1[idx1]
    p2 = peaks2[idx2]

    y1_n = y1[p1] / (np.max(y1[p1]) or 1)
    y2_n = y2[p2] / (np.max(y2[p2]) or 1)

    if len(p1) > 0 and len(p2) > 0:
        matches = 0
        for d1 in x1[p1]:
            for d2 in x2[p2]:
                if abs(d1 - d2) / d1 < 0.02:
                    matches += 1
                    break

        d_sim = matches / max(len(p1), len(p2))
    else:
        d_sim = 0

    min_len = min(len(y1_n), len(y2_n))
    y1_short = y1_n[:min_len]
    y2_short = y2_n[:min_len]

    if min_len > 2:
        corr = np.corrcoef(y1_short, y2_short)[0, 1]
        i_sim = max(0, corr) if not np.isnan(corr) else 0
    else:
        i_sim = 0

    similarity = (d_sim * 0.6 + i_sim * 0.4) * 100
    return round(similarity, 1)


def scherrer_crystallite_size(
    fwhm_deg: float,
    twotheta_deg: float,
    wavelength: float = 1.5406,
    k_shape: float = 0.89,
) -> float:
    """
    Scherrer 公式计算平均晶粒尺寸

    D = Kλ / (β cos θ)
    """
    if fwhm_deg <= 0 or twotheta_deg <= 0:
        return 0.0

    theta_rad = math.radians(twotheta_deg / 2)
    beta_rad = math.radians(fwhm_deg)

    D = k_shape * wavelength / (beta_rad * math.cos(theta_rad))

    return round(D, 2)


def scherrer_analysis(peaks: List[Dict]) -> List[Dict]:
    """
    对所有峰进行 Scherrer 晶粒尺寸分析
    """
    results = []
    for peak in peaks:
        twotheta = peak.get('twotheta', 0)
        fwhm = peak.get('fwhm', 0)

        if twotheta > 0 and fwhm > 0:
            D = scherrer_crystallite_size(fwhm, twotheta)
            results.append({
                **peak,
                'crystallite_size_nm': D,
                'note': _crystallite_note(D),
            })
        else:
            results.append({**peak, 'crystallite_size_nm': 0, 'note': 'insufficient data'})

    return results


def _crystallite_note(D: float) -> str:
    if D == 0:
        return 'N/A'
    elif D < 10:
        return f'纳米晶 ({D:.0f}nm)'
    elif D < 100:
        return f'细晶粒 ({D:.0f}nm)'
    else:
        return f'粗晶粒 ({D:.0f}nm)'


def hanawalt_search(
    exp_peaks: List[Tuple[float, float]],
    mineral_db: Dict,
    top_n: int = 3,
    wavelength: float = 1.5406,
) -> List[Dict]:
    """
    Hanawalt 检索算法 — 传统 PDF 检索方法

    原理：
      1. 取前3个最强峰（d1, d2, d3）
      2. 在索引中查找 d1 在相同区间的矿物
      3. 验证 d2, d3 是否匹配
    """
    if len(exp_peaks) < 3:
        return []

    sorted_peaks = sorted(exp_peaks, key=lambda x: x[1], reverse=True)[:top_n]
    d_values = [d for d, I in sorted_peaks]

    results = []
    for formula, info in mineral_db.items():
        ref_peaks = info.get('peaks', [])
        if not ref_peaks:
            continue

        ref_sorted = sorted(ref_peaks, key=lambda x: x[1], reverse=True)
        ref_d_values = [d for d, I in ref_sorted[:top_n]]

        matches = 0
        matched_d = []

        for exp_d in d_values:
            for ref_d in ref_d_values:
                tol = _adaptive_tolerance(ref_d, wavelength) * ref_d
                if abs(exp_d - ref_d) <= max(tol, 0.03):
                    matches += 1
                    matched_d.append((exp_d, ref_d))
                    break

        if matches >= 2:
            score = matches / top_n * 100
            results.append({
                'name': info.get('name', formula),
                'formula': formula,
                'hanawalt_score': round(score, 1),
                'n_matched': matches,
                'top_peaks': d_values,
                'ref_top_peaks': ref_d_values,
                'matched_peaks': matched_d,
            })

    results.sort(key=lambda x: (x['hanawalt_score'], x['n_matched']), reverse=True)
    return results


class XRDAnalyzer:
    """
    XRD 综合分析器

    整合所有算法，提供端到端的物相鉴定
    """

    def __init__(self, mineral_db: Dict = None, wavelength: float = 1.5406):
        self.mineral_db = mineral_db or {}
        self.wavelength = wavelength

    def set_database(self, db: Dict):
        """设置矿物参考库"""
        self.mineral_db = db

    def analyze(
        self,
        peaks: List[Tuple[float, float]],
        elements: List[str] = None,
        min_fom: float = 30.0,
        min_peaks: int = 2,
    ) -> Dict:
        """
        综合分析入口

        Parameters
        ----------
        peaks : [(d, I), ...] — 峰列表
        elements : list — 元素过滤
        min_fom : float — 最小 FOM 分数
        min_peaks : int — 最小匹配峰数

        Returns
        -------
        dict — 综合分析结果
        """
        exp_peaks = sorted(peaks, key=lambda x: x[1], reverse=True)

        filtered_db = self._filter_by_elements(elements)

        fom_results = []
        for formula, info in filtered_db.items():
            ref_peaks = info.get('peaks', [])
            fom = calculate_fom(exp_peaks, ref_peaks, self.wavelength)

            if fom['n_matched'] >= min_peaks and fom['total_fom'] >= min_fom:
                fom_results.append({
                    'name': info.get('name', formula),
                    'formula': formula,
                    **fom,
                })

        fom_results.sort(key=lambda x: x['total_fom'], reverse=True)

        hanawalt_results = hanawalt_search(exp_peaks, filtered_db, top_n=3)

        high_confidence = []
        for fr in fom_results:
            for hr in hanawalt_results:
                if fr['formula'] == hr['formula']:
                    confidence = (fr['total_fom'] + hr['hanawalt_score']) / 2
                    high_confidence.append({
                        **fr,
                        'confidence': round(confidence, 1),
                        'hanawalt_score': hr['hanawalt_score'],
                        'verified': True,
                    })
                    break

        return {
            'n_exp_peaks': len(exp_peaks),
            'fom_results': fom_results[:10],
            'hanawalt_results': hanawalt_results[:10],
            'high_confidence': high_confidence[:5],
        }

    def _filter_by_elements(self, elements: List[str]) -> Dict:
        """按元素过滤参考库"""
        if not elements:
            return self.mineral_db

        filtered = {}
        for formula, info in self.mineral_db.items():
            formula_elements = info.get('elements', [])
            if all(e in formula_elements for e in elements):
                filtered[formula] = info

        return filtered if filtered else self.mineral_db


def gaussian_fit(x: np.ndarray, y: np.ndarray, peak_idx: int, window: int = 10) -> Dict:
    """
    高斯拟合

    Parameters
    ----------
    x : array — 2θ 角度数组
    y : array — 强度数组
    peak_idx : int — 峰索引
    window : int — 拟合窗口

    Returns
    -------
    dict — 拟合参数 {A, mu, sigma, fwhm, area}
    """
    half_w = window // 2
    start = max(0, peak_idx - half_w)
    end = min(len(x), peak_idx + half_w)

    x_win = x[start:end]
    y_win = y[start:end]

    if len(x_win) < 5:
        return {'A': 0, 'mu': 0, 'sigma': 0, 'fwhm': 0, 'area': 0}

    y_max = np.max(y_win)
    y_min = np.min(y_win)
    mu_init = x[peak_idx]

    try:
        from scipy.optimize import curve_fit

        def gaussian(x, A, mu, sigma):
            return A * np.exp(-(x - mu) ** 2 / (2 * sigma ** 2))

        p0 = [y_max, mu_init, 0.1]
        popt, _ = curve_fit(gaussian, x_win, y_win - y_min, p0=p0, maxfev=1000)

        A, mu, sigma = popt
        fwhm = 2.355 * abs(sigma)
        area = A * abs(sigma) * math.sqrt(2 * math.pi)

        return {
            'A': round(A, 2),
            'mu': round(mu, 4),
            'sigma': round(abs(sigma), 4),
            'fwhm': round(fwhm, 4),
            'area': round(area, 2),
        }
    except:
        return {'A': round(y_max, 2), 'mu': round(mu_init, 4), 'sigma': 0.1, 'fwhm': 0.24, 'area': 0}


def lorentzian_fit(x: np.ndarray, y: np.ndarray, peak_idx: int, window: int = 10) -> Dict:
    """
    Lorentzian 拟合
    """
    half_w = window // 2
    start = max(0, peak_idx - half_w)
    end = min(len(x), peak_idx + half_w)

    x_win = x[start:end]
    y_win = y[start:end]

    if len(x_win) < 5:
        return {'A': 0, 'mu': 0, 'gamma': 0, 'fwhm': 0, 'area': 0}

    y_max = np.max(y_win)
    y_min = np.min(y_win)
    mu_init = x[peak_idx]

    try:
        from scipy.optimize import curve_fit

        def lorentzian(x, A, mu, gamma):
            return A * (gamma ** 2) / ((x - mu) ** 2 + gamma ** 2)

        p0 = [y_max, mu_init, 0.1]
        popt, _ = curve_fit(lorentzian, x_win, y_win - y_min, p0=p0, maxfev=1000)

        A, mu, gamma = popt
        fwhm = 2 * abs(gamma)
        area = A * abs(gamma) * math.pi

        return {
            'A': round(A, 2),
            'mu': round(mu, 4),
            'gamma': round(abs(gamma), 4),
            'fwhm': round(fwhm, 4),
            'area': round(area, 2),
        }
    except:
        return {'A': round(y_max, 2), 'mu': round(mu_init, 4), 'gamma': 0.1, 'fwhm': 0.2, 'area': 0}


def pseudo_voigt_fit(x: np.ndarray, y: np.ndarray, peak_idx: int, window: int = 10) -> Dict:
    """
    Pseudo-Voigt 拟合
    """
    half_w = window // 2
    start = max(0, peak_idx - half_w)
    end = min(len(x), peak_idx + half_w)

    x_win = x[start:end]
    y_win = y[start:end]

    if len(x_win) < 5:
        return {'A': 0, 'mu': 0, 'sigma': 0, 'eta': 0, 'fwhm': 0, 'area': 0}

    y_max = np.max(y_win)
    y_min = np.min(y_win)
    mu_init = x[peak_idx]

    try:
        from scipy.optimize import curve_fit

        def pseudo_voigt(x, A, mu, sigma, eta):
            gaussian = A * np.exp(-(x - mu) ** 2 / (2 * sigma ** 2))
            lorentzian = A * (sigma ** 2) / ((x - mu) ** 2 + sigma ** 2)
            return eta * lorentzian + (1 - eta) * gaussian

        p0 = [y_max, mu_init, 0.1, 0.5]
        popt, _ = curve_fit(pseudo_voigt, x_win, y_win - y_min, p0=p0, maxfev=1000)

        A, mu, sigma, eta = popt
        fwhm_g = 2.355 * abs(sigma)
        fwhm_l = 2 * abs(sigma)
        fwhm = eta * fwhm_l + (1 - eta) * fwhm_g

        return {
            'A': round(A, 2),
            'mu': round(mu, 4),
            'sigma': round(abs(sigma), 4),
            'eta': round(max(0, min(1, eta)), 3),
            'fwhm': round(fwhm, 4),
            'area': round(A * abs(sigma) * math.sqrt(2 * math.pi), 2),
        }
    except:
        return {'A': round(y_max, 2), 'mu': round(mu_init, 4), 'sigma': 0.1, 'eta': 0.5, 'fwhm': 0.22, 'area': 0}


def strip_k_alpha2(x: np.ndarray, y: np.ndarray, wavelength_ka1: float = 1.5406,
                   wavelength_ka2: float = 1.5444, intensity_ratio: float = 0.5) -> np.ndarray:
    """
    Kα2 剥离

    Parameters
    ----------
    x : array — 2θ 角度数组
    y : array — 强度数组
    wavelength_ka1 : float — Kα1 波长
    wavelength_ka2 : float — Kα2 波长
    intensity_ratio : float — I(ka2)/I(ka1) 强度比

    Returns
    -------
    array — 剥离 Kα2 后的强度数组
    """
    delta_lambda = wavelength_ka2 - wavelength_ka1
    delta_2theta = 2 * math.degrees(math.asin(wavelength_ka2 / (2 * 1.0))) - \
                   2 * math.degrees(math.asin(wavelength_ka1 / (2 * 1.0)))

    delta_2theta = abs(delta_2theta) * (x[1] - x[0]) / 0.01

    y_corrected = y.copy()

    for i in range(len(x)):
        idx_shifted = i + int(round(delta_2theta))
        if idx_shifted < len(y):
            y_corrected[i] = y[i] - y[idx_shifted] * intensity_ratio

    return np.maximum(y_corrected, 0)


def calculate_lattice_parameter(d_spacings: List[float], hkl_list: List[Tuple],
                               crystal_system: str = 'cubic') -> Dict:
    """
    计算晶格参数

    Parameters
    ----------
    d_spacings : list — d-spacing 值
    hkl_list : list — 对应的 hkl 指数
    crystal_system : str — 晶系

    Returns
    -------
    dict — 晶格参数
    """
    if len(d_spacings) != len(hkl_list):
        return {'a': 0, 'b': 0, 'c': 0, 'alpha': 0, 'beta': 0, 'gamma': 0}

    results = []

    for d, (h, k, l) in zip(d_spacings, hkl_list):
        if d <= 0:
            continue

        if crystal_system == 'cubic':
            a = d * math.sqrt(h ** 2 + k ** 2 + l ** 2)
            results.append(a)
        elif crystal_system == 'tetragonal':
            if l != 0:
                a = d * math.sqrt(h ** 2 + k ** 2 + l ** 2)
                results.append(a)
        elif crystal_system == 'orthorhombic':
            results.append(d * math.sqrt(h ** 2 + k ** 2 + l ** 2))

    if results:
        avg_a = np.mean(results)
        std_a = np.std(results)
        return {
            'a': round(avg_a, 4),
            'std': round(std_a, 4),
            'crystal_system': crystal_system,
            'n_reflections': len(results),
        }

    return {'a': 0, 'b': 0, 'c': 0, 'alpha': 90, 'beta': 90, 'gamma': 90}
