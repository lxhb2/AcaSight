"""
意图解析器 (IntentParser)
基于规则 + LLM 双层解析

用法:
    parser = IntentParser()
    intent = parser.parse("帮我搜索催化剂相关的论文")
    → {task_type: "search_literature", module: "literature", operation: "search", params: {...}, confidence: 0.85}
"""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import re


class TaskType(str, Enum):
    SEARCH_LITERATURE = "search_literature"
    READ_PAPER = "read_paper"
    WRITE_PAPER = "write_paper"
    GENERATE_OUTLINE = "generate_outline"
    POLISH_TEXT = "polish_text"
    DRAW_CHART = "draw_chart"
    EXPORT_WORD = "export_word"
    ANALYZE_PAPER = "analyze_paper"
    GENERATE_CITATION = "generate_citation"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"
    GENERAL_QA = "general_qa"
    WORKFLOW = "workflow"  # 需要执行完整工作流


@dataclass
class Intent:
    task_type: TaskType
    module: str
    operation: str
    params: Dict[str, Any]
    confidence: float          # 0.0 ~ 1.0
    raw_input: str
    workflow_id: str = ""      # 如果需要工作流
    requires_confirmation: bool = True
    suggested_mode: str = "assist"


# ─── 规则映射表 ───

TASK_PATTERNS = {
    TaskType.SEARCH_LITERATURE: {
        "patterns": [
            r"(搜|找|查|检索)\S*(论文|文献|文章|资料)",
            r"(search|find|query)\s+(paper|literature|article)",
            r"有.*(论文|文献).*(吗|推荐|介绍)",
        ],
        "module": "literature",
        "operation": "search",
        "param_keys": ["query", "limit"],
    },
    TaskType.WRITE_PAPER: {
        "patterns": [
            r"(写|生成|撰写|创作)\S*(论文|文章|综述|报告|提纲|大纲)",
            r"(帮我|请|来)\S*(写|生成|创作)",
            r"(开始|启动).*(写作|撰写)",
        ],
        "module": "writing",
        "operation": "generate_section",
        "param_keys": ["topic", "section_title"],
    },
    TaskType.GENERATE_OUTLINE: {
        "patterns": [
            r"(提纲|大纲|目录|框架|结构)",
            r"(generate|create)\s+(outline|structure)",
        ],
        "module": "writing",
        "operation": "generate_outline",
        "param_keys": ["topic"],
    },
    TaskType.POLISH_TEXT: {
        "patterns": [
            r"(润色|优化|修改|改进|降重|精简|扩写).*(文本|文字|段落|章节)",
            r"(polish|revise|improve|paraphrase|shorten|expand)",
        ],
        "module": "writing",
        "operation": "polish",
        "param_keys": ["text", "mode"],
    },
    TaskType.DRAW_CHART: {
        "patterns": [
            r"(画|生成|创建|做|制作)\S*(图|图表|图线|曲线|XRD|TG|FTIR|SEM)",
            r"(绘图|画图|作图|draw|chart|plot|graph)",
        ],
        "module": "charts",
        "operation": "auto_generate",
        "param_keys": ["description", "chart_type"],
    },
    TaskType.EXPORT_WORD: {
        "patterns": [
            r"(导出|保存|下载|生成)\S*(word|doc|文档|文件)",
            r"(export|save|download).*(word|doc)",
        ],
        "module": "writing",
        "operation": "export_word",
        "param_keys": ["markdown_content", "template"],
    },
    TaskType.ANALYZE_PAPER: {
        "patterns": [
            r"(分析|解读|解释|理解)\S*(论文|文献|文章|PDF)",
            r"(这篇|这篇论文|这个文献)",
            r"(analyze|review|understand).*(paper|article)",
        ],
        "module": "literature",
        "operation": "decompose",
        "param_keys": ["paper_id", "title", "full_text"],
    },
    TaskType.GENERATE_CITATION: {
        "patterns": [
            r"(引用|参考文献|引用格式|citation|reference).*(生成|导出)",
            r"(cite|reference).*(format|export)",
        ],
        "module": "literature",
        "operation": "export_citation",
        "param_keys": ["paper_id", "style"],
    },
    TaskType.TRANSLATE: {
        "patterns": [
            r"(翻译|translate|译)\S*(成|为|到)\S*",
            r"英文|中文|日文|翻译",
        ],
        "module": "agent",
        "operation": "summarize",
        "param_keys": ["text"],
    },
    TaskType.SUMMARIZE: {
        "patterns": [
            r"(总结|摘要|概括|归纳|summarize)",
        ],
        "module": "agent",
        "operation": "summarize",
        "param_keys": ["text"],
    },
}

