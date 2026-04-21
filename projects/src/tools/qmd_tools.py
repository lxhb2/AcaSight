"""
QMD - Quick Markdown Search (Python 实现)
兼容 Windows 的本地 Markdown 搜索引擎

提供 BM25 全文搜索和文档检索功能，专为 AI Agent 工具调用优化。
"""
import os
import re
import json
import math
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter


class QMDIndex:
    """BM25 全文搜索引擎（Python 原生实现）"""

    def __init__(self, workspace_dir: str = None):
        if workspace_dir is None:
            workspace_dir = os.getenv("COZE_WORKSPACE_PATH", r"D:\四季如歌\新建文件夹\脉冲学习")
        self.workspace = os.path.abspath(workspace_dir)
        self.index_name = "qmd"
        self.collections: Dict[str, str] = {}  # name -> path
        self._load_config()

    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        cache_dir = os.path.join(self.workspace, ".qmd")
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "config.json")

    def _load_config(self):
        """加载配置"""
        config_path = self._get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.collections = cfg.get("collections", {})
                self.index_name = cfg.get("index_name", "qmd")
            except Exception:
                pass

    def _save_config(self):
        """保存配置"""
        config_path = self._get_config_path()
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({
                "collections": self.collections,
                "index_name": self.index_name,
            }, f, ensure_ascii=False, indent=2)

    def add_collection(self, name: str, path: str, description: str = ""):
        """添加一个文档集合"""
        abs_path = os.path.abspath(path)
        if not os.path.isdir(abs_path):
            return f"错误: 路径不存在: {abs_path}"
        self.collections[name] = {
            "path": abs_path,
            "description": description,
        }
        self._save_config()
        return f"已添加集合 '{name}': {abs_path}"

    def remove_collection(self, name: str):
        """移除一个文档集合"""
        if name in self.collections:
            del self.collections[name]
            self._save_config()
            return f"已移除集合 '{name}'"
        return f"集合 '{name}' 不存在"

    def list_collections(self) -> str:
        """列出所有文档集合"""
        if not self.collections:
            return "还没有创建任何文档集合。"
        result = "# 文档集合\n\n"
        for name, info in self.collections.items():
            path = info["path"] if isinstance(info, dict) else info
            desc = info.get("description", "") if isinstance(info, dict) else ""
            result += f"- **{name}**: `{path}`\n"
            if desc:
                result += f"  - {desc}\n"
        return result

    def _parse_markdown(self, content: str) -> List[str]:
        """将 Markdown 内容分词"""
        # 移除 YAML frontmatter
        text = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        # 移除标题标记、代码块、链接等
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'#{1,6}\s+', '', text)
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
        text = re.sub(r'[*_~]+', '', text)
        text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
        # 英文分词 + 中文分字
        english_words = re.findall(r'[a-zA-Z]+', text)
        # 中文字符单字分词
        chinese_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', text)
        return [w.lower() for w in english_words] + chinese_chars

    def _find_md_files(self, directory: str) -> List[str]:
        """递归查找所有 Markdown 文件"""
        files = []
        for root, _, filenames in os.walk(directory):
            for fn in filenames:
                if fn.endswith(('.md', '.markdown', '.txt')):
                    files.append(os.path.join(root, fn))
        return sorted(files)

    def _build_bm25_index(self, collection_name: str = None) -> Tuple[List[Dict], Dict, int]:
        """
        构建 BM25 索引
        
        返回: (docs, idf, total_docs)
        """
        collections_to_search = {}
        if collection_name:
            if collection_name in self.collections:
                collections_to_search[collection_name] = self.collections[collection_name]
            else:
                return [], {}, 0
        else:
            collections_to_search = self.collections

        docs = []  # 每个文档: {"path": str, "content": str, "tokens": List[str], "collection": str}
        doc_freq = Counter()  # 包含每个词的文档数

        for cname, cinfo in collections_to_search.items():
            cpath = cinfo["path"] if isinstance(cinfo, dict) else cinfo
            for filepath in self._find_md_files(cpath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    tokens = self._parse_markdown(content)
                    rel_path = os.path.relpath(filepath, cpath)
                    docs.append({
                        "path": f"{cname}/{rel_path}",
                        "abs_path": filepath,
                        "content": content,
                        "tokens": tokens,
                        "collection": cname,
                    })
                    # 统计文档频率
                    unique_tokens = set(tokens)
                    for token in unique_tokens:
                        doc_freq[token] += 1
                except Exception:
                    continue

        # 计算 IDF
        N = len(docs)
        k1, b = 1.2, 0.75  # BM25 参数
        idf = {}
        for term, df in doc_freq.items():
            idf[term] = math.log((N - df + 0.5) / (df + 0.5) + 1)

        return docs, idf, N

    def search(self, query: str, collection: str = None, top_n: int = 5) -> str:
        """
        BM25 关键词搜索
        
        Args:
            query: 搜索关键词
            collection: 限定集合名
            top_n: 返回结果数量
        
        Returns:
            Markdown 格式的搜索结果
        """
        query_tokens = self._parse_markdown(query)
        if not query_tokens:
            return "搜索词为空。"

        docs, idf, N = self._build_bm25_index(collection)
        if N == 0:
            return "没有创建任何文档集合。请先使用 add_collection 添加。"

        # BM25 评分
        k1, b = 1.2, 0.75
        avg_len = sum(len(d["tokens"]) for d in docs) / max(N, 1)
        scores = []

        for i, doc in enumerate(docs):
            score = 0
            doc_len = len(doc["tokens"])
            token_counts = Counter(doc["tokens"])
            for qt in query_tokens:
                if qt in idf:
                    tf = token_counts.get(qt, 0)
                    idf_val = idf.get(qt, 0)
                    score += idf_val * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
            if score > 0:
                scores.append((i, score))

        # 排序
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:top_n]

        if not scores:
            return f"未找到匹配 '{query}' 的文档。"

        # 构建结果
        result = f"# 搜索结果: {query}\n\n找到 {len(scores)} 个相关文档:\n\n"
        for rank, (idx, score) in enumerate(scores, 1):
            doc = docs[idx]
            snippet = self._extract_snippet(doc["content"], query_tokens, max_lines=8)
            result += f"## {rank}. {doc['path']} (score: {score:.2f})\n\n"
            result += f"```\n{snippet}\n```\n\n"

        return result

    def search_json(self, query: str, collection: str = None, top_n: int = 5) -> List[Dict]:
        """搜索并返回 JSON 格式结果（供 Agent 使用）"""
        query_tokens = self._parse_markdown(query)
        if not query_tokens:
            return []

        docs, idf, N = self._build_bm25_index(collection)
        if N == 0:
            return []

        k1, b = 1.2, 0.75
        avg_len = sum(len(d["tokens"]) for d in docs) / max(N, 1)
        scores = []

        for i, doc in enumerate(docs):
            score = 0
            doc_len = len(doc["tokens"])
            token_counts = Counter(doc["tokens"])
            for qt in query_tokens:
                if qt in idf:
                    tf = token_counts.get(qt, 0)
                    idf_val = idf.get(qt, 0)
                    score += idf_val * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
            if score > 0:
                scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:top_n]

        results = []
        for idx, score in scores:
            doc = docs[idx]
            snippet = self._extract_snippet(doc["content"], query_tokens, max_lines=5)
            results.append({
                "path": doc["path"],
                "abs_path": doc["abs_path"],
                "score": round(score, 3),
                "snippet": snippet,
            })
        return results

    def get_document(self, path: str) -> str:
        """
        获取指定文档内容
        
        Args:
            path: 文档路径，格式为 "collection/relative/path.md"
        
        Returns:
            文档内容
        """
        # 尝试直接读取
        if os.path.isabs(path) and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"读取失败: {e}"

        # 从集合路径查找
        parts = path.split("/", 1)
        if len(parts) == 2:
            collection_name, rel_path = parts
            if collection_name in self.collections:
                cpath = self.collections[collection_name]
                if isinstance(cpath, dict):
                    cpath = cpath["path"]
                full_path = os.path.join(cpath, rel_path)
                if os.path.exists(full_path):
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            return f.read()
                    except Exception as e:
                        return f"读取失败: {e}"
                return f"文件不存在: {full_path}"
            return f"集合 '{collection_name}' 不存在"

        # 模糊匹配
        for cname, cinfo in self.collections.items():
            cpath = cinfo["path"] if isinstance(cinfo, dict) else cinfo
            full_path = os.path.join(cpath, path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    return f"读取失败: {e}"

        return f"未找到文档: {path}"

    def get_document_lines(self, path: str, start: int = None, end: int = None, limit: int = 50) -> str:
        """获取文档的指定行范围"""
        content = self.get_document(path)
        if content.startswith("读取失败") or content.startswith("未找到") or content.startswith("文件不存在") or content.startswith("集合"):
            return content
        lines = content.split('\n')
        if start is not None and end is not None:
            snippet = lines[start-1:end]
        else:
            snippet = lines[:limit]
        result = f"## {path}\n\n"
        for i, line in enumerate(snippet, start or 1):
            result += f"{i:4d} | {line}\n"
        return result

    def list_files(self, collection_name: str = None) -> str:
        """列出文档集合中的文件"""
        if collection_name:
            if collection_name not in self.collections:
                return f"集合 '{collection_name}' 不存在"
            collections = {collection_name: self.collections[collection_name]}
        else:
            collections = self.collections

        result = "# 文档文件列表\n\n"
        for cname, cinfo in collections.items():
            cpath = cinfo["path"] if isinstance(cinfo, dict) else cinfo
            files = self._find_md_files(cpath)
            result += f"## {cname} ({len(files)} 个文件)\n\n"
            for f in files[:20]:
                rel = os.path.relpath(f, cpath)
                result += f"- `{rel}`\n"
            if len(files) > 20:
                result += f"- ... 还有 {len(files) - 20} 个文件\n"
            result += "\n"
        return result

    def status(self) -> str:
        """显示索引状态"""
        total_files = 0
        for cname, cinfo in self.collections.items():
            cpath = cinfo["path"] if isinstance(cinfo, dict) else cinfo
            total_files += len(self._find_md_files(cpath))

        result = "# QMD 状态\n\n"
        result += f"- 集合数量: {len(self.collections)}\n"
        result += f"- 文档总数: {total_files}\n"
        result += f"- 索引路径: {self._get_config_path()}\n"
        return result

    @staticmethod
    def _extract_snippet(content: str, query_tokens: List[str], max_lines: int = 8) -> str:
        """从文档中提取包含搜索词的片段"""
        lines = content.split('\n')
        matching_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for qt in query_tokens:
                if qt in line_lower:
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    matching_lines.extend(range(start, end))
                    break

        if matching_lines:
            unique_lines = sorted(set(matching_lines))
            snippet_lines = lines[unique_lines[0]:unique_lines[-1]+1]
            return '\n'.join(snippet_lines[:max_lines])
        else:
            return '\n'.join(lines[:max_lines])


# ==================== 全局实例 ====================

_qmd_instance = None


def get_qmd_index(workspace_dir: str = None) -> QMDIndex:
    """获取 QMD 索引实例（单例）"""
    global _qmd_instance
    if _qmd_instance is None:
        _qmd_instance = QMDIndex(workspace_dir)
    return _qmd_instance


# ==================== Agent 工具函数 ====================

def qmd_search(query: str, collection: str = "", top_n: int = 5) -> str:
    """
    搜索 Markdown 文档集合
    
    使用 BM25 算法进行全文关键词搜索，返回最相关的文档片段。
    
    Args:
        query: 搜索关键词或短语
        collection: 限定搜索的集合名（可选，不指定则搜索全部）
        top_n: 返回结果数量（默认5，最多20）
    
    Returns:
        搜索结果（Markdown 格式）
    """
    top_n = min(top_n, 20)
    idx = get_qmd_index()
    return idx.search(query, collection or None, top_n)


def qmd_get(path: str) -> str:
    """
    获取指定文档的完整内容
    
    Args:
        path: 文档路径，格式为 "集合名/相对路径.md"
              也可以是绝对路径
    
    Returns:
        文档的完整内容
    """
    idx = get_qmd_index()
    return idx.get_document(path)


def qmd_get_lines(path: str, start: int = 0, end: int = 0, limit: int = 50) -> str:
    """
    获取文档的指定行范围
    
    Args:
        path: 文档路径
        start: 起始行号（从1开始，0表示从头开始）
        end: 结束行号（0表示到末尾）
        limit: 最大返回行数（默认50）
    
    Returns:
        带行号的文档内容
    """
    idx = get_qmd_index()
    s = start if start > 0 else None
    e = end if end > 0 else None
    return idx.get_document_lines(path, s, e, limit)


def qmd_list_collections() -> str:
    """列出所有已注册的文档集合"""
    idx = get_qmd_index()
    return idx.list_collections()


def qmd_list_files(collection: str = "") -> str:
    """列出指定集合中的所有文件"""
    idx = get_qmd_index()
    return idx.list_files(collection or None)


def qmd_add_collection(name: str, path: str, description: str = "") -> str:
    """
    添加一个文档集合到索引
    
    Args:
        name: 集合名称
        path: 文件夹路径
        description: 集合描述（可选）
    
    Returns:
        操作结果
    """
    idx = get_qmd_index()
    return idx.add_collection(name, path, description)


def qmd_remove_collection(name: str) -> str:
    """
    移除一个文档集合
    
    Args:
        name: 集合名称
    
    Returns:
        操作结果
    """
    idx = get_qmd_index()
    return idx.remove_collection(name)


def qmd_status() -> str:
    """显示 QMD 索引状态"""
    idx = get_qmd_index()
    return idx.status()
