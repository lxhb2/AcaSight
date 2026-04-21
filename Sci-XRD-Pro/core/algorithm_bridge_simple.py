"""
简化版算法桥接模块
直接使用修复后的高级算法
"""

import numpy as np
from typing import List, Dict, Tuple, Optional

# 导入修复后的高级算法
try:
    from core.fixed_advanced_algorithms import (
        d_to_twotheta,
        twotheta_to_d,
        derivative_peak_detection,
        calculate_fom,
        hanawalt_search,
        normalize_pattern_similarity,
        scherrer_grain_size,
        adaptive_tolerance
    )
    ADVANCED_ALGORITHMS_AVAILABLE = True
    print("[算法桥接] 高级算法加载成功")
except ImportError as e:
    ADVANCED_ALGORITHMS_AVAILABLE = False
    print(f"[算法桥接] 警告: 无法导入高级算法: {e}")
    print("[算法桥接] 使用简化算法")

# 导入当前项目的算法
try:
    from core.peak_detector import NonDestructivePeakDetector
    from core.phase_matcher import PhaseMatcher
    SIMPLE_ALGORITHMS_AVAILABLE = True
except ImportError:
    SIMPLE_ALGORITHMS_AVAILABLE = False
    print("[算法桥接] 警告: 无法导入简化算法")


class AdvancedAlgorithmBridge:
    """高级算法桥接器"""
    
    def __init__(self):
        self.use_advanced = ADVANCED_ALGORITHMS_AVAILABLE
        
        if SIMPLE_ALGORITHMS_AVAILABLE:
            self.simple_detector = NonDestructivePeakDetector()
            self.phase_matcher = PhaseMatcher()
        else:
            self.simple_detector = None
            self.phase_matcher = None
            
        print(f"[算法桥接] 初始化完成 - 高级算法: {self.use_advanced}")
        
    def detect_peaks(self, angles, intensities, method='auto'):
        """
        检测峰位（智能选择算法）
        
        Args:
            angles: 2θ角度数组
            intensities: 强度数组
            method: 'auto'（自动选择）, 'advanced', 'simple'
            
        Returns:
            峰信息列表
        """
        if method == 'advanced' or (method == 'auto' and self.use_advanced):
            # 使用高级算法
            try:
                peaks = derivative_peak_detection(
                    angles, intensities,
                    smooth_window=5,
                    min_prominence=0.02,
                    min_distance=10
                )
                
                # 转换为标准格式
                formatted_peaks = []
                for peak in peaks:
                    formatted_peaks.append({
                        'position': peak['twotheta'],
                        'd_spacing': peak['d'],
                        'intensity': peak['intensity'],
                        'fwhm': peak['fwhm'],
                        'prominence': peak.get('prominence', 0),
                        'method': 'derivative_advanced',
                        'advanced': True
                    })
                
                print(f"[算法桥接] 使用高级算法检测到 {len(formatted_peaks)} 个峰")
                return formatted_peaks
                
            except Exception as e:
                print(f"[算法桥接] 高级算法失败: {e}")
                if self.simple_detector:
                    method = 'simple'
                else:
                    raise
        
        if method == 'simple' and self.simple_detector:
            # 使用简化算法
            peaks = self.simple_detector.detect_peaks(angles, intensities, method='wavelet')
            
            # 添加算法标记
            for peak in peaks:
                peak['method'] = 'wavelet_simple'
                peak['advanced'] = False
                
            print(f"[算法桥接] 使用简化算法检测到 {len(peaks)} 个峰")
            return peaks
            
        # 如果没有算法可用，返回空列表
        print("[算法桥接] 警告: 没有可用的峰检测算法")
        return []
        
    def match_phases(self, peaks, mineral_db=None, method='auto'):
        """
        匹配物相
        
        Args:
            peaks: 峰信息列表
            mineral_db: 矿物数据库
            method: 'auto', 'fom', 'hanawalt', 'simple'
            
        Returns:
            匹配结果列表
        """
        if not peaks:
            return []
            
        # 准备峰数据
        peak_data = []
        for peak in peaks:
            if 'd_spacing' in peak:
                d = peak['d_spacing']
            elif 'position' in peak:
                d = twotheta_to_d(peak['position'])
            else:
                continue
                
            intensity = peak.get('intensity', 100)
            peak_data.append((d, intensity))
        
        if not peak_data:
            return []
            
        # 如果没有提供数据库，使用内置数据库
        if mineral_db is None:
            mineral_db = self._get_default_mineral_db()
            
        results = []
        
        if method in ['auto', 'fom'] and self.use_advanced:
            # 使用FOM算法
            try:
                for formula, info in mineral_db.items():
                    ref_peaks = info.get('peaks', [])
                    fom_result = calculate_fom(peak_data, ref_peaks)
                    
                    if fom_result['n_matched'] >= 2 and fom_result['total_fom'] >= 30:
                        results.append({
                            'name': info.get('name', formula),
                            'formula': formula,
                            'score': fom_result['total_fom'],
                            'method': 'fom',
                            'n_matched': fom_result['n_matched'],
                            'avg_delta_d': fom_result['avg_delta_d']
                        })
                        
                print(f"[算法桥接] FOM算法找到 {len(results)} 个匹配")
                
            except Exception as e:
                print(f"[算法桥接] FOM算法失败: {e}")
                if method == 'auto':
                    method = 'hanawalt'
        
        if method in ['auto', 'hanawalt'] and self.use_advanced:
            # 使用Hanawalt算法
            try:
                hanawalt_results = hanawalt_search(peak_data, mineral_db, top_n=3)
                
                for hr in hanawalt_results:
                    results.append({
                        'name': hr['name'],
                        'formula': hr['formula'],
                        'score': hr['hanawalt_score'],
                        'method': 'hanawalt',
                        'n_matched': hr['n_matched']
                    })
                    
                print(f"[算法桥接] Hanawalt算法找到 {len(hanawalt_results)} 个匹配")
                
            except Exception as e:
                print(f"[算法桥接] Hanawalt算法失败: {e}")
                if method == 'auto' and self.phase_matcher:
                    method = 'simple'
        
        if method in ['auto', 'simple'] and self.phase_matcher:
            # 使用简化算法
            simple_results = self.phase_matcher.match_phases(peaks)
            
            for sr in simple_results:
                results.append({
                    'name': sr.get('name', 'Unknown'),
                    'formula': sr.get('formula', ''),
                    'score': sr.get('score', 0),
                    'method': 'simple',
                    'n_matched': sr.get('n_matched', 0)
                })
                
            print(f"[算法桥接] 简化算法找到 {len(simple_results)} 个匹配")
        
        # 去重和排序
        unique_results = {}
        for result in results:
            key = result['formula']
            if key not in unique_results or result['score'] > unique_results[key]['score']:
                unique_results[key] = result
        
        final_results = list(unique_results.values())
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        return final_results[:10]  # 返回前10个
        
    def calculate_grain_size(self, peak_fwhm, two_theta, wavelength=1.5406):
        """计算晶粒尺寸"""
        if self.use_advanced:
            try:
                return scherrer_grain_size(peak_fwhm, two_theta, wavelength)
            except Exception as e:
                print(f"[算法桥接] 高级晶粒尺寸计算失败: {e}")
        
        # 简化版本
        try:
            theta_rad = np.radians(two_theta / 2)
            beta_rad = np.radians(peak_fwhm)
            k = 0.9  # 形状因子
            size_angstrom = k * wavelength / (beta_rad * np.cos(theta_rad))
            size_nm = size_angstrom / 10
            
            return {
                'size_nm': round(size_nm, 2),
                'theta_rad': theta_rad,
                'beta_rad': beta_rad,
                'note': f'晶粒尺寸 ≈ {size_nm:.1f} nm (简化计算)'
            }
        except:
            return {'size_nm': 0, 'note': '计算失败'}
    
    def _get_default_mineral_db(self):
        """获取默认矿物数据库"""
        return {
            'SiO2': {
                'name': 'Quartz',
                'peaks': [(4.26, 25), (3.34, 100), (2.46, 15), (2.28, 10), (1.82, 25)]
            },
            'CaCO3': {
                'name': 'Calcite',
                'peaks': [(3.04, 100), (2.49, 40), (2.28, 18), (1.91, 12), (1.87, 12)]
            },
            'FeS2': {
                'name': 'Pyrite',
                'peaks': [(2.71, 100), (2.42, 85), (2.09, 60), (1.63, 50), (1.56, 40)]
            },
            'CuFeS2': {
                'name': 'Chalcopyrite',
                'peaks': [(3.03, 100), (1.86, 83), (1.59, 20), (2.62, 7), (1.21, 7)]
            },
            'Fe2O3': {
                'name': 'Hematite',
                'peaks': [(2.70, 100), (2.52, 60), (1.69, 40), (1.48, 30), (1.45, 25)]
            }
        }


