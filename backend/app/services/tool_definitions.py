"""
六大模块工具注册表
每个模块注册其工具到全局 ToolRegistry，供 Agent 调度

模块工具清单：
  literature: search, decompose, query_dimension, get_field, export_citation
  writing:    generate_outline, generate_section, polish_text, export_word
  charts:     auto_generate_chart, list_templates, parse_data
  agent:      chat, summarize, translate, analyze
  knowledge:  query_graph, extract_concepts, trend_analysis
  notes:      save_note, export_markdown, format_convert
"""

from app.services.agent_tools import tool, registry, get_orchestrator
from app.services.literature_service import (
    search_structured_papers, query_by_dimension, get_structured_paper,
    query_paper_field, decompose_paper, export_paper_citation,
    STRUCTURED_FIELDS, list_sources, get_paper_statistics,
)

# ═══════════════════════════════════════════════
# 文献管理模块工具
# ═══════════════════════════════════════════════

@tool(
    name="literature_search",
    module="literature",
    description="搜索结构化文献库。输入关键词，返回匹配的论文列表（含标题、作者、摘要等）。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"},
            "source": {"type": "string", "description": "来源过滤: local / database / api", "default": ""},
            "limit": {"type": "integer", "description": "返回数量", "default": 10},
        },
        "required": ["query"],
    }
)
async def _literature_search(query: str, source: str = "", limit: int = 10):
    result = search_structured_papers(query, source, limit=limit, offset=0)
    return result


@tool(
    name="literature_decompose",
    module="literature",
    description="使用 AI 将论文全文拆分为 11 个结构化字段（摘要、背景、目的、现状、问题、理论、方法、结果、创新、局限、结论）",
    parameters={
        "type": "object",
        "properties": {
            "paper_id": {"type": "string", "description": "文献唯一 ID"},
            "title": {"type": "string", "description": "论文标题"},
            "full_text": {"type": "string", "description": "论文全文文本"},
            "authors": {"type": "string", "description": "作者", "default": ""},
            "year": {"type": "integer", "description": "年份", "default": 0},
            "journal": {"type": "string", "description": "期刊", "default": ""},
            "doi": {"type": "string", "description": "DOI", "default": ""},
            "source": {"type": "string", "description": "来源", "default": "local"},
        },
        "required": ["paper_id", "title", "full_text"],
    }
)
async def _literature_decompose(
    paper_id: str, title: str, full_text: str,
    authors: str = "", year: int = 0, journal: str = "",
    doi: str = "", source: str = "local",
):
    paper = await decompose_paper(
        paper_id=paper_id, title=title, full_text=full_text,
        authors=authors, year=year, journal=journal, doi=doi, source=source,
    )
    return paper.__dict__


@tool(
    name="literature_dimension_query",
    module="literature",
    description="按学术维度查询文献。用于写作时为特定段落找引用支撑。维度选择: background(背景), method(方法), results(结果), innovation(创新), conclusion(结论) 等",
    parameters={
        "type": "object",
        "properties": {
            "dimension": {
                "type": "string",
                "description": f"查询维度，可选: {', '.join(STRUCTURED_FIELDS)}",
            },
            "keywords": {"type": "string", "description": "附加关键词过滤", "default": ""},
            "limit": {"type": "integer", "description": "返回数量", "default": 5},
        },
        "required": ["dimension"],
    }
)
async def _literature_dimension_query(dimension: str, keywords: str = "", limit: int = 5):
    return query_by_dimension(dimension, keywords, limit)


@tool(
    name="literature_get_field",
    module="literature",
    description="获取单篇文献的指定字段内容（用于插入引用时提取具体内容）",
    parameters={
        "type": "object",
        "properties": {
            "paper_id": {"type": "string", "description": "文献 ID"},
            "field": {
                "type": "string",
                "description": f"字段名，可选: {', '.join(STRUCTURED_FIELDS)}",
            },
        },
        "required": ["paper_id", "field"],
    }
)
async def _literature_get_field(paper_id: str, field: str):
    content = query_paper_field(paper_id, field)
    return {"paper_id": paper_id, "field": field, "content": content}


@tool(
    name="literature_export_citation",
    module="literature",
    description="导出文献的规范引用格式（GB/T 7714）。用于插入参考文献列表。",
    parameters={
        "type": "object",
        "properties": {
            "paper_id": {"type": "string", "description": "文献 ID"},
            "style": {"type": "string", "description": "引用格式: gbt7714", "default": "gbt7714"},
        },
        "required": ["paper_id"],
    }
)
def _literature_export_citation(paper_id: str, style: str = "gbt7714"):
    citation = export_paper_citation(paper_id, style)
    return {"citation": citation, "style": style}


