"""
Figure Edit Service — AutoFigure-Edit 融合版 (方向N.1)

功能:
- method_text → 学术风格图片生成 (调用 ai_service image model)
- SAM3 图标分割 (API 模式，通过 _call_sam3_api)
- 图标裁剪 + RMBG2 去背景
- 多模态 LLM 生成 SVG 模板 (占位符模式: none/box/label)
- SVG 语法验证 + LLM 修复
- SVG 优化 (迭代优化)
- 图标替换到 SVG (base64 嵌入或替换占位符)

设计:
- 复用 AcaSight ai_service (task_type="figure_edit")
- 复用全局 httpx 连接池
- SAM3 后端: fal.ai API / Roboflow API / 本地 (可选)
- 输出: final.svg + final.png (SVG rasterized)

依赖: Pillow, requests, base64, io, re, json, structlog
可选: librosa, numpy (SAM3 本地), rembg
"""

import base64
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import structlog
from PIL import Image

from app.services.ai_service import ai_service, get_http_client

logger = structlog.get_logger()

# ── 配置 ──

SAM3_BACKEND = os.getenv("SAM3_BACKEND", "fal")  # fal / roboflow / local / api
SAM3_API_KEY = os.getenv("SAM3_API_KEY", "")
SAM3_FAL_MODEL = os.getenv("SAM3_FAL_MODEL", "fal-ai/sam3")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_ENDPOINT = os.getenv("ROBOFLOW_ENDPOINT", "")

RMBG_MODEL_PATH = os.getenv("RMBG_MODEL_PATH", "")

PLACEHOLDER_MODES = ("none", "box", "label")


# ── 辅助函数 ──

def _pil_to_base64(img: Image.Image) -> str:
    """PIL Image → base64 PNG"""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _pil_to_data_uri(img: Image.Image) -> str:
    return f"data:image/png;base64,{_pil_to_base64(img)}"


async def _call_sam3_api(
    image_b64: str,
    prompts: List[str],
    backend: str = SAM3_BACKEND,
    min_score: float = 0.5,
    max_masks: int = 32,
) -> List[Dict[str, Any]]:
    """
    调用 SAM3 API 进行图标分割
    
    返回: [{"bbox": [x1,y1,x2,y2], "area": float, "label": str}, ...]
    """
    if backend == "fal":
        return await _sam3_fal(image_b64, prompts, min_score, max_masks)
    elif backend == "roboflow":
        return await _sam3_roboflow(image_b64, prompts, min_score)
    elif backend == "api":
        return await _sam3_generic_api(image_b64, prompts, min_score)
    else:
        logger.warning("Unknown SAM3 backend", backend=backend)
        return []


