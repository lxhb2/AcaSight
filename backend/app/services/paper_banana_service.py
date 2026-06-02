"""
PaperBanana 技能包 — 论文插图自动生成 Pipeline

适配 AcaSight Agent 架构，将 PaperBanana 的 6-Agent Pipeline
转化为 AcaSight 的 skill + module agent 模式。

Pipeline: Retriever → Planner → Visualizer → Critic → Polish → Stylist
支持: plot（matplotlib代码生成）+ diagram（图像生成）

设计原则:
- 不依赖 Google Gemini API，使用 AcaSight 的 ai_service 多 provider 路由
- plot 生成使用 ProcessPoolExecutor 沙箱执行 matplotlib 代码
- critic 循环最多 3 轮，自动判断"No changes needed"时停止
- 输出 base64 JPEG + matplotlib 代码 + 评估报告
"""

import asyncio
import base64
import io
import json
import re
import traceback
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from app.services.ai_service import ai_service
import structlog

logger = structlog.get_logger()

# 全局代码执行池（沙箱隔离）
_executor: Optional[ProcessPoolExecutor] = None


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ProcessPoolExecutor(max_workers=4)
    return _executor


def _execute_plot_code(code_text: str) -> Optional[str]:
    """沙箱执行 matplotlib 代码 → 返回 base64 JPEG"""
    match = re.search(r"```python(.*?)```", code_text, re.DOTALL)
    code_clean = match.group(1).strip() if match else code_text.strip()

    plt.switch_backend("Agg")
    plt.close("all")
    plt.rcdefaults()

    try:
        exec_globals = {"plt": plt, "matplotlib": matplotlib}
        exec(code_clean, exec_globals)
        if plt.get_fignums():
            buf = io.BytesIO()
            plt.savefig(buf, format="jpeg", bbox_inches="tight", dpi=300)
            plt.close("all")
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("utf-8")
        return None
    except Exception as e:
        logger.warning(f"Plot code execution failed: {e}")
        return None


# ==================== SCI 期刊风格指南 ====================

STYLE_GUIDES = {
    "nature": {
        "name": "Nature",
        "plot": {
            "font_family": "Arial",
            "font_size": 7,
            "title_size": 9,
            "label_size": 7,
            "tick_size": 6,
            "legend_size": 6,
            "figure_width": 3.5,  # inches (single column)
            "figure_height": 2.5,
            "dpi": 300,
            "colors": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4", "#91D1C2", "#B09C85"],
            "grid": True,
            "grid_alpha": 0.3,
            "line_width": 1.0,
            "marker_size": 4,
        },
        "diagram": {
            "background": "pure white or very light pastel",
            "style": "clean, minimal, professional",
            "font": "Arial or Helvetica",
            "color_scheme": "muted, nature-palette",
        },
    },
    "ieee": {
        "name": "IEEE",
        "plot": {
            "font_family": "Times New Roman",
            "font_size": 8,
            "title_size": 9,
            "label_size": 8,
            "tick_size": 7,
            "legend_size": 7,
            "figure_width": 3.5,
            "figure_height": 2.5,
            "dpi": 300,
            "colors": ["#0072BD", "#D95319", "#EDB120", "#7E2F8E", "#77AC30", "#4DBEEE", "#A2142F", "#4170A4"],
            "grid": True,
            "grid_alpha": 0.2,
            "line_width": 1.0,
            "marker_size": 3,
        },
        "diagram": {
            "background": "white",
            "style": "technical, precise",
            "font": "Times New Roman",
            "color_scheme": "blue-primary",
        },
    },
    "elsevier": {
        "name": "Elsevier",
        "plot": {
            "font_family": "Arial",
            "font_size": 8,
            "title_size": 10,
            "label_size": 8,
            "tick_size": 7,
            "legend_size": 7,
            "figure_width": 4.0,
            "figure_height": 3.0,
            "dpi": 300,
            "colors": ["#0C5DA5", "#FF2C00", "#00B945", "#FF9500", "#845B97", "#474747", "#9E9E9E", "#00E5FF"],
            "grid": True,
            "grid_alpha": 0.25,
            "line_width": 1.2,
            "marker_size": 5,
        },
        "diagram": {
            "background": "white",
            "style": "clean, professional",
            "font": "Arial",
            "color_scheme": "diverse, balanced",
        },
    },
}


# ==================== Pipeline Agents ====================


