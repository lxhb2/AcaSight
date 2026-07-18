import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Loader2, RefreshCw, ChevronDown, ChevronRight,
  Brain, Trash2, Sparkles, Copy, CheckCircle2,
  Save, Eye, Database, Table2, Download, Plus, X,
  Check, Square, CheckSquare,
} from 'lucide-react';
import { papersApi, literatureTableApi } from '@/services/api';
import type { PaperItem } from '@/services/api';

const DIMENSION_KEYS = [
  'abstract',
  'research_background',
  'research_purpose',
  'research_status',
  'research_questions',
  'basic_theory',
  'research_methods',
  'results_and_evaluation',
  'innovation_points',
  'limitations_and_suggestions',
  'conclusions',
] as const;

const DIMENSION_LABELS: Record<string, string> = {
  abstract: '摘要',
  research_background: '研究背景',
  research_purpose: '研究目的与意义',
  research_status: '研究现状',
  research_questions: '研究问题',
  basic_theory: '基本理论',
  research_methods: '研究方法',
  results_and_evaluation: '结果与评价',
  innovation_points: '创新点',
  limitations_and_suggestions: '局限与建议',
  conclusions: '结论',
};

const DIMENSION_COLORS: Record<string, string> = {
  abstract: '#6366f1',
  research_background: '#8b5cf6',
  research_purpose: '#06b6d4',
  research_status: '#0ea5e9',
  research_questions: '#f59e0b',
  basic_theory: '#10b981',
  research_methods: '#14b8a6',
  results_and_evaluation: '#f97316',
  innovation_points: '#ec4899',
  limitations_and_suggestions: '#ef4444',
  conclusions: '#6366f1',
};

type DimensionSource = 'none' | 'database' | 'preview';
type DisplayMode = 'single' | 'compare';

type DimColumn = {
  key: string;
  label: string;
  source: string;
};

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

