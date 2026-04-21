"""
增强版主窗口 - 完整XRD分析功能
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime

# PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QTextEdit,
    QGroupBox, QSplitter, QStatusBar, QToolBar, QMenuBar, QMenu,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QLineEdit, QProgressBar,
    QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QIcon, QFont

# Matplotlib集成
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# 导入核心模块
sys.path.append(str(Path(__file__).parent.parent))

from core.chart_manager import DualLayerChartManager
from core.enhanced_raw_parser import EnhancedRawDataParser
from core.peak_detector import NonDestructivePeakDetector
from core.phase_matcher import PhaseMatcher
from core.algorithm_lib import XRDAlgorithmLibrary
from core.simple_export_manager import SimpleExportManager as ExportManager


class AnalysisWorker(QThread):
    """分析工作线程"""
    
    progress_signal = pyqtSignal(int)
    message_signal = pyqtSignal(str)
    result_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, analysis_type, data, params):
        super().__init__()
        self.analysis_type = analysis_type
        self.data = data
        self.params = params
        
    def run(self):
        try:
            if self.analysis_type == 'peak_detection':
                self._run_peak_detection()
            elif self.analysis_type == 'phase_matching':
                self._run_phase_matching()
            elif self.analysis_type == 'full_analysis':
                self._run_full_analysis()
                
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def _run_peak_detection(self):
        """运行峰检测"""
        self.message_signal.emit("正在检测峰位...")
        
        detector = NonDestructivePeakDetector(
            min_snr=self.params.get('min_snr', 2.0),
            min_prominence=self.params.get('min_prominence', 0.01),
            min_width=self.params.get('min_width', 0.1),
            max_width=self.params.get('max_width', 5.0)
        )
        
        peaks = detector.detect_peaks(
            self.data['angles'],
            self.data['intensities'],
            method=self.params.get('method', 'wavelet')
        )
        
        self.progress_signal.emit(50)
        self.message_signal.emit(f"检测到 {len(peaks)} 个峰")
        
        result = {
            'peaks': peaks,
            'method': self.params.get('method', 'wavelet'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.result_signal.emit(result)
    
    def _run_phase_matching(self):
        """运行物相匹配"""
        self.message_signal.emit("正在匹配物相...")
        
        matcher = PhaseMatcher()
        phases = matcher.match_phases(
            self.params['peaks'],
            wavelength=self.params.get('wavelength', 1.5406),
            max_phases=self.params.get('max_phases', 5),
            min_confidence=self.params.get('min_confidence', 0.4)
        )
        
        self.progress_signal.emit(50)
        self.message_signal.emit(f"匹配到 {len(phases)} 个物相")
        
        result = {
            'phases': phases,
            'wavelength': self.params.get('wavelength', 1.5406),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.result_signal.emit(result)
    
    def _run_full_analysis(self):
        """运行完整分析"""
        results = {}
        
        # 1. 峰检测
        self.message_signal.emit("步骤1/3: 检测峰位...")
        detector = NonDestructivePeakDetector()
        peaks = detector.detect_peaks(
            self.data['angles'],
            self.data['intensities'],
            method='wavelet'
        )
        results['peaks'] = peaks
        self.progress_signal.emit(33)
        
        # 2. 物相匹配
        self.message_signal.emit("步骤2/3: 匹配物相...")
        matcher = PhaseMatcher()
        phases = matcher.match_phases(peaks, max_phases=3)
        results['phases'] = phases
        self.progress_signal.emit(66)
        
        # 3. 高级分析
        self.message_signal.emit("步骤3/3: 高级分析...")
        algo_lib = XRDAlgorithmLibrary()
        
        # 晶粒尺寸分析
        if peaks and len(peaks) >= 3:
            try:
                crystallite_sizes = []
                for peak in peaks[:5]:
                    theta_rad = np.radians(peak['position'] / 2)
                    fwhm_rad = np.radians(peak['fwhm'])
                    size = algo_lib.calculate_crystallite_size(fwhm_rad, theta_rad)
                    crystallite_sizes.append(size)
                
                if crystallite_sizes:
                    results['crystallite_size'] = {
                        'avg': np.mean(crystallite_sizes),
                        'std': np.std(crystallite_sizes),
                        'values': crystallite_sizes
                    }
            except:
                pass
        
        self.progress_signal.emit(100)
        self.message_signal.emit("分析完成")
        
        results['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.result_signal.emit(results)


class EnhancedXRDWindow(QMainWindow):
    """增强版XRD分析窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化核心模块
        self.raw_parser = EnhancedRawDataParser()
        self.peak_detector = NonDestructivePeakDetector()
        self.phase_matcher = PhaseMatcher()
        self.algo_lib = XRDAlgorithmLibrary()
        self.export_manager = ExportManager()
        self.chart_manager = None
        
        # 数据存储
        self.current_data = None
        self.current_filepath = None
        self.current_peaks = []
        self.current_phases = []
        self.analysis_results = {}
        
        # 分析线程
        self.analysis_worker = None
        
        # 初始化UI
        self.init_ui()
        
        # 设置窗口属性
        self.setWindowTitle("Sci-XRD Pro - 增强版")
        self.setGeometry(100, 100, 1400, 900)
        
        # 显示欢迎消息
        self.statusBar().showMessage("Sci-XRD Pro 增强版已就绪", 3000)
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 1. 创建菜单栏
        self.create_menu_bar()
        
        # 2. 创建工具栏
        self.create_tool_bar()
        
        # 3. 创建主工作区
        self.create_main_workspace(main_layout)
        
        # 4. 创建状态栏
        self.create_status_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        open_action = QAction("打开文件(&O)...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("导出结果(&E)...", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 分析菜单
        analysis_menu = menubar.addMenu("分析(&A)")
        
        peak_action = QAction("峰检测(&P)", self)
        peak_action.setShortcut("Ctrl+P")
        peak_action.triggered.connect(self.run_peak_detection)
        analysis_menu.addAction(peak_action)
        
        phase_action = QAction("物相匹配(&M)", self)
        phase_action.setShortcut("Ctrl+M")
        phase_action.triggered.connect(self.run_phase_matching)
        analysis_menu.addAction(phase_action)
        
        analysis_menu.addSeparator()
        
        full_analysis_action = QAction("完整分析(&F)", self)
        full_analysis_action.setShortcut("Ctrl+F")
        full_analysis_action.triggered.connect(self.run_full_analysis)
        analysis_menu.addAction(full_analysis_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")
        
        settings_action = QAction("分析设置(&S)...", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)
        
        tools_menu.addSeparator()
        
        background_action = QAction("背景扣除(&B)", self)
        background_action.triggered.connect(self.subtract_background)
        tools_menu.addAction(background_action)
        
        smoothing_action = QAction("数据平滑(&S)", self)
        smoothing_action.triggered.connect(self.smooth_data)
        tools_menu.addAction(smoothing_action)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        
        reset_view_action = QAction("重置视图(&R)", self)
        reset_view_action.triggered.connect(self.reset_chart_view)
        view_menu.addAction(reset_view_action)
        
        view_menu.addSeparator()
        
        show_peaks_action = QAction("显示/隐藏峰标记", self, checkable=True)
        show_peaks_action.setChecked(True)
        show_peaks_action.triggered.connect(self.toggle_peak_markers)
        view_menu.addAction(show_peaks_action)
        
        show_phases_action = QAction("显示/隐藏物相标签", self, checkable=True)
        show_phases_action.setChecked(True)
        show_phases_action.triggered.connect(self.toggle_phase_labels)
        view_menu.addAction(show_phases_action)
    
    def create_tool_bar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        # 文件操作
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # 分析操作
        peak_action = QAction("检测峰", self)
        peak_action.triggered.connect(self.run_peak_detection)
        toolbar.addAction(peak_action)
        
        phase_action = QAction("匹配物相", self)
        phase_action.triggered.connect(self.run_phase_matching)
        toolbar.addAction(phase_action)
        
        full_action = QAction("完整分析", self)
        full_action.triggered.connect(self.run_full_analysis)
        toolbar.addAction(full_action)
        
        toolbar.addSeparator()
        
        # 导出操作
        export_action = QAction("导出", self)
        export_action.triggered.connect(self.export_results)
        toolbar.addAction(export_action)
    
    def create_main_workspace(self, main_layout):
        """创建主工作区"""
        # 使用分割器
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 左侧：控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 文件信息组
        file_group = QGroupBox("文件信息")
        file_layout = QVBoxLayout()
        
        self.file_info_label = QLabel("未加载文件")
        self.file_info_label.setWordWrap(True)
        file_layout.addWidget(self.file_info_label)
        
        self.data_stats_label = QLabel("数据点: 0 | 角度范围: 0.0° - 0.0°")
        file_layout.addWidget(self.data_stats_label)
        
        file_group.setLayout(file_layout)
        left_layout.addWidget(file_group)
        
        # 分析参数组
        params_group = QGroupBox("分析参数")
        params_layout = QVBoxLayout()
        
        # 峰检测方法
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("检测方法:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems(["小波变换", "Savitzky-Golay", "简单检测"])
        method_layout.addWidget(self.method_combo)
        params_layout.addLayout(method_layout)
        
        # 灵敏度设置
        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.addWidget(QLabel("灵敏度:"))
        self.sensitivity_slider = QSpinBox()
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        sensitivity_layout.addWidget(self.sensitivity_slider)
        params_layout.addLayout(sensitivity_layout)
        
        # 匹配设置
        match_layout = QHBoxLayout()
        match_layout.addWidget(QLabel("最大物相:"))
        self.max_phases_spin = QSpinBox()
        self.max_phases_spin.setRange(1, 10)
        self.max_phases_spin.setValue(3)
        match_layout.addWidget(self.max_phases_spin)
        params_layout.addLayout(match_layout)
        
        params_group.setLayout(params_layout)
        left_layout.addWidget(params_group)
        
        # 分析控制组
        control_group = QGroupBox("分析控制")
        control_layout = QVBoxLayout()
        
        self.load_test_button = QPushButton("加载测试数据")
        self.load_test_button.clicked.connect(self.load_test_data)
        control_layout.addWidget(self.load_test_button)
        
        self.analyze_button = QPushButton("开始分析")
        self.analyze_button.clicked.connect(self.run_full_analysis)
        self.analyze_button.setEnabled(False)
        control_layout.addWidget(self.analyze_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("就绪")
        control_layout.addWidget(self.status_label)
        
        control_group.setLayout(control_layout)
        left_layout.addWidget(control_group)
        
        # 右侧：主工作区（标签页）
        right_panel = QTabWidget()
        
        # 标签1：图表视图
        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        
        # 图表区域
        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        chart_layout.addWidget(self.toolbar)
        chart_layout.addWidget(self.canvas)
        
        # 图表控制
        chart_controls = QHBoxLayout()
        
        self.auto_range_check = QCheckBox("自动范围")
        self.auto_range_check.setChecked(True)
        chart_controls.addWidget(self.auto_range_check)
        
        self.show_grid_check = QCheckBox("显示网格")
        self.show_grid_check.setChecked(True)
        chart_controls.addWidget(self.show_grid_check)
        
        chart_controls.addStretch()
        
        refresh_button = QPushButton("刷新图表")
        refresh_button.clicked.connect(self.refresh_chart)
        chart_controls.addWidget(refresh_button)
        
        chart_layout.addLayout(chart_controls)
        
        right_panel.addTab(chart_tab, "XRD图谱")
        
        # 标签2：峰位信息
        peaks_tab = QWidget()
        peaks_layout = QVBoxLayout(peaks_tab)
        
        self.peaks_table = QTableWidget()
        self.peaks_table.setColumnCount(6)
        self.peaks_table.setHorizontalHeaderLabels([
            "序号", "2θ (°)", "强度", "半高宽", "面积", "物相"
        ])
        peaks_layout.addWidget(self.peaks_table)
        
        right_panel.addTab(peaks_tab, "峰位信息")
        
        # 标签3：物相匹配
        phases_tab = QWidget()
        phases_layout = QVBoxLayout(phases_tab)
        
        self.phases_table = QTableWidget()
        self.phases_table.setColumnCount(5)
        self.phases_table.setHorizontalHeaderLabels([
            "矿物", "化学式", "匹配分数", "置信度", "匹配峰数"
        ])
        phases_layout.addWidget(self.phases_table)
        
        right_panel.addTab(phases_tab, "物相匹配")
        
        # 标签4：分析报告
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        
        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        report_layout.addWidget(self.report_text)
        
        right_panel.addTab(report_tab, "分析报告")
        
        # 将左右面板添加到分割器
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        
        # 设置分割器初始比例
        main_splitter.setSizes([300, 1100])
    
    def create_status_bar(self):
        """创建状态栏"""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        
        self.main_status_label = QLabel("就绪")
        status_bar.addWidget(self.main_status_label, 1)
        
        self.memory_label = QLabel("内存: --")
        status_bar.addWidget(self.memory_label)
    
    def open_file(self):
        """打开文件"""
        file_filter = (
            "XRD数据文件 (*.raw *.xrdml *.txt *.csv *.dat *.xy *.xrd);;"
            "所有文件 (*.*)"
        )
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "打开XRD数据文件", "", file_filter
        )
        
        if filepath:
            self.load_file(filepath)
    
    def load_file(self, filepath):
        """加载文件"""
        try:
            self.main_status_label.setText("正在加载文件...")
            QApplication.processEvents()
            
            # 使用RAW解析器加载文件
            result = self.raw_parser.parse_file(filepath)
            
            if result['data'] is None:
                QMessageBox.warning(self, "错误", 
                    f"无法解析文件数据: {filepath}\n"
                    "请检查文件格式是否为有效的XRD数据。"
                )
                return
            
            self.current_data = result['data']
            self.current_filepath = filepath
            
            # 更新文件信息
            filename = Path(filepath).name
            angles = self.current_data['angles']
            intensities = self.current_data['intensities']
            
            self.file_info_label.setText(
                f"文件: {filename}\n"
                f"仪器: {result['instrument']}\n"
                f"数据列: {len(angles)}"
            )
            
            self.data_stats_label.setText(
                f"角度范围: {angles.min():.2f}° - {angles.max():.2f}°\n"
                f"强度范围: {intensities.min():.2f} - {intensities.max():.2f}"
            )
            
            # 创建图表
            self.create_chart()
            
            # 绘制原始数据
            self.chart_manager.plot_original_data(
                angles,
                intensities,
                label='原始数据'
            )
            
            self.analyze_button.setEnabled(True)
            self.main_status_label.setText("文件加载成功")
            
            # 更新报告
            self.update_report(f"文件加载: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", 
                f"加载文件失败:\n{str(e)}\n\n"
                "请确保文件格式正确，或尝试其他文件格式。"
            )
            self.main_status_label.setText("加载失败")
    
    def load_test_data(self):
        """加载测试数据"""
        try:
            self.main_status_label.setText("正在生成测试数据...")
            
            # 生成模拟XRD数据
            x = np.linspace(10, 80, 2000)
            
            # 基线
            y = np.ones_like(x) * 100
            
            # 添加石英峰 (PDF#46-1045)
            quartz_peaks = [
                (20.85, 200, 0.15),  # 4.26 Å
                (26.65, 1000, 0.12),  # 3.34 Å
                (36.54, 120, 0.18),  # 2.46 Å
                (39.47, 80, 0.20),   # 2.28 Å
                (50.15, 150, 0.16),  # 1.82 Å
                (59.95, 100, 0.18),  # 1.54 Å
            ]
            
            for position, intensity, fwhm in quartz_peaks:
                y += intensity * np.exp(-((x - position) ** 2) / (2 * (fwhm/2.3548) ** 2))
            
            # 添加方解石峰 (PDF#47-1743)
            calcite_peaks = [
                (23.07, 300, 0.14),  # 3.86 Å
                (29.40, 800, 0.13),  # 3.04 Å
                (35.97, 250, 0.16),  # 2.50 Å
                (39.40, 180, 0.18),  # 2.29 Å
                (43.15, 120, 0.20),  # 2.10 Å
                (47.50, 90, 0.22),   # 1.91 Å
            ]
            
            for position, intensity, fwhm in calcite_peaks:
                y += intensity * np.exp(-((x - position) ** 2) / (2 * (fwhm/2.3548) ** 2))
            
            # 添加噪声
            y += np.random.normal(0, 30, len(x))
            
            self.current_data = {
                'angles': x,
                'intensities': y
            }
            self.current_filepath = "测试数据 (模拟石英+方解石)"
            
            # 更新文件信息
            self.file_info_label.setText(
                "文件: 测试数据\n"
                "仪器: 模拟生成\n"
                "样品: 石英 + 方解石\n"
                "数据列: 2000"
            )
            
            self.data_stats_label.setText(
                f"角度范围: {x.min():.2f}° - {x.max():.2f}°\n"
                f"强度范围: {y.min():.2f} - {y.max():.2f}"
            )
            
            # 创建图表
            self.create_chart()
            
            # 绘制原始数据
            self.chart_manager.plot_original_data(x, y, label='测试数据')
            
            self.analyze_button.setEnabled(True)
            self.main_status_label.setText("测试数据生成成功")
            
            # 更新报告
            self.update_report("加载测试数据: 模拟石英+方解石XRD图谱")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成测试数据失败:\n{str(e)}")
            self.main_status_label.setText("生成失败")
    
    def create_chart(self):
        """创建图表"""
        # 清除现有图表
        self.figure.clear()
        
        # 创建新的图表管理器
        self.chart_manager = DualLayerChartManager()
        self.chart_manager.fig = self.figure
        self.chart_manager.ax = self.figure.add_subplot(111)
        self.chart_manager._setup_chart_style()
        
        # 设置标题和标签
        self.chart_manager.ax.set_title("XRD图谱分析", fontsize=14)
        self.chart_manager.ax.set_xlabel("2θ (°)", fontsize=12)
        self.chart_manager.ax.set_ylabel("强度", fontsize=12)
        
        # 显示网格
        self.chart_manager.ax.grid(True, alpha=0.3)
        
        # 更新画布
        self.canvas.draw()
    
    def refresh_chart(self):
        """刷新图表"""
        if self.chart_manager and self.current_data:
            # 重新绘制数据
            self.chart_manager.ax.clear()
            self.chart_manager._setup_chart_style()
            
            self.chart_manager.plot_original_data(
                self.current_data['angles'],
                self.current_data['intensities'],
                label='原始数据'
            )
            
            # 重新添加峰标记
            if self.current_peaks:
                peak_markers = []
                for i, peak in enumerate(self.current_peaks):
                    peak_markers.append({
                        'position': peak['position'],
                        'intensity': peak['intensity'],
                        'index': i + 1,
                        'mineral': peak.get('mineral', '')
                    })
                
                self.chart_manager.add_peak_markers(peak_markers)
            
            # 设置网格
            self.chart_manager.ax.grid(self.show_grid_check.isChecked(), alpha=0.3)
            
            self.canvas.draw()
    
    def reset_chart_view(self):
        """重置图表视图"""
        if self.chart_manager and self.current_data:
            self.chart_manager.ax.set_xlim(
                self.current_data['angles'].min(),
                self.current_data['angles'].max()
            )
            self.chart_manager.ax.set_ylim(
                self.current_data['intensities'].min() * 0.9,
                self.current_data['intensities'].max() * 1.1
            )
            self.canvas.draw()
    
    def toggle_peak_markers(self, checked):
        """切换峰标记显示"""
        if self.chart_manager:
            # 这里需要实现显示/隐藏峰标记的逻辑
            pass
    
    def toggle_phase_labels(self, checked):
        """切换物相标签显示"""
        if self.chart_manager:
            # 这里需要实现显示/隐藏物相标签的逻辑
            pass
    
    def run_peak_detection(self):
        """运行峰检测"""
        if self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
        
        # 准备参数
        method_map = {
            "小波变换": "wavelet",
            "Savitzky-Golay": "savitzky", 
            "简单检测": "simple"
        }
        
        params = {
            'method': method_map.get(self.method_combo.currentText(), 'wavelet'),
            'min_snr': 2.0 / (self.sensitivity_slider.value() / 5.0),
            'min_prominence': 0.01 / (self.sensitivity_slider.value() / 5.0),
            'min_width': 0.1,
            'max_width': 5.0
        }
        
        # 启动分析线程
        self.start_analysis('peak_detection', params)
    
    def run_phase_matching(self):
        """运行物相匹配"""
        if not self.current_peaks:
            QMessageBox.warning(self, "警告", "请先进行峰检测")
            return
        
        params = {
            'peaks': self.current_peaks,
            'wavelength': 1.5406,
            'max_phases': self.max_phases_spin.value(),
            'min_confidence': 0.4
        }
        
        # 启动分析线程
        self.start_analysis('phase_matching', params)
    
    def run_full_analysis(self):
        """运行完整分析"""
        if self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
        
        # 启动分析线程
        self.start_analysis('full_analysis', {})
    
    def start_analysis(self, analysis_type, params):
        """启动分析线程"""
        # 停止现有线程
        if self.analysis_worker and self.analysis_worker.isRunning():
            self.analysis_worker.terminate()
            self.analysis_worker.wait()
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("正在分析...")
        
        # 创建并启动工作线程
        self.analysis_worker = AnalysisWorker(
            analysis_type,
            self.current_data,
            params
        )
        
        # 连接信号
        self.analysis_worker.progress_signal.connect(self.update_progress)
        self.analysis_worker.message_signal.connect(self.update_status)
        self.analysis_worker.result_signal.connect(self.handle_analysis_result)
        self.analysis_worker.error_signal.connect(self.handle_analysis_error)
        
        self.analysis_worker.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.setText(message)
    
    def handle_analysis_result(self, result):
        """处理分析结果"""
        analysis_type = self.analysis_worker.analysis_type
        
        if analysis_type == 'peak_detection':
            self.current_peaks = result['peaks']
            self.update_peaks_table()
            self.plot_peaks_on_chart()
            
        elif analysis_type == 'phase_matching':
            self.current_phases = result['phases']
            self.update_phases_table()
            self.update_peak_minerals()
            
        elif analysis_type == 'full_analysis':
            self.current_peaks = result.get('peaks', [])
            self.current_phases = result.get('phases', [])
            self.analysis_results = result
            
            self.update_peaks_table()
            self.update_phases_table()
            self.plot_peaks_on_chart()
            self.update_peak_minerals()
            self.generate_comprehensive_report()
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        self.status_label.setText("分析完成")
        
        # 更新主状态
        self.main_status_label.setText(f"{analysis_type}完成")
    
    def handle_analysis_error(self, error_message):
        """处理分析错误"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("分析失败")
        
        QMessageBox.critical(self, "分析错误", f"分析过程中出现错误:\n{error_message}")
    
    def update_peaks_table(self):
        """更新峰位表格"""
        self.peaks_table.setRowCount(len(self.current_peaks))
        
        for i, peak in enumerate(self.current_peaks):
            self.peaks_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.peaks_table.setItem(i, 1, QTableWidgetItem(f"{peak['position']:.3f}"))
            self.peaks_table.setItem(i, 2, QTableWidgetItem(f"{peak['intensity']:.1f}"))
            self.peaks_table.setItem(i, 3, QTableWidgetItem(f"{peak['fwhm']:.3f}"))
            self.peaks_table.setItem(i, 4, QTableWidgetItem(f"{peak.get('area', 0):.3f}"))
            self.peaks_table.setItem(i, 5, QTableWidgetItem(peak.get('mineral', '')))
        
        # 调整列宽
        self.peaks_table.resizeColumnsToContents()
    
    def update_phases_table(self):
        """更新物相表格"""
        self.phases_table.setRowCount(len(self.current_phases))
        
        for i, phase in enumerate(self.current_phases):
            self.phases_table.setItem(i, 0, QTableWidgetItem(phase['mineral']))
            self.phases_table.setItem(i, 1, QTableWidgetItem(phase['formula']))
            self.phases_table.setItem(i, 2, QTableWidgetItem(f"{phase['match_score']:.1f}"))
            self.phases_table.setItem(i, 3, QTableWidgetItem(f"{phase['confidence']:.1%}"))
            self.phases_table.setItem(i, 4, QTableWidgetItem(str(len(phase['matched_peaks']))))
        
        # 调整列宽
        self.phases_table.resizeColumnsToContents()
    
    def plot_peaks_on_chart(self):
        """在图表上绘制峰标记"""
        if self.chart_manager and self.current_peaks:
            peak_markers = []
            for i, peak in enumerate(self.current_peaks):
                peak_markers.append({
                    'position': peak['position'],
                    'intensity': peak['intensity'],
                    'index': i + 1,
                    'mineral': peak.get('mineral', '')
                })
            
            self.chart_manager.add_peak_markers(peak_markers)
            self.canvas.draw()
    
    def update_peak_minerals(self):
        """更新峰的矿物信息"""
        if not self.current_peaks or not self.current_phases:
            return
        
        # 为每个峰分配矿物
        mineral_assignments = {}
        for phase in self.current_phases:
            for peak_idx in phase['matched_peaks']:
                if peak_idx < len(self.current_peaks):
                    mineral_assignments[peak_idx] = phase['mineral']
        
        # 更新峰数据
        for i, peak in enumerate(self.current_peaks):
            if i in mineral_assignments:
                peak['mineral'] = mineral_assignments[i]
        
        # 更新表格
        self.update_peaks_table()
    
    def generate_comprehensive_report(self):
        """生成综合分析报告"""
        report = "=== Sci-XRD Pro 分析报告 ===\n\n"
        
        # 文件信息
        report += "1. 文件信息\n"
        report += f"   文件: {self.current_filepath}\n"
        report += f"   数据点: {len(self.current_data['angles'])}\n"
        report += f"   角度范围: {self.current_data['angles'].min():.2f}° - {self.current_data['angles'].max():.2f}°\n\n"
        
        # 峰检测结果
        report += "2. 峰检测结果\n"
        report += f"   检测到峰数: {len(self.current_peaks)}\n"
        
        if self.current_peaks:
            report += "   主要峰位:\n"
            for i, peak in enumerate(self.current_peaks[:10]):
                mineral = peak.get('mineral', '未知')
                report += f"     {i+1:2d}. 2θ={peak['position']:6.2f}°, I={peak['intensity']:7.1f}, FWHM={peak['fwhm']:.3f}°, {mineral}\n"
        report += "\n"
        
        # 物相匹配结果
        report += "3. 物相匹配结果\n"
        if self.current_phases:
            report += f"   匹配到物相: {len(self.current_phases)}\n"
            for i, phase in enumerate(self.current_phases):
                report += f"   {i+1}. {phase['mineral']} ({phase['formula']})\n"
                report += f"       匹配分数: {phase['match_score']:.1f}\n"
                report += f"       置信度: {phase['confidence']:.1%}\n"
                report += f"       匹配峰数: {len(phase['matched_peaks'])}\n"
        else:
            report += "   未匹配到物相\n"
        report += "\n"
        
        # 高级分析结果
        report += "4. 高级分析\n"
        if 'crystallite_size' in self.analysis_results:
            size_info = self.analysis_results['crystallite_size']
            report += f"   平均晶粒尺寸: {size_info['avg']:.1f} Å ({size_info['avg']/10:.1f} nm)\n"
            report += f"   标准差: {size_info['std']:.1f} Å\n"
        else:
            report += "   晶粒尺寸: 需要更多数据\n"
        report += "\n"
        
        # 分析总结
        report += "5. 分析总结\n"
        report += f"   分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        if self.current_phases:
            primary_phase = self.current_phases[0]
            report += f"   主要物相: {primary_phase['mineral']} (置信度: {primary_phase['confidence']:.1%})\n"
        
        report += "\n=== 报告结束 ===\n"
        
        self.report_text.setText(report)
    
    def update_report(self, message):
        """更新报告"""
        current = self.report_text.toPlainText()
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.report_text.setText(f"[{timestamp}] {message}\n{current}")
    
    def subtract_background(self):
        """背景扣除"""
        if self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
        
        try:
            angles = self.current_data['angles']
            intensities = self.current_data['intensities']
            
            # 使用算法库进行背景扣除
            background = self.algo_lib.subtract_background_tophat(intensities, window_size=101)
            background_corrected = intensities - background
            
            # 创建分析图层
            if self.chart_manager:
                self.chart_manager.add_analysis_overlay(
                    angles, background_corrected, label='背景扣除后'
                )
                self.canvas.draw()
            
            self.update_report("执行背景扣除 (Top-Hat方法)")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"背景扣除失败:\n{str(e)}")
    
    def smooth_data(self):
        """数据平滑"""
        if self.current_data is None:
            QMessageBox.warning(self, "警告", "请先加载数据")
            return
        
        try:
            from scipy import signal
            
            angles = self.current_data['angles']
            intensities = self.current_data['intensities']
            
            # Savitzky-Golay平滑
            window_length = 11  # 必须为奇数
            polyorder = 3
            smoothed = signal.savgol_filter(intensities, window_length, polyorder)
            
            # 创建分析图层
            if self.chart_manager:
                self.chart_manager.add_analysis_overlay(
                    angles, smoothed, label=f'平滑后 (窗口={window_length})'
                )
                self.canvas.draw()
            
            self.update_report(f"执行数据平滑 (Savitzky-Golay, 窗口={window_length})")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据平滑失败:\n{str(e)}")
    
    def show_settings(self):
        """显示分析设置"""
        QMessageBox.information(self, "分析设置", 
            "当前分析设置:\n\n"
            f"峰检测方法: {self.method_combo.currentText()}\n"
            f"灵敏度: {self.sensitivity_slider.value()}/10\n"
            f"最大物相数: {self.max_phases_spin.value()}\n\n"
            "可以在左侧面板调整这些参数。"
        )
    
    def export_results(self):
        """导出结果"""
        if not self.current_data:
            QMessageBox.warning(self, "警告", "没有可导出的数据")
            return
        
        # 选择导出格式
        formats = {
            "Origin格式 (*.txt)": "origin",
            "CSV格式 (*.csv)": "csv", 
            "Excel格式 (*.xlsx)": "excel",
            "JSON格式 (*.json)": "json"
        }
        
        file_filter = ";;".join([f"{desc} (*.{ext})" for desc, ext in 
                               [("Origin格式", "txt"), ("CSV格式", "csv"), 
                                ("Excel格式", "xlsx"), ("JSON格式", "json")]])
        
        filepath, selected_filter = QFileDialog.getSaveFileName(
            self, "导出分析结果", "", file_filter
        )
        
        if filepath:
            try:
                # 准备导出数据
                export_data = {
                    'data': self.current_data,
                    'peaks': self.current_peaks,
                    'phases': self.current_phases,
                    'analysis_results': self.analysis_results,
                    'metadata': {
                        'export_time': datetime.now().isoformat(),
                        'software': 'Sci-XRD Pro',
                        'version': '1.0.0'
                    }
                }
                
                # 根据选择的格式导出
                if filepath.endswith('.txt'):
                    # 导出为Origin格式
                    self.export_manager.export_for_origin(
                        data=export_data,
                        filename=Path(filepath).stem
                    )
                elif filepath.endswith('.csv'):
                    # 导出为CSV
                    self._export_to_csv(filepath, export_data)
                elif filepath.endswith('.xlsx'):
                    # 导出为Excel
                    self._export_to_excel(filepath, export_data)
                elif filepath.endswith('.json'):
                    # 导出为JSON
                    self._export_to_json(filepath, export_data)
                
                QMessageBox.information(self, "导出成功", 
                    f"分析结果已导出到:\n{filepath}")
                
                self.update_report(f"导出结果到: {Path(filepath).name}")
                
            except Exception as e:
                QMessageBox.critical(self, "导出错误", 
                    f"导出失败:\n{str(e)}")
    
    def _export_to_csv(self, filepath, data):
        """导出为CSV格式"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 写入数据
            writer.writerow(['Angle (2θ)', 'Intensity'])
            for angle, intensity in zip(data['data']['angles'], data['data']['intensities']):
                writer.writerow([f"{angle:.6f}", f"{intensity:.6f}"])
            
            # 写入峰信息
            if data['peaks']:
                writer.writerow([])
                writer.writerow(['Peak Analysis'])
                writer.writerow(['Index', 'Position', 'Intensity', 'FWHM', 'Area', 'Mineral'])
                for i, peak in enumerate(data['peaks']):
                    writer.writerow([
                        i+1,
                        f"{peak['position']:.4f}",
                        f"{peak['intensity']:.2f}",
                        f"{peak['fwhm']:.4f}",
                        f"{peak.get('area', 0):.4f}",
                        peak.get('mineral', '')
                    ])
    
    def _export_to_excel(self, filepath, data):
        """导出为Excel格式"""
        import pandas as pd
        
        # 创建Excel写入器
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 写入原始数据
            df_data = pd.DataFrame({
                'Angle (2θ)': data['data']['angles'],
                'Intensity': data['data']['intensities']
            })
            df_data.to_excel(writer, sheet_name='Raw Data', index=False)
            
            # 写入峰信息
            if data['peaks']:
                peaks_data = []
                for i, peak in enumerate(data['peaks']):
                    peaks_data.append({
                        'Index': i+1,
                        'Position': peak['position'],
                        'Intensity': peak['intensity'],
                        'FWHM': peak['fwhm'],
                        'Area': peak.get('area', 0),
                        'Mineral': peak.get('mineral', '')
                    })
                
                df_peaks = pd.DataFrame(peaks_data)
                df_peaks.to_excel(writer, sheet_name='Peak Analysis', index=False)
            
            # 写入物相信息
            if data['phases']:
                phases_data = []
                for phase in data['phases']:
                    phases_data.append({
                        'Mineral': phase['mineral'],
                        'Formula': phase['formula'],
                        'Match Score': phase['match_score'],
                        'Confidence': phase['confidence'],
                        'Matched Peaks': len(phase['matched_peaks'])
                    })
                
                df_phases = pd.DataFrame(phases_data)
                df_phases.to_excel(writer, sheet_name='Phase Matching', index=False)
    
    def _export_to_json(self, filepath, data):
        """导出为JSON格式"""
        import json
        
        # 转换NumPy数组为列表
        json_data = {
            'metadata': data['metadata'],
            'data': {
                'angles': data['data']['angles'].tolist(),
                'intensities': data['data']['intensities'].tolist()
            },
            'peaks': data['peaks'],
            'phases': data['phases'],
            'analysis_results': data['analysis_results']
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Sci-XRD Pro Enhanced")
    app.setOrganizationName("QClaw")
    
    window = EnhancedXRDWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()