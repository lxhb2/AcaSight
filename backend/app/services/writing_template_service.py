"""
写作模板系统服务 (方向U.3)

功能:
1. 模板 CRUD
2. 分类标签
3. 模板分享
4. 默认模板
5. 模板搜索
"""

import json
import os
import time
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

DEFAULT_TEMPLATES_DIR = os.path.join(os.getcwd(), "data", "writing_templates")


# ── 默认模板 ──

BUILT_IN_TEMPLATES = [
    {
        "id": "sci-research-article",
        "name": "SCI 研究论文",
        "description": "标准 SCI 期刊研究论文结构",
        "category": "research",
        "tags": ["SCI", "研究论文", "IMRAD"],
        "sections": [
            {"title": "Abstract", "description": "摘要 (250词以内)", "required": True},
            {"title": "Introduction", "description": "引言: 研究背景、问题、目标", "required": True},
            {"title": "Methods", "description": "方法: 实验/计算/分析方法", "required": True},
            {"title": "Results", "description": "结果: 数据、图表、统计", "required": True},
            {"title": "Discussion", "description": "讨论: 结果解释、对比、意义", "required": True},
            {"title": "Conclusion", "description": "结论: 核心发现与展望", "required": True},
            {"title": "References", "description": "参考文献", "required": True},
        ],
        "style": {
            "citation_format": "GB/T 7714",
            "figure_style": "nature",
            "language": "zh",
        },
        "is_builtin": True,
    },
    {
        "id": "review-article",
        "name": "综述论文",
        "description": "文献综述/系统综述模板",
        "category": "review",
        "tags": ["综述", "文献回顾", "系统评价"],
        "sections": [
            {"title": "Abstract", "description": "摘要", "required": True},
            {"title": "Introduction", "description": "引言: 综述范围与目的", "required": True},
            {"title": "Search Strategy", "description": "检索策略: 数据库/关键词/筛选", "required": True},
            {"title": "Main Body", "description": "主体: 按主题/时间/方法分类", "required": True},
            {"title": "Analysis", "description": "分析: 对比/趋势/空白", "required": True},
            {"title": "Conclusion", "description": "结论与展望", "required": True},
            {"title": "References", "description": "参考文献", "required": True},
        ],
        "style": {"citation_format": "APA", "language": "zh"},
        "is_builtin": True,
    },
    {
        "id": "case-report",
        "name": "病例报告",
        "description": "医学病例报告 (CARE 指南)",
        "category": "clinical",
        "tags": ["病例报告", "CARE", "临床"],
        "sections": [
            {"title": "Abstract", "description": "摘要", "required": True},
            {"title": "Introduction", "description": "引言", "required": True},
            {"title": "Case Presentation", "description": "病例展示", "required": True},
            {"title": "Discussion", "description": "讨论", "required": True},
            {"title": "Conclusion", "description": "结论", "required": True},
            {"title": "References", "description": "参考文献", "required": True},
        ],
        "style": {"citation_format": "Vancouver", "language": "zh"},
        "is_builtin": True,
    },
    {
        "id": "conference-paper",
        "name": "会议论文",
        "description": "学术会议论文模板 (4-8页)",
        "category": "conference",
        "tags": ["会议", "短论文"],
        "sections": [
            {"title": "Abstract", "description": "摘要 (150词)", "required": True},
            {"title": "Introduction", "description": "引言", "required": True},
            {"title": "Methodology", "description": "方法", "required": True},
            {"title": "Results and Discussion", "description": "结果与讨论 (合并)", "required": True},
            {"title": "Conclusion", "description": "结论", "required": True},
            {"title": "References", "description": "参考文献 (精简)", "required": True},
        ],
        "style": {"citation_format": "IEEE", "language": "en"},
        "is_builtin": True,
    },
]


class WritingTemplateService:
    """
    写作模板系统服务
    
    存储结构:
    data/writing_templates/
    ├── built_in/                    # 内置模板
    │   └── {template_id}.json
    └── custom/                      # 用户自定义模板
        └── {template_id}.json
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        self._templates_dir = templates_dir or DEFAULT_TEMPLATES_DIR
        self._built_in_dir = os.path.join(self._templates_dir, "built_in")
        self._custom_dir = os.path.join(self._templates_dir, "custom")
        
        os.makedirs(self._built_in_dir, exist_ok=True)
        os.makedirs(self._custom_dir, exist_ok=True)
        
        # 初始化内置模板
        self._init_built_in_templates()
    
    def _init_built_in_templates(self):
        """初始化内置模板"""
        for template in BUILT_IN_TEMPLATES:
            path = os.path.join(self._built_in_dir, f"{template['id']}.json")
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(template, f, ensure_ascii=False, indent=2)
    
    def list_templates(
        self,
        category: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict]:
        """列出所有模板 (内置 + 自定义)"""
        templates = []
        
        # 读取内置模板
        for filename in os.listdir(self._built_in_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self._built_in_dir, filename), "r", encoding="utf-8") as f:
                    templates.append(json.load(f))
        
        # 读取自定义模板
        for filename in os.listdir(self._custom_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self._custom_dir, filename), "r", encoding="utf-8") as f:
                    templates.append(json.load(f))
        
        # 过滤
        if category:
            templates = [t for t in templates if t.get("category") == category]
        
        if tag:
            templates = [t for t in templates if tag in t.get("tags", [])]
        
        if search:
            search_lower = search.lower()
            templates = [
                t for t in templates
                if search_lower in t.get("name", "").lower()
                or search_lower in t.get("description", "").lower()
                or search_lower in " ".join(t.get("tags", []))
            ]
        
        return templates
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取模板"""
        # 先查自定义
        custom_path = os.path.join(self._custom_dir, f"{template_id}.json")
        if os.path.exists(custom_path):
            with open(custom_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        # 再查内置
        builtin_path = os.path.join(self._built_in_dir, f"{template_id}.json")
        if os.path.exists(builtin_path):
            with open(builtin_path, "r", encoding="utf-8") as f:
                return json.load(f)
        
        return None
    
    def create_template(self, template: Dict) -> Dict:
        """创建自定义模板"""
        template_id = template.get("id") or f"custom-{int(time.time())}"
        template["id"] = template_id
        template["is_builtin"] = False
        template["created_at"] = time.time()
        
        path = os.path.join(self._custom_dir, f"{template_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        logger.info("Template created", template_id=template_id)
        return {"id": template_id, "created": True}
    
    def update_template(self, template_id: str, updates: Dict) -> Optional[Dict]:
        """更新自定义模板 (不允许修改内置模板)"""
        custom_path = os.path.join(self._custom_dir, f"{template_id}.json")
        if not os.path.exists(custom_path):
            return None
        
        with open(custom_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        
        template.update(updates)
        template["updated_at"] = time.time()
        
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        
        return template
    
    def delete_template(self, template_id: str) -> bool:
        """删除自定义模板 (不允许删除内置模板)"""
        custom_path = os.path.join(self._custom_dir, f"{template_id}.json")
        if not os.path.exists(custom_path):
            return False
        
        os.remove(custom_path)
        logger.info("Template deleted", template_id=template_id)
        return True
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        templates = self.list_templates()
        categories = set()
        for t in templates:
            if t.get("category"):
                categories.add(t["category"])
        return sorted(categories)


# Singleton
_writing_template_service: Optional[WritingTemplateService] = None


def get_writing_template_service() -> WritingTemplateService:
    global _writing_template_service
    if _writing_template_service is None:
        _writing_template_service = WritingTemplateService()
    return _writing_template_service
