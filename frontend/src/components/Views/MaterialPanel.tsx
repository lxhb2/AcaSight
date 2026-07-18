import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import {
  FileSpreadsheet, FileText, BarChart3, FolderOpen,
  Upload, Trash2, RefreshCw, HardDrive, Clock, CheckCircle2,
  AlertCircle, Loader2, Archive, File, FileImage, FileType,
  Eye,
} from 'lucide-react';
import { storageApi, type MaterialItem, type CacheEntry } from '@/services/api';
import { useFileOpen } from '@/contexts/FileOpenContext';
import { openFile as openFilePicker } from '@/lib/tauri-adapter';

const FILE_TYPE_CATEGORIES = [
  { key: '', label: '全部', icon: <FolderOpen size={13} /> },
  { key: 'pdf', label: 'PDF', icon: <FileText size={13} /> },
  { key: 'image', label: '图片', icon: <FileImage size={13} /> },
  { key: 'svg', label: 'SVG', icon: <FileType size={13} /> },
  { key: 'data', label: '数据', icon: <FileSpreadsheet size={13} /> },
  { key: 'chart', label: '图表', icon: <BarChart3 size={13} /> },
  { key: 'doc', label: '文档', icon: <File size={13} /> },
  { key: 'other', label: '其他', icon: <FolderOpen size={13} /> },
] as const;

const CATEGORY_COLORS: Record<string, string> = {
  pdf: '#ef4444',
  image: '#ec4899',
  svg: '#8b5cf6',
  data: '#3b82f6',
  chart: '#10b981',
  doc: '#f59e0b',
  other: '#6b7280',
};

const VIEWABLE_EXTENSIONS = new Set(['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg']);
const IMAGE_EXTENSIONS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']);
const DATA_EXTENSIONS = new Set(['csv', 'tsv', 'xlsx', 'xls', 'json', 'xml']);
const CHART_EXTENSIONS = new Set(['plotly.json', 'chart.json']);
const DOC_EXTENSIONS = new Set(['txt', 'doc', 'docx', 'rtf', 'odt', 'md']);

function classifyFile(filename: string, category?: string): string {
  if (category && category !== 'other') return category;
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (ext === 'pdf') return 'pdf';
  if (ext === 'svg') return 'svg';
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  if (CHART_EXTENSIONS.has(filename.toLowerCase().replace(/.*\./, ''))) return 'chart';
  if (DATA_EXTENSIONS.has(ext)) return 'data';
  if (DOC_EXTENSIONS.has(ext)) return 'doc';
  return 'other';
}

function getFileTypeCategory(filename: string, category?: string) {
  return FILE_TYPE_CATEGORIES.find(c => c.key === classifyFile(filename, category)) || FILE_TYPE_CATEGORIES[FILE_TYPE_CATEGORIES.length - 1];
}

function getExtension(filename: string) {
  return filename.split('.').pop()?.toLowerCase() || '';
}

function isViewable(filename: string): boolean {
  const ext = getExtension(filename);
  return VIEWABLE_EXTENSIONS.has(ext);
}

function getOpenType(filename: string): 'pdf' | 'image' | 'svg' | null {
  const ext = getExtension(filename);
  if (ext === 'pdf') return 'pdf';
  if (ext === 'svg') return 'svg';
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  return null;
}

