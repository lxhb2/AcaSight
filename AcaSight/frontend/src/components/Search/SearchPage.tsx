import React, { useState, useCallback, useMemo } from 'react';
import { Search, Filter, Download, BookOpen, Calendar, User, ExternalLink, Star, ChevronDown, X, AlertCircle, Database, BookmarkPlus, CheckCircle2, Loader2, FileText, BarChart3, PieChart, TrendingUp, Inbox, Copy } from 'lucide-react';
import { searchApi, zoteroApi } from '@/services/api';
import { useFileOpen } from '@/contexts/FileOpenContext';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';

const Plot = createPlotlyComponent(Plotly);

interface UnifiedPaper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  doi?: string;
  journal?: string;
  cited_by_count?: number;
  is_open_access: boolean;
  pdf_url?: string;
  source: string;
  source_label: string;
}

interface SourceInfo {
  id: string;
  name: string;
  description: string;
  checked: boolean;
}

const SOURCES: SourceInfo[] = [
  { id: 'core', name: 'CORE', description: '全球开放获取论文聚合', checked: true },
  { id: 'openalex', name: 'OpenAlex', description: '开放学术数据平台', checked: true },
  { id: 'semanticscholar', name: 'Semantic Scholar', description: 'AI 驱动的学术搜索', checked: true },
  { id: 'crossref', name: 'Crossref', description: 'DOI 官方注册', checked: true },
  { id: 'europepmc', name: 'Europe PMC', description: '欧洲 PubMed Central', checked: false },
  { id: 'arxiv', name: 'arXiv', description: '预印本论文库', checked: false },
];

const YEAR_FILTERS = [
  { label: '全部时间', value: 'all' },
  { label: '2025', value: '2025' },
  { label: '2024', value: '2024' },
  { label: '2023', value: '2023' },
  { label: '近3年', value: '3y' },
  { label: '近5年', value: '5y' },
];

const SORT_OPTIONS = [
  { label: '相关度', value: 'relevance' },
  { label: '引用数 ↓', value: 'citations' },
  { label: '最新', value: 'date_desc' },
  { label: '最早', value: 'date_asc' },
];

const SOURCE_LABELS: Record<string, string> = {
  core: 'CORE',
  openalex: 'OpenAlex',
  semanticscholar: 'Semantic Scholar',
  crossref: 'Crossref',
  europepmc: 'Europe PMC',
  arxiv: 'arXiv',
};

const SOURCE_COLORS: Record<string, string> = {
  core: '#6366f1',
  openalex: '#06b6d4',
  semanticscholar: '#f59e0b',
  crossref: '#10b981',
  europepmc: '#ec4899',
  arxiv: '#ef4444',
};

function normalizePaper(raw: Record<string, any>, source: string): UnifiedPaper {
  return {
    id: raw.id || raw.doi || raw.arxiv_id || `${source}-${Math.random().toString(36).slice(2)}`,
    title: (raw.title || 'Untitled').trim(),
    authors: Array.isArray(raw.authors) ? raw.authors : [],
    year: raw.year ? Number(raw.year) : null,
    abstract: (raw.abstract || '').replace(/<[^>]*>/g, '').trim(),
    doi: raw.doi || undefined,
    journal: raw.journal || undefined,
    cited_by_count: raw.cited_by_count ?? undefined,
    is_open_access: Boolean(raw.is_open_access),
    pdf_url: raw.pdf_url || undefined,
    source,
    source_label: SOURCE_LABELS[source] || source,
  };
}

function mergeResults(sourceResults: Record<string, any>): UnifiedPaper[] {
  const allPapers: UnifiedPaper[] = [];
  const seenDois = new Set<string>();
  const seenTitles = new Set<string>();

  for (const [source, data] of Object.entries(sourceResults)) {
    const results = data?.results || [];
    for (const raw of results) {
      if (!raw || typeof raw !== 'object') continue;
      const paper = normalizePaper(raw, source);
      const normTitle = paper.title.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]/g, '');
      if (paper.doi && seenDois.has(paper.doi.toLowerCase())) continue;
      if (seenTitles.has(normTitle)) continue;
      if (paper.doi) seenDois.add(paper.doi.toLowerCase());
      seenTitles.add(normTitle);
      allPapers.push(paper);
    }
  }

  return allPapers;
}

