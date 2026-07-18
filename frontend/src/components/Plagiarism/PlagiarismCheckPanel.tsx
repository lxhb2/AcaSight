/**
 * 论文查重面板
 *
 * 功能：文本输入 / 文件上传 / 查重 / 结果展示 / 历史记录
 */

import React, { useState, useCallback } from 'react';
import {
  Search, Upload, FileText, Clock, ChevronDown, ChevronRight,
  Loader2, AlertTriangle, CheckCircle, XCircle, Shield,
} from 'lucide-react';
import { openFile, openTextFile } from '@/lib/tauri-adapter';

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

interface MatchResult {
  source_title: string;
  source_authors: string;
  similarity: number;
  matched_text: string;
  position: number;
}

interface CheckResult {
  similarity_score: number;
  matches: MatchResult[];
  checked_at: string;
  text_length: number;
  reference_count: number;
  message?: string;
}

interface HistoryItem {
  id: number;
  similarity_score: number;
  text_length: number;
  reference_count: number;
  match_count: number;
  checked_at: string;
}

/* ── style helpers ── */

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

const btnSecondary: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6,
  padding: '6px 14px', borderRadius: 'var(--radius-sm)',
  background: 'var(--canvas-soft-2)', color: 'var(--text-primary)',
  border: '1px solid var(--hairline)', cursor: 'pointer', fontSize: 12,
};

/** 相似度颜色 */
function scoreColor(score: number): string {
  if (score < 0.2) return 'var(--success)';
  if (score < 0.4) return 'var(--warning)';
  return 'var(--danger)';
}

function scoreLabel(score: number): string {
  if (score < 0.2) return '低风险';
  if (score < 0.4) return '中等风险';
  return '高风险';
}

function scoreIcon(score: number) {
  if (score < 0.2) return <CheckCircle size={16} style={{ color: 'var(--success)' }} />;
  if (score < 0.4) return <AlertTriangle size={16} style={{ color: 'var(--warning)' }} />;
  return <XCircle size={16} style={{ color: 'var(--danger)' }} />;
}

/* ── sub-components ── */

/** 匹配详情卡片 */
const MatchCard: React.FC<{ match: MatchResult }> = ({ match }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      border: '1px solid var(--hairline)',
      borderRadius: 'var(--radius-sm)',
      marginBottom: 6,
      overflow: 'hidden',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 12px', cursor: 'pointer',
          background: 'var(--canvas-soft)',
        }}
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span style={{ flex: 1, fontSize: 12, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {match.source_title}
        </span>
        <span style={{
          fontSize: 11, fontWeight: 600,
          color: scoreColor(match.similarity),
          padding: '2px 8px', borderRadius: 'var(--radius-xs)',
          background: `${scoreColor(match.similarity)}20`,
        }}>
          {(match.similarity * 100).toFixed(1)}%
        </span>
      </div>
      {expanded && (
        <div style={{ padding: '8px 12px', fontSize: 11, color: 'var(--text-secondary)' }}>
          <div style={{ marginBottom: 4 }}>
            <span style={{ color: 'var(--text-muted)' }}>作者: </span>{match.source_authors}
          </div>
          {match.matched_text && (
            <div style={{
              padding: 8, borderRadius: 'var(--radius-xs)',
              background: 'var(--canvas-soft-2)', lineHeight: 1.6,
              whiteSpace: 'pre-wrap', maxHeight: 120, overflow: 'auto',
              borderLeft: `3px solid ${scoreColor(match.similarity)}`,
            }}>
              {match.matched_text}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/** 历史记录 */
const HistorySection: React.FC = () => {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch<{ history: HistoryItem[] }>('/plagiarism/history?limit=20');
      setHistory(res.history || []);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  React.useEffect(() => { loadHistory(); }, [loadHistory]);

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, color: 'var(--text-muted)' }}>
        <Loader2 size={16} className="animate-spin" /> <span style={{ marginLeft: 8, fontSize: 12 }}>加载中...</span>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 24, color: 'var(--text-muted)', fontSize: 12 }}>
        暂无查重记录
      </div>
    );
  }

  return (
    <div>
      {history.map(h => (
        <div key={h.id} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 0', borderBottom: '1px solid var(--hairline)', fontSize: 11,
        }}>
          {scoreIcon(h.similarity_score)}
          <span style={{ color: scoreColor(h.similarity_score), fontWeight: 600 }}>
            {(h.similarity_score * 100).toFixed(1)}%
          </span>
          <span style={{ color: 'var(--text-muted)' }}>
            {h.text_length} 字 / {h.reference_count} 篇参考 / {h.match_count} 处匹配
          </span>
          <span style={{ flex: 1 }} />
          <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>
            {h.checked_at?.slice(0, 19).replace('T', ' ')}
          </span>
        </div>
      ))}
    </div>
  );
};

/* ── main panel ── */