export const MaterialPanel: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'materials' | 'cache' | 'stats'>('materials');
  const [activeCategory, setActiveCategory] = useState('');
  const [materials, setMaterials] = useState<MaterialItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [cacheEntries, setCacheEntries] = useState<CacheEntry[]>([]);
  const [cacheLoading, setCacheLoading] = useState(false);
  const [cacheCategory, setCacheCategory] = useState('');

  const [stats, setStats] = useState<{ total_files: number; total_size_mb: number; by_category: Record<string, { files: number; size_bytes: number }> } | null>(null);
  const [cacheStats, setCacheStats] = useState<{ total: number; expired: number; persisted: number; active: number; by_category: Record<string, number> } | null>(null);

  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);
  const showToast = (msg: string, type: string) => { setToast({ msg, type }); setTimeout(() => setToast(null), 3000); };

  const dropRef = useRef<HTMLDivElement>(null);
  const { openFile } = useFileOpen();

  const filteredMaterials = useMemo(() => {
    if (!activeCategory) return materials;
    return materials.filter(m => classifyFile(m.filename, m.category) === activeCategory);
  }, [materials, activeCategory]);

  const loadMaterials = useCallback(async () => {
    setLoading(true);
    try {
      const data = await storageApi.unifiedList({ limit: 200 });
      setMaterials(data.items || []);
    } catch {
      setMaterials([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadMaterials(); }, [loadMaterials]);

  const loadCache = useCallback(async () => {
    setCacheLoading(true);
    try {
      const data = await storageApi.cacheList(cacheCategory || undefined, 50);
      setCacheEntries(data.items || []);
    } catch {
      setCacheEntries([]);
    } finally {
      setCacheLoading(false);
    }
  }, [cacheCategory]);

  useEffect(() => { if (activeTab === 'cache') loadCache(); }, [activeTab, loadCache]);

  const loadStats = useCallback(async () => {
    try {
      const [s, cs] = await Promise.all([storageApi.unifiedStats(), storageApi.cacheStats()]);
      setStats(s);
      setCacheStats(cs);
    } catch { /* silently fail */ }
  }, []);

  useEffect(() => { if (activeTab === 'stats') loadStats(); }, [activeTab, loadStats]);

  const handleUpload = async (files: FileList | File[]) => {
    if (!files.length) return;
    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const ext = getExtension(file.name);
        let cat = 'other';
        if (ext === 'pdf') cat = 'pdf';
        else if (IMAGE_EXTENSIONS.has(ext)) cat = 'image';
        else if (ext === 'svg') cat = 'svg';
        else if (DATA_EXTENSIONS.has(ext)) cat = 'data';
        else if (DOC_EXTENSIONS.has(ext)) cat = 'doc';
        await storageApi.unifiedUpload(file, cat);
      }
      showToast(`已上传 ${files.length} 个文件`, 'success');
      loadMaterials();
    } catch (e: unknown) {
      showToast(`上传失败: ${e instanceof Error ? e.message : String(e)}`, 'error');
    } finally {
      setUploading(false);
    }
  };

  const handleUploadFromAdapter = useCallback(async () => {
    const files = await openFilePicker({ multiple: true, filters: [
      { name: 'Documents', extensions: ['pdf', 'doc', 'docx', 'txt', 'md', 'rtf'] },
      { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'] },
      { name: 'Data', extensions: ['csv', 'tsv', 'xlsx', 'xls', 'json', 'xml'] },
    ] });
    if (!files.length) return;
    setUploading(true);
    try {
      for (const f of files) {
        const ext = getExtension(f.name);
        let cat = 'other';
        if (ext === 'pdf') cat = 'pdf';
        else if (IMAGE_EXTENSIONS.has(ext)) cat = 'image';
        else if (ext === 'svg') cat = 'svg';
        else if (DATA_EXTENSIONS.has(ext)) cat = 'data';
        else if (DOC_EXTENSIONS.has(ext)) cat = 'doc';
        // Convert Uint8Array to File for storageApi
        const file = new globalThis.File([f.content as BlobPart], f.name);
        await storageApi.unifiedUpload(file, cat);
      }
      showToast(`已上传 ${files.length} 个文件`, 'success');
      loadMaterials();
    } catch (e: unknown) {
      showToast(`上传失败: ${e instanceof Error ? e.message : String(e)}`, 'error');
    } finally {
      setUploading(false);
    }
  }, [loadMaterials, showToast]);

  const handleDelete = async (path: string) => {
    try {
      await storageApi.unifiedDelete(path);
      showToast('已删除', 'success');
      loadMaterials();
    } catch (e: unknown) {
      showToast(`删除失败: ${e instanceof Error ? e.message : String(e)}`, 'error');
    }
  };

  const handleOpen = useCallback((m: MaterialItem) => {
    const openType = getOpenType(m.filename);
    if (!openType) {
      showToast('该格式暂不支持预览', 'error');
      return;
    }
    if (openType === 'pdf') {
      // PDF 使用 /api/pdf/proxy 端点，支持 proxy/hash/extract-text 全部功能
      const proxyUrl = `/api/pdf/proxy?url=${encodeURIComponent(m.path)}`;
      openFile(m.filename, 'pdf', { pdfUrl: proxyUrl });
    } else {
      // 图片/SVG 使用 unified/file 端点
      const baseUrl = '/api/storage/unified/file';
      const fileUrl = `${baseUrl}?path=${encodeURIComponent(m.path)}`;
      if (openType === 'svg') {
        openFile(m.filename, 'svg', { imageUrl: fileUrl });
      } else {
        openFile(m.filename, 'image', { imageUrl: fileUrl });
      }
    }
  }, [openFile, showToast]);

  const handleCacheCleanup = async () => {
    try {
      const result = await storageApi.cacheCleanup();
      showToast(`已清理 ${result.removed} 条过期缓存`, 'success');
      loadCache();
    } catch (e: unknown) {
      showToast(`清理失败: ${e instanceof Error ? e.message : String(e)}`, 'error');
    }
  };

  const handleCachePersist = async (cacheId: string) => {
    try {
      await storageApi.cachePersist(cacheId);
      showToast('已持久化', 'success');
      loadCache();
    } catch (e: unknown) {
      showToast(`持久化失败: ${e instanceof Error ? e.message : String(e)}`, 'error');
    }
  };

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); e.stopPropagation(); };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); e.stopPropagation();
    if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files);
  };

  const formatSize = (bytes: number) => bytes < 1024 ? `${bytes}B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)}KB` : `${(bytes / 1024 / 1024).toFixed(1)}MB`;
  const formatDate = (ts: number | string) => new Date(typeof ts === 'number' ? ts * 1000 : ts).toLocaleDateString('zh-CN');

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    materials.forEach(m => {
      const cat = classifyFile(m.filename, m.category);
      counts[cat] = (counts[cat] || 0) + 1;
    });
    return counts;
  }, [materials]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg-primary)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid var(--hairline)' }}>
        <HardDrive size={14} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--body)' }}>素材管理</span>
        <div style={{ flex: 1 }} />
        {(['materials', 'cache', 'stats'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            style={{
              padding: '3px 10px', fontSize: 10, borderRadius: 6, border: '1px solid var(--hairline)',
              background: activeTab === tab ? 'var(--accent)' : 'transparent',
              color: activeTab === tab ? '#fff' : 'var(--body)', cursor: 'pointer', transition: 'all 0.15s',
            }}>
            {tab === 'materials' ? '素材' : tab === 'cache' ? '缓存' : '统计'}
          </button>
        ))}
      </div>

      {activeTab === 'materials' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
          <div style={{ display: 'flex', gap: 4, marginBottom: 10, flexWrap: 'wrap' }}>
            {FILE_TYPE_CATEGORIES.map(cat => (
              <button key={cat.key} onClick={() => setActiveCategory(cat.key)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 3, padding: '4px 10px', fontSize: 10, borderRadius: 6,
                  border: activeCategory === cat.key ? `1px solid ${CATEGORY_COLORS[cat.key] || 'var(--accent)'}` : '1px solid var(--hairline)',
                  background: activeCategory === cat.key ? `${CATEGORY_COLORS[cat.key] || 'var(--accent)'}15` : 'transparent',
                  color: activeCategory === cat.key ? (CATEGORY_COLORS[cat.key] || 'var(--accent)') : 'var(--body)',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}>
                {cat.icon} {cat.label}
                {categoryCounts[cat.key] !== undefined && (
                  <span style={{ fontSize: 9, opacity: 0.7 }}>{categoryCounts[cat.key]}</span>
                )}
              </button>
            ))}
          </div>

          <div
            ref={dropRef}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            onClick={handleUploadFromAdapter}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              gap: 6, padding: 20, marginBottom: 10, borderRadius: 8,
              border: '2px dashed var(--hairline)', cursor: 'pointer', transition: 'border-color 0.15s',
              background: 'var(--canvas-soft)',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--hairline)'; }}
          >
            {uploading ? (
              <><Loader2 size={20} className="animate-spin" style={{ color: 'var(--accent)' }} /><span style={{ fontSize: 11, color: 'var(--mute)' }}>上传中...</span></>
            ) : (
              <><Upload size={20} style={{ color: 'var(--mute)' }} /><span style={{ fontSize: 11, color: 'var(--mute)' }}>拖拽文件到此处或点击上传</span></>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 10, color: 'var(--mute)' }}>
            <span>{filteredMaterials.length} 个素材</span>
            <button onClick={loadMaterials} style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '2px 6px', borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer', fontSize: 10 }}>
              <RefreshCw size={10} /> 刷新
            </button>
          </div>

          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}><Loader2 size={16} className="animate-spin" style={{ color: 'var(--mute)' }} /></div>
          ) : filteredMaterials.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 30, fontSize: 12, color: 'var(--mute)' }}>
              <FolderOpen size={24} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
              暂无素材，拖拽文件上传
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {filteredMaterials.map(m => {
                const cat = getFileTypeCategory(m.filename, m.category);
                const viewable = isViewable(m.filename);
                return (
                  <div key={m.path} style={{
                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', borderRadius: 6,
                    border: '1px solid var(--hairline)', background: 'var(--canvas)', transition: 'background 0.1s',
                    cursor: viewable ? 'pointer' : 'default',
                  }}
                    onClick={() => viewable && handleOpen(m)}
                    onMouseEnter={e => { e.currentTarget.style.background = 'var(--canvas-soft)'; }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'var(--canvas)'; }}
                  >
                    <span style={{ background: CATEGORY_COLORS[classifyFile(m.filename, m.category)] || '#6b7280', borderRadius: 4, padding: 3, display: 'flex', color: '#fff' }}>
                      {cat.icon}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--body)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.filename}</div>
                      <div style={{ fontSize: 9, color: 'var(--mute)' }}>{formatSize(m.size)} · {formatDate(m.mtime)}</div>
                    </div>
                    {viewable && (
                      <button onClick={(e) => { e.stopPropagation(); handleOpen(m); }} title="预览"
                        style={{ padding: 3, border: 'none', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', borderRadius: 3, transition: 'color 0.15s' }}
                      ><Eye size={12} /></button>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(m.path); }} title="删除"
                      style={{ padding: 3, border: 'none', background: 'transparent', color: 'var(--mute)', cursor: 'pointer', borderRadius: 3, transition: 'color 0.15s' }}
                      onMouseEnter={e => { e.currentTarget.style.color = 'var(--danger)'; }}
                      onMouseLeave={e => { e.currentTarget.style.color = 'var(--mute)'; }}
                    ><Trash2 size={11} /></button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {activeTab === 'cache' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: 'var(--body)', fontWeight: 500 }}>临时缓存</span>
            <div style={{ flex: 1 }} />
            <button onClick={loadCache} style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '2px 6px', borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer', fontSize: 10 }}>
              <RefreshCw size={10} />
            </button>
            <button onClick={handleCacheCleanup} style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--danger)', background: 'transparent', color: 'var(--danger)', cursor: 'pointer', fontSize: 10 }}>
              <Trash2 size={10} /> 清理过期
            </button>
          </div>

          <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
            <button onClick={() => setCacheCategory('')} style={{ padding: '2px 8px', fontSize: 9, borderRadius: 4, border: cacheCategory ? '1px solid var(--hairline)' : '1px solid var(--accent)', background: cacheCategory ? 'transparent' : 'var(--accent-bg-soft)', color: cacheCategory ? 'var(--body)' : 'var(--accent)', cursor: 'pointer' }}>全部</button>
            {['search', 'writing', 'chart', 'rag'].map(c => (
              <button key={c} onClick={() => setCacheCategory(c)} style={{ padding: '2px 8px', fontSize: 9, borderRadius: 4, border: cacheCategory === c ? '1px solid var(--accent)' : '1px solid var(--hairline)', background: cacheCategory === c ? 'var(--accent-bg-soft)' : 'transparent', color: cacheCategory === c ? 'var(--accent)' : 'var(--body)', cursor: 'pointer' }}>{c}</button>
            ))}
          </div>

          {cacheLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}><Loader2 size={16} className="animate-spin" style={{ color: 'var(--mute)' }} /></div>
          ) : cacheEntries.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 30, fontSize: 12, color: 'var(--mute)' }}>
              <Clock size={24} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
              暂无缓存数据
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {cacheEntries.map(entry => (
                <div key={entry.cache_id} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 8px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--canvas)' }}>
                  <span style={{ fontSize: 10 }}>{entry.persisted ? '📌' : '⏳'}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: 'var(--body)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{entry.key}</div>
                    <div style={{ fontSize: 9, color: 'var(--mute)' }}>{entry.category} · {formatDate(entry.created_at)}</div>
                  </div>
                  {!entry.persisted && (
                    <button onClick={() => handleCachePersist(entry.cache_id)} title="持久化" style={{ padding: 2, border: 'none', background: 'transparent', color: 'var(--mute)', cursor: 'pointer' }}>
                      <Archive size={11} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'stats' && (
        <div style={{ flex: 1, overflowY: 'auto', padding: 14 }}>
          {stats ? (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 14 }}>
                <div style={{ padding: 10, borderRadius: 8, border: '1px solid var(--hairline)', background: 'var(--canvas)' }}>
                  <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4 }}>总文件数</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--body)' }}>{stats.total_files}</div>
                </div>
                <div style={{ padding: 10, borderRadius: 8, border: '1px solid var(--hairline)', background: 'var(--canvas)' }}>
                  <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4 }}>总大小</div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--body)' }}>{stats.total_size_mb.toFixed(1)} MB</div>
                </div>
              </div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--body)', marginBottom: 6 }}>按类别</div>
              {Object.entries(stats.by_category || {}).map(([cat, info]) => (
                <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0' }}>
                  <span style={{ width: 8, height: 8, borderRadius: 4, background: CATEGORY_COLORS[cat] || '#6b7280' }} />
                  <span style={{ fontSize: 11, color: 'var(--body)', flex: 1 }}>{cat}</span>
                  <span style={{ fontSize: 10, color: 'var(--mute)' }}>{info.files} 文件 · {formatSize(info.size_bytes)}</span>
                </div>
              ))}
            </>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}><Loader2 size={16} className="animate-spin" style={{ color: 'var(--mute)' }} /></div>
          )}

          {cacheStats && (
            <>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--body)', margin: '14px 0 6px' }}>缓存状态</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
                <div style={{ padding: 6, borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--canvas)', textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#3b82f6' }}>{cacheStats.active}</div>
                  <div style={{ fontSize: 9, color: 'var(--mute)' }}>活跃</div>
                </div>
                <div style={{ padding: 6, borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--canvas)', textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#f59e0b' }}>{cacheStats.expired}</div>
                  <div style={{ fontSize: 9, color: 'var(--mute)' }}>已过期</div>
                </div>
                <div style={{ padding: 6, borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--canvas)', textAlign: 'center' }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: '#10b981' }}>{cacheStats.persisted}</div>
                  <div style={{ fontSize: 9, color: 'var(--mute)' }}>已持久化</div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {toast && (
        <div style={{
          position: 'absolute', bottom: 12, left: '50%', transform: 'translateX(-50%)',
          padding: '6px 14px', borderRadius: 6, fontSize: 11,
          background: toast.type === 'error' ? '#ef4444' : '#10b981', color: '#fff',
          boxShadow: '0 2px 8px rgba(0,0,0,0.2)', zIndex: 100,
          display: 'flex', alignItems: 'center', gap: 4,
        }}>
          {toast.type === 'error' ? <AlertCircle size={11} /> : <CheckCircle2 size={11} />}
          {toast.msg}
        </div>
      )}
    </div>
  );
};

export default MaterialPanel;
