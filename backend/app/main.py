"""
AcaSight 后端主应用 - 融合 PaperPal + pdf-research-assistant
FastAPI + PDF处理 + AI + 文献检索
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting AcaSight backend...")

    # 确保关键子目录存在
    import os
    data_dirs = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "agent_sessions"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache"),
    ]
    for d in data_dirs:
        os.makedirs(d, exist_ok=True)

    # 数据库初始化（可选，跳过失败）
    try:
        from app.database import init_db, close_db
        from app.models.paper import Paper
        from app.models.annotation import Annotation
        from app.models.paper_dimensions import PaperDimensions
        await init_db()
        app.state.db_ready = True
    except Exception as e:
        logger.warning(f"Database init skipped: {e}")
        app.state.db_ready = False

    # AI 服务
    try:
        # 使用模块级单例，确保 ai_config.py 的 reload_config() 能生效
        from app.services.ai_service import ai_service
        app.state.ai_service = ai_service
    except Exception as e:
        logger.warning(f"AI service init skipped: {e}")
        app.state.ai_service = None

    # 搜索服务
    try:
        from app.services.search_service import LiteratureSearchService
        app.state.search_service = LiteratureSearchService()
    except Exception as e:
        logger.warning(f"Search service init skipped: {e}")
        app.state.search_service = None

    # APScheduler: 定时缓存清理 (每小时)
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from app.services.cache_manager import CacheManager
        _scheduler = AsyncIOScheduler()
        _cache_mgr = CacheManager()

        async def _scheduled_cache_cleanup():
            try:
                result = await _cache_mgr.cleanup_expired()
                if result.get("deleted", 0) > 0:
                    logger.info(f"[APScheduler] Cache cleanup: removed {result['deleted']} expired entries")
            except Exception as e:
                logger.warning(f"[APScheduler] Cache cleanup failed: {e}")

        _scheduler.add_job(_scheduled_cache_cleanup, "interval", hours=1, id="cache_cleanup", replace_existing=True)
        _scheduler.start()
        app.state.scheduler = _scheduler
        logger.info("[APScheduler] Scheduled cache cleanup every 1 hour")
    except ImportError:
        logger.warning("APScheduler not installed, scheduled cleanup disabled")
        app.state.scheduler = None
    except Exception as e:
        logger.warning(f"APScheduler setup skipped: {e}")
        app.state.scheduler = None

    logger.info("AcaSight backend started!")
    yield

    logger.info("Shutting down...")
    # 停止调度器
    if hasattr(app.state, "scheduler") and app.state.scheduler:
        app.state.scheduler.shutdown(wait=False)
    # 关闭 AI 连接池
    try:
        from app.services.ai_service import close_http_client
        await close_http_client()
        logger.info("AI httpx connection pool closed")
    except Exception as e:
        logger.warning(f"AI connection pool close failed: {e}")
    try:
        from app.database import close_db
        await close_db()
    except:
        pass


app = FastAPI(
    title="AcaSight API",
    description="学术视界 - PDF阅读 + AI精读 + 文献检索 + 写作辅助",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# 中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Phase 11: 安全中间件 (方向V.4)
try:
    from app.middleware.security import setup_security_middleware
    # 移除旧的 CORS (security middleware 会重新添加)
    # 注意: FastAPI 中间件顺序是后加先执行，需在 CORS 之前添加
    setup_security_middleware(app)
    logger.info("Security middleware loaded")
except Exception as e:
    # 安全中间件加载失败时回退到基础 CORS
    logger.warning(f"Security middleware load failed: {e}, using basic CORS")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error", error=str(exc), path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": str(exc), "path": request.url.path},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail, "path": request.url.path},
    )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    import time as _time
    start = _time.time()
    response = await call_next(request)
    duration = round((_time.time() - start) * 1000, 1)
    if not request.url.path.startswith("/api/docs") and not request.url.path.startswith("/api/redoc"):
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration,
        )
        # 记录到监控服务
        try:
            from app.services.monitoring_service import get_monitoring_service
            svc = get_monitoring_service()
            svc.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration,
                client_ip=request.client.host if request.client else "",
            )
        except Exception:
            pass  # 监控不应阻塞请求
    return response


@app.get("/api/health")
async def health_check():
    info = {"status": "healthy", "version": "2.0.0"}
    services = {}

    if hasattr(app.state, "ai_service") and app.state.ai_service:
        services["ai"] = "ready"
    else:
        services["ai"] = "unavailable"

    services["pdf"] = "ready"

    if hasattr(app.state, "db_ready") and app.state.db_ready:
        services["database"] = "ready"
    else:
        services["database"] = "unavailable"

    if hasattr(app.state, "search_service") and app.state.search_service:
        services["search"] = "ready"
    else:
        services["search"] = "unavailable"

    try:
        from app.services.format_service import get_format_service
        fmt_svc = get_format_service()
        services["format_export"] = "ready" if fmt_svc.available else "pandoc_not_installed"
    except Exception:
        services["format_export"] = "unavailable"

    try:
        from app.agent.modules import list_agents
        agents = list_agents()
        services["agents"] = f"{len(agents)} registered"
    except Exception:
        services["agents"] = "unavailable"

    try:
        from app.services.workflow_engine import get_workflow_engine
        engine = get_workflow_engine()
        flows = engine.list_writing_flows()
        services["workflow"] = f"{len(flows)} active flows"
    except Exception:
        services["workflow"] = "unavailable"

    info["services"] = services

    try:
        from app.routers import papers
        info["routes_loaded"] = True
    except Exception:
        info["routes_loaded"] = False

    return info


# ==================== 路由注册 ====================

# PDF 路由（核心）
try:
    from app.routers import pdf
    app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF"])
    logger.info("PDF router loaded")
except Exception as e:
    logger.warning(f"PDF router load failed: {e}")

# 对话路由
try:
    from app.routers import chat
    app.include_router(chat.router, prefix="/api/chat", tags=["AI 对话"])
    logger.info("Chat router loaded")
except Exception as e:
    logger.warning(f"Chat router load failed: {e}")

# 搜索路由
try:
    from app.routers import search
    app.include_router(search.router, prefix="/api/search", tags=["搜索"])
    logger.info("Search router loaded")
except Exception as e:
    logger.warning(f"Search router load failed: {e}")

# 笔记路由
try:
    from app.routers import notes
    app.include_router(notes.router, prefix="/api/notes", tags=["笔记"])
except Exception:
    pass

# Zotero 路由
try:
    from app.routers import zotero
    app.include_router(zotero.router, prefix="/api/zotero", tags=["Zotero"])
except Exception:
    pass

# Layer 0: 存储管理路由
try:
    from app.routers import storage
    app.include_router(storage.router, prefix="/api/storage", tags=["存储"])
    logger.info("Storage router loaded")
except Exception as e:
    logger.warning(f"Storage router load failed: {e}")

# Layer 0: Zotero 同步路由
try:
    from app.routers import sync
    app.include_router(sync.router, prefix="/api/sync", tags=["同步"])
    logger.info("Sync router loaded")
except Exception as e:
    logger.warning(f"Sync router load failed: {e}")

# Phase 2.6: 全自动 AI 绘图路由
try:
    from app.routers import chart_auto
    app.include_router(chart_auto.router, prefix="/api/chart/auto", tags=["智能绘图"])
    logger.info("Chart auto router loaded")
except Exception as e:
    logger.warning(f"Chart auto router load failed: {e}")

# Agent 编排路由
try:
    from app.routers import agent_orchestration
    app.include_router(agent_orchestration.router, prefix="/api/agent", tags=["Agent 调度"])
    logger.info("Agent orchestration router loaded")
except Exception as e:
    logger.warning(f"Agent orchestration router load failed: {e}")

# Agent 工具对话端点 (function calling 增强)
try:
    from app.routers import agent_tools_api
    app.include_router(agent_tools_api.router, prefix="/api/agent", tags=["Agent 工具对话"])
    logger.info("Agent tools API router loaded")
except Exception as e:
    logger.warning(f"Agent tools API router load failed: {e}")

# 工作流与状态管理
try:
    from app.routers import workflow_api
    app.include_router(workflow_api.router, prefix="/api/system", tags=["工作流与状态"])
    logger.info("Workflow & State router loaded")
except Exception as e:
    logger.warning(f"Workflow & State router load failed: {e}")

# Phase 4: 智能写作助手路由
try:
    from app.routers import writing
    app.include_router(writing.router, prefix="/api/writing", tags=["智能写作"])
    logger.info("Writing router loaded")
except Exception as e:
    logger.warning(f"Writing router load failed: {e}")

# 文献结构化路由
try:
    from app.routers import literature
    app.include_router(literature.router, prefix="/api/literature", tags=["文献结构化"])
    logger.info("Literature router loaded")
except Exception as e:
    logger.warning(f"Literature router load failed: {e}")

# AI 配置路由
try:
    from app.routers import ai_config
    app.include_router(ai_config.router, prefix="/api/ai", tags=["AI 配置"])
    logger.info("AI config router loaded")
except Exception as e:
    logger.warning(f"AI config router load failed: {e}")

# Chapter C: 论文数据库 CRUD 路由
try:
    from app.routers import papers
    app.include_router(papers.router, prefix="/api/papers", tags=["论文数据库"])
    logger.info("Papers router loaded")
except Exception as e:
    logger.warning(f"Papers router load failed: {e}")

# Chapter D: 批注路由
try:
    from app.routers import annotations
    app.include_router(annotations.router, prefix="/api/annotations", tags=["批注"])
    logger.info("Annotations router loaded")
except Exception as e:
    logger.warning(f"Annotations router load failed: {e}")

# Chapter 8: 学术 Agent 路由
try:
    from app.agent.router import router as agent_router
    app.include_router(agent_router, tags=["学术 Agent"])
    logger.info("Agent router loaded")
except Exception as e:
    logger.warning(f"Agent router load failed: {e}")

# Chapter H: 引用图谱路由
try:
    from app.routers import knowledge_graph
    app.include_router(knowledge_graph.router, prefix="/api/knowledge", tags=["引用图谱"])
    logger.info("Knowledge graph router loaded")
except Exception as e:
    logger.warning(f"Knowledge graph router load failed: {e}")

# Chapter I: RAG 问答路由
try:
    from app.routers import rag
    app.include_router(rag.router, prefix="/api/rag", tags=["RAG 问答"])
    logger.info("RAG router loaded")
except Exception as e:
    logger.warning(f"RAG router load failed: {e}")

# Chapter J: 学术格式导出路由
try:
    from app.routers import format_export
    app.include_router(format_export.router, prefix="/api/format", tags=["格式导出"])
    logger.info("Format export router loaded")
except Exception as e:
    logger.warning(f"Format export router load failed: {e}")

# 模板路由
try:
    from app.routers import template
    app.include_router(template.router, prefix="/api/templates", tags=["模板"])
    logger.info("Template router loaded")
except Exception as e:
    logger.warning(f"Template router load failed: {e}")

# Phase 10: PaperBanana 图表生成 Pipeline
try:
    from app.routers import paper_banana
    app.include_router(paper_banana.router, prefix="/api")
    logger.info("PaperBanana router loaded")
except Exception as e:
    logger.warning(f"PaperBanana router load failed: {e}")

# Phase 10: Deep Research 多步骤研究 Pipeline
try:
    from app.routers import deep_research
    app.include_router(deep_research.router, prefix="/api")
    logger.info("Deep Research router loaded")
except Exception as e:
    logger.warning(f"Deep Research router load failed: {e}")

# Phase 10: Figure Edit SVG 矢量图编辑 (AutoFigure-Edit)
try:
    from app.routers import figure_edit
    app.include_router(figure_edit.router, prefix="/api")
    logger.info("Figure Edit router loaded")
except Exception as e:
    logger.warning(f"Figure Edit router load failed: {e}")

# Phase 10: Architecture 架构优化服务 (方向P)
try:
    from app.routers import arch
    app.include_router(arch.router, prefix="/api")
    logger.info("Architecture router loaded")
except Exception as e:
    logger.warning(f"Architecture router load failed: {e}")

# Phase 10: Plugin System 插件系统 (方向Q)
try:
    from app.routers import plugins
    app.include_router(plugins.router, prefix="/api")
    logger.info("Plugins router loaded")
except Exception as e:
    logger.warning(f"Plugins router load failed: {e}")

# Phase 11: Workspace State 工作区状态 (方向T)
try:
    from app.routers import workspace_state
    app.include_router(workspace_state.router, prefix="/api")
    logger.info("Workspace State router loaded")
except Exception as e:
    logger.warning(f"Workspace State router load failed: {e}")

# Phase 11: Version History + Writing Templates (方向U)
try:
    from app.routers import version_and_templates
    app.include_router(version_and_templates.vh_router, prefix="/api")
    app.include_router(version_and_templates.wt_router, prefix="/api")
    logger.info("Version History + Templates router loaded")
except Exception as e:
    logger.warning(f"Version History + Templates router load failed: {e}")

try:
    from app.routers import monitoring
    app.include_router(monitoring.router)
    logger.info("Monitoring router loaded")
except Exception as e:
    logger.warning(f"Monitoring router load failed: {e}")

try:
    from app.routers import data_preprocess
    app.include_router(data_preprocess.router, prefix="/api/data-preprocess", tags=["数据预处理"])
    logger.info("Data Preprocess router loaded")
except Exception as e:
    logger.warning(f"Data Preprocess router load failed: {e}")

try:
    from app.routers import dblp
    app.include_router(dblp.router, prefix="/api/dblp", tags=["DBLP检索"])
    logger.info("DBLP router loaded")
except Exception as e:
    logger.warning(f"DBLP router load failed: {e}")

# AI参考文献提取路由
try:
    from app.routers import citations
    app.include_router(citations.router, prefix="/api", tags=["AI参考文献提取"])
    logger.info("Citations router loaded")
except Exception as e:
    logger.warning(f"Citations router load failed: {e}")

# AI文献表格路由
try:
    from app.routers import literature_table
    app.include_router(literature_table.router, prefix="/api", tags=["AI文献表格"])
    logger.info("Literature table router loaded")
except Exception as e:
    logger.warning(f"Literature table router load failed: {e}")

# 文献综述MVP路由
try:
    from app.routers import literature_review
    app.include_router(literature_review.router, prefix="/api", tags=["文献综述"])
    logger.info("Literature review router loaded")
except Exception as e:
    logger.warning(f"Literature review router load failed: {e}")

# AI白板头脑风暴路由
try:
    from app.routers import brainstorm
    app.include_router(brainstorm.router, prefix="/api", tags=["AI白板头脑风暴"])
    logger.info("Brainstorm router loaded")
except Exception as e:
    logger.warning(f"Brainstorm router load failed: {e}")

# ── 前端静态文件 ──
from pathlib import Path
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # 先挂 API 路由，再挂静态文件 — 确保 API 优先
    # SPA fallback: 只处理非 /api 路径（API 路由由各 router 自行处理）
    from fastapi.responses import FileResponse
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        # 跳过 /api/ 路径，让 API routers 处理
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"API endpoint not found: /{full_path}")
        
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    logger.info(f"Frontend static: {frontend_dist}")
else:
    logger.warning(f"Frontend dist not found: {frontend_dist}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )