/**
 * GraphView — 引用可视化图谱 (Chapter H 重写)
 *
 * 使用 react-force-graph-2d 实现力导向图。
 * 数据来自后端 /api/knowledge/graph。
 * 支持节点展开/收缩、拖拽、搜索结果联动。
 * 支持本地文献+搜索文献合并关联。
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Search, ZoomIn, ZoomOut, RotateCcw, Info, X, ExternalLink, Globe, FileText } from 'lucide-react';
import { useApp } from '@/contexts/AppContext';

interface GraphNode {
  id: string;
  label: string;
  title: string;
  year: number | null;
  journal: string | null;
  citation_count: number;
  authors: string[];
  doi: string | null;
  tags: string[];
  is_favorite: boolean;
  group: string;
  source_type?: 'local' | 'online';
  x?: number;
  y?: number;
  val?: number;
  color?: string;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  tags?: string[];
}

const GROUP_COLORS: Record<string, string> = {};
const PALETTE = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
];

const ONLINE_COLOR = '#f97316';

function getGroupColor(group: string): string {
  if (group === 'online') return ONLINE_COLOR;
  if (!GROUP_COLORS[group]) {
    GROUP_COLORS[group] = PALETTE[Object.keys(GROUP_COLORS).length % PALETTE.length];
  }
  return GROUP_COLORS[group];
}

export const GraphView: React.FC = () => {
  const { openFile } = useApp();
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [includeSearch, setIncludeSearch] = useState(true);
  const [stats, setStats] = useState({ total_papers: 0, with_doi: 0, with_tags: 0, online_papers: 0 });
  const fgRef = useRef<any>(null);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      const url = `http://localhost:9000/api/knowledge/graph?include_search=${includeSearch}`;
      const resp = await fetch(url);
      if (resp.ok) {
        const data = await resp.json();
        const nodes = (data.nodes || []).map((n: GraphNode) => ({
          ...n,
          val: Math.max(3, Math.min(20, (n.citation_count || 0) / 10 + 3)),
          color: getGroupColor(n.group),
        }));
        setGraphData({ nodes, links: data.links || [] });
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [includeSearch]);

  const loadStats = useCallback(async () => {
    try {
      const resp = await fetch(`http://localhost:9000/api/knowledge/graph/stats?include_search=${includeSearch}`);
      if (resp.ok) setStats(await resp.json());
    } catch { /* ignore */ }
  }, [includeSearch]);

  useEffect(() => { loadGraph(); loadStats(); }, [loadGraph, loadStats]);

  const filteredData = useMemo(() => {
    if (!searchQuery.trim()) return graphData;
    const q = searchQuery.toLowerCase();
    const matchIds = new Set(
      graphData.nodes
        .filter(n => n.label.toLowerCase().includes(q) || (n.tags || []).some(t => t.toLowerCase().includes(q)))
        .map(n => n.id)
    );
    graphData.links.forEach(l => {
      const src = typeof l.source === 'string' ? l.source : l.source.id;
      const tgt = typeof l.target === 'string' ? l.target : l.target.id;
      if (matchIds.has(src)) matchIds.add(tgt);
      if (matchIds.has(tgt)) matchIds.add(src);
    });
    return {
      nodes: graphData.nodes.filter(n => matchIds.has(n.id)),
      links: graphData.links.filter(l => {
        const src = typeof l.source === 'string' ? l.source : l.source.id;
        const tgt = typeof l.target === 'string' ? l.target : l.target.id;
        return matchIds.has(src) && matchIds.has(tgt);
      }),
    };
  }, [graphData, searchQuery]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
    const connected = new Set<string>([node.id]);
    graphData.links.forEach(l => {
      const src = typeof l.source === 'string' ? l.source : l.source.id;
      const tgt = typeof l.target === 'string' ? l.target : l.target.id;
      if (src === node.id) connected.add(tgt);
      if (tgt === node.id) connected.add(src);
    });
    setHighlightNodes(connected);
  }, [graphData]);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
  }, []);

  const handleOpenPaper = useCallback((node: GraphNode) => {
    const paperId = parseInt(node.id.replace('paper-', ''));
    if (!isNaN(paperId)) {
      openFile(node.title + '.pdf', 'pdf', { abstract: undefined, authors: (node.authors || []).join(', ') || undefined, year: node.year || undefined, journal: node.journal || undefined });
    }
  }, [openFile]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px', borderBottom: '1px solid var(--hairline)' }}>
        <Search size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} />
        <input
          type="text"
          placeholder="搜索论文/标签..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          style={{ flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)', borderRadius: 4, padding: '3px 8px', fontSize: 11, color: 'var(--body)', outline: 'none' }}
        />
        <button
          onClick={() => setIncludeSearch(v => !v)}
          title={includeSearch ? '包含搜索文献' : '仅本地文献'}
          style={{
            display: 'flex', alignItems: 'center', gap: 3, padding: '2px 8px',
            borderRadius: 4, border: `1px solid ${includeSearch ? ONLINE_COLOR : 'var(--hairline)'}`,
            background: includeSearch ? 'rgba(249,115,22,0.1)' : 'transparent',
            color: includeSearch ? ONLINE_COLOR : 'var(--mute)',
            cursor: 'pointer', fontSize: 10, whiteSpace: 'nowrap',
          }}
        >
          <Globe size={11} />
          {includeSearch ? '含搜索' : '仅本地'}
        </button>
        <button onClick={() => { if (fgRef.current) fgRef.current.zoom(1.3, 300); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)' }}><ZoomIn size={14} /></button>
        <button onClick={() => { if (fgRef.current) fgRef.current.zoom(0.7, 300); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)' }}><ZoomOut size={14} /></button>
        <button onClick={() => { if (fgRef.current) fgRef.current.recenter(); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)' }}><RotateCcw size={14} /></button>
        <span style={{ fontSize: 10, color: 'var(--mute)' }}>{graphData.nodes.length} 节点 · {graphData.links.length} 连线</span>
      </div>

      {/* Graph */}
      <div style={{ flex: 1, position: 'relative' }}>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)', fontSize: 13 }}>
            加载图谱数据中...
          </div>
        ) : filteredData.nodes.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)', fontSize: 13 }}>
            <Info size={32} style={{ marginBottom: 8, opacity: 0.3 }} />
            暂无图谱数据<br />
            <span style={{ fontSize: 11 }}>导入论文后自动构建引用关系</span>
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={filteredData}
            nodeId="id"
            nodeLabel="label"
            nodeVal="val"
            nodeColor={n => highlightNodes.size > 0 ? (highlightNodes.has(n.id) ? (n as GraphNode).color || '#666' : 'rgba(128,128,128,0.15)') : (n as GraphNode).color || '#666'}
            nodeRelSize={4}
            nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
              const label = node.label.length > 20 ? node.label.slice(0, 18) + '…' : node.label;
              const fontSize = Math.max(8, 12 / globalScale);
              ctx.font = `${fontSize}px Sans-Serif`;
              const textWidth = ctx.measureText(label).width;
              const bgPadding = fontSize * 0.3;
              ctx.fillStyle = node.source_type === 'online' ? 'rgba(249,115,22,0.6)' : 'rgba(0,0,0,0.5)';
              ctx.fillRect(node.x - textWidth / 2 - bgPadding, node.y - fontSize / 2 - bgPadding, textWidth + bgPadding * 2, fontSize + bgPadding * 2);
              ctx.fillStyle = highlightNodes.size > 0 && !highlightNodes.has(node.id) ? 'rgba(200,200,200,0.3)' : '#fff';
              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillText(label, node.x, node.y);
            }}
            linkColor={l => {
              const type = (l as GraphLink).type;
              if (type === 'cites') return 'rgba(99,102,241,0.4)';
              if (type === 'shared_tag') return 'rgba(16,185,129,0.3)';
              return 'rgba(128,128,128,0.2)';
            }}
            linkWidth={l => (l as GraphLink).type === 'cites' ? 1.5 : 0.8}
            linkDirectionalArrowLength={l => (l as GraphLink).type === 'cites' ? 4 : 0}
            linkDirectionalArrowRelPos={0.9}
            linkCurvature={0.1}
            onNodeClick={handleNodeClick}
            onBackgroundClick={handleBackgroundClick}
            cooldownTicks={100}
            enableNodeDrag={true}
            warmupTicks={50}
          />
        )}

        {/* Node Detail Panel */}
        {selectedNode && (
          <div style={{
            position: 'absolute', right: 10, top: 10, width: 260,
            background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))',
            WebkitBackdropFilter: 'blur(var(--glass-blur))',
            border: '1px solid var(--hairline)', borderRadius: 8,
            padding: 12, fontSize: 12, color: 'var(--body)',
            boxShadow: 'var(--glass-shadow)', zIndex: 10,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontWeight: 600, fontSize: 13, flex: 1, marginRight: 8, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {selectedNode.title}
              </span>
              <button onClick={() => { setSelectedNode(null); setHighlightNodes(new Set()); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0 }}><X size={12} /></button>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 3,
                padding: '1px 6px', borderRadius: 3, fontSize: 9, fontWeight: 600,
                background: selectedNode.source_type === 'online' ? 'rgba(249,115,22,0.15)' : 'rgba(99,102,241,0.1)',
                color: selectedNode.source_type === 'online' ? ONLINE_COLOR : '#6366f1',
              }}>
                {selectedNode.source_type === 'online' ? <Globe size={9} /> : <FileText size={9} />}
                {selectedNode.source_type === 'online' ? '在线文献' : '本地文献'}
              </span>
            </div>
            {selectedNode.authors && selectedNode.authors.length > 0 && (
              <div style={{ color: 'var(--mute)', marginBottom: 4, fontSize: 11 }}>
                {selectedNode.authors.join(', ')}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, color: 'var(--mute)', marginBottom: 6, fontSize: 11 }}>
              {selectedNode.journal && <span>{selectedNode.journal}</span>}
              {selectedNode.year && <span>{selectedNode.year}</span>}
              {selectedNode.citation_count > 0 && <span>引用 {selectedNode.citation_count}</span>}
            </div>
            {selectedNode.tags && selectedNode.tags.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, marginBottom: 6 }}>
                {selectedNode.tags.map(t => (
                  <span key={t} style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: getGroupColor(t) + '20', color: getGroupColor(t) }}>#{t}</span>
                ))}
              </div>
            )}
            {selectedNode.doi && (
              <div style={{ fontSize: 10, color: 'var(--accent)', marginBottom: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                DOI: {selectedNode.doi}
              </div>
            )}
            <button
              onClick={() => handleOpenPaper(selectedNode)}
              style={{ width: '100%', padding: '4px 0', borderRadius: 4, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
            >
              <ExternalLink size={10} /> 打开论文
            </button>
          </div>
        )}
      </div>

      {/* Stats bar */}
      <div style={{ padding: '4px 10px', borderTop: '1px solid var(--hairline)', display: 'flex', gap: 12, fontSize: 10, color: 'var(--mute)' }}>
        <span>共 {stats.total_papers} 篇</span>
        <span>DOI {stats.with_doi}</span>
        <span>标签 {stats.with_tags}</span>
        {includeSearch && stats.online_papers > 0 && (
          <span style={{ color: ONLINE_COLOR }}>在线 {stats.online_papers}</span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: 9 }}>
          <span style={{ color: '#6366f1' }}>●</span> 引用{' '}
          <span style={{ color: '#10b981' }}>●</span> 同标签
          {includeSearch && <>{' '}<span style={{ color: ONLINE_COLOR }}>●</span> 在线</>}
        </span>
      </div>
    </div>
  );
};
