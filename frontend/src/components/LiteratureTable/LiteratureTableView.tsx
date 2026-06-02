import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Loader2, Table2, Download, Plus, X,
  Brain, Check, Square, CheckSquare,
} from 'lucide-react';
import { papersApi, literatureTableApi } from '@/services/api';
import type { PaperItem } from '@/services/api';

const DEFAULT_COLUMNS = [
  { key: 'title', label: '标题', source: 'metadata' },
  { key: 'authors', label: '作者', source: 'metadata' },
  { key: 'year', label: '年份', source: 'metadata' },
  { key: 'purpose', label: '研究目的', source: '11维度' },
  { key: 'method', label: '研究方法', source: '11维度' },
  { key: 'results', label: '主要结果', source: '11维度' },
  { key: 'innovation', label: '创新点', source: '11维度' },
  { key: 'limitations', label: '局限性', source: '11维度' },
];

export const LiteratureTableView: React.FC = () => {
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [columns, setColumns] = useState(DEFAULT_COLUMNS);
  const [tableData, setTableData] = useState<Array<Record<string, unknown>> | null>(null);
  const [tableColumns, setTableColumns] = useState(DEFAULT_COLUMNS);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [newColumnName, setNewColumnName] = useState('');
  const [showAddColumn, setShowAddColumn] = useState(false);
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
    if (selectedIds.size === 0) return;
    setGenerating(true);
    setTableData(null);
    try {
      const colKeys = columns.map(c => c.key);
      const res = await literatureTableApi.generate(Array.from(selectedIds), colKeys);
      if (mountedRef.current) {
        setTableData(res.data);
        setTableColumns(res.columns);
      }
    } catch (err) {
      alert('生成表格失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) setGenerating(false);
    }
  }, [selectedIds, columns]);

  const handleExport = useCallback(async () => {
    if (selectedIds.size === 0) return;
    try {
      const colKeys = columns.map(c => c.key);
      const response = await literatureTableApi.exportCsv(Array.from(selectedIds), colKeys);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'literature_table.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('导出失败: ' + (err instanceof Error ? err.message : String(err)));
    }
  }, [selectedIds, columns]);

  const handleAddColumn = useCallback(() => {
    if (!newColumnName.trim()) return;
    setColumns(prev => [...prev, { key: newColumnName.trim(), label: newColumnName.trim(), source: 'ai' }]);
    setNewColumnName('');
    setShowAddColumn(false);
  }, [newColumnName]);

  const handleRemoveColumn = useCallback((key: string) => {
    setColumns(prev => prev.filter(c => c.key !== key));
  }, []);

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
            <Table2 size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>文献对比表格</span>
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
          已选 {selectedIds.size} 篇
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
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 600 }}>列配置:</span>
          {columns.map(col => (
            <span key={col.key} style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 10, padding: '2px 6px', borderRadius: 3,
              background: col.source === 'ai' ? 'rgba(245,158,11,0.12)' : 'rgba(99,102,241,0.1)',
              color: col.source === 'ai' ? '#f59e0b' : 'var(--accent)',
            }}>
              {col.label}
              {col.source === 'ai' && <X size={10} style={{ cursor: 'pointer' }} onClick={() => handleRemoveColumn(col.key)} />}
            </span>
          ))}
          {showAddColumn ? (
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <input
                type="text" value={newColumnName}
                onChange={e => setNewColumnName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleAddColumn(); }}
                placeholder="AI列名称" autoFocus
                style={{ fontSize: 10, padding: '2px 6px', borderRadius: 3, border: '1px solid var(--hairline)', background: 'var(--bg-2)', color: 'var(--body)', width: 80, outline: 'none' }}
              />
              <Check size={12} style={{ cursor: 'pointer', color: '#10b981' }} onClick={handleAddColumn} />
              <X size={12} style={{ cursor: 'pointer', color: 'var(--mute)' }} onClick={() => { setShowAddColumn(false); setNewColumnName(''); }} />
            </div>
          ) : (
            <button onClick={() => setShowAddColumn(true)} style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: 10, padding: '2px 6px', borderRadius: 3, border: '1px dashed var(--hairline)', background: 'transparent', color: 'var(--mute)', cursor: 'pointer' }}>
              <Plus size={10} /> AI列
            </button>
          )}
          <div style={{ flex: 1 }} />
          {tableData && (
            <button onClick={handleExport} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', fontSize: 10, borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer' }}>
              <Download size={10} /> 导出CSV
            </button>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating || selectedIds.size === 0}
            style={{
              display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
              fontSize: 10, borderRadius: 4, border: 'none',
              background: 'var(--accent)', color: '#fff', cursor: generating ? 'wait' : 'pointer',
              opacity: generating || selectedIds.size === 0 ? 0.5 : 1,
            }}
          >
            {generating ? <Loader2 size={10} className="animate-spin" /> : <Brain size={10} />}
            {generating ? '生成中...' : '生成表格'}
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
          {!tableData && !generating && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)' }}>
              <Table2 size={40} style={{ opacity: 0.15, marginBottom: 12 }} />
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>文献对比表格</div>
              <div style={{ fontSize: 11, textAlign: 'center', lineHeight: 1.6 }}>
                从左侧选择论文，点击「生成表格」<br />
                基于11维度拆分数据自动填充
              </div>
            </div>
          )}
          {generating && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)' }}>
              <Loader2 size={24} className="animate-spin" style={{ marginBottom: 8 }} />
              <div style={{ fontSize: 12 }}>正在生成对比表格...</div>
            </div>
          )}
          {tableData && !generating && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
              <thead>
                <tr>
                  {tableColumns.map(col => (
                    <th key={col.key} style={{
                      padding: '6px 8px', textAlign: 'left', fontWeight: 600,
                      borderBottom: '2px solid var(--hairline)', color: 'var(--body)',
                      background: 'var(--bg-2)', whiteSpace: 'nowrap', position: 'sticky', top: 0,
                    }}>
                      {col.label}
                      {col.source === 'ai' && <span style={{ marginLeft: 4, fontSize: 8, color: '#f59e0b' }}>AI</span>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--hairline)' }}>
                    {tableColumns.map(col => (
                      <td key={col.key} style={{
                        padding: '6px 8px', color: 'var(--body)',
                        maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }} title={String(row[col.key] || '')}>
                        {String(row[col.key] || '—')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
