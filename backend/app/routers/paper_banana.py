"""
PaperBanana 图表生成 Pipeline 路由

M.1: Pipeline 核心 — 6-Agent 插图生成
M.2: 代码沙箱执行器
M.3: Critic 评估循环
M.4: SCI 期刊风格指南
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from app.services.paper_banana_service import (
    generate_figure_pipeline,
    get_available_styles,
)

router = APIRouter(prefix="/paper-banana", tags=["PaperBanana 图表生成"])


# ==================== 请求模型 ====================

class GeneratePlotRequest(BaseModel):
    """统计图生成请求"""
    data: str = Field(..., description="原始数据(JSON/CSV/表格文本)")
    visual_intent: str = Field(..., description="图表意图/标题")
    style_guide: str = Field(default="nature", description="风格指南: nature/ieee/elsevier")
    max_critic_rounds: int = Field(default=3, ge=0, le=5, description="最大评估轮数")
    references: Optional[List[Dict]] = Field(default=None, description="参考图表(可选)")


class GenerateDiagramRequest(BaseModel):
    """方法图生成请求"""
    methodology: str = Field(..., description="方法论文本")
    caption: str = Field(..., description="图表标题")
    style_guide: str = Field(default="nature", description="风格指南: nature/ieee/elsevier")
    max_critic_rounds: int = Field(default=3, ge=0, le=5, description="最大评估轮数")


class ExecutePlotCodeRequest(BaseModel):
    """直接执行 matplotlib 代码"""
    code: str = Field(..., description="matplotlib Python 代码")


# ==================== API 端点 ====================

@router.post("/generate-plot")
async def api_generate_plot(req: GeneratePlotRequest):
    """统计图生成 Pipeline (数据→描述→代码→执行→评估→修正)"""
    result = await generate_figure_pipeline(
        content=req.data,
        visual_intent=req.visual_intent,
        task_type="plot",
        style_guide=req.style_guide,
        max_critic_rounds=req.max_critic_rounds,
        references=req.references,
    )
    return {"success": True, "data": result}


@router.post("/generate-diagram")
async def api_generate_diagram(req: GenerateDiagramRequest):
    """方法图生成 Pipeline (文本→描述→图像→评估→修正)
    
    注意: diagram 生成需要图像生成API(Gemini/GPT-Image)，
    当前版本仅返回描述，图像生成需要配置对应 provider。
    """
    result = await generate_figure_pipeline(
        content=req.methodology,
        visual_intent=req.caption,
        task_type="diagram",
        style_guide=req.style_guide,
        max_critic_rounds=req.max_critic_rounds,
    )
    return {"success": True, "data": result}


@router.post("/execute-plot-code")
async def api_execute_plot_code(req: ExecutePlotCodeRequest):
    """直接执行 matplotlib 代码并返回图像 (沙箱隔离)"""
    from app.services.paper_banana_service import _execute_plot_code
    import asyncio
    
    loop = asyncio.get_running_loop()
    from concurrent.futures import ProcessPoolExecutor
    executor = ProcessPoolExecutor(max_workers=2)
    
    try:
        base64_jpg = await loop.run_in_executor(executor, _execute_plot_code, req.code)
        if base64_jpg:
            return {"success": True, "image_base64": base64_jpg}
        else:
            return {"success": False, "error": "代码执行完成但未生成图像（可能没有调用绘图函数）"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        executor.shutdown(wait=False)


@router.get("/styles")
async def api_get_styles():
    """获取可用的 SCI 期刊风格指南列表"""
    return {"styles": get_available_styles()}
