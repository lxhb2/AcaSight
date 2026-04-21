"""
修复版高级XRD算法
包含原来Sci-XRD-Project的所有高级算法
"""

import math
import re
import numpy as np
from typing import List, Dict, Tuple, Optional, Union

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


def adaptive_tolerance(d: float, wavelength: float = 1.5406) -> float:
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
    for i in range(half_w, n - half_w):
        window = y_norm[i - half_w:i + half_w + 1]
        dy[i] = np.polyfit(range(smooth_window), window, 1)[0]

    # 二阶导数
    d2y = np.zeros(n)
    for i in range(half_w, n - half_w):
        window = dy[i - half_w:i + half_w + 1]
        d2y[i] = np.polyfit(range(smooth_window), window, 1)[0]

    # 寻找峰位（dy=0 且 d2y<0）
    peaks = []
    for i in range(half_w + 1, n - half_w - 1):
        # 一阶导数过零点
        if dy[i] * dy[i + 1] <= 0 and dy[i] > dy[i + 1]:
            # 二阶导数为负（凸函数）
            if d2y[i] < 0:
                # 插值精确位置
                if dy[i] != dy[i + 1]:
                    frac = -dy[i] / (dy[i + 1] - dy[i])
                    pos = x[i] + frac * (x[i + 1] - x[i])
                    intensity = y[i] + frac * (y[i + 1] - y[i])
                else:
                    pos = x[i]
                    intensity = y[i]

                # 计算半高宽（简化）
                left_idx = max(0, i - 20)
                right_idx = min(n - 1, i + 20)
                
                half_max = intensity / 2
                left_pos = None
                right_pos = None
                
                # 向左找半高宽点
                for j in range(i, left_idx - 1, -1):
                    if y[j] <= half_max:
                        if j < i - 1:
                            frac = (half_max - y[j]) / (y[j + 1] - y[j])
                            left_pos = x[j] + frac * (x[j + 1] - x[j])
                        break
                
                # 向右找半高宽点
                for j in range(i, right_idx + 1):
                    if y[j] <= half_max:
                        if j > i + 1:
                            frac = (half_max - y[j - 1]) / (y[j] - y[j - 1])
                            right_pos = x[j - 1] + frac * (x[j] - x[j - 1])
                        break
                
                fwhm = 0.0
                if left_pos is not None and right_pos is not None:
                    fwhm = right_pos - left_pos
                
                # 计算突出度
                left_min = np.min(y[max(0, i - 50):i])
                right_min = np.min(y[i:min(n, i + 50)])
                prominence = intensity - max(left_min, right_min)
                
                if prominence >= min_prominence * np.max(y):
                    peaks.append({
                        'twotheta': float(pos),
                        'd': twotheta_to_d(float(pos)),
                        'intensity': float(intensity),
                        'fwhm': float(fwhm),
                        'prominence': float(prominence),
                        'derivative': 'second_order'
                    })

    # 按强度排序
    peaks.sort(key=lambda p: p['intensity'], reverse=True)
    
    # 过滤太近的峰
    filtered_peaks = []
    for peak in peaks:
        too_close = False
        for existing in filtered_peaks:
            if abs(peak['twotheta'] - existing['twotheta']) < min_distance * (x[1] - x[0]):
                too_close = True
                break
        if not too_close:
            filtered_peaks.append(peak)
    
    return filtered_peaks


# =============================================================================
# 算法 2: FOM 综合匹配度
# =============================================================================