# ═══════════════════════════════════════════════
# 写作模块工具
# ═══════════════════════════════════════════════

@tool(
    name="write_generate_outline",
    module="writing",
    description="根据论文主题生成详细提纲（含各章节标题、字数分配、章节描述）",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "论文主题"},
            "subject": {"type": "string", "description": "学科方向", "default": ""},
            "paper_type": {"type": "string", "description": "论文类型: 课程论文/本科毕业论文/硕博毕业论文/期刊论文", "default": "本科毕业论文"},
            "word_count": {"type": "integer", "description": "目标字数", "default": 12000},
        },
        "required": ["topic"],
    }
)
async def _write_generate_outline(topic: str, subject: str = "", paper_type: str = "本科毕业论文", word_count: int = 12000):
    from app.routers.writing import _call_ai, _build_system_prompt
    import json
    
    prompt = f"""请为以下论文主题生成详细的论文提纲：

**论文主题**：{topic}
**论文学科**：{subject or '通用'}
**论文类型**：{paper_type}
**目标字数**：{word_count}字

请按以下 JSON 格式返回：
{{
  "title": "论文标题",
  "outline": [
    {{"level": 1, "title": "第一章 绪论", "sections": [
      {{"level": 2, "title": "1.1 研究背景", "estimated_words": 800, "description": "..."}}
    ]}}
  ],
  "keywords": ["关键词"],
  "estimated_total_words": 8000
}}"""
    
    result = await _call_ai([
        {"role": "system", "content": _build_system_prompt("生成论文提纲")},
        {"role": "user", "content": prompt},
    ], temperature=0.5)
    
    try:
        for m in ["```json", "```"]:
            if m in result:
                result = result.split(m)[1].split("```")[0]
        return json.loads(result.strip())
    except:
        return {"raw": result}


@tool(
    name="write_generate_section",
    module="writing",
    description="根据提纲生成论文某一章节的完整内容",
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "论文主题"},
            "section_title": {"type": "string", "description": "章节标题"},
            "context_before": {"type": "string", "description": "前面已写的内容", "default": ""},
            "word_count": {"type": "integer", "description": "目标字数", "default": 1500},
        },
        "required": ["topic", "section_title"],
    }
)
async def _write_generate_section(topic: str, section_title: str, context_before: str = "", word_count: int = 1500):
    from app.routers.writing import _call_ai, _build_system_prompt
    
    prompt = f"""请撰写论文「{section_title}」章节：

**论文主题**：{topic}
**目标字数**：约 {word_count} 字

{f'上文已写内容（供上下文参考）：\n{context_before[:1000]}' if context_before else ''}

要求：学术语言，逻辑严密，论证充分，直接输出正文，不要加导语。"""
    
    result = await _call_ai([
        {"role": "system", "content": _build_system_prompt("撰写论文章节")},
        {"role": "user", "content": prompt},
    ], temperature=0.6)
    return {"section_title": section_title, "content": result}


@tool(
    name="write_polish",
    module="writing",
    description="润色学术文本。模式: polish(润色), academic(正式改写), shorten(精简), expand(扩写), paraphrase(降重)",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "需要润色的文本"},
            "mode": {"type": "string", "description": "润色模式", "default": "polish"},
        },
        "required": ["text"],
    }
)
async def _write_polish(text: str, mode: str = "polish"):
    from app.routers.writing import _call_ai, _build_system_prompt
    
    mode_prompts = {
        "polish": "润色，使语言更流畅、更学术化：",
        "academic": "改写为更正式、更学术的表达，使用专业术语：",
        "shorten": "精简，删除冗余，保留核心观点：",
        "expand": "扩写，增加学术细节和论证：",
        "paraphrase": "改写（降重用），保持原意，换不同表达：",
    }
    prompt_text = mode_prompts.get(mode, mode_prompts["polish"])
    
    result = await _call_ai([
        {"role": "system", "content": _build_system_prompt("学术文本润色")},
        {"role": "user", "content": f"{prompt_text}\n\n原文：\n{text}"},
    ], temperature=0.4)
    return {"mode": mode, "content": result}


# ═══════════════════════════════════════════════
# 绘图模块工具
# ═══════════════════════════════════════════════

