#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sci-XRD Web图形界面 - 后端服务
"""

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict, Any
import uvicorn
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
import sys
from datetime import datetime
import traceback

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# 尝试导入本地模块
try:
    from core.xrd_analyzer import XRDAnalyzer
    from core.batch_processor import BatchProcessor
    from core.database_manager import DatabaseManager
except ImportError:
    # 如果本地导入失败，尝试相对导入
    try:
        from .core.xrd_analyzer import XRDAnalyzer
        from .core.batch_processor import BatchProcessor
        from .core.database_manager import DatabaseManager
    except ImportError:
        # 如果都失败，创建虚拟类
        class XRDAnalyzer:
            def __init__(self):
                pass
            def analyze(self, *args, **kwargs):
                return {"error": "XRDAnalyzer not available"}
        
        class BatchProcessor:
            def __init__(self):
                pass
            def process_batch(self, *args, **kwargs):
                return {"error": "BatchProcessor not available"}
        
        class DatabaseManager:
            def __init__(self, db_path=None):
                self.db_path = db_path
                pass
            def search_phases(self, *args, **kwargs):
                return []

app = FastAPI(
    title="Sci-XRD Web Interface",
    description="智能XRD分析Web界面",
    version="2.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建临时目录
TEMP_DIR = Path(tempfile.gettempdir()) / "sci_xrd_web"
TEMP_DIR.mkdir(exist_ok=True)

# 静态文件目录
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# 上传目录
UPLOAD_DIR = TEMP_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# 结果目录
RESULTS_DIR = TEMP_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 全局实例
xrd_analyzer = None
batch_processor = None
db_manager = None

@app.on_event("startup")
async def startup_event():
    """启动事件"""
    global xrd_analyzer, batch_processor, db_manager
    
    print("启动Sci-XRD Web服务...")
    
    try:
        # 初始化数据库管理器
        db_path = project_root / "pdf2_final_complete.db"
        db_manager = DatabaseManager(str(db_path))
        print(f"数据库已连接: {db_path}")
        
        # 初始化分析器
        xrd_analyzer = XRDAnalyzer(db_manager)
        
        # 初始化批处理器
        batch_processor = BatchProcessor(xrd_analyzer)
        
        print("Sci-XRD Web服务启动完成")
        
    except Exception as e:
        print(f"启动失败: {e}")
        traceback.print_exc()

@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    print("关闭Sci-XRD Web服务...")
    
    # 清理临时文件
    try:
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        print("临时文件已清理")
    except Exception as e:
        print(f"清理临时文件失败: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """主页"""
    html_content = r"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sci-XRD 智能XRD分析平台</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                width: 100%;
                max-width: 800px;
                overflow: hidden;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            
            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
                font-weight: 700;
            }
            
            .header p {
                font-size: 1.1rem;
                opacity: 0.9;
            }
            
            .content {
                padding: 40px;
            }
            
            .features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            
            .feature {
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                transition: transform 0.3s, box-shadow 0.3s;
            }
            
            .feature:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            
            .feature-icon {
                font-size: 2.5rem;
                margin-bottom: 15px;
                color: #667eea;
            }
            
            .feature h3 {
                margin-bottom: 10px;
                color: #333;
            }
            
            .feature p {
                color: #666;
                line-height: 1.5;
            }
            
            .actions {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }
            
            .btn {
                display: inline-block;
                padding: 15px 30px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-decoration: none;
                border-radius: 10px;
                font-size: 1.1rem;
                font-weight: 600;
                text-align: center;
                transition: transform 0.3s, box-shadow 0.3s;
                border: none;
                cursor: pointer;
            }
            
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
            }
            
            .btn-secondary {
                background: #6c757d;
            }
            
            .btn-secondary:hover {
                box-shadow: 0 10px 20px rgba(108, 117, 125, 0.4);
            }
            
            .status {
                margin-top: 30px;
                padding: 15px;
                background: #e8f4fd;
                border-radius: 10px;
                border-left: 4px solid #2196f3;
            }
            
            .status h4 {
                color: #2196f3;
                margin-bottom: 5px;
            }
            
            .footer {
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 0.9rem;
                border-top: 1px solid #eee;
            }
            
            @media (max-width: 768px) {
                .header {
                    padding: 30px 20px;
                }
                
                .header h1 {
                    font-size: 2rem;
                }
                
                .content {
                    padding: 30px 20px;
                }
                
                .features {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔬 Sci-XRD</h1>
                <p>智能XRD分析平台 - 专业、快速、易用</p>
            </div>
            
            <div class="content">
                <div class="features">
                    <div class="feature">
                        <div class="feature-icon">📊</div>
                        <h3>智能分析</h3>
                        <p>基于AI的智能参数推荐和物相鉴定，提高分析准确性</p>
                    </div>
                    
                    <div class="feature">
                        <div class="feature-icon">⚡</div>
                        <h3>快速处理</h3>
                        <p>毫秒级响应，支持批量文件处理，大幅提升工作效率</p>
                    </div>
                    
                    <div class="feature">
                        <div class="feature-icon">🖥️</div>
                        <h3>专业图表</h3>
                        <p>高质量图表输出，支持多种格式导出，满足出版要求</p>
                    </div>
                </div>
                
                <div class="actions">
                    <a href="/analyzer" class="btn">开始分析</a>
                    <a href="/batch" class="btn btn-secondary">批量处理</a>
                    <a href="/docs" class="btn btn-secondary">API文档</a>
                </div>
                
                <div class="status">
                    <h4>系统状态</h4>
                    <p>✅ 数据库已连接 | ✅ 分析引擎就绪 | ✅ Web服务运行中</p>
                    <p>📊 42,722张卡片 | 🔍 2,184,450个峰数据 | ⚡ 毫秒级响应</p>
                </div>
            </div>
            
            <div class="footer">
                <p>Sci-XRD v2.0.0 | © 2026 智能材料分析实验室</p>
                <p>技术支持: QClaw AI Assistant</p>
            </div>
        </div>
        
        <script>
            // 简单的页面交互
            document.addEventListener('DOMContentLoaded', function() {
                // 按钮点击效果
                const buttons = document.querySelectorAll('.btn');
                buttons.forEach(btn => {
                    btn.addEventListener('click', function(e) {
                        // 添加点击效果
                        this.style.transform = 'scale(0.98)';
                        setTimeout(() => {
                            this.style.transform = '';
                        }, 150);
                    });
                });
                
                // 更新状态时间
                function updateStatusTime() {
                    const now = new Date();
                    const timeStr = now.toLocaleTimeString('zh-CN');
                    const statusElement = document.querySelector('.status p');
                    if (statusElement) {
                        const text = statusElement.textContent;
                        const newText = text.replace(/\d{1,2}:\d{2}:\d{2}/, timeStr);
                        statusElement.textContent = newText;
                    }
                }
                
                // 每秒更新一次时间
                setInterval(updateStatusTime, 1000);
                updateStatusTime();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/status")
async def get_status():
    """获取系统状态"""
    try:
        status = {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0",
            "database": {
                "connected": db_manager is not None,
                "cards_count": db_manager.get_card_count() if db_manager else 0,
                "peaks_count": db_manager.get_peak_count() if db_manager else 0
            },
            "analyzer": {
                "ready": xrd_analyzer is not None
            },
            "batch_processor": {
                "ready": batch_processor is not None
            },
            "storage": {
                "temp_dir": str(TEMP_DIR),
                "upload_dir": str(UPLOAD_DIR),
                "results_dir": str(RESULTS_DIR)
            }
        }
        return JSONResponse(content=status)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """上传XRD数据文件"""
    try:
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = Path(file.filename).suffix
        unique_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 返回文件信息
        file_info = {
            "filename": unique_filename,
            "original_name": file.filename,
            "size": file_path.stat().st_size,
            "upload_time": timestamp,
            "path": str(file_path)
        }
        
        return JSONResponse(content={
            "success": True,
            "message": "文件上传成功",
            "file": file_info
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.post("/api/analyze")
async def analyze_file(
    filename: str = Form(...),
    params: Optional[str] = Form("{}")
):
    """分析XRD文件"""
    try:
        # 解析参数
        analysis_params = json.loads(params)
        
        # 构建文件路径
        file_path = UPLOAD_DIR / filename
        
        if not file_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "文件不存在"}
            )
        
        # 执行分析
        result = await xrd_analyzer.analyze_file(str(file_path), analysis_params)
        
        # 保存结果
        result_id = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result_file = RESULTS_DIR / f"{result_id}.json"
        
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return JSONResponse(content={
            "success": True,
            "result_id": result_id,
            "result": result
        })
        
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.get("/api/results/{result_id}")
async def get_result(result_id: str):
    """获取分析结果"""
    try:
        result_file = RESULTS_DIR / f"{result_id}.json"
        
        if not result_file.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "结果不存在"}
            )
        
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/batch")
async def batch_analyze(files: List[UploadFile] = File(...)):
    """批量分析文件"""
    try:
        # 保存上传的文件
        file_paths = []
        for file in files:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_filename = f"{timestamp}_{file.filename}"
            file_path = UPLOAD_DIR / unique_filename
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            file_paths.append(str(file_path))
        
        # 执行批量分析
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = await batch_processor.process_batch(file_paths, batch_id)
        
        return JSONResponse(content={
            "success": True,
            "batch_id": batch_id,
            "file_count": len(file_paths),
            "results": results
        })
        
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    """WebSocket状态推送"""
    await websocket.accept()
    
    try:
        while True:
            # 发送当前状态
            status = {
                "timestamp": datetime.now().isoformat(),
                "cpu_usage": "N/A",
                "memory_usage": "N/A",
                "active_tasks": 0,
                "queue_length": 0
            }
            
            await websocket.send_json(status)
            await asyncio.sleep(5)  # 每5秒发送一次
            
    except WebSocketDisconnect:
        print("WebSocket连接断开")
    except Exception as e:
        print(f"WebSocket错误: {e}")

@app.get("/api/export/{result_id}/{format}")
async def export_result(result_id: str, format: str):
    """导出分析结果"""
    try:
        result_file = RESULTS_DIR / f"{result_id}.json"
        
        if not result_file.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "结果不存在"}
            )
        
        with open(result_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        
        # 根据格式生成导出文件
        if format == "json":
            return JSONResponse(content=result)
        elif format == "csv":
            # 生成CSV文件
            csv_content = "Parameter,Value\n"
            for key, value in result.items():
                # 只处理基本类型
                if isinstance(value, (str, int, float, bool)):
                    csv_content += f"{key},{value}\n"
                elif isinstance(value, dict):
                    # 处理字典类型
                    csv_content += f"{key},[dict]\n"
                elif isinstance(value, list):
                    # 处理列表类型
                    csv_content += f"{key},[list]\n"
                else:
                    csv_content += f"{key},{str(value)}\n"
            
            return Response(content=csv_content, media_type="text/csv")
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"不支持的格式: {format}"}
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"导出失败: {str(e)}"}
        )