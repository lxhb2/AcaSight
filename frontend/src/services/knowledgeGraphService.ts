/**
 * 知识图谱可视化 API 客户端 — Feature 6.7
 *
 * 与后端 /api/knowledge-graph 通信
 */

const BASE_URL = '/api/knowledge-graph';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (options?.headers) {
    Object.assign(headers, options.headers as Record<string, string>);
  }
  const res = await fetch(`${BASE_URL}${url}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err);
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.json();
}

// ─── 类型定义 ───

/** 图谱节点 */
export interface KGNode {
  id: string;
  label: string;
  type: 'paper' | 'author' | 'keyword' | 'institution';
  size: number;
  metadata: Record<string, unknown>;
}

/** 图谱边 */
export interface KGEdge {
  source: string;
  target: string;
  weight: number;
  type: string;
}

/** 图谱数据 */
export interface KGGraphData {
  nodes: KGNode[];
  edges: KGEdge[];
}

/** 邻居查询结果 */
export interface KGNeighborsResult {
  center: KGNode | null;
  neighbors: KGNode[];
  edges: KGEdge[];
}

/** 路径节点 */
export interface KGPathNode {
  id: string;
  label: string;
  type: string;
}

/** 路径详情 */
export interface KGPath {
  nodes: KGPathNode[];
  edges: KGEdge[];
  length: number;
}

/** 路径查询结果 */
export interface KGPathsResult {
  paths: KGPath[];
  found: boolean;
  from_id: string;
  to_id: string;
}

/** 社区/聚类 */
export interface KGCluster {
  id: string;
  label: string;
  node_ids: string[];
  color: string;
}

/** 社区检测结果 */
export interface KGClustersResult {
  clusters: KGCluster[];
  total_clusters: number;
}

// ─── API 方法 ───

export const knowledgeGraphApi = {
  /** 获取完整知识图谱 */
  getGraph: (params?: {
    node_types?: string;
    max_nodes?: number;
    min_connections?: number;
  }) => {
    const p = new URLSearchParams();
    if (params?.node_types) p.set('node_types', params.node_types);
    if (params?.max_nodes !== undefined) p.set('max_nodes', String(params.max_nodes));
    if (params?.min_connections !== undefined) p.set('min_connections', String(params.min_connections));
    const qs = p.toString();
    return request<KGGraphData>(`/graph${qs ? `?${qs}` : ''}`);
  },

  /** 获取节点详情 */
  getNode: (nodeId: string) =>
    request<KGNode>(`/node/${encodeURIComponent(nodeId)}`),

  /** 获取节点邻居 */
  getNeighbors: (nodeId: string) =>
    request<KGNeighborsResult>(`/neighbors/${encodeURIComponent(nodeId)}`),

  /** 查找两节点间路径 */
  findPaths: (fromId: string, toId: string, maxDepth?: number) => {
    const p = new URLSearchParams({ from_id: fromId, to_id: toId });
    if (maxDepth !== undefined) p.set('max_depth', String(maxDepth));
    return request<KGPathsResult>(`/paths?${p}`);
  },

  /** 获取社区检测结果 */
  getClusters: () =>
    request<KGClustersResult>('/clusters'),
};
