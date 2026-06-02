"""
Visual Evaluator — 图表视觉评估循环 (方向P.1)

设计参考: ggplotAgent qa_image_checker_node
核心功能:
- VL (Vision-Language) 模型评估图表质量
- MATCH/MISMATCH 二元判定
- 反馈提取 → 传回生成器进行修复
- 支持自定义评估标准 (SCI风格指南)
- 最大重试循环 (默认3轮)

使用方式:
  evaluator = VisualEvaluator()
  result = await evaluator.evaluate(
      image_path="chart.png",
      criteria="Nature style bar chart with labeled axes",
      max_retries=3,
  )
"""

import base64
import io
import os
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
import structlog

from app.services.ai_service import ai_service

logger = structlog.get_logger()

# ── 评估 Prompt 模板 ──

QA_PROMPT_TEMPLATE = """## YOUR ROLE
You are a scientific figure quality assurance expert with expertise in academic publishing standards.

## YOUR TASK
Compare the "Evaluation Criteria" to the "Image" and evaluate if the image is **perfect**. A perfect figure meets these conditions:

1. **Full Compliance with the Criteria:** All elements in the figure (type, data, text) closely match the evaluation criteria.
2. **High Visual Quality:** All text elements (labels, annotations, legends, axis titles, tick labels) are clear, fully visible, and not obscured by other graphical components. Text readability and proper spatial separation are maintained across all regions.
3. **Academic Standards:** The figure follows academic publishing conventions (Nature/IEEE/Elsevier style) — clean layout, appropriate font sizes, no clipping, proper aspect ratio.

## OUTPUT FORMAT
Your response MUST start with `MATCH` or `MISMATCH:`. In brief:

- If the image is flawless, the first line must be only the word: `MATCH`
- If there is **any** issue, the first line must be `MISMATCH:` followed by a brief explanation of all inconsistencies and visual quality issues.

---
**EVALUATION CRITERIA:**
{criteria}

Now, analyze the attached image and generate your response in the specified format."""

SCI_STYLE_CRITERIA = {
    "nature": (
        "Nature-style figure: clean layout, sans-serif font (Helvetica/Arial), "
        "no box around plot area, thin axis lines, minimal gridlines, "
        "high DPI quality, clear and readable labels at 5-7pt equivalent."
    ),
    "ieee": (
        "IEEE-style figure: professional engineering plot, clear axis labels with units, "
        "gridlines where appropriate, distinct line styles/markers for multiple series, "
        "proper legend placement, Times New Roman or similar serif font."
    ),
    "elsevier": (
        "Elsevier-style figure: compact and efficient layout, clear figure caption, "
        "consistent color scheme, proper axis labeling, suitable for single/double column."
    ),
    "default": (
        "Professional academic figure: clear labels, proper axis titles with units, "
        "readable text, clean layout, no overlapping elements, suitable for publication."
    ),
}


class VisualEvaluationResult:
    """视觉评估结果"""
    def __init__(
        self,
        passed: bool,
        feedback: Optional[str] = None,
        retry_count: int = 0,
        history: Optional[List[Dict[str, Any]]] = None,
    ):
        self.passed = passed
        self.feedback = feedback
        self.retry_count = retry_count
        self.history = history or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "feedback": self.feedback,
            "retry_count": self.retry_count,
            "history": self.history,
        }


