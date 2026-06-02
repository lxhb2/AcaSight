import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Download, Upload, Trash2, RefreshCw, Clock, Tag, Loader2, AlertTriangle, Check, X, FileDown, FileUp, Copy } from 'lucide-react';
import { workspaceStateApi, type WorkspaceInfo, type WorkspaceSnapshot } from '@/services/api';

interface DataExportImportPanelProps {
  onClose?: () => void;
}

export const DataExportImportPanel: React.FC<DataExportImportPanelProps> = ({ onClose }) => {
  const { t } = useTranslation();
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [snapshots, setSnapshots] = useState<WorkspaceSnapshot[]>([]);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [includeSnapshots, setIncludeSnapshots] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [importJson, setImportJson] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'workspaces' | 'export' | 'import'>('workspaces');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadWorkspaces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await workspaceStateApi.list();
      setWorkspaces(res.data ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  const loadSnapshots = useCallback(async (workspaceId: string) => {
    try {
      const res = await workspaceStateApi.getSnapshots(workspaceId);
      setSnapshots(res.data ?? []);
    } catch (_e: unknown) {
      setSnapshots([]);
    }
  }, []);

  const handleSelectWorkspace = useCallback(async (id: string) => {
    setSelectedId(prev => prev === id ? null : id);
    if (id !== selectedId) {
      await loadSnapshots(id);
    }
  }, [selectedId, loadSnapshots]);

  const handleExport = useCallback(async () => {
    if (!selectedId) return;
    setExporting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await workspaceStateApi.export(selectedId, includeSnapshots);
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `acasight-workspace-${selectedId}-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccessMsg(t('dataExport.exportSuccess', '导出成功'));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  }, [selectedId, includeSnapshots, t]);

  const handleImport = useCallback(async () => {
    if (!importJson.trim()) return;
    setImporting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const data = JSON.parse(importJson);
      const workspaceId = data.workspace_id || `imported-${Date.now()}`;
      await workspaceStateApi.import(workspaceId, data, overwrite);
      setSuccessMsg(t('dataExport.importSuccess', '导入成功'));
      setImportJson('');
      await loadWorkspaces();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('dataExport.invalidJson', 'JSON格式无效'));
    } finally {
      setImporting(false);
    }
  }, [importJson, overwrite, t, loadWorkspaces]);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      setImportJson(text);
      setActiveTab('import');
    };
    reader.readAsText(file);
  }, []);

  const handleDelete = useCallback(async (id: string) => {
    setDeleting(true);
    setError(null);
    try {
      await workspaceStateApi.delete(id);
      if (selectedId === id) {
        setSelectedId(null);
        setSnapshots([]);
      }
      await loadWorkspaces();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeleting(false);
    }
  }, [selectedId, loadWorkspaces]);

  const handleRestore = useCallback(async (workspaceId: string, snapshotTimestamp?: number) => {
    setLoading(true);
    setError(null);
    try {
      await workspaceStateApi.restore(workspaceId, snapshotTimestamp);
      setSuccessMsg(t('dataExport.restoreSuccess', '恢复成功'));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [t]);

  const formatTime = (ts: number) => new Date(ts * 1000).toLocaleString();
  const formatSize = (bytes: number) => bytes > 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${bytes} B`;

  const tabs: { id: typeof activeTab; icon: typeof Download; labelKey: string }[] = [
    { id: 'workspaces', icon: Copy, labelKey: 'dataExport.workspaces' },
    { id: 'export', icon: FileDown, labelKey: 'dataExport.export' },
    { id: 'import', icon: FileUp, labelKey: 'dataExport.import' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', color: 'var(--ink)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--hairline)' }}>
        <Download size={16} style={{ color: 'var(--accent)' }} />
        <span style={{ fontWeight: 600, fontSize: 14 }}>{t('dataExport.title', '数据导出导入')}</span>
        {onClose && (
          <button onClick={onClose} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)' }}>
            <X size={14} />
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 2, padding: '8px 16px', borderBottom: '1px solid var(--hairline)' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1, padding: '6px 8px', borderRadius: 6, border: 'none',
              background: activeTab === tab.id ? 'var(--accent)' : 'transparent',
              color: activeTab === tab.id ? '#fff' : 'var(--ink)',
              cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
            }}
          >
            <tab.icon size={12} />
            {t(tab.labelKey, tab.id)}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ padding: '8px 16px', background: 'rgba(239,68,68,0.1)', color: '#ef4444', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertTriangle size={12} />{error}
          <button onClick={() => setError(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444' }}><X size={12} /></button>
        </div>
      )}

      {successMsg && (
        <div style={{ padding: '8px 16px', background: 'rgba(16,185,129,0.1)', color: '#10b981', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Check size={12} />{successMsg}
          <button onClick={() => setSuccessMsg(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#10b981' }}><X size={12} /></button>
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto' }}>
        {activeTab === 'workspaces' && (
          <div>
            <div style={{ padding: '8px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: 'var(--mute)' }}>{workspaces.length} {t('dataExport.workspaceCount', '个工作区')}</span>
              <button onClick={loadWorkspaces} disabled={loading} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
                <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
                {t('dataExport.refresh', '刷新')}
              </button>
            </div>

            {loading && workspaces.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
                <Loader2 size={16} className="animate-spin" />
                <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('dataExport.loading', '加载中...')}</span>
              </div>
            ) : workspaces.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 }}>
                <FileDown size={24} style={{ color: 'var(--mute)' }} />
                <span style={{ fontSize: 13, color: 'var(--mute)' }}>{t('dataExport.noWorkspaces', '暂无已保存的工作区')}</span>
              </div>
            ) : (
              workspaces.map(ws => (
                <div key={ws.id} style={{ borderBottom: '1px solid var(--hairline)' }}>
                  <div
                    style={{ display: 'flex', alignItems: 'center', padding: '8px 16px', cursor: 'pointer', gap: 8 }}
                    onClick={() => handleSelectWorkspace(ws.id)}
                  >
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
                        <span style={{ fontWeight: 500 }}>{ws.name || ws.id}</span>
                        {ws.update_count > 0 && <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: 'var(--accent-bg-soft)', color: 'var(--accent)' }}>v{ws.update_count}</span>}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--mute)', marginTop: 2 }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}><Clock size={10} />{formatTime(ws.updated_at)}</span>
                        {ws.tags.length > 0 && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                            <Tag size={10} />{ws.tags.slice(0, 3).join(', ')}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleRestore(ws.id); }}
                      disabled={loading}
                      style={{ padding: '2px 8px', borderRadius: 4, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 11 }}
                    >
                      {t('dataExport.restore', '恢复')}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(ws.id); }}
                      disabled={deleting}
                      style={{ padding: '2px 6px', borderRadius: 4, border: 'none', background: 'transparent', color: '#ef4444', cursor: deleting ? 'wait' : 'pointer' }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>

                  {selectedId === ws.id && snapshots.length > 0 && (
                    <div style={{ padding: '0 16px 8px', animation: 'floating-panel-appear 0.15s ease' }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 4 }}>{t('dataExport.snapshots', '快照列表')}</div>
                      {snapshots.map(snap => (
                        <div key={snap.timestamp} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 8px', fontSize: 11, borderRadius: 4, marginBottom: 2, background: 'var(--canvas)' }}>
                          <Clock size={10} style={{ color: 'var(--mute)' }} />
                          <span style={{ flex: 1 }}>{formatTime(snap.timestamp)}</span>
                          <span style={{ color: 'var(--mute)' }}>{formatSize(snap.size_bytes)}</span>
                          <button
                            onClick={() => handleRestore(ws.id, snap.timestamp)}
                            style={{ padding: '1px 6px', borderRadius: 3, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 10 }}
                          >
                            {t('dataExport.restore', '恢复')}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'export' && (
          <div style={{ padding: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileDown size={14} /> {t('dataExport.exportTitle', '导出工作区数据')}
              </div>
              <p style={{ fontSize: 12, color: 'var(--mute)', lineHeight: 1.6, marginBottom: 12 }}>
                {t('dataExport.exportDesc', '选择一个工作区，将其状态导出为JSON文件。可选择是否包含历史快照。')}
              </p>

              {!selectedId ? (
                <div style={{ padding: 12, borderRadius: 8, border: '1px dashed var(--hairline)', textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
                  {t('dataExport.selectWorkspace', '请先在"工作区"标签中选择一个工作区')}
                </div>
              ) : (
                <div>
                  <div style={{ padding: '8px 12px', borderRadius: 6, background: 'var(--canvas)', marginBottom: 12, fontSize: 12 }}>
                    {t('dataExport.selected', '已选择')}: <strong>{workspaces.find(w => w.id === selectedId)?.name || selectedId}</strong>
                  </div>

                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, fontSize: 12, cursor: 'pointer' }}>
                    <input type="checkbox" checked={includeSnapshots} onChange={e => setIncludeSnapshots(e.target.checked)} />
                    {t('dataExport.includeSnapshots', '包含历史快照')}
                  </label>

                  <button
                    onClick={handleExport}
                    disabled={exporting}
                    style={{
                      padding: '8px 20px', borderRadius: 8, border: 'none',
                      background: exporting ? 'var(--mute)' : 'var(--accent)', color: '#fff',
                      cursor: exporting ? 'wait' : 'pointer', fontSize: 13, fontWeight: 600,
                      display: 'flex', alignItems: 'center', gap: 6,
                    }}
                  >
                    {exporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                    {t('dataExport.exportBtn', '导出JSON')}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'import' && (
          <div style={{ padding: 16 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <FileUp size={14} /> {t('dataExport.importTitle', '导入工作区数据')}
            </div>
            <p style={{ fontSize: 12, color: 'var(--mute)', lineHeight: 1.6, marginBottom: 12 }}>
              {t('dataExport.importDesc', '上传之前导出的JSON文件，或直接粘贴JSON内容。')}
            </p>

            <div style={{ marginBottom: 12 }}>
              <input ref={fileInputRef} type="file" accept=".json" onChange={handleFileUpload} style={{ display: 'none' }} />
              <button
                onClick={() => fileInputRef.current?.click()}
                style={{
                  padding: '8px 16px', borderRadius: 8, border: '1px dashed var(--accent)',
                  background: 'rgba(99,102,241,0.05)', color: 'var(--accent)',
                  cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6, width: '100%', justifyContent: 'center',
                }}
              >
                <Upload size={14} />
                {t('dataExport.uploadFile', '上传JSON文件')}
              </button>
            </div>

            <textarea
              value={importJson}
              onChange={e => setImportJson(e.target.value)}
              placeholder={t('dataExport.pasteJson', '或在此粘贴JSON内容...')}
              rows={8}
              style={{
                width: '100%', padding: '8px 12px', borderRadius: 6,
                border: '1px solid var(--hairline)', background: 'var(--canvas)',
                color: 'var(--ink)', fontSize: 11, fontFamily: 'monospace',
                outline: 'none', resize: 'vertical', marginBottom: 12,
              }}
            />

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, fontSize: 12, cursor: 'pointer' }}>
              <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
              {t('dataExport.overwrite', '覆盖已有工作区（如存在同名工作区）')}
            </label>

            <button
              onClick={handleImport}
              disabled={importing || !importJson.trim()}
              style={{
                padding: '8px 20px', borderRadius: 8, border: 'none',
                background: (importing || !importJson.trim()) ? 'var(--mute)' : '#10b981', color: '#fff',
                cursor: (importing || !importJson.trim()) ? 'not-allowed' : 'pointer', fontSize: 13, fontWeight: 600,
                display: 'flex', alignItems: 'center', gap: 6,
              }}
            >
              {importing ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
              {t('dataExport.importBtn', '导入数据')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
