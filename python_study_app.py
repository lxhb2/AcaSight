#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python 编程学习中心 - 桌面应用
支持导入风变编程课程文件夹进行学习
"""

import sys
import os
import json
import shutil
from pathlib import Path

# PyQt5 用于创建桌面 GUI
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QFrame, QScrollArea, QProgressBar, QFileDialog, QMessageBox,
    QToolBar, QAction, QStatusBar, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt, QSize, QUrl, QTimer, QSettings
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from PyQt5.QtWebEngineWidgets import QWebEngineView

# 尝试导入 PyQt5，如果失败则使用备用方案
try:
    from PyQt5.QtWidgets import QGraphicsDropShadowEffect
    HAS_SHADOW = True
except:
    HAS_SHADOW = False


class Course:
    """课程数据类"""
    def __init__(self, name, path, course_type):
        self.name = name
        self.path = path
        self.course_type = course_type
        self.chapters = []


class PythonLearningApp(QMainWindow):
    """主应用窗口"""
    
    def __init__(self):
        super().__init__()
        self.courses = []
        self.current_course = None
        self.progress = {}
        self.settings = QSettings('PythonLearning', 'StudyApp')
        
        # 加载进度
        self.load_progress()
        
        # 初始化 UI
        self.init_ui()
        
        # 加载保存的路径
        self.load_saved_path()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('Python 编程学习中心')
        self.setMinimumSize(1200, 800)
        self.setGeometry(100, 100, 1400, 900)
        
        # 设置深色主题
        self.set_dark_theme()
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧：课程列表
        self.create_sidebar()
        
        # 右侧：学习区域
        self.create_content_area()
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar_frame)
        splitter.addWidget(self.content_frame)
        splitter.setSizes([350, 900])
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage('就绪')
    
    def set_dark_theme(self):
        """设置深色主题"""
        dark_style = """
        QMainWindow {
            background-color: #0a0c10;
        }
        QWidget {
            color: #f0f2f5;
            font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        }
        QTreeWidget {
            background-color: #111318;
            border: none;
            color: #f0f2f5;
            outline: none;
        }
        QTreeWidget::item {
            padding: 8px;
            border-radius: 6px;
            margin: 2px 0;
        }
        QTreeWidget::item:hover {
            background-color: #1a1d24;
        }
        QTreeWidget::item:selected {
            background-color: #6366f1;
            color: white;
        }
        QTreeWidget::branch {
            background: transparent;
        }
        QPushButton {
            background-color: #1a1d24;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 10px 20px;
            color: #f0f2f5;
        }
        QPushButton:hover {
            background-color: #22262f;
            border-color: #6366f1;
        }
        QPushButton#primaryBtn {
            background-color: #6366f1;
            border: none;
        }
        QPushButton#primaryBtn:hover {
            background-color: #818cf8;
        }
        QLabel {
            color: #f0f2f5;
        }
        QFrame#cardFrame {
            background-color: #111318;
            border-radius: 12px;
            border: 1px solid #222;
        }
        QScrollArea {
            background-color: transparent;
            border: none;
        }
        QProgressBar {
            background-color: #1a1d24;
            border: none;
            border-radius: 4px;
            height: 8px;
        }
        QProgressBar::chunk {
            background-color: #6366f1;
            border-radius: 4px;
        }
        QToolBar {
            background-color: #111318;
            border: none;
            spacing: 10px;
            padding: 8px;
        }
        QStatusBar {
            background-color: #111318;
            color: #8b919d;
        }
        """
        self.setStyleSheet(dark_style)
    
    def create_sidebar(self):
        """创建侧边栏"""
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setFixedWidth(350)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(15)
        
        # 顶部：Logo 和标题
        header_layout = QHBoxLayout()
        
        # Logo
        logo_label = QLabel("🐍")
        logo_label.setStyleSheet("font-size: 36px;")
        header_layout.addWidget(logo_label)
        
        # 标题
        title_layout = QVBoxLayout()
        title_label = QLabel("Python 学习中心")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #818cf8;")
        subtitle_label = QLabel("编程学习助手")
        subtitle_label.setStyleSheet("font-size: 12px; color: #5c6370;")
        title_layout.addLayout(title_layout)
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)
        
        sidebar_layout.addLayout(header_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        sidebar_layout.addWidget(self.progress_bar)
        
        # 进度文字
        self.progress_label = QLabel("0 / 0 课程")
        self.progress_label.setStyleSheet("font-size: 12px; color: #8b919d;")
        sidebar_layout.addWidget(self.progress_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("📁 选择文件夹")
        import_btn.setObjectName("primaryBtn")
        import_btn.clicked.connect(self.import_course_folder)
        btn_layout.addWidget(import_btn)
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_courses)
        btn_layout.addWidget(refresh_btn)
        
        sidebar_layout.addLayout(btn_layout)
        
        # 课程树
        self.course_tree = QTreeWidget()
        self.course_tree.setHeaderHidden(True)
        self.course_tree.itemClicked.connect(self.on_course_item_clicked)
        sidebar_layout.addWidget(self.course_tree)
        
        # 底部统计
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #111318; border-radius: 8px; padding: 15px;")
        stats_layout = QHBoxLayout(stats_frame)
        
        self.total_label = QLabel("总课程: 0")
        self.completed_label = QLabel("已完成: 0")
        self.rate_label = QLabel("进度: 0%")
        
        for label in [self.total_label, self.completed_label, self.rate_label]:
            label.setStyleSheet("font-size: 13px; color: #8b919d;")
            stats_layout.addWidget(label)
        
        sidebar_layout.addWidget(stats_frame)
    
    def create_content_area(self):
        """创建内容区域"""
        self.content_frame = QFrame()
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 工具栏
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        self.prev_action = QAction("◀ 上一课", self)
        self.prev_action.triggered.connect(self.prev_lesson)
        toolbar.addAction(self.prev_action)
        
        self.next_action = QAction("下一课 ▶", self)
        self.next_action.triggered.connect(self.next_lesson)
        toolbar.addAction(self.next_action)
        
        toolbar.addSeparator()
        
        self.mark_action = QAction("✓ 标记完成", self)
        self.mark_action.triggered.connect(self.mark_complete)
        toolbar.addAction(self.mark_action)
        
        toolbar.addSeparator()
        
        self.home_action = QAction("🏠 首页", self)
        self.home_action.triggered.connect(self.show_welcome)
        toolbar.addAction(self.home_action)
        
        content_layout.addWidget(toolbar)
        
        # 页面堆叠
        self.stack = QStackedWidget()
        
        # 欢迎页
        self.welcome_widget = self.create_welcome_page()
        self.stack.addWidget(self.welcome_widget)
        
        # 学习页面 (WebView)
        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.on_page_loaded)
        self.stack.addWidget(self.web_view)
        
        content_layout.addWidget(self.stack)
        
        # 初始显示欢迎页
        self.show_welcome()
    
    def create_welcome_page(self):
        """创建欢迎页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # 欢迎文字
        welcome_label = QLabel("🐍")
        welcome_label.setStyleSheet("font-size: 100px;")
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        title = QLabel("Python 编程学习中心")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #818cf8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        desc = QLabel("点击左侧「选择文件夹」按钮，导入你的风变编程课程")
        desc.setStyleSheet("font-size: 16px; color: #8b919d; margin: 20px 0;")
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        # 功能说明
        features = QFrame()
        features.setStyleSheet("""
            background-color: #111318;
            border-radius: 16px;
            padding: 30px;
            margin: 20px 100px;
        """)
        features_layout = QVBoxLayout(features)
        
        features_title = QLabel("📚 功能特点")
        features_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #f0f2f5; margin-bottom: 20px;")
        features_layout.addWidget(features_title)
        
        feature_list = [
            "📁 支持导入风变编程课程文件夹",
            "📖 课程内容本地浏览，无需联网",
            "💾 学习进度自动保存",
            "⬆️ 上一课/下一课 便捷导航",
            "✅ 标记已完成课程",
        ]
        
        for feat in feature_list:
            feat_label = QLabel(feat)
            feat_label.setStyleSheet("font-size: 14px; color: #8b919d; margin: 8px 0;")
            features_layout.addWidget(feat_label)
        
        layout.addWidget(features)
        
        return widget
    
    def import_course_folder(self):
        """导入课程文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择课程文件夹",
            os.path.expanduser("~/Desktop")
        )
        
        if folder:
            self.scan_course_folder(folder)
    
    def scan_course_folder(self, folder_path):
        """扫描课程文件夹"""
        self.courses = []
        
        # 课程分类映射
        course_types = {
            '【1】Python基础语法': ('📚', '#6366f1'),
            '【2】Python爬虫精讲': ('🕷️', '#06b6d4'),
            '【3】python办公自动化': ('⚡', '#f59e0b'),
            '【4】Python数据分析实战': ('📊', '#22c55e'),
        }
        
        folder = Path(folder_path)
        
        # 遍历子文件夹
        for subfolder in sorted(folder.iterdir()):
            if subfolder.is_dir():
                subfolder_name = subfolder.name
                
                # 匹配课程类型
                course_type = None
                icon = '📖'
                color = '#6366f1'
                
                for type_name, (type_icon, type_color) in course_types.items():
                    if type_name in subfolder_name:
                        course_type = type_name
                        icon = type_icon
                        color = type_color
                        break
                
                if course_type:
                    # 扫描 HTML 文件
                    html_files = sorted(subfolder.glob('*.html'))
                    
                    if html_files:
                        course = Course(subfolder.name, str(subfolder), course_type)
                        
                        for html_file in html_files:
                            # 提取课程名称
                            name = html_file.stem
                            # 移除数字前缀
                            name = name.replace('0关-', '').replace('1关-', '')
                            
                            course.chapters.append({
                                'name': name,
                                'path': str(html_file),
                                'file': html_file
                            })
                        
                        self.courses.append(course)
        
        # 保存路径
        self.settings.setValue('coursePath', folder_path)
        
        # 更新 UI
        self.update_course_tree()
        self.update_stats()
        
        # 显示状态
        total = sum(len(c.chapters) for c in self.courses)
        self.statusBar().showMessage(f'成功导入 {total} 个课程', 5000)
    
    def update_course_tree(self):
        """更新课程树"""
        self.course_tree.clear()
        
        for course in self.courses:
            # 课程大类
            course_item = QTreeWidgetItem(self.course_tree)
            course_item.setText(0, f"{course.chapters[0]['file'].parent.name if course.chapters else course.name}")
            course_item.setData(0, Qt.UserRole, course)
            
            # 章节
            for i, chapter in enumerate(course.chapters):
                chapter_item = QTreeWidgetItem(course_item)
                chapter_item.setText(0, f"  {i+1}. {chapter['name']}")
                chapter_item.setData(0, Qt.UserRole, chapter)
                
                # 检查是否已完成
                chapter_id = f"{course.name}:{chapter['name']}"
                if chapter_id in self.progress:
                    # 可以添加完成标记
                    pass
            
            course_item.setExpanded(True)
    
    def on_course_item_clicked(self, item, column):
        """课程项点击"""
        data = item.data(0, Qt.UserRole)
        
        if isinstance(data, dict) and 'path' in data:
            # 章节项，加载课程
            self.load_lesson(data)
        elif isinstance(data, Course):
            # 课程大类，展开/折叠
            item.setExpanded(not item.isExpanded())
    
    def load_lesson(self, chapter):
        """加载课程"""
        file_path = chapter['path']
        
        if os.path.exists(file_path):
            # 加载 HTML 文件
            url = QUrl.fromLocalFile(os.path.abspath(file_path))
            self.web_view.setUrl(url)
            self.stack.setCurrentWidget(self.web_view)
            
            # 更新状态
            self.current_course = chapter
            self.statusBar().showMessage(f'正在学习: {chapter["name"]}')
    
    def on_page_loaded(self, ok):
        """页面加载完成"""
        if ok:
            self.statusBar().showMessage('页面加载完成')
    
    def prev_lesson(self):
        """上一课"""
        # 需要实现课程索引逻辑
        pass
    
    def next_lesson(self):
        """下一课"""
        pass
    
    def mark_complete(self):
        """标记完成"""
        if self.current_course:
            chapter_id = f"{self.current_course.get('path', '')}"
            self.progress[chapter_id] = True
            self.save_progress()
            self.update_stats()
            self.statusBar().showMessage('已标记为完成 ✓', 3000)
    
    def show_welcome(self):
        """显示欢迎页"""
        self.stack.setCurrentWidget(self.welcome_widget)
        self.current_course = None
        self.statusBar().showMessage('就绪')
    
    def refresh_courses(self):
        """刷新课程"""
        path = self.settings.value('coursePath')
        if path and os.path.exists(path):
            self.scan_course_folder(path)
        else:
            QMessageBox.information(self, '提示', '请先选择课程文件夹')
    
    def load_saved_path(self):
        """加载保存的路径"""
        path = self.settings.value('coursePath')
        if path and os.path.exists(path):
            self.scan_course_folder(path)
    
    def update_stats(self):
        """更新统计"""
        total = sum(len(c.chapters) for c in self.courses)
        completed = len(self.progress)
        rate = int(completed / total * 100) if total > 0 else 0
        
        self.total_label.setText(f"总课程: {total}")
        self.completed_label.setText(f"已完成: {completed}")
        self.rate_label.setText(f"进度: {rate}%")
        
        self.progress_bar.setValue(rate)
        self.progress_label.setText(f"{completed} / {total} 课程")
    
    def save_progress(self):
        """保存进度"""
        self.settings.setValue('progress', json.dumps(self.progress))
    
    def load_progress(self):
        """加载进度"""
        try:
            self.progress = json.loads(self.settings.value('progress', '{}'))
        except:
            self.progress = {}
    
    def closeEvent(self, event):
        """关闭事件"""
        self.save_progress()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("Python 编程学习中心")
    app.setOrganizationName("StudyApp")
    
    # 设置应用图标（如果有）
    # app.setWindowIcon(QIcon('icon.png'))
    
    window = PythonLearningApp()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
