#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD 系统启动器 (Pythonw版本 - 无控制台窗口)
"""

import os
import sys
import webbrowser
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import threading
import time

class SciXRDLauncher:
    """Sci-XRD启动器GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sci-XRD 智能分析系统 v2.0.0")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # 设置图标（如果有）
        try:
            icon_path = Path(__file__).parent / "sci_xrd_icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass
        
        self.setup_ui()
        self.running = False
        self.process = None
    
    def setup_ui(self):
        """设置用户界面"""
        # 标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(
            title_frame,
            text="🔬 Sci-XRD 智能分析系统",
            font=("Arial", 24, "bold")
        )
        title_label.pack()
        
        version_label = ttk.Label(
            title_frame,
            text="版本 2.0.0 - 完整优化版",
            font=("Arial", 12)
        )
        version_label.pack()
        
        # 分隔线
        ttk.Separator(self.root, orient='horizontal').pack(fill='x', padx=20, pady=10)
        
        # 状态区域
        status_frame = ttk.LabelFrame(self.root, text="系统状态", padding=10)
        status_frame.pack(fill='x', padx=20, pady=10)
        
        self.status_text = tk.Text(
            status_frame,
            height=8,
            width=60,
            font=("Consolas", 10),
            bg='black',
            fg='white'
        )
        self.status_text.pack()
        
        # 按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.start_button = ttk.Button(
            button_frame,
            text="🚀 启动系统",
            command=self.start_system,
            width=15
        )
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="🛑 停止系统",
            command=self.stop_system,
            width=15,
            state='disabled'
        )
        self.stop_button.pack(side='left', padx=5)
        
        self.open_button = ttk.Button(
            button_frame,
            text="🌐 打开浏览器",
            command=self.open_browser,
            width=15
        )
        self.open_button.pack(side='left', padx=5)
        
        # 信息区域
        info_frame = ttk.LabelFrame(self.root, text="系统信息", padding=10)
        info_frame.pack(fill='x', padx=20, pady=10)
        
        info_text = """• 服务地址: http://localhost:8000
• API文档: http://localhost:8000/docs
• 实时图表: http://localhost:8000/analyzer
• 批量处理: http://localhost:8000/batch
• 技术支持: QClaw AI Assistant"""
        
        info_label = ttk.Label(
            info_frame,
            text=info_text,
            font=("Arial", 10),
            justify='left'
        )
        info_label.pack()
        
        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief='sunken',
            anchor='w'
        )
        status_bar.pack(side='bottom', fill='x')
    
    def log(self, message, color='white'):
        """添加日志消息"""
        self.status_text.insert('end', f"{message}\n")
        self.status_text.see('end')
        self.root.update()
    
    def check_environment(self):
        """检查环境"""
        self.log("检查Python环境...", "yellow")
        
        try:
            # 检查Python
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                self.log(f"✅ Python: {result.stdout.strip()}", "green")
            else:
                self.log("❌ Python未找到", "red")
                return False
            
            # 检查FastAPI
            try:
                import fastapi
                self.log("✅ FastAPI已安装", "green")
            except ImportError:
                self.log("⏳ 安装FastAPI...", "yellow")
                
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]"],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    self.log("✅ 依赖安装完成", "green")
                else:
                    self.log("❌ 依赖安装失败", "red")
                    return False
            
            # 检查必要文件
            web_dir = Path(__file__).parent / "web_interface"
            if not web_dir.exists():
                self.log("❌ Web目录不存在", "red")
                return False
            
            self.log("✅ 必要文件检查通过", "green")
            return True
            
        except Exception as e:
            self.log(f"❌ 环境检查失败: {e}", "red")
            return False
    
    def start_system(self):
        """启动系统"""
        if self.running:
            messagebox.showinfo("提示", "系统已在运行中")
            return
        
        # 检查环境
        if not self.check_environment():
            messagebox.showerror("错误", "环境检查失败，请检查Python和依赖")
            return
        
        # 启动服务线程
        self.running = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_var.set("启动中...")
        
        thread = threading.Thread(target=self.run_server, daemon=True)
        thread.start()
        
        # 打开浏览器
        self.open_browser()
    
    def run_server(self):
        """运行服务器"""
        try:
            web_dir = Path(__file__).parent / "web_interface"
            os.chdir(web_dir)
            
            self.log("启动Web服务...", "yellow")
            self.log("服务地址: http://localhost:8000", "cyan")
            self.log("按'停止系统'按钮停止服务", "cyan")
            
            # 启动uvicorn
            self.process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            self.status_var.set("运行中 - http://localhost:8000")
            
            # 读取输出
            for line in iter(self.process.stdout.readline, ''):
                if not self.running:
                    break
                self.log(f"[SERVER] {line.strip()}", "gray")
            
        except Exception as e:
            self.log(f"❌ 服务启动失败: {e}", "red")
            self.stop_system()
    
    def stop_system(self):
        """停止系统"""
        if not self.running:
            return
        
        self.running = False
        self.status_var.set("停止中...")
        
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_var.set("已停止")
        self.log("系统已停止", "yellow")
    
    def open_browser(self):
        """打开浏览器"""
        try:
            webbrowser.open("http://localhost:8000")
            self.log("✅ 浏览器已打开", "green")
        except Exception as e:
            self.log(f"⚠️ 无法打开浏览器: {e}", "yellow")
    
    def run(self):
        """运行启动器"""
        self.root.mainloop()
        
        # 退出时停止服务
        if self.running:
            self.stop_system()

def main():
    """主函数"""
    # 检查是否已有实例在运行
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 12345))
    except socket.error:
        messagebox.showinfo("提示", "Sci-XRD启动器已在运行中")
        return
    
    # 运行启动器
    launcher = SciXRDLauncher()
    launcher.run()

if __name__ == "__main__":
    main()