async def _planner_figure(
    content: str,
    visual_intent: str,
    task_type: str = "plot",
    style_guide: str = "nature",
    references: Optional[List[Dict]] = None,
) -> str:
    """Planner Agent: 根据内容和意图生成详细图表描述"""
    style = STYLE_GUIDES.get(style_guide, STYLE_GUIDES["nature"])
    style_config = style.get("plot" if task_type == "plot" else "diagram", {})

    if task_type == "plot":
        system_prompt = f"""You are an expert statistical plot illustrator for {style['name']} journal publications.
Generate a detailed description for a statistical plot based on the provided raw data and visual intent.
The description will be used to generate matplotlib code.

Style Requirements ({style['name']}):
{json.dumps(style_config, indent=2)}

IMPORTANT:
- Specify exact aesthetic parameters: HEX color codes, font sizes, line widths, marker dimensions
- Explicitly enumerate every raw data point's coordinate
- Ensure all values are mathematically correct
- Do NOT include figure title/caption in the generated plot"""

        ref_section = ""
        if references:
            ref_section = "\n\nReference Examples:\n"
            for i, ref in enumerate(references[:3]):
                ref_section += f"Example {i+1}: {ref.get('description', '')[:200]}\n"

        prompt = f"""Raw Data: {content}
Visual Intent: {visual_intent}{ref_section}

Provide a detailed description for the target plot to be generated, including:
1. Plot type and layout
2. Exact data mapping (x, y, hue)
3. All data points with exact coordinates
4. Aesthetic parameters (colors, fonts, sizes)
5. Axis labels, legend placement, grid style"""
    else:
        system_prompt = f"""You are an expert scientific diagram illustrator for {style['name']} journal publications.
Generate a detailed description for a method diagram based on the provided methodology text and figure caption.

Style Requirements ({style['name']}):
{json.dumps(style_config, indent=2)}

IMPORTANT:
- Describe each element and their connections clearly
- Include background style, colors, line thickness, icon styles
- Do NOT include figure title/caption"""

        prompt = f"""Methodology Section: {content}
Figure Caption: {visual_intent}

Provide a detailed description for the target diagram to be generated."""

    result = ""
    async for chunk in ai_service.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        temperature=0.5,
        task_type="critic",
    ):
        result += chunk
    return result.strip()


async def _visualizer_plot(description: str, style_guide: str = "nature") -> Tuple[Optional[str], str]:
    """Visualizer Agent (plot): 生成 matplotlib 代码并执行"""
    style = STYLE_GUIDES.get(style_guide, STYLE_GUIDES["nature"])
    plot_style = style.get("plot", {})

    system_prompt = f"""You are an expert matplotlib programmer. Write Python code to generate a high-quality statistical plot.
Style: {style['name']} journal standard.
Requirements:
- Use matplotlib only (no seaborn)
- Font: {plot_style.get('font_family', 'Arial')}, size {plot_style.get('font_size', 7)}pt
- DPI: {plot_style.get('dpi', 300)}
- Colors from palette: {plot_style.get('colors', [])}
- Figure size: {plot_style.get('figure_width', 3.5)}x{plot_style.get('figure_height', 2.5)} inches
- Grid: {plot_style.get('grid', True)}, alpha={plot_style.get('grid_alpha', 0.3)}
- Line width: {plot_style.get('line_width', 1.0)}
- NO figure title (caption is separate)
- NO plt.show()
- Save ready (plt.savefig will be called externally)

Output ONLY the Python code, no explanations."""

    prompt = f"Write matplotlib code to generate a plot based on this description:\n\n{description}\n\nCode:"

    result = ""
    async for chunk in ai_service.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        temperature=0.3,
        task_type="agent_reasoning",
    ):
        result += chunk

    # 沙箱执行代码
    loop = asyncio.get_running_loop()
    base64_jpg = await loop.run_in_executor(_get_executor(), _execute_plot_code, result)

    return base64_jpg, result


async def _critic_figure(
    content: str,
    visual_intent: str,
    description: str,
    image_base64: Optional[str],
    task_type: str = "plot",
    style_guide: str = "nature",
) -> Dict[str, str]:
    """Critic Agent: 评估图表质量并返回改进建议"""
    style = STYLE_GUIDES.get(style_guide, STYLE_GUIDES["nature"])

    if task_type == "plot":
        system_prompt = f"""You are a Lead Visual Designer for {style['name']} journal.
Critique the generated plot and provide improvement suggestions.

Evaluate:
1. Data fidelity - are all data points accurately represented?
2. Visual clarity - is the plot easy to read?
3. Style compliance - does it follow {style['name']} standards?
4. Label accuracy - are axis labels, legend correct?

Output JSON:
{{"critic_suggestions": "detailed suggestions or 'No changes needed.'", "revised_description": "revised description or 'No changes needed.'"}}"""

        prompt = f"""Raw Data: {content}
Visual Intent: {visual_intent}
Current Description: {description}"""
    else:
        system_prompt = f"""You are a Lead Visual Designer for {style['name']} journal.
Critique the generated diagram and provide improvement suggestions.

Evaluate:
1. Fidelity - does the diagram accurately represent the methodology?
2. Visual clarity - is the layout clean and professional?
3. Style compliance - does it follow {style['name']} standards?
4. Text accuracy - are labels correct?

Output JSON:
{{"critic_suggestions": "detailed suggestions or 'No changes needed.'", "revised_description": "revised description or 'No changes needed.'"}}"""

        prompt = f"""Methodology Section: {content}
Figure Caption: {visual_intent}
Current Description: {description}"""

    result = ""
    async for chunk in ai_service.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        temperature=0.3,
        task_type="critic",
    ):
        result += chunk

    # 解析 JSON
    try:
        cleaned = result.replace("```json", "").replace("```", "").strip()
        eval_result = json.loads(cleaned)
    except:
        eval_result = {"critic_suggestions": result, "revised_description": "No changes needed."}

    return {
        "suggestions": eval_result.get("critic_suggestions", "No changes needed."),
        "revised_description": eval_result.get("revised_description", "No changes needed."),
    }


