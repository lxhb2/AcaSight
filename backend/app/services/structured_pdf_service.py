"""
PDF 结构化解析服务 — 基于 OpenDataLoader PDF

将 PDF 解析为结构化 JSON，用于：
1. 11维度论文拆分：从结构化元素中按标题层级自动匹配维度
2. RAG 语义分块：按元素/章节/尺寸分块，每个 chunk 带 bounding box 和页码
3. 全文 Markdown 输出：保留标题层级、表格、图片引用
"""

import os
import json
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog

logger = structlog.get_logger()

# 延迟导入 opendataloader_pdf，避免未安装时影响启动
_odl = None


def _get_odl():
    global _odl
    if _odl is None:
        try:
            import opendataloader_pdf
            _odl = opendataloader_pdf
        except ImportError:
            logger.warning("opendataloader-pdf not installed — structured parsing disabled")
    return _odl


def is_available() -> bool:
    """检查 opendataloader-pdf 是否可用"""
    return _get_odl() is not None


def convert_pdf_to_structured(
    pdf_path: str,
    output_dir: Optional[str] = None,
    formats: str = "json,markdown",
    reading_order: str = "xycut",
) -> Dict[str, Any]:
    """
    将 PDF 转换为结构化 JSON + Markdown

    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录（默认临时目录）
        formats: 输出格式，逗号分隔（json, markdown, html）
        reading_order: 阅读顺序算法（xycut | off）

    Returns:
        dict: {
            "json_path": str,       # JSON 输出路径
            "markdown_path": str,   # Markdown 输出路径（可选）
            "document": dict,       # 解析后的结构化文档
            "markdown": str,        # Markdown 文本内容
        }
    """
    odl = _get_odl()
    if odl is None:
        raise RuntimeError("opendataloader-pdf not installed")

    use_temp = output_dir is None
    if use_temp:
        output_dir = tempfile.mkdtemp(prefix="odl_")

    try:
        odl.convert(
            input_path=pdf_path,
            output_dir=output_dir,
            format=formats,
            reading_order=reading_order,
            quiet=True,
        )
    except Exception as e:
        logger.error("OpenDataLoader convert failed", pdf_path=pdf_path, error=str(e))
        raise

    pdf_name = Path(pdf_path).stem
    result: Dict[str, Any] = {}

    # 读取 JSON 输出
    json_path = Path(output_dir) / f"{pdf_name}.json"
    if json_path.exists():
        result["json_path"] = str(json_path)
        with open(json_path, encoding="utf-8") as f:
            result["document"] = json.load(f)
    else:
        logger.warning("JSON output not found", path=str(json_path))
        result["document"] = {}

    # 读取 Markdown 输出
    md_path = Path(output_dir) / f"{pdf_name}.md"
    if md_path.exists():
        result["markdown_path"] = str(md_path)
        with open(md_path, encoding="utf-8") as f:
            result["markdown"] = f.read()
    else:
        result["markdown"] = ""

    return result


# ──────────────────────────────────────────────
# 11 维度映射：从结构化文档中按标题层级提取
# ──────────────────────────────────────────────

# 论文常见标题 → 11维度映射表
HEADING_DIMENSION_MAP = {
    "abstract": "abstract",
    "摘要": "abstract",
    "introduction": "research_background",
    "背景": "research_background",
    "研究背景": "research_background",
    "purpose": "research_purpose",
    "研究目的": "research_purpose",
    "研究意义": "research_purpose",
    "related work": "research_status",
    "literature review": "research_status",
    "研究现状": "research_status",
    "文献综述": "research_status",
    "research questions": "research_questions",
    "研究问题": "research_questions",
    "theory": "basic_theory",
    "theoretical framework": "basic_theory",
    "基本理论": "basic_theory",
    "理论基础": "basic_theory",
    "method": "research_methods",
    "methodology": "research_methods",
    "研究方法": "research_methods",
    "实验设计": "research_methods",
    "实验方法": "research_methods",
    "results": "results_and_evaluation",
    "evaluation": "results_and_evaluation",
    "结果": "results_and_evaluation",
    "实验结果": "results_and_evaluation",
    "结果与评价": "results_and_evaluation",
    "innovation": "innovation_points",
    "contribution": "innovation_points",
    "创新点": "innovation_points",
    "创新": "innovation_points",
    "limitations": "limitations_and_suggestions",
    "future work": "limitations_and_suggestions",
    "局限": "limitations_and_suggestions",
    "局限与建议": "limitations_and_suggestions",
    "conclusion": "conclusions",
    "结论": "conclusions",
    "总结": "conclusions",
}


def _match_dimension(heading_text: str) -> Optional[str]:
    """将标题文本匹配到11维度之一"""
    heading_lower = heading_text.lower().strip()
    for pattern, dimension in HEADING_DIMENSION_MAP.items():
        if pattern in heading_lower:
            return dimension
    return None


