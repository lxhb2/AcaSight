"""
Figure Edit API 路由 — SVG 矢量图编辑 (方向N)

端点:
- POST /api/figure-edit/method-to-svg   — 完整流程: method→SVG
- POST /api/figure-edit/segment          — SAM3 图标分割
- POST /api/figure-edit/generate-svg     — 多模态 LLM 生成 SVG
- POST /api/figure-edit/replace-icons    — 图标替换到 SVG
- GET  /api/figure-edit/status           — 服务状态 (SAM3 可用性)
"""

import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.figure_edit_service import method_to_svg, _generate_figure_image, _segment_icons, _generate_svg_template, _replace_icons_in_svg, _optimize_svg, _validate_svg, _fix_svg_with_llm
from app.services.sam_segmenter import sam3_segmenter, SAM3Segmenter
from PIL import Image

import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/figure-edit", tags=["Figure Edit 矢量图编辑"])


# ==================== 请求模型 ====================

class MethodToSvgRequest(BaseModel):
    """Method→SVG 完整流程请求"""
    method_text: str = Field(..., min_length=5, max_length=10000, description="Paper method 文本")
    sam_prompts: str = Field(default="icon", description="SAM3 text prompt (逗号分隔)")
    placeholder_mode: str = Field(default="label", description="占位符模式: none/box/label")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="SAM3 最低置信度")
    merge_threshold: float = Field(default=0.9, ge=0.0, le=1.0, description="Box 合并阈值")
    optimize_iterations: int = Field(default=2, ge=0, le=5, description="SVG 优化迭代次数")
    input_figure_base64: Optional[str] = Field(None, description="已有图片 Base64 (跳过步骤一生图)")


class SegmentRequest(BaseModel):
    """SAM3 分割请求"""
    image_base64: Optional[str] = Field(None, description="Base64 图片")
    prompts: str = Field(default="icon", description="SAM3 text prompt")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0)
    merge_threshold: float = Field(default=0.9, ge=0.0, le=1.0)


class GenerateSvgRequest(BaseModel):
    """SVG 生成请求"""
    figure_base64: str = Field(..., description="原始图片 Base64")
    samed_base64: Optional[str] = Field(None, description="SAM 标记图片 Base64")
    boxlib_json: Optional[Dict] = Field(None, description="boxlib JSON")
    placeholder_mode: str = Field(default="label", description="none/box/label")


class ReplaceIconsRequest(BaseModel):
    """图标替换请求"""
    svg_base64: str = Field(..., description="SVG 模板 Base64")
    icons: List[Dict[str, Any]] = Field(..., description="图标信息列表 [{label, icon_base64}]")


class FixSvgRequest(BaseModel):
    """SVG 修复请求"""
    svg_code: str = Field(..., description="待修复的 SVG 代码")


# ==================== API 端点 ====================

