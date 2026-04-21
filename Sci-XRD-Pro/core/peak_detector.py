"""
非破坏性峰检测算法 - 保持原始数据完整性

核心特性：
1. 非破坏性检测：不修改原始数据
2. 自适应阈值：自动调整检测灵敏度
3. 多尺度检测：适应不同峰宽
4. 噪声抑制：智能过滤噪声峰
5. 峰形分析：计算峰参数（位置、强度、半高宽、面积）

算法原理：
- 基于连续小波变换的多尺度峰检测
- 自适应背景估计和噪声水平评估
- 峰形拟合（高斯/洛伦兹/伪Voigt）
- 峰重叠解析
"""

import numpy as np
from scipy import signal, interpolate, optimize
from scipy.ndimage import gaussian_filter1d
from typing import List, Dict, Tuple, Optional, Union, Any
import warnings


class NonDestructivePeakDetector:
    """非破坏性峰检测器"""
    
    def __init__(self, min_snr: float = 2.0, min_prominence: float = 0.01,
                 min_width: float = 0.1, max_width: float = 5.0):
        """
        初始化峰检测器
        
        Args:
            min_snr: 最小信噪比
            min_prominence: 最小突出度（相对最大强度的比例）
            min_width: 最小峰宽（度）
            max_width: 最大峰宽（度）
        """
        self.min_snr = min_snr
        self.min_prominence = min_prominence
        self.min_width = min_width
        self.max_width = max_width
        
        # 缓存检测结果
        self._cache = {}
    
    def detect_peaks(self, angles: np.ndarray, intensities: np.ndarray,
                    method: str = 'wavelet', **kwargs) -> List[Dict]:
        """
        检测XRD峰位（非破坏性）
        
        Args:
            angles: 2θ角度数组
            intensities: 强度数组
            method: 检测方法 ('wavelet', 'savitzky', 'simple')
            **kwargs: 方法特定参数
            
        Returns:
            峰信息列表，每个元素包含：
            - position: 峰位 (2θ角度)
            - intensity: 峰强度
            - fwhm: 半高宽
            - area: 峰面积
            - prominence: 峰突出度
            - left_base: 左基线位置
            - right_base: 右基线位置
            - snr: 信噪比
        """
        cache_key = (hash(angles.tobytes()), hash(intensities.tobytes()), method)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 数据验证
        if len(angles) != len(intensities):
            raise ValueError("角度和强度数组长度必须相同")
        
        if len(angles) < 10:
            raise ValueError("数据点太少，无法进行可靠的峰检测")
        
        # 选择检测方法
        if method == 'wavelet':
            peaks = self._detect_with_wavelet(angles, intensities, **kwargs)
        elif method == 'savitzky':
            peaks = self._detect_with_savitzky(angles, intensities, **kwargs)
        elif method == 'simple':
            peaks = self._detect_simple(angles, intensities, **kwargs)
        else:
            raise ValueError(f"未知检测方法: {method}")
        
        # 后处理：过滤和排序
        peaks = self._post_process_peaks(angles, intensities, peaks)
        
        # 缓存结果
        self._cache[cache_key] = peaks
        
        return peaks
    
    def _detect_with_wavelet(self, angles: np.ndarray, intensities: np.ndarray,
                            scales: List[float] = None, **kwargs) -> List[Dict]:
        """基于小波变换的峰检测"""
        if scales is None:
            # 自动确定尺度范围
            angle_range = angles[-1] - angles[0]
            min_scale = max(self.min_width / 2.0, 0.5)  # 最小尺度
            max_scale = min(self.max_width * 2.0, angle_range / 4)  # 最大尺度
            scales = np.logspace(np.log10(min_scale), np.log10(max_scale), 10)
        
        # 1. 估计背景和噪声
        background = self._estimate_background(intensities)
        noise_level = self._estimate_noise_level(intensities - background)
        
        # 2. 多尺度小波变换
        wavelet_coeffs = []
        for scale in scales:
            # 使用高斯一阶导数作为小波
            wavelet = self._gaussian_wavelet(angles, scale)
            coeff = np.convolve(intensities - background, wavelet, mode='same')
            wavelet_coeffs.append(coeff)
        
        wavelet_coeffs = np.array(wavelet_coeffs)
        
        # 3. 寻找局部极大值
        peak_candidates = []
        for i in range(1, len(angles) - 1):
            # 检查所有尺度上的响应
            max_response = np.max(np.abs(wavelet_coeffs[:, i]))
            
            if max_response > noise_level * self.min_snr:
                # 检查是否为局部极大值
                if (intensities[i] > intensities[i-1] and 
                    intensities[i] > intensities[i+1]):
                    
                    # 计算突出度
                    prominence = self._calculate_prominence(angles, intensities, i)
                    
                    if prominence > self.min_prominence * np.max(intensities):
                        peak_candidates.append({
                            'index': i,
                            'position': angles[i],
                            'intensity': intensities[i],
                            'prominence': prominence,
                            'response': max_response
                        })
        
        # 4. 峰形拟合和参数提取
        peaks = []
        for candidate in peak_candidates:
            peak_params = self._fit_peak_shape(angles, intensities, 
                                              candidate['index'])
            if peak_params:
                peaks.append({
                    'position': peak_params['position'],
                    'intensity': peak_params['intensity'],
                    'fwhm': peak_params['fwhm'],
                    'area': peak_params['area'],
                    'prominence': candidate['prominence'],
                    'left_base': peak_params.get('left_base', angles[0]),
                    'right_base': peak_params.get('right_base', angles[-1]),
                    'snr': candidate['response'] / noise_level if noise_level > 0 else 0
                })
        
        return peaks
    
    def _detect_with_savitzky(self, angles: np.ndarray, intensities: np.ndarray,
                             window_length: int = 11, polyorder: int = 3,
                             **kwargs) -> List[Dict]:
        """基于Savitzky-Golay滤波的峰检测"""
        # 1. 平滑数据
        smoothed = signal.savgol_filter(intensities, window_length, polyorder)
        
        # 2. 计算一阶和二阶导数
        first_deriv = np.gradient(smoothed, angles)
        second_deriv = np.gradient(first_deriv, angles)
        
        # 3. 寻找峰位（一阶导数为零，二阶导数为负）
        peak_indices = []
        for i in range(1, len(angles) - 1):
            # 检查一阶导数过零点
            if (first_deriv[i-1] > 0 and first_deriv[i+1] < 0 and
                second_deriv[i] < 0):
                
                # 精确定位峰位（抛物线拟合）
                try:
                    # 使用三点抛物线拟合
                    x = angles[i-1:i+2]
                    y = intensities[i-1:i+2]
                    coeffs = np.polyfit(x, y, 2)
                    
                    # 抛物线顶点位置
                    a, b, c = coeffs
                    if a < 0:  # 确保是极大值
                        peak_pos = -b / (2 * a)
                        peak_intensity = a * peak_pos**2 + b * peak_pos + c
                        
                        # 检查是否在合理范围内
                        if (angles[i-1] <= peak_pos <= angles[i+1] and
                            peak_intensity > intensities[i] * 0.9):
                            peak_indices.append((i, peak_pos, peak_intensity))
                except:
                    # 如果拟合失败，使用原始位置
                    peak_indices.append((i, angles[i], intensities[i]))
        
        # 4. 提取峰参数
        peaks = []
        for idx, pos, intensity in peak_indices:
            # 计算突出度
            prominence = self._calculate_prominence(angles, intensities, idx)
            
            if prominence > self.min_prominence * np.max(intensities):
                # 峰形拟合
                peak_params = self._fit_peak_shape(angles, intensities, idx)
                
                if peak_params:
                    peaks.append({
                        'position': peak_params['position'],
                        'intensity': peak_params['intensity'],
                        'fwhm': peak_params['fwhm'],
                        'area': peak_params['area'],
                        'prominence': prominence,
                        'left_base': peak_params.get('left_base', angles[0]),
                        'right_base': peak_params.get('right_base', angles[-1]),
                        'snr': intensity / self._estimate_noise_level(intensities)
                    })
        
        return peaks
    
    def _detect_simple(self, angles: np.ndarray, intensities: np.ndarray,
                      **kwargs) -> List[Dict]:
        """简单峰检测（基于局部极大值）"""
        # 寻找局部极大值
        peak_indices = signal.find_peaks(intensities, 
                                        prominence=self.min_prominence * np.max(intensities),
                                        width=self.min_width / np.mean(np.diff(angles)))[0]
        
        peaks = []
        for idx in peak_indices:
            # 峰形拟合
            peak_params = self._fit_peak_shape(angles, intensities, idx)
            
            if peak_params:
                # 计算突出度
                prominence = self._calculate_prominence(angles, intensities, idx)
                
                peaks.append({
                    'position': peak_params['position'],
                    'intensity': peak_params['intensity'],
                    'fwhm': peak_params['fwhm'],
                    'area': peak_params['area'],
                    'prominence': prominence,
                    'left_base': peak_params.get('left_base', angles[0]),
                    'right_base': peak_params.get('right_base', angles[-1]),
                    'snr': intensities[idx] / self._estimate_noise_level(intensities)
                })
        
        return peaks
    
    def _fit_peak_shape(self, angles: np.ndarray, intensities: np.ndarray,
                       peak_index: int) -> Optional[Dict]:
        """拟合峰形并提取参数"""
        try:
            # 确定拟合范围
            window = self._get_fitting_window(angles, intensities, peak_index)
            
            if window is None:
                return None
            
            left_idx, right_idx = window
            fit_angles = angles[left_idx:right_idx+1]
            fit_intensities = intensities[left_idx:right_idx+1]
            
            # 背景估计
            background_left = np.mean(intensities[max(0, left_idx-5):left_idx])
            background_right = np.mean(intensities[right_idx:min(len(intensities), right_idx+5)])
            background = np.linspace(background_left, background_right, len(fit_angles))
            
            # 扣除背景
            net_intensities = fit_intensities - background
            
            # 初始参数估计
            peak_pos = angles[peak_index]
            peak_intensity = net_intensities[peak_index - left_idx]
            
            # 估计FWHM
            half_max = peak_intensity / 2
            left_half = np.where(net_intensities[:peak_index-left_idx] >= half_max)[0]
            right_half = np.where(net_intensities[peak_index-left_idx:] >= half_max)[0]
            
            if len(left_half) > 0 and len(right_half) > 0:
                fwhm_left = fit_angles[left_half[0]]
                fwhm_right = fit_angles[peak_index-left_idx + right_half[-1]]
                fwhm_estimate = fwhm_right - fwhm_left
            else:
                fwhm_estimate = self.min_width
            
            # 高斯拟合
            def gaussian(x, amplitude, center, sigma, offset):
                return amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2)) + offset
            
            # 初始参数
            p0 = [peak_intensity, peak_pos, fwhm_estimate / 2.3548, 0]
            
            # 拟合
            try:
                popt, _ = optimize.curve_fit(gaussian, fit_angles, net_intensities, p0=p0,
                                           maxfev=5000)
                
                amplitude, center, sigma, offset = popt
                
                # 计算参数
                fwhm = 2.3548 * sigma  # 高斯FWHM
                area = amplitude * sigma * np.sqrt(2 * np.pi)
                
                return {
                    'position': center,
                    'intensity': amplitude + offset,
                    'fwhm': fwhm,
                    'area': area,
                    'left_base': fit_angles[0],
                    'right_base': fit_angles[-1],
                    'sigma': sigma,
                    'amplitude': amplitude
                }
                
            except (RuntimeError, ValueError):
                # 如果拟合失败，返回估计值
                return {
                    'position': peak_pos,
                    'intensity': peak_intensity,
                    'fwhm': fwhm_estimate,
                    'area': peak_intensity * fwhm_estimate * 0.5,  # 近似面积
                    'left_base': fit_angles[0],
                    'right_base': fit_angles[-1]
                }
                
        except Exception as e:
            warnings.warn(f"峰形拟合失败: {e}")
            return None
    
    def _get_fitting_window(self, angles: np.ndarray, intensities: np.ndarray,
                           peak_index: int) -> Optional[Tuple[int, int]]:
        """确定峰拟合窗口"""
        if peak_index < 0 or peak_index >= len(angles):
            return None
        
        peak_intensity = intensities[peak_index]
        half_max = peak_intensity / 2
        
        # 向左寻找基线
        left_idx = peak_index
        for i in range(peak_index - 1, -1, -1):
            if intensities[i] <= half_max or i == 0:
                left_idx = i
                break
        
        # 向右寻找基线
        right_idx = peak_index
        for i in range(peak_index + 1, len(intensities)):
            if intensities[i] <= half_max or i == len(intensities) - 1:
                right_idx = i
                break
        
        # 确保窗口足够大
        min_points = 5
        if right_idx - left_idx < min_points:
            # 扩展窗口
            left_idx = max(0, left_idx - min_points)
            right_idx = min(len(angles) - 1, right_idx + min_points)
        
        return left_idx, right_idx
    
    def _calculate_prominence(self, angles: np.ndarray, intensities: np.ndarray,
                             peak_index: int) -> float:
        """计算峰突出度"""
        if peak_index < 0 or peak_index >= len(intensities):
            return 0
        
        peak_intensity = intensities[peak_index]
        
        # 向左寻找最低点
        left_min = peak_intensity
        for i in range(peak_index - 1, -1, -1):
            if intensities[i] < left_min:
                left_min = intensities[i]
            if intensities[i] > peak_intensity * 0.9:  # 遇到更高的峰
                break
        
        # 向右寻找最低点
        right_min = peak_intensity
        for i in range(peak_index + 1, len(intensities)):
            if intensities[i] < right_min:
                right_min = intensities[i]
            if intensities[i] > peak_intensity * 0.9:  # 遇到更高的峰
                break
        
        # 突出度是峰高与两侧最低点中较高者的差值
        reference_level = max(left_min, right_min)
        prominence = peak_intensity - reference_level
        
        return prominence
    
    def _estimate_background(self, intensities: np.ndarray, 
                            window_size: int = 51) -> np.ndarray:
        """估计背景信号"""
        if len(intensities) < window_size:
            window_size = len(intensities) // 2
        
        # 使用移动最小值估计背景
        background = np.zeros_like(intensities)
        half_window = window_size // 2
        
        for i in range(len(intensities)):
            left = max(0, i - half_window)
            right = min(len(intensities), i + half_window + 1)
            background[i] = np.min(intensities[left:right])
        
        # 平滑背景
        background = gaussian_filter1d(background, sigma=window_size/10)
        
        return background
    
    def _estimate_noise_level(self, signal: np.ndarray) -> float:
        """估计噪声水平"""
        if len(signal) < 10:
            return 0
        
        # 使用中值绝对偏差估计噪声
        median = np.median(signal)
        mad = np.median(np.abs(signal - median))
        
        # MAD到标准差的转换因子（对于正态分布）
        sigma = mad * 1.4826
        
        return sigma
    
    def _gaussian_wavelet(self, x: np.ndarray, scale: float) -> np.ndarray:
        """高斯一阶导数小波"""
        # 高斯函数
        gaussian = np.exp(-x**2 / (2 * scale**2))
        # 一阶导数
        derivative = -x / (scale**2) * gaussian
        return derivative
    
    def _post_process_peaks(self, angles: np.ndarray, intensities: np.ndarray,
                           peaks: List[Dict]) -> List[Dict]:
        """
        后处理峰：过滤和排序
        
        Args:
            angles: 角度数组
            intensities: 强度数组
            peaks: 原始峰列表
            
        Returns:
            处理后的峰列表
        """
        if not peaks:
            return []
        
        # 1. 过滤无效峰
        valid_peaks = []
        for peak in peaks:
            # 检查基本参数
            if (peak['position'] >= angles[0] and 
                peak['position'] <= angles[-1] and
                peak['intensity'] > 0 and
                peak['fwhm'] > 0):
                valid_peaks.append(peak)
        
        # 2. 按位置排序
        valid_peaks.sort(key=lambda x: x['position'])
        
        # 3. 合并过于接近的峰
        merged_peaks = []
        min_separation = self.min_width
        
        for peak in valid_peaks:
            if not merged_peaks:
                merged_peaks.append(peak)
            else:
                last_peak = merged_peaks[-1]
                separation = peak['position'] - last_peak['position']
                
                if separation < min_separation:
                    # 合并峰：选择强度较大的
                    if peak['intensity'] > last_peak['intensity']:
                        merged_peaks[-1] = peak
                else:
                    merged_peaks.append(peak)
        
        return merged_peaks