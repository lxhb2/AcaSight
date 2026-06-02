import React, { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Filter, Download, BookOpen, Calendar, User, ExternalLink, Star, ChevronDown, X, AlertCircle, Database, BookmarkPlus, CheckCircle2, Loader2, FileText, BarChart3, PieChart, TrendingUp, Inbox, Copy, Brain, Zap } from 'lucide-react';
import { searchApi, zoteroApi } from '@/services/api';
import { useFileOpen } from '@/contexts/FileOpenContext';
import { VirtualList } from '@/hooks/useVirtualScroll';
import { DeepResearchPanel } from '@/components/Search/DeepResearchPanel';
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
  { label: '综合排序', value: 'hybrid' },
  { label: '相关度', value: 'relevance' },
  { label: '引用数 ↓', value: 'citations' },
  { label: '最新', value: 'date_desc' },
  { label: '最早', value: 'date_asc' },
];

/** 混合排序权重：引用数 40% + 出版年衰减 35% + 关键词匹配度 25% */
const HYBRID_WEIGHTS = { citations: 0.40, year: 0.35, relevance: 0.25 };
const CURRENT_YEAR = new Date().getFullYear();

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

interface SearchResultCardProps {
  paper: UnifiedPaper;
  expandedId: string | null;
  setExpandedId: (id: string | null) => void;
  onOpenInReader: (paper: UnifiedPaper) => void;
}

