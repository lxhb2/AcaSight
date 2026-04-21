# -*- coding: utf-8 -*-
"""
XRD 高级算法模块
================
包含：
  1. FOM 综合匹配度算法（Figure of Merit）
  2. 一阶/二阶导数峰位检测
  3. 峰宽分析（Scherrer 晶粒尺寸）
  4. Hanawalt 检索索引
  5. 归一化图谱相似度
"""

import math
import re
import numpy as np
from typing import List, Dict, Tuple, Optional

# =============================================================================
# 工具函数
# =============================================================================

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


# =============================================================================
# 算法 1: 一阶/二阶导数峰位检测
# =============================================================================

def derivative_peak_detection(
    x: np.ndarray,
    y: np.ndarray,
    smooth_window: int = 5,
    min_prominence: float = 0.02,
    min_distance: int = 10,
) -> List[Dict]:
    """
    导数峰位检测 — 抗噪声能力强，比单纯阈值更精确

    原理：
      - 一阶导数 y'=0 处为峰顶/谷底
      - 二阶导数 y''<0 处为峰顶
      - 通过平滑和导数结合，消除噪声影响

    Parameters
    ----------
    x : array — 2θ 角度数组
    y : array — 强度数组
    smooth_window : int — 平滑窗口大小
    min_prominence : float — 最小突出度（相对值）
    min_distance : int — 最小峰间距（点数）

    Returns
    -------
    list of dict — 峰位列表 [{'twotheta': float, 'd': float, 'intensity': float,
                               'fwhm': float, 'derivative': str}, ...]
    """
    x = np.asarray(x)
    y = np.asarray(y)

    # 归一化强度
    y_norm = y / (np.max(y) or 1)

    # Savitzky-Golay 平滑 + 导数
    n = len(y_norm)
    half_w = smooth_window // 2

    # 一阶导数
    dy = np.zeros(n)
    dy[half_w:-half_w] = np.diff(y_norm[half_w:-half_w + 1]) / np.diff(x[half_w:-half_w + 1])

    # 二阶导数
    d2y = np.zeros(n)
    d2y[half_w:-half_w] = np.diff(dy[half_w:-half_w + 1]) / np.diff(x[half_w:-half_w + 1])

    # 找峰：dy 从正变负（极大值点）
    peaks = []
    for i in range(half_w, n - half_w - 1):
        # 一阶导数变号：从正到负
        if dy[i] > 0 and dy[i + 1] < 0:
            # 二阶导数为负（确认是极大值）
            if d2y[i] < 0:
                twotheta = x[i]
                intensity = y[i]
                prominence = y_norm[i] - np.min(y_norm[max(0, i - min_distance):i + min_distance])

                if prominence >= min_prominence:
                    # 估计 FWHM
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

    # 按强度降序
    peaks.sort(key=lambda p: p['intensity'], reverse=True)
    return peaks


def _estimate_fwhm(x: np.ndarray, y: np.ndarray, peak_idx: int, half_max: float) -> float:
    """估计半高宽 FWHM"""
    n = len(y)
    # 向左找半高点
    left_idx = peak_idx
    for i in range(peak_idx, -1, -1):
        if y[i] <= half_max:
            left_idx = i
            break

    # 向右找半高点
    right_idx = peak_idx
    for i in range(peak_idx, n):
        if y[i] <= half_max:
            right_idx = i
            break

    if right_idx > left_idx:
        return abs(x[right_idx - 1] - x[left_idx])
    return 0.0


# =============================================================================
# 算法 2: FOM 综合匹配度（Figure of Merit）
# =============================================================================

