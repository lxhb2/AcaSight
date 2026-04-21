"""
现代化UI主题和样式
"""

from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon, QPainter, QLinearGradient
from PyQt6 import QtCore


class ModernTheme:
    """现代化主题配置"""
    
    # 颜色方案
    COLORS = {
        # 主色调
        'primary': '#2196F3',        # 蓝色
        'primary_dark': '#1976D2',
        'primary_light': '#64B5F6',
        
        # 强调色
        'accent': '#FF5722',        # 橙红色
        'accent_dark': '#E64A19',
        
        # 成功色
        'success': '#4CAF50',       # 绿色
        'success_dark': '#388E3C',
        
        # 警告色
        'warning': '#FFC107',       # 黄色
        'warning_dark': '#FFA000',
        
        # 错误色
        'error': '#F44336',         # 红色
        'error_dark': '#D32F2F',
        
        # 背景色
        'background': '#FAFAFA',
        'background_dark': '#ECEFF1',
        'surface': '#FFFFFF',
        
        # 文本色
        'text_primary': '#212121',
        'text_secondary': '#757575',
        'text_on_primary': '#FFFFFF',
        
        # 边框色
        'border': '#E0E0E0',
        'border_focus': '#2196F3',
        
        # 图表色
        'chart_line': '#2196F3',
        'chart_peak': '#F44336',
        'chart_background': '#FFFFFF',
        'chart_grid': '#E0E0E0'
    }
    
    @staticmethod
    def apply_theme(app: QApplication):
        """应用现代化主题"""
        # 设置Fusion样式作为基础
        app.setStyle('Fusion')
        
        # 创建调色板
        palette = ModernTheme._create_palette()
        app.setPalette(palette)
        
        # 设置全局字体
        font = QFont('Segoe UI', 10)
        app.setFont(font)
        
        # 设置样式表
        ModernTheme._apply_stylesheet(app)
    
    @staticmethod
    def _create_palette() -> QPalette:
        """创建调色板"""
        palette = QPalette()
        
        # 窗口背景
        palette.setColor(QPalette.ColorRole.Window, QColor(ModernTheme.COLORS['background']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(ModernTheme.COLORS['text_primary']))
        
        # 基础颜色
        palette.setColor(QPalette.ColorRole.Base, QColor(ModernTheme.COLORS['surface']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(ModernTheme.COLORS['background_dark']))
        
        # 工具提示
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(ModernTheme.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(ModernTheme.COLORS['text_on_primary']))
        
        # 文本颜色
        palette.setColor(QPalette.ColorRole.Text, QColor(ModernTheme.COLORS['text_primary']))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(ModernTheme.COLORS['text_secondary']))
        
        # 按钮
        palette.setColor(QPalette.ColorRole.Button, QColor(ModernTheme.COLORS['surface']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(ModernTheme.COLORS['text_primary']))
        
        # 高亮
        palette.setColor(QPalette.ColorRole.Highlight, QColor(ModernTheme.COLORS['primary']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(ModernTheme.COLORS['text_on_primary']))
        
        # 链接
        palette.setColor(QPalette.ColorRole.Link, QColor(ModernTheme.COLORS['primary']))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(ModernTheme.COLORS['primary_dark']))
        
        # 禁用状态 - 使用 ColorGroup 而不是 ColorRole
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, 
                        QColor(ModernTheme.COLORS['text_secondary']))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, 
                        QColor(ModernTheme.COLORS['text_secondary']))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, 
                        QColor(ModernTheme.COLORS['text_secondary']))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, 
                        QColor(ModernTheme.COLORS['border']))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, 
                        QColor(ModernTheme.COLORS['text_secondary']))
        
        return palette
    
    @staticmethod
    def _apply_stylesheet(app: QApplication):
        """应用样式表"""
        stylesheet = """
        /* ==================== 全局样式 ==================== */
        QMainWindow {
            background-color: #FAFAFA;
        }
        
        QWidget {
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            font-size: 10pt;
        }
        
        /* ==================== 按钮样式 ==================== */
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            min-width: 80px;
            font-weight: 500;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton:pressed {
            background-color: #1565C0;
        }
        
        QPushButton:disabled {
            background-color: #BDBDBD;
            color: #757575;
        }
        
        QPushButton#primary_button {
            background-color: #4CAF50;
        }
        
        QPushButton#primary_button:hover {
            background-color: #388E3C;
        }
        
        QPushButton#danger_button {
            background-color: #F44336;
        }
        
        QPushButton#danger_button:hover {
            background-color: #D32F2F;
        }
        
        QPushButton#outline_button {
            background-color: transparent;
            color: #2196F3;
            border: 2px solid #2196F3;
        }
        
        QPushButton#outline_button:hover {
            background-color: #E3F2FD;
        }
        
        /* ==================== 输入框样式 ==================== */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            padding: 8px;
            selection-background-color: #2196F3;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border: 2px solid #2196F3;
        }
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background-color: #F5F5F5;
            color: #9E9E9E;
        }
        
        /* ==================== 组合框样式 ==================== */
        QComboBox {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            padding: 8px 12px;
            min-width: 100px;
        }
        
        QComboBox:hover {
            border: 1px solid #2196F3;
        }
        
        QComboBox:focus {
            border: 2px solid #2196F3;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #757575;
            margin-right: 8px;
        }
        
        QComboBox QAbstractItemView {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            selection-background-color: #2196F3;
            padding: 4px;
        }
        
        /* ==================== 滑块样式 ==================== */
        QSlider::groove:horizontal {
            border: none;
            height: 4px;
            background-color: #E0E0E0;
            border-radius: 2px;
        }
        
        QSlider::handle:horizontal {
            background-color: #2196F3;
            border: none;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #1976D2;
        }
        
        QSlider::sub-page:horizontal {
            background-color: #2196F3;
            border-radius: 2px;
        }
        
        /* ==================== 进度条样式 ==================== */
        QProgressBar {
            background-color: #E0E0E0;
            border: none;
            border-radius: 4px;
            text-align: center;
            min-height: 20px;
        }
        
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 4px;
        }
        
        /* ==================== 分组框样式 ==================== */
        QGroupBox {
            font-weight: 600;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 12px;
            margin-top: 12px;
            background-color: white;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 8px;
            background-color: white;
        }
        
        /* ==================== 标签样式 ==================== */
        QLabel {
            color: #212121;
        }
        
        QLabel#title_label {
            font-size: 24px;
            font-weight: bold;
            color: #212121;
        }
        
        QLabel#subtitle_label {
            font-size: 16px;
            font-weight: 500;
            color: #757575;
        }
        
        QLabel#status_success {
            color: #4CAF50;
            font-weight: 500;
        }
        
        QLabel#status_error {
            color: #F44336;
            font-weight: 500;
        }
        
        QLabel#status_warning {
            color: #FFC107;
            font-weight: 500;
        }
        
        /* ==================== 表格样式 ==================== */
        QTableWidget, QTableView {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            gridline-color: #E0E0E0;
            selection-background-color: #E3F2FD;
        }
        
        QTableWidget::item, QTableView::item {
            padding: 8px;
            border-bottom: 1px solid #F5F5F5;
        }
        
        QTableWidget::item:selected, QTableView::item:selected {
            background-color: #2196F3;
            color: white;
        }
        
        QHeaderView::section {
            background-color: #F5F5F5;
            color: #212121;
            font-weight: 600;
            padding: 10px;
            border: none;
            border-bottom: 2px solid #2196F3;
        }
        
        /* ==================== 列表样式 ==================== */
        QListWidget, QListView {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            selection-background-color: #E3F2FD;
        }
        
        QListWidget::item, QListView::item {
            padding: 8px;
            border-bottom: 1px solid #F5F5F5;
        }
        
        QListWidget::item:hover, QListView::item:hover {
            background-color: #F5F5F5;
        }
        
        QListWidget::item:selected, QListView::item:selected {
            background-color: #2196F3;
            color: white;
        }
        
        /* ==================== 菜单样式 ==================== */
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #E0E0E0;
            padding: 4px;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 8px 12px;
            border-radius: 4px;
        }
        
        QMenuBar::item:selected {
            background-color: #E3F2FD;
        }
        
        QMenu {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 8px 24px 8px 12px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background-color: #E3F2FD;
        }
        
        QMenu::separator {
            height: 1px;
            background-color: #E0E0E0;
            margin: 4px 8px;
        }
        
        /* ==================== 工具栏样式 ==================== */
        QToolBar {
            background-color: white;
            border: none;
            border-bottom: 1px solid #E0E0E0;
            spacing: 4px;
            padding: 4px;
        }
        
        QToolBar::separator {
            width: 1px;
            background-color: #E0E0E0;
            margin: 4px 8px;
        }
        
        /* ==================== 滚动条样式 ==================== */
        QScrollBar:vertical {
            background-color: #F5F5F5;
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }
        
        QScrollBar::handle:vertical {
            background-color: #BDBDBD;
            border-radius: 6px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #9E9E9E;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        
        QScrollBar:horizontal {
            background-color: #F5F5F5;
            height: 12px;
            border-radius: 6px;
            margin: 0;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #BDBDBD;
            border-radius: 6px;
            min-width: 30px;
        }
        
        /* ==================== 工具提示样式 ==================== */
        QToolTip {
            background-color: #424242;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 9pt;
        }
        
        /* ==================== 状态栏样式 ==================== */
        QStatusBar {
            background-color: white;
            border-top: 1px solid #E0E0E0;
            padding: 4px;
        }
        
        QStatusBar QLabel {
            color: #757575;
            font-size: 9pt;
        }
        
        /* ==================== 标签页样式 ==================== */
        QTabWidget::pane {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            margin-top: -1px;
        }
        
        QTabBar::tab {
            background-color: #F5F5F5;
            color: #757575;
            padding: 10px 24px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 500;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            color: #2196F3;
            border-bottom: 2px solid #2196F3;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #EEEEEE;
            color: #424242;
        }
        
        /* ==================== 对话框样式 ==================== */
        QDialog {
            background-color: #FAFAFA;
        }
        
        QMessageBox {
            background-color: white;
        }
        
        /* ==================== 分割器样式 ==================== */
        QSplitter::handle {
            background-color: #E0E0E0;
        }
        
        QSplitter::handle:horizontal {
            width: 1px;
        }
        
        QSplitter::handle:vertical {
            height: 1px;
        }
        
        QSplitter::handle:hover {
            background-color: #2196F3;
        }
        
        /* ==================== 复选框样式 ==================== */
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #BDBDBD;
            border-radius: 4px;
            background-color: white;
        }
        
        QCheckBox::indicator:hover {
            border-color: #2196F3;
        }
        
        QCheckBox::indicator:checked {
            background-color: #2196F3;
            border-color: #2196F3;
        }
        
        QCheckBox:disabled {
            color: #9E9E9E;
        }
        
        /* ==================== 单选框样式 ==================== */
        QRadioButton {
            spacing: 8px;
        }
        
        QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #BDBDBD;
            border-radius: 9px;
            background-color: white;
        }
        
        QRadioButton::indicator:hover {
            border-color: #2196F3;
        }
        
        QRadioButton::indicator:checked {
            background-color: #2196F3;
            border-color: #2196F3;
        }
        
        /* ==================== 旋转框样式 ==================== */
        QSpinBox, QDoubleSpinBox {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            padding: 6px;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border: 2px solid #2196F3;
        }
        
        QSpinBox::up-button, QDoubleSpinBox::up-button {
            background-color: transparent;
            border: none;
            width: 16px;
        }
        
        QSpinBox::down-button, QDoubleSpinBox::down-button {
            background-color: transparent;
            border: none;
            width: 16px;
        }
        """
        
        app.setStyleSheet(stylesheet)


