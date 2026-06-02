import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Search, Loader2, CheckCircle2, Circle, AlertCircle,
  ChevronDown, ChevronUp, FileText, Lightbulb, Target,
  BookOpen, Zap, Brain, ListChecks, ExternalLink,
  X, Sparkles, Database, AlertTriangle,
} from 'lucide-react';
import {
  deepResearchApi,
  type DeepResearchResult as ApiDeepResearchResult,
  type DeepResearchSource,
  type DeepResearchMode as ApiDeepResearchMode,
} from '@/services/api';

type ResearchStep = 'search' | 'analyze' | 'synthesize' | 'cite';

interface StepStatus {
  step: ResearchStep;
  status: 'pending' | 'running' | 'completed' | 'error';
  progress: number;
  detail?: string;
}

const STEP_ORDER: ResearchStep[] = ['search', 'analyze', 'synthesize', 'cite'];

const STEP_ICONS: Record<ResearchStep, React.ReactNode> = {
  search: <Search size={14} />,
  analyze: <Brain size={14} />,
  synthesize: <Sparkles size={14} />,
  cite: <ListChecks size={14} />,
};

const MODE_ICONS: Record<string, React.ReactNode> = {
  quick: <Zap size={14} />,
  deep: <Brain size={14} />,
  comprehensive: <Target size={14} />,
};