async def _sam3_fal(
    image_b64: str, prompts: List[str], min_score: float, max_masks: int
) -> List[Dict[str, Any]]:
    """fal.ai SAM3 API"""
    if not SAM3_API_KEY:
        logger.warning("FAL_KEY not set, skipping SAM3")
        return []

    payload = {
        "image": f"data:image/png;base64,{image_b64}",
        "prompts": prompts,
        "min_score": min_score,
        "max_masks": max_masks,
    }

    try:
        client = await get_http_client()
        resp = await client.post(
            "https://fal.run/" + SAM3_FAL_MODEL,
            headers={
                "Authorization": f"Key {SAM3_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()

        detections = []
        for item in data.get("masks", []):
            bbox = item.get("bbox", [0, 0, 100, 100])
            detections.append({
                "bbox": bbox,
                "area": item.get("area", 0),
                "label": item.get("label", ""),
                "score": item.get("score", 0.0),
            })
        return detections

    except Exception as e:
        logger.error("SAM3 FAL failed", error=str(e))
        return []


async def _sam3_roboflow(
    image_b64: str, prompts: List[str], min_score: float
) -> List[Dict[str, Any]]:
    """Roboflow SAM3 API"""
    if not ROBOFLOW_API_KEY or not ROBOFLOW_ENDPOINT:
        return []

    payload = {
        "image": image_b64,
        "prompts": prompts,
        "confidence": min_score,
    }

    try:
        client = await get_http_client()
        resp = await client.post(
            ROBOFLOW_ENDPOINT,
            headers={
                "Authorization": ROBOFLOW_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("detections", [])

    except Exception as e:
        logger.error("SAM3 Roboflow failed", error=str(e))
        return []


async def _generate_figure_image(
    method_text: str,
    output_path: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """
    步骤一: 调用图像生成模型，根据 method_text 生成学术风格图片
    
    支持两种模式:
    1. OpenAI Images API (gpt-image-1, dall-e-3)
    2. 多模态 chat 降级 (让 LLM 描述图片 → 返回占位符)
    
    返回: 图片路径 (output_path)
    """
    logger.info("FigureEdit: generating figure image", model=model)

    # 尝试 OpenAI Images API
    image_api_key = os.getenv("OPENAI_IMAGE_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    image_base_url = os.getenv("OPENAI_IMAGE_BASE_URL", "https://api.openai.com/v1")
    image_model = model or os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

    if image_api_key:
        try:
            client = await get_http_client()
            payload = {
                "model": image_model,
                "prompt": (
                    f"Generate a high-quality academic figure for a scientific paper. "
                    f"Method: {method_text[:500]}\n\n"
                    "Style: clean, professional, white background, labeled components, "
                    "suitable for Nature/IEEE publication. "
                    "No text watermark. Vector-like quality."
                ),
                "n": 1,
                "size": "1024x1024",
            }

            resp = await client.post(
                f"{image_base_url}/images/generations",
                headers={
                    "Authorization": f"Bearer {image_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120.0,
            )
            resp.raise_for_status()
            data = resp.json()

            # 提取图片
            img_data_b64 = None
            img_url = None
            for item in data.get("data", []):
                if item.get("b64_json"):
                    img_data_b64 = item["b64_json"]
                    break
                if item.get("url"):
                    img_url = item["url"]
                    break

            if img_data_b64:
                img_bytes = base64.b64decode(img_data_b64)
                with open(output_path, "wb") as f:
                    f.write(img_bytes)
                logger.info("Figure image generated via Images API", path=output_path)
                return output_path

            elif img_url:
                resp2 = await client.get(img_url, timeout=60.0)
                with open(output_path, "wb") as f:
                    f.write(resp2.content)
                logger.info("Figure image downloaded from URL", path=output_path)
                return output_path

        except Exception as e:
            logger.warning("Images API failed, falling back", error=str(e))

    # 降级方案: 用用户上传的图片或创建占位符
    logger.info("FigureEdit: no image API available, creating placeholder")
    img = Image.new("RGB", (800, 600), color="white")
    # Draw placeholder text
    try:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.text((400, 300), "[Figure placeholder]\nUpload an image or configure OPENAI_IMAGE_API_KEY", fill="gray", anchor="mm")
    except Exception:
        pass
    img.save(output_path)
    return output_path


async def _segment_icons(
    image_path: str,
    output_dir: str,
    sam_prompts: str = "icon",
    min_score: float = 0.5,
    merge_threshold: float = 0.9,
) -> Tuple[str, str, List[Dict[str, Any]]]:
    """
    步骤二: SAM3 分割图标区域
    
    返回: (samed_path, boxlib_path, detections)
    """
    logger.info("FigureEdit: segmenting icons", prompts=sam_prompts)

    img = Image.open(image_path)
    img_b64 = _pil_to_base64(img)

    prompts_list = [p.strip() for p in sam_prompts.split(",")]

    detections = await _call_sam3_api(
        image_b64=img_b64,
        prompts=prompts_list,
        min_score=min_score,
    )

    # 保存 samed.png (带标记的图片)
    samed_path = os.path.join(output_dir, "samed.png")
    shutil.copyfile(image_path, samed_path)  # 简化版: 不画框

    # 保存 boxlib.json
    boxlib_path = os.path.join(output_dir, "boxlib.json")
    boxlib = {
        "image_size": list(img.size),
        "detections": detections,
    }
    with open(boxlib_path, "w", encoding="utf-8") as f:
        json.dump(boxlib, f, ensure_ascii=False, indent=2)

    logger.info("Icon segmentation done", count=len(detections))
    return samed_path, boxlib_path, detections


async def _crop_and_remove_bg(
    image_path: str,
    boxlib_path: str,
    output_dir: str,
) -> List[Dict[str, Any]]:
    """
    步骤三: 裁切图标区域 + RMBG2 去背景
    
    返回: [{"label": str, "nobg_path": str, "bbox": [...]}, ...]
    """
    logger.info("FigureEdit: cropping and removing background")

    with open(boxlib_path, "r", encoding="utf-8") as f:
        boxlib = json.load(f)

    img = Image.open(image_path)
    img_width, img_height = img.size

    icon_infos = []
    for i, det in enumerate(boxlib.get("detections", [])):
        bbox = det.get("bbox", [0, 0, 100, 100])
        label = det.get("label", f"<AF>{i+1:02d}")

        x1, y1, x2, y2 = bbox
        # 裁切
        icon_img = img.crop((int(x1), int(y1), int(x2), int(y2)))

        # 去背景 (可选, 需要 rembg)
        if RMBG_MODEL_PATH and os.path.exists(RMBG_MODEL_PATH):
            try:
                from rembg import remove
                icon_img = remove(icon_img)
            except Exception:
                pass

        # 保存
        nobg_path = os.path.join(output_dir, f"icon_{i:02d}_nobg.png")
        icon_img.save(nobg_path)

        icon_infos.append({
            "label": label,
            "label_clean": label.replace("<", "").replace(">", ""),
            "nobg_path": nobg_path,
            "bbox": bbox,
        })

    logger.info("Cropping and BG removal done", count=len(icon_infos))
    return icon_infos


async def _generate_svg_template(
    figure_path: str,
    samed_path: str,
    boxlib_path: str,
    output_path: str,
    placeholder_mode: str = "label",
) -> str:
    """
    步骤四: 多模态 LLM 生成 SVG 模板
    
    返回: SVG 代码字符串
    """
    logger.info("FigureEdit: generating SVG template", mode=placeholder_mode)

    figure_img = Image.open(figure_path)
    samed_img = Image.open(samed_path)
    fig_width, fig_height = figure_img.size

    # 构建 prompt
    if placeholder_mode == "none":
        prompt = f"""Generate SVG code to faithfully reproduce this academic figure.

CRITICAL DIMENSION REQUIREMENT:
- The original image has dimensions: {fig_width} x {fig_height} pixels
- Your SVG MUST use these EXACT dimensions:
  - Set viewBox="0 0 {fig_width} {fig_height}"
  - Set width="{fig_width}" height="{fig_height}"

Output ONLY the SVG code, starting with <svg and ending with </svg>."""

    elif placeholder_mode == "box":
        with open(boxlib_path, "r", encoding="utf-8") as f:
            boxlib_content = f.read()
        prompt = f"""Generate SVG code to reproduce this academic figure, using rectangle placeholders for icon areas.

ICON COORDINATES FROM BOXLIB:
{boxlib_content}

CRITICAL DIMENSION REQUIREMENT:
- Original image: {fig_width} x {fig_height} pixels
- SVG MUST use viewBox="0 0 {fig_width} {fig_height}"

Output ONLY the SVG code."""

    else:  # label mode (default)
        prompt = f"""Generate SVG code to reproduce this academic figure, using gray rectangle placeholders with black borders and centered labels like <AF>01, <AF>02, etc.

PLACEHOLDER STYLE REQUIREMENT:
- Rectangle with fill="#808080" stroke="black" stroke-width="2"
- Centered white text showing the label

CRITICAL DIMENSION REQUIREMENT:
- Original image: {fig_width} x {fig_height} pixels
- SVG MUST use viewBox="0 0 {fig_width} {fig_height}"

Output ONLY the SVG code."""

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": _pil_to_data_uri(figure_img)},
                },
                {
                    "type": "image_url",
                    "image_url": {"url": _pil_to_data_uri(samed_img)},
                },
            ],
        }
    ]

    svg_code = ""
    async for chunk in ai_service.chat(
        messages=messages,
        task_type="figure_edit",
        temperature=0.4,
        max_tokens=4096,
    ):
        svg_code += chunk

    # 提取 SVG 代码
    svg_match = re.search(r"(<svg[\s\S]*?</svg>)", svg_code, re.IGNORECASE)
    if svg_match:
        svg_code = svg_match.group(1)

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code)

    logger.info("SVG template generated", path=output_path, length=len(svg_code))
    return svg_code


def _validate_svg(svg_code: str) -> Tuple[bool, List[str]]:
    """SVG 语法验证 (简易版)"""
    errors = []
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(svg_code)
        return True, []
    except ET.ParseError as e:
        errors.append(str(e))
        return False, errors


async def _fix_svg_with_llm(svg_code: str) -> str:
    """用 LLM 修复 SVG 语法错误"""
    logger.info("FigureEdit: fixing SVG with LLM")

    messages = [
        {
            "role": "user",
            "content": (
                f"This SVG code has syntax errors. Please fix them and output ONLY the corrected SVG code.\n\n"
                f"```svg\n{svg_code[:3000]}\n```"
            ),
        }
    ]

    fixed = ""
    async for chunk in ai_service.chat(
        messages=messages,
        task_type="figure_edit",
        temperature=0.2,
    ):
        fixed += chunk

    svg_match = re.search(r"(<svg[\s\S]*?</svg>)", fixed, re.IGNORECASE)
    if svg_match:
        return svg_match.group(1)
    return svg_code


async def _optimize_svg(
    svg_path: str,
    figure_path: str,
    output_path: str,
    max_iterations: int = 2,
) -> str:
    """
    步骤四.六: LLM 优化 SVG 模板
    """
    logger.info("FigureEdit: optimizing SVG", iterations=max_iterations)

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_code = f.read()

    figure_img = Image.open(figure_path)

    for i in range(max_iterations):
        logger.info(f"Optimization iteration {i+1}/{max_iterations}")

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Compare this SVG with the original figure image. "
                            f"Optimize the SVG to better match the layout, text positions, arrows, and colors.\n"
                            f"Output ONLY the improved SVG code."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": _pil_to_data_uri(figure_img)}},
                ],
            }
        ]

        if i == 0:
            messages[0]["content"][0]["text"] += f"\n\nCurrent SVG:\n```svg\n{svg_code}\n```"

        new_svg = ""
        async for chunk in ai_service.chat(
            messages=messages,
            task_type="figure_edit",
            temperature=0.3,
            max_tokens=4096,
        ):
            new_svg += chunk

        svg_match = re.search(r"(<svg[\s\S]*?</svg>)", new_svg, re.IGNORECASE)
        if svg_match:
            svg_code = svg_match.group(1)

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_code)

    logger.info("SVG optimization done", path=output_path)
    return svg_code