class AnimationHelper:
    """动画辅助类"""
    
    @staticmethod
    def create_fade_animation(target, duration=300):
        """创建淡入淡出动画"""
        animation = QPropertyAnimation(target, b"windowOpacity")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        return animation
    
    @staticmethod
    def create_slide_animation(target, property_name, duration=300):
        """创建滑动动画"""
        animation = QPropertyAnimation(target, property_name)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        return animation
    
    @staticmethod
    def create_color_animation(target, property_name, duration=500):
        """创建颜色动画"""
        animation = QPropertyAnimation(target, property_name)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.Linear)
        return animation


class IconFactory:
    """图标工厂"""
    
    @staticmethod
    def create_colored_icon(color: str, size: int = 24) -> QIcon:
        """创建纯色图标"""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(color))
        return QIcon(pixmap)
    
    @staticmethod
    def get_standard_icons():
        """获取标准图标字典"""
        return {
            'file': '📄',
            'folder': '📁',
            'save': '💾',
            'open': '📂',
            'close': '✖',
            'analyze': '🔍',
            'peak': '⛰️',
            'phase': '🔬',
            'export': '📤',
            'import': '📥',
            'settings': '⚙️',
            'help': '❓',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅',
            'ai': '🤖',
            'chart': '📊',
            'table': '📋',
            'refresh': '🔄'
        }


class ResponsiveLayout:
    """响应式布局辅助"""
    
    @staticmethod
    def adapt_to_screen(screen_size, base_width=1400):
        """根据屏幕大小调整布局"""
        scale_factor = min(screen_size.width() / base_width, 1.0)
        
        return {
            'font_size': max(9, int(10 * scale_factor)),
            'padding': max(4, int(8 * scale_factor)),
            'spacing': max(4, int(8 * scale_factor)),
            'button_width': max(60, int(80 * scale_factor)),
            'icon_size': max(16, int(24 * scale_factor))
        }


# 应用主题的便捷函数
def apply_modern_theme(app: QApplication):
    """应用现代化主题的便捷函数"""
    ModernTheme.apply_theme(app)