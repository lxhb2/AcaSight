"""
Sci-XRD-Pro GUI - 图形界面版本
基于 PyQt5 的专业 XRD 分析界面
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QProgressBar, QTextEdit, QGroupBox,
    QTabWidget, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QSlider, QStatusBar, QToolBar, QAction, QMenu, QMenuBar,
    QFrame, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPalette, QColor

from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from core.algorithms.peak_detection import Peak
from core.algorithms.phase_matching_v2 import HighAccuracyPhaseMatcher, Phase, MatchResult
from core.algorithms.xrd_preprocessor import XRDPreprocessor, smooth_savgol, background_snip



class AnalysisWorker(QThread):
    """后台分析工作线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    result = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, file_path, config, preloaded_data=None):
        """
        Args:
            file_path: 数据文件路径
            config: 分析配置
            preloaded_data: 预加载的原始数据 (two_theta, intensity) 或 None
        """
        super().__init__()
        self.file_path = file_path
        self.config = config
        self.preloaded_data = preloaded_data

    def run(self):
        try:
            self.status.emit("Loading data...")
            self.progress.emit(10)

            # 使用预加载数据或重新加载
            if self.preloaded_data is not None:
                two_theta, intensity = self.preloaded_data
                self.status.emit("Using preloaded data...")
                self.progress.emit(25)
            else:
                # Load data - 处理各种编码和注释格式
                data = None
                for enc in ['utf-8-sig', 'utf-8', 'gbk', 'latin-1', 'cp1252']:
                    try:
                        # 尝试跳过以 ; 开头的注释行（Bruker RAW格式）
                        data = np.loadtxt(self.file_path, encoding=enc, comments=';')
                        break
                    except Exception:
                        continue
                
                # 如果失败，尝试跳过 # 注释
                if data is None:
                    for enc in ['utf-8-sig', 'utf-8', 'gbk']:
                        try:
                            data = np.loadtxt(self.file_path, encoding=enc, comments='#')
                            break
                        except Exception:
                            continue
                
                # 如果仍然失败，尝试逐行解析
                if data is None:
                    data = []
                    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'latin-1']:
                        try:
                            with open(self.file_path, encoding=enc) as f:
                                lines = f.readlines()
                            for line in lines:
                                line = line.strip()
                                if not line or line.startswith('#') or line.startswith(';'):
                                    continue
                                parts = line.split()
                                if len(parts) >= 2:
                                    try:
                                        x = float(parts[0].replace(',', '.'))
                                        y = float(parts[1].replace(',', '.'))
                                        data.append([x, y])
                                    except ValueError:
                                        continue
                            if len(data) >= 3:
                                data = np.array(data)
                                break
                        except Exception:
                            continue
                
                if data is None:
                    raise ValueError("无法加载数据文件")
                
                two_theta = data[:, 0]
                intensity = data[:, 1]

            self.status.emit("Preprocessing...")
            self.progress.emit(25)

            # Preprocess
            preprocessor = XRDPreprocessor()
            y_processed = intensity.copy()
            if self.config.get('smooth', True):
                y_processed = smooth_savgol(y_processed)
            if self.config.get('bg_removal', True):
                y_processed = background_snip(y_processed)

            self.status.emit("Peak detection...")
            self.progress.emit(40)

            # Peak detection
            from core.algorithms.peak_detection import JadePeakDetector
            detector = JadePeakDetector()
            peaks = detector.detect(
                two_theta,
                y_processed,
                threshold=self.config.get('threshold', 0.05),
                min_intensity=self.config.get('min_intensity', 50)
            )

            self.status.emit("Phase matching...")
            self.progress.emit(60)

            # Phase matching
            matcher = HighAccuracyPhaseMatcher()
            matches = matcher.match(
                peaks,
                top_n=self.config.get('top_n', 10),
                min_score=self.config.get('min_score', 0.3)
            )

            self.status.emit("Analysis complete")
            self.progress.emit(100)

            # Send result
            self.result.emit({
                'two_theta': two_theta,
                'intensity': y_processed,
                'peaks': peaks,
                'matches': matches,
                'quantities': [],
                'raw_data': (two_theta, intensity)
            })

        except Exception as e:
            self.error.emit(str(e))


