"""
文献结构化分解服务 (11字段 RAG拆分)
Phase 1 — 核心基础服务
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

# ─── 数据结构 ───

STRUCTURED_FIELDS = [
    "abstract",          # 摘要
    "background",        # 研究背景
    "purpose",           # 研究目的与意义
    "current_status",    # 研究现状
    "research_question", # 研究问题
    "basic_theory",      # 基本理论
    "method",            # 研究方法
    "results",           # 结果与评价
    "innovation",        # 创新点
    "limitations",       # 局限与建议
    "conclusion",        # 结论
]

@dataclass
class StructuredPaper:
    id: str
    title: str
    authors: str = ""
    year: int = 0
    journal: str = ""
    doi: str = ""
    source: str = "local"  # local | database | api
    
    # 11 结构化字段
    abstract: str = ""
    background: str = ""
    purpose: str = ""
    current_status: str = ""
    research_question: str = ""
    basic_theory: str = ""
    method: str = ""
    results: str = ""
    innovation: str = ""
    limitations: str = ""
    conclusion: str = ""
    
    # 元数据
    full_text_path: str = ""
    knowledge_graph_id: str = ""
    structured_at: str = ""
    created_at: str = ""
    updated_at: str = ""


# ─── 数据库管理 ───

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "literature", "paper.db")

def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化文学结构化存储数据库"""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS paper_structured (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT DEFAULT '',
            year INTEGER DEFAULT 0,
            journal TEXT DEFAULT '',
            doi TEXT DEFAULT '',
            source TEXT DEFAULT 'local',
            
            abstract TEXT DEFAULT '',
            background TEXT DEFAULT '',
            purpose TEXT DEFAULT '',
            current_status TEXT DEFAULT '',
            research_question TEXT DEFAULT '',
            basic_theory TEXT DEFAULT '',
            method TEXT DEFAULT '',
            results TEXT DEFAULT '',
            innovation TEXT DEFAULT '',
            limitations TEXT DEFAULT '',
            conclusion TEXT DEFAULT '',
            
            full_text_path TEXT DEFAULT '',
            knowledge_graph_id TEXT DEFAULT '',
            structured_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_paper_source ON paper_structured(source);
        CREATE INDEX IF NOT EXISTS idx_paper_year ON paper_structured(year);
        CREATE INDEX IF NOT EXISTS idx_paper_doi ON paper_structured(doi);
        CREATE INDEX IF NOT EXISTS idx_paper_kg ON paper_structured(knowledge_graph_id);
        
        -- 临时缓存表（网络检索未确认文献，30min过期）
        CREATE TABLE IF NOT EXISTS paper_temp_cache (
            id TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_temp_expires ON paper_temp_cache(expires_at);
    """)
    conn.commit()
    conn.close()
    print("[literature] Database initialized")


# ─── CRUD 操作 ───

def save_structured_paper(paper: StructuredPaper) -> str:
    """保存/更新结构化文献"""
    conn = get_db()
    now = datetime.now().isoformat()
    paper.structured_at = now
    paper.updated_at = now
    
    data = asdict(paper)
    # 处理空字符串 → None
    for k, v in data.items():
        if v == "" and k in STRUCTURED_FIELDS:
            data[k] = None
    
    keys = list(data.keys())
    placeholders = ", ".join(["?" for _ in keys])
    cols = ", ".join(keys)
    
    conn.execute(f"""
        INSERT OR REPLACE INTO paper_structured ({cols})
        VALUES ({placeholders})
    """, [data[k] for k in keys])
    
    conn.commit()
    conn.close()
    return paper.id


def get_structured_paper(paper_id: str) -> Optional[Dict]:
    """获取单篇结构化文献"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM paper_structured WHERE id = ?", (paper_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def search_structured_papers(
    query: str = "",
    source: str = "",
    fields: List[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict]:
    """搜索结构化文献（模糊匹配）"""
    conn = get_db()
    conditions = []
    params = []
    
    if query:
        like = f"%{query}%"
        conditions.append(
            "(title LIKE ? OR authors LIKE ? OR journal LIKE ? OR abstract LIKE ?)"
        )
        params.extend([like, like, like, like])
    
    if source:
        conditions.append("source = ?")
        params.append(source)
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    rows = conn.execute(
        f"SELECT * FROM paper_structured WHERE {where} ORDER BY year DESC LIMIT ? OFFSET ?",
        params + [limit, offset]
    ).fetchall()
    
    total = conn.execute(
        f"SELECT COUNT(*) FROM paper_structured WHERE {where}", params
    ).fetchone()[0]
    
    conn.close()
    return {
        "results": [dict(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def query_paper_field(paper_id: str, field: str) -> Optional[str]:
    """查询文献指定字段（用于写作引用）"""
    if field not in STRUCTURED_FIELDS:
        return None
    conn = get_db()
    row = conn.execute(
        f"SELECT {field} FROM paper_structured WHERE id = ?", (paper_id,)
    ).fetchone()
    conn.close()
    return row[0] if row and row[0] else None


def query_by_dimension(dimension: str, keywords: str = "", limit: int = 10) -> List[Dict]:
    """
    按维度查询文献 → 用于写作时"为该段落找文献支撑"
    dimension: STRUCTURED_FIELDS 之一
    """
    conn = get_db()
    cols = ["id", "title", "authors", "year", "journal", "doi", dimension]
    where = f"{dimension} IS NOT NULL AND {dimension} != ''"
    params = []
    
    if keywords:
        like = f"%{keywords}%"
        where += f" AND {dimension} LIKE ?"
        params.append(like)
    
    rows = conn.execute(
        f"SELECT {', '.join(cols)} FROM paper_structured WHERE {where} ORDER BY year DESC LIMIT ?",
        params + [limit]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_structured_paper(paper_id: str) -> bool:
    """删除结构化文献"""
    conn = get_db()
    conn.execute("DELETE FROM paper_structured WHERE id = ?", (paper_id,))
    conn.commit()
    deleted = conn.total_changes > 0
    conn.close()
    return deleted


def list_sources() -> Dict[str, int]:
    """各来源文献统计"""
    conn = get_db()
    rows = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM paper_structured GROUP BY source"
    ).fetchall()
    conn.close()
    return {r["source"]: r["cnt"] for r in rows}


def get_paper_statistics() -> Dict:
    """文献库统计"""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM paper_structured").fetchone()[0]
    by_year = conn.execute(
        "SELECT year, COUNT(*) as cnt FROM paper_structured WHERE year > 0 GROUP BY year ORDER BY year"
    ).fetchall()
    structured_count = conn.execute(
        "SELECT COUNT(*) FROM paper_structured WHERE abstract != '' AND method != '' AND conclusion != ''"
    ).fetchone()[0]
    conn.close()
    return {
        "total": total,
        "fully_structured": structured_count,
        "by_year": [dict(r) for r in by_year],
        "sources": list_sources(),
    }


# ─── RAG 分解引擎 ───

async def decompose_paper(
    paper_id: str,
    title: str,
    full_text: str,
    authors: str = "",
    year: int = 0,
    journal: str = "",
    doi: str = "",
    source: str = "local",
) -> StructuredPaper:
    """使用 AI 将论文正文拆分为 11 个结构化字段"""
    
    prompt = f"""你是一位专业的学术文献分析师。请仔细阅读以下论文全文，将其拆分为标准化结构。

**论文标题**：{title}
**作者**：{authors}
**年份**：{year}

**论文全文**（可能较长，请按需分段处理）：
{full_text[:15000]}

请按以下 11 个维度提取信息，以 JSON 格式返回。如果某个维度在原文中没有明确内容，该字段留空字符串 ""。
对于每个维度，请从原文中提取**关键句子和段落**（而非概括），保持原文细节。

返回 JSON 格式：
{{
  "abstract": "摘要内容...",
  "background": "研究背景（为什么做这个研究）...",
  "purpose": "研究目的与意义...",
  "current_status": "国内外研究现状...",
  "research_question": "核心研究问题...",
  "basic_theory": "使用的基本理论/框架...",
  "method": "研究方法（实验设计/数据分析方法）...",
  "results": "主要结果与评价...",
  "innovation": "创新点...",
  "limitations": "研究局限与未来建议...",
  "conclusion": "结论..."
}}

要求：
1. 每个字段尽可能详细，直接引用原文关键内容
2. 不要编造原文没有的内容
3. 保持学术语言的客观性和准确性
4. 仅返回 JSON，不要额外解释"""

    from app.services.ai_service import ai_service
    
    result = ""
    async for chunk in ai_service.chat([
        {"role": "system", "content": "你是一位精准的学术文献分析专家，擅长从论文中提取结构化信息。请严格按 JSON 格式回复。"},
        {"role": "user", "content": prompt}
    ], temperature=0.2):
        result += chunk
    
    # 提取 JSON
    json_str = result
    for marker in ["```json", "```"]:
        if marker in json_str:
            json_str = json_str.split(marker)[1].split("```")[0]
            break
    
    try:
        data = json.loads(json_str.strip())
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON 对象
        import re
        match = re.search(r'\{[^{}]*"abstract"[^{}]*\}', result, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = {f: "" for f in STRUCTURED_FIELDS}
    
    # 构建 StructuredPaper
    paper = StructuredPaper(
        id=paper_id,
        title=title,
        authors=authors,
        year=year,
        journal=journal,
        doi=doi,
        source=source,
        abstract=data.get("abstract", ""),
        background=data.get("background", ""),
        purpose=data.get("purpose", ""),
        current_status=data.get("current_status", ""),
        research_question=data.get("research_question", ""),
        basic_theory=data.get("basic_theory", ""),
        method=data.get("method", ""),
        results=data.get("results", ""),
        innovation=data.get("innovation", ""),
        limitations=data.get("limitations", ""),
        conclusion=data.get("conclusion", ""),
    )
    
    save_structured_paper(paper)
    return paper


# ─── 临时缓存管理 ───

import time

TEMP_CACHE_TTL = 30 * 60  # 30 分钟

def cache_search_results(query: str, results: List[Dict]) -> str:
    """缓存网络检索结果"""
    cache_id = f"search_{hash(query)}_{int(time.time())}"
    conn = get_db()
    expires = (datetime.now().timestamp() + TEMP_CACHE_TTL)
    conn.execute(
        "INSERT OR REPLACE INTO paper_temp_cache (id, data_json, cached_at, expires_at) VALUES (?, ?, ?, ?)",
        (cache_id, json.dumps(results, ensure_ascii=False), datetime.now().isoformat(), datetime.fromtimestamp(expires).isoformat())
    )
    conn.commit()
    conn.close()
    return cache_id


def get_cached_results(cache_id: str) -> Optional[List[Dict]]:
    """获取缓存结果"""
    conn = get_db()
    row = conn.execute(
        "SELECT data_json FROM paper_temp_cache WHERE id = ? AND expires_at > ?",
        (cache_id, datetime.now().isoformat())
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None


def cleanup_temp_cache():
    """清理过期缓存"""
    conn = get_db()
    conn.execute(
        "DELETE FROM paper_temp_cache WHERE expires_at < ?",
        (datetime.now().isoformat(),)
    )
    conn.commit()
    conn.close()


# ─── 导出 ───

def export_paper_citation(paper_id: str, style: str = "gbt7714") -> Optional[str]:
    """按格式导出文献引用"""
    paper = get_structured_paper(paper_id)
    if not paper:
        return None
    
    if style == "gbt7714":
        # GB/T 7714-2015 格式
        authors = paper.get("authors", "").replace(",", "，")
        title = paper.get("title", "")
        journal = paper.get("journal", "")
        year = paper.get("year", "")
        doi = paper.get("doi", "")
        
        if journal:
            return f"{authors}. {title}[J]. {journal}, {year}. DOI: {doi}" if doi else f"{authors}. {title}[J]. {journal}, {year}."
        else:
            return f"{authors}. {title}[EB/OL]. ({year}). DOI: {doi}" if doi else f"{authors}. {title}[EB/OL]. ({year})."
    
    return None
