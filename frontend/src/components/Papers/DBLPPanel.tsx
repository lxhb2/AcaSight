import React, { useState, useCallback, useEffect, useMemo } from 'react';
import {
  Search, Loader2, ExternalLink, Inbox, CheckCircle2,
  Filter, Calendar, BookOpen,
  Globe, X,
} from 'lucide-react';
import { dblpApi } from '@/services/api';
import type { DBLPPaper } from '@/services/api';

const CATEGORY_LABELS: Record<string, string> = {
  ai: '人工智能',
  cv: '计算机视觉',
  nlp: '自然语言处理',
  systems: '系统与体系结构',
  security: '安全与隐私',
  db: '数据库与数据挖掘',
  se: '软件工程',
  network: '网络与通信',
  hci: '人机交互',
  graphics: '图形学',
};

const CONFERENCE_COLORS: Record<string, string> = {
  ai: '#6366f1',
  cv: '#ec4899',
  nlp: '#06b6d4',
  systems: '#f59e0b',
  security: '#ef4444',
  db: '#10b981',
  se: '#8b5cf6',
  network: '#0ea5e9',
  hci: '#f97316',
  graphics: '#14b8a6',
};

type SearchMode = 'keyword' | 'author' | 'conference';

export const DBLPPanel: React.FC = () => {
  const [mode, setMode] = useState<SearchMode>('keyword');
  const [query, setQuery] = useState('');
  const [author, setAuthor] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedConference, setSelectedConference] = useState('');
  const [conferenceYear, setConferenceYear] = useState(new Date().getFullYear());
  const [conferenceKeyword, setConferenceKeyword] = useState('');
  const [results, setResults] = useState<DBLPPaper[]>([]);
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conferences, setConferences] = useState<Record<string, string[]>>({});
  const [importingIds, setImportingIds] = useState<Set<string>>(new Set());
  const [importedIds, setImportedIds] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [yearFrom, setYearFrom] = useState<number | undefined>(undefined);
  const [yearTo, setYearTo] = useState<number | undefined>(undefined);
  const [venueFilter, setVenueFilter] = useState('');

  useEffect(() => {
    dblpApi.listConferences().then(res => setConferences(res.conferences)).catch(() => {});
  }, []);

  const conferenceList = useMemo(() => {
    if (!selectedCategory) return [];
    return conferences[selectedCategory] || [];
  }, [selectedCategory, conferences]);

  const handleSearch = useCallback(async () => {
    setSearching(true);
    setError(null);
    setResults([]);
    try {
      let res;
      if (mode === 'keyword') {
        res = await dblpApi.search(query, 30, yearFrom, yearTo, venueFilter || undefined);
      } else if (mode === 'author') {
        res = await dblpApi.searchByAuthor(author, 30);
      } else {
        if (!selectedConference) {
          setError('请选择一个会议');
          setSearching(false);
          return;
        }
        res = await dblpApi.conferencePapers(selectedConference, conferenceYear, conferenceKeyword || undefined, 50);
      }

      if (res.error) {
        setError(res.error);
      } else {
        setResults(res.results);
        setTotal(res.total);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '搜索失败');
    } finally {
      setSearching(false);
    }
  }, [mode, query, author, selectedConference, conferenceYear, conferenceKeyword, yearFrom, yearTo, venueFilter]);

  const handleImport = useCallback(async (paper: DBLPPaper) => {
    const paperKey = paper.key || paper.doi || paper.title;
    setImportingIds(prev => new Set(prev).add(paperKey));
    try {
      await dblpApi.importPapers([paper]);
      setImportedIds(prev => new Set(prev).add(paperKey));
    } catch { /* ignore */ }
    finally {
      setImportingIds(prev => { const n = new Set(prev); n.delete(paperKey); return n; });
    }
  }, []);

  const handleBatchImport = useCallback(async () => {
    const toImport = results.filter(p => {
      const key = p.key || p.doi || p.title;
      return !importedIds.has(key);
    });
    if (toImport.length === 0) return;
    try {
      await dblpApi.importPapers(toImport);
      const newImported = new Set(importedIds);
      toImport.forEach(p => {
        const key = p.key || p.doi || p.title;
        newImported.add(key);
      });
      setImportedIds(newImported);
    } catch { /* ignore */ }
  }, [results, importedIds]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  }, [handleSearch]);

  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 20 }, (_, i) => currentYear - i);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* 标题栏 */}
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid var(--hairline)',
        background: 'var(--glass-bg, var(--bg-2))',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <Globe size={16} style={{ color: '#6366f1' }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>DBLP 会议论文检索</span>
          <span style={{ fontSize: 9, color: 'var(--mute)', background: 'var(--accent-bg-soft)', padding: '1px 6px', borderRadius: 3 }}>
            PaperHunter
          </span>
        </div>

        {/* 模式切换 */}
        <div style={{
          display: 'flex', gap: 4, padding: 3, borderRadius: 6,
          background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', marginBottom: 8,
        }}>
          {([
            { key: 'keyword' as SearchMode, label: '关键词', icon: <Search size={11} /> },
            { key: 'author' as SearchMode, label: '作者', icon: <BookOpen size={11} /> },
            { key: 'conference' as SearchMode, label: '会议', icon: <Calendar size={11} /> },
          ]).map(m => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              style={{
                flex: 1, padding: '4px 8px', borderRadius: 4, fontSize: 11,
                background: mode === m.key ? 'var(--accent)' : 'transparent',
                color: mode === m.key ? '#fff' : 'var(--body)',
                border: 'none', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                fontWeight: mode === m.key ? 600 : 400, transition: 'all 0.12s',
              }}
            >
              {m.icon} {m.label}
            </button>
          ))}
        </div>

        {/* 搜索输入区 */}
        {mode === 'keyword' && (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入关键词搜索 DBLP..."
              style={{
                flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                borderRadius: 4, padding: '6px 10px', fontSize: 12, color: 'var(--body)', outline: 'none',
              }}
            />
            <button
              onClick={() => setShowFilters(!showFilters)}
              style={{
                padding: '4px 8px', borderRadius: 4, border: '1px solid var(--hairline)',
                background: showFilters ? 'var(--accent-bg-soft)' : 'transparent',
                color: showFilters ? 'var(--accent)' : 'var(--mute)', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 3, fontSize: 10,
              }}
            >
              <Filter size={10} /> 筛选
            </button>
            <button
              onClick={handleSearch}
              disabled={searching || !query.trim()}
              style={{
                padding: '6px 12px', borderRadius: 4, border: 'none',
                background: 'var(--accent)', color: '#fff', cursor: searching ? 'wait' : 'pointer',
                fontSize: 11, display: 'flex', alignItems: 'center', gap: 4,
                opacity: searching || !query.trim() ? 0.5 : 1,
              }}
            >
              {searching ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
              搜索
            </button>
          </div>
        )}

        {mode === 'author' && (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              type="text"
              value={author}
              onChange={e => setAuthor(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入作者姓名 (如: Jiawei Han)..."
              style={{
                flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                borderRadius: 4, padding: '6px 10px', fontSize: 12, color: 'var(--body)', outline: 'none',
              }}
            />
            <button
              onClick={handleSearch}
              disabled={searching || !author.trim()}
              style={{
                padding: '6px 12px', borderRadius: 4, border: 'none',
                background: 'var(--accent)', color: '#fff', cursor: searching ? 'wait' : 'pointer',
                fontSize: 11, display: 'flex', alignItems: 'center', gap: 4,
                opacity: searching || !author.trim() ? 0.5 : 1,
              }}
            >
              {searching ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
            </button>
          </div>
        )}

        {mode === 'conference' && (
          <div>
            {/* 类别选择 */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
              {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => { setSelectedCategory(key); setSelectedConference(''); }}
                  style={{
                    padding: '2px 8px', borderRadius: 4, fontSize: 10,
                    background: selectedCategory === key ? `${CONFERENCE_COLORS[key]}20` : 'transparent',
                    color: selectedCategory === key ? CONFERENCE_COLORS[key] : 'var(--mute)',
                    border: `1px solid ${selectedCategory === key ? CONFERENCE_COLORS[key] : 'var(--hairline)'}`,
                    cursor: 'pointer', transition: 'all 0.1s',
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            {/* 会议选择 + 年份 */}
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <select
                value={selectedConference}
                onChange={e => setSelectedConference(e.target.value)}
                style={{
                  flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                  borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
                }}
              >
                <option value="">选择会议...</option>
                {conferenceList.map(c => (
                  <option key={c} value={c}>{c.toUpperCase()}</option>
                ))}
              </select>
              <select
                value={conferenceYear}
                onChange={e => setConferenceYear(Number(e.target.value))}
                style={{
                  width: 80, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                  borderRadius: 4, padding: '4px 6px', fontSize: 11, color: 'var(--body)', outline: 'none',
                }}
              >
                {yearOptions.map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
              <input
                type="text"
                value={conferenceKeyword}
                onChange={e => setConferenceKeyword(e.target.value)}
                placeholder="关键词(可选)"
                style={{
                  width: 120, background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                  borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
                }}
              />
              <button
                onClick={handleSearch}
                disabled={searching || !selectedConference}
                style={{
                  padding: '4px 10px', borderRadius: 4, border: 'none',
                  background: 'var(--accent)', color: '#fff', cursor: searching ? 'wait' : 'pointer',
                  fontSize: 11, display: 'flex', alignItems: 'center', gap: 3,
                  opacity: searching || !selectedConference ? 0.5 : 1,
                }}
              >
                {searching ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
              </button>
            </div>
          </div>
        )}

        {/* 高级筛选 */}
        {showFilters && mode === 'keyword' && (
          <div style={{
            marginTop: 8, padding: '8px 10px', borderRadius: 6,
            background: 'var(--bg-2)', border: '1px solid var(--hairline)',
            display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap',
          }}>
            <span style={{ fontSize: 10, color: 'var(--mute)' }}>年份:</span>
            <input
              type="number"
              value={yearFrom || ''}
              onChange={e => setYearFrom(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="起始"
              style={{
                width: 60, background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                borderRadius: 3, padding: '2px 6px', fontSize: 10, color: 'var(--body)', outline: 'none',
              }}
            />
            <span style={{ fontSize: 10, color: 'var(--mute)' }}>-</span>
            <input
              type="number"
              value={yearTo || ''}
              onChange={e => setYearTo(e.target.value ? Number(e.target.value) : undefined)}
              placeholder="截止"
              style={{
                width: 60, background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                borderRadius: 3, padding: '2px 6px', fontSize: 10, color: 'var(--body)', outline: 'none',
              }}
            />
            <span style={{ fontSize: 10, color: 'var(--mute)' }}>会议:</span>
            <input
              type="text"
              value={venueFilter}
              onChange={e => setVenueFilter(e.target.value)}
              placeholder="如 CVPR"
              style={{
                width: 80, background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                borderRadius: 3, padding: '2px 6px', fontSize: 10, color: 'var(--body)', outline: 'none',
              }}
            />
          </div>
        )}
      </div>

      {/* 结果区 */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {error && (
          <div style={{
            margin: '8px 12px', padding: '8px 12px', borderRadius: 6,
            background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)',
            color: '#ef4444', fontSize: 11, display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <X size={12} />
            {error}
            <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}>
              <X size={10} />
            </button>
          </div>
        )}

        {searching && (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
            <Loader2 size={20} className="animate-spin" style={{ display: 'inline', marginRight: 8 }} />
            正在检索 DBLP...
          </div>
        )}

        {!searching && results.length > 0 && (
          <>
            <div style={{
              padding: '6px 12px', borderBottom: '1px solid var(--hairline)',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'var(--canvas-soft)',
            }}>
              <span style={{ fontSize: 11, color: 'var(--mute)' }}>
                找到 <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{total}</span> 条结果，显示 {results.length} 条
              </span>
              <button
                onClick={handleBatchImport}
                style={{
                  fontSize: 10, padding: '3px 8px', borderRadius: 4,
                  border: '1px solid var(--hairline)', background: 'transparent',
                  color: 'var(--accent)', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 3,
                }}
              >
                <Inbox size={10} /> 全部入库
              </button>
            </div>

            {results.map((paper, idx) => {
              const paperKey = paper.key || paper.doi || paper.title;
              const isImported = importedIds.has(paperKey);
              const isImporting = importingIds.has(paperKey);

              return (
                <div
                  key={paperKey + idx}
                  style={{
                    padding: '8px 12px', borderBottom: '1px solid var(--hairline)',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-bg-soft)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 12, fontWeight: 500, color: 'var(--body)',
                        lineHeight: 1.4, marginBottom: 3,
                      }}>
                        {paper.title}
                      </div>
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center', fontSize: 10, color: 'var(--mute)' }}>
                        {paper.authors.length > 0 && (
                          <span>
                            {paper.authors.slice(0, 3).join(', ')}{paper.authors.length > 3 ? ` +${paper.authors.length - 3}` : ''}
                          </span>
                        )}
                        {paper.year > 0 && <span>{paper.year}</span>}
                        {paper.venue && (
                          <span style={{
                            padding: '0px 4px', borderRadius: 2,
                            background: 'var(--accent-bg-soft)', color: 'var(--accent)',
                            fontSize: 9, fontWeight: 500,
                          }}>
                            {paper.venue}
                          </span>
                        )}
                        {paper.type && (
                          <span style={{ fontSize: 9, color: 'var(--mute)' }}>
                            {paper.type}
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 3, flexShrink: 0, alignItems: 'center' }}>
                      {paper.url && (
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '3px 5px', borderRadius: 3, fontSize: 9,
                            border: '1px solid var(--hairline)', color: 'var(--mute)',
                            textDecoration: 'none', display: 'flex', alignItems: 'center',
                          }}
                          title="在 DBLP 中查看"
                        >
                          <ExternalLink size={10} />
                        </a>
                      )}
                      {paper.doi && (
                        <a
                          href={`https://doi.org/${paper.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            padding: '3px 5px', borderRadius: 3, fontSize: 9,
                            border: '1px solid var(--hairline)', color: 'var(--mute)',
                            textDecoration: 'none', display: 'flex', alignItems: 'center',
                          }}
                          title="DOI 链接"
                        >
                          DOI
                        </a>
                      )}
                      <button
                        onClick={() => handleImport(paper)}
                        disabled={isImporting || isImported}
                        style={{
                          padding: '3px 8px', borderRadius: 3, fontSize: 9,
                          border: `1px solid ${isImported ? '#10b981' : 'var(--hairline)'}`,
                          background: isImported ? 'rgba(16,185,129,0.08)' : 'transparent',
                          color: isImported ? '#10b981' : 'var(--accent)',
                          cursor: isImporting || isImported ? 'default' : 'pointer',
                          display: 'flex', alignItems: 'center', gap: 3,
                        }}
                      >
                        {isImporting ? <Loader2 size={9} className="animate-spin" /> : isImported ? <CheckCircle2 size={9} /> : <Inbox size={9} />}
                        {isImported ? '已入库' : '入库'}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </>
        )}

        {!searching && !error && results.length === 0 && (
          <div style={{
            padding: 48, textAlign: 'center', color: 'var(--mute)',
          }}>
            <Globe size={36} style={{ opacity: 0.12, marginBottom: 12 }} />
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4, color: 'var(--body)' }}>DBLP 会议论文检索</div>
            <div style={{ fontSize: 11, lineHeight: 1.6, maxWidth: 300, margin: '0 auto' }}>
              搜索计算机科学领域顶级会议论文<br />
              支持关键词、作者、会议三种检索模式<br />
              检索结果可一键导入论文库
            </div>
            <div style={{
              marginTop: 16, display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap',
            }}>
              {Object.entries(CATEGORY_LABELS).slice(0, 5).map(([key, label]) => (
                <span
                  key={key}
                  style={{
                    padding: '2px 8px', borderRadius: 4, fontSize: 9,
                    background: `${CONFERENCE_COLORS[key]}12`, color: CONFERENCE_COLORS[key],
                    border: `1px solid ${CONFERENCE_COLORS[key]}30`,
                  }}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