export const DeepResearchPanel: React.FC = () => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [selectedMode, setSelectedMode] = useState('deep');
  const [isResearching, setIsResearching] = useState(false);
  const [steps, setSteps] = useState<StepStatus[]>(STEP_ORDER.map(s => ({ step: s, status: 'pending', progress: 0 })));
  const [result, setResult] = useState<ApiDeepResearchResult | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({ summary: true, papers: true, insights: false, gaps: false });
  const [availableSources, setAvailableSources] = useState<DeepResearchSource[]>([]);
  const [availableModes, setAvailableModes] = useState<ApiDeepResearchMode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef(false);

  useEffect(() => {
    deepResearchApi.getSources().then(res => {
      if (res.data) {
        setAvailableSources(res.data.sources || []);
        setAvailableModes(res.data.modes || []);
      }
    }).catch(() => {});
  }, []);

  const toggleSection = useCallback((section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const advanceStep = useCallback((stepIndex: number, status: StepStatus['status'], progress?: number) => {
    setSteps(prev => prev.map((s, i) => i === stepIndex ? { ...s, status, progress: progress ?? s.progress } : s));
  }, []);

  const handleStartResearch = useCallback(async () => {
    if (!query.trim()) return;
    abortRef.current = false;
    setIsResearching(true);
    setResult(null);
    setError(null);
    setSteps(STEP_ORDER.map(s => ({ step: s, status: 'pending', progress: 0 })));

    try {
      advanceStep(0, 'running', 10);

      const res = await deepResearchApi.start(query, selectedMode);

      if (abortRef.current) return;

      advanceStep(0, 'completed', 100);
      advanceStep(1, 'running', 50);
      advanceStep(1, 'completed', 100);
      advanceStep(2, 'running', 75);
      advanceStep(2, 'completed', 100);
      advanceStep(3, 'running', 90);
      advanceStep(3, 'completed', 100);

      if (res.success && res.data) {
        setResult(res.data);
      } else {
        setError(t('deepResearch.researchFailed'));
      }
    } catch (e: unknown) {
      if (!abortRef.current) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
        setSteps(prev => prev.map(s => s.status === 'running' ? { ...s, status: 'error', detail: msg } : s));
      }
    } finally {
      setIsResearching(false);
    }
  }, [query, selectedMode, advanceStep, t]);

  const handleAbort = useCallback(() => {
    abortRef.current = true;
    setIsResearching(false);
    setSteps(prev => prev.map(s => s.status === 'running' ? { ...s, status: 'error', detail: 'Aborted' } : s));
  }, []);

  const overallProgress = steps.reduce((sum, s) => sum + s.progress, 0) / steps.length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflow: 'auto', padding: '0 16px 16px' }}>
        {/* Query Input */}
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
            {t('deepResearch.title')}
          </label>
          <textarea
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t('search.placeholder')}
            rows={2}
            disabled={isResearching}
            style={{
              width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              background: 'var(--canvas)', border: '1px solid var(--hairline)',
              color: 'var(--ink)', fontSize: 12, resize: 'none',
              outline: 'none', lineHeight: 1.5, fontFamily: 'inherit',
            }}
          />
        </div>

        {/* Mode Selection */}
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
            {t('deepResearch.researchMode')}
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: `repeat(${availableModes.length || 3}, 1fr)`, gap: 6 }}>
            {(availableModes.length > 0 ? availableModes : [
              { id: 'quick', label: 'Quick', est_time: '3-5 min', breadth: 3, depth: 1 },
              { id: 'deep', label: 'Deep', est_time: '10-15 min', breadth: 4, depth: 2 },
              { id: 'comprehensive', label: 'Comprehensive', est_time: '20-30 min', breadth: 5, depth: 3 },
            ]).map(m => (
              <button
                key={m.id}
                onClick={() => setSelectedMode(m.id)}
                disabled={isResearching}
                style={{
                  padding: '8px 6px', borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${selectedMode === m.id ? 'var(--accent)' : 'var(--hairline)'}`,
                  background: selectedMode === m.id ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)',
                  color: selectedMode === m.id ? 'var(--accent)' : 'var(--body)',
                  cursor: isResearching ? 'not-allowed' : 'pointer',
                  textAlign: 'center', transition: 'all 0.12s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 3 }}>
                  {MODE_ICONS[m.id] || <Brain size={14} />}
                </div>
                <div style={{ fontSize: 10, fontWeight: selectedMode === m.id ? 600 : 400 }}>
                  {t(`deepResearch.mode${m.id.charAt(0).toUpperCase() + m.id.slice(1)}`, m.label)}
                </div>
                <div style={{ fontSize: 9, color: 'var(--mute)', marginTop: 1 }}>
                  {t('deepResearch.estimatedTime', { time: m.est_time })}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Available Sources */}
        {availableSources.length > 0 && (
          <div style={{ marginTop: 10 }}>
            <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
              <Database size={11} /> {t('deepResearch.availableSources')}
            </label>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {availableSources.map(src => (
                <span key={src.id} style={{
                  fontSize: 9, padding: '2px 8px', borderRadius: 'var(--radius-sm)',
                  background: src.available ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)',
                  color: src.available ? 'var(--accent)' : 'var(--mute)',
                  border: `1px solid ${src.available ? 'var(--accent)' : 'var(--hairline)'}`,
                  opacity: src.available ? 1 : 0.5,
                }}>
                  {src.name}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-soft)', border: '1px solid var(--danger)', fontSize: 11, color: 'var(--danger)', display: 'flex', alignItems: 'flex-start', gap: 6 }}>
            <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Progress Steps */}
        {(isResearching || steps.some(s => s.status !== 'pending')) && !result && (
          <div style={{ marginTop: 14, padding: 12, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--ink)' }}>{t('deepResearch.progress')}</span>
              <span style={{ fontSize: 10, color: 'var(--mute)' }}>{Math.round(overallProgress)}%</span>
            </div>
            <div style={{ height: 3, borderRadius: 2, background: 'var(--hairline)', marginBottom: 10, overflow: 'hidden' }}>
              <div style={{ width: `${overallProgress}%`, height: '100%', background: 'var(--accent)', borderRadius: 2, transition: 'width 0.3s ease' }} />
            </div>
            {steps.map((step) => (
              <div key={step.step} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', opacity: step.status === 'pending' ? 0.4 : 1 }}>
                {step.status === 'completed' ? (
                  <CheckCircle2 size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} />
                ) : step.status === 'running' ? (
                  <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent)', flexShrink: 0 }} />
                ) : step.status === 'error' ? (
                  <AlertCircle size={14} style={{ color: 'var(--danger)', flexShrink: 0 }} />
                ) : (
                  <Circle size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} />
                )}
                <span style={{ fontSize: 11, color: step.status === 'running' ? 'var(--accent)' : 'var(--body)', fontWeight: step.status === 'running' ? 600 : 400, display: 'flex', alignItems: 'center', gap: 4 }}>
                  {STEP_ICONS[step.step]}
                  {t(`deepResearch.step${step.step.charAt(0).toUpperCase() + step.step.slice(1)}`)}
                </span>
                {step.status === 'running' && (
                  <span style={{ fontSize: 9, color: 'var(--mute)', marginLeft: 'auto' }}>{Math.round(step.progress)}%</span>
                )}
                {step.status === 'completed' && (
                  <CheckCircle2 size={10} style={{ color: 'var(--accent)', marginLeft: 'auto' }} />
                )}
              </div>
            ))}
          </div>
        )}

        {/* Results */}
        {result && (
          <div style={{ marginTop: 14 }}>
            {/* Summary */}
            <div style={{ marginBottom: 10 }}>
              <button onClick={() => toggleSection('summary')} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '6px 0', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                <BookOpen size={14} style={{ color: 'var(--accent)' }} />
                {t('deepResearch.resultSummary')}
                <span style={{ fontSize: 10, color: 'var(--mute)', fontWeight: 400 }}>
                  ({result.metadata.total_papers} papers, {result.metadata.elapsed_seconds.toFixed(0)}s)
                </span>
                {expandedSections.summary ? <ChevronUp size={12} style={{ marginLeft: 'auto' }} /> : <ChevronDown size={12} style={{ marginLeft: 'auto' }} />}
              </button>
              {expandedSections.summary && (
                <div style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', fontSize: 11, color: 'var(--body)', lineHeight: 1.6 }}>
                  {result.summary}
                </div>
              )}
            </div>

            {/* Papers */}
            <div style={{ marginBottom: 10 }}>
              <button onClick={() => toggleSection('papers')} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '6px 0', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                <FileText size={14} style={{ color: 'var(--cyan)' }} />
                {t('deepResearch.resultPapers')} ({result.papers.length})
                {expandedSections.papers ? <ChevronUp size={12} style={{ marginLeft: 'auto' }} /> : <ChevronDown size={12} style={{ marginLeft: 'auto' }} />}
              </button>
              {expandedSections.papers && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {result.papers.map((paper, i) => (
                    <div key={i} style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink)', marginBottom: 2 }}>{paper.title}</div>
                          <div style={{ fontSize: 9, color: 'var(--mute)' }}>
                            {paper.authors.slice(0, 2).join(', ')}{paper.authors.length > 2 ? ' et al.' : ''} · {paper.year}
                            {paper.source && <span style={{ marginLeft: 4, padding: '0 4px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', fontSize: 8 }}>{paper.source}</span>}
                          </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          {paper.relevance > 0 && (
                            <span style={{ fontSize: 9, padding: '1px 6px', borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', color: 'var(--accent)', fontWeight: 600 }}>
                              {(paper.relevance * 100).toFixed(0)}%
                            </span>
                          )}
                          {paper.citation_count > 0 && (
                            <span style={{ fontSize: 9, color: 'var(--mute)' }}>📖{paper.citation_count}</span>
                          )}
                          {paper.doi && (
                            <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--mute)', display: 'flex' }}>
                              <ExternalLink size={10} />
                            </a>
                          )}
                          {paper.url && !paper.doi && (
                            <a href={paper.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--mute)', display: 'flex' }}>
                              <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      </div>
                      {paper.key_finding && (
                        <div style={{ fontSize: 10, color: 'var(--body)', marginTop: 4, lineHeight: 1.5 }}>{paper.key_finding}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Insights */}
            <div style={{ marginBottom: 10 }}>
              <button onClick={() => toggleSection('insights')} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '6px 0', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                <Lightbulb size={14} style={{ color: 'var(--warning)' }} />
                {t('deepResearch.resultInsights')} ({result.insights.length})
                {expandedSections.insights ? <ChevronUp size={12} style={{ marginLeft: 'auto' }} /> : <ChevronDown size={12} style={{ marginLeft: 'auto' }} />}
              </button>
              {expandedSections.insights && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {result.insights.map((insight, i) => (
                    <div key={i} style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink)', marginBottom: 3 }}>{insight.title}</div>
                      <div style={{ fontSize: 10, color: 'var(--body)', lineHeight: 1.5 }}>{insight.description}</div>
                      {insight.relatedPapers.length > 0 && (
                        <div style={{ marginTop: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {insight.relatedPapers.map((p, j) => (
                            <span key={j} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', color: 'var(--accent)' }}>{p}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Research Gaps */}
            <div style={{ marginBottom: 10 }}>
              <button onClick={() => toggleSection('gaps')} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '6px 0', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                <Target size={14} style={{ color: 'var(--danger)' }} />
                {t('deepResearch.resultGaps')} ({result.gaps.length})
                {expandedSections.gaps ? <ChevronUp size={12} style={{ marginLeft: 'auto' }} /> : <ChevronDown size={12} style={{ marginLeft: 'auto' }} />}
              </button>
              {expandedSections.gaps && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {result.gaps.map((gap, i) => (
                    <div key={i} style={{ padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink)', marginBottom: 3 }}>{gap.area}</div>
                      <div style={{ fontSize: 10, color: 'var(--body)', lineHeight: 1.5 }}>{gap.description}</div>
                      {gap.potentialQuestions.length > 0 && (
                        <div style={{ marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                          {gap.potentialQuestions.map((q, j) => (
                            <div key={j} style={{ fontSize: 9, color: 'var(--mute)', display: 'flex', alignItems: 'flex-start', gap: 4 }}>
                              <span style={{ color: 'var(--warning)' }}>?</span>
                              <span>{q}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Metadata */}
            {result.metadata && (
              <div style={{ marginTop: 6, padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>Mode: <span style={{ color: 'var(--body)' }}>{result.metadata.mode}</span></span>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>Queries: <span style={{ color: 'var(--body)' }}>{result.metadata.total_queries}</span></span>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>Sources: <span style={{ color: 'var(--body)' }}>{result.metadata.sources_used.join(', ')}</span></span>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>B×D: <span style={{ color: 'var(--body)' }}>{result.metadata.breadth}×{result.metadata.depth}</span></span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom Action Bar */}
      <div style={{
        padding: '10px 16px', borderTop: '1px solid var(--hairline)',
        background: 'var(--glass-bg)', display: 'flex', gap: 8,
      }}>
        {!isResearching ? (
          <button
            onClick={handleStartResearch}
            disabled={!query.trim()}
            style={{
              flex: 1, padding: '8px 16px', borderRadius: 'var(--radius-sm)',
              background: 'var(--accent)', color: 'var(--on-primary)', border: 'none',
              cursor: !query.trim() ? 'not-allowed' : 'pointer',
              fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              opacity: !query.trim() ? 0.6 : 1,
            }}
          >
            <Search size={14} />
            {t('deepResearch.startResearch')}
          </button>
        ) : (
          <button
            onClick={handleAbort}
            style={{
              flex: 1, padding: '8px 16px', borderRadius: 'var(--radius-sm)',
              background: 'var(--danger-soft)', color: 'var(--danger)', border: '1px solid var(--danger)',
              cursor: 'pointer', fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            <X size={14} />
            {t('common.cancel')}
          </button>
        )}
      </div>
    </div>
  );
};
