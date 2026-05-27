"""
Nature Skills v2.0 — 将 nature-skills 的 9 个完整学术能力注册为 Agent 技能

每个技能深度嵌入了 Nature 期刊标准规则（来自 nature-skills 的 SKILL.md 文件）。
不再依赖磁盘文件加载，所有规则内联在代码中。

映射关系：
- nature-reader       → paper_qa, paper_summarize
- nature-polishing    → polish_text
- nature-writing      → draft_section, generate_outline
- nature-citation     → format_citation
- nature-figure       → generate_figure
- nature-academic-search → search_literature
- nature-response     → draft_response
- nature-data         → check_data_availability
- nature-paper2ppt    → paper_to_ppt

参考: https://github.com/Yuan1z0825/nature-skills
"""

import asyncio
import json
import structlog
from typing import Any, Dict, List, Optional

from app.agent.skill_registry import SkillDefinition, SkillCategory, SkillRegistry

logger = structlog.get_logger()


def _get_ai_service():
    from app.services.ai_service import ai_service
    return ai_service


async def _safe_chat(messages, max_tokens=4096, timeout=60.0, provider=None):
    try:
        result = ""

        async def _do_chat():
            nonlocal result
            async for chunk in _get_ai_service().chat(
                messages, max_tokens=max_tokens, provider=provider
            ):
                result += chunk
            return result

        return await asyncio.wait_for(_do_chat(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error("AI chat timeout", timeout=timeout)
        raise
    except Exception as e:
        logger.error("AI chat failed", error=str(e))
        raise


# ============================================================
# Nature 学术规则 — 深度嵌入（来自 nature-skills SKILL.md）
# ============================================================

# ---- nature-reader 规则 ----
READER_RULES = """# Nature Reader — 全文阅读与翻译规则

## 核心原则
1. 生成段级中英对照 Markdown，不是纯摘要或纯翻译
2. 保留论文结构、证据链、术语、方程式、引用标记
3. 图片和表格提取为资源文件，放置在首次提及位置
4. 图注保持英文原文 + 中文翻译并列
5. 每一实质性段落保留原文锚点（页码+段落位置）
6. 输出文件: paper.md (完整双语阅读器), source_map.json, translation_notes.md

## 双语对照规范
- 原文和翻译在段落级别并排展示
- 专业术语首次出现时标注英文原文
- 引用标记 [1], (Author, 2023) 保留不变
- 保持学术语言的精确性，不意译不增减
- 长句按中文习惯适当拆分，保持原意

## 什么时候用
- 全文翻译阅读
- 中英对照精读
- 提取论文核心论证
- 回答论文相关问题"""

# ---- nature-polishing 规则 ----
POLISHING_RULES = """# Nature Style Academic Polishing — 学术润色规则

## 核心原则
1. 语言服务于论证 — 不要在论证有问题的前提下润色句子
2. 写作顺序优先于措辞 — 先确保逻辑清晰
3. 以同理心对待读者 — 相关 > 新颖 > 可信 > 可复用 > 意义
4. 不编造数据、参考文献、机制或新颖性声明
5. 核心论证必须由作者提供，AI 不得从头起草

## 文章层级润色规则

### 1. 先识别论文类型
- Research paper: 读者想知道现象为何重要、研究方法是否可靠、结论是否被证据支持
- Methods paper: 公平比较、使用门槛、与现有方法的差异
- Review: 覆盖范围、分类逻辑、批判性分析

### 2. 各部分写作规范

**摘要**:
- Context → Gap → Approach → Key Result → Implication
- 每句话承担一个功能，不重复
- 动词使用现在时（除方法用过去时）

**引言**:
- Field Scale → Bottleneck → Prior Attempts → Unresolved Gap → Present Study
- 漏斗式：从宽到窄
- 每段只有一个核心论点

**方法**:
- Module Motivation → Module Design → Forward Process → Technical Advantage
- 提供足够的实验细节使结果可复现

**结果**:
- 构建证据阶梯，不是按时间顺序的实验日志
- 每个结果必须有对应的主要图表
- 不讨论结果的意义（留给 Discussion）

**讨论**:
- 解释结果的意义与领域的关系
- 与已有工作对比
- 坦诚说明局限性
- 指出未来方向和应用前景

### 3. 语言规范
- 句子不超过 30 词
- 避免过度声明（不使用 groundbreaking, unprecedented 等）
- 声明强度匹配证据强度
- 避免破折号（em dash），优先用逗号或括号
- 英式英语拼写
- 被动语态按学科惯例使用

### 4. 引用规范
- 每个声明必须有文献支撑
- 引用位置在句末标点之前
- 不自引（除非必要）
- 参考文献格式统一"""

# ---- nature-writing 规则 ----
WRITING_RULES = """# Nature Style Scientific Writing — 学术写作规则

## 核心原则
1. 作者提供证据，AI 不做编造
2. 先写论证，再写句子
3. 让论文易于被评判：相关性、新颖性、可信度、可复用性、意义
4. 声明要有边界，不做超出证据范围的推广

## 各章节写作指南

### Abstract (摘要)
- Context → Gap → Approach → Key Result → Implication 结构
- 长度: 150-250 词
- 关键结果用量化表述（"提高了 23%" 而非 "显著提高"）

### Introduction (引言)
- Field Scale → Bottleneck → Prior Attempts → Unresolved Gap → Present Study
- 仅引用高度相关的文献
- 明确说明本文贡献

### Method (方法)
- Module Motivation → Module Design → Forward Process → Technical Advantage
- 包含足够细节使实验可复现
- 数据集、代码、训练配置需明确说明

### Results (结果)
- 构建证据阶梯，每个结论有一级证据支撑
- 按科学逻辑组织（非实验时间顺序）
- 用量化结果替代主观描述

### Discussion (讨论)
- 核心发现的意义
- 与相关工作的系统对比
- 局限性声明（不回避）
- 未来方向和应用前景

### Conclusion (结论)
- 3-5 句：核心发现 + 贡献 + 局限 + 展望"""

# ---- nature-citation 规则 ----
CITATION_RULES = """# Nature Citation — 学术引用规则

## 核心原则
1. 每个片段分配稳定 ID (S001, S002...)
2. Nature 系列优先：Nature, Nature [field], Nature Communications, Communications [field], Scientific Reports, npj
3. CNS 范围：Cell, Nature, Science 及其主要姊妹刊
4. 文献必须真正支撑对应声明（不仅标题相关）
5. 搜索结果优先使用: Crossref > PubMed > 出版社官方页 > 二次索引

## 引用强度标记
- 强支撑: 该文献直接支撑该声明
- 部分支撑: 该文献部分相关
- 背景支撑: 提供背景信息
- 不建议引用: 标题相关但实际不支撑

## 输出格式
- 文本 (.txt): 段级引用建议 + 每段候选文献
- 引用管理文件: ENW / RIS / Zotero RDF
- 结构化 JSON: 段→文献映射关系

## 中文用户模式
- 用户可用中文输入，但用英文概念查询
- 默认返回中文说明
- 中国特有的主题可以用中文文献"""

# ---- nature-figure 规则 ----
FIGURE_RULES = """# Nature Figure Making — 学术图表规范

## 核心原则
1. 每张图始于一个核心结论和证据层次
2. 先定 figure contract（结论、证据逻辑、导出格式、审稿风险），再写代码
3. 颜色策略：同一方法族在不同 panel 使用相同颜色
4. 首选 Python: matplotlib + seaborn + subplot_mosaic + statsmodels
5. 次选 R: ggplot2 + patchwork + ComplexHeatmap + ggrepel + svglite

## 技术规范
- 字体: Arial / DejaVu Sans (非衬线)
- 主输出: SVG (可编辑矢量)
- 次输出: PNG 300 dpi
- 颜色: Nature 调色板（低饱和度）
- 字体大小: 7-8 pt (panel 标签), 6-7 pt (轴标签), 5-6 pt (图注)

## 图表类型
- bar: 分类对比
- line: 趋势/时间序列
- heatmap: 二维密度
- scatter: 相关性/分布
- radar: 多维对比
- distribution: 分布统计
- forest: 效应量汇总
- area: 累积趋势
- image_plate: 图像排版
- network: 网络关系

## rcParams 必须设置
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['svg.fonttype'] = 'none'"""

# ---- nature-response 规则 ----
RESPONSE_RULES = """# Nature Reviewer Response — 审稿意见回复规则

## 核心原则
1. 每条审稿意见必须回应、交叉引用或标记为未解决
2. 每条回复映射到: 稿件修改证据 / 修改位置 / 合理异议 / AUTHOR_INPUT_NEEDED
3. 不编造实验、分析、引用、行号、图 panels 或补充材料
4. 优先简洁、证据导向的回复，而不是冗长的辩解
5. 提出异议时，先承认审稿人的关切，再给出科学理由

## 回复结构
1. 识别决策类型: minor revision / major revision / revise-and-resubmit
2. 提取编辑指示 (E.1, E.2...) 和审稿人评论 (R1.1, R1.2...)
3. 每条评论分类: major / minor / editorial
4. 创建回复策略摘要
5. 起草逐条回复
6. 修改声明映射到具体位置

## 回复语气
- 专业、合作
- 不防御、不争辩
- 每条评论以感谢开头
- 不接受的意见给出科学理由"""

# ---- nature-data 规则 ----
DATA_RULES = """# Nature Data Availability — 数据可用性声明规则

## 核心原则
1. 每个支撑结果的数据集有持久访问路径
2. 优先学科专用存储库 > 通用存储库 > 补充材料
3. 限制数据必须说明原因和申请路径
4. FAIR 原则: 可发现、可访问、可互操作、可复用

## 声明要素
- 新生成数据和复用第三方数据分别声明
- 数据不能开放共享时: 说明原因、谁控制访问、如何评估申请
- 数据、代码、材料、材料声明分开
- 每个数据集包含: 存储库、入库号、许可证、保存期限

## 中文→英文术语转换
- 数据可用性声明 → Data Availability
- 原始数据 → raw data
- 处理后数据 → processed data
- 源数据 → source data
- 补充材料 → Supplementary Information
- 受限数据 → restricted data
- 合理请求 → reasonable request (需说明审核路径)"""

# ---- nature-paper2ppt 规则 ----
PAPER2PPT_RULES = """# Nature Paper to PPT — 论文转PPT规则

## 核心原则
1. 以论文科学论证为演示主线（非章节顺序）
2. 默认 10-16 页中文 PPT
3. 仅选取支撑论证的图表
4. 每页包含: 标题、要点、关键数据/图表
5. 输出真实 .pptx 文件

## 幻灯逻辑顺序
1. 问题为什么重要？
2. 论文填补什么空白？
3. 作者做了什么？
4. 关键证据是什么？
5. 为什么结果可信？
6. 什么新的/可复用的？
7. 局限性和开放问题

## 技术规范
- Python-first: PyMuPDF (元数据/文本), Pillow (裁剪), python-pptx (PPT生成)
- 不安装新依赖（如已有工具可完成）
- 不启动 GUI 应用
- 不需要每页渲染预览
- 默认避免穷举 OCR"""


# ============================================================
# 工具实现函数
# ============================================================

async def paper_qa_handler(query: str, pdf_id: str) -> dict:
    """基于 PDF 全文回答学术问题"""
    try:
        from app.services.vector_service import vector_service
        relevant_chunks = await vector_service.asearch(
            query, filter={"pdf_id": pdf_id}, top_k=5
        )
        
        if not relevant_chunks:
            return {"answer": "未找到相关段落，请确认 PDF 已导入向量库。", "citations": []}
        
        context_text = "\n\n---\n\n".join(
            [c.get("text", c.get("content", "")) for c in relevant_chunks]
        )
        
        system_msg = (
            "你是一位学术文献阅读助手。\n\n"
            f"{READER_RULES}\n\n"
            "请基于给定的文献段落回答以下问题。严格基于原文，不编造。引用时标注段落位置。"
        )
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"文献内容：\n{context_text[:6000]}\n\n问题：{query}"}
        ]
        
        result = await _safe_chat(messages, max_tokens=2000)
        
        if not result:
            return {"answer": "AI 服务未返回结果，请检查 AI 配置。", "citations": []}
        
        citations = [
            {"text": c.get("text", c.get("content", ""))[:100], "score": c.get("score", 0)}
            for c in relevant_chunks[:3]
        ]
        
        return {"answer": result, "citations": citations}
    
    except Exception as e:
        logger.error("paper_qa failed", error=str(e))
        return {"answer": f"处理失败: {str(e)}", "citations": []}