def calculate_fom(
    exp_peaks: List[Tuple[float, float]],
    ref_peaks: List[Tuple[float, float]],
    wavelength: float = 1.5406,
) -> Dict:
    """
    计算 FOM 综合匹配度 — 类似 ICDD PDF 评分标准

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

    # 强度归一化
    exp_max = max(I for d, I in exp_peaks) or 1
    ref_max = max(I for d, I in ref_peaks) or 1

    # 1. d-FOM：每个实验峰找最佳参考峰匹配
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
                # d-FOM: 匹配质量
                d_score = 1.0 - (diff / max(tol, 0.03))
                d_score = max(0, min(1, d_score))

                # Δd/d: 相对偏差
                delta = diff / ref_d

                # I-FOM: 强度匹配
                ref_norm_I = ref_I / ref_max
                i_score = 1.0 - abs(exp_norm_I - ref_norm_I)
                i_score = max(0, min(1, i_score))

                # 综合分数（d权重更高）
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

    # 2. M-FOM：多峰匹配因子
    # 匹配峰数 / max(实验峰数, 参考峰数)
    match_ratio = len(d_fom_scores) / max(len(exp_peaks), len(ref_peaks))

    # 3. Δd/d 平均值（越小越好）
    avg_delta = sum(delta_d_scores) / len(delta_d_scores) if delta_d_scores else 1.0
    delta_score = 1.0 / (1.0 + avg_delta * 100)  # 转换为 0-1 分数

    # 4. 计算各项 FOM
    d_fom = sum(d_fom_scores) / len(d_fom_scores) if d_fom_scores else 0
    i_fom = sum(i_fom_scores) / len(i_fom_scores) if i_fom_scores else 0
    m_fom = match_ratio

    # 5. 总 FOM（加权平均）
    # d-FOM 40%, Δd/d 20%, I-FOM 20%, M-FOM 20%
    total_fom = (
        d_fom * 0.40 +
        delta_score * 0.20 +
        i_fom * 0.20 +
        m_fom * 0.20
    )

    # 6. ICDD 标准品质因子（0-100）
    icdd_score = total_fom * 100

    return {
        'd_fom': round(d_fom * 100, 1),       # d匹配分 0-100
        'delta_fom': round(delta_score * 100, 1),  # Δd/d 分 0-100
        'i_fom': round(i_fom * 100, 1),        # 强度分 0-100
        'm_fom': round(m_fom * 100, 1),       # 多峰因子 0-100
        'total_fom': round(icdd_score, 1),    # 总 FOM 0-100
        'n_matched': len(d_fom_scores),
        'avg_delta_d': round(avg_delta * 100, 3),  # 平均 Δd/d (%)
        'matched_ref_indices': list(matched_refs),
    }


def _empty_fom_result() -> Dict:
    return {
        'd_fom': 0.0, 'delta_fom': 0.0, 'i_fom': 0.0,
        'm_fom': 0.0, 'total_fom': 0.0, 'n_matched': 0,
        'avg_delta_d': 0.0, 'matched_ref_indices': [],
    }


# =============================================================================
# 算法 3: 图谱相似度（归一化互相关）
# =============================================================================

def pattern_similarity(
    x1: np.ndarray, y1: np.ndarray,
    x2: np.ndarray, y2: np.ndarray,
    n_peaks: int = 5,
) -> float:
    """
    计算两条 XRD 图谱的相似度 — 归一化互相关

    方法：
      1. 取两条图谱的前 n_peaks 个峰
      2. 计算峰位置的相对距离
      3. 计算强度比例的相关性

    返回: 相似度 0-100
    """
    # 找峰
    from scipy.signal import find_peaks
    peaks1, _ = find_peaks(y1, prominence=0.05)
    peaks2, _ = find_peaks(y2, prominence=0.05)

    if len(peaks1) == 0 or len(peaks2) == 0:
        return 0.0

    # 取主要峰
    idx1 = np.argsort(y1[peaks1])[-n_peaks:]
    idx2 = np.argsort(y2[peaks2])[-n_peaks:]
    p1 = peaks1[idx1]
    p2 = peaks2[idx2]

    # 归一化强度
    y1_n = y1[p1] / (np.max(y1[p1]) or 1)
    y2_n = y2[p2] / (np.max(y2[p2]) or 1)

    # d-spacing 相似度（如果 x 是 d 值）
    if len(p1) > 0 and len(p2) > 0:
        # 简单匹配
        matches = 0
        for d1 in x1[p1]:
            for d2 in x2[p2]:
                if abs(d1 - d2) / d1 < 0.02:
                    matches += 1
                    break

        d_sim = matches / max(len(p1), len(p2))
    else:
        d_sim = 0

    # 强度相关性
    min_len = min(len(y1_n), len(y2_n))
    y1_short = y1_n[:min_len]
    y2_short = y2_n[:min_len]

    if min_len > 2:
        corr = np.corrcoef(y1_short, y2_short)[0, 1]
        i_sim = max(0, corr) if not np.isnan(corr) else 0
    else:
        i_sim = 0

    # 综合相似度
    similarity = (d_sim * 0.6 + i_sim * 0.4) * 100
    return round(similarity, 1)


# =============================================================================
# 算法 4: Scherrer 晶粒尺寸
# =============================================================================

def scherrer_crystallite_size(
    fwhm_deg: float,
    twotheta_deg: float,
    wavelength: float = 1.5406,
    k_shape: float = 0.89,
) -> float:
    """
    Scherrer 公式计算平均晶粒尺寸

    D = Kλ / (β cos θ)

    Parameters
    ----------
    fwhm_deg : float — 半高宽（度）
    twotheta_deg : float — 峰位 2θ（度）
    wavelength : float — 辐射波长（Å）
    k_shape : float — Scherrer 常数（0.62-2.0，通常取 0.89）

    Returns
    -------
    float — 平均晶粒尺寸（nm）
    """
    if fwhm_deg <= 0 or twotheta_deg <= 0:
        return 0.0

    theta_rad = math.radians(twotheta_deg / 2)
    beta_rad = math.radians(fwhm_deg)

    # Scherrer 公式
    D = k_shape * wavelength / (beta_rad * math.cos(theta_rad))

    return round(D, 2)


def scherrer_analysis(peaks: List[Dict]) -> List[Dict]:
    """
    对所有峰进行 Scherrer 晶粒尺寸分析

    返回每个峰的晶粒尺寸估计
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


