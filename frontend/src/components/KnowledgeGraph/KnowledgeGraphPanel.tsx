/**
 * KnowledgeGraphPanel — 知识图谱可视化面板 (Feature 6.7)
 *
 * 使用 Canvas API 实现自定义力导向图布局：
 * - 库仑斥力 + 胡克引力 + 中心引力 + 阻尼
 * - 节点拖拽、缩放平移、点击详情、悬停高亮
 * - 节点类型筛选、搜索、社区检测
 * - Glass-morphism 风格
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  Search, ZoomIn, ZoomOut, RotateCcw, X, Filter,
  Loader2, ChevronRight, Map, Route, Layers,
} from 'lucide-react';
import {
  knowledgeGraphApi,
  KGNode, KGEdge, KGCluster, KGNeighborsResult, KGPathsResult,
} from '@/services/knowledgeGraphService';

// ─── 常量 ───

/** 节点类型颜色映射 */
const TYPE_COLORS: Record<string, string> = {
  paper: '#4a90d9',
  author: '#2ecc71',
  keyword: '#e67e22',
  institution: '#9b59b6',
};

/** 节点类型中文标签 */
const TYPE_LABELS: Record<string, string> = {
  paper: '论文',
  author: '作者',
  keyword: '关键词',
  institution: '机构',
};

/** 力模拟参数 */
const SIM = {
  repulsion: 800,       // 库仑斥力系数
  attraction: 0.005,    // 胡克引力系数
  centerGravity: 0.01,  // 中心引力
  damping: 0.85,        // 速度阻尼
  minAlpha: 0.001,      // 最小活跃度（低于此值停止模拟）
  alphaDecay: 0.998,    // 活跃度衰减
};

// ─── 力模拟节点（内部状态） ───

interface SimNode extends KGNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number; // 固定位置（拖拽时）
  fy?: number;
}

// ─── 组件 ───

