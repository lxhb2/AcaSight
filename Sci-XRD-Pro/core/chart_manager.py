"""
双图层图表管理器 - 保持原始峰值形状的核心组件

核心设计：
1. 原始图层 (Original Layer): 黑色实线，永不修改
2. 分析图层 (Analysis Layer): 半透明叠加，显示处理结果
3. 标记图层 (Marker Layer): 红色虚线+数字标签，可独立控制

特性：
- 原始数据完整性保护
- 非破坏性分析结果展示
- 图层独立控制（显示/隐藏）
- 智能标注避免重叠
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import List, Dict, Tuple, Optional, Any
import warnings


class DualLayerChartManager:
    """双图层图表管理器"""
    
    def __init__(self, figsize=(10, 6), dpi=100):
        """
        初始化双图层图表管理器
        
        Args:
            figsize: 图表尺寸
            dpi: 分辨率
        """
        self.fig: Figure = plt.figure(figsize=figsize, dpi=dpi)
        self.ax: Axes = self.fig.add_subplot(111)
        
        # 三个独立图层
        self.original_layer = None          # 原始数据图层
        self.analysis_layer = None          # 分析结果图层
        self.marker_layers = []             # 标记图层列表
        
        # 图层控制状态
        self.layers_visible = {
            'original': True,
            'analysis': True,
            'markers': True
        }
        
        # 样式配置
        self.styles = {
            'original': {
                'color': 'black',
                'linewidth': 1.5,
                'linestyle': '-',
                'alpha': 1.0,
                'label': '原始数据',
                'zorder': 10  # 最高层级
            },
            'analysis': {
                'color': 'blue',
                'linewidth': 1.0,
                'linestyle': '-',
                'alpha': 0.5,
                'label': '分析结果',
                'zorder': 5   # 中间层级
            },
            'peak_marker': {
                'color': 'red',
                'linewidth': 0.8,
                'linestyle': '--',
                'alpha': 0.6,
                'zorder': 6
            },
            'peak_label': {
                'fontsize': 9,
                'color': 'red',
                'bbox': dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.3),
                'ha': 'center',
                'va': 'bottom',
                'zorder': 7
            }
        }
        
        # 初始化图表样式
        self._setup_chart_style()
    
    def _setup_chart_style(self):
        """设置图表基本样式"""
        self.ax.set_xlabel('2θ (度)', fontsize=12)
        self.ax.set_ylabel('强度 (a.u.)', fontsize=12)
        self.ax.set_title('XRD图谱分析', fontsize=14, fontweight='bold')
        self.ax.grid(True, linestyle='--', alpha=0.3)
        self.ax.legend(loc='upper right')
        
        # 设置科学计数法
        self.ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
    
    def plot_original_data(self, x_data: np.ndarray, y_data: np.ndarray, 
                          label: str = None, **kwargs):
        """
        绘制原始数据（永不修改的图层）
        
        Args:
            x_data: X轴数据（2θ角度）
            y_data: Y轴数据（强度）
            label: 数据标签
            **kwargs: 额外样式参数
        """
        # 清除之前的原始图层（如果有）
        if self.original_layer is not None:
            self.original_layer.remove()
        
        # 合并样式
        style = self.styles['original'].copy()
        if label:
            style['label'] = label
        style.update(kwargs)
        
        # 绘制原始数据
        self.original_layer, = self.ax.plot(
            x_data, y_data,
            color=style['color'],
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
            label=style['label'],
            zorder=style['zorder']
        )
        
        # 自动调整坐标轴范围
        self._auto_adjust_axes(x_data, y_data)
        
        # 刷新图表
        self.fig.canvas.draw_idle()
        
        return self.original_layer
    
    def add_analysis_overlay(self, x_data: np.ndarray, y_processed: np.ndarray,
                            label: str = None, **kwargs):
        """
        添加分析结果叠加层
        
        Args:
            x_data: X轴数据（与原始数据相同）
            y_processed: 处理后的Y轴数据
            label: 分析结果标签
            **kwargs: 额外样式参数
        """
        # 清除之前的分析图层（如果有）
        if self.analysis_layer is not None:
            self.analysis_layer.remove()
        
        # 合并样式
        style = self.styles['analysis'].copy()
        if label:
            style['label'] = label
        style.update(kwargs)
        
        # 绘制分析结果叠加层
        self.analysis_layer, = self.ax.plot(
            x_data, y_processed,
            color=style['color'],
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
            label=style['label'],
            zorder=style['zorder']
        )
        
        # 刷新图表
        self.fig.canvas.draw_idle()
        
        return self.analysis_layer
    
    def add_peak_markers(self, peaks: List[Dict], smart_labeling: bool = True):
        """
        添加峰标记（独立图层）
        
        Args:
            peaks: 峰信息列表，每个元素包含：
                  - 'position': 峰位 (2θ角度)
                  - 'intensity': 峰强度
                  - 'index': 峰编号（可选）
                  - 'mineral': 匹配的矿物（可选）
            smart_labeling: 是否启用智能标注（避免标签重叠）
        """
        # 清除之前的标记图层
        self.clear_markers()
        
        if not peaks:
            return []
        
        # 智能标注：避免标签重叠
        if smart_labeling:
            peaks_to_label = self._smart_peak_selection(peaks)
        else:
            peaks_to_label = peaks
        
        # 添加峰标记
        for i, peak in enumerate(peaks_to_label):
            # 峰位垂直线
            vline = self.ax.axvline(
                x=peak['position'],
                color=self.styles['peak_marker']['color'],
                linestyle=self.styles['peak_marker']['linestyle'],
                linewidth=self.styles['peak_marker']['linewidth'],
                alpha=self.styles['peak_marker']['alpha'],
                zorder=self.styles['peak_marker']['zorder']
            )
            
            # 峰标签
            label_text = self._format_peak_label(peak, i)
            
            # 计算标签位置（避免重叠）
            label_x, label_y = self._calculate_label_position(peak, i, peaks_to_label)
            
            label = self.ax.text(
                label_x, label_y,
                label_text,
                fontsize=self.styles['peak_label']['fontsize'],
                color=self.styles['peak_label']['color'],
                bbox=self.styles['peak_label']['bbox'],
                ha=self.styles['peak_label']['ha'],
                va=self.styles['peak_label']['va'],
                zorder=self.styles['peak_label']['zorder']
            )
            
            self.marker_layers.extend([vline, label])
        
        # 刷新图表
        self.fig.canvas.draw_idle()
        
        return self.marker_layers
    
    def _smart_peak_selection(self, peaks: List[Dict], max_labels: int = 15) -> List[Dict]:
        """
        智能峰选择：避免标签重叠
        
        Args:
            peaks: 所有检测到的峰
            max_labels: 最大标注数量
        
        Returns:
            选择标注的峰列表
        """
        if len(peaks) <= max_labels:
            return peaks
        
        # 按强度排序
        sorted_peaks = sorted(peaks, key=lambda x: x['intensity'], reverse=True)
        
        # 选择最强的前N个峰
        selected = sorted_peaks[:max_labels]
        
        # 按位置排序
        selected = sorted(selected, key=lambda x: x['position'])
        
        return selected
    
    def _format_peak_label(self, peak: Dict, index: int) -> str:
        """格式化峰标签"""
        if 'mineral' in peak and peak['mineral']:
            # 如果有矿物信息，显示矿物简写
            mineral_abbr = peak['mineral'][:10]  # 截断前10个字符
            return f"{index+1}\n{mineral_abbr}"
        else:
            # 只显示峰编号
            return str(index + 1)
    
    def _calculate_label_position(self, peak: Dict, index: int, 
                                 all_peaks: List[Dict]) -> Tuple[float, float]:
        """计算标签位置，避免重叠"""
        # 获取当前Y轴范围
        y_min, y_max = self.ax.get_ylim()
        y_range = y_max - y_min
        
        # 基础位置：峰顶上方10%的位置
        base_y = peak['intensity'] * 1.1
        
        # 检查与相邻峰的标签是否可能重叠
        min_distance = 0.05 * (self.ax.get_xlim()[1] - self.ax.get_xlim()[0])
        
        for j, other_peak in enumerate(all_peaks):
            if j == index:
                continue
            
            if abs(peak['position'] - other_peak['position']) < min_distance:
                # 如果峰位太近，调整标签高度
                if j < index:
                    base_y = base_y * 1.15  # 向上调整
                else:
                    base_y = base_y * 0.95  # 向下调整
        
        # 确保标签在图表范围内
        label_y = min(max(base_y, y_min + 0.05 * y_range), y_max - 0.05 * y_range)
        
        return peak['position'], label_y
    
    def _auto_adjust_axes(self, x_data: np.ndarray, y_data: np.ndarray):
        """自动调整坐标轴范围"""
        if len(x_data) == 0 or len(y_data) == 0:
            return
        
        x_min, x_max = np.min(x_data), np.max(x_data)
        y_min, y_max = np.min(y_data), np.max(y_data)
        
        # 添加边距
        x_margin = (x_max - x_min) * 0.05
        y_margin = (y_max - y_min) * 0.1
        
        self.ax.set_xlim(x_min - x_margin, x_max + x_margin)
        self.ax.set_ylim(y_min - y_margin, y_max + y_margin)
    
    def clear_markers(self):
        """清除所有标记图层"""
        for marker in self.marker_layers:
            try:
                marker.remove()
            except:
                pass
        self.marker_layers.clear()
    
    def clear_analysis(self):
        """清除分析图层"""
        if self.analysis_layer is not None:
            self.analysis_layer.remove()
            self.analysis_layer = None
    
    def clear_all(self):
        """清除所有图层（保留原始数据）"""
        self.clear_analysis()
        self.clear_markers()
    
    def toggle_layer(self, layer_name: str, visible: bool = None):
        """
        切换图层显示状态
        
        Args:
            layer_name: 图层名称 ('original', 'analysis', 'markers')
            visible: 是否显示（None表示切换）
        """
        if layer_name not in self.layers_visible:
            raise ValueError(f"未知图层: {layer_name}")
        
        if visible is None:
            self.layers_visible[layer_name] = not self.layers_visible[layer_name]
        else:
            self.layers_visible[layer_name] = visible
        
        # 更新图层可见性
        self._update_layer_visibility()
    
    def _update_layer_visibility(self):
        """更新所有图层的可见性"""
        # 原始图层
        if self.original_layer is not None:
            self.original_layer.set_visible(self.layers_visible['original'])
        
        # 分析图层
        if self.analysis_layer is not None:
            self.analysis_layer.set_visible(self.layers_visible['analysis'])
        
        # 标记图层
        for marker in self.marker_layers:
            marker.set_visible(self.layers_visible['markers'])
        
        # 刷新图表
        self.fig.canvas.draw_idle()
    
    def save_figure(self, filename: str, dpi: int = 300, 
                   transparent: bool = False):
        """
        保存图表
        
        Args:
            filename: 保存路径
            dpi: 分辨率
            transparent: 是否透明背景
        """
        self.fig.savefig(filename, dpi=dpi, transparent=transparent,
                        bbox_inches='tight', pad_inches=0.1)
    
    def get_figure(self) -> Figure:
        """获取图表对象"""
        return self.fig
    
    def get_axes(self) -> Axes:
        """获取坐标轴对象"""
        return self.ax
    
    def update_styles(self, layer_type: str, **kwargs):
        """
        更新图层样式
        
        Args:
            layer_type: 图层类型 ('original', 'analysis', 'peak_marker', 'peak_label')
            **kwargs: 样式参数
        """
        if layer_type in self.styles:
            self.styles[layer_type].update(kwargs)
        else:
            raise ValueError(f"未知图层类型: {layer_type}")


# 测试函数
def test_dual_layer_chart():
    """测试双图层图表系统"""
    import numpy as np
    
    # 创建测试数据
    x = np.linspace(10, 80, 1000)
    y_original = np.exp(-(x-45)**2/(2*10**2)) + 0.5*np.exp(-(x-65)**2/(2*8**2)) + np.random.normal(0, 0.05, 1000)
    y_processed = y_original - 0.3  # 模拟处理后的数据
    
    # 创建峰数据
    peaks = [
        {'position': 45.0, 'intensity': 1.0, 'index': 1, 'mineral': 'Quartz'},
        {'position': 65.0, 'intensity': 0.8, 'index': 2, 'mineral': 'Calcite'},
        {'position': 35.0, 'intensity': 0.6, 'index': 3, 'mineral': 'Feldspar'},
        {'position': 55.0, 'intensity': 0.5, 'index': 4, 'mineral': 'Mica'},
    ]
    
    # 创建图表管理器
    chart = DualLayerChartManager()
    
    # 绘制原始数据
    chart.plot_original_data(x, y_original, label='原始XRD数据')
    
    # 添加分析结果
    chart.add_analysis_overlay(x, y_processed, label='背景扣除后')
    
    # 添加峰标记
    chart.add_peak_markers(peaks)
    
    # 测试图层控制
    print("测试图层控制...")
    chart.toggle_layer('analysis', False)  # 隐藏分析图层
    chart.toggle_layer('markers', False)   # 隐藏标记
    
    # 重新显示
    chart.toggle_layer('analysis', True)
    chart.toggle_layer('markers', True)
    
    # 保存图表
    chart.save_figure('test_chart.png')
    
    print("双图层图表系统测试完成！")
    
    return chart


if __name__ == '__main__':
    test_dual_layer_chart()