# 测试函数
def test_bridge():
    """测试桥接模块"""
    print("=" * 70)
    print("测试算法桥接模块")
    print("=" * 70)
    
    # 创建桥接器
    bridge = AdvancedAlgorithmBridge()
    
    # 生成测试数据
    angles = np.linspace(5, 65, 1000)
    intensities = np.ones_like(angles) * 100
    
    # 添加石英峰
    quartz_d = [4.26, 3.34, 2.46, 2.28, 1.82]
    for d in quartz_d:
        two_theta = d_to_twotheta(d)
        idx = np.argmin(np.abs(angles - two_theta))
        intensities[idx] = 500
        # 添加一些宽度
        for i in range(-5, 6):
            if 0 <= idx + i < len(intensities):
                intensities[idx + i] = max(intensities[idx + i], 400 - abs(i) * 50)
    
    # 添加噪声
    intensities += np.random.normal(0, 20, len(angles))
    
    print(f"\n测试数据: {len(angles)} 个点")
    
    # 测试峰检测
    print("\n1. 测试峰检测...")
    peaks = bridge.detect_peaks(angles, intensities, method='auto')
    print(f"   检测到 {len(peaks)} 个峰")
    
    for i, peak in enumerate(peaks[:5]):
        print(f"   峰{i+1}: 2θ={peak['position']:.2f}°, d={peak['d_spacing']:.4f}Å, "
              f"I={peak['intensity']:.0f}, 方法={peak['method']}")
    
    # 测试物相匹配
    print("\n2. 测试物相匹配...")
    if peaks:
        matches = bridge.match_phases(peaks, method='auto')
        print(f"   找到 {len(matches)} 个匹配")
        
        for match in matches[:3]:
            print(f"   - {match['name']} ({match['formula']}): {match['score']:.1f}分 "
                  f"(方法: {match['method']})")
    
    # 测试晶粒尺寸计算
    print("\n3. 测试晶粒尺寸计算...")
    if peaks:
        peak = peaks[0]
        result = bridge.calculate_grain_size(peak.get('fwhm', 0.2), peak['position'])
        print(f"   晶粒尺寸: {result.get('size_nm', 0):.1f} nm")
        print(f"   说明: {result.get('note', '')}")
    
    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70)


if __name__ == '__main__':
    test_bridge()
