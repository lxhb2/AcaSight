import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Loader2, Brain, Lightbulb, Download, CheckSquare, Square,
  Sparkles,
} from 'lucide-react';
import { papersApi } from '@/services/api';
import type { PaperItem } from '@/services/api';

export const BrainstormView: React.FC = () => {
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [focus, setFocus] = useState('');
  const [generating, setGenerating] = useState(false);
  const [content, setContent] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const res = await papersApi.list({ page_size: 100, sort_by: 'created_at', sort_order: 'desc' });
        if (!cancelled && mountedRef.current) setPapers(res.items || []);
      } catch {
        if (!cancelled && mountedRef.current) setPapers([]);
      } finally {
        if (!cancelled && mountedRef.current) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; mountedRef.current = false; };
  }, []);

  const togglePaper = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const handleGenerate = useCallback(async () => {
    if (selectedIds.size < 2) return;
    setGenerating(true);
    setContent('');
    try {
      const response = await fetch('/api/brainstorm/generate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: Array.from(selectedIds), focus: focus || null }),
      });
      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'chunk') {
                setContent(prev => prev + data.content);
              } else if (data.type === 'complete') {
                setContent(data.content);
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (e) {
              if (e instanceof Error && e.message !== 'Unexpected') throw e;
            }
          }
        }
      }
    } catch (err) {
      alert('头脑风暴生成失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) setGenerating(false);
    }
  }, [selectedIds, focus]);

  const handleExport = useCallback(() => {
    if (!content) return;
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `头脑风暴_${focus || '选题'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [content, focus]);

  const filteredPapers = searchQuery
    ? papers.filter(p => (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()))
    : papers;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{
        width: 260, minWidth: 200, borderRight: '1px solid var(--hairline)',
        display: 'flex', flexDirection: 'column', background: 'var(--canvas-soft)',
      }}>
        <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <Lightbulb size={14} style={{ color: '#f59e0b' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>AI白板头脑风暴</span>
          </div>
          <input
            type="text" placeholder="搜索论文..." value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%', background: 'var(--bg-2)', border: '1px solid var(--hairline)',
              borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
        <div style={{ padding: '4px 10px', fontSize: 10, color: 'var(--mute)' }}>
          已选 {selectedIds.size} 篇（至少2篇）
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading && <div style={{ padding: 16, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}><Loader2 size={14} className="animate-spin" style={{ display: 'inline', marginRight: 4 }} />加载中...</div>}
          {!loading && filteredPapers.map(paper => (
            <div
              key={paper.id}
              onClick={() => togglePaper(paper.id)}
              style={{
                padding: '6px 10px', cursor: 'pointer', fontSize: 11,
                background: selectedIds.has(paper.id) ? 'var(--accent-bg-soft)' : 'transparent',
                borderBottom: '1px solid var(--hairline)',
                display: 'flex', alignItems: 'flex-start', gap: 6,
              }}
            >
              {selectedIds.has(paper.id) ? <CheckSquare size={12} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 2 }} /> : <Square size={12} style={{ color: 'var(--mute)', flexShrink: 0, marginTop: 2 }} />}
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: selectedIds.has(paper.id) ? 'var(--accent)' : 'var(--body)' }}>
                {paper.title}
              </div>
            </div>
          ))}
        </div>
        <div style={{ padding: '8px 10px', borderTop: '1px solid var(--hairline)' }}>
          <input
            type="text" placeholder="聚焦方向（可选）" value={focus}
            onChange={e => setFocus(e.target.value)}
            style={{
              width: '100%', background: 'var(--bg-2)', border: '1px solid var(--hairline)',
              borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{
          padding: '8px 16px', borderBottom: '1px solid var(--hairline)',
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--glass-bg, var(--bg-2))',
        }}>
          <Brain size={14} style={{ color: '#f59e0b' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>科研选题头脑风暴</span>
          <div style={{ flex: 1 }} />
          {content && (
            <button onClick={handleExport} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', fontSize: 10, borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer' }}>
              <Download size={10} /> 导出
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating || selectedIds.size < 2}
            style={{
              display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
              fontSize: 10, borderRadius: 4, border: 'none',
              background: '#f59e0b', color: '#fff', cursor: generating ? 'wait' : 'pointer',
              opacity: generating || selectedIds.size < 2 ? 0.5 : 1,
            }}
          >
            {generating ? <Loader2 size={10} className="animate-spin" /> : <Sparkles size={10} />}
            {generating ? '生成中...' : '开始头脑风暴'}
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {!content && !generating && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)' }}>
              <Lightbulb size={40} style={{ opacity: 0.15, marginBottom: 12 }} />
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>AI白板头脑风暴</div>
              <div style={{ fontSize: 11, textAlign: 'center', lineHeight: 1.6 }}>
                选择2篇以上文献，AI将横向对比<br />挖掘研究空白，生成选题思路
              </div>
            </div>
          )}
          {generating && !content && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)' }}>
              <Loader2 size={24} className="animate-spin" style={{ marginBottom: 8, color: '#f59e0b' }} />
              <div style={{ fontSize: 12 }}>正在分析文献，生成选题思路...</div>
            </div>
          )}
          {content && (
            <div style={{
              fontSize: 13, lineHeight: 1.8, color: 'var(--body)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {content}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