export const KnowledgeGraphPanel: React.FC = () => {
  // ── 数据状态 ──
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [edges, setEdges] = useState<KGEdge[]>([]);
  const [clusters, setClusters] = useState<KGCluster[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── 控制状态 ──
  const [nodeTypeFilter, setNodeTypeFilter] = useState<Record<string, boolean>>({
    paper: true, author: true, keyword: true, institution: true,
  });
  const [maxNodes, setMaxNodes] = useState(200);
  const [minConnections, setMinConnections] = useState(0);
  const [showClusters, setShowClusters] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // ── 交互状态 ──
  const [selectedNode, setSelectedNode] = useState<SimNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<SimNode | null>(null);
  const [neighborData, setNeighborData] = useState<KGNeighborsResult | null>(null);
  const [pathSearchFrom, setPathSearchFrom] = useState<string | null>(null);
  const [pathSearchTo, setPathSearchTo] = useState<string>('');
  const [pathResult, setPathResult] = useState<KGPathsResult | null>(null);
  const [pathLoading, setPathLoading] = useState(false);

  // ── Canvas 引用 ──
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const simNodesRef = useRef<SimNode[]>([]);
  const edgesRef = useRef<KGEdge[]>([]);
  const alphaRef = useRef(1.0);
  const animFrameRef = useRef<number>(0);
  const transformRef = useRef({ x: 0, y: 0, scale: 1 });
  const dragRef = useRef<{ nodeId: string | null; startX: number; startY: number; isPanning: boolean }>({
    nodeId: null, startX: 0, startY: 0, isPanning: false,
  });

  // ── 过滤后的数据 ──
  const filteredNodes = useMemo(() => {
    let result = nodes.filter(n => nodeTypeFilter[n.type] !== false);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchIds = new Set<string>();
      result.forEach(n => {
        if (n.label.toLowerCase().includes(q)) matchIds.add(n.id);
      });
      // 也包含匹配节点的邻居
      edges.forEach(e => {
        if (matchIds.has(e.source)) matchIds.add(e.target);
        if (matchIds.has(e.target)) matchIds.add(e.source);
      });
      result = result.filter(n => matchIds.has(n.id));
    }
    return result;
  }, [nodes, edges, nodeTypeFilter, searchQuery]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    return edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
  }, [filteredNodes, edges]);

  // 高亮节点集合
  const highlightIds = useMemo(() => {
    const ids = new Set<string>();
    if (hoveredNode) {
      ids.add(hoveredNode.id);
      filteredEdges.forEach(e => {
        if (e.source === hoveredNode.id) ids.add(e.target);
        if (e.target === hoveredNode.id) ids.add(e.source);
      });
    }
    if (selectedNode) {
      ids.add(selectedNode.id);
      filteredEdges.forEach(e => {
        if (e.source === selectedNode.id) ids.add(e.target);
        if (e.target === selectedNode.id) ids.add(e.source);
      });
    }
    // 路径高亮
    if (pathResult?.found) {
      pathResult.paths.forEach(p => {
        p.nodes.forEach(n => ids.add(n.id));
      });
    }
    return ids;
  }, [hoveredNode, selectedNode, filteredEdges, pathResult]);

  // ── 加载图谱数据 ──
  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const activeTypes = Object.entries(nodeTypeFilter)
        .filter(([, v]) => v)
        .map(([k]) => k)
        .join(',');
      const data = await knowledgeGraphApi.getGraph({
        node_types: activeTypes || undefined,
        max_nodes: maxNodes,
        min_connections: minConnections,
      });
      // 初始化模拟节点（随机位置）
      const simNodes: SimNode[] = data.nodes.map(n => ({
        ...n,
        x: (Math.random() - 0.5) * 600,
        y: (Math.random() - 0.5) * 600,
        vx: 0,
        vy: 0,
      }));
      setNodes(simNodes);
      setEdges(data.edges);
      simNodesRef.current = simNodes;
      edgesRef.current = data.edges;
      alphaRef.current = 1.0;
      // 重置视图
      transformRef.current = { x: 0, y: 0, scale: 1 };
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载图谱失败');
    } finally {
      setLoading(false);
    }
  }, [nodeTypeFilter, maxNodes, minConnections]);

  // 加载社区检测
  const loadClusters = useCallback(async () => {
    try {
      const data = await knowledgeGraphApi.getClusters();
      setClusters(data.clusters);
    } catch { /* 忽略 */ }
  }, []);

  useEffect(() => { loadGraph(); }, [loadGraph]);

  useEffect(() => {
    if (showClusters && clusters.length === 0) {
      loadClusters();
    }
  }, [showClusters, clusters.length, loadClusters]);

  // ── 力模拟循环 ──
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const simLoop = () => {
      const simNodes = simNodesRef.current;
      const simEdges = edgesRef.current;
      const alpha = alphaRef.current;

      if (alpha > SIM.minAlpha && simNodes.length > 0) {
        // 库仑斥力：所有节点对之间
        for (let i = 0; i < simNodes.length; i++) {
          for (let j = i + 1; j < simNodes.length; j++) {
            const ni = simNodes[i];
            const nj = simNodes[j];
            let dx = nj.x - ni.x;
            let dy = nj.y - ni.y;
            let dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; dist = 1; }
            const force = (SIM.repulsion * alpha) / (dist * dist);
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            ni.vx -= fx;
            ni.vy -= fy;
            nj.vx += fx;
            nj.vy += fy;
          }
        }

        // 胡克引力：沿边
        for (const edge of simEdges) {
          const src = simNodes.find(n => n.id === edge.source);
          const tgt = simNodes.find(n => n.id === edge.target);
          if (!src || !tgt) continue;
          const dx = tgt.x - src.x;
          const dy = tgt.y - src.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 1) continue;
          const force = dist * SIM.attraction * alpha * (edge.weight || 1);
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          src.vx += fx;
          src.vy += fy;
          tgt.vx -= fx;
          tgt.vy -= fy;
        }

        // 中心引力
        for (const node of simNodes) {
          node.vx -= node.x * SIM.centerGravity * alpha;
          node.vy -= node.y * SIM.centerGravity * alpha;
        }

        // 更新位置
        for (const node of simNodes) {
          if (node.fx !== undefined && node.fy !== undefined) {
            node.x = node.fx;
            node.y = node.fy;
            node.vx = 0;
            node.vy = 0;
            continue;
          }
          node.vx *= SIM.damping;
          node.vy *= SIM.damping;
          node.x += node.vx;
          node.y += node.vy;
        }

        alphaRef.current *= SIM.alphaDecay;
      }

      // ── 渲染 ──
      const { width, height } = canvas;
      const dpr = window.devicePixelRatio || 1;
      ctx.clearRect(0, 0, width, height);
      ctx.save();

      // 应用变换
      const tx = transformRef.current;
      ctx.translate(width / 2 + tx.x * dpr, height / 2 + tx.y * dpr);
      ctx.scale(tx.scale * dpr, tx.scale * dpr);

      // 获取过滤后的节点 ID 集合
      const filteredIds = new Set(filteredNodes.map(n => n.id));
      const hasHighlight = highlightIds.size > 0;

      // 绘制边
      for (const edge of simEdges) {
        if (!filteredIds.has(edge.source) || !filteredIds.has(edge.target)) continue;
        const src = simNodes.find(n => n.id === edge.source);
        const tgt = simNodes.find(n => n.id === edge.target);
        if (!src || !tgt) continue;

        const isHighlighted = hasHighlight && highlightIds.has(edge.source) && highlightIds.has(edge.target);
        const isDimmed = hasHighlight && !isHighlighted;

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);
        ctx.strokeStyle = isDimmed
          ? 'rgba(128,128,128,0.05)'
          : isHighlighted
            ? `rgba(176, 125, 130, ${0.3 + (edge.weight || 0.5) * 0.4})`
            : `rgba(128,128,128,${0.08 + (edge.weight || 0.5) * 0.12})`;
        ctx.lineWidth = isHighlighted ? 1.5 : 0.8;
        ctx.stroke();
      }

      // 绘制节点
      for (const node of simNodes) {
        if (!filteredIds.has(node.id)) continue;

        const isHighlighted = hasHighlight && highlightIds.has(node.id);
        const isDimmed = hasHighlight && !isHighlighted;
        const isSelected = selectedNode?.id === node.id;
        const isHovered = hoveredNode?.id === node.id;

        const baseColor = showClusters
          ? (clusters.find(c => c.node_ids.includes(node.id))?.color || TYPE_COLORS[node.type] || '#999')
          : (TYPE_COLORS[node.type] || '#999');

        const radius = Math.max(3, node.size * 1.5);

        // 光晕效果（选中/悬停）
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, radius + 6, 0, Math.PI * 2);
          ctx.fillStyle = baseColor + '30';
          ctx.fill();
        }

        // 节点圆
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = isDimmed ? baseColor + '20' : baseColor;
        ctx.fill();

        if (isSelected) {
          ctx.strokeStyle = '#fff';
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // 标签
        if (tx.scale > 0.4 || isHighlighted || isSelected) {
          const fontSize = Math.max(8, 11 / tx.scale);
          ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          const label = node.label.length > 18 ? node.label.slice(0, 16) + '…' : node.label;
          const textY = node.y + radius + 3;
          // 文字背景
          const tw = ctx.measureText(label).width;
          ctx.fillStyle = isDimmed ? 'rgba(0,0,0,0.1)' : 'rgba(0,0,0,0.5)';
          ctx.fillRect(node.x - tw / 2 - 2, textY - 1, tw + 4, fontSize + 2);
          // 文字
          ctx.fillStyle = isDimmed ? 'rgba(255,255,255,0.2)' : '#fff';
          ctx.fillText(label, node.x, textY);
        }
      }

      ctx.restore();
      animFrameRef.current = requestAnimationFrame(simLoop);
    };

    animFrameRef.current = requestAnimationFrame(simLoop);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [filteredNodes, filteredEdges, highlightIds, selectedNode, hoveredNode, showClusters, clusters]);

  // ── Canvas 尺寸自适应 ──
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      canvas.style.width = `${rect.width}px`;
      canvas.style.height = `${rect.height}px`;
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  // ── 坐标转换 ──
  const screenToWorld = useCallback((sx: number, sy: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const tx = transformRef.current;
    const dpr = window.devicePixelRatio || 1;
    return {
      x: (sx - canvas.width / 2 / dpr - tx.x) / tx.scale,
      y: (sy - canvas.height / 2 / dpr - tx.y) / tx.scale,
    };
  }, []);

  const findNodeAt = useCallback((sx: number, sy: number) => {
    const { x, y } = screenToWorld(sx, sy);
    const filteredIds = new Set(filteredNodes.map(n => n.id));
    // 反向遍历（后绘制的在上面）
    for (let i = simNodesRef.current.length - 1; i >= 0; i--) {
      const node = simNodesRef.current[i];
      if (!filteredIds.has(node.id)) continue;
      const radius = Math.max(3, node.size * 1.5) + 4;
      const dx = node.x - x;
      const dy = node.y - y;
      if (dx * dx + dy * dy < radius * radius) return node;
    }
    return null;
  }, [screenToWorld, filteredNodes]);

  // ── 鼠标事件 ──
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const node = findNodeAt(sx, sy);
    if (node) {
      dragRef.current = { nodeId: node.id, startX: e.clientX, startY: e.clientY, isPanning: false };
      node.fx = node.x;
      node.fy = node.y;
      alphaRef.current = Math.max(alphaRef.current, 0.3);
    } else {
      dragRef.current = { nodeId: null, startX: e.clientX, startY: e.clientY, isPanning: true };
    }
  }, [findNodeAt]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;

    if (dragRef.current.nodeId) {
      // 拖拽节点
      const node = simNodesRef.current.find(n => n.id === dragRef.current.nodeId);
      if (node) {
        const { x, y } = screenToWorld(sx, sy);
        node.fx = x;
        node.fy = y;
        node.x = x;
        node.y = y;
      }
    } else if (dragRef.current.isPanning) {
      // 平移画布
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      transformRef.current.x += dx;
      transformRef.current.y += dy;
      dragRef.current.startX = e.clientX;
      dragRef.current.startY = e.clientY;
    } else {
      // 悬停检测
      const node = findNodeAt(sx, sy);
      setHoveredNode(node);
      if (canvasRef.current) {
        canvasRef.current.style.cursor = node ? 'pointer' : 'grab';
      }
    }
  }, [findNodeAt, screenToWorld]);

  const handleMouseUp = useCallback(() => {
    if (dragRef.current.nodeId) {
      const node = simNodesRef.current.find(n => n.id === dragRef.current.nodeId);
      if (node) {
        delete node.fx;
        delete node.fy;
      }
    }
    dragRef.current = { nodeId: null, startX: 0, startY: 0, isPanning: false };
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    transformRef.current.scale = Math.max(0.1, Math.min(5, transformRef.current.scale * delta));
  }, []);

  const handleClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = (e.target as HTMLCanvasElement).getBoundingClientRect();
    const sx = e.clientX - rect.left;
    const sy = e.clientY - rect.top;
    const node = findNodeAt(sx, sy);
    if (node) {
      setSelectedNode(node);
      // 加载邻居数据
      knowledgeGraphApi.getNeighbors(node.id).then(setNeighborData).catch(() => {});
    } else {
      setSelectedNode(null);
      setNeighborData(null);
    }
  }, [findNodeAt]);

  // ── 操作方法 ──
  const handleResetLayout = useCallback(() => {
    simNodesRef.current.forEach(n => {
      n.x = (Math.random() - 0.5) * 600;
      n.y = (Math.random() - 0.5) * 600;
      n.vx = 0;
      n.vy = 0;
      delete n.fx;
      delete n.fy;
    });
    alphaRef.current = 1.0;
    transformRef.current = { x: 0, y: 0, scale: 1 };
  }, []);

  const handleZoomIn = useCallback(() => {
    transformRef.current.scale = Math.min(5, transformRef.current.scale * 1.3);
  }, []);

  const handleZoomOut = useCallback(() => {
    transformRef.current.scale = Math.max(0.1, transformRef.current.scale / 1.3);
  }, []);

  const handleFindPath = useCallback(async () => {
    if (!pathSearchFrom || !pathSearchTo.trim()) return;
    setPathLoading(true);
    try {
      const result = await knowledgeGraphApi.findPaths(pathSearchFrom, pathSearchTo.trim(), 5);
      setPathResult(result);
    } catch {
      setPathResult(null);
    } finally {
      setPathLoading(false);
    }
  }, [pathSearchFrom, pathSearchTo]);

  // ── 统计 ──
  const stats = useMemo(() => ({
    nodes: filteredNodes.length,
    edges: filteredEdges.length,
    clusters: clusters.length,
    byType: filteredNodes.reduce((acc, n) => {
      acc[n.type] = (acc[n.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
  }), [filteredNodes, filteredEdges, clusters]);

  // ── 渲染 ──
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)' }}>
      {/* ── 顶部控制栏 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
        borderBottom: '1px solid var(--hairline)', background: 'var(--glass-bg)',
        backdropFilter: 'blur(var(--glass-blur))', flexWrap: 'wrap',
      }}>
        {/* 搜索 */}
        <Search size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} />
        <input
          type="text"
          placeholder="搜索节点..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{
            width: 120, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
            borderRadius: 4, padding: '3px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
          }}
        />

        {/* 类型筛选 */}
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <Filter size={12} style={{ color: 'var(--mute)' }} />
          {Object.entries(TYPE_LABELS).map(([type, label]) => (
            <label key={type} style={{
              display: 'flex', alignItems: 'center', gap: 2, fontSize: 10,
              cursor: 'pointer', color: nodeTypeFilter[type] ? TYPE_COLORS[type] : 'var(--mute)',
            }}>
              <input
                type="checkbox"
                checked={nodeTypeFilter[type] !== false}
                onChange={e => setNodeTypeFilter(prev => ({ ...prev, [type]: e.target.checked }))}
                style={{ width: 10, height: 10, accentColor: TYPE_COLORS[type] }}
              />
              {label}
            </label>
          ))}
        </div>

        {/* 最大节点数 */}
        <label style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 10, color: 'var(--mute)' }}>
          节点数
          <input
            type="range" min={50} max={500} step={10} value={maxNodes}
            onChange={e => setMaxNodes(Number(e.target.value))}
            style={{ width: 60, accentColor: 'var(--accent)' }}
          />
          {maxNodes}
        </label>

        {/* 最小连接数 */}
        <label style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 10, color: 'var(--mute)' }}>
          连接≥
          <input
            type="range" min={0} max={10} step={1} value={minConnections}
            onChange={e => setMinConnections(Number(e.target.value))}
            style={{ width: 50, accentColor: 'var(--accent)' }}
          />
          {minConnections}
        </label>

        {/* 社区检测开关 */}
        <button
          onClick={() => setShowClusters(v => !v)}
          title="社区检测"
          style={{
            display: 'flex', alignItems: 'center', gap: 3, padding: '2px 8px',
            borderRadius: 4, border: `1px solid ${showClusters ? 'var(--accent)' : 'var(--hairline)'}`,
            background: showClusters ? 'var(--accent-bg-soft)' : 'transparent',
            color: showClusters ? 'var(--accent)' : 'var(--mute)',
            cursor: 'pointer', fontSize: 10, whiteSpace: 'nowrap',
          }}
        >
          <Layers size={11} />
          社区
        </button>

        {/* 布局重置 */}
        <button onClick={handleResetLayout} title="重置布局" style={{
          background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)',
        }}><RotateCcw size={14} /></button>

        {/* 缩放 */}
        <button onClick={handleZoomIn} title="放大" style={{
          background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)',
        }}><ZoomIn size={14} /></button>
        <button onClick={handleZoomOut} title="缩小" style={{
          background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)',
        }}><ZoomOut size={14} /></button>
      </div>

      {/* ── 主区域 ── */}
      <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
        {/* Canvas */}
        <div ref={containerRef} style={{ flex: 1, position: 'relative' }}>
          {loading ? (
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              height: '100%', color: 'var(--mute)', fontSize: 13, gap: 8,
            }}>
              <Loader2 size={16} className="animate-spin" />
              加载知识图谱中...
            </div>
          ) : error ? (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              height: '100%', color: 'var(--danger)', fontSize: 13, gap: 8, padding: 20,
            }}>
              <span>{error}</span>
              <button onClick={loadGraph} style={{
                padding: '4px 12px', borderRadius: 4, border: '1px solid var(--danger)',
                background: 'transparent', color: 'var(--danger)', cursor: 'pointer', fontSize: 11,
              }}>重试</button>
            </div>
          ) : (
            <canvas
              ref={canvasRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              onWheel={handleWheel}
              onClick={handleClick}
              style={{ display: 'block', width: '100%', height: '100%', cursor: 'grab' }}
            />
          )}

          {/* ── 图例（左下角） ── */}
          <div style={{
            position: 'absolute', left: 10, bottom: 10,
            background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))',
            border: '1px solid var(--hairline)', borderRadius: 6,
            padding: '6px 10px', fontSize: 10, color: 'var(--body)',
            boxShadow: 'var(--glass-shadow-sm)',
          }}>
            <div style={{ fontWeight: 600, marginBottom: 4, fontSize: 10 }}>图例</div>
            {Object.entries(TYPE_LABELS).map(([type, label]) => (
              <div key={type} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: TYPE_COLORS[type], display: 'inline-block',
                }} />
                <span>{label}</span>
              </div>
            ))}
            {showClusters && clusters.length > 0 && (
              <div style={{ borderTop: '1px solid var(--hairline)', marginTop: 4, paddingTop: 4 }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>社区</div>
                {clusters.slice(0, 5).map(c => (
                  <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 1 }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: c.color, display: 'inline-block',
                    }} />
                    <span>{c.label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ── 统计（右下角） ── */}
          <div style={{
            position: 'absolute', right: selectedNode ? 280 : 10, bottom: 10,
            background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))',
            border: '1px solid var(--hairline)', borderRadius: 6,
            padding: '6px 10px', fontSize: 10, color: 'var(--mute)',
            boxShadow: 'var(--glass-shadow-sm)',
          }}>
            <span>{stats.nodes} 节点</span>
            <span style={{ margin: '0 6px' }}>·</span>
            <span>{stats.edges} 边</span>
            {stats.clusters > 0 && (
              <>
                <span style={{ margin: '0 6px' }}>·</span>
                <span>{stats.clusters} 社区</span>
              </>
            )}
          </div>
        </div>

        {/* ── 右侧详情面板 ── */}
        {selectedNode && (
          <div style={{
            width: 260, borderLeft: '1px solid var(--hairline)',
            background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))',
            overflowY: 'auto', fontSize: 12, color: 'var(--body)',
            display: 'flex', flexDirection: 'column',
          }}>
            {/* 节点标题 */}
            <div style={{
              padding: '10px 12px', borderBottom: '1px solid var(--hairline)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
            }}>
              <div style={{ flex: 1, marginRight: 8 }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, lineHeight: 1.3 }}>
                  {selectedNode.label}
                </div>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', gap: 3,
                  padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                  background: TYPE_COLORS[selectedNode.type] + '20',
                  color: TYPE_COLORS[selectedNode.type],
                }}>
                  {TYPE_LABELS[selectedNode.type] || selectedNode.type}
                </span>
              </div>
              <button onClick={() => { setSelectedNode(null); setNeighborData(null); }} style={{
                background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0,
              }}><X size={14} /></button>
            </div>

            {/* 元数据 */}
            <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--hairline)' }}>
              {Object.entries(selectedNode.metadata).map(([key, value]) => {
                if (value === null || value === undefined || value === '' || value === 0) return null;
                const label = {
                  year: '年份', journal: '期刊', citation_count: '引用数', doi: 'DOI',
                  abstract: '摘要', name: '名称', paper_count: '论文数', h_index: 'H指数',
                  frequency: '频次', country: '国家', author_count: '作者数',
                }[key] || key;
                return (
                  <div key={key} style={{ marginBottom: 4, fontSize: 11 }}>
                    <span style={{ color: 'var(--mute)', marginRight: 6 }}>{label}:</span>
                    <span style={{ color: 'var(--body)' }}>
                      {key === 'abstract'
                        ? String(value).slice(0, 100) + (String(value).length > 100 ? '…' : '')
                        : String(value)}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* 连接节点列表 */}
            <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--hairline)', flex: 1, overflowY: 'auto' }}>
              <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 6, color: 'var(--mute)' }}>
                相关节点 ({neighborData?.neighbors.length || 0})
              </div>
              {(neighborData?.neighbors || []).slice(0, 20).map(n => (
                <div
                  key={n.id}
                  onClick={() => {
                    const simNode = simNodesRef.current.find(sn => sn.id === n.id);
                    if (simNode) {
                      setSelectedNode(simNode);
                      knowledgeGraphApi.getNeighbors(n.id).then(setNeighborData).catch(() => {});
                    }
                  }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0',
                    cursor: 'pointer', fontSize: 11,
                  }}
                >
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: TYPE_COLORS[n.type] || '#999', flexShrink: 0,
                  }} />
                  <span style={{
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    color: 'var(--body)',
                  }}>
                    {n.label}
                  </span>
                  <ChevronRight size={10} style={{ color: 'var(--mute)', flexShrink: 0, marginLeft: 'auto' }} />
                </div>
              ))}
            </div>

            {/* 路径搜索 */}
            <div style={{ padding: '8px 12px', borderTop: '1px solid var(--hairline)' }}>
              <div style={{ fontWeight: 600, fontSize: 11, marginBottom: 6, color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Route size={11} />
                查找路径
              </div>
              <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4 }}>
                从 <span style={{ color: 'var(--accent)' }}>{selectedNode.label.slice(0, 15)}</span> 到:
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                <input
                  type="text"
                  placeholder="目标节点 ID"
                  value={pathSearchTo}
                  onChange={e => setPathSearchTo(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { setPathSearchFrom(selectedNode.id); handleFindPath(); } }}
                  style={{
                    flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                    borderRadius: 4, padding: '3px 6px', fontSize: 10, color: 'var(--body)', outline: 'none',
                  }}
                />
                <button
                  onClick={() => { setPathSearchFrom(selectedNode.id); handleFindPath(); }}
                  disabled={pathLoading || !pathSearchTo.trim()}
                  style={{
                    padding: '3px 8px', borderRadius: 4, border: 'none',
                    background: 'var(--accent)', color: '#fff', cursor: 'pointer',
                    fontSize: 10, opacity: pathLoading || !pathSearchTo.trim() ? 0.5 : 1,
                  }}
                >
                  {pathLoading ? <Loader2 size={10} className="animate-spin" /> : <Map size={10} />}
                </button>
              </div>
              {pathResult && (
                <div style={{ marginTop: 6, fontSize: 10 }}>
                  {pathResult.found ? (
                    <div style={{ color: 'var(--success)' }}>
                      找到 {pathResult.paths.length} 条路径
                      {pathResult.paths[0] && (
                        <span style={{ color: 'var(--mute)' }}> (最短 {pathResult.paths[0].length} 步)</span>
                      )}
                    </div>
                  ) : (
                    <div style={{ color: 'var(--danger)' }}>未找到路径</div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgeGraphPanel;
