import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Activity, CheckCircle2, XCircle, Loader2, Wand2, Code,
  Image as ImageIcon, AlertTriangle, ChevronDown, ChevronUp,
  RefreshCw, FileText,
} from 'lucide-react';
import {
  archApi,
  type ArchStatus,
  type VisualEvalResult,
} from '@/services/api';

const SERVICE_KEYS: Array<keyof Pick<ArchStatus, 'visual_evaluator' | 'stage_orchestrator' | 'loop_detector' | 'ai_formatter'>> = [
  'visual_evaluator',
  'stage_orchestrator',
  'loop_detector',
  'ai_formatter',
];

const FORMAT_OPTIONS = ['text', 'json', 'svg', 'code'] as const;

export const ArchPanel: React.FC = () => {
  const { t } = useTranslation();

  const [status, setStatus] = useState<ArchStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [statusError, setStatusError] = useState<string | null>(null);

  const [expandedStatus, setExpandedStatus] = useState(true);
  const [expandedFormat, setExpandedFormat] = useState(false);
  const [expandedEval, setExpandedEval] = useState(false);

  const [formatInput, setFormatInput] = useState('');
  const [formatExpected, setFormatExpected] = useState<string>('text');
  const [formatStrict, setFormatStrict] = useState(false);
  const [formatLoading, setFormatLoading] = useState(false);
  const [formatResult, setFormatResult] = useState<{ format: string; content: any; warnings: string[] } | null>(null);
  const [formatError, setFormatError] = useState<string | null>(null);

  const [evalImageBase64, setEvalImageBase64] = useState('');
  const [evalCriteria, setEvalCriteria] = useState('');
  const [evalStyle, setEvalStyle] = useState('default');
  const [evalMaxRetries, setEvalMaxRetries] = useState(3);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalResult, setEvalResult] = useState<VisualEvalResult | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [expandedHistory, setExpandedHistory] = useState(false);

  const fetchStatus = useCallback(async () => {
    setStatusLoading(true);
    setStatusError(null);
    try {
      const res = await archApi.getStatus();
      if (res.success && res.data) {
        setStatus(res.data);
      } else {
        setStatusError(t('arch.statusFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setStatusError(msg);
    } finally {
      setStatusLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleFormat = useCallback(async () => {
    if (!formatInput.trim()) return;
    setFormatLoading(true);
    setFormatError(null);
    setFormatResult(null);
    try {
      const res = await archApi.format(formatInput, formatExpected, formatStrict);
      if (res.success && res.data) {
        setFormatResult(res.data);
      } else {
        setFormatError(t('arch.formatFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setFormatError(msg);
    } finally {
      setFormatLoading(false);
    }
  }, [formatInput, formatExpected, formatStrict, t]);

  const handleEvaluate = useCallback(async () => {
    if (!evalImageBase64.trim()) return;
    setEvalLoading(true);
    setEvalError(null);
    setEvalResult(null);
    try {
      const res = await archApi.evaluateVisual(evalImageBase64, {
        criteria: evalCriteria || undefined,
        style: evalStyle,
        maxRetries: evalMaxRetries,
      });
      if (res.success && res.data) {
        setEvalResult(res.data);
      } else {
        setEvalError(t('arch.evalFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setEvalError(msg);
    } finally {
      setEvalLoading(false);
    }
  }, [evalImageBase64, evalCriteria, evalStyle, evalMaxRetries, t]);

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <Activity size={18} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)' }}>{t('arch.title')}</span>
        <button
          onClick={fetchStatus}
          disabled={statusLoading}
          style={{
            marginLeft: 'auto', width: 28, height: 28, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
            color: 'var(--body)', cursor: statusLoading ? 'wait' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <RefreshCw size={13} style={{ animation: statusLoading ? 'spin 1s linear infinite' : 'none' }} />
        </button>
      </div>

      {statusError && (
        <div style={{
          padding: '8px 12px', marginBottom: 16, borderRadius: 'var(--radius-sm)',
          background: 'var(--danger-soft)', border: '1px solid var(--danger)',
          display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--danger)',
        }}>
          <AlertTriangle size={13} />
          <span style={{ flex: 1 }}>{statusError}</span>
          <button onClick={() => setStatusError(null)} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', padding: 0 }}>
            <XCircle size={14} />
          </button>
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => setExpandedStatus(prev => !prev)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 12px', borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
            cursor: 'pointer', textAlign: 'left' as const,
          }}
        >
          <Activity size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)', flex: 1 }}>{t('arch.serviceStatus')}</span>
          {expandedStatus ? <ChevronUp size={14} style={{ color: 'var(--mute)' }} /> : <ChevronDown size={14} style={{ color: 'var(--mute)' }} />}
        </button>

        {expandedStatus && (
          <div style={{
            marginTop: 6, padding: 12, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
          }}>
            {statusLoading && !status ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16, color: 'var(--mute)', gap: 8, fontSize: 12 }}>
                <Loader2 size={14} className="animate-spin" /> {t('arch.loading')}
              </div>
            ) : status ? (
              <>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
                  {SERVICE_KEYS.map(key => (
                    <span
                      key={key}
                      style={{
                        fontSize: 9, padding: '2px 8px', borderRadius: 'var(--radius-sm)',
                        background: status[key] ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)',
                        color: status[key] ? 'var(--accent)' : 'var(--mute)',
                        border: `1px solid ${status[key] ? 'var(--accent)' : 'var(--hairline)'}`,
                        display: 'flex', alignItems: 'center', gap: 3,
                      }}
                    >
                      {status[key] ? <CheckCircle2 size={9} /> : <XCircle size={9} />}
                      {t(`arch.${key}`)}
                    </span>
                  ))}
                </div>

                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, display: 'block', marginBottom: 4 }}>
                    {t('arch.sciStyles')}
                  </span>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {status.sci_styles.map(s => (
                      <span key={s} style={{
                        fontSize: 10, padding: '2px 6px', borderRadius: 'var(--radius-sm)',
                        background: 'var(--accent-bg-soft)', color: 'var(--accent)',
                      }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, display: 'block', marginBottom: 4 }}>
                    {t('arch.outputFormats')}
                  </span>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {status.output_formats.map(f => (
                      <span key={f} style={{
                        fontSize: 10, padding: '2px 6px', borderRadius: 'var(--radius-sm)',
                        background: 'var(--canvas-soft)', color: 'var(--body)', border: '1px solid var(--hairline)',
                      }}>
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              </>
            ) : null}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => setExpandedFormat(prev => !prev)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 12px', borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
            cursor: 'pointer', textAlign: 'left' as const,
          }}
        >
          <Code size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)', flex: 1 }}>{t('arch.formatTool')}</span>
          {expandedFormat ? <ChevronUp size={14} style={{ color: 'var(--mute)' }} /> : <ChevronDown size={14} style={{ color: 'var(--mute)' }} />}
        </button>

        {expandedFormat && (
          <div style={{
            marginTop: 6, padding: 12, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
          }}>
            <div style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, marginBottom: 4, display: 'block' }}>
                {t('arch.rawResponse')}
              </label>
              <textarea
                value={formatInput}
                onChange={e => setFormatInput(e.target.value)}
                placeholder={t('arch.rawResponsePlaceholder')}
                rows={5}
                style={{
                  width: '100%', padding: '6px 10px',
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 11,
                  outline: 'none', fontFamily: 'monospace', resize: 'vertical' as const,
                  boxSizing: 'border-box' as const,
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500 }}>{t('arch.expectedFormat')}</span>
                <select
                  value={formatExpected}
                  onChange={e => setFormatExpected(e.target.value)}
                  style={{
                    height: 28, padding: '0 8px',
                    background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                    borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 11,
                    outline: 'none',
                  }}
                >
                  {FORMAT_OPTIONS.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500 }}>{t('arch.strict')}</span>
                <button
                  onClick={() => setFormatStrict(prev => !prev)}
                  style={{
                    width: 36, height: 20, borderRadius: 10, border: 'none',
                    background: formatStrict ? 'var(--accent)' : 'var(--canvas-soft)',
                    cursor: 'pointer', position: 'relative', transition: 'background 0.2s',
                  }}
                >
                  <span style={{
                    position: 'absolute', top: 2,
                    left: formatStrict ? 18 : 2,
                    width: 16, height: 16, borderRadius: '50%',
                    background: formatStrict ? 'var(--on-primary)' : 'var(--mute)',
                    transition: 'left 0.2s',
                  }} />
                </button>
              </div>
            </div>

            <button
              onClick={handleFormat}
              disabled={formatLoading || !formatInput.trim()}
              style={{
                padding: '6px 14px', borderRadius: 'var(--radius-sm)',
                background: 'var(--accent)', color: 'var(--on-primary)',
                border: 'none', cursor: formatLoading ? 'wait' : 'pointer',
                fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 5,
                opacity: formatLoading || !formatInput.trim() ? 0.6 : 1,
              }}
            >
              {formatLoading ? <Loader2 size={12} className="animate-spin" /> : <Wand2 size={12} />}
              {t('arch.formatAction')}
            </button>

            {formatError && (
              <div style={{
                marginTop: 10, padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                background: 'var(--danger-soft)', color: 'var(--danger)', fontSize: 11,
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <AlertTriangle size={12} /> {formatError}
              </div>
            )}

            {formatResult && (
              <div style={{ marginTop: 10 }}>
                <div style={{
                  padding: '8px 10px', borderRadius: 'var(--radius-sm)',
                  background: 'var(--accent-bg-soft)', border: '1px solid var(--accent)',
                  fontSize: 11, marginBottom: 6,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <CheckCircle2 size={12} style={{ color: 'var(--accent)' }} />
                  <span style={{ fontWeight: 500, color: 'var(--accent)' }}>{t('arch.formatResult')}</span>
                  <span style={{ color: 'var(--body)', marginLeft: 4 }}>{formatResult.format}</span>
                </div>

                <div style={{
                  padding: '8px 10px', borderRadius: 'var(--radius-sm)',
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  fontSize: 11, marginBottom: 6,
                }}>
                  <span style={{ color: 'var(--mute)', fontWeight: 500, display: 'block', marginBottom: 4 }}>{t('arch.content')}</span>
                  <pre style={{
                    margin: 0, padding: '4px 6px', borderRadius: 'var(--radius-sm)',
                    background: 'var(--canvas)', fontSize: 10, color: 'var(--body)',
                    overflow: 'auto', maxHeight: 200, whiteSpace: 'pre-wrap' as const,
                    wordBreak: 'break-all' as const,
                  }}>
                    {typeof formatResult.content === 'string' ? formatResult.content : JSON.stringify(formatResult.content, null, 2)}
                  </pre>
                </div>

                {formatResult.warnings.length > 0 && (
                  <div style={{
                    padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                    background: 'var(--danger-soft)', border: '1px solid var(--danger)',
                    fontSize: 10,
                  }}>
                    {formatResult.warnings.map((w, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--danger)', marginBottom: 2 }}>
                        <AlertTriangle size={10} /> {w}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ marginBottom: 24 }}>
        <button
          onClick={() => setExpandedEval(prev => !prev)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 12px', borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
            cursor: 'pointer', textAlign: 'left' as const,
          }}
        >
          <ImageIcon size={14} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--ink)', flex: 1 }}>{t('arch.visualEval')}</span>
          {expandedEval ? <ChevronUp size={14} style={{ color: 'var(--mute)' }} /> : <ChevronDown size={14} style={{ color: 'var(--mute)' }} />}
        </button>

        {expandedEval && (
          <div style={{
            marginTop: 6, padding: 12, borderRadius: 'var(--radius-sm)',
            background: 'var(--canvas)', border: '1px solid var(--hairline)',
          }}>
            <div style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, marginBottom: 4, display: 'block' }}>
                {t('arch.imageBase64')}
              </label>
              <textarea
                value={evalImageBase64}
                onChange={e => setEvalImageBase64(e.target.value)}
                placeholder={t('arch.imageBase64Placeholder')}
                rows={4}
                style={{
                  width: '100%', padding: '6px 10px',
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 11,
                  outline: 'none', fontFamily: 'monospace', resize: 'vertical' as const,
                  boxSizing: 'border-box' as const,
                }}
              />
            </div>

            <div style={{ marginBottom: 8 }}>
              <label style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500, marginBottom: 4, display: 'block' }}>
                {t('arch.criteria')}
              </label>
              <input
                value={evalCriteria}
                onChange={e => setEvalCriteria(e.target.value)}
                placeholder={t('arch.criteriaPlaceholder')}
                style={{
                  width: '100%', height: 32, padding: '0 10px',
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 12,
                  outline: 'none', boxSizing: 'border-box' as const,
                }}
              />
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500 }}>{t('arch.style')}</span>
                <select
                  value={evalStyle}
                  onChange={e => setEvalStyle(e.target.value)}
                  style={{
                    height: 28, padding: '0 8px',
                    background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                    borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 11,
                    outline: 'none',
                  }}
                >
                  <option value="default">default</option>
                  {status?.sci_styles.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 11, color: 'var(--mute)', fontWeight: 500 }}>{t('arch.maxRetries')}</span>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={evalMaxRetries}
                  onChange={e => setEvalMaxRetries(Number(e.target.value) || 3)}
                  style={{
                    width: 56, height: 28, padding: '0 8px', textAlign: 'center',
                    background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                    borderRadius: 'var(--radius-sm)', color: 'var(--ink)', fontSize: 11,
                    outline: 'none', boxSizing: 'border-box' as const,
                  }}
                />
              </div>
            </div>

            <button
              onClick={handleEvaluate}
              disabled={evalLoading || !evalImageBase64.trim()}
              style={{
                padding: '6px 14px', borderRadius: 'var(--radius-sm)',
                background: 'var(--accent)', color: 'var(--on-primary)',
                border: 'none', cursor: evalLoading ? 'wait' : 'pointer',
                fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 5,
                opacity: evalLoading || !evalImageBase64.trim() ? 0.6 : 1,
              }}
            >
              {evalLoading ? <Loader2 size={12} className="animate-spin" /> : <ImageIcon size={12} />}
              {t('arch.evalAction')}
            </button>

            {evalError && (
              <div style={{
                marginTop: 10, padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                background: 'var(--danger-soft)', color: 'var(--danger)', fontSize: 11,
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <AlertTriangle size={12} /> {evalError}
              </div>
            )}

            {evalResult && (
              <div style={{ marginTop: 10 }}>
                <div style={{
                  padding: '8px 10px', borderRadius: 'var(--radius-sm)',
                  background: evalResult.passed ? 'var(--accent-bg-soft)' : 'var(--danger-soft)',
                  border: `1px solid ${evalResult.passed ? 'var(--accent)' : 'var(--danger)'}`,
                  fontSize: 11, marginBottom: 6,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  {evalResult.passed ? (
                    <CheckCircle2 size={12} style={{ color: 'var(--accent)' }} />
                  ) : (
                    <XCircle size={12} style={{ color: 'var(--danger)' }} />
                  )}
                  <span style={{ fontWeight: 600, color: evalResult.passed ? 'var(--accent)' : 'var(--danger)' }}>
                    {evalResult.passed ? t('arch.evalPassed') : t('arch.evalFailed')}
                  </span>
                  <span style={{ color: 'var(--mute)', marginLeft: 8 }}>
                    {t('arch.retryCount')}: {evalResult.retry_count}
                  </span>
                </div>

                {evalResult.feedback && (
                  <div style={{
                    padding: '6px 10px', borderRadius: 'var(--radius-sm)',
                    background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                    fontSize: 11, marginBottom: 6, color: 'var(--body)',
                  }}>
                    <span style={{ color: 'var(--mute)', fontWeight: 500 }}>{t('arch.feedback')}:</span>{' '}
                    {evalResult.feedback}
                  </div>
                )}

                {evalResult.history.length > 0 && (
                  <div>
                    <button
                      onClick={() => setExpandedHistory(prev => !prev)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 4,
                        background: 'none', border: 'none', color: 'var(--mute)',
                        cursor: 'pointer', fontSize: 10, padding: '4px 0',
                      }}
                    >
                      <FileText size={11} />
                      {t('arch.evalHistory')} ({evalResult.history.length})
                      {expandedHistory ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                    </button>
                    {expandedHistory && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
                        {evalResult.history.map((h, i) => (
                          <div key={i} style={{
                            padding: '4px 8px', borderRadius: 'var(--radius-sm)',
                            background: h.passed ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)',
                            border: `1px solid ${h.passed ? 'var(--accent)' : 'var(--hairline)'}`,
                            fontSize: 10, display: 'flex', alignItems: 'center', gap: 6,
                          }}>
                            {h.passed ? (
                              <CheckCircle2 size={10} style={{ color: 'var(--accent)' }} />
                            ) : (
                              <XCircle size={10} style={{ color: 'var(--danger)' }} />
                            )}
                            <span style={{ fontWeight: 500, color: 'var(--ink)' }}>
                              {t('arch.attempt')} {h.attempt}
                            </span>
                            <span style={{ color: h.passed ? 'var(--accent)' : 'var(--danger)', fontWeight: 500 }}>
                              {h.passed ? t('arch.evalPassed') : t('arch.evalFailed')}
                            </span>
                            {h.feedback && (
                              <span style={{ color: 'var(--mute)', marginLeft: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
                                — {h.feedback}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