def _replace_icons_in_svg(
    svg_path: str,
    icon_infos: List[Dict[str, Any]],
    output_path: str,
    scale_factors: Tuple[float, float] = (1.0, 1.0),
) -> str:
    """
    步骤五: 将透明图标替换到 SVG 占位符中
    
    匹配模式: label 模式 (推荐) — 按 <AF>01 标签匹配
    """
    logger.info("FigureEdit: replacing icons in SVG", icon_count=len(icon_infos))

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()

    scale_x, scale_y = scale_factors

    for icon_info in icon_infos:
        label = icon_info.get("label", "")
        label_clean = icon_info.get("label_clean", label.replace("<", "").replace(">", ""))
        nobg_path = icon_info.get("nobg_path", "")

        if not nobg_path or not os.path.exists(nobg_path):
            continue

        # 读取图标 → base64
        icon_img = Image.open(nobg_path)
        icon_b64 = _pil_to_base64(icon_img)
        data_uri = f"data:image/png;base64,{icon_b64}"

        # 查找 <g id="AF01"> 或 <rect ...> 标签
        g_pattern = rf'<g[^>]*\bid=["\']?{re.escape(label_clean)}["\']?[^>]*>[\s\S]*?</g>'
        g_match = re.search(g_pattern, svg_content, re.IGNORECASE)

        if g_match:
            # 替换整个 <g> 为 <image>
            old_g = g_match.group(0)
            new_image = (
                f'<g id="{label_clean}">\n'
                f'  <image x="{{x}}" y="{{y}}" width="{{w}}" height="{{h}}" '
                f'preserveAspectRatio="xMidYMid meet" href="{data_uri}" />\n'
                f'</g>'
            )
            # 从旧 <g> 中提取 x/y/width/height
            rect_match = re.search(r'(?:x|x1)=["\']?([\d.]+)["\']?', old_g)
            y_match = re.search(r'(?:y|y1)=["\']?([\d.]+)["\']?', old_g)
            w_match = re.search(r'width=["\']?([\d.]+)["\']?', old_g)
            h_match = re.search(r'height=["\']?([\d.]+)["\']?', old_g)

            if rect_match and y_match and w_match and h_match:
                x_val = float(rect_match.group(1))
                y_val = float(y_match.group(1))
                w_val = float(w_match.group(1))
                h_val = float(h_match.group(1))
                new_image = (
                    f'<g id="{label_clean}">\n'
                    f'  <image x="{x_val}" y="{y_val}" '
                    f'width="{w_val}" height="{h_val}" '
                    f'preserveAspectRatio="xMidYMid meet" href="{data_uri}" />\n'
                    f'</g>'
                )

            svg_content = svg_content.replace(old_g, new_image)
            logger.info(f"  Replaced {label} with icon image")

    # 保存
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    logger.info("Icon replacement done", path=output_path)
    return svg_content


