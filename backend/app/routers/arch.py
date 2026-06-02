"""
Architecture API 路由 — 方向P 架构优化服务

端点:
- POST /api/arch/evaluate-visual  — 图表视觉评估
- POST /api/arch/pipeline         — Stage Pipeline 执行
- POST /api/arch/detect-loop      — Agent 循环检测 (手动)
- POST /api/arch/format           — AI 响应格式化
- GET  /api/arch/status           — 架构服务状态
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.visual_evaluator import visual_evaluator, SCI_STYLE_CRITERIA
from app.services.stage_orchestrator import (
    StageOrchestrator,
    StageDefinition,
    RetryPolicy,
    RetryStrategy,
    create_pipeline,
)
from app.agent.loop_detector import LoopDetector
from app.services.ai_formatter import ai_formatter, OutputFormat

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/arch", tags=["架构优化服务"])


# ==================== 请求模型 ====================

class VisualEvalRequest(BaseModel):
    """视觉评估请求"""
    image_base64: str = Field(..., description="待评估图片 Base64")
    criteria: Optional[str] = Field(None, description="评估标准描述")
    style: str = Field(default="default", description="SCI 风格: nature/ieee/elsevier/default")
    max_retries: int = Field(default=3, ge=1, le=10, description="最大重试次数")


class PipelineRequest(BaseModel):
    """Stage Pipeline 请求"""
    pipeline_id: str = Field(..., description="Pipeline ID")
    stages: List[Dict[str, Any]] = Field(..., description="Stage 定义列表")
    initial_params: Optional[Dict[str, Any]] = Field(None, description="初始参数")
    max_concurrent: int = Field(default=4, ge=1, le=16, description="最大并发数")


class LoopDetectRequest(BaseModel):
    """循环检测请求"""
    tool_calls: List[Dict[str, Any]] = Field(..., description="工具调用记录 [{name, args}]")


class FormatRequest(BaseModel):
    """AI 响应格式化请求"""
    raw_response: str = Field(..., description="AI 原始响应")
    expected_format: str = Field(default="text", description="期望格式: text/json/markdown/svg/code/list")
    strict: bool = Field(default=False, description="严格模式")


# ==================== API 端点 ====================

@router.post("/evaluate-visual")
async def api_visual_evaluate(req: VisualEvalRequest):
    """
    图表视觉评估 — VL模型评估图表质量

    支持评估+修复循环: 评估 → 不通过 → 反馈 → 修复 → 重新评估
    """
    if req.style not in SCI_STYLE_CRITERIA:
        raise HTTPException(400, f"Invalid style: {req.style}. Available: {list(SCI_STYLE_CRITERIA.keys())}")

    try:
        result = await visual_evaluator.evaluate(
            image_base64=req.image_base64,
            criteria=req.criteria,
            style=req.style,
            max_retries=req.max_retries,
        )

        return {
            "success": True,
            "data": result.to_dict(),
        }

    except Exception as e:
        logger.error("Visual evaluation failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/pipeline")
async def api_pipeline(req: PipelineRequest):
    """
    Stage Pipeline 执行 — DAG 并行编排

    支持: 依赖图、并行执行、重试策略、回滚
    """
    try:
        # 构建 Stage 定义
        stages = []
        for s in req.stages:
            retry_policy = RetryPolicy()
            if "retry_policy" in s:
                rp = s["retry_policy"]
                retry_policy = RetryPolicy(
                    strategy=RetryStrategy(rp.get("strategy", "exponential")),
                    max_retries=rp.get("max_retries", 3),
                    base_delay=rp.get("base_delay", 1.0),
                    max_delay=rp.get("max_delay", 60.0),
                )

            stage = StageDefinition(
                stage_id=s["stage_id"],
                name=s.get("name", s["stage_id"]),
                dependencies=s.get("dependencies", []),
                timeout=s.get("timeout", 300.0),
                retry_policy=retry_policy,
                critical=s.get("critical", True),
                params=s.get("params", {}),
            )
            stages.append(stage)

        orchestrator = create_pipeline(
            pipeline_id=req.pipeline_id,
            stages=stages,
            max_concurrent=req.max_concurrent,
        )

        result = await orchestrator.execute(req.initial_params or {})

        return {
            "success": True,
            "data": {
                "pipeline_id": result.pipeline_id,
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "stages": {
                    sid: {
                        "status": sr.status.value,
                        "error": sr.error,
                        "attempts": sr.attempts,
                        "duration_seconds": sr.duration_seconds,
                    }
                    for sid, sr in result.stages.items()
                },
                "snapshot": result.snapshot,
            },
        }

    except Exception as e:
        logger.error("Pipeline execution failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/detect-loop")
async def api_detect_loop(req: LoopDetectRequest):
    """
    Agent 循环检测 (手动触发)

    输入工具调用记录，返回检测结果
    """
    try:
        detector = LoopDetector(max_repeats=3)
        detections = []

        for tc in req.tool_calls:
            detection = detector.record_tool_call(
                tool_name=tc.get("name", ""),
                args=tc.get("args", {}),
            )
            if detection.is_looping:
                detections.append({
                    "is_looping": True,
                    "loop_type": detection.loop_type.value,
                    "details": detection.details,
                    "suggestion": detection.suggestion,
                })

        stats = detector.get_stats()

        return {
            "success": True,
            "data": {
                "is_looping": detector.is_looping(),
                "detections": detections,
                "stats": stats,
            },
        }

    except Exception as e:
        logger.error("Loop detection failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/format")
async def api_format(req: FormatRequest):
    """
    AI 响应格式化

    支持: text/json/markdown/svg/code/list
    自动修复常见格式问题 (BOM、代码围栏、JSON 修复等)
    """
    try:
        expected = OutputFormat(req.expected_format)
    except ValueError:
        raise HTTPException(400, f"Invalid format: {req.expected_format}. Available: {[f.value for f in OutputFormat]}")

    try:
        result = ai_formatter.format(req.raw_response, expected, strict=req.strict)

        return {
            "success": result.success,
            "data": {
                "format": result.format.value,
                "content": result.content,
                "warnings": result.warnings,
                "extracted_from": result.extracted_from,
            },
        }

    except Exception as e:
        logger.error("Format failed", error=str(e))
        raise HTTPException(500, str(e))


@router.get("/status")
async def api_status():
    """架构服务状态"""
    return {
        "success": True,
        "data": {
            "visual_evaluator": True,
            "stage_orchestrator": True,
            "loop_detector": True,
            "ai_formatter": True,
            "sci_styles": list(SCI_STYLE_CRITERIA.keys()),
            "output_formats": [f.value for f in OutputFormat],
            "retry_strategies": [s.value for s in RetryStrategy],
        },
    }
