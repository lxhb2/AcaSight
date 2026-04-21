"""
Sci-XRD Pro - 智能工作流组件
提供引导式分析流程
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QGroupBox, QListWidget
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont


class WorkflowStep:
    """工作流步骤"""
    def __init__(self, step_id: str, title: str, description: str):
        self.id = step_id
        self.title = title
        self.description = description
        self.completed = False
        self.data = None


class SmartWorkflow(QWidget):
    """
    智能工作流组件
    提供引导式分析流程
    """
    workflow_completed = pyqtSignal()
    step_completed = pyqtSignal(str)  # step_id
    step_started = pyqtSignal(str)   # step_id
    
    # 工作流步骤定义
    STEPS = [
        ('file_upload', '上传数据', '加载XRD数据文件'),
        ('detect_peaks', '峰检测', '自动检测峰位'),
        ('match_phases', '物相匹配', '匹配已知物相'),
        ('ai_analysis', 'AI分析', '获取智能洞察'),
        ('export_results', '导出结果', '保存分析报告')
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.steps = {}
        self.current_step = None
        self.handlers = {}
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("分析工作流")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.STEPS) * 100)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # 步骤列表
        self.steps_group = QGroupBox("步骤")
        steps_layout = QVBoxLayout()
        
        self.step_buttons = {}
        for step_id, title, desc in self.STEPS:
            step_widget = self._create_step_widget(step_id, title, desc)
            steps_layout.addWidget(step_widget)
            self.steps[step_id] = WorkflowStep(step_id, title, desc)
        
        self.steps_group.setLayout(steps_layout)
        layout.addWidget(self.steps_group)
        
        # 重置按钮
        reset_btn = QPushButton("重置工作流")
        reset_btn.clicked.connect(self.reset)
        layout.addWidget(reset_btn)
        
        self._update_progress()
    
    def _create_step_widget(self, step_id: str, title: str, desc: str) -> QWidget:
        """创建步骤组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 状态指示器
        status_label = QLabel("○")
        status_label.setObjectName(f"status_{step_id}")
        status_label.setStyleSheet("color: gray; font-size: 16px;")
        layout.addWidget(status_label)
        
        # 标题和描述
        text_layout = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setObjectName(f"title_{step_id}")
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("color: gray;")
        desc_label.setObjectName(f"desc_{step_id}")
        text_layout.addWidget(desc_label)
        layout.addLayout(text_layout)
        
        # 执行按钮
        btn = QPushButton("执行")
        btn.setObjectName(f"btn_{step_id}")
        btn.clicked.connect(lambda: self._execute_step(step_id))
        btn.setEnabled(step_id == 'file_upload')  # 只有第一步可点击
        layout.addWidget(btn)
        self.step_buttons[step_id] = btn
        
        return widget
    
    def register_handler(self, step_id: str, handler):
        """注册步骤处理函数"""
        self.handlers[step_id] = handler
    
    def _execute_step(self, step_id: str):
        """执行步骤"""
        if step_id not in self.steps:
            return
        
        self.step_started.emit(step_id)
        
        # 获取处理函数
        handler = self.handlers.get(step_id)
        if handler:
            try:
                result = handler()
                self._complete_step(step_id, result)
            except Exception as e:
                print(f"步骤执行失败: {e}")
                self._fail_step(step_id, str(e))
        else:
            # 没有处理函数，直接标记完成
            self._complete_step(step_id, None)
    
    def _complete_step(self, step_id: str, result):
        """标记步骤完成"""
        step = self.steps[step_id]
        step.completed = True
        step.data = result
        
        # 更新UI
        status_label = self.findChild(QLabel, f"status_{step_id}")
        if status_label:
            status_label.setText("●")
            status_label.setStyleSheet("color: green; font-size: 16px;")
        
        btn = self.step_buttons.get(step_id)
        if btn:
            btn.setEnabled(False)
            btn.setText("完成")
        
        self.step_completed.emit(step_id)
        self._enable_next_step(step_id)
        self._update_progress()
        
        # 检查是否全部完成
        if all(s.completed for s in self.steps.values()):
            self.workflow_completed.emit()
    
    def _fail_step(self, step_id: str, error: str):
        """标记步骤失败"""
        step = self.steps[step_id]
        
        # 更新UI
        status_label = self.findChild(QLabel, f"status_{step_id}")
        if status_label:
            status_label.setText("✗")
            status_label.setStyleSheet("color: red; font-size: 16px;")
        
        btn = self.step_buttons.get(step_id)
        if btn:
            btn.setEnabled(True)
            btn.setText("重试")
    
    def _enable_next_step(self, current_step_id: str):
        """启用下一步"""
        step_ids = [s[0] for s in self.STEPS]
        try:
            current_idx = step_ids.index(current_step_id)
            if current_idx + 1 < len(step_ids):
                next_step_id = step_ids[current_idx + 1]
                next_btn = self.step_buttons.get(next_step_id)
                if next_btn:
                    next_btn.setEnabled(True)
        except ValueError:
            pass
    
    def _update_progress(self):
        """更新进度条"""
        completed = sum(1 for s in self.steps.values() if s.completed)
        total = len(self.STEPS)
        progress = int(completed / total * 100)
        self.progress_bar.setValue(progress * 100)
        self.progress_bar.setFormat(f"进度: {progress}%")
    
    def reset(self):
        """重置工作流"""
        for step_id, step in self.steps.items():
            step.completed = False
            step.data = None
            
            # 重置UI
            status_label = self.findChild(QLabel, f"status_{step_id}")
            if status_label:
                status_label.setText("○")
                status_label.setStyleSheet("color: gray; font-size: 16px;")
            
            btn = self.step_buttons.get(step_id)
            if btn:
                btn.setEnabled(step_id == 'file_upload')
                btn.setText("执行")
        
        self._update_progress()
    
    def get_completed_steps(self) -> list:
        """获取已完成的步骤"""
        return [s for s in self.steps.values() if s.completed]
    
    def is_step_completed(self, step_id: str) -> bool:
        """检查步骤是否完成"""
        return self.steps.get(step_id, WorkflowStep('','','')).completed
