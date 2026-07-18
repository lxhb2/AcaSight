"""
知识图谱服务 — Feature 6.7

从文献数据构建多类型知识图谱（论文、作者、关键词、机构），
支持邻居查询、路径查找、社区检测。
"""

import os
import json
import sqlite3
import logging
from typing import Optional, List, Dict, Any, Set
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# ─── 类型常量 ───
NODE_TYPE_PAPER = "paper"
NODE_TYPE_AUTHOR = "author"
NODE_TYPE_KEYWORD = "keyword"
NODE_TYPE_INSTITUTION = "institution"

VALID_NODE_TYPES = {NODE_TYPE_PAPER, NODE_TYPE_AUTHOR, NODE_TYPE_KEYWORD, NODE_TYPE_INSTITUTION}

# ─── 节点颜色映射 ───
NODE_TYPE_COLORS = {
    NODE_TYPE_PAPER: "#4a90d9",
    NODE_TYPE_AUTHOR: "#2ecc71",
    NODE_TYPE_KEYWORD: "#e67e22",
    NODE_TYPE_INSTITUTION: "#9b59b6",
}

# ─── 示例/演示数据（无文献时使用） ───
DEMO_DATA = {
    "nodes": [
        {"id": "paper-1", "label": "Deep Learning for NLP", "type": "paper", "size": 8, "metadata": {"year": 2020, "journal": "Nature", "citation_count": 150, "authors": ["Alice Chen", "Bob Smith"], "doi": "10.1234/demo1"}},
        {"id": "paper-2", "label": "Transformer Architecture", "type": "paper", "size": 10, "metadata": {"year": 2017, "journal": "NeurIPS", "citation_count": 5000, "authors": ["Ashish Vaswani", "Noam Shazeer"], "doi": "10.1234/demo2"}},
        {"id": "paper-3", "label": "BERT: Pre-training of Deep Bidirectional Transformers", "type": "paper", "size": 9, "metadata": {"year": 2019, "journal": "NAACL", "citation_count": 3000, "authors": ["Jacob Devlin", "Ming-Wei Chang"], "doi": "10.1234/demo3"}},
        {"id": "paper-4", "label": "GPT-3: Language Models are Few-Shot Learners", "type": "paper", "size": 9, "metadata": {"year": 2020, "journal": "NeurIPS", "citation_count": 2500, "authors": ["Tom Brown", "Benjamin Mann"], "doi": "10.1234/demo4"}},
        {"id": "paper-5", "label": "Attention Mechanisms in Computer Vision", "type": "paper", "size": 6, "metadata": {"year": 2021, "journal": "CVPR", "citation_count": 200, "authors": ["Meng-Hao Guo", "Tian-Xing Xu"], "doi": "10.1234/demo5"}},
        {"id": "author-1", "label": "Alice Chen", "type": "author", "size": 5, "metadata": {"paper_count": 12, "h_index": 8}},
        {"id": "author-2", "label": "Bob Smith", "type": "author", "size": 4, "metadata": {"paper_count": 8, "h_index": 5}},
        {"id": "author-3", "label": "Ashish Vaswani", "type": "author", "size": 7, "metadata": {"paper_count": 25, "h_index": 15}},
        {"id": "author-4", "label": "Jacob Devlin", "type": "author", "size": 6, "metadata": {"paper_count": 18, "h_index": 12}},
        {"id": "keyword-1", "label": "Deep Learning", "type": "keyword", "size": 7, "metadata": {"frequency": 45}},
        {"id": "keyword-2", "label": "Transformer", "type": "keyword", "size": 8, "metadata": {"frequency": 60}},
        {"id": "keyword-3", "label": "Attention Mechanism", "type": "keyword", "size": 6, "metadata": {"frequency": 35}},
        {"id": "keyword-4", "label": "NLP", "type": "keyword", "size": 7, "metadata": {"frequency": 50}},
        {"id": "keyword-5", "label": "Pre-training", "type": "keyword", "size": 5, "metadata": {"frequency": 28}},
        {"id": "inst-1", "label": "Google Research", "type": "institution", "size": 8, "metadata": {"country": "USA", "paper_count": 500}},
        {"id": "inst-2", "label": "Stanford University", "type": "institution", "size": 7, "metadata": {"country": "USA", "paper_count": 350}},
        {"id": "inst-3", "label": "Tsinghua University", "type": "institution", "size": 6, "metadata": {"country": "China", "paper_count": 280}},
    ],
    "edges": [
        {"source": "paper-1", "target": "paper-2", "weight": 0.8, "type": "cites"},
        {"source": "paper-3", "target": "paper-2", "weight": 0.9, "type": "cites"},
        {"source": "paper-4", "target": "paper-2", "weight": 0.7, "type": "cites"},
        {"source": "paper-4", "target": "paper-3", "weight": 0.6, "type": "cites"},
        {"source": "paper-5", "target": "paper-2", "weight": 0.5, "type": "cites"},
        {"source": "paper-1", "target": "author-1", "weight": 1.0, "type": "authored_by"},
        {"source": "paper-1", "target": "author-2", "weight": 1.0, "type": "authored_by"},
        {"source": "paper-2", "target": "author-3", "weight": 1.0, "type": "authored_by"},
        {"source": "paper-3", "target": "author-4", "weight": 1.0, "type": "authored_by"},
        {"source": "paper-1", "target": "keyword-1", "weight": 0.8, "type": "has_keyword"},
        {"source": "paper-1", "target": "keyword-4", "weight": 0.9, "type": "has_keyword"},
        {"source": "paper-2", "target": "keyword-2", "weight": 1.0, "type": "has_keyword"},
        {"source": "paper-2", "target": "keyword-3", "weight": 0.9, "type": "has_keyword"},
        {"source": "paper-3", "target": "keyword-2", "weight": 0.8, "type": "has_keyword"},
        {"source": "paper-3", "target": "keyword-5", "weight": 0.9, "type": "has_keyword"},
        {"source": "paper-4", "target": "keyword-2", "weight": 0.7, "type": "has_keyword"},
        {"source": "paper-4", "target": "keyword-5", "weight": 0.8, "type": "has_keyword"},
        {"source": "paper-5", "target": "keyword-3", "weight": 0.9, "type": "has_keyword"},
        {"source": "paper-5", "target": "keyword-1", "weight": 0.6, "type": "has_keyword"},
        {"source": "author-3", "target": "inst-1", "weight": 1.0, "type": "affiliated_with"},
        {"source": "author-4", "target": "inst-1", "weight": 1.0, "type": "affiliated_with"},
        {"source": "author-1", "target": "inst-2", "weight": 1.0, "type": "affiliated_with"},
        {"source": "author-2", "target": "inst-3", "weight": 1.0, "type": "affiliated_with"},
    ],
}


