"""
AI助手面板 - 集成到主界面
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
import asyncio
from datetime import datetime

# PyQt6
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QGroupBox, QSplitter, QScrollArea,
    QFrame, QProgressBar, QCheckBox, QLineEdit, QListWidget,
    QListWidgetItem, QTabWidget, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSize
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon

# 导入AI客户端
sys.path.append(str(Path(__file__).parent.parent))

try:
    from ai.optimized_ollama_client import SyncOllamaClient, AIAnalysisResult
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("警告: AI模块不可用，将使用降级模式")


class AIAnalysisWorker(QThread):
    """AI分析工作线程"""
    
    progress_signal = pyqtSignal(int)
    message_signal = pyqtSignal(str)
    result_signal = pyqtSignal(AIAnalysisResult)
    error_signal = pyqtSignal(str)
    
    def __init__(self, angles, intensities, analysis_type='full'):
        super().__init__()
        self.angles = angles
        self.intensities = intensities
        self.analysis_type = analysis_type
        self.ai_client = None
        
    def run(self):
        try:
            if not AI_AVAILABLE:
                raise ImportError("AI模块不可用")
            
            self.message_signal.emit("初始化AI分析引擎...")
            self.progress_signal.emit(10)
            
            # 创建AI客户端
            self.ai_client = SyncOllamaClient()
            
            self.message_signal.emit("正在分析XRD数据...")
            self.progress_signal.emit(30)
            
            # 执行AI分析
            result = self.ai_client.analyze_xrd_data(
                self.angles, self.intensities, self.analysis_type
            )
            
            self.progress_signal.emit(90)
            self.message_signal.emit("分析完成，正在处理结果...")
            
            # 发送结果
            self.result_signal.emit(result)
            self.progress_signal.emit(100)
            
        except Exception as e:
            self.error_signal.emit(str(e))


class AIAssistantPanel(QWidget):
    """AI助手面板"""
    
    analysis_complete = pyqtSignal(AIAnalysisResult)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.ai_worker = None
        self.current_result = None
        self.history = []
        
        self.init_ui()
        
        # 性能监控
        self.performance_timer = QTimer()
        self.performance_timer.timeout.connect(self.update_performance_stats)
        self.performance_timer.start(5000)  # 每5秒更新一次
        
    def init_ui(self):
        """初始化用户界面"""
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("🤖 AI XRD分析助手")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 状态指示器
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 12))
        self.status_indicator.setStyleSheet("color: green;")
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666;")
        
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        main_layout.addWidget(status_frame)
        
        # 分析控制组
        control_group = QGroupBox("分析控制")
        control_layout = QVBoxLayout()
        
        # 分析类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("分析类型:"))
        
        self.analysis_combo = QComboBox()
        self.analysis_combo.addItems([
            "完整分析", 
            "峰位检测", 
            "物相匹配", 
            "质量评估",
            "优化建议"
        ])
        type_layout.addWidget(self.analysis_combo)
        
        control_layout.addLayout(type_layout)
        
        # 分析按钮
        self.analyze_button = QPushButton("开始AI分析")
        self.analyze_button.clicked.connect(self.start_analysis)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        control_layout.addWidget(self.analyze_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 结果展示区域
        result_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 聊天界面
        chat_group = QGroupBox("AI对话")
        chat_layout = QVBoxLayout()
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(200)
        chat_layout.addWidget(self.chat_display)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入问题或命令...")
        self.chat_input.returnPressed.connect(self.send_chat_message)
        input_layout.addWidget(self.chat_input)
        
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.send_chat_message)
        input_layout.addWidget(self.send_button)
        
        chat_layout.addLayout(input_layout)
        chat_group.setLayout(chat_layout)
        
        # 分析结果
        result_group = QGroupBox("分析结果")
        result_layout = QVBoxLayout()
        
        self.result_tabs = QTabWidget()
        
        # 峰位标签页
        peaks_tab = QWidget()
        peaks_layout = QVBoxLayout(peaks_tab)
        
        self.peaks_table = QTableWidget()
        self.peaks_table.setColumnCount(4)
        self.peaks_table.setHorizontalHeaderLabels(["2θ (°)", "强度", "置信度", "备注"])
        peaks_layout.addWidget(self.peaks_table)
        
        self.result_tabs.addTab(peaks_tab, "峰位")
        
        # 物相标签页
        phases_tab = QWidget()
        phases_layout = QVBoxLayout(phases_tab)
        
        self.phases_list = QListWidget()
        phases_layout.addWidget(self.phases_list)
        
        self.result_tabs.addTab(phases_tab, "物相")
        
        # 建议标签页
        suggestions_tab = QWidget()
        suggestions_layout = QVBoxLayout(suggestions_tab)
        
        self.suggestions_list = QListWidget()
        suggestions_layout.addWidget(self.suggestions_list)
        
        self.result_tabs.addTab(suggestions_tab, "建议")
        
        # 详情标签页
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        self.result_tabs.addTab(details_tab, "详情")
        
        result_layout.addWidget(self.result_tabs)
        result_group.setLayout(result_layout)
        
        result_splitter.addWidget(chat_group)
        result_splitter.addWidget(result_group)
        result_splitter.setSizes([200, 400])
        
        main_layout.addWidget(result_splitter)
        
        # 性能统计
        stats_group = QGroupBox("性能统计")
        stats_layout = QHBoxLayout()
        
        self.stats_label = QLabel("等待分析...")
        self.stats_label.setStyleSheet("color: #666; font-size: 10pt;")
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # 初始化聊天
        self.add_chat_message("AI助手", "您好！我是XRD分析助手，可以帮您分析XRD数据。", is_ai=True)
        
    def start_analysis(self):
        """开始AI分析"""
        if not AI_AVAILABLE:
            self.add_chat_message("系统", "AI功能不可用，请检查Ollama安装。", is_ai=False)
            return
        
        # 检查是否有数据
        if not hasattr(self.parent(), 'current_data') or self.parent().current_data is None:
            self.add_chat_message("系统", "请先加载XRD数据。", is_ai=False)
            return
        
        # 停止现有分析
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()
        
        # 获取数据
        angles = self.parent().current_data['angles']
        intensities = self.parent().current_data['intensities']
        
        # 获取分析类型
        analysis_type_map = {
            "完整分析": "full",
            "峰位检测": "peak_analysis",
            "物相匹配": "phase_matching",
            "质量评估": "quality_assessment",
            "优化建议": "optimization_suggestions"
        }
        
        analysis_type = analysis_type_map.get(
            self.analysis_combo.currentText(), "full"
        )
        
        # 更新UI状态
        self.analyze_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.status_indicator.setStyleSheet("color: orange;")
        self.status_label.setText("分析中...")
        
        # 添加聊天消息
        self.add_chat_message("用户", f"开始{self.analysis_combo.currentText()}...", is_ai=False)
        
        # 创建并启动工作线程
        self.ai_worker = AIAnalysisWorker(angles, intensities, analysis_type)
        self.ai_worker.progress_signal.connect(self.update_progress)
        self.ai_worker.message_signal.connect(self.update_status)
        self.ai_worker.result_signal.connect(self.handle_analysis_result)
        self.ai_worker.error_signal.connect(self.handle_analysis_error)
        
        self.ai_worker.start()
    
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """更新状态"""
        self.status_label.setText(message)
    
    def handle_analysis_result(self, result: AIAnalysisResult):
        """处理分析结果"""
        self.current_result = result
        
        # 更新UI状态
        self.analyze_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_indicator.setStyleSheet("color: green;")
        self.status_label.setText("分析完成")
        
        # 显示结果
        self.display_analysis_result(result)
        
        # 添加到历史
        self.history.append({
            'timestamp': datetime.now(),
            'result': result,
            'type': self.analysis_combo.currentText()
        })
        
        # 发送信号
        self.analysis_complete.emit(result)
    
    def handle_analysis_error(self, error_message):
        """处理分析错误"""
        self.analyze_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_indicator.setStyleSheet("color: red;")
        self.status_label.setText("分析失败")
        
        self.add_chat_message("AI助手", f"分析失败: {error_message}", is_ai=True)
    
    def display_analysis_result(self, result: AIAnalysisResult):
        """显示分析结果"""
        # 更新峰位表格
        self.update_peaks_table(result.peaks)
        
        # 更新物相列表
        self.update_phases_list(result.phases)
        
        # 更新建议列表
        self.update_suggestions_list(result.suggestions)
        
        # 更新详情文本
        self.update_details_text(result)
        
        # 添加聊天消息
        confidence_percent = result.confidence * 100
        message = (
            f"分析完成！\n"
            f"• 置信度: {confidence_percent:.1f}%\n"
            f"• 检测到峰数: {len(result.peaks)}\n"
            f"• 匹配物相: {len(result.phases)}\n"
            f"• 处理时间: {result.processing_time:.2f}秒\n"
            f"• 使用模型: {result.model_used}"
        )
        
        self.add_chat_message("AI助手", message, is_ai=True)
        
        # 如果有具体建议，也显示
        if result.suggestions:
            suggestions_text = "\n".join([f"• {s}" for s in result.suggestions[:3]])
            self.add_chat_message("AI助手", f"主要建议:\n{suggestions_text}", is_ai=True)
    
    def update_peaks_table(self, peaks: List[Dict]):
        """更新峰位表格"""
        self.peaks_table.setRowCount(len(peaks))
        
        for i, peak in enumerate(peaks):
            self.peaks_table.setItem(i, 0, QTableWidgetItem(f"{peak.get('position', 0):.2f}"))
            self.peaks_table.setItem(i, 1, QTableWidgetItem(f"{peak.get('intensity', 0):.1f}"))
            self.peaks_table.setItem(i, 2, QTableWidgetItem(f"{peak.get('confidence', 0):.2f}"))
            self.peaks_table.setItem(i, 3, QTableWidgetItem(peak.get('note', '')))
        
        self.peaks_table.resizeColumnsToContents()
    
    def update_phases_list(self, phases: List[Dict]):
        """更新物相列表"""
        self.phases_list.clear()
        
        for phase in phases:
            mineral = phase.get('mineral', '未知')
            formula = phase.get('formula', '')
            confidence = phase.get('confidence', 0)
            
            item_text = f"{mineral}"
            if formula:
                item_text += f" ({formula})"
            item_text += f" - 置信度: {confidence:.1%}"
            
            item = QListWidgetItem(item_text)
            
            # 根据置信度设置颜色
            if confidence > 0.8:
                item.setForeground(QColor(0, 128, 0))  # 绿色
            elif confidence > 0.6:
                item.setForeground(QColor(255, 165, 0))  # 橙色
            else:
                item.setForeground(QColor(255, 0, 0))  # 红色
            
            self.phases_list.addItem(item)
    
    def update_suggestions_list(self, suggestions: List[str]):
        """更新建议列表"""
        self.suggestions_list.clear()
        
        for suggestion in suggestions:
            item = QListWidgetItem(f"• {suggestion}")
            self.suggestions_list.addItem(item)
    
    def update_details_text(self, result: AIAnalysisResult):
        """更新详情文本"""
        details = f"""AI分析报告
