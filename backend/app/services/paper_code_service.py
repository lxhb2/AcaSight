import re
from typing import Optional

DIRECTION_ABBREVS = {
    "机器学习": "ML", "深度学习": "DL", "自然语言处理": "NLP",
    "计算机视觉": "CV", "知识图谱": "KG", "推荐系统": "RS",
    "数据挖掘": "DM", "信息检索": "IR", "强化学习": "RL",
    "联邦学习": "FL", "图神经网络": "GNN", "大语言模型": "LLM",
    "多模态": "MM", "语音识别": "SR", "机器人": "RB",
    "生物信息": "BI", "医学影像": "MI", "量子计算": "QC",
    "网络安全": "NS", "物联网": "IoT", "边缘计算": "EC",
    "云计算": "CC", "数据库": "DB", "分布式系统": "DS",
    "软件工程": "SE", "人机交互": "HCI", "可视化": "VS",
    "优化算法": "OA", "信号处理": "SP", "控制系统": "CS",
}


def _extract_author_initials(authors: list[str] | None) -> str:
    if not authors:
        return "XX"
    first_author = authors[0]
    parts = first_author.strip().split()
    if not parts:
        return "XX"
    last_name = parts[-1]
    if re.match(r'[\u4e00-\u9fff]', last_name):
        pinyin_map = {"张": "ZH", "李": "LI", "王": "WA", "刘": "LIU", "陈": "CH",
                      "杨": "YA", "赵": "ZH", "黄": "HU", "周": "ZH", "吴": "WU",
                      "徐": "XU", "孙": "SU", "胡": "HU", "朱": "ZH", "高": "GA",
                      "林": "LI", "何": "HE", "郭": "GU", "马": "MA", "罗": "LUO"}
        first_char = last_name[0]
        return pinyin_map.get(first_char, last_name[:2].upper())
    return last_name[:2].upper()


def _guess_direction(title: str, abstract: str = "", keywords: list = None) -> str:
    text = f"{title} {abstract}".lower()
    if keywords:
        text += " " + " ".join(keywords).lower()
    best_match = "GEN"
    best_len = 0
    for direction, abbrev in DIRECTION_ABBREVS.items():
        if direction in text and len(direction) > best_len:
            best_match = abbrev
            best_len = len(direction)
    for direction, abbrev in DIRECTION_ABBREVS.items():
        if abbrev.lower() in text:
            best_match = abbrev
            break
    return best_match


async def generate_paper_code(
    title: str,
    authors: list[str] | None,
    year: int | None,
    abstract: str = "",
    keywords: list = None,
    db_session=None,
) -> str:
    direction = _guess_direction(title, abstract, keywords)
    initials = _extract_author_initials(authors)
    year_str = str(year) if year else "0000"
    prefix = f"{direction}-{initials}-{year_str}"

    if db_session is not None:
        from sqlalchemy import select, func as sa_func
        from app.models.paper import Paper
        result = await db_session.execute(
            select(sa_func.count(Paper.id)).where(Paper.paper_code.like(f"{prefix}%"))
        )
        count = result.scalar() or 0
        seq = count + 1
    else:
        seq = 1

    return f"{prefix}-{seq:02d}"