def calculate_fom(
    exp_peaks: List[Tuple[float, float]],
    ref_peaks: List[Tuple[float, float]],
    wavelength: float = 1.5406,
    d_weight: float = 0.5,
    i_weight: float = 0.3,
    m_weight: float = 0.2,
) -> Dict:
    """
    FOM (Figure of Merit) 综合匹配度算法
    
    参数:
        exp_peaks: 实验峰 [(d, I), ...]
        ref_peaks: 参考峰 [(d, I), ...]
        
    返回:
        {
            'd_fom': d-spacing 匹配分数,
            'i_fom': 强度匹配分数,
            'm_fom': 多重性匹配分数,
            'total_fom': 总分,
            'n_matched': 匹配峰数,
            'avg_delta_d': 平均d-spacing误差百分比
        }
    """
    if not exp_peaks or not ref_peaks:
        return {
            'd_fom': 0, 'i_fom': 0, 'm_fom': 0, 'total_fom': 0,
            'n_matched': 0, 'avg_delta_d': 100.0
        }
    
    # 归一化强度
    exp_max = max(i for _, i in exp_peaks)
    ref_max = max(i for _, i in ref_peaks)
    
    exp_norm = [(d, i/exp_max) for d, i in exp_peaks]
    ref_norm = [(d, i/ref_max) for d, i in ref_peaks]
    
    # 匹配峰
    matched_pairs = []
    total_delta_d = 0.0
    
    for exp_d, exp_i in exp_norm:
        best_match = None
        best_error = float('inf')
        
        for ref_d, ref_i in ref_norm:
            # 计算d-spacing误差百分比
            error_pct = abs(exp_d - ref_d) / ref_d * 100
            
            # 使用自适应容差
            tolerance = adaptive_tolerance(ref_d, wavelength) * 100  # 转百分比
            
            if error_pct <= tolerance:
                if error_pct < best_error:
                    best_error = error_pct
                    best_match = (ref_d, ref_i, error_pct)
        
        if best_match:
            matched_pairs.append((exp_d, exp_i, best_match[0], best_match[1], best_error))
            total_delta_d += best_error
    
    n_matched = len(matched_pairs)
    
    if n_matched == 0:
        return {
            'd_fom': 0, 'i_fom': 0, 'm_fom': 0, 'total_fom': 0,
            'n_matched': 0, 'avg_delta_d': 100.0
        }
    
    # 1. d-spacing 匹配分数 (0-100)
    avg_delta_d = total_delta_d / n_matched
    d_fom = max(0, 100 - avg_delta_d * 2)  # 误差每1%扣2分
    
    # 2. 强度匹配分数
    intensity_errors = []
    for exp_d, exp_i, ref_d, ref_i, _ in matched_pairs:
        intensity_error = abs(exp_i - ref_i) * 100  # 百分比误差
        intensity_errors.append(intensity_error)
    
    avg_intensity_error = np.mean(intensity_errors) if intensity_errors else 100
    i_fom = max(0, 100 - avg_intensity_error)
    
    # 3. 多重性匹配分数
    n_exp = len(exp_peaks)
    n_ref = len(ref_peaks)
    m_fom = min(100, n_matched / max(n_exp, n_ref) * 200)  # 匹配率×200
    
    # 4. 总分
    total_fom = d_fom * d_weight + i_fom * i_weight + m_fom * m_weight
    
    return {
        'd_fom': round(d_fom, 1),
        'i_fom': round(i_fom, 1),
        'm_fom': round(m_fom, 1),
        'total_fom': round(total_fom, 1),
        'n_matched': n_matched,
        'avg_delta_d': round(avg_delta_d, 3)
    }


# =============================================================================
# 算法 3: Hanawalt 检索
# =============================================================================

def hanawalt_search(
    exp_peaks: List[Tuple[float, float]],
    mineral_db: Dict,
    top_n: int = 3,
    wavelength: float = 1.5406,
) -> List[Dict]:
    """
    Hanawalt 检索算法 — 基于最强峰匹配
    
    参数:
        exp_peaks: 实验峰 [(d, I), ...]
        mineral_db: 矿物数据库 {formula: {'name': str, 'peaks': [(d, I), ...]}}
        top_n: 使用前几个最强峰
        
    返回:
        [{'name': str, 'formula': str, 'hanawalt_score': float, 'n_matched': int}, ...]
    """
    if not exp_peaks or not mineral_db:
        return []
    
    # 按强度排序，取最强top_n个峰
    sorted_exp = sorted(exp_peaks, key=lambda x: x[1], reverse=True)[:top_n]
    exp_d_list = [d for d, _ in sorted_exp]
    
    results = []
    
    for formula, info in mineral_db.items():
        ref_peaks = info.get('peaks', [])
        if not ref_peaks:
            continue
        
        # 按强度排序参考峰
        sorted_ref = sorted(ref_peaks, key=lambda x: x[1], reverse=True)[:top_n]
        ref_d_list = [d for d, _ in sorted_ref]
        
        # 匹配最强峰
        matched = 0
        total_score = 0
        
        for exp_d in exp_d_list:
            best_match_score = 0
            
            for ref_d in ref_d_list:
                # 计算匹配分数
                error_pct = abs(exp_d - ref_d) / ref_d * 100
                tolerance = adaptive_tolerance(ref_d, wavelength) * 100
                
                if error_pct <= tolerance:
                    score = max(0, 100 - error_pct * 2)  # 误差每1%扣2分
                    if score > best_match_score:
                        best_match_score = score
            
            if best_match_score > 0:
                matched += 1
                total_score += best_match_score
        
        if matched > 0:
            hanawalt_score = total_score / matched if matched > 0 else 0
            results.append({
                'name': info.get('name', formula),
                'formula': formula,
                'hanawalt_score': round(hanawalt_score, 1),
                'n_matched': matched
            })
    
    # 按分数排序
    results.sort(key=lambda x: x['hanawalt_score'], reverse=True)
    return results[:10]  # 返回前10个