export const DimensionDisplayView: React.FC = () => {
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [mode, setMode] = useState<DisplayMode>('single');
  const [selectedPaperId, setSelectedPaperId] = useState<number | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const [dimensions, setDimensions] = useState<Record<string, string> | null>(null);
  const [dimSource, setDimSource] = useState<DimensionSource>('none');
  const [dimsLoading, setDimsLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const [columns, setColumns] = useState<DimColumn[]>(DEFAULT_COLUMNS);
  const [tableData, setTableData] = useState<Array<Record<string, unknown>> | null>(null);
  const [tableColumns, setTableColumns] = useState<DimColumn[]>(DEFAULT_COLUMNS);
  const [generating, setGenerating] = useState(false);
  const [newColumnName, setNewColumnName] = useState('');
  const [showAddColumn, setShowAddColumn] = useState(false);

  const initRef = useRef(false);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await papersApi.list({ page_size: 100, sort_by: 'created_at', sort_order: 'desc' });
        if (!cancelled) setPapers(res.items || []);
      } catch {
        if (!cancelled) setPapers([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, []);

  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const loadDimensionsFromDB = useCallback(async (paperId: number) => {
    setDimsLoading(true);
    setDimensions(null);
    setDimSource('none');
    try {
      const dims = await papersApi.getDimensions(paperId);
      if (mountedRef.current) {
        const dimMap: Record<string, string> = {};
        for (const k of DIMENSION_KEYS) {
          dimMap[k] = (dims as unknown as Record<string, unknown>)[k] as string || '';
        }
        setDimensions(dimMap);
        setDimSource('database');
        const filled = DIMENSION_KEYS.filter(k => dimMap[k]);
        setExpandedKeys(new Set(filled));
      }
    } catch {
      if (mountedRef.current) {
        setDimensions(null);
        setDimSource('none');
      }
    } finally {
      if (mountedRef.current) setDimsLoading(false);
    }
  }, []);

  const handleSelectPaper = useCallback((paperId: number) => {
    if (mode === 'single') {
      setSelectedPaperId(paperId);
      loadDimensionsFromDB(paperId);
    } else {
      setSelectedIds(prev => {
        const next = new Set(prev);
        if (next.has(paperId)) next.delete(paperId); else next.add(paperId);
        return next;
      });
    }
  }, [mode, loadDimensionsFromDB]);

  const handleModeChange = useCallback((newMode: DisplayMode) => {
    setMode(newMode);
    setDimensions(null);
    setDimSource('none');
    setTableData(null);
    setSelectedPaperId(null);
    setSelectedIds(new Set());
    setExpandedKeys(new Set());
  }, []);

  const handlePreviewExtract = useCallback(async () => {
    if (!selectedPaperId) return;
    setExtracting(true);
    try {
      const res = await papersApi.previewDimensions(selectedPaperId);
      if (mountedRef.current) {
        setDimensions(res.dimensions);
        setDimSource('preview');
        const filled = DIMENSION_KEYS.filter(k => res.dimensions[k]);
        setExpandedKeys(new Set(filled));
      }
    } catch (err) {
      alert('维度拆分失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) setExtracting(false);
    }
  }, [selectedPaperId]);

  const handleConfirmSave = useCallback(async () => {
    if (!selectedPaperId || !dimensions) return;
    setSaving(true);
    try {
      await papersApi.confirmDimensions(selectedPaperId, dimensions);
      if (mountedRef.current) {
        setDimSource('database');
      }
    } catch (err) {
      alert('保存失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) setSaving(false);
    }
  }, [selectedPaperId, dimensions]);

  const handleDirectExtract = useCallback(async () => {
    if (!selectedPaperId) return;
    setExtracting(true);
    try {
      await papersApi.createDimensions(selectedPaperId);
      await loadDimensionsFromDB(selectedPaperId);
    } catch (err) {
      alert('维度拆分失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) setExtracting(false);
    }
  }, [selectedPaperId, loadDimensionsFromDB]);

  const handleDeleteDimensions = useCallback(async () => {
    if (!selectedPaperId) return;
    try {
      await papersApi.deleteDimensions(selectedPaperId);
      if (mountedRef.current) {
        setDimensions(null);
        setDimSource('none');
        setExpandedKeys(new Set());
      }
    } catch { /* ignore */ }
  }, [selectedPaperId]);

  const toggleExpanded = useCallback((key: string) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const handleCopy = useCallback(async (key: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedKey(key);
      setTimeout(() => { if (mountedRef.current) setCopiedKey(null); }, 1500);
    } catch { /* ignore */ }
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
    ? papers.filter(p => (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()) || (p.authors || []).some(a => (a || '').toLowerCase().includes(searchQuery.toLowerCase())))
    : papers;

  const selectedPaper = papers.find(p => p.id === selectedPaperId);
  const filledCount = dimensions ? DIMENSION_KEYS.filter(k => dimensions[k]).length : 0;
  const progressPercent = dimensions ? Math.round((filledCount / 11) * 100) : 0;
  const isPreview = dimSource === 'preview';
  const isFromDB = dimSource === 'database';

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{
        width: 280, minWidth: 220, borderRight: '1px solid var(--hairline)',
        display: 'flex', flexDirection: 'column', background: 'var(--canvas-soft)',
      }}>
        <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <Table2 size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>11维度数据显示器</span>
          </div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
            <button
              onClick={() => handleModeChange('single')}
              style={{
                flex: 1, padding: '4px 0', fontSize: 10, borderRadius: 4, border: '1px solid',
                borderColor: mode === 'single' ? 'var(--accent)' : 'var(--hairline)',
                background: mode === 'single' ? 'var(--accent-bg-soft)' : 'transparent',
                color: mode === 'single' ? 'var(--accent)' : 'var(--mute)',
                cursor: 'pointer', fontWeight: 600,
              }}
            >
              单篇详情
            </button>
            <button
              onClick={() => handleModeChange('compare')}
              style={{
                flex: 1, padding: '4px 0', fontSize: 10, borderRadius: 4, border: '1px solid',
                borderColor: mode === 'compare' ? 'var(--accent)' : 'var(--hairline)',
                background: mode === 'compare' ? 'var(--accent-bg-soft)' : 'transparent',
                color: mode === 'compare' ? 'var(--accent)' : 'var(--mute)',
                cursor: 'pointer', fontWeight: 600,
              }}
            >
              多篇对比
            </button>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <input
              type="text"
              placeholder="搜索论文..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
              }}
            />
            <button
              onClick={() => { setLoading(true); papersApi.list({ page_size: 100, sort_by: 'created_at', sort_order: 'desc' }).then(r => { setPapers(r.items || []); setLoading(false); }).catch(() => { setPapers([]); setLoading(false); }); }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: '2px' }}
              title="刷新"
            >
              <RefreshCw size={12} />
            </button>
          </div>
        </div>

        {mode === 'compare' && (
          <div style={{ padding: '4px 10px', fontSize: 10, color: 'var(--mute)' }}>
            已选 {selectedIds.size} 篇
          </div>
        )}

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading && (
            <div style={{ padding: 16, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}>
              <Loader2 size={14} className="animate-spin" style={{ display: 'inline', marginRight: 4 }} />
              加载中...
            </div>
          )}
          {!loading && filteredPapers.length === 0 && (
            <div style={{ padding: 16, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}>
              暂无论文数据
            </div>
          )}
          {filteredPapers.map(paper => {
            const isSelected = mode === 'single'
              ? selectedPaperId === paper.id
              : selectedIds.has(paper.id);
            return (
              <div
                key={paper.id}
                onClick={() => handleSelectPaper(paper.id)}
                style={{
                  padding: '6px 10px', cursor: 'pointer', fontSize: 11,
                  background: isSelected ? 'var(--accent-bg-soft)' : 'transparent',
                  borderLeft: mode === 'single' && isSelected ? '3px solid var(--accent)' : '3px solid transparent',
                  borderBottom: '1px solid var(--hairline)',
                  display: 'flex', alignItems: 'flex-start', gap: 6,
                }}
              >
                {mode === 'compare' && (
                  isSelected ? <CheckSquare size={12} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 2 }} /> : <Square size={12} style={{ color: 'var(--mute)', flexShrink: 0, marginTop: 2 }} />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    color: isSelected ? 'var(--accent)' : 'var(--body)', fontWeight: 500,
                  }}>
                    {paper.title}
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 2, fontSize: 9, color: 'var(--mute)' }}>
                    {paper.year ? <span>{paper.year}</span> : null}
                    {paper.journal ? <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 120 }}>{paper.journal}</span> : null}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div style={{ padding: '4px 10px', borderTop: '1px solid var(--hairline)', fontSize: 9, color: 'var(--mute)', textAlign: 'center' }}>
          {filteredPapers.length} 篇论文
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {mode === 'single' ? (
          <>
            {!selectedPaper ? (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: 'var(--mute)', padding: 32 }}>
                <Brain size={40} style={{ opacity: 0.15, marginBottom: 12 }} />
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>论文11维度拆分</div>
                <div style={{ fontSize: 11, textAlign: 'center', lineHeight: 1.6 }}>
                  从左侧选择一篇论文<br />先预览拆分结果，确认后保存到数据库
                </div>
              </div>
            ) : (
              <>
                <div style={{
                  padding: '10px 16px', borderBottom: '1px solid var(--hairline)',
                  background: 'var(--glass-bg, var(--bg-2))',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 13, fontWeight: 600, color: 'var(--body)',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {selectedPaper.title}
                      </div>
                      <div style={{ display: 'flex', gap: 8, marginTop: 2, fontSize: 10, color: 'var(--mute)' }}>
                        {(selectedPaper.authors || []).length > 0 && (
                          <span>{selectedPaper.authors!.slice(0, 3).join(', ')}{selectedPaper.authors!.length > 3 ? ` +${selectedPaper.authors!.length - 3}` : ''}</span>
                        )}
                        {selectedPaper.year ? <span>{selectedPaper.year}</span> : null}
                        {selectedPaper.journal ? <span>{selectedPaper.journal}</span> : null}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                      {isFromDB && (
                        <button
                          onClick={handleDeleteDimensions}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px',
                            fontSize: 10, borderRadius: 4, border: '1px solid var(--hairline)',
                            background: 'transparent', color: 'var(--danger)', cursor: 'pointer',
                          }}
                        >
                          <Trash2 size={10} /> 清除
                        </button>
                      )}
                      {isPreview && (
                        <button
                          onClick={handleConfirmSave}
                          disabled={saving}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
                            fontSize: 10, borderRadius: 4, border: 'none',
                            background: '#10b981', color: '#fff', cursor: saving ? 'wait' : 'pointer',
                            opacity: saving ? 0.7 : 1,
                          }}
                        >
                          {saving ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />}
                          {saving ? '保存中...' : '确认保存'}
                        </button>
                      )}
                      <button
                        onClick={handlePreviewExtract}
                        disabled={extracting}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
                          fontSize: 10, borderRadius: 4, border: 'none',
                          background: 'var(--accent)', color: '#fff', cursor: extracting ? 'wait' : 'pointer',
                          opacity: extracting ? 0.7 : 1,
                        }}
                      >
                        {extracting ? <Loader2 size={10} className="animate-spin" /> : <Eye size={10} />}
                        {extracting ? '拆分中...' : isFromDB ? '重新预览' : '预览拆分'}
                      </button>
                    </div>
                  </div>

                  {dimensions && (
                    <div style={{ marginTop: 8 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 9, color: 'var(--mute)' }}>维度填充进度</span>
                          <span style={{ fontSize: 9, color: 'var(--accent)', fontWeight: 600 }}>{filledCount}/11 ({progressPercent}%)</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          {isPreview && (
                            <span style={{
                              display: 'flex', alignItems: 'center', gap: 3,
                              fontSize: 9, padding: '1px 6px', borderRadius: 3,
                              background: 'rgba(245,158,11,0.12)', color: '#f59e0b', fontWeight: 600,
                            }}>
                              <Eye size={9} /> 预览中
                            </span>
                          )}
                          {isFromDB && (
                            <span style={{
                              display: 'flex', alignItems: 'center', gap: 3,
                              fontSize: 9, padding: '1px 6px', borderRadius: 3,
                              background: 'rgba(16,185,129,0.12)', color: '#10b981', fontWeight: 600,
                            }}>
                              <Database size={9} /> 已存储
                            </span>
                          )}
                        </div>
                      </div>
                      <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-2)', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%', borderRadius: 2,
                          background: isPreview ? 'linear-gradient(90deg, #f59e0b, #f97316)' : 'linear-gradient(90deg, #6366f1, #06b6d4)',
                          width: `${progressPercent}%`,
                          transition: 'width 0.3s ease',
                        }} />
                      </div>
                    </div>
                  )}
                </div>

                <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
                  {dimsLoading && (
                    <div style={{ padding: 32, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
                      <Loader2 size={20} className="animate-spin" style={{ display: 'inline', marginRight: 8 }} />
                      从数据库加载维度数据...
                    </div>
                  )}
                  {!dimsLoading && !dimensions && (
                    <div style={{ padding: 32, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
                      <Sparkles size={24} style={{ opacity: 0.2, marginBottom: 8 }} />
                      <div style={{ marginBottom: 4 }}>该论文尚未进行维度拆分</div>
                      <div style={{ fontSize: 10, lineHeight: 1.6 }}>
                        点击「预览拆分」先查看AI拆分结果<br />
                        确认无误后再保存到数据库
                      </div>
                      <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'center' }}>
                        <button
                          onClick={handlePreviewExtract}
                          disabled={extracting}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                            fontSize: 12, borderRadius: 6, border: 'none',
                            background: 'var(--accent)', color: '#fff', cursor: extracting ? 'wait' : 'pointer',
                            opacity: extracting ? 0.7 : 1,
                          }}
                        >
                          {extracting ? <Loader2 size={12} className="animate-spin" /> : <Eye size={12} />}
                          {extracting ? '拆分中...' : '预览拆分'}
                        </button>
                        <button
                          onClick={handleDirectExtract}
                          disabled={extracting}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
                            fontSize: 12, borderRadius: 6, border: '1px solid var(--hairline)',
                            background: 'transparent', color: 'var(--body)', cursor: extracting ? 'wait' : 'pointer',
                          }}
                        >
                          <Database size={12} />
                          直接拆分存库
                        </button>
                      </div>
                    </div>
                  )}
                  {!dimsLoading && dimensions && isPreview && (
                    <div style={{
                      marginBottom: 8, padding: '8px 12px', borderRadius: 8,
                      background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <Eye size={14} style={{ color: '#f59e0b', flexShrink: 0 }} />
                      <div style={{ flex: 1, fontSize: 11, color: 'var(--body)' }}>
                        <span style={{ fontWeight: 600, color: '#f59e0b' }}>预览模式</span> — 当前为AI拆分预览结果，尚未保存到数据库
                      </div>
                      <button
                        onClick={handleConfirmSave}
                        disabled={saving}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
                          fontSize: 10, borderRadius: 4, border: 'none',
                          background: '#10b981', color: '#fff', cursor: saving ? 'wait' : 'pointer',
                          opacity: saving ? 0.7 : 1, flexShrink: 0,
                        }}
                      >
                        {saving ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />}
                        确认保存
                      </button>
                    </div>
                  )}
                  {!dimsLoading && dimensions && DIMENSION_KEYS.map((key, idx) => {
                    const content = dimensions[key] || null;
                    const isExpanded = expandedKeys.has(key);
                    const color = DIMENSION_COLORS[key];
                    const label = DIMENSION_LABELS[key];
                    return (
                      <div
                        key={key}
                        style={{
                          marginBottom: 4, borderRadius: 8,
                          border: `1px solid ${isExpanded ? `${color}30` : 'var(--hairline)'}`,
                          background: isExpanded ? `${color}06` : 'transparent',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          onClick={() => toggleExpanded(key)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 8,
                            padding: '8px 12px', cursor: 'pointer',
                            userSelect: 'none',
                          }}
                        >
                          <span style={{
                            width: 22, height: 22, borderRadius: 6,
                            background: content ? `${color}18` : 'var(--bg-2)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: content ? color : 'var(--mute)', flexShrink: 0,
                            fontSize: 10, fontWeight: 700,
                          }}>
                            {idx + 1}
                          </span>
                          <span style={{ flex: 1, fontSize: 12, fontWeight: 500, color: content ? 'var(--body)' : 'var(--mute)' }}>
                            {label}
                          </span>
                          {content ? (
                            <span style={{
                              fontSize: 8, padding: '1px 5px', borderRadius: 3,
                              background: `${color}15`, color, fontWeight: 600,
                            }}>
                              已填充
                            </span>
                          ) : (
                            <span style={{ fontSize: 8, color: 'var(--mute)', padding: '1px 5px' }}>
                              空
                            </span>
                          )}
                          {isExpanded ? <ChevronDown size={12} style={{ color: 'var(--mute)' }} /> : <ChevronRight size={12} style={{ color: 'var(--mute)' }} />}
                        </div>
                        {isExpanded && (
                          <div style={{ padding: '0 12px 10px 42px' }}>
                            {content ? (
                              <div style={{ position: 'relative' }}>
                                <div style={{
                                  fontSize: 12, lineHeight: 1.7, color: 'var(--body)',
                                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                                }}>
                                  {content}
                                </div>
                                <button
                                  onClick={() => handleCopy(key, content)}
                                  style={{
                                    position: 'absolute', top: 0, right: 0,
                                    background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                                    borderRadius: 4, padding: '2px 6px', cursor: 'pointer',
                                    fontSize: 9, color: copiedKey === key ? '#10b981' : 'var(--mute)',
                                    display: 'flex', alignItems: 'center', gap: 3,
                                  }}
                                >
                                  {copiedKey === key ? <CheckCircle2 size={10} /> : <Copy size={10} />}
                                  {copiedKey === key ? '已复制' : '复制'}
                                </button>
                              </div>
                            ) : (
                              <div style={{ fontSize: 11, color: 'var(--mute)', fontStyle: 'italic' }}>
                                该维度暂无内容
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </>
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  );
};