const SearchResultCard: React.FC<SearchResultCardProps> = React.memo(({
  paper, expandedId, setExpandedId, onOpenInReader,
}) => {
  const { t } = useTranslation();
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set());
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [importingIds, setImportingIds] = useState<Set<string>>(new Set());
  const [importedIds, setImportedIds] = useState<Set<string>>(new Set());
  const [dupIds, setDupIds] = useState<Set<string>>(new Set());

  const handleSaveToZotero = useCallback(async () => {
    setSavingIds(prev => new Set(prev).add(paper.id));
    try {
      await zoteroApi.writeItem({
        action: 'create',
        itemType: 'journalArticle',
        fields: {
          title: paper.title,
          date: paper.year ? String(paper.year) : '',
          DOI: paper.doi || '',
          url: paper.pdf_url || '',
        },
        creators: paper.authors.map(a => ({ firstName: a.split(' ')[0] || a, lastName: a.split(' ').slice(1).join(' ') || a, creatorType: 'author' })),
      });
      setSavedIds(prev => new Set(prev).add(paper.id));
    } catch (_e: unknown) {
      // silent
    } finally {
      setSavingIds(prev => { const n = new Set(prev); n.delete(paper.id); return n; });
    }
  }, [paper]);

  const handleImportToDb = useCallback(async () => {
    setImportingIds(prev => new Set(prev).add(paper.id));
    try {
      const res = await searchApi.importPaper({
        title: paper.title,
        authors: paper.authors,
        year: paper.year,
        abstract: paper.abstract,
        doi: paper.doi,
      });
      if ((res as Record<string, unknown>).duplicate) {
        setDupIds(prev => new Set(prev).add(paper.id));
      } else {
        setImportedIds(prev => new Set(prev).add(paper.id));
      }
    } catch (_e: unknown) {
      // silent
    } finally {
      setImportingIds(prev => { const n = new Set(prev); n.delete(paper.id); return n; });
    }
  }, [paper]);

  const handleOpenInReader = useCallback(() => {
    onOpenInReader(paper);
  }, [paper, onOpenInReader]);

  return (
    <div className="search-result-card">
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
            {paper.cited_by_count.toLocaleString()} {t('search.citations')}
          </span>
        )}
      </div>

      {paper.abstract && (
        <p className="search-result-abstract" style={{ maxHeight: 60, overflow: 'hidden' }}>{paper.abstract}</p>
      )}

      <div className="search-result-actions">
        <button
          onClick={() => setExpandedId(expandedId === paper.id ? null : paper.id)}
          className="search-action-btn"
        >
          <ChevronDown size={12} className={`transition-transform ${expandedId === paper.id ? 'rotate-180' : ''}`} />
          {t('search.details')}
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
            <button onClick={handleOpenInReader} className="search-action-btn success">
              <FileText size={12} />
              {t('search.openInReader')}
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
          onClick={handleSaveToZotero}
          disabled={savingIds.has(paper.id) || savedIds.has(paper.id)}
          className="search-action-btn"
          style={savedIds.has(paper.id) ? { color: '#10b981', borderColor: '#10b981' } : {}}
        >
          {savingIds.has(paper.id) ? <Loader2 size={12} className="animate-spin" /> : savedIds.has(paper.id) ? <CheckCircle2 size={12} /> : <BookmarkPlus size={12} />}
          {savedIds.has(paper.id) ? t('search.saved') : 'Zotero'}
        </button>

        <button
          onClick={handleImportToDb}
          disabled={importingIds.has(paper.id) || importedIds.has(paper.id) || dupIds.has(paper.id)}
          className="search-action-btn"
          style={importedIds.has(paper.id) ? { color: '#6366f1', borderColor: '#6366f1' } : dupIds.has(paper.id) ? { color: 'var(--mute)', borderColor: 'var(--hairline)' } : {}}
          title={dupIds.has(paper.id) ? t('search.alreadyExists') : t('search.importToDb')}
        >
          {importingIds.has(paper.id) ? <Loader2 size={12} className="animate-spin" /> : importedIds.has(paper.id) ? <CheckCircle2 size={12} /> : dupIds.has(paper.id) ? <Copy size={12} /> : <Inbox size={12} />}
          {importedIds.has(paper.id) ? t('search.imported') : dupIds.has(paper.id) ? t('search.duplicate') : t('search.import')}
        </button>
      </div>

      {expandedId === paper.id && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--hairline)', animation: 'floating-panel-appear 0.15s ease' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
            <div>
              <span style={{ color: 'var(--mute)' }}>{t('search.source')}: </span>
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
                <span style={{ color: 'var(--mute)' }}>{t('search.citationCount')}: </span>
                <span style={{ color: 'var(--body)' }}>{paper.cited_by_count.toLocaleString()}</span>
              </div>
            )}
            {paper.year && (
              <div>
                <span style={{ color: 'var(--mute)' }}>{t('search.year')}: </span>
                <span style={{ color: 'var(--body)' }}>{paper.year}</span>
              </div>
            )}
            {paper.journal && (
              <div>
                <span style={{ color: 'var(--mute)' }}>{t('search.journal')}: </span>
                <span style={{ color: 'var(--body)' }}>{paper.journal}</span>
              </div>
            )}
            {paper.is_open_access && (
              <div>
                <span style={{ color: 'var(--mute)' }}>{t('search.openAccess')}: </span>
                <span style={{ color: '#10b981' }}>✅</span>
              </div>
            )}
            <div style={{ gridColumn: '1 / -1' }}>
              <span style={{ color: 'var(--mute)' }}>{t('search.authors')}: </span>
              <span style={{ color: 'var(--body)' }}>{paper.authors.join('; ')}</span>
            </div>
            {paper.abstract && (
              <div style={{ gridColumn: '1 / -1', marginTop: 4 }}>
                <span style={{ color: 'var(--mute)' }}>{t('search.abstract')}: </span>
                <p style={{ marginTop: 4, lineHeight: 1.6, color: 'var(--body)' }}>{paper.abstract}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  const prevExpanded = prevProps.expandedId === prevProps.paper.id;
  const nextExpanded = nextProps.expandedId === nextProps.paper.id;
  return prevExpanded === nextExpanded
    && prevProps.paper.id === nextProps.paper.id
    && prevProps.onOpenInReader === nextProps.onOpenInReader;
});

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