================

分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
使用模型: {result.model_used}
处理时间: {result.processing_time:.2f}秒
总体置信度: {result.confidence:.1%}

峰位检测结果:
"""
        
        if result.peaks:
            for i, peak in enumerate(result.peaks):
                details += f"{i+1:2d}. 2θ={peak.get('position', 0):6.2f}°, "
                details += f"I={peak.get('intensity', 0):7.1f}, "
                details += f"置信度={peak.get('confidence', 0):.2f}\n"
        else:
            details += "  未检测到明显峰位\n"
        
        details += "\n物相匹配结果:\n"
        if result.phases:
            for phase in result.phases:
                details += f"• {phase.get('mineral', '未知')} "
                details += f"({phase.get('formula', '')}): "
                details += f"{phase.get('confidence', 0):.1%}\n"
        else:
            details += "  未匹配到物相\n"
        
        details += "\n分析建议:\n"
        if result.suggestions:
            for suggestion in result.suggestions:
                details += f"• {suggestion}\n"
        else:
            details += "  无具体建议\n"
        
        self.details_text.setText(details)
    
    def add_chat_message(self, sender: str, message: str, is_ai: bool = False):
        """添加聊天消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if is_ai:
            # AI消息 - 绿色
            html = f"""
            <div style="margin: 5px; padding: 8px; border-radius: 8px; background-color: #f0f9ff; border-left: 4px solid #4CAF50;">
                <div style="font-weight: bold; color: #2E7D32;">{sender} <span style="font-size: 0.8em; color: #666;">{timestamp}</span></div>
                <div style="margin-top: 4px; white-space: pre-wrap;">{message}</div>
            </div>
            """
        else:
            # 用户消息 - 蓝色
            html = f"""
            <div style="margin: 5px; padding: 8px; border-radius: 8px; background-color: #e3f2fd; border-left: 4px solid #2196F3;">
                <div style="font-weight: bold; color: #1565C0;">{sender} <span style="font-size: 0.8em; color: #666;">{timestamp}</span></div>
                <div style="margin-top: 4px; white-space: pre-wrap;">{message}</div>
            </div>
            """
        
        # 保存当前滚动位置
        scrollbar = self.chat_display.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        
        # 添加消息
        self.chat_display.append(html)
        
        # 如果之前已经在底部，保持滚动到底部
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())
    
    def send_chat_message(self):
        """发送聊天消息"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        # 添加用户消息
        self.add_chat_message("用户", message, is_ai=False)
        
        # 清空输入框
        self.chat_input.clear()
        
        # 处理消息
        self.process_chat_message(message)
    
    def process_chat_message(self, message: str):
        """处理聊天消息"""
        message_lower = message.lower()
        
        # 简单命令处理
        if any(cmd in message_lower for cmd in ['帮助', 'help', '?']):
            response = """我可以帮您：
