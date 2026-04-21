"""
Sci-XRD Pro - 统一工具模块
d-spacing 与 2θ 角度转换、自适应容差等通用功能
"""

import math
import numpy as np
from typing import Tuple

# 默认波长 (Cu K-alpha)
DEFAULT_WAVELENGTH = 1.5406


def d_to_twotheta(d: float, wavelength: float = DEFAULT_WAVELENGTH) -> float:
    """
    d-spacing 转 2θ 角度
    
    Args:
        d: d-spacing (Å)
        wavelength: X射线波长 (Å)
        
    Returns:
        2θ 角度 (度)
    """
    if d <= 0:
        return 180.0
    sin_theta = wavelength / (2 * d)
    if sin_theta >= 1.0:
        return 180.0
    return math.degrees(2 * math.asin(sin_theta))


def twotheta_to_d(twotheta: float, wavelength: float = DEFAULT_WAVELENGTH) -> float:
    """
    2θ 角度转 d-spacing
    
    Args:
        twotheta: 2θ 角度 (度)
        wavelength: X射线波长 (Å)
        
    Returns:
        d-spacing (Å)
    """
    if twotheta <= 0:
        return float('inf')
    theta_rad = math.radians(twotheta / 2)
    if theta_rad >= math.pi / 2:
        return 0.0
    return wavelength / (2 * math.sin(theta_rad))


def adaptive_tolerance(d: float, wavelength: float = DEFAULT_WAVELENGTH) -> float:
    """
    自适应容差 - 根据角度自动调整匹配精度
    低角度容差宽松，高角度容差严格
    
    Args:
        d: d-spacing (Å)
        wavelength: X射线波长 (Å)
        
    Returns:
        容差值 (Å)
    """
    try:
        sin_theta = wavelength / (2 * d)
        if sin_theta >= 1.0:
            return 0.02
        two_theta = math.degrees(2 * math.asin(sin_theta))
        
        if two_theta >= 80:
            return 0.008
        elif two_theta >= 60:
            return 0.010
        elif two_theta >= 40:
            return 0.015
        elif two_theta >= 20:
            return 0.020
        else:
            return 0.025
    except:
        return 0.02


def adaptive_tolerance_percent(d: float, wavelength: float = DEFAULT_WAVELENGTH) -> float:
    """
    自适应容差百分比
    
    Args:
        d: d-spacing (Å)
        wavelength: X射线波长 (Å)
        
    Returns:
        容差百分比 (%)
    """
    return adaptive_tolerance(d, wavelength) / d * 100


def convert_angles_to_d(angles: np.ndarray, wavelength: float = DEFAULT_WAVELENGTH) -> np.ndarray:
    """批量转换 2θ -> d"""
    return np.array([twotheta_to_d(a, wavelength) for a in angles])


def convert_d_to_angles(d_spacing: np.ndarray, wavelength: float = DEFAULT_WAVELENGTH) -> np.ndarray:
    """批量转换 d -> 2θ"""
    return np.array([d_to_twotheta(d, wavelength) for d in d_spacing])


def parse_angle_intensity_data(content: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    解析角度-强度数据
    
    Args:
        content: 文件内容或数据字符串
        
    Returns:
        (angles, intensities) 元组
    """
    lines = content.strip().split('\n')
    angles = []
    intensities = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        parts = line.split()
        if len(parts) >= 2:
            try:
                angle = float(parts[0])
                intensity = float(parts[1])
                angles.append(angle)
                intensities.append(intensity)
            except ValueError:
                continue
    
    return np.array(angles), np.array(intensities)


def normalize_intensity(intensity: np.ndarray) -> np.ndarray:
    """归一化强度到 0-100"""
    min_i = np.min(intensity)
    max_i = np.max(intensity)
    if max_i == min_i:
        return np.ones_like(intensity) * 50
    return (intensity - min_i) / (max_i - min_i) * 100


def smooth_data(data: np.ndarray, window: int = 5) -> np.ndarray:
    """简单移动平均平滑"""
    if window <= 1:
        return data
    smoothed = np.convolve(data, np.ones(window)/window, mode='same')
    return smoothed


def find_baseline(intensity: np.ndarray, window: int = 50) -> np.ndarray:
    """估算基线 (使用最小值滑动窗口)"""
    n = len(intensity)
    baseline = np.zeros(n)
    
    half = window // 2
    for i in range(n):
        start = max(0, i - half)
        end = min(n, i + half + 1)
        baseline[i] = np.min(intensity[start:end])
    
    return baseline


def remove_baseline(intensity: np.ndarray, baseline: np.ndarray = None) -> np.ndarray:
    """去除基线"""
    if baseline is None:
        baseline = find_baseline(intensity)
    return intensity - baseline


def calculate_fwhm(peak_position: float, intensities: np.ndarray, x_data: np.ndarray) -> float:
    """计算半高宽"""
    half_max_idx = np.argmax(intensities)
    half_max = intensities[half_max_idx] / 2
    
    # 向左找半高点
    left_idx = half_max_idx
    for i in range(half_max_idx, 0, -1):
        if intensities[i] <= half_max:
            left_idx = i
            break
    
    # 向右找半高点
    right_idx = half_max_idx
    for i in range(half_max_idx, len(intensities)):
        if intensities[i] <= half_max:
            right_idx = i
            break
    
    if left_idx < right_idx:
        return x_data[right_idx] - x_data[left_idx]
    return 0.1


def estimate_noise_level(intensity: np.ndarray) -> float:
    """估算噪声水平"""
    # 使用高频成分的标准差作为噪声估计
    if len(intensity) < 10:
        return 0.0
    
    # 计算相邻点差异的标准差
    diff = np.abs(np.diff(intensity))
    return np.std(diff)
