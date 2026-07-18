"""
论文查重服务

基于 n-gram Jaccard 相似度的纯 Python 查重实现，
无需外部 ML 依赖。
"""

import re
import json
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class MatchResult:
    """单条匹配结果"""
    source_title: str = ""
    source_authors: str = ""
    similarity: float = 0.0
    matched_text: str = ""
    position: int = 0  # 匹配文本在原文中的起始位置


@dataclass
class CheckResult:
    """查重结果"""
    similarity_score: float = 0.0
    matches: List[MatchResult] = field(default_factory=list)
    checked_at: str = ""
    text_length: int = 0
    reference_count: int = 0


class PlagiarismService:
    """论文查重服务

    使用字符级 n-gram 和 Jaccard 相似度进行文本比对。
    """

    def __init__(self):
        self._history_db = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'plagiarism', 'history.db'
        )

    # ── 核心算法 ──

    def extract_ngrams(self, text: str, n: int = 3) -> Set[str]:
        """生成字符级 n-gram 集合

        Args:
            text: 输入文本
            n: n-gram 的 n 值，默认 3（三字符组）

        Returns:
            n-gram 字符串集合
        """
        # 预处理：转小写、去除多余空白
        text = re.sub(r'\s+', ' ', text.lower().strip())
        if len(text) < n:
            return {text} if text else set()
        return {text[i:i + n] for i in range(len(text) - n + 1)}

    def jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """计算 Jaccard 相似度

        J(A, B) = |A ∩ B| / |A ∪ B|

        Args:
            set1: 第一个集合
            set2: 第二个集合

        Returns:
            相似度值 [0, 1]
        """
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def check_similarity(self, text: str, reference_texts: List[Dict]) -> CheckResult:
        """检查文本与参考文本集的相似度

        Args:
            text: 待检查文本
            reference_texts: 参考文本列表，每项包含 title, authors, content 等字段

        Returns:
            CheckResult 包含总体相似度和各条匹配详情
        """
        if not text or not text.strip():
            return CheckResult(text_length=0)

        text_ngrams = self.extract_ngrams(text)
        if not text_ngrams:
            return CheckResult(text_length=len(text))

        matches: List[MatchResult] = []
        max_similarity = 0.0

        for ref in reference_texts:
            ref_content = ref.get('content', '') or ref.get('abstract', '') or ''
            if not ref_content.strip():
                continue

            ref_ngrams = self.extract_ngrams(ref_content)
            similarity = self.jaccard_similarity(text_ngrams, ref_ngrams)

            if similarity > 0.05:  # 过滤极低相似度
                # 查找匹配片段
                matched_text, position = self.find_matching_passages(text, ref_content)
                matches.append(MatchResult(
                    source_title=ref.get('title', '未知'),
                    source_authors=ref.get('authors', '未知'),
                    similarity=round(similarity, 4),
                    matched_text=matched_text,
                    position=position,
                ))

            max_similarity = max(max_similarity, similarity)

        # 按相似度降序排列
        matches.sort(key=lambda m: m.similarity, reverse=True)

        # 总体相似度取最高值（也可取加权平均）
        overall_score = round(max_similarity, 4)

        result = CheckResult(
            similarity_score=overall_score,
            matches=matches,
            checked_at=datetime.now().isoformat(),
            text_length=len(text),
            reference_count=len(reference_texts),
        )

        # 保存到历史记录
        self._save_history(result)

        return result

    def find_matching_passages(
        self,
        text: str,
        reference: str,
        window_size: int = 100,
    ) -> Tuple[str, int]:
        """查找文本中的匹配片段

        使用滑动窗口在原文中寻找与参考文本最相似的片段。

        Args:
            text: 待检查文本
            reference: 参考文本
            window_size: 滑动窗口大小（字符数）

        Returns:
            (匹配文本, 匹配起始位置)
        """
        if not text or not reference:
            return "", 0

        # 预处理
        text_clean = re.sub(r'\s+', ' ', text.lower())
        ref_clean = re.sub(r'\s+', ' ', reference.lower())

        ref_ngrams = self.extract_ngrams(ref_clean)
        if not ref_ngrams:
            return "", 0

        best_similarity = 0.0
        best_position = 0
        best_text = ""

        # 滑动窗口
        step = max(window_size // 4, 20)
        for pos in range(0, len(text_clean), step):
            window = text_clean[pos:pos + window_size]
            if len(window) < 10:
                continue
            window_ngrams = self.extract_ngrams(window)
            sim = self.jaccard_similarity(window_ngrams, ref_ngrams)
            if sim > best_similarity:
                best_similarity = sim
                best_position = pos
                # 返回原文中对应位置的文字
                best_text = text[pos:pos + window_size]

        return best_text, best_position

    # ── 历史记录管理 ──

    def _get_history_db(self) -> sqlite3.Connection:
        """获取历史记录数据库连接"""
        os.makedirs(os.path.dirname(self._history_db), exist_ok=True)
        conn = sqlite3.connect(self._history_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _save_history(self, result: CheckResult) -> None:
        """保存查重结果到历史记录"""
        try:
            conn = self._get_history_db()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS check_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    similarity_score REAL NOT NULL,
                    text_length INTEGER DEFAULT 0,
                    reference_count INTEGER DEFAULT 0,
                    match_count INTEGER DEFAULT 0,
                    matches_json TEXT DEFAULT '[]',
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                """INSERT INTO check_history
                   (similarity_score, text_length, reference_count, match_count, matches_json, checked_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    result.similarity_score,
                    result.text_length,
                    result.reference_count,
                    len(result.matches),
                    json.dumps([asdict(m) for m in result.matches], ensure_ascii=False),
                    result.checked_at,
                )
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # 历史记录保存失败不应影响主流程

    def get_history(self, limit: int = 20) -> List[Dict]:
        """获取查重历史记录"""
        try:
            conn = self._get_history_db()
            rows = conn.execute(
                """SELECT id, similarity_score, text_length, reference_count,
                          match_count, checked_at
                   FROM check_history ORDER BY id DESC LIMIT ?""",
                (limit,)
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    # ── 文本提取 ──

    def extract_text_from_file(self, content: bytes, filename: str) -> str:
        """从文件中提取文本

        支持 .txt / .md / .docx 格式。
        """
        lower_name = filename.lower()

        if lower_name.endswith(('.txt', '.md')):
            return content.decode('utf-8', errors='replace')

        if lower_name.endswith('.docx'):
            try:
                import zipfile
                import xml.etree.ElementTree as ET
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    with zf.open('word/document.xml') as doc:
                        tree = ET.parse(doc)
                        root = tree.getroot()
                        # 提取所有文本节点
                        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                        texts = []
                        for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                            if p.text:
                                texts.append(p.text)
                        return '\n'.join(texts)
            except Exception as e:
                return f"[docx 解析失败: {str(e)}]"

        # 默认当作文本处理
        return content.decode('utf-8', errors='replace')


# 需要导入 io（用于 docx 解析）
import io

# 全局单例
plagiarism_service = PlagiarismService()