async def _polish_figure(description: str, suggestions: str, style_guide: str = "nature") -> str:
    """Polish Agent: 根据评估建议润色描述"""
    if suggestions.strip() == "No changes needed.":
        return description

    style = STYLE_GUIDES.get(style_guide, STYLE_GUIDES["nature"])
    system_prompt = f"You are a scientific figure polishing expert for {style['name']} journal. Apply the critic's suggestions to improve the figure description while maintaining accuracy."

    prompt = f"""Original Description: {description}

Critic Suggestions: {suggestions}

Provide the polished figure description incorporating all valid suggestions:"""

    result = ""
    async for chunk in ai_service.chat(
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        temperature=0.3,
        task_type="polish",
    ):
        result += chunk
    return result.strip()


# ==================== 主 Pipeline ====================


async def generate_figure_pipeline(
    content: str,
    visual_intent: str,
    task_type: str = "plot",  # plot | diagram
    style_guide: str = "nature",
    max_critic_rounds: int = 3,
    references: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """完整的 PaperBanana 图表生成 Pipeline

    Args:
        content: 原始数据(plot)或方法文本(diagram)
        visual_intent: 图表意图/标题
        task_type: plot(统计图) 或 diagram(方法图)
        style_guide: 风格指南 (nature/ieee/elsevier)
        max_critic_rounds: 最大评估轮数
        references: 参考图表列表(可选)

    Returns:
        {
            "image_base64": str,           # JPEG base64
            "code": str,                    # matplotlib 代码(plot only)
            "description": str,             # 最终描述
            "critic_reports": List[Dict],   # 评估报告
            "rounds_completed": int,        # 实际评估轮数
        }
    """
    logger.info(f"PaperBanana pipeline started", task_type=task_type, style=style_guide)

    # Step 1: Planner
    description = await _planner_figure(content, visual_intent, task_type, style_guide, references)

    # Step 2: Visualizer (plot only; diagram 需要图像生成API，暂返回描述)
    image_base64 = None
    code = ""
    if task_type == "plot":
        image_base64, code = await _visualizer_plot(description, style_guide)

    # Step 3-5: Critic → Polish → Re-visualize 循环
    critic_reports = []
    current_desc = description
    current_image = image_base64
    current_code = code

    for round_idx in range(max_critic_rounds):
        # Critic
        critic_result = await _critic_figure(
            content, visual_intent, current_desc, current_image, task_type, style_guide
        )
        critic_reports.append(critic_result)

        suggestions = critic_result["suggestions"]
        revised = critic_result["revised_description"]

        # 判断是否需要继续
        if suggestions.strip() == "No changes needed." and round_idx > 0:
            logger.info(f"Critic round {round_idx}: no changes needed, stopping")
            break

        # Polish
        polished = await _polish_figure(current_desc, suggestions, style_guide)
        if polished and polished.strip() != "No changes needed.":
            current_desc = polished
        elif revised and revised.strip() != "No changes needed.":
            current_desc = revised

        # Re-visualize (plot only)
        if task_type == "plot":
            new_image, new_code = await _visualizer_plot(current_desc, style_guide)
            if new_image:
                current_image = new_image
                current_code = new_code

    result = {
        "image_base64": current_image or "",
        "code": current_code,
        "description": current_desc,
        "critic_reports": critic_reports,
        "rounds_completed": len(critic_reports),
        "task_type": task_type,
        "style_guide": style_guide,
    }

    logger.info(f"PaperBanana pipeline completed", rounds=len(critic_reports), has_image=bool(current_image))
    return result


def get_available_styles() -> List[Dict]:
    """获取可用的风格指南列表"""
    return [
        {"id": k, "name": v["name"], "supports": ["plot", "diagram"]}
        for k, v in STYLE_GUIDES.items()
    ]