async def paper_summarize_handler(pdf_id: str, length: str = "medium", language: str = "chinese") -> dict:
    """生成论文摘要"""
    length_map = {"short": 200, "medium": 500, "long": 1000}
    max_len = length_map.get(length, 500)
    
    lang_note = "请用中文生成摘要。" if language == "chinese" else "Generate the summary in English."
    
    system_msg = (
        f"请按照 Nature 期刊标准生成学术论文摘要，约 {max_len} 字。{lang_note}\n\n"
        f"{READER_RULES}\n\n"
        "摘要结构：Context → Gap → Approach → Key Result → Implication\n"
        "用量化结果替代主观描述，不编造任何数据。"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": f"请为以下文献生成摘要（PDF ID: {pdf_id}）。如果上下文中包含文献全文，请基于全文生成；否则请提示用户先打开 PDF 文件。"}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=2000)
        if not result:
            return {"summary": "AI 服务未返回结果，请检查 AI 配置。", "pdf_id": pdf_id, "length": length, "status": "error"}
        return {"summary": result, "pdf_id": pdf_id, "length": length, "status": "ok"}
    except Exception as e:
        return {"summary": f"摘要生成失败: {str(e)}", "pdf_id": pdf_id, "length": length, "status": "error"}


async def polish_text_handler(text: str, style: str = "nature", target_lang: str = "english") -> dict:
    """学术文本润色 — 基于 Nature 标准的 12 步润色流程"""
    style_desc = {
        "nature": "Nature 期刊风格（精确、简洁、英式英语）",
        "academic": "通用学术风格",
        "concise": "极简风格",
    }.get(style, "学术风格")
    
    system_msg = (
        f"你是学术文本润色专家。请遵循以下规则润色文本。\n"
        f"风格：{style_desc}\n"
        f"目标语言：{target_lang}\n\n"
        f"{POLISHING_RULES}\n\n"
        "润色步骤：\n"
        "1. 首先阅读全文，理解核心论证\n"
        "2. 检查逻辑结构是否需要重组\n"
        "3. 逐句润色：缩短句子至 ≤30 词\n"
        "4. 检查声明强度：移除过度声明\n"
        "5. 统一术语\n"
        "6. 最终通读确认流畅性\n\n"
        "直接输出润色后的文本，不要加解释。"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": text}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"polished": "AI 服务未返回结果，请检查 AI 配置。", "style": style, "original_length": len(text), "target_lang": target_lang}
        
        return {"polished": result, "style": style, "original_length": len(text), "target_lang": target_lang}
    except Exception as e:
        logger.error("polish_text failed", error=str(e))
        return {"polished": f"润色失败: {str(e)}", "style": style, "original_length": len(text), "target_lang": target_lang}


async def translate_text_handler(text: str, source_lang: str = "auto", target_lang: str = "english", domain: str = "academic") -> dict:
    """学术翻译 — 保持术语准确，句式符合学术惯例"""
    system_msg = (
        f"你是 Nature 期刊级学术翻译专家。请将文本从 {source_lang} 翻译为 {target_lang}。\n\n"
        f"{READER_RULES}\n\n"
        "翻译要求：\n"
        "1. 术语翻译准确，符合学科惯例\n"
        "2. 保持学术语言风格\n"
        "3. 长句按目标语言习惯适当拆分\n"
        "4. 专有名词保留原文或按通行译法\n"
        "5. 被动语态按目标语言习惯调整\n"
        "6. 专业术语首次出现时在括号标注原文\n"
        "7. 不意译、不增减信息\n\n"
        "直接输出翻译后的文本。"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": text}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"translated": "AI 服务未返回结果，请检查 AI 配置。", "source_lang": source_lang, "target_lang": target_lang}
        
        return {"translated": result, "source_lang": source_lang, "target_lang": target_lang}
    except Exception as e:
        logger.error("translate_text failed", error=str(e))
        return {"translated": f"翻译失败: {str(e)}", "source_lang": source_lang, "target_lang": target_lang}


async def draft_section_handler(
    section_type: str, topic: str, key_points: str = "", references: str = ""
) -> dict:
    """论文章节起草 — 严格按 Nature 各章节写作指南"""
    section_guides = {
        "abstract": "Context → Gap → Approach → Key Result → Implication",
        "introduction": "Field Scale → Bottleneck → Prior Attempts → Unresolved Gap → Present Study",
        "method": "Module Motivation → Module Design → Forward Process → Technical Advantage",
        "results": "构建证据阶梯，每个结论有数据支撑。非实验日志。",
        "discussion": "核心意义 → 与已有工作对比 → 局限性 → 未来方向",
        "conclusion": "核心发现 → 学术贡献 → 局限性 → 未来展望（3-5句）",
    }
    
    guide = section_guides.get(section_type, "")
    
    system_msg = (
        f"你是学术论文写作专家。请起草 {section_type} 章节。\n"
        f"主题：{topic}\n"
        f"写作指南：{guide}\n\n"
        f"{WRITING_RULES}\n\n"
        "严格要求：\n"
        "- 不编造数据、机制、参考文献、统计量\n"
        "- 只基于提供的信息写作\n"
        "- 保持学术语言的精确性\n"
        "- 每个结论必须有证据支撑"
    )
    
    if key_points:
        system_msg += f"\n\n要点：\n{key_points}"
    if references:
        system_msg += f"\n\n参考文献：\n{references}"
    
    messages = [{"role": "system", "content": system_msg}]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"draft": "AI 服务未返回结果，请检查 AI 配置。", "section_type": section_type, "topic": topic}
        
        return {"draft": result, "section_type": section_type, "topic": topic}
    except Exception as e:
        logger.error("draft_section failed", error=str(e))
        return {"draft": f"章节起草失败: {str(e)}", "section_type": section_type, "topic": topic}


async def generate_outline_handler(topic: str, paper_type: str = "research", field: str = "") -> dict:
    """生成论文大纲"""
    system_msg = (
        "你是学术论文架构师。请为以下主题生成 Nature 风格论文大纲。\n\n"
        f"{WRITING_RULES}\n\n"
        f"主题：{topic}\n"
        f"论文类型：{paper_type}\n"
        f"领域：{field or '通用'}\n\n"
        "输出格式：\n"
        "1. 标题建议（3个备选）\n"
        "2. 各章节标题和核心要点\n"
        "3. 预计各章节字数\n"
        "4. 关键图表建议（每个主要结果配一张图/表）\n"
        "5. 参考文献范围"
    )
    
    messages = [{"role": "system", "content": system_msg}]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"outline": "AI 服务未返回结果，请检查 AI 配置。", "topic": topic, "paper_type": paper_type}
        
        return {"outline": result, "topic": topic, "paper_type": paper_type}
    except Exception as e:
        logger.error("generate_outline failed", error=str(e))
        return {"outline": f"大纲生成失败: {str(e)}", "topic": topic, "paper_type": paper_type}


async def format_citation_handler(
    references: str, style: str = "nature", output_format: str = "text"
) -> dict:
    """格式化参考文献 — 支持多种期刊风格"""
    style_names = {
        "nature": "Nature 风格（Vancouver 数字序号）",
        "ieee": "IEEE 风格",
        "apa": "APA 第7版",
        "vancouver": "Vancouver 风格",
    }
    
    system_msg = (
        "你是学术引用格式化专家。\n\n"
        f"{CITATION_RULES}\n\n"
        f"请将以下参考文献格式化为 {style_names.get(style, style)}。\n"
        f"输出格式: {output_format}\n\n"
        "格式要求：\n"
        "- 作者：姓全称 + 名缩写\n"
        "- 标题：首字母大写（专有名词除外）\n"
        "- 期刊名：标准缩写\n"
        "- 年份、卷(期)、页码\n"
        "- DOI 放在最后"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": references}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"formatted": "AI 服务未返回结果，请检查 AI 配置。", "style": style, "output_format": output_format}
        
        return {"formatted": result, "style": style, "output_format": output_format}
    except Exception as e:
        logger.error("format_citation failed", error=str(e))
        return {"formatted": f"引用格式化失败: {str(e)}", "style": style, "output_format": output_format}


async def search_literature_handler(
    query: str, sources: str = "crossref,pubmed,arxiv", limit: int = 10
) -> dict:
    """多源文献检索"""
    try:
        from app.services.search_service import LiteratureSearchService
        svc = LiteratureSearchService()
        source_list = [s.strip() for s in sources.split(",")]
        results = await svc.search(query, sources=source_list, limit=limit)
        total = sum(
            len(r.get("results", [])) for r in results.values() if isinstance(r, dict)
        )
        return {"results": results, "count": total}
    except Exception as e:
        logger.warning(f"Search service failed, using AI suggestion: {e}")
        system_msg = (
            "你是学术文献检索助手。\n\n"
            "请基于用户查询给出检索建议，包括：\n"
            "1. 推荐的关键词组合（含 MeSH 词）\n"
            "2. 建议检索的数据源\n"
            "3. 已知的重要文献方向\n"
            "4. 时间范围建议"
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"数据源：{sources}\n限制：{limit} 条\n查询：{query}"}
        ]
        
        try:
            result = await _safe_chat(messages, max_tokens=1500)
            
            if not result:
                return {"suggestions": "AI 服务未返回结果，请检查 AI 配置。", "note": "实际检索需要搜索服务运行", "count": 0}
            
            return {"suggestions": result, "note": "实际检索需要搜索服务运行", "count": 0}
        except Exception as e2:
            logger.error("search_literature AI fallback failed", error=str(e2))
            return {"suggestions": f"检索建议生成失败: {str(e2)}", "note": "搜索服务和 AI 均不可用", "count": 0}


async def search_zotero_handler(
    query: str,
    title: str = "",
    year_range: str = "",
    fulltext: str = "",
    item_type: str = "",
    mode: str = "standard",
    limit: int = 20,
    sort: str = "relevance",
) -> dict:
    """搜索本地 Zotero 文献库 — 通过 zotero-mcp 插件"""
    try:
        from app.services.zotero_tools import get_zotero
        zotero = get_zotero()

        if not await zotero.connected():
            return {
                "connected": False,
                "note": "Zotero MCP 服务未连接。请确保 Zotero 已运行且 MCP 插件已启用（默认端口 23120）。",
                "count": 0,
            }

        result = await zotero.search_library(
            q=query or None,
            title=title or None,
            year_range=year_range or None,
            fulltext=fulltext or None,
            item_type=item_type or None,
            mode=mode,
            limit=limit,
            sort=sort,
            relevance_scoring=True,
        )

        if result.get("error"):
            return {"error": result["error"], "connected": result.get("connected", True), "count": 0}

        content = zotero._extract_text(result) if hasattr(zotero, '_extract_text') else str(result.get("content", result))
        
        return {
            "connected": True,
            "results": content,
            "count": result.get("total", 0),
            "query": query,
            "source": "Zotero 本地文献库",
        }
    except ImportError:
        return {"error": "ZoteroTools 服务未加载", "connected": False, "count": 0}
    except Exception as e:
        logger.error("search_zotero failed", error=str(e))
        return {"error": f"Zotero 搜索失败: {str(e)}", "connected": False, "count": 0}


async def get_zotero_content_handler(item_key: str, mode: str = "standard") -> dict:
    """获取 Zotero 文献完整内容（PDF 全文/笔记/摘要）"""
    try:
        from app.services.zotero_tools import get_zotero
        zotero = get_zotero()

        if not await zotero.connected():
            return {"connected": False, "note": "Zotero MCP 服务未连接"}

        result = await zotero.get_content(item_key=item_key, mode=mode)
        if result.get("error"):
            return {"error": result["error"]}

        content = zotero._extract_text(result) if hasattr(zotero, '_extract_text') else str(result.get("content", result))
        return {"connected": True, "content": content, "item_key": item_key, "mode": mode}
    except Exception as e:
        logger.error("get_zotero_content failed", error=str(e))
        return {"error": str(e)}


async def find_similar_zotero_handler(item_key: str, top_k: int = 5, min_score: float = 0.3) -> dict:
    """发现与指定 Zotero 文献语义相似的其他文献"""
    try:
        from app.services.zotero_tools import get_zotero
        zotero = get_zotero()

        if not await zotero.connected():
            return {"connected": False, "note": "Zotero MCP 服务未连接"}

        result = await zotero.find_similar(item_key=item_key, top_k=top_k, min_score=min_score)
        if result.get("error"):
            return {"error": result["error"]}

        content = zotero._extract_text(result) if hasattr(zotero, '_extract_text') else str(result.get("content", result))
        return {"connected": True, "similar": content, "count": len(content) if isinstance(content, list) else 0}
    except Exception as e:
        logger.error("find_similar_zotero failed", error=str(e))
        return {"error": str(e)}


async def generate_figure_handler(
    description: str, chart_type: str = "bar", data_description: str = ""
) -> dict:
    """生成学术图表代码 — Nature 标准"""
    chart_guides = {
        "bar": "柱状图：分类对比，均值+误差线",
        "line": "折线图：时间序列/趋势，lines+markers",
        "heatmap": "热力图：二维密度/相关性矩阵",
        "scatter": "散点图：双变量相关性",
        "radar": "雷达图：多维指标对比",
        "distribution": "分布图：直方图/核密度估计",
        "forest": "森林图：效应量和置信区间",
        "area": "面积图：累积趋势",
        "image_plate": "图像排版：多图组合排版",
        "network": "网络图：节点链接关系",
    }
    
    guide = chart_guides.get(chart_type, chart_type)
    
    system_msg = (
        "你是 Nature 期刊标准学术图表生成专家。\n\n"
        f"{FIGURE_RULES}\n\n"
        f"图表类型：{guide}\n"
        f"用户描述：{description}\n"
    )
    if data_description:
        system_msg += f"数据描述：{data_description}\n"
    
    system_msg += (
        "\n请输出完整的、可直接运行的 Python 代码。\n"
        "必须包含：\n"
        "1. import 语句\n"
        "2. rcParams 设置\n"
        "3. 模拟数据（基于用户描述）\n"
        "4. 图表绘制代码\n"
        "5. SVG 和 PNG 导出"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": description}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"code": "AI 服务未返回结果，请检查 AI 配置。", "chart_type": chart_type}
        
        return {"code": result, "chart_type": chart_type}
    except Exception as e:
        logger.error("generate_figure failed", error=str(e))
        return {"code": f"图表代码生成失败: {str(e)}", "chart_type": chart_type}


async def draft_response_handler(
    reviewer_comments: str, manuscript_changes: str = ""
) -> dict:
    """起草审稿意见回复 — Nature 标准"""
    system_msg = (
        "你是 Nature 期刊审稿意见回复专家。\n\n"
        f"{RESPONSE_RULES}\n\n"
    )
    if manuscript_changes:
        system_msg += f"稿件修改说明：\n{manuscript_changes}\n"
    
    system_msg += (
        "\n请输出逐条回复，每条包含：\n"
        "- 评论 ID（R1.1, R1.2, ...）\n"
        "- 严重程度（major / minor / editorial）\n"
        "- 审稿人原意摘要\n"
        "- 具体回复\n"
        "- 修改位置映射"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": reviewer_comments}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"response": "AI 服务未返回结果，请检查 AI 配置。"}
        
        return {"response": result}
    except Exception as e:
        logger.error("draft_response failed", error=str(e))
        return {"response": f"审稿回复起草失败: {str(e)}"}


async def check_data_availability_handler(
    description: str, repository: str = ""
) -> dict:
    """审核数据可用性声明 — FAIR 原则"""
    system_msg = (
        "你是数据可用性声明审核专家。\n\n"
        f"{DATA_RULES}\n\n"
        "请检查并改进以下数据可用性声明。输出：\n"
        "1. 改进后的声明（英文）\n"
        "2. 中文说明\n"
        "3. FAIR 合规性检查结果\n"
        "4. 缺失信息清单"
    )
    if repository:
        system_msg += f"\n建议存储库：{repository}"
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": description}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"review": "AI 服务未返回结果，请检查 AI 配置。"}
        
        return {"review": result}
    except Exception as e:
        logger.error("check_data_availability failed", error=str(e))
        return {"review": f"数据可用性审核失败: {str(e)}"}


async def paper_to_ppt_handler(
    paper_content: str, slide_count: int = 15, language: str = "chinese"
) -> dict:
    """论文转 PPT 大纲 — Nature 风格"""
    system_msg = (
        "你是学术论文转 PPT 专家。\n\n"
        f"{PAPER2PPT_RULES}\n\n"
        f"目标页数：{slide_count}\n"
        f"语言：{'中文' if language == 'chinese' else 'English'}\n\n"
        "请输出 PPT 大纲，每页包含：\n"
        "- 幻灯片标题\n"
        "- 核心要点（3-5条）\n"
        "- 建议配图/表\n"
        "- 演讲备注"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": paper_content[:8000]}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        
        if not result:
            return {"ppt_outline": "AI 服务未返回结果，请检查 AI 配置。", "slide_count": slide_count}
        
        return {"ppt_outline": result, "slide_count": slide_count}
    except Exception as e:
        logger.error("paper_to_ppt failed", error=str(e))
        return {"ppt_outline": f"PPT 大纲生成失败: {str(e)}", "slide_count": slide_count}


async def data_preprocess_handler(
    data_content: str, file_type: str = "csv", operations: str = "clean,deduplicate,split_columns"
) -> dict:
    """数据预处理 — TXT/CSV文件解析、清洗、分列"""
    system_msg = (
        "你是数据预处理专家。请对提供的数据执行以下预处理操作：\n\n"
        "1. 解析：识别数据格式（CSV/TXT/TSV），自动检测分隔符和编码\n"
        "2. 清洗：去除空行、冗余空白、异常字符、重复记录\n"
        "3. 分列：根据分隔符或固定宽度拆分列，推断列类型（数值/文本/日期）\n"
        "4. 格式化：统一数值格式、日期格式、文本大小写\n"
        "5. 统计：输出行数、列数、缺失值统计、数据类型摘要\n\n"
        f"文件类型：{file_type}\n"
        f"请求操作：{operations}\n\n"
        "请输出：\n"
        "- 清洗后的数据（Markdown 表格格式）\n"
        "- 操作日志（每步执行了什么）\n"
        "- 数据统计摘要\n"
        "- 发现的问题和建议"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": data_content[:8000]}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        if not result:
            return {"result": "AI 服务未返回结果，请检查 AI 配置。", "file_type": file_type, "operations": operations}
        return {"result": result, "file_type": file_type, "operations": operations}
    except Exception as e:
        logger.error("data_preprocess failed", error=str(e))
        return {"result": f"数据预处理失败: {str(e)}", "file_type": file_type, "operations": operations}


async def auto_chart_handler(
    data_content: str, chart_purpose: str = "", preference: str = ""
) -> dict:
    """自动绘图 — 根据数据自动选择图表类型并生成代码"""
    system_msg = (
        "你是学术数据可视化专家。请根据提供的数据自动选择最合适的图表类型并生成绘图代码。\n\n"
        "图表选择逻辑：\n"
        "- 分类对比 → 柱状图/条形图\n"
        "- 趋势变化 → 折线图/面积图\n"
        "- 占比分布 → 饼图/环形图\n"
        "- 相关性 → 散点图/气泡图\n"
        "- 多维对比 → 雷达图/热力图\n"
        "- 分布统计 → 直方图/箱线图/小提琴图\n"
        "- 时间序列 → 折线图+面积图\n\n"
        f"{FIGURE_RULES}\n\n"
        "请输出：\n"
        "1. 推荐的图表类型及理由\n"
        "2. 完整的 Python matplotlib 代码（可直接运行）\n"
        "3. 数据解读要点\n"
        "4. 图表优化建议"
    )
    
    if chart_purpose:
        system_msg += f"\n\n绘图目的：{chart_purpose}"
    if preference:
        system_msg += f"\n偏好：{preference}"
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": data_content[:8000]}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        if not result:
            return {"result": "AI 服务未返回结果，请检查 AI 配置。"}
        return {"result": result}
    except Exception as e:
        logger.error("auto_chart failed", error=str(e))
        return {"result": f"自动绘图失败: {str(e)}"}


async def knowledge_graph_gen_handler(
    content: str, graph_type: str = "citation", depth: int = 2
) -> dict:
    """知识图谱生成"""
    system_msg = (
        "你是知识图谱构建专家。请根据提供的学术内容生成知识图谱数据。\n\n"
        "图谱类型：\n"
        "- citation: 引用关系图谱（论文→论文引用关系）\n"
        "- concept: 概念关系图谱（概念→概念关系）\n"
        "- author: 作者合作图谱（作者→合作关系）\n"
        "- entity: 实体关系图谱（综合实体关系）\n\n"
        f"当前类型：{graph_type}\n"
        f"深度：{depth}\n\n"
        "请输出 JSON 格式的图谱数据：\n"
        "```json\n"
        "{\n"
        '  "nodes": [{"id": "...", "label": "...", "type": "...", "properties": {...}}],\n'
        '  "edges": [{"source": "...", "target": "...", "label": "...", "weight": 1.0}]\n'
        "}\n"
        "```\n\n"
        "同时输出：\n"
        "- 图谱摘要（节点数、边数、关键节点）\n"
        "- 核心发现（最重要的关系和模式）\n"
        "- 可视化建议（布局方式、颜色编码方案）"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": content[:8000]}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        if not result:
            return {"result": "AI 服务未返回结果，请检查 AI 配置。", "graph_type": graph_type}
        return {"result": result, "graph_type": graph_type}
    except Exception as e:
        logger.error("knowledge_graph_gen failed", error=str(e))
        return {"result": f"知识图谱生成失败: {str(e)}", "graph_type": graph_type}


async def document_parse_handler(
    file_content: str, file_type: str = "pdf", extract_options: str = "text,structure,references"
) -> dict:
    """文档解析 — PDF/Word/TXT内容提取"""
    system_msg = (
        "你是文档解析专家。请从提供的文档内容中提取结构化信息。\n\n"
        f"文档类型：{file_type}\n"
        f"提取选项：{extract_options}\n\n"
        "解析能力：\n"
        "- 文本提取：提取全文文本，保留段落结构\n"
        "- 结构识别：识别标题层级、章节、段落、列表\n"
        "- 参考文献提取：提取引用列表，解析作者/标题/年份/期刊/DOI\n"
        "- 图表信息：识别图表标题、图注、表格内容\n"
        "- 元数据：提取标题、作者、摘要、关键词、DOI\n\n"
        "请输出：\n"
        "1. 文档元数据（标题、作者、年份、DOI等）\n"
        "2. 结构化大纲（层级标题）\n"
        "3. 提取的文本内容（按章节组织）\n"
        "4. 参考文献列表（标准化格式）\n"
        "5. 图表索引\n"
        "6. 解析质量报告（完整性评估、缺失部分）"
    )
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": file_content[:8000]}
    ]
    
    try:
        result = await _safe_chat(messages, max_tokens=4096)
        if not result:
            return {"result": "AI 服务未返回结果，请检查 AI 配置。", "file_type": file_type}
        return {"result": result, "file_type": file_type}
    except Exception as e:
        logger.error("document_parse failed", error=str(e))
        return {"result": f"文档解析失败: {str(e)}", "file_type": file_type}


# ============================================================
# 技能注册
# ============================================================

def register_nature_skills(registry: "SkillRegistry"):
    """将所有 Nature 技能注册到 Agent 技能表"""
    
    # ====== 阅读类 ======
    registry.register(SkillDefinition(
        name="paper_qa",
        description="基于PDF全文回答学术问题。输入查询和PDF标识，返回带引用的回答。严格基于原文，不编造。",
        category=SkillCategory.READING,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "关于论文的具体问题"},
                "pdf_id": {"type": "string", "description": "PDF文件标识符（文件路径或ID）"}
            },
            "required": ["query", "pdf_id"]
        },
        handler=paper_qa_handler,
        examples=["这篇论文的研究方法是什么？", "作者在实验中用了哪些数据集？", "主要结论是什么？"],
    ))
    
    registry.register(SkillDefinition(
        name="paper_summarize",
        description="生成学术论文摘要。支持短/中/长三种长度，支持中英文。遵循 Context→Gap→Approach→Result→Implication 结构。",
        category=SkillCategory.READING,
        parameters={
            "type": "object",
            "properties": {
                "pdf_id": {"type": "string", "description": "PDF文件标识符"},
                "length": {"type": "string", "enum": ["short", "medium", "long"], "description": "摘要长度: short=200字, medium=500字, long=1000字"},
                "language": {"type": "string", "enum": ["chinese", "english"], "description": "输出语言"}
            },
            "required": ["pdf_id"]
        },
        handler=paper_summarize_handler,
    ))
    
    # ====== 写作润色 ======
    registry.register(SkillDefinition(
        name="polish_text",
        description="学术文本润色。遵循Nature期刊标准：句子≤30词、声明强度匹配证据、英式英语、术语准确。支持中译英润色。",
        category=SkillCategory.WRITING,
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "需要润色的学术文本"},
                "style": {"type": "string", "enum": ["nature", "academic", "concise"], "description": "润色风格: nature=Nature期刊, academic=通用学术, concise=极简"},
                "target_lang": {"type": "string", "enum": ["english", "chinese"], "description": "目标语言"}
            },
            "required": ["text"]
        },
        handler=polish_text_handler,
        examples=["润色这段文字，按Nature风格", "将这段中文润色为英文学术语言"],
    ))
    
    # ====== 翻译 ======
    registry.register(SkillDefinition(
        name="translate_text",
        description="学术翻译。保持学术术语准确，句式符合目标语言学术写作惯例。支持中英互译。",
        category=SkillCategory.TRANSLATION,
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "需要翻译的文本"},
                "source_lang": {"type": "string", "description": "源语言（auto=自动检测）"},
                "target_lang": {"type": "string", "description": "目标语言: english/chinese/japanese/german/french"},
                "domain": {"type": "string", "description": "学术领域，如 computer science, biology, medicine"}
            },
            "required": ["text", "target_lang"]
        },
        handler=translate_text_handler,
    ))
    
    # ====== 写作起草 ======
    registry.register(SkillDefinition(
        name="draft_section",
        description="起草论文章节（abstract/introduction/method/results/discussion/conclusion）。遵循Nature写作指南：Context→Gap→Approach→Result→Implication 等结构，不编造数据。",
        category=SkillCategory.WRITING,
        parameters={
            "type": "object",
            "properties": {
                "section_type": {"type": "string", "enum": ["abstract", "introduction", "method", "results", "discussion", "conclusion"], "description": "章节类型"},
                "topic": {"type": "string", "description": "论文章节主题描述"},
                "key_points": {"type": "string", "description": "要点，用逗号或换行分隔"},
                "references": {"type": "string", "description": "参考文献列表"}
            },
            "required": ["section_type", "topic"]
        },
        handler=draft_section_handler,
    ))
    
    registry.register(SkillDefinition(
        name="generate_outline",
        description="生成论文大纲。包括标题建议（3个）、各章节标题和要点、预计字数、关键图表建议、参考文献范围。",
        category=SkillCategory.WRITING,
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "论文主题"},
                "paper_type": {"type": "string", "enum": ["research", "review", "letter", "case_study"], "description": "论文类型"},
                "field": {"type": "string", "description": "学术领域，如 machine learning, materials science"}
            },
            "required": ["topic"]
        },
        handler=generate_outline_handler,
    ))
    
    # ====== 引用 ======
    registry.register(SkillDefinition(
        name="format_citation",
        description="格式化参考文献。支持 Nature/IEEE/APA/Vancouver 等风格，输出文本/RIS/BibTeX/ENW 格式。",
        category=SkillCategory.CITATION,
        parameters={
            "type": "object",
            "properties": {
                "references": {"type": "string", "description": "待格式化的参考文献列表"},
                "style": {"type": "string", "enum": ["nature", "ieee", "apa", "vancouver"], "description": "引用风格"},
                "output_format": {"type": "string", "enum": ["text", "ris", "bibtex", "enw"], "description": "输出格式"}
            },
            "required": ["references"]
        },
        handler=format_citation_handler,
    ))
    
    # ====== 检索 ======
    registry.register(SkillDefinition(
        name="search_literature",
        description="多源文献检索。搜索 CORE/OpenAlex/Semantic Scholar/Crossref/Europe PMC/arXiv，返回去重排序的文献列表。",
        category=SkillCategory.SEARCH,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词"},
                "sources": {"type": "string", "description": "数据源（逗号分隔）: core,openalex,semanticscholar,crossref,europepmc,arxiv"},
                "limit": {"type": "integer", "description": "每个数据源返回数量，默认10"}
            },
            "required": ["query"]
        },
        handler=search_literature_handler,
    ))

    # ====== Zotero 本地文献检索 ======
    registry.register(SkillDefinition(
        name="search_zotero",
        description="搜索本地 Zotero 文献库。检索已收藏的论文标题/作者/年份/标签/全文，支持布尔运算和相关性评分。",
        category=SkillCategory.SEARCH,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "通用搜索关键词（搜索标题/作者/摘要/标签）"},
                "title": {"type": "string", "description": "按标题搜索（支持 contains/exact/startsWith/endsWith/regex）"},
                "year_range": {"type": "string", "description": "年份范围，如 2020-2024"},
                "fulltext": {"type": "string", "description": "在 PDF 全文/笔记中搜索"},
                "item_type": {"type": "string", "description": "文献类型：journalArticle/book/conferencePaper/thesis等"},
                "mode": {"type": "string", "enum": ["minimal", "preview", "standard", "complete"], "description": "信息详细程度"},
                "limit": {"type": "integer", "description": "返回数量，默认 20"},
                "sort": {"type": "string", "enum": ["relevance", "date", "title", "year"], "description": "排序方式"},
            },
            "required": []
        },
        handler=search_zotero_handler,
        examples=["我的 Zotero 库里有关于 transformer 的论文吗？", "找一下 2023-2024 年收藏的深度学习文章", "在我的文献库里搜索包含 'attention mechanism' 的 PDF 全文"],
    ))

    registry.register(SkillDefinition(
        name="get_zotero_content",
        description="获取 Zotero 文献的完整内容（PDF 全文提取/笔记/摘要/网页快照）。用于文献精读和分析。",
        category=SkillCategory.READING,
        parameters={
            "type": "object",
            "properties": {
                "item_key": {"type": "string", "description": "Zotero 条目 Key"},
                "mode": {"type": "string", "enum": ["minimal", "preview", "standard", "complete"], "description": "内容详细程度：minimal=500字符, preview=1.5K, standard=3K, complete=无限制"},
            },
            "required": ["item_key"]
        },
        handler=get_zotero_content_handler,
        examples=["读取 Zotero 里这篇论文的全文内容", "获取这篇文献的摘要和笔记"],
    ))

    registry.register(SkillDefinition(
        name="find_similar_zotero",
        description="基于指定文献，在 Zotero 库中发现语义相似的其他论文。利用 AI 向量嵌入进行概念级匹配。",
        category=SkillCategory.SEARCH,
        parameters={
            "type": "object",
            "properties": {
                "item_key": {"type": "string", "description": "Zotero 条目 Key（基准文献）"},
                "top_k": {"type": "integer", "description": "返回相似文献数量，默认 5"},
                "min_score": {"type": "number", "description": "最低相似度阈值 0-1，默认 0.3"},
            },
            "required": ["item_key"]
        },
        handler=find_similar_zotero_handler,
        examples=["找出和这篇论文相似的其他文献", "我的 Zotero 库里有没有类似这篇文章的论文？"],
    ))
    
    # ====== 图表 ======
    registry.register(SkillDefinition(
        name="generate_figure",
        description="生成Nature标准学术图表的matplotlib代码。支持10种图表类型，遵循Nature视觉规范（Arial字体、SVG输出、语义配色）。",
        category=SkillCategory.FIGURE,
        parameters={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "图表描述，包含要展示的数据和结论"},
                "chart_type": {"type": "string", "enum": ["bar", "line", "heatmap", "scatter", "radar", "distribution", "forest", "area", "image_plate", "network"], "description": "图表类型"},
                "data_description": {"type": "string", "description": "数据结构和样例描述"}
            },
            "required": ["description"]
        },
        handler=generate_figure_handler,
    ))
    
    # ====== 审稿回复 ======
    registry.register(SkillDefinition(
        name="draft_response",
        description="起草审稿意见逐条回复。每条评论分配ID、分类（major/minor/editorial）、映射到具体稿件修改。适用于大修/小修回复。",
        category=SkillCategory.RESPONSE,
        parameters={
            "type": "object",
            "properties": {
                "reviewer_comments": {"type": "string", "description": "审稿意见全文"},
                "manuscript_changes": {"type": "string", "description": "已做的稿件修改说明"}
            },
            "required": ["reviewer_comments"]
        },
        handler=draft_response_handler,
    ))
    
    # ====== 数据可用性 ======
    registry.register(SkillDefinition(
        name="check_data_availability",
        description="审核数据可用性声明合规性。检查持久访问路径、存储库策略、FAIR原则、限制数据说明。输出改进版声明和缺失信息清单。",
        category=SkillCategory.DATA,
        parameters={
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "数据可用性声明文本"},
                "repository": {"type": "string", "description": "建议的数据存储库"}
            },
            "required": ["description"]
        },
        handler=check_data_availability_handler,
    ))
    
    # ====== 论文转PPT ======
    registry.register(SkillDefinition(
        name="paper_to_ppt",
        description="将论文转为PPT大纲。以科学论证为主线（非章节顺序），适合 journal club / 组会汇报。",
        category=SkillCategory.PAPER2PPT,
        parameters={
            "type": "object",
            "properties": {
                "paper_content": {"type": "string", "description": "论文内容文本"},
                "slide_count": {"type": "integer", "description": "目标 PPT 页数，默认 15"},
                "language": {"type": "string", "enum": ["chinese", "english"], "description": "PPT语言"}
            },
            "required": ["paper_content"]
        },
        handler=paper_to_ppt_handler,
    ))
    
    # ====== 数据预处理 ======
    registry.register(SkillDefinition(
        name="data_preprocess",
        description="数据预处理：解析TXT/CSV/TSV文件，执行清洗冗余内容、去重、分列整理、格式统一等操作。输出清洗后数据和统计摘要。",
        category=SkillCategory.DATA_PROCESS,
        parameters={
            "type": "object",
            "properties": {
                "data_content": {"type": "string", "description": "原始数据内容（文本形式）"},
                "file_type": {"type": "string", "enum": ["csv", "tsv", "txt", "json"], "description": "文件类型，默认csv"},
                "operations": {"type": "string", "description": "要执行的操作（逗号分隔）: clean,deduplicate,split_columns,format,statistics"}
            },
            "required": ["data_content"]
        },
        handler=data_preprocess_handler,
        examples=["请清洗这份数据，去除空行和重复记录", "将这个CSV文件分列整理"],
    ))
    
    # ====== 自动绘图 ======
    registry.register(SkillDefinition(
        name="auto_chart",
        description="自动绘图：根据数据内容自动选择最合适的图表类型（柱状图/折线图/散点图/热力图等），生成Nature标准matplotlib代码。",
        category=SkillCategory.AUTO_CHART,
        parameters={
            "type": "object",
            "properties": {
                "data_content": {"type": "string", "description": "数据内容（文本或表格形式）"},
                "chart_purpose": {"type": "string", "description": "绘图目的或要展示的结论"},
                "preference": {"type": "string", "description": "图表偏好，如 bar,line,scatter,heatmap"}
            },
            "required": ["data_content"]
        },
        handler=auto_chart_handler,
        examples=["根据这组数据推荐合适的图表", "为这些实验结果生成对比柱状图"],
    ))
    
    # ====== 知识图谱生成 ======
    registry.register(SkillDefinition(
        name="knowledge_graph_gen",
        description="知识图谱生成：从学术内容中提取实体和关系，构建引用图谱/概念图谱/作者合作图谱。输出节点-边JSON数据。",
        category=SkillCategory.KNOWLEDGE_GRAPH,
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "学术内容文本（论文/摘要/引用列表）"},
                "graph_type": {"type": "string", "enum": ["citation", "concept", "author", "entity"], "description": "图谱类型: citation=引用关系, concept=概念关系, author=作者合作, entity=实体关系"},
                "depth": {"type": "integer", "description": "图谱深度，默认2"}
            },
            "required": ["content"]
        },
        handler=knowledge_graph_gen_handler,
        examples=["为这篇论文生成引用关系图谱", "提取这些论文的概念关系网络"],
    ))
    
    # ====== 文档解析 ======
    registry.register(SkillDefinition(
        name="document_parse",
        description="文档解析：从PDF/Word/TXT中提取结构化内容，包括元数据、章节结构、参考文献、图表信息。输出结构化JSON。",
        category=SkillCategory.DOCUMENT_PARSE,
        parameters={
            "type": "object",
            "properties": {
                "file_content": {"type": "string", "description": "文档文本内容"},
                "file_type": {"type": "string", "enum": ["pdf", "word", "txt"], "description": "文档类型，默认pdf"},
                "extract_options": {"type": "string", "description": "提取选项（逗号分隔）: text,structure,references,figures,metadata"}
            },
            "required": ["file_content"]
        },
        handler=document_parse_handler,
        examples=["解析这篇PDF论文的结构和参考文献", "提取这个Word文档的章节大纲"],
    ))