# =============================================================================
# 算法 4: 归一化图谱相似度
# =============================================================================

def normalize_pattern_similarity(
    pattern1: np.ndarray,
    pattern2: np.ndarray,
    method: str = 'correlation'
) -> float:
    """
    计算两个XRD图谱的相似度
    
    参数:
        pattern1, pattern2: 强度数组
        method: 'correlation' (相关系数) 或 'euclidean' (欧氏距离)
        
    返回:
        相似度分数 (0-1)
    """
    if len(pattern1) != len(pattern2):
        # 重采样到相同长度
        from scipy import interpolate
        x_old = np.linspace(0, 1, len(pattern1))
        x_new = np.linspace(0, 1, len(pattern2))
        
        if len(pattern1) < len(pattern2):
            f = interpolate.interp1d(x_old, pattern1, kind='linear', fill_value='extrapolate')
            pattern1 = f(x_new)
        else:
            f = interpolate.interp1d(x_old, pattern2, kind='linear', fill_value='extrapolate')
            pattern2 = f(x_new)
    
    # 归一化
    p1_norm = (pattern1 - np.mean(pattern1)) / (np.std(pattern1) or 1)
    p2_norm = (pattern2 - np.mean(pattern2)) / (np.std(pattern2) or 1)
    
    if method == 'correlation':
        # 相关系数
        corr = np.corrcoef(p1_norm, p2_norm)[0, 1]
        return max(0, (corr + 1) / 2)  # 映射到0-1
    
    elif method == 'euclidean':
        # 欧氏距离（转换为相似度）
        distance = np.sqrt(np.sum((p1_norm - p2_norm) ** 2))
        max_distance = np.sqrt(len(p1_norm) * 4)  # 最大可能距离
        similarity = 1 - distance / max_distance
        return max(0, min(1, similarity))
    
    else:
        raise ValueError(f"未知方法: {method}")


# =============================================================================
# 算法 5: Scherrer 晶粒尺寸计算
# =============================================================================

def scherrer_grain_size(
    fwhm: float,
    two_theta: float,
    wavelength: float = 1.5406,
    shape_factor: float = 0.9
) -> Dict:
    """
    Scherrer 公式计算晶粒尺寸
    
    参数:
        fwhm: 半高宽 (度)
        two_theta: 峰位 (度)
        wavelength: 波长 (Å)
        shape_factor: 形状因子 (通常0.9)
        
    返回:
        {'size_nm': float, 'theta_rad': float, 'beta_rad': float}
    """
    # 转换为弧度
    theta_rad = math.radians(two_theta / 2)
    beta_rad = math.radians(fwhm)
    
    # Scherrer 公式: D = Kλ / (β cosθ)
    size_angstrom = shape_factor * wavelength / (beta_rad * math.cos(theta_rad))
    size_nm = size_angstrom / 10  # Å 转 nm
    
    return {
        'size_nm': round(size_nm, 2),
        'theta_rad': theta_rad,
        'beta_rad': beta_rad,
        'note': f'晶粒尺寸 ≈ {size_nm:.1f} nm (K={shape_factor}, λ={wavelength}Å)'
    }


def scherrer_analysis(peaks: List[Dict]) -> List[Dict]:
    """
    批量Scherrer分析
    
    参数:
        peaks: [{'twotheta': float, 'fwhm': float, 'intensity': float}, ...]
        
    返回:
        每个峰的分析结果
    """
    results = []
    for peak in peaks:
        fwhm = peak.get('fwhm', 0.1)
        two_theta = peak.get('twotheta', 20.0)
        
        if fwhm <= 0:
            continue