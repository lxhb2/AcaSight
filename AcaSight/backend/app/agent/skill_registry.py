"""
Skill Registry — 学术技能注册表
借鉴 Hermes Agent skill_utils 模式，声明式注册学术技能
Agent 通过 OpenAI function calling 自动调度
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import json
import structlog

logger = structlog.get_logger()


class SkillCategory(Enum):
    LITERATURE = "literature"       # 文献管理
    READING = "reading"             # PDF 阅读
    WRITING = "writing"             # 写作辅助
    ANALYSIS = "analysis"           # 数据分析
    FORMATTING = "formatting"       # 格式排版
    TRANSLATION = "translation"     # 翻译
    SEARCH = "search"               # 检索
    FIGURE = "figure"               # 图表生成
    CITATION = "citation"           # 引用管理
    DATA = "data"                   # 数据可用性
    RESPONSE = "response"           # 审稿回复
    PAPER2PPT = "paper2ppt"        # 论文转PPT
    DATA_PROCESS = "data_process"  # 数据预处理
    AUTO_CHART = "auto_chart"      # 自动绘图
    KNOWLEDGE_GRAPH = "knowledge_graph"  # 知识图谱
    DOCUMENT_PARSE = "document_parse"    # 文档解析


@dataclass
class SkillDefinition:
    """学术技能定义"""
    name: str                           # 技能名称（工具调用名）
    description: str                    # LLM 可读描述（关键！）
    category: SkillCategory             # 分类
    parameters: dict                   # JSON Schema 参数定义
    handler: Callable                  # 实际执行函数
    examples: List[str] = field(default_factory=list)  # 使用示例
    requires_context: List[str] = field(default_factory=list)  # 需要的上下文


class SkillBundle:
    """技能包 — 将多个相关技能组合为一个逻辑组
    
    参考 Hermes Agent 的 skill_bundles.py 设计。
    用于前端的分类展示和 Agent 的按组检索。
    """
    name: str
    description: str
    skills: List[str]  # skill names
    category: SkillCategory
    
    def __init__(self, name: str, description: str, skills: List[str], category: SkillCategory):
        self.name = name
        self.description = description
        self.skills = skills
        self.category = category


class SkillRegistry:
    """技能注册表 — Agent 通过此表发现和调用技能"""
    
    # 预定义的技能包
    BUILTIN_BUNDLES = {
        "reading": SkillBundle(
            name="reading",
            description="文献阅读与理解：问答、摘要、翻译",
            skills=["paper_qa", "paper_summarize", "translate_text"],
            category=SkillCategory.READING,
        ),
        "writing": SkillBundle(
            name="writing",
            description="学术写作：起草章节、生成大纲、润色",
            skills=["draft_section", "generate_outline", "polish_text", "format_citation"],
            category=SkillCategory.WRITING,
        ),
        "search": SkillBundle(
            name="search",
            description="文献检索与发现：外部数据源 + 本地 Zotero 库",
            skills=["search_literature", "search_zotero", "find_similar_zotero"],
            category=SkillCategory.SEARCH,
        ),
        "review": SkillBundle(
            name="review",
            description="论文评审与回复：审稿回复、数据可用性",
            skills=["draft_response", "check_data_availability"],
            category=SkillCategory.RESPONSE,
        ),
        "presentation": SkillBundle(
            name="presentation",
            description="论文展示与图表：PPT生成、学术图表",
            skills=["paper_to_ppt", "generate_figure"],
            category=SkillCategory.PAPER2PPT,
        ),
    }
    
    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._bundles: Dict[str, SkillBundle] = dict(self.BUILTIN_BUNDLES)
    
    def register(self, skill: SkillDefinition):
        """注册一个技能"""
        if skill.name in self._skills:
            raise ValueError(f"技能已存在: {skill.name}")
        self._skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name} ({skill.category.value})")
    
    def register_bundle(self, bundle: SkillBundle):
        """注册一个技能包"""
        if bundle.name in self._bundles:
            raise ValueError(f"技能包已存在: {bundle.name}")
        # 验证包内技能都存在
        for sname in bundle.skills:
            if sname not in self._skills:
                raise ValueError(f"技能包 {bundle.name} 引用了未注册的技能: {sname}")
        self._bundles[bundle.name] = bundle
        logger.info(f"Registered skill bundle: {bundle.name} ({len(bundle.skills)} skills)")
    
    def get_tool_schemas(self, bundle_name: Optional[str] = None) -> List[dict]:
        """生成 OpenAI function calling 格式的工具定义
        
        Args:
            bundle_name: 可选，限定为某个技能包的工具
        """
        skills = self._skills.values()
        if bundle_name and bundle_name in self._bundles:
            bundle = self._bundles[bundle_name]
            skills = [s for s in skills if s.name in bundle.skills]
        
        return [
            {
                "type": "function",
                "function": {
                    "name": s.name,
                    "description": s.description,
                    "parameters": s.parameters,
                }
            }
            for s in skills
        ]
    
    async def execute(self, tool_name: str, arguments: dict) -> Any:
        """执行技能"""
        skill = self._skills.get(tool_name)
        if not skill:
            return {"error": f"未知技能: {tool_name}"}
        
        try:
            import inspect
            if inspect.iscoroutinefunction(skill.handler):
                return await skill.handler(**arguments)
            else:
                return skill.handler(**arguments)
        except Exception as e:
            return {"error": f"技能执行失败: {str(e)}"}
    
    def list_skills(self, category: Optional[str] = None) -> List[dict]:
        """列出所有技能（可筛选分类）
        
        Args:
            category: 可选，按分类筛选
        """
        skills = self._skills.values()
        if category:
            skills = [s for s in skills if s.category.value == category]
        
        return [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category.value,
                "examples": s.examples,
            }
            for s in skills
        ]
    
    def list_bundles(self) -> List[dict]:
        """列出所有技能包"""
        return [
            {
                "name": b.name,
                "description": b.description,
                "category": b.category.value,
                "skills": [
                    {"name": s, "description": self._skills[s].description}
                    for s in b.skills if s in self._skills
                ],
            }
            for b in self._bundles.values()
        ]