class KnowledgeGraphService:
    """知识图谱服务：构建、查询、路径查找、社区检测"""

    def __init__(self):
        # 内存缓存
        self._graph_cache: Optional[Dict[str, Any]] = None
        self._cache_key: Optional[str] = None

    def build_graph(
        self,
        node_types: Optional[str] = None,
        max_nodes: int = 200,
        min_connections: int = 0,
    ) -> Dict[str, Any]:
        """
        从文献数据构建知识图谱

        Args:
            node_types: 逗号分隔的节点类型 (paper|author|keyword|institution)
            max_nodes: 最大节点数
            min_connections: 最小连接数过滤
        """
        # 解析节点类型过滤
        type_filter: Optional[Set[str]] = None
        if node_types:
            type_filter = {t.strip() for t in node_types.split(",") if t.strip() in VALID_NODE_TYPES}
            if not type_filter:
                type_filter = None

        # 尝试从数据库加载文献数据
        papers = self._load_papers_from_db()

        if not papers:
            # 无文献数据，返回演示数据
            result = self._filter_demo_data(type_filter, max_nodes, min_connections)
            return result

        # 从文献数据构建图谱
        nodes: List[Dict] = []
        edges: List[Dict] = []
        node_map: Dict[str, Dict] = {}  # id -> node
        adjacency: Dict[str, Set[str]] = defaultdict(set)  # 节点邻接表

        # 1. 创建论文节点
        for p in papers:
            if type_filter and NODE_TYPE_PAPER not in type_filter:
                continue
            node_id = f"paper-{p['id']}"
            node = {
                "id": node_id,
                "label": (p.get("title") or "Untitled")[:60],
                "type": NODE_TYPE_PAPER,
                "size": max(4, min(15, (p.get("citation_count") or 0) // 50 + 4)),
                "metadata": {
                    "year": p.get("year"),
                    "journal": p.get("journal"),
                    "citation_count": p.get("citation_count", 0),
                    "doi": p.get("doi"),
                    "abstract": (p.get("abstract") or "")[:200],
                },
            }
            nodes.append(node)
            node_map[node_id] = node

        # 2. 创建作者节点 + 边
        if not type_filter or NODE_TYPE_AUTHOR in type_filter:
            author_papers: Dict[str, List[str]] = defaultdict(list)
            for p in papers:
                authors = p.get("authors") or []
                if isinstance(authors, str):
                    try:
                        authors = json.loads(authors)
                    except (json.JSONDecodeError, TypeError):
                        authors = [a.strip() for a in authors.split(",") if a.strip()]
                for author in authors[:5]:  # 限制每篇最多5位作者
                    if not author:
                        continue
                    author_id = f"author-{author.lower().replace(' ', '-')}"
                    if author_id not in node_map:
                        node = {
                            "id": author_id,
                            "label": author,
                            "type": NODE_TYPE_AUTHOR,
                            "size": 4,
                            "metadata": {"name": author},
                        }
                        nodes.append(node)
                        node_map[author_id] = node
                    # 论文-作者边
                    paper_id = f"paper-{p['id']}"
                    edge = {"source": paper_id, "target": author_id, "weight": 1.0, "type": "authored_by"}
                    edges.append(edge)
                    adjacency[paper_id].add(author_id)
                    adjacency[author_id].add(paper_id)
                    author_papers[author_id].append(paper_id)

            # 更新作者节点大小
            for author_id, paper_ids in author_papers.items():
                if author_id in node_map:
                    node_map[author_id]["size"] = max(3, min(12, len(paper_ids) + 2))
                    node_map[author_id]["metadata"]["paper_count"] = len(paper_ids)

        # 3. 创建关键词节点 + 边
        if not type_filter or NODE_TYPE_KEYWORD in type_filter:
            keyword_papers: Dict[str, List[str]] = defaultdict(list)
            for p in papers:
                keywords = p.get("keywords") or []
                if isinstance(keywords, str):
                    try:
                        keywords = json.loads(keywords)
                    except (json.JSONDecodeError, TypeError):
                        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
                tags = p.get("tags") or []
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags = [t.strip() for t in tags.split(",") if t.strip()]
                all_kw = list(set(keywords + tags))[:8]  # 合并关键词和标签
                for kw in all_kw:
                    if not kw:
                        continue
                    kw_id = f"keyword-{kw.lower().replace(' ', '-')}"
                    if kw_id not in node_map:
                        node = {
                            "id": kw_id,
                            "label": kw,
                            "type": NODE_TYPE_KEYWORD,
                            "size": 3,
                            "metadata": {"name": kw},
                        }
                        nodes.append(node)
                        node_map[kw_id] = node
                    paper_id = f"paper-{p['id']}"
                    edge = {"source": paper_id, "target": kw_id, "weight": 0.7, "type": "has_keyword"}
                    edges.append(edge)
                    adjacency[paper_id].add(kw_id)
                    adjacency[kw_id].add(paper_id)
                    keyword_papers[kw_id].append(paper_id)

            # 更新关键词节点大小
            for kw_id, paper_ids in keyword_papers.items():
                if kw_id in node_map:
                    node_map[kw_id]["size"] = max(3, min(12, len(paper_ids) + 2))
                    node_map[kw_id]["metadata"]["frequency"] = len(paper_ids)

        # 4. 创建机构节点 + 边（从 extra_fields 提取）
        if not type_filter or NODE_TYPE_INSTITUTION in type_filter:
            inst_authors: Dict[str, List[str]] = defaultdict(list)
            for p in papers:
                extra = p.get("extra_fields") or {}
                if isinstance(extra, str):
                    try:
                        extra = json.loads(extra)
                    except (json.JSONDecodeError, TypeError):
                        extra = {}
                institutions = extra.get("institutions") or []
                if not institutions:
                    continue
                if isinstance(institutions, str):
                    institutions = [i.strip() for i in institutions.split(",") if i.strip()]
                authors = p.get("authors") or []
                if isinstance(authors, str):
                    try:
                        authors = json.loads(authors)
                    except (json.JSONDecodeError, TypeError):
                        authors = [a.strip() for a in authors.split(",") if a.strip()]
                for inst in institutions[:3]:
                    if not inst:
                        continue
                    inst_id = f"inst-{inst.lower().replace(' ', '-')}"
                    if inst_id not in node_map:
                        node = {
                            "id": inst_id,
                            "label": inst,
                            "type": NODE_TYPE_INSTITUTION,
                            "size": 4,
                            "metadata": {"name": inst},
                        }
                        nodes.append(node)
                        node_map[inst_id] = node
                    # 作者-机构边
                    for author in authors[:3]:
                        author_id = f"author-{author.lower().replace(' ', '-')}"
                        if author_id in node_map:
                            edge = {"source": author_id, "target": inst_id, "weight": 1.0, "type": "affiliated_with"}
                            edges.append(edge)
                            adjacency[author_id].add(inst_id)
                            adjacency[inst_id].add(author_id)
                            inst_authors[inst_id].append(author_id)

            # 更新机构节点大小
            for inst_id, author_ids in inst_authors.items():
                if inst_id in node_map:
                    node_map[inst_id]["size"] = max(3, min(12, len(set(author_ids)) + 3))
                    node_map[inst_id]["metadata"]["author_count"] = len(set(author_ids))

        # 5. 论文间引用边
        if not type_filter or NODE_TYPE_PAPER in type_filter:
            doi_map: Dict[str, str] = {}
            for p in papers:
                if p.get("doi"):
                    doi_map[p["doi"]] = f"paper-{p['id']}"
            for p in papers:
                extra = p.get("extra_fields") or {}
                if isinstance(extra, str):
                    try:
                        extra = json.loads(extra)
                    except (json.JSONDecodeError, TypeError):
                        extra = {}
                refs = extra.get("references") or []
                if not refs:
                    continue
                paper_id = f"paper-{p['id']}"
                for ref in refs[:10]:
                    ref_doi = ref.get("doi") if isinstance(ref, dict) else None
                    if ref_doi and ref_doi in doi_map and doi_map[ref_doi] != paper_id:
                        target_id = doi_map[ref_doi]
                        edge = {"source": paper_id, "target": target_id, "weight": 0.8, "type": "cites"}
                        edges.append(edge)
                        adjacency[paper_id].add(target_id)
                        adjacency[target_id].add(paper_id)

        # 6. 最小连接数过滤
        if min_connections > 0:
            valid_ids = {nid for nid, neighbors in adjacency.items() if len(neighbors) >= min_connections}
            # 保留连接数不足但类型为 paper 的节点（论文是核心）
            for node in nodes:
                if node["type"] == NODE_TYPE_PAPER and node["id"] not in valid_ids:
                    if len(adjacency.get(node["id"], set())) > 0:
                        valid_ids.add(node["id"])
            nodes = [n for n in nodes if n["id"] in valid_ids]
            edges = [e for e in edges if e["source"] in valid_ids and e["target"] in valid_ids]

        # 7. 限制最大节点数
        if len(nodes) > max_nodes:
            # 按连接数排序，保留连接最多的节点
            node_scores = {n["id"]: len(adjacency.get(n["id"], set())) for n in nodes}
            nodes.sort(key=lambda n: node_scores.get(n["id"], 0), reverse=True)
            keep_ids = {n["id"] for n in nodes[:max_nodes]}
            nodes = nodes[:max_nodes]
            edges = [e for e in edges if e["source"] in keep_ids and e["target"] in keep_ids]

        # 缓存
        result = {"nodes": nodes, "edges": edges}
        cache_key = f"{node_types}:{max_nodes}:{min_connections}"
        self._graph_cache = result
        self._cache_key = cache_key

        return result

    def get_node_details(self, node_id: str) -> Optional[Dict]:
        """获取节点详情"""
        # 先尝试从缓存中查找
        if self._graph_cache:
            for node in self._graph_cache.get("nodes", []):
                if node["id"] == node_id:
                    return node
        # 否则重建图谱查找
        graph = self.build_graph()
        for node in graph.get("nodes", []):
            if node["id"] == node_id:
                return node
        return None

    def get_neighbors(self, node_id: str) -> Dict[str, Any]:
        """获取节点的邻居节点和边"""
        graph = self.build_graph()
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # 找到所有直接邻居
        neighbor_ids: Set[str] = set()
        neighbor_edges: List[Dict] = []
        for edge in edges:
            if edge["source"] == node_id:
                neighbor_ids.add(edge["target"])
                neighbor_edges.append(edge)
            elif edge["target"] == node_id:
                neighbor_ids.add(edge["source"])
                neighbor_edges.append(edge)

        # 收集邻居节点
        node_map = {n["id"]: n for n in nodes}
        neighbor_nodes = [node_map[nid] for nid in neighbor_ids if nid in node_map]

        # 中心节点
        center_node = node_map.get(node_id)

        return {
            "center": center_node,
            "neighbors": neighbor_nodes,
            "edges": neighbor_edges,
        }

    def find_paths(self, from_id: str, to_id: str, max_depth: int = 4) -> Dict[str, Any]:
        """BFS 查找两个节点之间的最短路径"""
        graph = self.build_graph()
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # 构建邻接表
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        edge_map: Dict[str, Dict] = {}  # "src->tgt" -> edge
        for edge in edges:
            src, tgt = edge["source"], edge["target"]
            adjacency[src].add(tgt)
            adjacency[tgt].add(src)
            edge_map[f"{src}->{tgt}"] = edge
            edge_map[f"{tgt}->{src}"] = edge

        if from_id not in adjacency or to_id not in adjacency:
            return {"paths": [], "found": False, "message": "节点不存在"}

        # BFS
        visited: Set[str] = {from_id}
        queue: deque = deque([(from_id, [from_id])])
        paths: List[List[str]] = []

        while queue and len(paths) < 5:  # 最多返回5条路径
            current, path = queue.popleft()
            if len(path) - 1 > max_depth:
                continue
            if current == to_id:
                paths.append(path)
                continue
            for neighbor in adjacency[current]:
                if neighbor not in visited or neighbor == to_id:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        # 构建路径详情
        node_map = {n["id"]: n for n in nodes}
        detailed_paths = []
        for path in paths:
            path_nodes = [node_map.get(nid, {"id": nid, "label": nid, "type": "unknown"}) for nid in path]
            path_edges = []
            for i in range(len(path) - 1):
                key = f"{path[i]}->{path[i+1]}"
                edge = edge_map.get(key, {"source": path[i], "target": path[i+1], "weight": 0, "type": "unknown"})
                path_edges.append(edge)
            detailed_paths.append({"nodes": path_nodes, "edges": path_edges, "length": len(path) - 1})

        return {
            "paths": detailed_paths,
            "found": len(paths) > 0,
            "from_id": from_id,
            "to_id": to_id,
        }

    def detect_clusters(self) -> Dict[str, Any]:
        """
        简单社区检测：基于连通分量的聚类

        使用 BFS 找出所有连通分量，每个连通分量视为一个社区。
        对大社区进一步按度中心性拆分。
        """
        graph = self.build_graph()
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        # 构建邻接表
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for edge in edges:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])

        # BFS 找连通分量
        visited: Set[str] = set()
        components: List[Set[str]] = []
        all_node_ids = {n["id"] for n in nodes}

        for node_id in all_node_ids:
            if node_id in visited:
                continue
            component: Set[str] = set()
            queue: deque = deque([node_id])
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            components.append(component)

        # 颜色列表
        cluster_colors = [
            "#4a90d9", "#2ecc71", "#e67e22", "#9b59b6", "#e74c3c",
            "#1abc9c", "#f39c12", "#3498db", "#e91e63", "#00bcd4",
        ]

        # 按大小排序，大社区拆分
        clusters: List[Dict] = []
        cluster_id = 0
        for component in sorted(components, key=len, reverse=True):
            if len(component) <= 15:
                # 小社区直接作为一个聚类
                clusters.append({
                    "id": f"cluster-{cluster_id}",
                    "label": f"社区 {cluster_id + 1}（{len(component)} 节点）",
                    "node_ids": list(component),
                    "color": cluster_colors[cluster_id % len(cluster_colors)],
                })
                cluster_id += 1
            else:
                # 大社区按度中心性拆分
                # 计算每个节点的度
                degrees = {nid: len(adjacency.get(nid, set())) for nid in component}
                # 取度最高的节点作为种子
                sorted_by_degree = sorted(degrees.items(), key=lambda x: x[1], reverse=True)
                seeds = [sorted_by_degree[i][0] for i in range(0, min(3, len(sorted_by_degree)), max(1, len(sorted_by_degree) // 3))]

                if not seeds:
                    clusters.append({
                        "id": f"cluster-{cluster_id}",
                        "label": f"社区 {cluster_id + 1}（{len(component)} 节点）",
                        "node_ids": list(component),
                        "color": cluster_colors[cluster_id % len(cluster_colors)],
                    })
                    cluster_id += 1
                    continue

                # 简单标签传播：每个节点归属最近的种子
                sub_clusters: Dict[str, Set[str]] = {s: {s} for s in seeds}
                assigned: Set[str] = set(seeds)
                for nid in component:
                    if nid in assigned:
                        continue
                    # 找最近的种子（BFS 距离）
                    best_seed = seeds[0]
                    best_dist = float('inf')
                    for seed in seeds:
                        dist = self._bfs_distance(nid, seed, adjacency)
                        if dist < best_dist:
                            best_dist = dist
                            best_seed = seed
                    sub_clusters[best_seed].add(nid)
                    assigned.add(nid)

                for seed, members in sub_clusters.items():
                    if members:
                        clusters.append({
                            "id": f"cluster-{cluster_id}",
                            "label": f"社区 {cluster_id + 1}（{len(members)} 节点）",
                            "node_ids": list(members),
                            "color": cluster_colors[cluster_id % len(cluster_colors)],
                        })
                        cluster_id += 1

        return {"clusters": clusters, "total_clusters": len(clusters)}

    # ─── 内部方法 ───

    def _load_papers_from_db(self) -> List[Dict]:
        """从 SQLite 数据库加载文献数据"""
        try:
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "literature", "paper.db")
            if not os.path.exists(db_path):
                return []
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            # 先检测可用列，避免因缺少列报错
            cursor = conn.execute("PRAGMA table_info(paper_structured)")
            available_cols = {row[1] for row in cursor.fetchall()}
            desired_cols = ["id", "title", "authors", "year", "journal", "doi", "abstract", "keywords", "tags", "extra_fields", "citation_count"]
            select_cols = [c for c in desired_cols if c in available_cols]
            if not select_cols or "id" not in select_cols or "title" not in select_cols:
                conn.close()
                return []
            rows = conn.execute(
                f"SELECT {', '.join(select_cols)} FROM paper_structured ORDER BY year DESC LIMIT 500"
            ).fetchall()
            conn.close()
            result = []
            for row in rows:
                d = dict(row)
                # 解析 JSON 字段
                for field in ["authors", "keywords", "tags", "extra_fields"]:
                    val = d.get(field)
                    if isinstance(val, str):
                        try:
                            d[field] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
                # 确保缺失字段有默认值
                for field in desired_cols:
                    if field not in d:
                        d[field] = [] if field in ("authors", "keywords", "tags") else ({} if field == "extra_fields" else None)
                result.append(d)
            return result
        except Exception as e:
            logger.warning(f"加载文献数据失败: {e}")
            return []

    def _filter_demo_data(
        self,
        type_filter: Optional[Set[str]],
        max_nodes: int,
        min_connections: int,
    ) -> Dict[str, Any]:
        """过滤演示数据"""
        nodes = DEMO_DATA["nodes"]
        edges = DEMO_DATA["edges"]

        # 按类型过滤
        if type_filter:
            valid_ids = {n["id"] for n in nodes if n["type"] in type_filter}
            # 同时保留连接节点（保证图连通性）
            for edge in edges:
                src_type = next((n["type"] for n in nodes if n["id"] == edge["source"]), None)
                tgt_type = next((n["type"] for n in nodes if n["id"] == edge["target"]), None)
                if src_type in type_filter and tgt_type in type_filter:
                    valid_ids.add(edge["source"])
                    valid_ids.add(edge["target"])
            nodes = [n for n in nodes if n["id"] in valid_ids]
            edges = [e for e in edges if e["source"] in valid_ids and e["target"] in valid_ids]

        # 最小连接数过滤
        if min_connections > 0:
            adjacency: Dict[str, int] = defaultdict(int)
            for edge in edges:
                adjacency[edge["source"]] += 1
                adjacency[edge["target"]] += 1
            valid_ids = {nid for nid, count in adjacency.items() if count >= min_connections}
            nodes = [n for n in nodes if n["id"] in valid_ids]
            edges = [e for e in edges if e["source"] in valid_ids and e["target"] in valid_ids]

        # 限制最大节点数
        if len(nodes) > max_nodes:
            nodes = nodes[:max_nodes]
            node_ids = {n["id"] for n in nodes}
            edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

        return {"nodes": nodes, "edges": edges}

    def _bfs_distance(self, from_id: str, to_id: str, adjacency: Dict[str, Set[str]]) -> int:
        """计算两个节点之间的 BFS 距离"""
        if from_id == to_id:
            return 0
        visited = {from_id}
        queue: deque = deque([(from_id, 0)])
        while queue:
            current, dist = queue.popleft()
            if dist > 6:  # 限制搜索深度
                break
            for neighbor in adjacency.get(current, set()):
                if neighbor == to_id:
                    return dist + 1
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, dist + 1))
        return float('inf')


# ─── 单例 ───
_kg_service: Optional[KnowledgeGraphService] = None


def get_knowledge_graph_service() -> KnowledgeGraphService:
    """获取知识图谱服务单例"""
    global _kg_service
    if _kg_service is None:
        _kg_service = KnowledgeGraphService()
    return _kg_service
