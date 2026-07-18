/**
 * 批量文献处理面板
 *
 * 功能：导入 / 分析 / 导出 / 统计
 */

import React, { useState, useCallback, useRef } from 'react';
import {
  Upload, FileText, Download, BarChart3, Play, Check, X, Loader2,
  AlertCircle,
} from 'lucide-react';
import { openFile, saveFile } from '@/lib/tauri-adapter';

const BASE_URL = '/api';

/* ── helpers ── */

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

/* ── types ── */

interface ImportEntry {
  title: string;
  authors: string;
  year: string;
  journal: string;
  doi: string;
  abstract: string;
  status: string;
  paper_id?: number;
  existing_id?: number;
}

interface ImportResult {
  imported: number;
  duplicates: number;
  entries: ImportEntry[];
  total_parsed: number;
}

interface StatsData {
  total: number;
  by_year: Record<string, number>;
  by_journal: Record<string, number>;
  by_keyword: Record<string, number>;
}

interface PaperItem {
  id: number;
  title: string;
  authors: string[];
  abstract: string | null;
  doi: string | null;
  journal: string | null;
  year: number | null;
  keywords: string[];
}

/* ── glass style helpers ── */

const glassPanel: React.CSSProperties = {
  background: 'var(--glass-bg)',
  border: '1px solid var(--hairline)',
  borderRadius: 'var(--glass-radius)',
  boxShadow: 'var(--glass-shadow-sm)',
  padding: 16,
};

const btnPrimary: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  padding: '6px 14px', borderRadius: 'var(--radius-sm)',
  background: 'var(--accent)', color: '#fff',
  border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 500,
};

/* ── sub-components ── */

