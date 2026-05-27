"""
AcaSight 后端主应用 - 融合 PaperPal + pdf-research-assistant
FastAPI + PDF处理 + AI + 文献检索
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting AcaSight backend...")

    # 数据库初始化（可选，跳过失败）
    try:
        from app.database import init_db, close_db
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

    logger.info("AcaSight backend started!")
    yield

    logger.info("Shutting down...")
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/api/health")
async def health_check():
    info = {"status": "healthy", "version": "2.0.0"}
    try:
        services = {}
        if hasattr(app.state, "ai_service") and app.state.ai_service:
            services["ai"] = "ready"
        else:
            services["ai"] = "unavailable"
        services["pdf"] = "ready"
        info["services"] = services
    except:
        pass
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

# Phase 4: 智能写作助手路由
try:
    from app.routers import writing
    app.include_router(writing.router, prefix="/api/writing", tags=["智能写作"])
    logger.info("Writing router loaded")
except Exception as e:
    logger.warning(f"Writing router load failed: {e}")

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

# ── 前端静态文件 ──
from pathlib import Path
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # 先挂 API 路由，再挂静态文件 — 确保 API 优先
    # SPA fallback: 所有非 /api 路径返回 index.html
    from fastapi.responses import FileResponse
    
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "Not found"}, status_code=404)
        
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
        port=9000,
        reload=True,
        log_level="info",
    )