# =============================================================================
# 算法 5: Hanawalt 检索
# =============================================================================

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

    Parameters
    ----------
    exp_peaks : [(d, I), ...] — 实验峰（已按强度降序）
    mineral_db : dict — 矿物参考库
    top_n : int — 取前 n 个最强峰进行检索
    wavelength : float — 辐射波长

    Returns
    -------
    list of dict — Hanawalt 检索结果
    """
    if len(exp_peaks) < 3:
        return []

    # 取前 top_n 个峰
    sorted_peaks = sorted(exp_peaks, key=lambda x: x[1], reverse=True)[:top_n]
    d_values = [d for d, I in sorted_peaks]

    results = []
    for formula, info in mineral_db.items():
        ref_peaks = info.get('peaks', [])
        if not ref_peaks:
            continue

        ref_sorted = sorted(ref_peaks, key=lambda x: x[1], reverse=True)
        ref_d_values = [d for d, I in ref_sorted[:top_n]]

        # Hanawalt 匹配
        matches = 0
        matched_d = []

        for exp_d in d_values:
            for ref_d in ref_d_values:
                tol = _adaptive_tolerance(ref_d, wavelength) * ref_d
                if abs(exp_d - ref_d) <= max(tol, 0.03):
                    matches += 1
                    matched_d.append((exp_d, ref_d))
                    break

        if matches >= 2:  # 至少2个峰匹配
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

    # 按 Hanawalt 分数排序
    results.sort(key=lambda x: (x['hanawalt_score'], x['n_matched']), reverse=True)
    return results


# =============================================================================
# 算法 6: 综合检索（FOM + Hanawalt + 多峰验证）
# =============================================================================

class XRDAnalyzer:
    """
    XRD 综合分析器

    整合所有算法，提供端到端的物相鉴定
    """

    def __init__(self, mineral_db: Dict = None, wavelength: float = 1.5406):
        """
        Parameters
        ----------
        mineral_db : dict — 矿物参考库
        wavelength : float — 辐射波长
        """
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

        # 元素过滤后的参考库
        filtered_db = self._filter_by_elements(elements)

        # 1. FOM 检索
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

        # 2. Hanawalt 检索
        hanawalt_results = hanawalt_search(exp_peaks, filtered_db, top_n=3)

        # 3. 交叉验证：同时被 FOM 和 Hanawalt 识别的高置信矿物
        high_confidence = []
        for fr in fom_results:
            for hr in hanawalt_results:
                if fr['formula'] == hr['formula']:
                    # 计算置信度
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
        """根据元素过滤参考库"""
        if not elements:
            return self.mineral_db

        filtered = {}
        for formula, info in self.mineral_db.items():
            formula_str = formula
            if ' ' in formula_str:
                elem_list = [re.sub(r'\d+', '', e).strip()
                             for e in formula_str.split()]
            else:
                elem_list = [e for e, _ in re.findall(r'([A-Z][a-z]?)(\d*)', formula_str)]

            elem_set = set(e.title() for e in elem_list if e)
            req_set = set(e.strip().title() for e in elements)

            if req_set.issubset(elem_set):
                filtered[formula] = info

        return filtered


# =============================================================================
# 演示
# =============================================================================

def _demo():
    """演示所有算法"""
    # 测试数据
    exp_peaks = [
        (3.035, 100),
        (1.858, 85),
        (2.715, 90),
        (2.425, 80),
        (3.348, 30),
    ]

    # 参考库
    db = {
        'CuFeS2': {
            'name': 'Chalcopyrite',
            'peaks': [(3.030, 100), (1.860, 83), (1.590, 20), (1.210, 7), (2.620, 7)],
        },
        'FeS2': {
            'name': 'Pyrite',
            'peaks': [(2.710, 100), (2.420, 85), (2.090, 60), (1.630, 50), (1.560, 40)],
        },
        'SiO2': {
            'name': 'Quartz',
            'peaks': [(3.350, 100), (4.250, 25), (1.820, 25), (1.540, 20), (2.450, 15)],
        },
        'CaCO3': {
            'name': 'Calcite',
            'peaks': [(3.040, 100), (2.280, 40), (2.090, 30), (1.910, 25), (1.870, 20)],
        },
    }

    print("=" * 70)
    print("Algorithm 1: FOM Analysis")
    print("=" * 70)
    for formula, info in db.items():
        fom = calculate_fom(exp_peaks, info['peaks'])
        print("\n{}:".format(info['name']))
        print("  d-FOM={:.1f}  I-FOM={:.1f}  M-FOM={:.1f}  Total={:.1f}".format(
            fom['d_fom'], fom['i_fom'], fom['m_fom'], fom['total_fom']))
        print("  Matched peaks={}  Avg delta-d={:.3f}%".format(
            fom['n_matched'], fom['avg_delta_d']))

    print("\n" + "=" * 70)
    print("Algorithm 2: Hanawalt Search")
    print("=" * 70)
    results = hanawalt_search(exp_peaks, db, top_n=3)
    for r in results[:5]:
        print("{}: score={:.0f}  matched={}/3".format(
            r['name'], r['hanawalt_score'], r['n_matched']))

    print("\n" + "=" * 70)
    print("Algorithm 3: Scherrer Crystallite Size")
    print("=" * 70)
    test_peaks = [
        {'twotheta': 29.5, 'fwhm': 0.15, 'intensity': 100},
        {'twotheta': 36.0, 'fwhm': 0.25, 'intensity': 80},
        {'twotheta': 45.8, 'fwhm': 0.10, 'intensity': 60},
    ]
    for p in scherrer_analysis(test_peaks):
        print("2θ={:.1f}° FWHM={:.3f}° → D={}nm  ({})".format(
            p['twotheta'], p['fwhm'], p['crystallite_size_nm'], p['note']))

    print("\n" + "=" * 70)
    print("Algorithm 4: Comprehensive XRDAnalyzer")
    print("=" * 70)
    analyzer = XRDAnalyzer(db)
    result = analyzer.analyze(exp_peaks, min_fom=30)
    print("\nFOM Results:")
    for r in result['fom_results'][:3]:
        print("  {}: FOM={:.1f}".format(r['name'], r['total_fom']))
    print("\nHigh Confidence (FOM+Hanawalt):")
    for r in result['high_confidence']:
        print("  {}: confidence={:.1f}".format(r['name'], r['confidence']))


if __name__ == "__main__":
    _demo()