def extract_dimensions_from_structured(document: dict) -> Dict[str, str]:
    """
    从 OpenDataLoader 结构化 JSON 中提取 11 维度

    策略：
    1. 遍历所有 heading 元素，匹配到维度映射
    2. 收集该 heading 下的所有 paragraph/list 内容
    3. 未匹配到的维度留空

    Returns:
        dict: 11 维度字典，未匹配的维度为空字符串
    """
    from app.models.paper_dimensions import PaperDimensions

    dimensions = {k: "" for k in PaperDimensions.DIMENSION_KEYS}
    kids = document.get("kids", [])

    current_dimension = None
    current_content: List[str] = []

    for element in kids:
        elem_type = element.get("type", "")
        content = element.get("content", "").strip()

        if elem_type == "heading":
            # 保存上一个维度的内容
            if current_dimension and current_content:
                dimensions[current_dimension] = "\n".join(current_content).strip()

            # 尝试匹配新维度
            matched = _match_dimension(content)
            current_dimension = matched
            current_content = [content] if matched else []

        elif elem_type in ("paragraph", "list") and current_dimension and content:
            current_content.append(content)

    # 保存最后一个维度
    if current_dimension and current_content:
        dimensions[current_dimension] = "\n".join(current_content).strip()

    # 如果结构化提取结果太少（<3个维度有值），返回空结果让 AI 兜底
    filled = sum(1 for v in dimensions.values() if v)
    if filled < 3:
        logger.info("Structured extraction too sparse, will fallback to AI", filled=filled)
        return {k: "" for k in PaperDimensions.DIMENSION_KEYS}

    logger.info("Structured dimension extraction done", filled=filled, total=11)
    return dimensions


# ──────────────────────────────────────────────
# RAG 语义分块
# ──────────────────────────────────────────────

def chunk_by_element(document: dict) -> List[Dict[str, Any]]:
    """
    策略1：按语义元素分块

    每个 paragraph/heading/list 元素为一个 chunk，
    带 bounding box 和页码元数据，适合精确引用。
    """
    chunks = []
    for element in document.get("kids", []):
        if element.get("type") in ("paragraph", "heading", "list"):
            content = element.get("content", "").strip()
            if content:
                chunks.append({
                    "text": content,
                    "metadata": {
                        "type": element["type"],
                        "page": element.get("page number"),
                        "bbox": element.get("bounding box"),
                    }
                })
    return chunks


def chunk_by_section(document: dict) -> List[Dict[str, Any]]:
    """
    策略2：按章节分块

    将同一标题下的内容合并为一个 chunk，
    适合上下文丰富的检索。
    """
    chunks = []
    current_heading = None
    current_content: List[str] = []
    current_page = None

    for element in document.get("kids", []):
        elem_type = element.get("type")

        if elem_type == "heading":
            if current_content:
                chunks.append({
                    "text": "\n".join(current_content),
                    "metadata": {
                        "heading": current_heading,
                        "page": current_page,
                    }
                })
            current_heading = element.get("content", "")
            current_content = [current_heading]
            current_page = element.get("page number")
        elif elem_type in ("paragraph", "list"):
            content = element.get("content", "").strip()
            if content:
                current_content.append(content)

    if current_content:
        chunks.append({
            "text": "\n".join(current_content),
            "metadata": {
                "heading": current_heading,
                "page": current_page,
            }
        })

    return chunks


def chunk_with_min_size(document: dict, min_chars: int = 500) -> List[Dict[str, Any]]:
    """
    策略3：按最小尺寸合并分块

    合并相邻小元素直到达到最小字符数，
    适合平衡 chunk 大小、减少噪声。
    """
    chunks = []
    buffer_text = ""
    buffer_pages: List[int] = []

    for element in document.get("kids", []):
        if element.get("type") in ("paragraph", "heading", "list"):
            content = element.get("content", "").strip()
            page = element.get("page number")

            if content:
                buffer_text += content + "\n"
                if page and page not in buffer_pages:
                    buffer_pages.append(page)

                if len(buffer_text) >= min_chars:
                    chunks.append({
                        "text": buffer_text.strip(),
                        "metadata": {
                            "pages": buffer_pages.copy(),
                        }
                    })
                    buffer_text = ""
                    buffer_pages = []

    if buffer_text.strip():
        chunks.append({
            "text": buffer_text.strip(),
            "metadata": {
                "pages": buffer_pages,
            }
        })

    return chunks


def chunk_for_rag(document: dict, strategy: str = "section") -> List[Dict[str, Any]]:
    """
    为 RAG 生成语义分块

    Args:
        document: OpenDataLoader 结构化文档
        strategy: 分块策略（element | section | merged）

    Returns:
        List[dict]: 每个 chunk 包含 text 和 metadata
    """
    if strategy == "element":
        return chunk_by_element(document)
    elif strategy == "merged":
        return chunk_with_min_size(document)
    else:  # default: section
        return chunk_by_section(document)