export const PlagiarismCheckPanel: React.FC = () => {
  const [text, setText] = useState('');
  const [checkType, setCheckType] = useState<'local' | 'external'>('local');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'check' | 'history'>('check');

  const runCheck = useCallback(async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await apiFetch<CheckResult>('/plagiarism/check', {
        method: 'POST',
        body: JSON.stringify({ text, check_type: checkType }),
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || '查重失败');
    } finally {
      setLoading(false);
    }
  }, [text, checkType]);

  const handleFileUpload = useCallback(async () => {
    try {
      const files = await openTextFile({
        filters: [
          { name: '文档文件', extensions: ['txt', 'md', 'docx'] },
        ],
        multiple: false,
      });
      if (files.length > 0) {
        setText(files[0].content);
      }
    } catch {
      // 用户取消
    }
  }, []);

  const handleFileCheck = useCallback(async () => {
    try {
      const files = await openFile({
        filters: [
          { name: '文档文件', extensions: ['txt', 'md', 'docx'] },
        ],
        multiple: false,
      });
      if (files.length === 0) return;

      setLoading(true);
      setError('');
      setResult(null);

      const f = files[0];
      const blob = new Blob([f.content as BlobPart]);
      const file = new File([blob], f.name);
      const form = new FormData();
      form.append('file', file);

      const res = await apiFetch<CheckResult>('/plagiarism/check-file', {
        method: 'POST', body: form,
      });
      setResult(res);
    } catch (e: any) {
      setError(e.message || '文件查重失败');
    } finally {
      setLoading(false);
    }
  }, []);

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
        <button
          onClick={() => setActiveTab('check')}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '8px 12px', fontSize: 12,
            color: activeTab === 'check' ? 'var(--accent)' : 'var(--text-muted)',
            background: 'transparent', border: 'none',
            borderBottom: activeTab === 'check' ? '2px solid var(--accent)' : '2px solid transparent',
            cursor: 'pointer',
          }}
        >
          <Shield size={13} /> 查重
        </button>
        <button
          onClick={() => setActiveTab('history')}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '8px 12px', fontSize: 12,
            color: activeTab === 'history' ? 'var(--accent)' : 'var(--text-muted)',
            background: 'transparent', border: 'none',
            borderBottom: activeTab === 'history' ? '2px solid var(--accent)' : '2px solid transparent',
            cursor: 'pointer',
          }}
        >
          <Clock size={13} /> 历史
        </button>
      </div>

      {/* 内容区 */}
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {activeTab === 'check' && (
          <>
            {/* 文本输入 */}
            <div style={glassPanel}>
              <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileText size={14} /> 输入待检查文本
              </h3>
              <textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="在此粘贴或输入需要查重的文本..."
                style={{
                  width: '100%', minHeight: 120, padding: 10,
                  borderRadius: 'var(--radius-sm)', fontSize: 12, lineHeight: 1.6,
                  background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                  color: 'var(--text-primary)', resize: 'vertical', outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8, flexWrap: 'wrap' }}>
                <select
                  value={checkType}
                  onChange={e => setCheckType(e.target.value as any)}
                  style={{
                    padding: '5px 8px', borderRadius: 'var(--radius-sm)',
                    background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
                    color: 'var(--text-primary)', fontSize: 12,
                  }}
                >
                  <option value="local">本地查重</option>
                  <option value="external">外部查重(预留)</option>
                </select>
                <button
                  onClick={runCheck}
                  disabled={loading || !text.trim()}
                  style={{
                    ...btnPrimary,
                    opacity: loading || !text.trim() ? 0.5 : 1,
                  }}
                >
                  {loading ? <Loader2 size={12} className="animate-spin" /> : <Search size={12} />}
                  开始查重
                </button>
                <button onClick={handleFileUpload} style={btnSecondary}>
                  <Upload size={12} /> 导入文本
                </button>
                <button onClick={handleFileCheck} style={btnSecondary}>
                  <FileText size={12} /> 文件查重
                </button>
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                background: 'var(--danger-soft)', color: 'var(--danger)',
                fontSize: 12, marginTop: 8,
              }}>
                <AlertTriangle size={14} /> {error}
              </div>
            )}

            {/* 查重结果 */}
            {result && (
              <div style={{ ...glassPanel, marginTop: 12 }}>
                {/* 总分 */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: 12, borderRadius: 'var(--radius-md)',
                  background: `${scoreColor(result.similarity_score)}10`,
                  border: `1px solid ${scoreColor(result.similarity_score)}30`,
                  marginBottom: 12,
                }}>
                  {scoreIcon(result.similarity_score)}
                  <div>
                    <div style={{ fontSize: 20, fontWeight: 700, color: scoreColor(result.similarity_score) }}>
                      {(result.similarity_score * 100).toFixed(1)}%
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {scoreLabel(result.similarity_score)} · {result.text_length} 字 · {result.reference_count} 篇参考
                    </div>
                  </div>
                  {result.message && (
                    <div style={{ fontSize: 11, color: 'var(--warning)', marginLeft: 'auto' }}>{result.message}</div>
                  )}
                </div>

                {/* 匹配列表 */}
                {result.matches.length > 0 ? (
                  <div>
                    <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
                      匹配来源 ({result.matches.length})
                    </h4>
                    {result.matches.map((m, i) => (
                      <MatchCard key={i} match={m} />
                    ))}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: 16, color: 'var(--text-muted)', fontSize: 12 }}>
                    未发现显著相似内容
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {activeTab === 'history' && (
          <div style={glassPanel}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={14} /> 查重历史
            </h3>
            <HistorySection />
          </div>
        )}
      </div>
    </div>
  );
};

export default PlagiarismCheckPanel;
