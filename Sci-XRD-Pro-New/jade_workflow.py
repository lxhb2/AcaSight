#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD-Pro - Jade风格完整处理流程
===============================

标准XRD数据处理流程（类似MDI Jade）：
1. 数据导入 (RAW/TXT/CSV)
2. 数据预处理 (平滑/背景扣除/Kα2剥离)
3. 寻峰 (Peak Search)
4. 物相鉴定 (Search/Match)
5. 定量分析 (Quantitative)
6. 绘图输出 (Origin风格)

使用方法:
    python jade_workflow.py <数据文件>
    python jade_workflow.py --demo
"""

import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.algorithms.peak_detection import PeakDetector, Peak
from core.algorithms.phase_matching_v2 import HighAccuracyPhaseMatcher
from utils.origin_plotter import OriginPlotter


@dataclass
class XRDData:
    """XRD数据结构"""
    angles: np.ndarray      # 2θ角度
    intensities: np.ndarray # 强度
    wavelength: float = 1.5406  # Cu Kα1
    sample_name: str = ""
    
    @property
    def d_spacings(self) -> np.ndarray:
        """计算d值"""
        theta = np.radians(self.angles / 2)
        return self.wavelength / (2 * np.sin(theta))


class JadeStyleProcessor:
    """
    Jade风格XRD处理器
    
    功能:
    - 数据导入 (支持多种格式)
    - 预处理 (平滑/背景扣除)
    - 寻峰 (多种算法)
    - 物相鉴定 (PDF数据库匹配)
    - 定量分析 (RIR方法)
    - Origin风格绘图
    """
    
    def __init__(self):
        self.data: Optional[XRDData] = None
        self.peaks: List[Peak] = []
        self.phases: List[Dict] = []
        self.background: Optional[np.ndarray] = None
        self.smoothed: Optional[np.ndarray] = None
        
        # 初始化组件
        self.peak_detector = PeakDetector(method='scipy', sensitivity=0.1)
        self.phase_matcher = HighAccuracyPhaseMatcher()
    
    # ==================== 1. 数据导入 ====================
    
    def load_data(self, filepath: str, format: str = 'auto') -> 'JadeStyleProcessor':
        """
        加载XRD数据
        
        Args:
            filepath: 文件路径
            format: 'auto', 'txt', 'csv', 'raw', 'xy'
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        # 自动检测格式
        if format == 'auto':
            ext = path.suffix.lower()
            if ext == '.raw':
                format = 'raw'
            elif ext == '.csv':
                format = 'csv'
            else:
                format = 'txt'
        
        # 读取数据
        if format == 'raw':
            angles, intensities = self._load_bruker_raw(filepath)
        elif format == 'csv':
            data = np.loadtxt(filepath, delimiter=',', skiprows=1)
            angles, intensities = data[:, 0], data[:, 1]
        else:
            # TXT/XY格式
            data = np.loadtxt(filepath)
            if data.shape[1] >= 2:
                angles, intensities = data[:, 0], data[:, 1]
            else:
                raise ValueError("数据格式错误，需要2列数据")
        
        self.data = XRDData(
            angles=angles,
            intensities=intensities,
            sample_name=path.stem
        )
        
        print(f"[导入] {filepath}")
        print(f"  数据点: {len(angles)}")
        print(f"  角度范围: {angles.min():.2f}° - {angles.max():.2f}°")
        
        return self
    
    def _load_bruker_raw(self, filepath: str) -> Tuple[np.ndarray, np.ndarray]:
        """加载Bruker RAW文件"""
        from core.io.bruker_raw_parser import BrukerRawParser
        parser = BrukerRawParser()
        result = parser.parse(filepath)
        return result['angles'], result['intensities']
    
    # ==================== 2. 数据预处理 ====================
    
    def smooth(self, window: int = 5, polyorder: int = 2) -> 'JadeStyleProcessor':
        """
        Savitzky-Golay平滑
        
        Args:
            window: 窗口大小 (奇数)
            polyorder: 多项式阶数
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        from scipy.signal import savgol_filter
        
        if window % 2 == 0:
            window += 1
        
        self.smoothed = savgol_filter(
            self.data.intensities, 
            window_length=window, 
            polyorder=polyorder
        )
        
        print(f"[平滑] 窗口={window}, 阶数={polyorder}")
        return self
    
    def remove_background(self, iterations: int = 50, window: int = 50) -> 'JadeStyleProcessor':
        """
        背景扣除 (SNIP算法)
        
        Args:
            iterations: 迭代次数
            window: 窗口大小
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        y = self.smoothed if self.smoothed is not None else self.data.intensities
        
        # SNIP背景扣除
        background = self._snip_background(y, iterations, window)
        self.background = background
        
        # 扣除背景
        if self.smoothed is not None:
            self.smoothed = y - background
            self.smoothed[self.smoothed < 0] = 0
        
        print(f"[背景扣除] 迭代={iterations}")
        return self
    
    def _snip_background(self, y: np.ndarray, iterations: int, window: int) -> np.ndarray:
        """SNIP背景扣除算法"""
        n = len(y)
        background = y.copy()
        
        for _ in range(iterations):
            for i in range(n):
                start = max(0, i - window)
                end = min(n, i + window + 1)
                local_min = np.min(background[start:end])
                background[i] = min(background[i], local_min)
        
        return background
    
    # ==================== 3. 寻峰 ====================
    
    def search_peaks(self, threshold: float = 0.1, 
                     min_intensity: float = 0.0) -> List[Peak]:
        """
        寻峰
        
        Args:
            threshold: 检测阈值 (相对强度)
            min_intensity: 最小绝对强度
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        # 使用平滑/背景扣除后的数据
        if self.smoothed is not None:
            y = self.smoothed
        else:
            y = self.data.intensities
        
        # 设置检测器参数
        self.peak_detector.sensitivity = threshold
        
        # 检测峰
        self.peaks = self.peak_detector.detect(self.data.angles, y)
        
        # 过滤低强度峰
        if min_intensity > 0:
            self.peaks = [p for p in self.peaks if p.intensity >= min_intensity]
        
        print(f"[寻峰] 检测到 {len(self.peaks)} 个峰")
        
        # 显示前10个峰
        for i, peak in enumerate(self.peaks[:10], 1):
            print(f"  {i:2d}. 2theta={peak.position:6.2f}deg, d={peak.d_spacing:6.4f}A, I={peak.intensity:8.1f}")
        
        return self.peaks
    
    # ==================== 4. 物相鉴定 ====================
    
    def identify_phases(self, top_n: int = 10, 
                        min_score: float = 30.0) -> List[Dict]:
        """
        物相鉴定 (Search/Match)
        
        Args:
            top_n: 返回前N个匹配
            min_score: 最小匹配分数
        """
        if not self.peaks:
            print("[警告] 未检测到峰，请先执行寻峰")
            return []
        
        # 准备峰数据
        exp_peaks = [(p.d_spacing, p.intensity) for p in self.peaks]
        
        # 执行匹配
        results = self.phase_matcher._fom_match(exp_peaks, top_n=top_n, min_score=min_score)
        
        self.phases = []
        for result in results:
            self.phases.append({
                'name': result.phase.name,
                'formula': result.phase.formula,
                'score': result.score,
                'd_fom': result.d_fom,
                'i_fom': result.i_fom,
                'pdf_number': result.phase.pdf_number,
                'space_group': result.phase.space_group,
                'matched_peaks': result.matched_peaks
            })
        
        print(f"\n[物相鉴定] 找到 {len(self.phases)} 个匹配")
        
        for i, phase in enumerate(self.phases[:5], 1):
            print(f"  {i}. {phase['name']} ({phase['formula']})")
            print(f"     PDF: {phase['pdf_number']}, Score: {phase['score']:.1f}%")
        
        return self.phases
    
    # ==================== 5. 定量分析 ====================
    
    def quantitative_analysis(self) -> Dict:
        """
        定量分析 (RIR方法)
        
        Returns:
            各相含量估计
        """
        if not self.phases:
            print("[警告] 未鉴定物相，请先执行物相鉴定")
            return {}
        
        print("\n[定量分析]")
        
        # 简化版：基于匹配峰强度估算
        results = {}
        total_intensity = sum(p.intensity for p in self.peaks)
        
        for phase in self.phases[:3]:
            # 计算该相的峰强度占比
            phase_intensity = 0
            for mp in phase.get('matched_peaks', []):
                phase_intensity += mp.get('intensity', 0)
            
            if total_intensity > 0:
                estimated = (phase_intensity / total_intensity) * 100
            else:
                estimated = 0
            
            results[phase['name']] = {
                'estimated_wt': estimated,
                'confidence': phase['score'] / 100
            }
            
            print(f"  {phase['name']}: ~{estimated:.1f} wt%")
        
        return results
    
    # ==================== 6. 绘图输出 ====================
    
    def plot_origin_style(self, output: str = "xrd_result.png",
                          show_peaks: bool = True,
                          show_phases: bool = True) -> str:
        """
        Origin风格绘图
        
        Args:
            output: 输出文件名
            show_peaks: 是否标注峰位
            show_phases: 是否显示物相
        """
        if self.data is None:
            raise ValueError("请先加载数据")
        
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        matplotlib.rcParams['axes.unicode_minus'] = False
        
        # 创建图像
        fig, ax = plt.subplots(figsize=(14, 8), dpi=150)
        
        # 绘制数据
        x = self.data.angles
        y = self.smoothed if self.smoothed is not None else self.data.intensities
        
        ax.plot(x, y, 'b-', linewidth=1.5, label='XRD Data')
        
        # 绘制背景
        if self.background is not None:
            ax.plot(x, self.background, 'r--', linewidth=1, alpha=0.5, label='Background')
        
        # 标注峰位
        if show_peaks and self.peaks:
            for peak in self.peaks[:15]:
                ax.annotate(f'{peak.d_spacing:.3f}A',
                           xy=(peak.position, peak.intensity),
                           xytext=(peak.position, peak.intensity + 30),
                           fontsize=8, ha='center',
                           arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))
        
        # 添加物相标注
        if show_phases and self.phases:
            text = "Identified Phases:\n"
            for i, phase in enumerate(self.phases[:3], 1):
                text += f"{i}. {phase['name']} ({phase['score']:.0f}%)\n"
            ax.text(0.95, 0.95, text, transform=ax.transAxes, fontsize=10,
                   va='top', ha='right', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 设置标签
        ax.set_xlabel('2θ (°)')
        ax.set_ylabel('Intensity (a.u.)')
        ax.set_title(f'XRD Pattern - {self.data.sample_name}')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        
        # 保存
        plt.tight_layout()
        plt.savefig(output, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"\n[绘图] 保存: {output}")
        
        return output
    
    # ==================== 完整流程 ====================
    
    def process(self, filepath: str, 
                smooth_window: int = 5,
                bg_iterations: int = 50,
                peak_threshold: float = 0.1) -> 'JadeStyleProcessor':
        """
        完整处理流程
        
        Args:
            filepath: 数据文件路径
            smooth_window: 平滑窗口
            bg_iterations: 背景扣除迭代
            peak_threshold: 寻峰阈值
        """
        print("=" * 60)
        print("Sci-XRD-Pro - Jade风格处理流程")
        print("=" * 60)
        
        # 1. 数据导入
        self.load_data(filepath)
        
        # 2. 预处理
        self.smooth(window=smooth_window)
        self.remove_background(iterations=bg_iterations)
        
        # 3. 寻峰
        self.search_peaks(threshold=peak_threshold)
        
        # 4. 物相鉴定
        self.identify_phases()
        
        # 5. 定量分析
        self.quantitative_analysis()
        
        # 6. 绘图
        output_name = Path(filepath).stem + "_result.png"
        self.plot_origin_style(output=output_name)
        
        print("\n" + "=" * 60)
        print("处理完成!")
        print("=" * 60)
        
        return self


def demo():
    """演示完整流程"""
    print("=" * 60)
    print("Sci-XRD-Pro - Jade风格处理演示")
    print("=" * 60)
    
    # 创建模拟数据
    angles = np.linspace(5, 65, 2000)
    intensities = np.ones_like(angles) * 50
    
    # 添加石英峰 (PDF#46-1045)
    quartz_peaks = [
        (4.257, 100), (3.343, 35), (2.458, 12),
        (2.282, 12), (2.237, 6), (2.128, 5)
    ]
    
    for d, i in quartz_peaks:
        two_theta = 2 * np.degrees(np.arcsin(1.5406 / (2 * d)))
        if 5 <= two_theta <= 65:
            width = 0.15 + np.random.random() * 0.05
            intensities += i * 8 * np.exp(-((angles - two_theta)**2) / (2 * width**2))
    
    # 添加方解石峰 (PDF#47-1743)
    calcite_peaks = [
        (3.035, 100), (2.495, 18), (2.285, 18),
        (1.913, 17), (1.875, 10)
    ]
    
    for d, i in calcite_peaks:
        two_theta = 2 * np.degrees(np.arcsin(1.5406 / (2 * d)))
        if 5 <= two_theta <= 65:
            width = 0.12 + np.random.random() * 0.04
            intensities += i * 5 * np.exp(-((angles - two_theta)**2) / (2 * width**2))
    
    # 添加噪声
    intensities += np.random.normal(0, 5, len(angles))
    intensities[intensities < 0] = 0
    
    # 保存临时文件
    temp_file = "demo_xrd_data.txt"
    np.savetxt(temp_file, np.column_stack([angles, intensities]), 
               fmt='%.4f', header='2theta Intensity')
    
    # 处理
    processor = JadeStyleProcessor()
    processor.process(temp_file, smooth_window=7, peak_threshold=0.05)
    
    # 清理
    import os
    os.remove(temp_file)
    
    return processor


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Jade风格XRD处理')
    parser.add_argument('file', nargs='?', help='XRD数据文件')
    parser.add_argument('--demo', action='store_true', help='运行演示')
    parser.add_argument('--smooth', type=int, default=5, help='平滑窗口')
    parser.add_argument('--bg', type=int, default=50, help='背景扣除迭代')
    parser.add_argument('--threshold', type=float, default=0.1, help='寻峰阈值')
    
    args = parser.parse_args()
    
    if args.demo or not args.file:
        demo()
    else:
        processor = JadeStyleProcessor()
        processor.process(
            args.file,
            smooth_window=args.smooth,
            bg_iterations=args.bg,
            peak_threshold=args.threshold
        )
