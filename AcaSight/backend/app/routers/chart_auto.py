"""
全自动绘图端点 — AI 分析数据 → 推荐图表配置
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from app.services.ai_service import ai_service
import structlog

logger = structlog.get_logger()
router = APIRouter()


class AutoChartRequest(BaseModel):
    description: str = Field(default="", description="用户用自然语言描述想要的图表")
    columns: List[dict] = Field(default_factory=list, description="[{key, label, type}]")
    sample_data: List[dict] = Field(default_factory=list, description="前3行样本数据")
    total_rows: int = Field(default=0)


class AutoChartResponse(BaseModel):
    chart_type: str = "scatter"
    x_col: str = ""
    y_cols: List[str] = Field(default_factory=list)
    title: str = ""
    reason: str = ""


SYSTEM_PROMPT = """你是一个学术数据可视化专家。用户提供列定义、样本数据和需求描述，你推荐最佳图表配置。

规则：
1. 散点图(scatter): 两个数值列，看相关性/分布
2. 折线图(line): X 是时间/序列，Y 是数值趋势；mode 自动为 lines+markers
3. 柱状图(bar): X 是类别，Y 是数值比较
4. 饼图(pie): 类别占比分析，hole 用 0.4
5. 直方图(histogram): 单列数值分布
6. 箱线图(box): 数值列的统计概要
7. 热力图(heatmap): 两个类别维度 + 数值密度
8. 3D-scatter: 三个数值列的空间分布

输出格式（严格 JSON，不要 markdown 代码块）：
{"chart_type":"bar","x_col":"期刊","y_cols":["引用数"],"title":"期刊引用数对比","reason":"柱状图最适合类别对比"}

注意：
- chart_type 必须是 scatter/line/bar/pie/histogram/box/heatmap/3d-scatter 之一
- x_col 必须是列定义中的某个 key
- y_cols 必须是列定义中的 key 数组
- 只输出纯 JSON，不要解释，不要代码块标记"""


class RefineChartRequest(BaseModel):
    description: str = Field(default="", description="用户反馈/优化需求")
    current_config: dict = Field(default_factory=dict, description="当前图表配置")
    columns: List[dict] = Field(default_factory=list, description="[{key, label, type}]")
    sample_data: List[dict] = Field(default_factory=list, description="前3行样本数据")
    total_rows: int = Field(default=0)


REFINE_SYSTEM_PROMPT = """你是一个学术数据可视化向导。用户当前有一个图表配置，想要优化它。根据用户反馈调整配置。

当前配置将作为 JSON 提供。你可以修改 chart_type、x_col、y_cols、title、fit_type、legend_position、academic_mode 等字段。

输出格式（严格 JSON，不要 markdown 代码块）：
{"chart_type":"line","x_col":"angle","y_cols":["intensity"],"title":"XRD衍射图","reason":"折线图更适合展示XRD谱","fit_type":null,"legend_position":"right","academic_mode":true}

只输出纯 JSON，不要解释，不要代码块标记。"""


@router.post("/", response_model=AutoChartResponse)
async def auto_chart(req: AutoChartRequest):
    """
    AI 自动推荐图表配置。
    传入列定义、样本数据和用户描述，返回推荐的图表类型、轴映射和标题。
    """
    # 构建用户消息
    parts = []
    if req.description.strip():
        parts.append(f"用户需求: {req.description.strip()}")
    if req.columns:
        cols_desc = ", ".join(
            f"{c.get('label', c.get('key', '?'))}({c.get('type', '?')})"
            for c in req.columns
        )
        parts.append(f"列定义: [{cols_desc}]")
    if req.sample_data:
        sample_str = json.dumps(req.sample_data[:3], ensure_ascii=False, default=str)
        parts.append(f"样本数据(前3行): {sample_str}")
    parts.append(f"总行数: {req.total_rows}")

    user_message = "\n".join(parts)

    try:
        # chat() is an async generator; collect all chunks
        text_parts: list[str] = []
        async for chunk in ai_service.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            temperature=0.3,
        ):
            text_parts.append(chunk)
        text = "".join(text_parts)
        # 清理可能的 markdown 包裹
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        config = json.loads(text)
        return AutoChartResponse(
            chart_type=config.get("chart_type", "scatter"),
            x_col=config.get("x_col", ""),
            y_cols=config.get("y_cols", []),
            title=config.get("title", ""),
            reason=config.get("reason", ""),
        )
    except json.JSONDecodeError as e:
        logger.warning("AI chart response parse failed", text=text[:200], error=str(e))
        raise HTTPException(status_code=422, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        logger.error("Auto chart failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"自动推荐失败: {e}")


@router.post("/refine", response_model=AutoChartResponse)
async def refine_chart(req: RefineChartRequest):
    """
    半自动向导：基于当前配置和用户反馈，AI 建议优化方案。
    """
    parts = []
    if req.current_config:
        parts.append(f"当前配置: {json.dumps(req.current_config, ensure_ascii=False)}")
    if req.description.strip():
        parts.append(f"用户反馈: {req.description.strip()}")
    if req.columns:
        cols_desc = ", ".join(
            f"{c.get('label', c.get('key', '?'))}({c.get('type', '?')})"
            for c in req.columns
        )
        parts.append(f"列定义: [{cols_desc}]")
    if req.sample_data:
        sample_str = json.dumps(req.sample_data[:3], ensure_ascii=False, default=str)
        parts.append(f"样本数据(前3行): {sample_str}")
    parts.append(f"总行数: {req.total_rows}")

    user_message = "\n".join(parts)

    try:
        text_parts: list[str] = []
        async for chunk in ai_service.chat(
            messages=[
                {"role": "system", "content": REFINE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=False,
            temperature=0.3,
        ):
            text_parts.append(chunk)
        text = "".join(text_parts)
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        config = json.loads(text)
        return AutoChartResponse(
            chart_type=config.get("chart_type", req.current_config.get("chart_type", "scatter")),
            x_col=config.get("x_col", req.current_config.get("x_col", "")),
            y_cols=config.get("y_cols", req.current_config.get("y_cols", [])),
            title=config.get("title", ""),
            reason=config.get("reason", ""),
        )
    except json.JSONDecodeError as e:
        logger.warning("AI refine response parse failed", text=text[:200], error=str(e))
        raise HTTPException(status_code=422, detail=f"AI 返回格式错误: {e}")
    except Exception as e:
        logger.error("Refine chart failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"优化推荐失败: {e}")