function sortPapers(papers: UnifiedPaper[], sort: string): UnifiedPaper[] {
  const sorted = [...papers];
  switch (sort) {
    case 'citations':
      sorted.sort((a, b) => (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0));
      break;
    case 'date_desc':
      sorted.sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
      break;
    case 'date_asc':
      sorted.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
      break;
  }
  return sorted;
}

function getYearRange(filter: string): { from?: number; to?: number } {
  const now = new Date().getFullYear();
  switch (filter) {
    case '2025': return { from: 2025, to: 2025 };
    case '2024': return { from: 2024, to: 2024 };
    case '2023': return { from: 2023, to: 2023 };
    case '3y': return { from: now - 2, to: now };
    case '5y': return { from: now - 4, to: now };
    default: return {};
  }
}

export const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UnifiedPaper[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [selectedSort, setSelectedSort] = useState('relevance');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sources, setSources] = useState(SOURCES);
  const [showSources, setShowSources] = useState(false);
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set());
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [importingIds, setImportingIds] = useState<Set<string>>(new Set());
  const [importedIds, setImportedIds] = useState<Set<string>>(new Set());
  const [dupIds, setDupIds] = useState<Set<string>>(new Set());
  const [totalCount, setTotalCount] = useState(0);
  const [showChart, setShowChart] = useState(false);

  const { openFile } = useFileOpen();

  const handleOpenInReader = useCallback((paper: UnifiedPaper) => {
    if (!paper.pdf_url) return;
    openFile(paper.title + '.pdf', 'pdf', {
      pdfUrl: paper.pdf_url,
      abstract: paper.abstract,
      authors: paper.authors.join(', '),
      year: paper.year ?? undefined,
      journal: paper.journal,
    });
  }, [openFile]);

  const checkedSources = useMemo(
    () => sources.filter(s => s.checked).map(s => s.id),
    [sources]
  );

  const toggleSource = useCallback((id: string) => {
    setSources(prev => prev.map(s => s.id === id ? { ...s, checked: !s.checked } : s));
  }, []);

  const selectAllSources = useCallback(() => {
    setSources(prev => prev.map(s => ({ ...s, checked: true })));
  }, []);

  const clearSources = useCallback(() => {
    setSources(prev => prev.map(s => ({ ...s, checked: false })));
  }, []);

  const handleSearch = useCallback(async () => {
    const q = query.trim();
    if (!q) return;
    if (checkedSources.length === 0) {
      setError('请至少选择一个数据源');
      return;
    }

    setIsSearching(true);
    setError(null);
    setResults([]);
    setExpandedId(null);

    try {
      const yearRange = getYearRange(selectedFilter);
      const data = await searchApi.search(
        q,
        checkedSources,
        20,
        yearRange.from,
        yearRange.to
      );

      if (data?.results) {
        const merged = mergeResults(data.results);
        const sorted = sortPapers(merged, selectedSort);
        setResults(sorted);
        setTotalCount(sorted.length);
      } else {
        setResults([]);
        setTotalCount(0);
      }
    } catch (e: any) {
      setError(e.message || '搜索失败，请检查网络连接');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query, checkedSources, selectedFilter, selectedSort]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  }, [handleSearch]);

  const handleSaveToZotero = useCallback(async (paper: UnifiedPaper) => {
    if (savingIds.has(paper.id) || savedIds.has(paper.id)) return;
    setSavingIds(prev => new Set(prev).add(paper.id));

    try {
      await zoteroApi.writeMetadata({
        itemKey: '',
        fields: {
          title: paper.title,
          abstractNote: paper.abstract,
          date: paper.year?.toString(),
          publicationTitle: paper.journal,
          DOI: paper.doi,
          url: paper.pdf_url,
        },
        creators: paper.authors.map(name => ({
          creatorType: 'author',
          firstName: name.split(' ').slice(0, -1).join(' '),
          lastName: name.split(' ').pop() || name,
        })),
      } as any);
    } catch (e: any) {
      console.warn('Zotero save attempted:', e.message);
    }

    setSavingIds(prev => {
      const next = new Set(prev);
      next.delete(paper.id);
      return next;
    });
    setSavedIds(prev => new Set(prev).add(paper.id));
  }, [savingIds, savedIds]);

  const handleImportToDb = useCallback(async (paper: UnifiedPaper) => {
    if (importingIds.has(paper.id) || importedIds.has(paper.id)) return;
    setImportingIds(prev => new Set(prev).add(paper.id));

    try {
      // 改用 searchApi.importPaper（支持 DOI 去重）
      const result = await searchApi.importPaper({
        title: paper.title,
        authors: paper.authors,
        abstract: paper.abstract ?? undefined,
        doi: paper.doi ?? undefined,
        year: paper.year ?? undefined,
        journal: paper.journal ?? undefined,
        pdf_url: paper.pdf_url ?? undefined,
        citation_count: paper.cited_by_count ?? 0,
        tags: [],
      });
      if (result.status === 'exists' || result.status === 'already_imported') {
        setDupIds(prev => new Set(prev).add(paper.id));
      } else {
        setImportedIds(prev => new Set(prev).add(paper.id));
      }
    } catch (e: any) {
      console.warn('Import to DB failed:', e.message);
    }

    setImportingIds(prev => {
      const next = new Set(prev);
      next.delete(paper.id);
      return next;
    });
  }, [importingIds]);

  const displayedResults = useMemo(
    () => sortPapers(results, selectedSort),
    [results, selectedSort]
  );

  const chartData = useMemo(() => {
    if (!displayedResults.length) return null;
    const sorted = [...displayedResults].sort((a, b) => (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0));
    const top15 = sorted.slice(0, 15);

    const citationBar = {
      x: top15.map(p => (p.title.length > 35 ? p.title.slice(0, 35) + '...' : p.title)),
      y: top15.map(p => p.cited_by_count ?? 0),
      text: top15.map(p => p.title),
    };

    const yearMap = new Map<number, number>();
    displayedResults.forEach(p => {
      if (p.year) yearMap.set(p.year, (yearMap.get(p.year) || 0) + 1);
    });
    const yearEntries = [...yearMap.entries()].sort((a, b) => a[0] - b[0]);
    const yearHist = { x: yearEntries.map(e => String(e[0])), y: yearEntries.map(e => e[1]) };

    const srcMap = new Map<string, number>();
    displayedResults.forEach(p => {
      const label = p.source_label;
      srcMap.set(label, (srcMap.get(label) || 0) + 1);
    });
    const pieData = {
      labels: [...srcMap.keys()],
      values: [...srcMap.values()],
      colors: [...srcMap.keys()].map(k => SOURCE_COLORS[Object.entries(SOURCE_LABELS).find(([,v]) => v === k)?.[0] || '']) || '#888',
    };

    return { citationBar, yearHist, pieData };
  }, [displayedResults]);

  return (
    <div className="search-page-container">
      <div className="search-hero">
        <h1 className="search-hero-title">AI 文献检索</h1>

        <div className="search-bar-wrap">
          <div className="search-input-wrap">
            <Search className="search-icon" size={18} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入研究主题、关键词或论文标题（英文效果更好）..."
              className="search-input"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={isSearching || !query.trim()}
            className="search-btn"
          >
            {isSearching ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Search size={18} />
            )}
            搜索
          </button>
        </div>

        <div>
          <button
            onClick={() => setShowSources(!showSources)}
            className="search-sources-toggle"
          >
            <Database size={14} />
            <span>数据源:</span>
            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
              {checkedSources.length} / {sources.length}
            </span>
            <ChevronDown size={14} className={`transition-transform ${showSources ? 'rotate-180' : ''}`} />
          </button>
          {showSources && (
            <div className="search-sources-grid">
              {sources.map((src) => (
                <label
                  key={src.id}
                  className={`search-source-chip ${src.checked ? 'checked' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={src.checked}
                    onChange={() => toggleSource(src.id)}
                    className="sr-only"
                  />
                  <div
                    className="search-source-dot"
                    style={src.checked ? { borderColor: SOURCE_COLORS[src.id], background: SOURCE_COLORS[src.id], boxShadow: `0 0 6px ${SOURCE_COLORS[src.id]}40` } : {}}
                  />
                  <span style={{ color: src.checked ? 'var(--ink)' : 'var(--mute)' }}>
                    {src.name}
                  </span>
                </label>
              ))}
              <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 12, paddingTop: 6, borderTop: '1px solid var(--hairline)' }}>
                <button onClick={selectAllSources} style={{ fontSize: 11, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}>全选</button>
                <button onClick={clearSources} style={{ fontSize: 11, color: 'var(--mute)', background: 'none', border: 'none', cursor: 'pointer' }}>清除</button>
              </div>
            </div>
          )}
        </div>

        <div className="search-filters-row">
          <Filter size={14} style={{ color: 'var(--mute)' }} />
          {YEAR_FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => setSelectedFilter(filter.value)}
              className={`search-filter-chip ${selectedFilter === filter.value ? 'active' : ''}`}
            >
              {filter.label}
            </button>
          ))}
          <select
            value={selectedSort}
            onChange={(e) => setSelectedSort(e.target.value)}
            className="search-sort-select"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="search-results-area">
        {error && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 12, marginBottom: 12, borderRadius: 12, background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', color: '#ef4444' }}>
            <AlertCircle size={16} />
            <span style={{ fontSize: 13 }}>{error}</span>
            <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}><X size={14} /></button>
          </div>
        )}

        {isSearching && (
          <div className="search-loading-state">
            <div className="search-loading-spinner" />
            <p style={{ fontSize: 13 }}>正在从 {checkedSources.length} 个数据源检索...</p>
          </div>
        )}

        {!isSearching && displayedResults.length > 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 13, color: 'var(--mute)' }}>
                找到 <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{totalCount}</span> 条结果（已去重）
              </div>
              <button
                onClick={() => setShowChart(prev => !prev)}
                className={`search-chart-btn ${showChart ? 'active' : ''}`}
              >
                <BarChart3 size={14} />
                {showChart ? '隐藏图表' : '图表分析'}
              </button>
            </div>

            {showChart && chartData && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                  <div className="search-result-card">
                    <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4, color: 'var(--ink)' }}>
                      <TrendingUp size={14} /> 引用数 Top 15
                    </h4>
                    <Plot
                      data={[{
                        x: chartData.citationBar.y,
                        y: chartData.citationBar.x,
                        type: 'bar',
                        orientation: 'h',
                        marker: { color: '#6366f1' },
                        text: chartData.citationBar.y.map(v => v.toLocaleString()),
                        textposition: 'outside',
                        textfont: { size: 9 },
                      }]}
                      layout={{
                        margin: { l: 140, r: 40, t: 10, b: 30 },
                        height: 380,
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: 'var(--color-text-secondary)', size: 10 },
                        xaxis: { title: '引用数', showgrid: true, gridcolor: 'rgba(128,128,128,0.15)' },
                        yaxis: { automargin: true },
                        showlegend: false,
                      }}
                      config={{ displayModeBar: false, responsive: true }}
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div className="search-result-card">
                    <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4, color: 'var(--ink)' }}>
                      <PieChart size={14} /> 数据源分布
                    </h4>
                    <Plot
                      data={[{
                        labels: chartData.pieData.labels,
                        values: chartData.pieData.values,
                        type: 'pie',
                        hole: 0.45,
                        marker: { colors: chartData.pieData.colors },
                        textinfo: 'label+percent',
                        textfont: { size: 11 },
                      }]}
                      layout={{
                        margin: { l: 10, r: 10, t: 10, b: 10 },
                        height: 380,
                        paper_bgcolor: 'rgba(0,0,0,0)',
                        plot_bgcolor: 'rgba(0,0,0,0)',
                        font: { color: 'var(--color-text-secondary)' },
                        showlegend: true,
                        legend: { orientation: 'h', y: -0.05, font: { size: 10 } },
                      }}
                      config={{ displayModeBar: false, responsive: true }}
                      style={{ width: '100%' }}
                    />
                  </div>
                </div>
                <div className="search-result-card" style={{ marginTop: 12 }}>
                  <h4 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4, color: 'var(--ink)' }}>
                    <Calendar size={14} /> 发表年份分布
                  </h4>
                  <Plot
                    data={[{
                      x: chartData.yearHist.x,
                      y: chartData.yearHist.y,
                      type: 'bar',
                      marker: { color: '#06b6d4' },
                    }]}
                    layout={{
                      margin: { l: 40, r: 20, t: 10, b: 40 },
                      height: 200,
                      paper_bgcolor: 'rgba(0,0,0,0)',
                      plot_bgcolor: 'rgba(0,0,0,0)',
                      font: { color: 'var(--color-text-secondary)', size: 10 },
                      xaxis: { title: '年份', showgrid: false },
                      yaxis: { title: '论文数', showgrid: true, gridcolor: 'rgba(128,128,128,0.15)' },
                      showlegend: false,
                    }}
                    config={{ displayModeBar: false, responsive: true }}
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            )}

            {displayedResults.map((paper) => (
              <div key={paper.id} className="search-result-card">
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                  <h3 className="search-result-title" style={{ flex: 1, marginRight: 12 }}>
                    {paper.title}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
                    <span
                      className="search-badge"
                      style={{ background: `${SOURCE_COLORS[paper.source]}15`, color: SOURCE_COLORS[paper.source] }}
                    >
                      {paper.source_label}
                    </span>
                    {paper.is_open_access && (
                      <span className="search-badge" style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981' }}>OA</span>
                    )}
                    <button style={{ padding: 4, borderRadius: 6, color: 'var(--mute)', background: 'none', border: 'none', cursor: 'pointer' }}>
                      <Star size={14} />
                    </button>
                  </div>
                </div>

                <div className="search-result-meta">
                  {paper.authors.length > 0 && (
                    <div className="search-result-meta-item">
                      <User size={12} />
                      <span>{paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? ` +${paper.authors.length - 3}` : ''}</span>
                    </div>
                  )}
                  {paper.year && (
                    <div className="search-result-meta-item">
                      <Calendar size={12} />
                      <span>{paper.year}</span>
                    </div>
                  )}
                  {paper.journal && (
                    <div className="search-result-meta-item">
                      <BookOpen size={12} />
                      <span>{paper.journal}</span>
                    </div>
                  )}
                  {paper.cited_by_count != null && paper.cited_by_count > 0 && (
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>
                      {paper.cited_by_count.toLocaleString()} 引用
                    </span>
                  )}
                </div>

                {paper.abstract && (
                  <p className="search-result-abstract">{paper.abstract}</p>
                )}

                <div className="search-result-actions">
                  <button
                    onClick={() => setExpandedId(expandedId === paper.id ? null : paper.id)}
                    className="search-action-btn"
                  >
                    <ChevronDown size={12} className={`transition-transform ${expandedId === paper.id ? 'rotate-180' : ''}`} />
                    详情
                  </button>

                  {paper.pdf_url && (
                    <>
                      <a
                        href={paper.pdf_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="search-action-btn primary"
                        style={{ textDecoration: 'none' }}
                      >
                        <Download size={12} />
                        PDF
                      </a>
                      <button
                        onClick={() => handleOpenInReader(paper)}
                        className="search-action-btn success"
                      >
                        <FileText size={12} />
                        阅读器打开
                      </button>
                    </>
                  )}

                  {paper.doi && (
                    <a
                      href={`https://doi.org/${paper.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="search-action-btn"
                      style={{ textDecoration: 'none' }}
                    >
                      <ExternalLink size={12} />
                      DOI
                    </a>
                  )}

                  <button
                    onClick={() => handleSaveToZotero(paper)}
                    disabled={savingIds.has(paper.id) || savedIds.has(paper.id)}
                    className="search-action-btn"
                    style={savedIds.has(paper.id) ? { color: '#10b981', borderColor: '#10b981' } : {}}
                  >
                    {savingIds.has(paper.id) ? <Loader2 size={12} className="animate-spin" /> : savedIds.has(paper.id) ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
                    {savedIds.has(paper.id) ? '已保存' : 'Zotero'}
                  </button>

                  <button
                    onClick={() => handleImportToDb(paper)}
                    disabled={importingIds.has(paper.id) || importedIds.has(paper.id) || dupIds.has(paper.id)}
                    className="search-action-btn"
                    style={importedIds.has(paper.id) ? { color: '#6366f1', borderColor: '#6366f1' } : dupIds.has(paper.id) ? { color: 'var(--mute)', borderColor: 'var(--hairline)' } : {}}
                    title={dupIds.has(paper.id) ? '该文献已存在于数据库中' : '导入到本地文献库'}
                  >
                    {importingIds.has(paper.id) ? <Loader2 size={12} className="animate-spin" /> : importedIds.has(paper.id) ? <CheckCircle2 size={12} /> : dupIds.has(paper.id) ? <Copy size={12} /> : <Inbox size={12} />}
                    {importedIds.has(paper.id) ? '已入库' : dupIds.has(paper.id) ? '已存在' : '入库'}
                  </button>
                </div>

                {expandedId === paper.id && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--hairline)', animation: 'floating-panel-appear 0.15s ease' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
                      <div>
                        <span style={{ color: 'var(--mute)' }}>数据源: </span>
                        <span style={{ color: SOURCE_COLORS[paper.source] }}>{paper.source_label}</span>
                      </div>
                      {paper.doi && (
                        <div>
                          <span style={{ color: 'var(--mute)' }}>DOI: </span>
                          <span style={{ color: 'var(--body)' }}>{paper.doi}</span>
                        </div>
                      )}
                      {paper.cited_by_count != null && (
                        <div>
                          <span style={{ color: 'var(--mute)' }}>引用数: </span>
                          <span style={{ color: 'var(--body)' }}>{paper.cited_by_count.toLocaleString()}</span>
                        </div>
                      )}
                      {paper.year && (
                        <div>
                          <span style={{ color: 'var(--mute)' }}>发表年份: </span>
                          <span style={{ color: 'var(--body)' }}>{paper.year}</span>
                        </div>
                      )}
                      {paper.journal && (
                        <div>
                          <span style={{ color: 'var(--mute)' }}>期刊/会议: </span>
                          <span style={{ color: 'var(--body)' }}>{paper.journal}</span>
                        </div>
                      )}
                      {paper.is_open_access && (
                        <div>
                          <span style={{ color: 'var(--mute)' }}>开放获取: </span>
                          <span style={{ color: '#10b981' }}>✅ 是</span>
                        </div>
                      )}
                      <div style={{ gridColumn: '1 / -1' }}>
                        <span style={{ color: 'var(--mute)' }}>作者: </span>
                        <span style={{ color: 'var(--body)' }}>{paper.authors.join('; ')}</span>
                      </div>
                      {paper.abstract && (
                        <div style={{ gridColumn: '1 / -1', marginTop: 4 }}>
                          <span style={{ color: 'var(--mute)' }}>摘要: </span>
                          <p style={{ marginTop: 4, lineHeight: 1.6, color: 'var(--body)' }}>{paper.abstract}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {!isSearching && !error && results.length === 0 && (
          <div className="search-empty-state">
            <div className="search-empty-icon">
              <Search size={28} />
            </div>
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', marginBottom: 6 }}>输入关键词开始搜索</p>
            <p style={{ fontSize: 13 }}>
              聚合 CORE · OpenAlex · Semantic Scholar · Crossref · Europe PMC · arXiv 六大数据库
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