@tool(
    name="chart_auto_generate",
    module="charts",
    description="根据数据描述自动生成符合学术规范的图表。支持 XRD、TG、FTIR、SEM 等 12 种模板。",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "图表需求描述"},
            "data": {"type": "string", "description": "JSON 格式的数据", "default": "[]"},
            "chart_type": {"type": "string", "description": "图表类型: xrd/tg/ftir/sem/scatter/bar/line", "default": "scatter"},
        },
        "required": ["description"],
    }
)
async def _chart_auto_generate(description: str, data: str = "[]", chart_type: str = "scatter"):
    import json as _json
    from app.services.ai_service import AIService
    
    try:
        parsed_data = _json.loads(data) if isinstance(data, str) else data
    except:
        parsed_data = []
    
        prompt = f"""你是一个科研绘图专家。请为以下需求生成 Plotly JSON 配置：

图表描述: {description}
图表类型: {chart_type}
数据: {_json.dumps(parsed_data, ensure_ascii=False)[:2000]}

返回 Plotly.js 的 data + layout JSON（不含额外解释）"""
    
    result = ""
    async for chunk in ai_service.chat([
        {"role": "system", "content": "你是一个专业的科研绘图助手，擅长生成 SCI 论文级的 Plotly 图表配置。"},
        {"role": "user", "content": prompt},
    ], temperature=0.3):
        result += chunk
    
    try:
        for m in ["```json", "```"]:
            if m in result:
                result = result.split(m)[1].split("```")[0]
        return _json.loads(result.strip())
    except:
        return {"raw": result, "chart_type": chart_type}


@tool(
    name="chart_list_templates",
    module="charts",
    description="列出所有可用的科研绘图模板",
    parameters={
        "type": "object",
        "properties": {},
    }
)
def _chart_list_templates():
    return {
        "templates": [
            {"id": "xrd-pattern", "name": "XRD 衍射图谱", "description": "粉末/薄膜 XRD 图谱"},
            {"id": "tg-curve", "name": "TG/DTG 热重曲线", "description": "热重分析"},
            {"id": "ftir-spectrum", "name": "FTIR 红外光谱", "description": "傅里叶变换红外"},
            {"id": "uv-vis", "name": "UV-Vis 紫外光谱", "description": "紫外可见吸收"},
            {"id": "cv-curve", "name": "CV 循环伏安", "description": "电化学循环伏安"},
            {"id": "nyquist", "name": "Nyquist 阻抗图", "description": "电化学阻抗谱"},
            {"id": "stress-strain", "name": "应力-应变曲线", "description": "材料力学"},
            {"id": "time-series", "name": "时间序列图", "description": "时序数据"},
            {"id": "bar-comparison", "name": "柱状对比图", "description": "分组比较"},
            {"id": "scatter-fit", "name": "散点拟合图", "description": "多项式拟合"},
            {"id": "heatmap", "name": "热力图", "description": "矩阵数据"},
            {"id": "sem-image", "name": "SEM/TEM 标注", "description": "电镜图叠加"},
        ]
    }


# ═══════════════════════════════════════════════
# 知识管理模块工具
# ═══════════════════════════════════════════════

@tool(
    name="knowledge_query_graph",
    module="knowledge",
    description="查询知识图谱中的实体和关系",
    parameters={
        "type": "object",
        "properties": {
            "entity": {"type": "string", "description": "实体名称或关键词"},
            "relation": {"type": "string", "description": "关系类型过滤", "default": ""},
            "limit": {"type": "integer", "description": "返回数量", "default": 20},
        },
        "required": ["entity"],
    }
)
async def _knowledge_query_graph(entity: str, relation: str = "", limit: int = 20):
    try:
        from app.routers.knowledge_graph import router as kg_router
        # 调用知识图谱查询接口
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "http://localhost:9000/api/kg/query",
                params={"entity": entity, "relation": relation, "limit": limit}
            )
            return resp.json() if resp.status_code == 200 else {"nodes": [], "edges": []}
    except Exception:
        return {"nodes": [], "edges": [], "message": f"知识图谱查询实体: {entity}"}


# ═══════════════════════════════════════════════
# Agent 基础工具
# ═══════════════════════════════════════════════

@tool(
    name="agent_summarize",
    module="agent",
    description="总结文本内容，提取核心要点",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "需要总结的文本"},
            "max_length": {"type": "integer", "description": "最大输出字数", "default": 200},
        },
        "required": ["text"],
    }
)
async def _agent_summarize(text: str, max_length: int = 200):
    from app.services.ai_service import ai_service
    result = ""
    async for chunk in ai_service.chat([
        {"role": "system", "content": f"请用不超过{max_length}字总结以下内容，提取核心要点。"},
        {"role": "user", "content": text[:5000]},
    ], temperature=0.3):
        result += chunk
    return {"summary": result}


# ═══════════════════════════════════════════════
# 初始化报告
# ═══════════════════════════════════════════════

def init_agent_tools():
    """初始化所有模块工具"""
    registry_summary = registry.summary()
    print(f"[AgentTools] Total tools registered: {registry_summary['total_tools']}")
    for module, count in registry_summary['modules'].items():
        print(f"  {module}: {count} tools")
    return registry_summary


# 模块导入时自动注册
init_agent_tools()