@router.post("/method-to-svg")
async def api_method_to_svg(req: MethodToSvgRequest):
    """
    完整流程: Method 文本 → SVG 矢量图

    5 步流水线:
    1. 生成学术风格图片
    2. SAM3 分割图标区域
    3. 裁切 + 去背景
    4. 多模态 LLM 生成 SVG 模板
    5. 图标替换
    """
    if req.placeholder_mode not in ("none", "box", "label"):
        raise HTTPException(400, f"Invalid placeholder_mode: {req.placeholder_mode}")

    # 创建临时输出目录
    output_dir = tempfile.mkdtemp(prefix="acasight_figure_")

    try:
        # 如果用户上传了已有图片，直接使用跳过生图步骤
        if req.input_figure_base64:
            import base64 as b64mod, io as iomod
            fig_data = b64mod.b64decode(req.input_figure_base64)
            fig_img = Image.open(iomod.BytesIO(fig_data))
            figure_path = os.path.join(output_dir, "figure.png")
            fig_img.save(figure_path)
        
        result = await method_to_svg(
            method_text=req.method_text,
            output_dir=output_dir,
            sam_prompts=req.sam_prompts,
            placeholder_mode=req.placeholder_mode,
            min_score=req.min_score,
            merge_threshold=req.merge_threshold,
            optimize_iterations=req.optimize_iterations,
        )

        # 读取最终 SVG
        final_svg_path = result.get("final_svg", "")
        svg_content = ""
        if final_svg_path and os.path.exists(final_svg_path):
            with open(final_svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()

        return {
            "success": True,
            "data": {
                "svg_content": svg_content,
                "icon_count": len(result.get("icon_infos", [])),
                "files": {
                    "figure": result.get("figure_path"),
                    "samed": result.get("samed_path"),
                    "boxlib": result.get("boxlib_path"),
                    "template_svg": result.get("template_svg"),
                    "final_svg": result.get("final_svg"),
                },
            },
        }

    except Exception as e:
        logger.error("method-to-svg failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/segment")
async def api_segment(req: SegmentRequest):
    """SAM3 图标/区域分割"""
    if not req.image_base64:
        raise HTTPException(400, "image_base64 is required")

    try:
        import base64, io
        img_data = base64.b64decode(req.image_base64)
        img = Image.open(io.BytesIO(img_data))

        result = await sam3_segmenter.segment(
            image=img,
            prompts=req.prompts,
            min_score=req.min_score,
            merge_threshold=req.merge_threshold,
        )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error("Segmentation failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/generate-svg")
async def api_generate_svg(req: GenerateSvgRequest):
    """多模态 LLM 生成 SVG 模板"""
    import base64, io, tempfile

    temp_dir = tempfile.mkdtemp(prefix="acasight_svg_")

    try:
        # 保存图片
        fig_data = base64.b64decode(req.figure_base64)
        fig_img = Image.open(io.BytesIO(fig_data))
        figure_path = os.path.join(temp_dir, "figure.png")
        fig_img.save(figure_path)

        # SAM 标记图
        samed_path = figure_path  # 默认用原图
        if req.samed_base64:
            samed_data = base64.b64decode(req.samed_base64)
            samed_img = Image.open(io.BytesIO(samed_data))
            samed_path = os.path.join(temp_dir, "samed.png")
            samed_img.save(samed_path)

        # boxlib
        boxlib_path = os.path.join(temp_dir, "boxlib.json")
        import json
        with open(boxlib_path, "w") as f:
            json.dump(req.boxlib_json or {"detections": [], "image_size": list(fig_img.size)}, f)

        # 生成 SVG
        output_path = os.path.join(temp_dir, "template.svg")
        svg_code = await _generate_svg_template(
            figure_path=figure_path,
            samed_path=samed_path,
            boxlib_path=boxlib_path,
            output_path=output_path,
            placeholder_mode=req.placeholder_mode,
        )

        return {"success": True, "data": {"svg_code": svg_code}}

    except Exception as e:
        logger.error("SVG generation failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/replace-icons")
async def api_replace_icons(req: ReplaceIconsRequest):
    """图标替换到 SVG"""
    import base64, io, tempfile, json

    temp_dir = tempfile.mkdtemp(prefix="acasight_replace_")

    try:
        # 保存 SVG 模板
        svg_path = os.path.join(temp_dir, "template.svg")
        svg_code = base64.b64decode(req.svg_base64).decode("utf-8")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_code)

        # 保存图标
        icon_infos = []
        for i, icon in enumerate(req.icons):
            label = icon.get("label", f"<AF>{i+1:02d}")
            icon_b64 = icon.get("icon_base64", "")
            if icon_b64:
                icon_data = base64.b64decode(icon_b64)
                icon_img = Image.open(io.BytesIO(icon_data))
                nobg_path = os.path.join(temp_dir, f"icon_{i:02d}_nobg.png")
                icon_img.save(nobg_path)
                icon_infos.append({
                    "label": label,
                    "label_clean": label.replace("<", "").replace(">", ""),
                    "nobg_path": nobg_path,
                })

        # 替换
        output_path = os.path.join(temp_dir, "final.svg")
        final_svg = _replace_icons_in_svg(
            svg_path=svg_path,
            icon_infos=icon_infos,
            output_path=output_path,
        )

        return {"success": True, "data": {"svg_code": final_svg}}

    except Exception as e:
        logger.error("Icon replacement failed", error=str(e))
        raise HTTPException(500, str(e))


@router.post("/fix-svg")
async def api_fix_svg(req: FixSvgRequest):
    """SVG 语法修复"""
    try:
        # 先验证
        valid, errors = _validate_svg(req.svg_code)
        if valid:
            return {"success": True, "data": {"svg_code": req.svg_code, "was_valid": True, "errors": []}}

        # 修复
        fixed = await _fix_svg_with_llm(req.svg_code)
        valid2, errors2 = _validate_svg(fixed)

        return {
            "success": True,
            "data": {
                "svg_code": fixed,
                "was_valid": valid2,
                "errors": errors2 if not valid2 else [],
                "original_errors": errors,
            },
        }

    except Exception as e:
        logger.error("SVG fix failed", error=str(e))
        raise HTTPException(500, str(e))


@router.get("/status")
async def api_status():
    """服务状态 (SAM3 可用性等)"""
    segmenter = SAM3Segmenter()

    return {
        "success": True,
        "data": {
            "sam3_available": segmenter.available,
            "sam3_backend": segmenter.backend,
            "placeholder_modes": ["none", "box", "label"],
            "features": {
                "method_to_svg": True,
                "segment": segmenter.available,
                "generate_svg": True,
                "replace_icons": True,
                "fix_svg": True,
                "optimize_svg": True,
            },
        },
    }