function sortPapers(papers: UnifiedPaper[], sort: string, query?: string): UnifiedPaper[] {
  const sorted = [...papers];
  switch (sort) {
    case 'hybrid': {
      // 综合排序：引用数 40% + 出版年 35% + 关键词匹配 25%
      const searchTerms = (query || '').toLowerCase().split(/\s+/).filter(Boolean);
      const maxCitations = Math.max(1, ...papers.map(p => p.cited_by_count ?? 0));
      sorted.sort((a, b) => {
        // 引用分数（对数归一化）
        const citeA = Math.log10((a.cited_by_count ?? 0) + 1) / Math.log10(maxCitations + 1);
        const citeB = Math.log10((b.cited_by_count ?? 0) + 1) / Math.log10(maxCitations + 1);
        // 出版年衰减（越新越靠近 1.0）
        const yearA = ((a.year ?? CURRENT_YEAR - 10) - (CURRENT_YEAR - 20)) / 20;
        const yearB = ((b.year ?? CURRENT_YEAR - 10) - (CURRENT_YEAR - 20)) / 20;
        // 关键词匹配得分
        const titleA = a.title.toLowerCase();
        const titleB = b.title.toLowerCase();
        const relA = searchTerms.length ? searchTerms.reduce((s, t) => s + (titleA.includes(t) ? 1 : 0), 0) / searchTerms.length : 0.5;
        const relB = searchTerms.length ? searchTerms.reduce((s, t) => s + (titleB.includes(t) ? 1 : 0), 0) / searchTerms.length : 0.5;
        const scoreA = HYBRID_WEIGHTS.citations * citeA + HYBRID_WEIGHTS.year * yearA + HYBRID_WEIGHTS.relevance * relA;
        const scoreB = HYBRID_WEIGHTS.citations * citeB + HYBRID_WEIGHTS.year * yearB + HYBRID_WEIGHTS.relevance * relB;
        return scoreB - scoreA;
      });
      break;
    }
    case 'citations':
      sorted.sort((a, b) => (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0));
      break;
    case 'date_desc':
      sorted.sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
      break;
    case 'date_asc':
      sorted.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
      break;
    // 'relevance' = 保持原始结果顺序（API 已排序）
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
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UnifiedPaper[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [selectedSort, setSelectedSort] = useState('relevance');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sources, setSources] = useState(SOURCES);
  const [showSources, setShowSources] = useState(false);
  const [importedIds, setImportedIds] = useState<Set<string>>(new Set());
  const [totalCount, setTotalCount] = useState(0);
  const [showChart, setShowChart] = useState(false);
  const [searchMode, setSearchMode] = useState<'normal' | 'deep'>('normal');

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
        const sorted = sortPapers(merged, selectedSort, q);
        setResults(sorted);
        setTotalCount(sorted.length);
      } else {
        setResults([]);
        setTotalCount(0);
      }
    } catch (e: unknown) {
      setError((e instanceof Error ? e.message : String(e)) || '搜索失败，请检查网络连接');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query, checkedSources, selectedFilter, selectedSort]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  }, [handleSearch]);

  const displayedResults = useMemo(
    () => sortPapers(results, selectedSort, query),
    [results, selectedSort, query]
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <h1 className="search-hero-title">{searchMode === 'deep' ? t('deepResearch.title') : 'AI 文献检索'}</h1>
          <div style={{ display: 'flex', gap: 4, padding: 3, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
            <button
              onClick={() => setSearchMode('normal')}
              style={{
                padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: 11,
                background: searchMode === 'normal' ? 'var(--accent)' : 'transparent',
                color: searchMode === 'normal' ? 'var(--on-primary)' : 'var(--body)',
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                fontWeight: searchMode === 'normal' ? 600 : 400, transition: 'all 0.12s',
              }}
            >
              <Zap size={12} /> {t('search.button')}
            </button>
            <button
              onClick={() => setSearchMode('deep')}
              style={{
                padding: '4px 12px', borderRadius: 'var(--radius-sm)', fontSize: 11,
                background: searchMode === 'deep' ? 'var(--accent)' : 'transparent',
                color: searchMode === 'deep' ? 'var(--on-primary)' : 'var(--body)',
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
                fontWeight: searchMode === 'deep' ? 600 : 400, transition: 'all 0.12s',
              }}
            >
              <Brain size={12} /> {t('deepResearch.title')}
            </button>
          </div>
        </div>

        {searchMode === 'deep' && <DeepResearchPanel />}
      </div>

      {searchMode === 'normal' && (
      <React.Fragment>
        <div className="search-bar-wrap" role="search">
          <div className="search-input-wrap">
            <Search className="search-icon" size={18} />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入研究主题、关键词或论文标题（英文效果更好）..."
              className="search-input"
              aria-label="搜索文献"
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
                {selectedSort === 'hybrid' && <span style={{ fontSize: 10, marginLeft: 6, color: 'var(--body)', background: 'var(--accent-bg-soft)', padding: '1px 6px', borderRadius: 3 }}>引用40% · 年份35% · 相关度25%</span>}
                {selectedSort === 'citations' && <span style={{ fontSize: 10, marginLeft: 6, color: 'var(--body)', background: 'var(--accent-bg-soft)', padding: '1px 6px', borderRadius: 3 }}>按引用次数降序</span>}
                {selectedSort === 'date_desc' && <span style={{ fontSize: 10, marginLeft: 6, color: 'var(--body)', background: 'var(--accent-bg-soft)', padding: '1px 6px', borderRadius: 3 }}>最新发表优先</span>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                {displayedResults.length > 0 && (
                  <button
                    onClick={async () => {
                      const papers = displayedResults.map(p => ({
                        title: p.title,
                        authors: p.authors,
                        abstract: p.abstract ?? undefined,
                        doi: p.doi ?? undefined,
                        year: p.year ?? undefined,
                        journal: p.journal ?? undefined,
                        pdf_url: p.pdf_url ?? undefined,
                        citation_count: p.cited_by_count ?? 0,
                        tags: [],
                      }));
                      try {
                        const res = await searchApi.batchImportPapers(papers);
                        const newImported = new Set(importedIds);
                        res.imported_titles?.forEach((t: string) => {
                          const match = displayedResults.find(p => p.title === t);
                          if (match) newImported.add(match.id);
                        });
                        setImportedIds(newImported);
                      } catch {}
                    }}
                    className="search-action-btn"
                    style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}
                  >
                    <Inbox size={12} />
                    全部入库
                  </button>
                )}
                <button
                  onClick={() => setShowChart(prev => !prev)}
                  className={`search-chart-btn ${showChart ? 'active' : ''}`}
                >
                  <BarChart3 size={14} />
                  {showChart ? '隐藏图表' : '图表分析'}
                </button>
              </div>
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

            {displayedResults.length >= 50 ? (
              <VirtualList
                items={displayedResults}
                itemHeight={180}
                overscan={3}
                renderItem={(paper) => (
                  <SearchResultCard
                    paper={paper}
                    expandedId={expandedId}
                    setExpandedId={setExpandedId}
                    onOpenInReader={handleOpenInReader}
                  />
                )}
              />
            ) : (
              displayedResults.map((paper) => (
                <SearchResultCard
                  key={paper.id}
                  paper={paper}
                  expandedId={expandedId}
                  setExpandedId={setExpandedId}
                  onOpenInReader={handleOpenInReader}
                />
              ))
            )}
          </div>
        )}

        {!isSearching && !error && query.trim() === '' && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 360, padding: 48, textAlign: 'center' }}>
            {/* 主视觉 */}
            <div style={{
              width: 88, height: 88, borderRadius: 28, marginBottom: 28,
              background: 'linear-gradient(135deg, rgba(99,102,241,0.12), rgba(6,182,212,0.08))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              border: '1px solid var(--hairline)', backdropFilter: 'blur(8px)',
            }}>
              <Search size={36} style={{ color: '#6366f1', opacity: 0.8 }} />
            </div>

            {/* 标题 */}
            <h2 style={{
              fontSize: 22, fontWeight: 700, color: 'var(--ink)', marginBottom: 6,
              letterSpacing: -0.3, lineHeight: 1.3,
            }}>
              学术文献智能搜索
            </h2>
            <p style={{
              fontSize: 14, color: 'var(--mute)', marginBottom: 32,
              maxWidth: 420, lineHeight: 1.6,
            }}>
              一次输入，并行检索 6 大开放学术数据库，覆盖 2.2 亿+ 篇论文
            </p>

            {/* 搜索技巧卡片 */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12,
              maxWidth: 560, width: '100%', marginBottom: 28,
            }}>
              {[
                { icon: <Search size={15} />, title: '关键词搜索', desc: '输入研究方向或主题词\n自动匹配最相关的论文', color: '#6366f1' },
                { icon: <ExternalLink size={15} />, title: 'DOI 精确检索', desc: '直接粘贴论文 DOI\n秒级定位目标文献', color: '#06b6d4' },
                { icon: <FileText size={15} />, title: '以文搜文', desc: '上传一篇 PDF 论文\n找到语义相似的研究', color: '#10b981' },
              ].map((tip, i) => (
                <div key={i} style={{
                  padding: '16px 14px', borderRadius: 16,
                  background: 'var(--glass-bg)', border: '1px solid var(--hairline)',
                  backdropFilter: 'blur(var(--glass-blur))',
                  textAlign: 'left', transition: 'all 0.2s',
                }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: 10, marginBottom: 10,
                    background: `${tip.color}14`, display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                  }}>
                    {/* color applied via style */}
                    <span style={{ color: tip.color, display: 'flex' }}>{tip.icon}</span>
                  </div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>{tip.title}</div>
                  <div style={{ fontSize: 11, color: 'var(--mute)', lineHeight: 1.55, whiteSpace: 'pre-line' }}>{tip.desc}</div>
                </div>
              ))}
            </div>

            {/* 底部统计 */}
            <div style={{
              display: 'flex', gap: 24, padding: '16px 28px',
              borderRadius: 14, background: 'var(--accent-bg-soft)',
              border: '1px solid var(--hairline)',
            }}>
              {[
                { value: '2.2 亿+', label: '收录论文' },
                { value: '6', label: '数据源' },
                { value: '< 3s', label: '平均响应' },
              ].map((stat, i) => (
                <div key={i} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--accent)' }}>{stat.value}</div>
                  <div style={{ fontSize: 11, color: 'var(--mute)', marginTop: 2 }}>{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!isSearching && !error && results.length === 0 && query.trim() !== '' && (
          <div className="search-empty-state">
            <div className="search-empty-icon">
              <Search size={28} />
            </div>
            <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)', marginBottom: 6 }}>未找到相关文献</p>
            <p style={{ fontSize: 13, color: 'var(--mute)', marginBottom: 16 }}>
              建议尝试更宽泛的关键词，或更换英文检索词
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 320, width: '100%' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 2 }}>搜索技巧</div>
              {[
                { tip: '使用英文关键词获取更多结果', icon: '🔤' },
                { tip: '尝试同义词或缩写（如 ML → Machine Learning）', icon: '💡' },
                { tip: '启用更多数据源扩大检索范围', icon: '📡' },
                { tip: '使用引号精确匹配短语 "deep learning"', icon: '🎯' },
              ].map((item, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 10px', borderRadius: 8, background: 'var(--canvas-soft)', fontSize: 12, color: 'var(--body)' }}>
                  <span style={{ fontSize: 14 }}>{item.icon}</span>
                  <span>{item.tip}</span>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 16 }}>
              <button onClick={() => { setQuery(''); (document.querySelector('.search-input') as HTMLInputElement)?.focus(); }}
                style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, background: 'var(--accent-bg-soft)', border: '1px solid var(--hairline)', color: 'var(--ink)', cursor: 'pointer' }}>
                重新搜索
              </button>
              <button onClick={() => { setSources(prev => prev.map(s => ({ ...s, checked: true }))) }}
                style={{ padding: '6px 14px', borderRadius: 8, fontSize: 12, background: 'var(--glass-bg)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: 'pointer' }}>
                启用全部数据源
              </button>
            </div>
          </div>
        )}
        </div>
      </React.Fragment>
      )}
    </div>
  );
};