class VisualEvaluator:
    """图表视觉评估器 — VL模型评估图表质量"""

    def __init__(self, style: str = "default"):
        self.style = style

    async def evaluate(
        self,
        image: Optional[Image.Image] = None,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
        criteria: Optional[str] = None,
        max_retries: int = 3,
        style: Optional[str] = None,
    ) -> VisualEvaluationResult:
        """
        评估图表视觉质量 (支持多轮修复循环)

        Args:
            image: PIL Image 对象
            image_path: 图片文件路径
            image_base64: Base64 图片
            criteria: 评估标准描述
            max_retries: 最大评估重试次数
            style: SCI 风格 (nature/ieee/elsevier/default)

        Returns:
            VisualEvaluationResult
        """
        effective_style = style or self.style
        effective_criteria = criteria or SCI_STYLE_CRITERIA.get(
            effective_style, SCI_STYLE_CRITERIA["default"]
        )

        # 加载图片
        img = self._load_image(image, image_path, image_base64)
        if img is None:
            return VisualEvaluationResult(
                passed=False,
                feedback="No image provided for evaluation",
                retry_count=0,
            )

        history = []

        for attempt in range(max_retries + 1):
            logger.info(
                "Visual evaluation attempt",
                attempt=attempt + 1,
                max_retries=max_retries + 1,
            )

            passed, feedback = await self._single_evaluate(img, effective_criteria)

            history.append({
                "attempt": attempt + 1,
                "passed": passed,
                "feedback": feedback,
            })

            if passed:
                logger.info("Visual evaluation passed", attempt=attempt + 1)
                return VisualEvaluationResult(
                    passed=True,
                    feedback=None,
                    retry_count=attempt,
                    history=history,
                )

            logger.info("Visual evaluation mismatch", attempt=attempt + 1, feedback=feedback[:100])

        # 所有轮次都未通过
        logger.warning("Visual evaluation failed after all retries", retries=max_retries)
        return VisualEvaluationResult(
            passed=False,
            feedback=feedback,
            retry_count=max_retries,
            history=history,
        )

    async def _single_evaluate(
        self, image: Image.Image, criteria: str
    ) -> Tuple[bool, Optional[str]]:
        """单次视觉评估"""
        prompt = QA_PROMPT_TEMPLATE.format(criteria=criteria)

        # 构建多模态消息
        img_data_uri = self._pil_to_data_uri(image)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": img_data_uri},
                    },
                ],
            }
        ]

        response = ""
        async for chunk in ai_service.chat(
            messages=messages,
            task_type="visual_evaluation",
            temperature=0.2,
            max_tokens=512,
        ):
            response += chunk

        response = response.strip()

        # 解析 MATCH/MISMATCH
        if response.upper().startswith("MATCH"):
            return True, None
        elif response.upper().startswith("MISMATCH:"):
            feedback = response[len("MISMATCH:"):].strip()
            return False, feedback
        elif "MISMATCH" in response.upper():
            # 尝试从响应中提取反馈
            idx = response.upper().index("MISMATCH")
            feedback = response[idx + len("MISMATCH"):].strip().lstrip(":").strip()
            return False, feedback
        else:
            # 模糊响应 — 假定为不匹配
            return False, f"Ambiguous evaluation: {response[:200]}"

    async def evaluate_with_regeneration(
        self,
        generate_fn,
        criteria: Optional[str] = None,
        max_retries: int = 3,
        style: Optional[str] = None,
    ) -> Tuple[Any, VisualEvaluationResult]:
        """
        评估+生成循环: 评估图表 → 如果不通过 → 调用生成函数修复 → 重新评估

        Args:
            generate_fn: 异步函数，接受 feedback 参数，返回新的 Image
            criteria: 评估标准
            max_retries: 最大重试次数
            style: SCI 风格

        Returns:
            (final_image, evaluation_result)
        """
        effective_style = style or self.style
        effective_criteria = criteria or SCI_STYLE_CRITERIA.get(
            effective_style, SCI_STYLE_CRITERIA["default"]
        )

        # 初始生成
        current_image = await generate_fn(feedback=None)
        history = []

        for attempt in range(max_retries + 1):
            passed, feedback = await self._single_evaluate(current_image, effective_criteria)
            history.append({
                "attempt": attempt + 1,
                "passed": passed,
                "feedback": feedback,
            })

            if passed:
                return current_image, VisualEvaluationResult(
                    passed=True, feedback=None, retry_count=attempt, history=history
                )

            # 生成修复版本
            if attempt < max_retries:
                logger.info("Regenerating with feedback", feedback=feedback[:100])
                current_image = await generate_fn(feedback=feedback)

        return current_image, VisualEvaluationResult(
            passed=False, feedback=feedback, retry_count=max_retries, history=history
        )

    @staticmethod
    def _load_image(
        image: Optional[Image.Image] = None,
        image_path: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> Optional[Image.Image]:
        """从各种输入加载 PIL Image"""
        if image is not None:
            return image
        if image_path and os.path.exists(image_path):
            return Image.open(image_path)
        if image_base64:
            img_data = base64.b64decode(image_base64)
            return Image.open(io.BytesIO(img_data))
        return None

    @staticmethod
    def _pil_to_data_uri(img: Image.Image) -> str:
        """PIL Image → data URI"""
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"


# Singleton
visual_evaluator = VisualEvaluator()