/** 导入区 */
const ImportSection: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const doImport = useCallback(async (file: File) => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await apiFetch<ImportResult>('/literature-batch/import', {
        method: 'POST', body: form,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || '导入失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleFileSelect = useCallback(async () => {
    try {
      const files = await openFile({
        filters: [
          { name: '文献文件', extensions: ['bib', 'ris', 'csv', 'xml'] },
        ],
        multiple: false,
      });
      if (files.length > 0) {
        const f = files[0];
        const blob = new Blob([f.content as BlobPart]);
        const file = new File([blob], f.name);
        await doImport(file);
      }
    } catch {
      // 用户取消
    }
  }, [doImport]);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) await doImport(file);
  }, [doImport]);

  return (
    <div style={glassPanel}>
      <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <Upload size={14} /> 批量导入
      </h3>

      {/* 拖放区 */}
      <div
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={handleFileSelect}
        style={{
          border: `2px dashed ${dragOver ? 'var(--accent)' : 'var(--hairline)'}`,
          borderRadius: 'var(--radius-md)',
          padding: '24px 16px',
          textAlign: 'center',
          cursor: 'pointer',
          background: dragOver ? 'var(--accent-bg-soft)' : 'transparent',
          transition: 'all 0.15s',
          marginBottom: 12,
        }}
      >
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--text-muted)' }}>
            <Loader2 size={18} className="animate-spin" /> 解析导入中...
          </div>
        ) : (
          <>
            <Upload size={24} style={{ color: 'var(--text-muted)', marginBottom: 8 }} />
            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
              拖放文件到此处，或点击选择
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
              支持 BibTeX (.bib) / RIS (.ris) / CSV / EndNote XML
            </div>
          </>
        )}
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept=".bib,.ris,.csv,.xml"
        style={{ display: 'none' }}
        onChange={e => {
          const f = e.target.files?.[0];
          if (f) doImport(f);
        }}
      />

      {/* 结果 */}
      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-soft)', color: 'var(--danger)', fontSize: 12, marginBottom: 8 }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {result && (
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
            <span>解析: <strong style={{ color: 'var(--text-primary)' }}>{result.total_parsed}</strong> 条</span>
            <span>导入: <strong style={{ color: 'var(--success)' }}>{result.imported}</strong> 条</span>
            <span>重复: <strong style={{ color: 'var(--warning)' }}>{result.duplicates}</strong> 条</span>
          </div>
          {result.entries.length > 0 && (
            <div style={{ maxHeight: 200, overflow: 'auto', borderTop: '1px solid var(--hairline)', paddingTop: 8 }}>
              {result.entries.slice(0, 20).map((e, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0', fontSize: 11 }}>
                  {e.status === 'imported' ? <Check size={12} style={{ color: 'var(--success)' }} /> :
                   e.status === 'duplicate' ? <X size={12} style={{ color: 'var(--warning)' }} /> :
                   <FileText size={12} style={{ color: 'var(--text-muted)' }} />}
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
                    {e.title || '(无标题)'}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{e.year}</span>
                </div>
              ))}
              {result.entries.length > 20 && (
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center', padding: 4 }}>
                  ...还有 {result.entries.length - 20} 条
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/** 分析区 */
const AnalysisSection: React.FC = () => {
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [dimensions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [searchQ, setSearchQ] = useState('');

  const loadPapers = useCallback(async () => {
    try {
      const res = await apiFetch<{ items: PaperItem[] }>('/papers?page_size=50');
      setPapers(res.items || []);
    } catch { /* ignore */ }
  }, []);

  React.useEffect(() => { loadPapers(); }, [loadPapers]);

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const runAnalysis = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setLoading(true);
    try {
      const res = await apiFetch<{ results: any[] }>('/literature-batch/analyze', {
        method: 'POST',
        body: JSON.stringify({ paper_ids: Array.from(selectedIds), dimensions }),
      });
      setResults(res.results || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, [selectedIds, dimensions]);

  const filtered = papers.filter(p =>
    !searchQ || p.title.toLowerCase().includes(searchQ.toLowerCase())
  );

  return (
    <div style={glassPanel}>
      <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <Play size={14} /> 批量分析
      </h3>

      <input
        type="text"
        placeholder="搜索文献..."
        value={searchQ}
        onChange={e => setSearchQ(e.target.value)}
        style={{
          width: '100%', padding: '6px 10px', borderRadius: 'var(--radius-sm)',
          background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
          color: 'var(--text-primary)', fontSize: 12, marginBottom: 8, outline: 'none',
        }}
      />

      <div style={{ maxHeight: 180, overflow: 'auto', border: '1px solid var(--hairline)', borderRadius: 'var(--radius-sm)', marginBottom: 8 }}>
        {filtered.map(p => (
          <label key={p.id} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 8px', fontSize: 11, cursor: 'pointer',
            borderBottom: '1px solid var(--hairline)',
          }}>
            <input
              type="checkbox"
              checked={selectedIds.has(p.id)}
              onChange={() => toggleSelect(p.id)}
            />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
              {p.title}
            </span>
          </label>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>已选 {selectedIds.size} 篇</span>
        <button onClick={runAnalysis} disabled={loading || selectedIds.size === 0} style={{
          ...btnPrimary,
          opacity: loading || selectedIds.size === 0 ? 0.5 : 1,
        }}>
          {loading ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
          开始分析
        </button>
      </div>

      {results.length > 0 && (
        <div style={{ maxHeight: 200, overflow: 'auto', borderTop: '1px solid var(--hairline)', paddingTop: 8 }}>
          {results.map((r, i) => (
            <div key={i} style={{ padding: '4px 0', fontSize: 11, borderBottom: '1px solid var(--hairline)' }}>
              <span style={{ color: r.status === 'analyzed' ? 'var(--success)' : 'var(--danger)', fontWeight: 500 }}>
                {r.status === 'analyzed' ? '✓' : '✗'}
              </span>
              <span style={{ color: 'var(--text-primary)', marginLeft: 6 }}>{r.title || `Paper #${r.paper_id}`}</span>
              {r.error && <span style={{ color: 'var(--danger)', marginLeft: 8 }}>{r.error}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/** 导出区 */
const ExportSection: React.FC = () => {
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [format, setFormat] = useState<'bibtex' | 'ris' | 'csv'>('bibtex');
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    apiFetch<{ items: PaperItem[] }>('/papers?page_size=100')
      .then(res => setPapers(res.items || []))
      .catch(() => {});
  }, []);

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const doExport = useCallback(async () => {
    if (selectedIds.size === 0) return;
    setLoading(true);
    try {
      const res = await apiFetch<{ content: string; filename: string }>('/literature-batch/export', {
        method: 'POST',
        body: JSON.stringify({ paper_ids: Array.from(selectedIds), format }),
      });
      await saveFile(res.content, {
        defaultPath: res.filename,
        filters: [{ name: '导出文件', extensions: [format === 'bibtex' ? 'bib' : format] }],
      });
    } catch { /* ignore */ }
    setLoading(false);
  }, [selectedIds, format]);

  return (
    <div style={glassPanel}>
      <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <Download size={14} /> 批量导出
      </h3>

      <div style={{ maxHeight: 180, overflow: 'auto', border: '1px solid var(--hairline)', borderRadius: 'var(--radius-sm)', marginBottom: 8 }}>
        {papers.map(p => (
          <label key={p.id} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 8px', fontSize: 11, cursor: 'pointer',
            borderBottom: '1px solid var(--hairline)',
          }}>
            <input type="checkbox" checked={selectedIds.has(p.id)} onChange={() => toggleSelect(p.id)} />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
              {p.title}
            </span>
          </label>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <select
          value={format}
          onChange={e => setFormat(e.target.value as any)}
          style={{
            padding: '5px 8px', borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
            color: 'var(--text-primary)', fontSize: 12,
          }}
        >
          <option value="bibtex">BibTeX</option>
          <option value="ris">RIS</option>
          <option value="csv">CSV</option>
        </select>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>已选 {selectedIds.size} 篇</span>
        <button onClick={doExport} disabled={loading || selectedIds.size === 0} style={{
          ...btnPrimary,
          opacity: loading || selectedIds.size === 0 ? 0.5 : 1,
        }}>
          {loading ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
          导出
        </button>
      </div>
    </div>
  );
};

/** 统计区 */
const StatisticsSection: React.FC = () => {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [tab, setTab] = useState<'year' | 'journal'>('year');

  React.useEffect(() => {
    apiFetch<StatsData>('/literature-batch/stats')
      .then(res => setStats(res))
      .catch(() => {});
  }, []);

  if (!stats) return null;

  const data = tab === 'year' ? stats.by_year : stats.by_journal;
  const entries = Object.entries(data);
  const maxVal = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div style={glassPanel}>
      <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <BarChart3 size={14} /> 文献统计
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>共 {stats.total} 篇</span>
      </h3>

      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {(['year', 'journal'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: 11,
              background: tab === t ? 'var(--accent)' : 'var(--canvas-soft)',
              color: tab === t ? '#fff' : 'var(--text-secondary)',
              border: '1px solid var(--hairline)', cursor: 'pointer',
            }}
          >
            {t === 'year' ? '按年份' : '按期刊'}
          </button>
        ))}
      </div>

      <div style={{ maxHeight: 200, overflow: 'auto' }}>
        {entries.slice(0, 15).map(([label, count]) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: 'var(--text-muted)', width: 60, textAlign: 'right', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {label}
            </span>
            <div style={{ flex: 1, height: 14, background: 'var(--canvas-soft)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{
                width: `${(count / maxVal) * 100}%`,
                height: '100%',
                background: 'var(--accent)',
                borderRadius: 3,
                transition: 'width 0.3s',
              }} />
            </div>
            <span style={{ fontSize: 10, color: 'var(--text-secondary)', width: 24, textAlign: 'right' }}>{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ── main panel ── */

export const BatchLiteraturePanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'import' | 'analyze' | 'export' | 'stats'>('import');

  const tabs = [
    { key: 'import' as const, label: '导入', icon: Upload },
    { key: 'analyze' as const, label: '分析', icon: Play },
    { key: 'export' as const, label: '导出', icon: Download },
    { key: 'stats' as const, label: '统计', icon: BarChart3 },
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      background: 'var(--panel-bg)', overflow: 'hidden',
    }}>
      {/* 标签栏 */}
      <div style={{
        display: 'flex', borderBottom: '1px solid var(--hairline)',
        padding: '0 8px', background: 'var(--glass-bg)',
      }}>
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '8px 12px', fontSize: 12,
              color: activeTab === t.key ? 'var(--accent)' : 'var(--text-muted)',
              background: 'transparent', border: 'none',
              borderBottom: activeTab === t.key ? '2px solid var(--accent)' : '2px solid transparent',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            <t.icon size={13} /> {t.label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'import' && <ImportSection />}
        {activeTab === 'analyze' && <AnalysisSection />}
        {activeTab === 'export' && <ExportSection />}
        {activeTab === 'stats' && <StatisticsSection />}
      </div>
    </div>
  );
};

export default BatchLiteraturePanel;