# 工作流触发词
WORKFLOW_PATTERNS = {
    "paper_writing": [
        r"(全流程|完整|从开始到结束).*(写|撰写|创作).*(论文|文章)",
        r"(自动|帮我|AI).*(写|撰写).*(论文|综述)",
    ],
    "literature_review": [
        r"(文献综述|文献回顾|literature review)",
    ],
    "experiment_plan": [
        r"(试验方案|研究方向|创新点|研究计划|实验方案)",
    ],
    "quick_polish": [
        r"(快速润色|润色导出|polish.*export)",
    ],
    "paper_qa_chart": [
        r"(论文问答|论文.+图表|analyse.*chart)",
    ],
}


class IntentParser:
    """
    意图解析器
    
    优先规则匹配（快速，0ms），规则miss时降级到 LLM 解析
    """
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    def parse(self, user_input: str) -> Intent:
        """解析用户输入为结构化意图"""
        
        # 1. 检查工作流触发
        wf_result = self._detect_workflow(user_input)
        if wf_result:
            return wf_result
        
        # 2. 规则匹配
        for task_type, config in TASK_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, user_input, re.IGNORECASE):
                    params = self._extract_params(user_input, config.get("param_keys", []))
                    return Intent(
                        task_type=task_type,
                        module=config["module"],
                        operation=config["operation"],
                        params=params,
                        confidence=0.8,
                        raw_input=user_input,
                    )
        
        # 3. 降级到通用问答
        return Intent(
            task_type=TaskType.GENERAL_QA,
            module="agent",
            operation="summarize",
            params={"text": user_input},
            confidence=0.4,
            raw_input=user_input,
        )
    
    def parse_with_llm(self, user_input: str) -> Intent:
        """使用 LLM 解析（精度更高但依赖API）"""
        if not self.llm:
            return self.parse(user_input)  # 降级到规则
        
        # TODO: 接入 LLM 解析
        return self.parse(user_input)
    
    # ─── 内部方法 ───
    
    def _detect_workflow(self, user_input: str) -> Optional[Intent]:
        for wf_id, patterns in WORKFLOW_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, user_input, re.IGNORECASE):
                    return Intent(
                        task_type=TaskType.WORKFLOW,
                        module="workflow",
                        operation="execute",
                        params={"query": user_input},
                        workflow_id=wf_id,
                        confidence=0.9,
                        raw_input=user_input,
                        requires_confirmation=True,
                        suggested_mode="assist",
                    )
        return None
    
    def _extract_params(self, text: str, keys: List[str]) -> Dict[str, Any]:
        params = {}
        
        # 尝试提取引号内容作为 query
        quoted = re.findall(r'["""]([^"""]+)["""]', text)
        if quoted and "query" in keys:
            params["query"] = quoted[0]
        elif "query" in keys:
            # 去掉常见的助词/前缀/后缀
            clean = re.sub(
                r'^(请|帮我|帮忙|搜索|查找|检索|找一找|找)\s*', '', text
            )
            clean = re.sub(r'\s*(吧|一下|呀|呢|了)\s*$', '', clean)
            params["query"] = clean.strip() or text.strip()
        
        if "text" in keys:
            params["text"] = params.get("query", text.strip())
        
        if "topic" in keys:
            params["topic"] = params.get("query", text.strip())
        
        if "description" in keys:
            params["description"] = params.get("query", text.strip())
        
        if "limit" in keys:
            # 尝试提取数字
            num_match = re.search(r'(\d+)\s*[篇个条]', text)
            params["limit"] = int(num_match.group(1)) if num_match else 10
        
        if "section_title" in keys:
            # 尝试提取章节
            section_match = re.search(r'[第]?([一二三四五六七八九十\d]+)[章节部分]', text)
            params["section_title"] = section_match.group(0) if section_match else ""
        
        if "mode" in keys:
            # 检测润色模式
            for kw, mode in [
                (r'降重|改写|paraphrase', 'paraphrase'),
                (r'精简|缩短|shorten', 'shorten'),
                (r'扩写|扩展|expand', 'expand'),
                (r'学术化|正式|academic', 'academic'),
            ]:
                if re.search(kw, text):
                    params["mode"] = mode
                    break
            params.setdefault("mode", "polish")
        
        return params
    
    def get_capabilities(self) -> List[Dict]:
        """列出解析器能识别的所有任务类型（供前端展示）"""
        return [
            {
                "task_type": t.value,
                "module": cfg["module"],
                "operation": cfg["operation"],
                "examples": [p for p in cfg["patterns"] if not p.startswith("(")],
            }
            for t, cfg in TASK_PATTERNS.items()
        ]