class XRDPlotCanvas(FigureCanvas):
    """XRD 图表画布"""
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # 设置样式
        self.axes.set_xlabel('2θ (deg)', fontsize=11)
        self.axes.set_ylabel('Intensity (a.u.)', fontsize=11)
        self.axes.set_title('XRD Pattern', fontsize=12, fontweight='bold')
        self.axes.grid(True, alpha=0.3)

    def plot_pattern(self, two_theta, intensity, peaks=None, title=None):
        """绘制 XRD 图谱"""
        self.axes.clear()

        # 绘制原始数据
        self.axes.plot(two_theta, intensity, 'b-', linewidth=0.8, label='XRD Data')

        # 标记峰位
        if peaks:
            for peak in peaks:
                self.axes.axvline(x=peak.position, color='r', linestyle='--', alpha=0.5)
                self.axes.plot(peak.position, peak.intensity, 'ro', markersize=6)

        if title:
            self.axes.set_title(title, fontsize=12, fontweight='bold')
        self.axes.set_xlabel('2θ (deg)', fontsize=11)
        self.axes.set_ylabel('Intensity (a.u.)', fontsize=11)
        self.axes.grid(True, alpha=0.3)
        self.axes.legend()

        self.fig.tight_layout()
        self.draw()

    def plot_pattern_overlay(self, two_theta_raw, intensity_raw, intensity_processed,
                            peaks=None, title=None):
        """
        绘制 XRD 图谱（原始数据 + 处理后数据叠加显示）

        Args:
            two_theta_raw: 原始 2θ 角度数组
            intensity_raw: 原始强度数组
            intensity_processed: 处理后强度数组（用于峰检测）
            peaks: 峰列表
            title: 图表标题
        """
        self.axes.clear()

        # 绘制原始数据（蓝色）
        self.axes.plot(two_theta_raw, intensity_raw, 'b-', linewidth=0.8,
                      alpha=0.7, label='Raw Data')

        # 绘制处理后数据（红色，用于峰检测）
        self.axes.plot(two_theta_raw, intensity_processed, 'r-', linewidth=0.5,
                      alpha=0.8, label='Processed')

        # 标记峰位
        if peaks:
            for peak in peaks:
                # 在原始数据上标记峰
                self.axes.axvline(x=peak.position, color='g', linestyle='--',
                                 alpha=0.6, linewidth=1)
                self.axes.plot(peak.position, peak.intensity, 'go', markersize=8,
                             markerfacecolor='none', markeredgecolor='g', markeredgewidth=2)

        if title:
            self.axes.set_title(title, fontsize=12, fontweight='bold')
        self.axes.set_xlabel('2θ (deg)', fontsize=11)
        self.axes.set_ylabel('Intensity (a.u.)', fontsize=11)
        self.axes.grid(True, alpha=0.3)
        self.axes.legend(loc='upper right')

        self.fig.tight_layout()
        self.draw()

    def clear_plot(self):
        """清除图表"""
        self.axes.clear()
        self.axes.set_xlabel('2θ (deg)', fontsize=11)
        self.axes.set_ylabel('Intensity (a.u.)', fontsize=11)
        self.axes.grid(True, alpha=0.3)
        self.draw()


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sci-XRD-Pro - XRD 分析系统")
        self.setGeometry(100, 100, 1400, 900)

        # 当前数据
        self.current_file = None
        self.analysis_result = None
        self.raw_two_theta = None
        self.raw_intensity = None
        self.processed_intensity = None

        self.init_ui()
        self.init_menu()
        self.init_toolbar()
        self.init_statusbar()

    def init_ui(self):
        """初始化界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板 - 控制区
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # 中间面板 - 图表区
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)

        # 右侧面板 - 结果区
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # 设置分割比例
        splitter.setSizes([300, 700, 400])

    def create_left_panel(self):
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # 文件选择组
        file_group = QGroupBox("数据文件")
        file_layout = QVBoxLayout(file_group)

        file_btn_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择 XRD 数据文件...")
        self.file_path_edit.setReadOnly(True)
        file_btn_layout.addWidget(self.file_path_edit)

        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_file)
        file_btn_layout.addWidget(browse_btn)

        file_layout.addLayout(file_btn_layout)

        # 快速加载按钮
        quick_layout = QHBoxLayout()
        demo_btn = QPushButton("加载演示数据")
        demo_btn.clicked.connect(self.load_demo)
        quick_layout.addWidget(demo_btn)

        clear_btn = QPushButton("清除")
        clear_btn.clicked.connect(self.clear_data)
        quick_layout.addWidget(clear_btn)

        file_layout.addLayout(quick_layout)
        layout.addWidget(file_group)

        # 参数设置组
        param_group = QGroupBox("分析参数")
        param_layout = QGridLayout(param_group)

        # 峰检测阈值
        param_layout.addWidget(QLabel("峰检测阈值:"), 0, 0)
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.01, 1.0)
        self.threshold_spin.setValue(0.05)
        self.threshold_spin.setSingleStep(0.01)
        param_layout.addWidget(self.threshold_spin, 0, 1)

        # 最小峰强度
        param_layout.addWidget(QLabel("最小峰强度:"), 1, 0)
        self.min_intensity_spin = QSpinBox()
        self.min_intensity_spin.setRange(0, 10000)
        self.min_intensity_spin.setValue(50)
        param_layout.addWidget(self.min_intensity_spin, 1, 1)

        # 最大匹配数
        param_layout.addWidget(QLabel("最大匹配数:"), 2, 0)
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(1, 20)
        self.top_n_spin.setValue(10)
        param_layout.addWidget(self.top_n_spin, 2, 1)

        # 最小匹配分数
        param_layout.addWidget(QLabel("最小匹配分数:"), 3, 0)
        self.min_score_spin = QDoubleSpinBox()
        self.min_score_spin.setRange(0.0, 1.0)
        self.min_score_spin.setValue(0.3)
        self.min_score_spin.setSingleStep(0.05)
        param_layout.addWidget(self.min_score_spin, 3, 1)

        layout.addWidget(param_group)

        # 预处理选项
        preprocess_group = QGroupBox("预处理选项")
        preprocess_layout = QVBoxLayout(preprocess_group)

        self.bg_check = QCheckBox("背景扣除 (SNIP)")
        self.bg_check.setChecked(True)
        preprocess_layout.addWidget(self.bg_check)

        self.smooth_check = QCheckBox("平滑滤波")
        self.smooth_check.setChecked(True)
        preprocess_layout.addWidget(self.smooth_check)

        self.ka2_check = QCheckBox("Kα2 剥离")
        self.ka2_check.setChecked(False)
        preprocess_layout.addWidget(self.ka2_check)

        layout.addWidget(preprocess_group)

        # 分析按钮
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.analyze_btn.clicked.connect(self.start_analysis)
        self.analyze_btn.setEnabled(False)
        layout.addWidget(self.analyze_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # 添加弹性空间
        layout.addStretch()

        return panel

    def create_center_panel(self):
        """创建中间面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 图表
        self.plot_canvas = XRDPlotCanvas(self, width=10, height=6)
        layout.addWidget(self.plot_canvas)

        # 工具栏
        self.toolbar = NavigationToolbar(self.plot_canvas, self)
        layout.addWidget(self.toolbar)

        # 日志输出
        log_group = QGroupBox("分析日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)

        return panel

    def create_right_panel(self):
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 标签页
        tabs = QTabWidget()

        # 峰列表标签
        peaks_tab = QWidget()
        peaks_layout = QVBoxLayout(peaks_tab)

        self.peaks_table = QTableWidget()
        self.peaks_table.setColumnCount(5)
        self.peaks_table.setHorizontalHeaderLabels([
            "序号", "2θ (°)", "d (Å)", "强度", "FWHM"
        ])
        self.peaks_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        peaks_layout.addWidget(self.peaks_table)

        tabs.addTab(peaks_tab, "峰列表")

        # 物相匹配标签
        phases_tab = QWidget()
        phases_layout = QVBoxLayout(phases_tab)

        self.phases_table = QTableWidget()
        self.phases_table.setColumnCount(5)
        self.phases_table.setHorizontalHeaderLabels([
            "排名", "物相名称", "化学式", "PDF", "匹配分数"
        ])
        self.phases_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        phases_layout.addWidget(self.phases_table)

        tabs.addTab(phases_tab, "物相匹配")

        # 定量结果标签
        quant_tab = QWidget()
        quant_layout = QVBoxLayout(quant_tab)

        self.quant_table = QTableWidget()
        self.quant_table.setColumnCount(3)
        self.quant_table.setHorizontalHeaderLabels([
            "物相", "含量 (wt%)", "误差"
        ])
        self.quant_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        quant_layout.addWidget(self.quant_table)

        tabs.addTab(quant_tab, "定量分析")

        layout.addWidget(tabs)

        # 导出按钮
        export_layout = QHBoxLayout()

        export_report_btn = QPushButton("导出报告")
        export_report_btn.clicked.connect(self.export_report)
        export_layout.addWidget(export_report_btn)

        export_data_btn = QPushButton("导出数据")
        export_data_btn.clicked.connect(self.export_data)
        export_layout.addWidget(export_data_btn)

        layout.addLayout(export_layout)

        return panel

    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        open_action = QAction("打开...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.browse_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 分析菜单
        analysis_menu = menubar.addMenu("分析")

        analyze_action = QAction("开始分析", self)
        analyze_action.setShortcut("F5")
        analyze_action.triggered.connect(self.start_analysis)
        analysis_menu.addAction(analyze_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        open_btn = QPushButton("打开")
        open_btn.clicked.connect(self.browse_file)
        toolbar.addWidget(open_btn)

        toolbar.addSeparator()

        self.toolbar_analyze_btn = QPushButton("分析")
        self.toolbar_analyze_btn.clicked.connect(self.start_analysis)
        toolbar.addWidget(self.toolbar_analyze_btn)

    def init_statusbar(self):
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 XRD 数据文件",
            "",
            "XRD Data (*.txt *.csv *.xy *.raw);;All Files (*.*)"
        )

        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        """加载文件"""
        try:
            self.current_file = file_path
            self.file_path_edit.setText(file_path)

            data = None
            errors = []
            
            # ---- 方案1：尝试np.loadtxt各种编码，跳过注释行 ----
            for enc in ['utf-8-sig', 'utf-8', 'gbk', 'latin-1', 'cp1252']:
                try:
                    # 尝试跳过以 ; 开头的注释行（Bruker RAW格式）
                    data = np.loadtxt(file_path, encoding=enc, comments=';')
                    self.log(f"File loaded with encoding: {enc}")
                    break
                except UnicodeDecodeError as e:
                    errors.append(f"  {enc}: UnicodeDecodeError - {e.encoding}/{e.reason}")
                except ValueError as e:
                    # 可能是其他格式，记录错误但继续尝试
                    errors.append(f"  {enc}: ValueError - {str(e)[:60]}")
                except Exception as e:
                    errors.append(f"  {enc}: {type(e).__name__} - {str(e)[:60]}")
            
            # ---- 方案1.5：尝试更多注释字符 ----
            if data is None:
                for enc in ['utf-8-sig', 'utf-8', 'gbk']:
                    try:
                        # 尝试跳过以 # 开头的注释行
                        data = np.loadtxt(file_path, encoding=enc, comments='#')
                        self.log(f"File loaded with encoding: {enc} (comment char #)")
                        break
                    except Exception:
                        pass
            
            # ---- 方案1.6：尝试跳过更多行 ----
            if data is None:
                for enc in ['utf-8-sig', 'utf-8', 'gbk']:
                    try:
                        # 尝试跳过前N行
                        for skiprows in range(0, 20):
                            try:
                                data = np.loadtxt(file_path, encoding=enc, skiprows=skiprows)
                                self.log(f"File loaded with encoding: {enc}, skipped {skiprows} rows")
                                break
                            except:
                                continue
                        if data is not None:
                            break
                    except Exception:
                        pass
            
            # ---- 方案2：二进制文件检测 + 文本回退 ----
            if data is None:
                # 读取文件头检测是否为二进制
                with open(file_path, 'rb') as f:
                    header_bytes = f.read(1024)
                
                # 检查是否包含大量null字节或非ASCII控制字符（binary file特征）
                null_count = header_bytes.count(b'\x00')
                non_printable = sum(1 for b in header_bytes if b > 127 and b not in (0x80, 0xA0))
                
                is_binary = null_count > 10 or (non_printable > 100 and null_count > 0)
                
                if is_binary:
                    # 尝试读取二进制XRD格式（Rigaku/ Bruker RAW/ Philips）
                    try:
                        data = self._load_binary_xrd(file_path, header_bytes)
                        self.log(f"Loaded as binary XRD format")
                    except Exception as e:
                        errors.append(f"Binary XRD: {str(e)[:80]}")
                else:
                    # 首先尝试专门的Bruker RAW解析器
                    try:
                        data = self._parse_bruker_raw(file_path)
                        self.log("Loaded as Bruker RAW format")
                    except Exception as e:
                        self.log(f"Bruker RAW parser failed: {e}")
                        # 手动逐行解析
                        for enc in ['utf-8-sig', 'utf-8', 'gbk', 'latin-1']:
                            try:
                                with open(file_path, encoding=enc) as f:
                                    lines = f.readlines()
                                # 过滤注释/空行，提取数字
                                vals = []
                                for line in lines:
                                    line = line.strip()
                                    # 跳过空行、注释行（# 或 ; 开头）
                                    if not line or line.startswith('#') or line.startswith(';'):
                                        continue
                                    # 跳过看起来像header的行（包含非数字字符）
                                    if any(c.isalpha() for c in line) and not any(c.isdigit() for c in line):
                                        continue
                                    
                                    # 尝试多种分隔符：空格、制表符、逗号、分号
                                    for sep in ['\t', ' ', ',', ';']:
                                        parts = line.split(sep)
                                        parts = [p.strip() for p in parts if p.strip()]
                                        if len(parts) >= 2:
                                            # 尝试解析前两个值为数字
                                            # 使用更安全的方式，避免嵌套try-except
                                            x_str = parts[0].replace(',', '.')
                                            y_str = parts[1].replace(',', '.')
                                            # 检查是否为数字
                                            if (x_str.replace('.', '', 1).replace('-', '', 1).isdigit() and 
                                                y_str.replace('.', '', 1).replace('-', '', 1).isdigit()):
                                                x_val = float(x_str)
                                                y_val = float(y_str)
                                                vals.append([x_val, y_val])
                                                break  # 成功解析，跳出分隔符循环
                                if len(vals) >= 3:
                                    data = np.array(vals)
                                    self.log(f"Parsed line-by-line with {enc}")
                                    break
                            except Exception as e:
                                errors.append(f"Line-by-line {enc}: {str(e)[:60]}")
            
            # ---- 方案3：生成演示数据提示 ----
            if data is None:
                diag = "尝试过的编码:\n" + "\n".join(errors[:6])
                self.log(diag)
                # 检查文件扩展名
                ext = os.path.splitext(file_path)[1].lower()
                hint = f"\n\n文件扩展名: {ext}"
                if ext == '.raw':
                    hint += "\n提示: 这是二进制RAW格式，需要专门的解析器"
                elif ext == '.brml':
                    hint += "\n提示: 这是Bruker XML格式"
                QMessageBox.critical(self, "错误", 
                    f"无法解码文件，请确认文件编码格式\n{diag}{hint}")
                return
            
            # 处理一维数据（只有一列）
            if data.ndim == 1:
                two_theta = data
                intensity = np.ones_like(data)
            else:
                two_theta = data[:, 0]
                intensity = data[:, 1]

            # 保存原始数据
            self.raw_two_theta = two_theta.copy()
            self.raw_intensity = intensity.copy()

            self.plot_canvas.plot_pattern(two_theta, intensity, title=f"原始数据: {os.path.basename(file_path)}")

            self.analyze_btn.setEnabled(True)
            self.statusbar.showMessage(f"已加载: {file_path}")
            self.log(f"加载文件: {file_path}")
            self.log(f"数据点数: {len(two_theta)}")
            self.log(f"角度范围: {two_theta.min():.2f}° - {two_theta.max():.2f}°")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载文件失败:\n{str(e)}")

    def _load_binary_xrd(self, file_path, header_bytes):
        """尝试解析二进制XRD格式文件"""
        import struct
        
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        
        # 尝试解析为32位浮点数数组
        float_count = len(raw_data) // 4
        floats = np.array(struct.unpack(f'<{float_count}f', raw_data[:float_count*4]), dtype=np.float32)
        
        # 如果数据看起来像count数据（前半部分为递增角度）
        if float_count >= 10:
            # 尝试每隔一个取两个通道
            channel1 = floats[0::2][:len(floats)//2]
            channel2 = floats[1::2][:len(floats)//2]
            
            # 检查是否为有效XRD数据
            if channel1.std() > 0 and channel2.std() > 0:
                # 假设channel1是角度，channel2是强度
                valid = ~np.isnan(channel1) & ~np.isnan(channel2) & ~np.isinf(channel1) & ~np.isinf(channel2)
                if valid.sum() >= 10:
                    return np.column_stack([channel1[valid], channel2[valid]])
        
        raise ValueError("Binary format not recognized")
    
    def _parse_bruker_raw(self, file_path):
        """解析Bruker RAW文本格式文件"""
        data = []
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
        
        # 查找数据开始位置
        data_start = 0
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith(';') and not any(c.isalpha() for c in line):
                # 第一个非注释、非字母行可能是数据开始
                data_start = i
                break
        
        # 解析数据
        for line in lines[data_start:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    x = float(parts[0].replace(',', '.'))
                    y = float(parts[1].replace(',', '.'))
                    data.append([x, y])
                except ValueError:
                    continue
        
        if len(data) >= 3:
            return np.array(data)
        else:
            raise ValueError("Not enough valid data points")
    
    def load_demo(self):
        """加载演示数据"""
        try:
            # 生成模拟数据
            x = np.linspace(5, 65, 2000)
            y = np.ones_like(x) * 50

            # 石英峰
            quartz_d = [4.26, 3.34, 2.46, 2.28, 1.82]
            quartz_i = [100, 80, 45, 35, 25]
            for d, i in zip(quartz_d, quartz_i):
                two_theta = 2 * np.degrees(np.arcsin(1.5406 / (2 * d)))
                if 5 < two_theta < 65:
                    y += i * 50 * np.exp(-((x - two_theta) ** 2) / 0.3)

            # 方解石峰
            calcite_d = [3.04, 2.49, 2.28, 1.91, 1.87]
            calcite_i = [100, 40, 18, 12, 12]
            for d, i in zip(calcite_d, calcite_i):
                two_theta = 2 * np.degrees(np.arcsin(1.5406 / (2 * d)))
                if 5 < two_theta < 65:
                    y += i * 30 * np.exp(-((x - two_theta) ** 2) / 0.3)

            y += np.random.normal(0, 5, len(x))

            # 保存临时文件
            demo_path = os.path.join(os.path.dirname(__file__), "demo_xrd_temp.txt")
            np.savetxt(demo_path, np.column_stack([x, y]))

            self.load_file(demo_path)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成演示数据失败:\n{str(e)}")

    def clear_data(self):
        """清除数据"""
        self.current_file = None
        self.analysis_result = None
        self.file_path_edit.clear()
        self.plot_canvas.clear_plot()
        self.peaks_table.setRowCount(0)
        self.phases_table.setRowCount(0)
        self.quant_table.setRowCount(0)
        self.log_text.clear()
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.statusbar.showMessage("就绪")

    def start_analysis(self):
        """开始分析"""
        if not self.current_file:
            QMessageBox.warning(self, "警告", "请先加载数据文件")
            return

        # 获取配置
        config = {
            'threshold': self.threshold_spin.value(),
            'min_intensity': self.min_intensity_spin.value(),
            'top_n': self.top_n_spin.value(),
            'min_score': self.min_score_spin.value(),
            'bg_removal': self.bg_check.isChecked(),
            'smooth': self.smooth_check.isChecked(),
            'ka2_strip': self.ka2_check.isChecked()
        }

        # 创建工作线程
        # 传递预加载的原始数据
        preloaded_data = (self.raw_two_theta, self.raw_intensity) if self.raw_two_theta is not None else None
        self.worker = AnalysisWorker(self.current_file, config, preloaded_data)
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.result.connect(self.handle_result)
        self.worker.error.connect(self.handle_error)

        # 禁用按钮
        self.analyze_btn.setEnabled(False)
        self.log("开始分析...")

        # 启动
        self.worker.start()

    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """更新状态"""
        self.statusbar.showMessage(message)
        self.log(message)

    def handle_result(self, result):
        """处理结果"""
        self.analysis_result = result
        self.processed_intensity = result['intensity']

        # 获取原始数据用于显示
        if 'raw_data' in result and result['raw_data'] is not None:
            raw_two_theta, raw_intensity = result['raw_data']
        else:
            raw_two_theta = result['two_theta']
            raw_intensity = result['intensity']

        # 显示原始数据 + 峰标记
        self.plot_canvas.plot_pattern_overlay(
            raw_two_theta,
            raw_intensity,
            result['intensity'],
            peaks=result['peaks'],
            title="分析结果 - 原始数据"
        )

        # 更新峰列表
        self.update_peaks_table(result['peaks'])

        # 更新物相匹配
        self.update_phases_table(result['matches'])

        # 更新定量结果
        self.update_quant_table(result['quantities'])

        # 启用按钮
        self.analyze_btn.setEnabled(True)
        self.statusbar.showMessage("分析完成")

        QMessageBox.information(self, "完成", "分析完成!")

    def handle_error(self, error_msg):
        """处理错误"""
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "分析错误", f"分析过程中出错:\n{error_msg}")
        self.log(f"错误: {error_msg}")

    def update_peaks_table(self, peaks):
        """更新峰列表"""
        self.peaks_table.setRowCount(len(peaks))
        for i, peak in enumerate(peaks):
            self.peaks_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.peaks_table.setItem(i, 1, QTableWidgetItem(f"{peak.position:.3f}"))
            self.peaks_table.setItem(i, 2, QTableWidgetItem(f"{peak.d_spacing:.4f}"))
            self.peaks_table.setItem(i, 3, QTableWidgetItem(f"{peak.intensity:.1f}"))
            self.peaks_table.setItem(i, 4, QTableWidgetItem(f"{peak.fwhm:.3f}"))

    def update_phases_table(self, matches):
        """更新物相匹配表"""
        self.phases_table.setRowCount(len(matches))
        for i, match in enumerate(matches):
            if isinstance(match, dict):
                phase = match.get('phase', {})
                score = match.get('score', 0)
            else:
                phase = match.phase
                score = match.score

            name = phase.name if hasattr(phase, 'name') else phase.get('name', 'Unknown')
            formula = phase.formula if hasattr(phase, 'formula') else phase.get('formula', '')
            pdf = phase.pdf_number if hasattr(phase, 'pdf_number') else phase.get('pdf_number', '')

            self.phases_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.phases_table.setItem(i, 1, QTableWidgetItem(name))
            self.phases_table.setItem(i, 2, QTableWidgetItem(formula))
            self.phases_table.setItem(i, 3, QTableWidgetItem(pdf))
            self.phases_table.setItem(i, 4, QTableWidgetItem(f"{score:.1%}"))

    def update_quant_table(self, quantities):
        """更新定量结果表"""
        self.quant_table.setRowCount(len(quantities))
        for i, q in enumerate(quantities):
            self.quant_table.setItem(i, 0, QTableWidgetItem(q['name']))
            self.quant_table.setItem(i, 1, QTableWidgetItem(f"{q['weight_percent']:.2f}"))
            self.quant_table.setItem(i, 2, QTableWidgetItem(f"{q['error']:.2f}"))

    def export_report(self):
        """导出报告"""
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "没有分析结果可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出报告",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("=" * 60 + "\n")
                    f.write("Sci-XRD-Pro 分析报告\n")
                    f.write("=" * 60 + "\n\n")

                    f.write(f"样品: {os.path.basename(self.current_file)}\n")
                    f.write(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                    f.write("峰列表:\n")
                    f.write("-" * 60 + "\n")
                    for i, peak in enumerate(self.analysis_result['peaks']):
                        f.write(f"{i+1}. 2θ={peak.position:.3f}°, d={peak.d_spacing:.4f}Å, I={peak.intensity:.1f}\n")

                    f.write("\n物相匹配:\n")
                    f.write("-" * 60 + "\n")
                    for i, match in enumerate(self.analysis_result['matches'][:10]):
                        phase = match['phase']
                        f.write(f"{i+1}. {phase.name} ({phase.formula}) - {match['score']:.1%}\n")

                QMessageBox.information(self, "完成", f"报告已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")

    def export_data(self):
        """导出数据"""
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            "",
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*.*)"
        )

        if file_path:
            try:
                np.savetxt(
                    file_path,
                    np.column_stack([
                        self.analysis_result['two_theta'],
                        self.analysis_result['intensity']
                    ]),
                    delimiter=',',
                    header='2theta,intensity'
                )
                QMessageBox.information(self, "完成", f"数据已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 Sci-XRD-Pro",
            """<h2>Sci-XRD-Pro v1.0</h2>
            <p>XRD 数据分析统一平台</p>
            <p>基于 JADE 标准工作流</p>
            <p>支持 PDF4-2009 数据库</p>
            <br>
            <p>功能特性:</p>
            <ul>
                <li>SNIP 背景扣除</li>
                <li>智能峰检测</li>
                <li>物相鉴定</li>
                <li>RIR 定量分析</li>
            </ul>
            """
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle('Fusion')

    # 设置字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    # 创建窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