1. 分析XRD数据（点击"开始AI分析"）
2. 解释分析结果
3. 提供优化建议
4. 回答XRD相关问题

常用命令：
• "分析数据" - 开始AI分析
• "显示峰位" - 查看检测到的峰
• "匹配物相" - 查看物相匹配结果
• "优化建议" - 获取分析优化建议"""
            
            self.add_chat_message("AI助手", response, is_ai=True)
            
        elif any(cmd in message_lower for cmd in ['分析', 'analyze', '开始']):
            self.start_analysis()
            
        elif any(cmd in message_lower for cmd in ['峰', 'peak']):
            if self.current_result and self.current_result.peaks:
                peaks_text = "检测到的峰位:\n"
                for i, peak in enumerate(self.current_result.peaks[:5]):
                    peaks_text += f"{i+1}. 2θ={peak.get('position', 0):.2f}°, I={peak.get('intensity', 0):.1f}\n"
                self.add_chat_message("AI助手", peaks_text, is_ai=True)
            else:
                self.add_chat_message("AI助手", "请先进行AI分析。", is_ai=True)
                
        elif any(cmd in message_lower for cmd in ['物相', 'phase', '矿物']):
            if self.current_result and self.current_result.phases:
                phases_text = "匹配的物相:\n"
                for phase in self.current_result.phases:
                    phases_text += f"• {phase.get('mineral', '未知')}: {phase.get('confidence', 0):.1%}\n"
                self.add_chat_message("AI助手", phases_text, is_ai=True)
            else:
                self.add_chat_message("AI助手", "请先进行AI分析。", is_ai=True)
                
        elif any(cmd in message_lower for cmd in ['建议', 'suggestion', '优化']):
            if self.current_result and self.current_result.suggestions:
                suggestions_text = "分析建议:\n"
                for suggestion in self.current_result.suggestions[:3]:
                    suggestions_text += f"• {suggestion}\n"
                self.add_chat_message("AI助手", suggestions_text, is_ai=True)
            else:
                self.add_chat_message("AI助手", "请先进行AI分析。", is_ai=True)
                
        else:
            # 默认响应
            response = f"我理解了您的问题: '{message}'\n\n"
            response += "对于XRD分析相关问题，我可以：\n"
            response += "1. 直接分析您加载的数据\n"
            response += "2. 解释特定的分析结果\n"
            response += "3. 提供数据采集或处理建议\n\n"
            response += "请尝试更具体的问题，或点击'开始AI分析'进行数据解析。"
            
            self.add_chat_message("AI助手", response, is_ai=True)
    
    def update_performance_stats(self):
        """更新性能统计"""
        if self.ai_worker and self.ai_worker.ai_client:
            try:
                stats = self.ai_worker.ai_client.get_performance_stats()
                
                stats_text = (
                    f"请求数: {stats.get('total_requests', 0)} | "
                    f"缓存命中率: {stats.get('cache_hit_rate', 0):.1%} | "
                    f"平均响应: {stats.get('avg_response_time', 0):.2f}s"
                )
                
                self.stats_label.setText(stats_text)
                
            except:
                pass
    
    def clear_history(self):
        """清空历史"""
        self.history.clear()
        self.chat_display.clear()
        self.add_chat_message("AI助手", "历史已清空。", is_ai=True)
    
    def export_conversation(self):
        """导出对话"""
        # 这里可以添加导出功能
        pass


# 测试函数
def test_ai_assistant():
    """测试AI助手面板"""
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    window = QWidget()
    layout = QVBoxLayout(window)
    
    assistant = AIAssistantPanel(window)
    layout.addWidget(assistant)
    
    window.setWindowTitle("AI助手测试")
    window.setGeometry(100, 100, 800, 600)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    test_ai_assistant()