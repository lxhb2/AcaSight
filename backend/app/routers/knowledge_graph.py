"""
知识图谱可视化路由 — Feature 6.7

提供知识图谱的构建、节点查询、邻居查询、路径查找、社区检测等接口。
前缀: /api/knowledge-graph
"""

from fastapi import APIRouter, Query
from typing import Optional
import logging

from app.services.knowledge_graph_service import get_knowledge_graph_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/graph")
async def get_graph(
    node_types: Optional[str] = Query(
        None,
        description="逗号分隔的节点类型: paper,author,keyword,institution"
    ),
    max_nodes: int = Query(200, ge=10, le=500, description="最大节点数"),
    min_connections: int = Query(0, ge=0, le=10, description="最小连接数过滤"),
):
    """获取完整知识图谱"""
    service = get_knowledge_graph_service()
    result = service.build_graph(
        node_types=node_types,
        max_nodes=max_nodes,
        min_connections=min_connections,
    )
    return result


@router.get("/node/{node_id}")
async def get_node(node_id: str):
    """获取节点详情"""
    service = get_knowledge_graph_service()
    result = service.get_node_details(node_id)
    if result is None:
        return {"error": "节点不存在", "node_id": node_id}
    return result


@router.get("/neighbors/{node_id}")
async def get_neighbors(node_id: str):
    """获取节点的邻居节点和边"""
    service = get_knowledge_graph_service()
    result = service.get_neighbors(node_id)
    return result


@router.get("/paths")
async def find_paths(
    from_id: str = Query(..., description="起始节点 ID"),
    to_id: str = Query(..., description="目标节点 ID"),
    max_depth: int = Query(4, ge=1, le=6, description="最大搜索深度"),
):
    """查找两个节点之间的最短路径"""
    service = get_knowledge_graph_service()
    result = service.find_paths(from_id=from_id, to_id=to_id, max_depth=max_depth)
    return result


@router.get("/clusters")
async def get_clusters():
    """获取社区检测结果"""
    service = get_knowledge_graph_service()
    result = service.detect_clusters()
    return result
