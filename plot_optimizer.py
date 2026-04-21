#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表显示优化模块
解决中文乱码、角标显示、曲线颜色等问题
"""

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import rcParams
import numpy as np
from pathlib import Path
import sys
import os

class PlotOptimizer:
    """图表显示优化器"""
    
    def __init__(self):
        self._setup_matplotlib()
        self._create_styles()
    
    def _setup_matplotlib(self):
        """设置matplotlib配置"""
        # 设置中文字体
        if sys.platform == 'win32':
            # Windows系统
            font_paths = [
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
                'C:/Windows/Fonts/simsun.ttc',  # 宋体
                'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
            ]
        else:
            # Linux/Mac系统
            font_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # 文泉驿微米黑
                '/System/Library/Fonts/PingFang.ttc',  # macOS苹方
            ]
        
        # 尝试添加中文字体
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    matplotlib.font_manager.fontManager.addfont(font_path)
                    font_name = matplotlib.font_manager.FontProperties(fname=font_path).get_name()
                    rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans', 'Arial']
                    rcParams['axes.unicode_minus'] = False
                    print(f"已设置中文字体: {font_name}")
                    break
                except Exception as e:
                    print(f"设置字体失败 {font_path}: {e}")
        
        # 基础配置
        rcParams.update({
            'figure.dpi': 150,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight',
            'savefig.pad_inches': 0.1,
            
            # 线条和标记
            'lines.linewidth': 1.5,
            'lines.markersize': 4,
            'lines.markeredgewidth': 0.5,
            
            # 坐标轴
            'axes.linewidth': 1.0,
            'axes.grid': False,  # 默认关闭网格
            'axes.edgecolor': 'black',
            'axes.labelcolor': 'black',
            'axes.titlecolor': 'black',
            
            # 刻度
            'xtick.color': 'black',
            'ytick.color': 'black',
            'xtick.direction': 'in',  # 刻度朝内
            'ytick.direction': 'in',
            'xtick.major.width': 1.0,
            'ytick.major.width': 1.0,
            'xtick.minor.width': 0.5,
            'ytick.minor.width': 0.5,
            
            # 图例
            'legend.frameon': True,
            'legend.framealpha': 0.8,
            'legend.edgecolor': 'black',
            'legend.fontsize': 9,
            
            # 图形
            'figure.figsize': [8, 6],
            'figure.titlesize': 12,
            'figure.titleweight': 'normal',
        })
    
    def _create_styles(self):
        """创建预定义样式"""
        self.styles = {
            'publication': {
                'figure.dpi': 600,
                'savefig.dpi': 600,
                'font.size': 10,
                'axes.titlesize': 11,
                'axes.labelsize': 10,
                'xtick.labelsize': 9,
                'ytick.labelsize': 9,
                'legend.fontsize': 9,
                'lines.linewidth': 1.2,
                'axes.linewidth': 0.8,
            },
            'presentation': {
                'figure.dpi': 150,
                'font.size': 12,
                'axes.titlesize': 14,
                'axes.labelsize': 12,
                'xtick.labelsize': 11,
                'ytick.labelsize': 11,
                'legend.fontsize': 11,
                'lines.linewidth': 2.0,
                'axes.linewidth': 1.2,
            },
            'black_white': {
                'lines.color': 'black',
                'axes.prop_cycle': plt.cycler('color', ['black', 'gray', 'dimgray', 'lightgray']),
            }
        }
    
    def apply_style(self, style_name='publication'):
        """应用预定义样式"""
        if style_name in self.styles:
            rcParams.update(self.styles[style_name])
            print(f"已应用样式: {style_name}")
    
    def create_xrd_plot(self, x_data, y_data, title="XRD Pattern", 
                       xlabel="2θ (°)", ylabel="Intensity (a.u.)",
                       style='publication', black_curves=True):
        """
        创建优化的XRD图表
        
        参数:
            x_data: X轴数据 (2θ角度)
            y_data: Y轴数据 (强度)
            title: 图表标题
            xlabel: X轴标签
            ylabel: Y轴标签
            style: 样式名称 ('publication', 'presentation', 'black_white')
            black_curves: 是否使用黑色曲线
        """
        # 应用样式
        self.apply_style(style)
        
        # 创建图形和坐标轴
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 绘制曲线
        if black_curves:
            ax.plot(x_data, y_data, color='black', linewidth=1.5, label='XRD Pattern')
        else:
            ax.plot(x_data, y_data, linewidth=1.5, label='XRD Pattern')
        
        # 设置坐标轴
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, pad=15)
        
        # 设置刻度
        ax.tick_params(axis='both', which='major', direction='in', length=6, width=1)
        ax.tick_params(axis='both', which='minor', direction='in', length=3, width=0.5)
        
        # 设置网格（可选）
        # ax.grid(True, linestyle='--', alpha=0.3, linewidth=0.5)
        
        # 自动调整刻度范围
        ax.set_xlim(left=min(x_data), right=max(x_data))
        
        # 优化布局
        plt.tight_layout()
        
        return fig, ax
    
    def add_peaks(self, ax, peak_positions, peak_intensities, 
                 color='red', marker='o', label='Peaks'):
        """添加峰位标记"""
        ax.scatter(peak_positions, peak_intensities, 
                  color=color, marker=marker, s=50, 
                  edgecolors='black', linewidth=0.5,
                  zorder=5, label=label)
        return ax
    
    def add_phase_labels(self, ax, phase_positions, phase_names, 
                        y_position=None, color='blue', rotation=90):
        """添加物相标签"""
        if y_position is None:
            y_position = ax.get_ylim()[1] * 0.95
        
        for pos, name in zip(phase_positions, phase_names):
            ax.text(pos, y_position, name, 
                   color=color, fontsize=9, rotation=rotation,
                   ha='center', va='top',
                   bbox=dict(boxstyle='round,pad=0.2', 
                            facecolor='white', 
                            edgecolor='gray', 
                            alpha=0.8))
        return ax
    
    def add_inset(self, fig, ax, x_range, y_range, 
                 loc='upper right', width=0.3, height=0.3):
        """添加局部放大插图"""
        from mpl_toolkits.axes_grid1.inset_locator import inset_axes
        
        # 创建插图坐标轴
        ax_inset = inset_axes(ax, width=width, height=height, loc=loc)
        
        # 设置插图范围
        ax_inset.set_xlim(x_range)
        ax_inset.set_ylim(y_range)
        
        # 绘制原始数据
        x_data = ax.lines[0].get_xdata()
        y_data = ax.lines[0].get_ydata()
        
        mask = (x_data >= x_range[0]) & (x_data <= x_range[1])
        ax_inset.plot(x_data[mask], y_data[mask], color='black', linewidth=1)
        
        # 设置插图样式
        ax_inset.tick_params(axis='both', labelsize=8)
        ax_inset.set_xlabel('2θ (°)', fontsize=8)
        ax_inset.set_ylabel('Intensity', fontsize=8)
        
        # 添加矩形标记主图区域
        rect = plt.Rectangle((x_range[0], y_range[0]), 
                            x_range[1] - x_range[0], 
                            y_range[1] - y_range[0],
                            fill=False, color='red', linestyle='--', linewidth=1)
        ax.add_patch(rect)
        
        return ax_inset
    
    def save_plot(self, fig, filename, formats=None, dpi=300):
        """
        保存图表为多种格式
        
        参数:
            fig: matplotlib图形对象
            filename: 基础文件名（不含扩展名）
            formats: 保存格式列表，如 ['png', 'pdf', 'svg']
            dpi: 分辨率
        """
        if formats is None:
            formats = ['png', 'pdf']
        
        saved_files = []
        
        for fmt in formats:
            output_file = f"{filename}.{fmt}"
            
            try:
                fig.savefig(output_file, dpi=dpi, bbox_inches='tight')
                saved_files.append(output_file)
                print(f"图表已保存: {output_file}")
            except Exception as e:
                print(f"保存 {fmt} 格式失败: {e}")
        
        return saved_files
    
    def create_multi_plot(self, data_list, titles=None, 
                         ncols=2, figsize=(15, 10), sharex=True, sharey=True):
        """创建多子图布局"""
        n_plots = len(data_list)
        nrows = (n_plots + ncols - 1) // ncols
        
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, 
                                figsize=figsize,
                                sharex=sharex, sharey=sharey,
                                constrained_layout=True)
        
        # 如果只有一行，确保axes是二维数组
        if nrows == 1:
            axes = axes.reshape(1, -1)
        
        # 绘制每个子图
        for idx, (x_data, y_data) in enumerate(data_list):
            row = idx // ncols
            col = idx % ncols
            
            ax = axes[row, col]
            ax.plot(x_data, y_data, color='black', linewidth=1)
            
            if titles and idx < len(titles):
                ax.set_title(titles[idx], fontsize=10)
            
            ax.tick_params(axis='both', labelsize=8)
            ax.grid(True, alpha=0.3, linewidth=0.5)
        
        # 隐藏多余的子图
        for idx in range(n_plots, nrows * ncols):
            row = idx // ncols
            col = idx % ncols
            axes[row, col].axis('off')
        
        return fig, axes
    
    def optimize_text_rendering(self):
        """优化文本渲染，解决角标和特殊字符问题"""
        # 设置数学字体
        rcParams['mathtext.default'] = 'regular'
        rcParams['mathtext.fontset'] = 'stix'
        
        # 特殊字符映射
        special_chars = {
            'alpha': 'α',
            'beta': 'β',
            'gamma': 'γ',
            'theta': 'θ',
            'lambda': 'λ',
            'degree': '°',
            'angstrom': 'Å',
            'micro': 'μ',
        }
        
        return special_chars

# 使用示例
if __name__ == "__main__":
    # 创建优化器
    optimizer = PlotOptimizer()
    
    # 生成示例数据
    x = np.linspace(5, 80, 1000)
    y = np.exp(-0.01 * (x - 40)**2) * 1000 + np.random.normal(0, 50, 1000)
    
    # 创建XRD图表
    fig, ax = optimizer.create_xrd_plot(
        x, y, 
        title="示例 XRD 谱图",
        xlabel="2θ (°)",
        ylabel="强度 (a.u.)",
        style='publication',
        black_curves=True
    )
    
    # 添加峰位标记
    peak_positions = [20.0, 40.0, 60.0]
    peak_intensities = [800, 1000, 600]
    optimizer.add_peaks(ax, peak_positions, peak_intensities, label='检测峰')
    
    # 添加物相标签
    phase_names = ['Quartz', 'Calcite', 'Feldspar']
    optimizer.add_phase_labels(ax, peak_positions, phase_names)
    
    # 添加图例
    ax.legend(loc='upper right', fontsize=9)
    
    # 保存图表
    optimizer.save_plot(fig, "optimized_xrd_plot", formats=['png', 'pdf'])
    
    # 显示图表
    plt.show()
    
    print("图表优化示例完成！")