"""
AI Response Formatter — 多 Provider 格式化增强 (方向P.4)

设计参考: agentscope Formatter 层
核心功能:
- 统一处理不同 AI Provider 的响应格式差异
- 自动修复常见格式问题 (JSON 提取、Markdown 代码块、BOM 等)
- 多种输出格式: text / json / markdown / svg / code
- 结构化提取 (从自由文本中提取 JSON/表格/列表)
- 响应后处理 pipeline (链式处理)

使用方式:
  formatter = AIResponseFormatter()
  result = formatter.format(raw_response, expected_format="json")
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()


# ── 数据模型 ──

class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    SVG = "svg"
    CODE = "code"
    LIST = "list"
    TABLE = "table"


@dataclass
class FormatResult:
    """格式化结果"""
    success: bool = True
    format: OutputFormat = OutputFormat.TEXT
    content: Any = None
    raw: str = ""
    warnings: List[str] = field(default_factory=list)
    extracted_from: str = ""  # 从哪种格式提取的


# ── 基础清理器 ──

def strip_bom(text: str) -> str:
    """去除 BOM"""
    if text.startswith('\ufeff'):
        return text[1:]
    return text


def strip_thinking_tags(text: str) -> str:
    """去除 <think/> 标签 (DeepSeek 等)"""
    return re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=re.IGNORECASE).strip()


def strip_code_fences(text: str) -> str:
    """去除 Markdown 代码围栏"""
    # 匹配 ```json ... ``` 或 ``` ... ```
    match = re.match(r'^```(?:\w+)?\s*\n([\s\S]*?)\n```\s*$', text.strip())
    if match:
        return match.group(1)
    return text


def normalize_whitespace(text: str) -> str:
    """规范化空白字符"""
    # 保留换行，合并连续空格
    return re.sub(r'[^\S\n]+', ' ', text).strip()


# ── JSON 提取器 ──

def extract_json(text: str) -> Optional[Any]:
    """
    从文本中提取 JSON (支持多种格式)
    
    1. 纯 JSON 字符串
    2. ```json ... ``` 代码块
    3. 嵌入在文本中的 {...} 或 [...]
    """
    # 尝试直接解析
    text = text.strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 去除代码围栏
    cleaned = strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # 提取 JSON 块
    # 1. ```json ... ```
    json_block = re.search(r'```json\s*\n([\s\S]*?)\n```', text, re.IGNORECASE)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. 第一个 { ... } 或 [ ... ]
    for pattern in [
        r'\{[\s\S]*\}',  # 对象
        r'\[[\s\S]*\]',  # 数组
    ]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                # 尝试修复常见的 JSON 问题
                fixed = _fix_common_json_errors(match.group(0))
                try:
                    return json.loads(fixed)
                except (json.JSONDecodeError, ValueError):
                    pass

    return None


def _fix_common_json_errors(json_str: str) -> str:
    """修复常见的 JSON 格式错误"""
    # 1. 尾随逗号
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    # 2. 单引号 → 双引号
    json_str = json_str.replace("'", '"')
    # 3. 未引用的键
    json_str = re.sub(r'(\w+)\s*:', r'"\1":', json_str)
    # 4. 布尔值
    json_str = json_str.replace('True', 'true').replace('False', 'false').replace('None', 'null')
    return json_str


# ── SVG 提取器 ──

def extract_svg(text: str) -> Optional[str]:
    """从文本中提取 SVG 代码"""
    match = re.search(r'(<svg[\s\S]*?</svg>)', text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


# ── 列表提取器 ──

def extract_list(text: str) -> List[str]:
    """从文本中提取列表项"""
    items = []
    
    # Markdown 列表: - item 或 * item 或 1. item
    for match in re.finditer(r'(?:^|\n)\s*(?:[-*]|\d+\.)\s+(.+)', text):
        items.append(match.group(1).strip())
    
    if items:
        return items
    
    # 换行分隔
    for line in text.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            items.append(line)
    
    return items


# ── AI Response Formatter ──

class AIResponseFormatter:
    """
    AI 响应格式化器
    
    Pipeline:
    1. 预处理 (BOM、thinking tags)
    2. 格式检测 (自动判断 JSON/SVG/Markdown/Code)
    3. 格式提取 (提取目标格式)
    4. 后处理 (验证、修复)
    """

    def __init__(self):
        self._preprocessors: List[Callable[[str], str]] = [
            strip_bom,
            strip_thinking_tags,
        ]

    def format(
        self,
        raw_response: str,
        expected_format: OutputFormat = OutputFormat.TEXT,
        strict: bool = False,
    ) -> FormatResult:
        """
        格式化 AI 响应
        
        Args:
            raw_response: AI 原始响应
            expected_format: 期望输出格式
            strict: 严格模式 (格式不匹配则报错)
        
        Returns:
            FormatResult
        """
        warnings = []

        # 1. 预处理
        text = raw_response
        for preprocessor in self._preprocessors:
            text = preprocessor(text)

        # 2. 自动检测格式 (如果未指定)
        detected_format = self._detect_format(text)

        # 3. 格式提取
        if expected_format == OutputFormat.JSON:
            result = extract_json(text)
            if result is not None:
                return FormatResult(
                    success=True,
                    format=OutputFormat.JSON,
                    content=result,
                    raw=text,
                    extracted_from=detected_format.value,
                )
            elif strict:
                return FormatResult(
                    success=False,
                    format=OutputFormat.JSON,
                    content=None,
                    raw=text,
                    warnings=["Failed to extract JSON from response"],
                )
            else:
                warnings.append("Could not extract JSON, returning as text")
                return FormatResult(
                    success=True,
                    format=OutputFormat.TEXT,
                    content=text,
                    raw=text,
                    warnings=warnings,
                    extracted_from=detected_format.value,
                )

        elif expected_format == OutputFormat.SVG:
            result = extract_svg(text)
            if result is not None:
                return FormatResult(
                    success=True,
                    format=OutputFormat.SVG,
                    content=result,
                    raw=text,
                    extracted_from=detected_format.value,
                )
            elif strict:
                return FormatResult(
                    success=False,
                    format=OutputFormat.SVG,
                    content=None,
                    raw=text,
                    warnings=["Failed to extract SVG from response"],
                )
            else:
                warnings.append("Could not extract SVG, returning as text")
                return FormatResult(
                    success=True,
                    format=OutputFormat.TEXT,
                    content=text,
                    raw=text,
                    warnings=warnings,
                    extracted_from=detected_format.value,
                )

        elif expected_format == OutputFormat.LIST:
            items = extract_list(text)
            return FormatResult(
                success=True,
                format=OutputFormat.LIST,
                content=items,
                raw=text,
                extracted_from=detected_format.value,
            )

        elif expected_format == OutputFormat.CODE:
            # 去除代码围栏
            cleaned = strip_code_fences(text)
            return FormatResult(
                success=True,
                format=OutputFormat.CODE,
                content=cleaned,
                raw=text,
                extracted_from=detected_format.value,
            )

        elif expected_format == OutputFormat.MARKDOWN:
            return FormatResult(
                success=True,
                format=OutputFormat.MARKDOWN,
                content=text,
                raw=text,
                extracted_from=detected_format.value,
            )

        else:  # TEXT
            return FormatResult(
                success=True,
                format=OutputFormat.TEXT,
                content=normalize_whitespace(text),
                raw=text,
            )

    @staticmethod
    def _detect_format(text: str) -> OutputFormat:
        """自动检测响应格式"""
        text = text.strip()

        # JSON
        if text.startswith('{') or text.startswith('['):
            try:
                json.loads(text)
                return OutputFormat.JSON
            except (json.JSONDecodeError, ValueError):
                pass

        # JSON in code fence
        if re.match(r'^```json\s*\n', text, re.IGNORECASE):
            return OutputFormat.JSON

        # SVG
        if text.startswith('<svg') or '<svg' in text[:200]:
            return OutputFormat.SVG

        # Code
        if text.startswith('```'):
            return OutputFormat.CODE

        # Markdown (有标题)
        if re.match(r'^#{1,6}\s', text, re.MULTILINE):
            return OutputFormat.MARKDOWN

        return OutputFormat.TEXT

    def format_json(self, raw_response: str, strict: bool = False) -> FormatResult:
        """快捷方法: 格式化为 JSON"""
        return self.format(raw_response, OutputFormat.JSON, strict)

    def format_svg(self, raw_response: str, strict: bool = False) -> FormatResult:
        """快捷方法: 格式化为 SVG"""
        return self.format(raw_response, OutputFormat.SVG, strict)

    def format_list(self, raw_response: str) -> FormatResult:
        """快捷方法: 格式化为列表"""
        return self.format(raw_response, OutputFormat.LIST)


# Singleton
ai_formatter = AIResponseFormatter()