async def method_to_svg(
    method_text: str,
    output_dir: str,
    sam_prompts: str = "icon",
    placeholder_mode: str = "label",
    min_score: float = 0.5,
    merge_threshold: float = 0.9,
    optimize_iterations: int = 2,
    image_model: Optional[str] = None,
    input_figure_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    完整流程: Method 文本 → SVG 图标替换
    
    流程:
    1. 生成图片 (method_text → image)
    2. SAM3 分割图标
    3. 裁切 + 去背景
    4. 生成 SVG 模板 (多模态 LLM)
    4.6 优化 SVG
    5. 图标替换
    
    返回: {"figure_path", "samed_path", "boxlib_path",
            "icon_infos", "template_svg", "final_svg"}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("FigureEdit: starting method_to_svg", mode=placeholder_mode)

    # 步骤一: 生成图片
    figure_path = str(output_dir / "figure.png")
    if input_figure_path and os.path.exists(input_figure_path):
        # 直接使用已有图片
        shutil.copyfile(input_figure_path, figure_path)
        logger.info("Using provided figure image", path=input_figure_path)
    else:
        await _generate_figure_image(method_text, figure_path, model=image_model)

    # 步骤二: SAM3 分割
    samed_path, boxlib_path, detections = await _segment_icons(
        image_path=figure_path,
        output_dir=str(output_dir),
        sam_prompts=sam_prompts,
        min_score=min_score,
        merge_threshold=merge_threshold,
    )

    no_icon_mode = len(detections) == 0
    if no_icon_mode:
        logger.info("No icons detected, using no-icon fallback mode")

    # 步骤三: 裁切 + 去背景
    icon_infos = []
    if not no_icon_mode:
        icon_infos = await _crop_and_remove_bg(
            image_path=figure_path,
            boxlib_path=boxlib_path,
            output_dir=str(output_dir),
        )

    # 步骤四: 生成 SVG 模板
    template_svg_path = output_dir / "template.svg"
    svg_code = await _generate_svg_template(
        figure_path=str(figure_path),
        samed_path=samed_path,
        boxlib_path=boxlib_path,
        output_path=str(template_svg_path),
        placeholder_mode=placeholder_mode,
    )

    # 验证 + 修复 SVG
    valid, errors = _validate_svg(svg_code)
    if not valid:
        logger.warning("SVG validation failed, attempting LLM fix", errors=errors)
        svg_code = await _fix_svg_with_llm(svg_code)
        with open(template_svg_path, "w", encoding="utf-8") as f:
            f.write(svg_code)

    # 步骤四.六: 优化 SVG
    optimized_path = output_dir / "optimized_template.svg"
    if optimize_iterations > 0:
        svg_code = await _optimize_svg(
            svg_path=str(template_svg_path),
            figure_path=str(figure_path),
            output_path=str(optimized_path),
            max_iterations=optimize_iterations,
        )
        template_to_use = str(optimized_path)
    else:
        template_to_use = str(template_svg_path)

    # 步骤五: 图标替换
    final_svg_path = output_dir / "final.svg"
    if no_icon_mode:
        # 无图标模式: 直接复制模板
        shutil.copyfile(template_to_use, final_svg_path)
    else:
        _replace_icons_in_svg(
            svg_path=template_to_use,
            icon_infos=icon_infos,
            output_path=str(final_svg_path),
            scale_factors=(1.0, 1.0),
        )

    logger.info("FigureEdit: method_to_svg completed", final_svg=str(final_svg_path))

    return {
        "figure_path": str(figure_path),
        "samed_path": samed_path,
        "boxlib_path": boxlib_path,
        "icon_infos": icon_infos,
        "template_svg": str(template_svg_path),
        "optimized_svg": str(optimized_path) if optimize_iterations > 0 else None,
        "final_svg": str(final_svg_path),
    }
