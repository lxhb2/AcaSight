"""
性能监控 API 路由 (方向V.3)

端点:
- GET  /api/monitoring/dashboard    — 完整仪表盘数据
- GET  /api/monitoring/health        — 健康度评分
- GET  /api/monitoring/requests      — API请求统计
- GET  /api/monitoring/system        — 系统资源统计
- GET  /api/monitoring/web-vitals    — 前端 Web Vitals 统计
- POST /api/monitoring/web-vitals    — 上报 Web Vitals
- GET  /api/monitoring/slowest       — 最慢端点
- GET  /api/monitoring/errors        — Top错误
"""

from typing import Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from app.services.monitoring_service import get_monitoring_service

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class WebVitalReport(BaseModel):
    """Web Vitals 上报"""
    metric_name: str = Field(..., description="LCP/FID/CLS/TTFB/INP/FCP/TBT")
    value: float = Field(..., description="指标值(ms或分数)")
    url: str = Field("", description="页面URL")
    user_agent: str = Field("", description="User-Agent")


@router.get("/dashboard")
async def get_dashboard():
    """完整仪表盘数据"""
    service = get_monitoring_service()
    return {"success": True, "data": service.get_dashboard_data()}


@router.get("/health")
async def get_health_score():
    """健康度评分"""
    service = get_monitoring_service()
    score = service.calculate_health_score()
    return {"success": True, "data": score.__dict__}


@router.get("/requests")
async def get_request_stats(
    minutes: int = Query(60, ge=1, le=1440, description="统计时间范围(分钟)"),
):
    """API请求统计"""
    service = get_monitoring_service()
    return {"success": True, "data": service.get_request_stats(minutes)}


@router.get("/system")
async def get_system_stats(
    minutes: int = Query(60, ge=1, le=1440, description="统计时间范围(分钟)"),
):
    """系统资源统计"""
    service = get_monitoring_service()
    return {"success": True, "data": service.get_system_stats(minutes)}


@router.get("/web-vitals")
async def get_web_vitals_stats(
    minutes: int = Query(60, ge=1, le=1440, description="统计时间范围(分钟)"),
):
    """前端 Web Vitals 统计"""
    service = get_monitoring_service()
    return {"success": True, "data": service.get_web_vitals_stats(minutes)}


@router.post("/web-vitals")
async def report_web_vital(report: WebVitalReport, request: Request):
    """上报 Web Vitals 指标"""
    service = get_monitoring_service()
    ua = report.user_agent or request.headers.get("user-agent", "")
    service.record_web_vital(
        metric_name=report.metric_name,
        value=report.value,
        url=report.url,
        user_agent=ua,
    )
    return {"success": True, "message": "Web vital recorded"}


@router.get("/slowest")
async def get_slowest_endpoints(
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """最慢的端点"""
    service = get_monitoring_service()
    return {"success": True, "data": service._get_slowest_endpoints(limit)}


@router.get("/errors")
async def get_top_errors(
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """Top错误"""
    service = get_monitoring_service()
    return {"success": True, "data": service._get_top_errors(limit)}
