import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { History, RotateCcw, GitCompare, ChevronDown, ChevronUp, Loader2, AlertTriangle, FileText, Clock, User } from 'lucide-react';
import { versionHistoryApi, type VersionInfo, type VersionDetail } from '@/services/api';

interface VersionHistoryPanelProps {
  documentId: string;
  onRestore?: (content: string) => void;
}

function formatTime(ts: number) {
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

export const VersionHistoryPanel: React.FC<VersionHistoryPanelProps> = ({ documentId, onRestore }) => {
  const { t } = useTranslation();
  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [versionDetail, setVersionDetail] = useState<VersionDetail | null>(null);
  const [compareVersion, setCompareVersion] = useState<string | null>(null);
  const [diffResult, setDiffResult] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);

  const loadVersions = useCallback(async () => {
    if (!documentId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await versionHistoryApi.list(documentId);
      setVersions(res.data ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    loadVersions();
  }, [loadVersions]);

  const loadVersionDetail = useCallback(async (versionId: string) => {
    try {
      const res = await versionHistoryApi.getVersion(documentId, versionId);
      setVersionDetail(res.data ?? null);
      setSelectedVersion(versionId === selectedVersion ? null : versionId);
    } catch (_e: unknown) {
      // silent
    }
  }, [documentId, selectedVersion]);

  const handleCompare = useCallback(async () => {
    if (!compareVersion || !selectedVersion) return;
    try {
      const res = await versionHistoryApi.compare(documentId, compareVersion, selectedVersion);
      setDiffResult(res.data?.diff ?? null);
    } catch (_e: unknown) {
      // silent
    }
  }, [documentId, compareVersion, selectedVersion]);

  const handleRestore = useCallback(async (versionId: string) => {
    setRestoring(true);
    try {
      const res = await versionHistoryApi.restore(documentId, versionId);
      if (res.data && onRestore) {
        const detail = await versionHistoryApi.getVersion(documentId, versionId);
        if (detail.data) onRestore(detail.data.content);
      }
      await loadVersions();
    } catch (_e: unknown) {
      // silent
    } finally {
      setRestoring(false);
    }
  }, [documentId, onRestore, loadVersions]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: 'var(--ink)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--hairline)' }}>
        <History size={16} style={{ color: 'var(--accent)' }} />
        <span style={{ fontWeight: 600, fontSize: 14 }}>{t('versionHistory.title')}</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--mute)' }}>{versions.length} {t('versionHistory.versions')}</span>
      </div>

      {error && (
        <div style={{ padding: '8px 16px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertTriangle size={12} />
          {error}
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
          <Loader2 size={16} className="animate-spin" />
          <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('versionHistory.loading')}</span>
        </div>
      ) : versions.length === 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
          <FileText size={24} style={{ color: 'var(--mute)' }} />
          <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('versionHistory.noVersions')}</span>
        </div>
      ) : (
        <div style={{ flex: 1, overflow: 'auto' }}>
          {compareVersion && selectedVersion && selectedVersion !== compareVersion && (
            <div style={{ padding: '8px 16px', background: 'rgba(99,102,241,0.1)', borderBottom: '1px solid var(--hairline)' }}>
              <button
                onClick={handleCompare}
                style={{ padding: '4px 12px', borderRadius: 6, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 12 }}
              >
                <GitCompare size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />
                {t('versionHistory.compare')}
              </button>
            </div>
          )}

          {diffResult && (
            <div style={{ padding: 12, background: 'var(--canvas)', borderBottom: '1px solid var(--hairline)', fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}>
              {diffResult}
            </div>
          )}

          {versions.map((v) => (
            <div key={v.version_id} style={{ borderBottom: '1px solid var(--hairline)' }}>
              <div
                style={{ display: 'flex', alignItems: 'center', padding: '8px 16px', cursor: 'pointer', gap: 8 }}
                onClick={() => loadVersionDetail(v.version_id)}
              >
                <input
                  type="radio"
                  name="compareVersion"
                  checked={compareVersion === v.version_id}
                  onChange={() => setCompareVersion(v.version_id === compareVersion ? null : v.version_id)}
                  onClick={(e) => e.stopPropagation()}
                  title={t('versionHistory.selectForCompare')}
                  style={{ flexShrink: 0 }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                    <span style={{ fontWeight: 500 }}>v{v.version_num}</span>
                    {v.note && <span style={{ color: 'var(--mute)', fontSize: 12 }}>- {v.note}</span>}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--mute)', marginTop: 2 }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Clock size={10} />{formatTime(v.timestamp)}</span>
                    {v.author && <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><User size={10} />{v.author}</span>}
                    <span>{v.content_length} chars</span>
                  </div>
                </div>
                {selectedVersion === v.version_id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </div>

              {selectedVersion === v.version_id && versionDetail && (
                <div style={{ padding: '0 16px 12px', animation: 'floating-panel-appear 0.15s ease' }}>
                  <div style={{ background: 'var(--canvas)', borderRadius: 6, padding: 8, fontSize: 12, maxHeight: 150, overflow: 'auto', fontFamily: 'monospace', whiteSpace: 'pre-wrap', color: 'var(--ink)' }}>
                    {versionDetail.content.slice(0, 500)}{versionDetail.content.length > 500 ? '...' : ''}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button
                      onClick={() => handleRestore(v.version_id)}
                      disabled={restoring}
                      style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 12px', borderRadius: 6, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: restoring ? 'wait' : 'pointer', fontSize: 12 }}
                    >
                      {restoring ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                      {t('versionHistory.restore')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
