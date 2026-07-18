/**
 * 文档管理面板组件
 * 显示文档列表，支持创建、删除、打开文档
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText, FileSpreadsheet, Presentation, Plus, Trash2, RefreshCw,
  Search, Filter, Loader2, File, Clock, HardDrive, X, ChevronDown,
} from 'lucide-react';
import { documentApi } from '@/services/documentService';
import type { Document, FileType, Template } from '@/services/documentService';

/** 文件类型图标映射 */
function FileTypeIcon({ type }: { type: FileType }) {
  switch (type) {
    case 'docx': return <FileText size={16} style={{ color: '#4285f4' }} />;
    case 'xlsx': return <FileSpreadsheet size={16} style={{ color: '#0f9d58' }} />;
    case 'pptx': return <Presentation size={16} style={{ color: '#db4437' }} />;
    default: return <File size={16} style={{ color: '#888' }} />;
  }
}

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** 格式化日期 */
function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin} 分钟前`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr} 小时前`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `${diffDay} 天前`;
    return d.toLocaleDateString('zh-CN');
  } catch {
    return dateStr;
  }
}

interface DocumentListProps {
  /** 打开文档回调 */
  onOpenDocument?: (doc: Document) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({ onOpenDocument }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<FileType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateMenu, setShowCreateMenu] = useState(false);
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [creating, setCreating] = useState(false);

  /** 加载文档列表 */
  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const fileType = filterType === 'all' ? undefined : filterType;
      const res = await documentApi.listDocuments(0, 50, fileType);
      setDocuments(res.items);
      setTotal(res.total);
    } catch (e) {
      console.error('加载文档列表失败:', e);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  /** 加载模板列表 */
  const loadTemplates = useCallback(async () => {
    try {
      const tpls = await documentApi.getTemplates();
      setTemplates(Array.isArray(tpls) ? tpls : []);
    } catch {
      setTemplates([]);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (showTemplateMenu) loadTemplates();
  }, [showTemplateMenu, loadTemplates]);

  /** 创建新文档 */
  const handleCreate = useCallback(async (fileType: FileType) => {
    setCreating(true);
    setShowCreateMenu(false);
    try {
      const title = `未命名${fileType === 'docx' ? '文档' : fileType === 'xlsx' ? '表格' : '演示文稿'}`;
      const doc = await documentApi.createDocument(title, fileType);
      setDocuments(prev => [doc, ...prev]);
      setTotal(prev => prev + 1);
      onOpenDocument?.(doc);
    } catch (e) {
      console.error('创建文档失败:', e);
    } finally {
      setCreating(false);
    }
  }, [onOpenDocument]);

  /** 从模板创建 */
  const handleCreateFromTemplate = useCallback(async (template: Template) => {
    setCreating(true);
    setShowTemplateMenu(false);
    try {
      const doc = await documentApi.createFromTemplate(template.id, `基于「${template.name}」的文档`);
      setDocuments(prev => [doc, ...prev]);
      setTotal(prev => prev + 1);
      onOpenDocument?.(doc);
    } catch (e) {
      console.error('从模板创建失败:', e);
    } finally {
      setCreating(false);
    }
  }, [onOpenDocument]);

  /** 删除文档 */
  const handleDelete = useCallback(async (docId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await documentApi.deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      setTotal(prev => prev - 1);
    } catch (err) {
      console.error('删除文档失败:', err);
    }
  }, []);

  /** 过滤文档 */
  const filteredDocs = searchQuery.trim()
    ? documents.filter(d => d.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--glass-bg, rgba(255,255,255,0.03))' }}>
      {/* 头部 */}
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--hairline, rgba(255,255,255,0.06))',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <FileText size={16} style={{ color: 'var(--accent, #6366f1)' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--body, #e0e0e0)' }}>
          文档管理
        </span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: 'var(--mute, #888)' }}>
          {total} 个文档
        </span>
        <button
          onClick={loadDocuments}
          title="刷新"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute, #888)', padding: 2 }}
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* 搜索 & 筛选 */}
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--hairline, rgba(255,255,255,0.06))',
        display: 'flex', gap: 6, alignItems: 'center',
      }}>
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', gap: 4,
          padding: '4px 8px', borderRadius: 6,
          background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
          border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
        }}>
          <Search size={13} style={{ color: 'var(--mute, #888)', flexShrink: 0 }} />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="搜索文档..."
            style={{
              flex: 1, background: 'transparent', border: 'none', outline: 'none',
              fontSize: 12, color: 'var(--body, #e0e0e0)',
            }}
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute, #888)', padding: 0 }}>
              <X size={12} />
            </button>
          )}
        </div>
        {/* 类型筛选 */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setFilterType(prev => {
              const types: Array<FileType | 'all'> = ['all', 'docx', 'xlsx', 'pptx'];
              const idx = types.indexOf(prev);
              return types[(idx + 1) % types.length];
            })}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '4px 8px', borderRadius: 6, fontSize: 11,
              background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
              border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
              color: 'var(--body, #e0e0e0)', cursor: 'pointer',
            }}
          >
            <Filter size={12} />
            {filterType === 'all' ? '全部' : filterType.toUpperCase()}
          </button>
        </div>
      </div>

      {/* 操作按钮 */}
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid var(--hairline, rgba(255,255,255,0.06))',
        display: 'flex', gap: 6,
      }}>
        {/* 新建文档 */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => { setShowCreateMenu(prev => !prev); setShowTemplateMenu(false); }}
            disabled={creating}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '5px 10px', borderRadius: 6, fontSize: 12,
              background: 'var(--accent, #6366f1)', color: '#fff',
              border: 'none', cursor: creating ? 'wait' : 'pointer',
              opacity: creating ? 0.7 : 1,
            }}
          >
            {creating ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />}
            新建文档
          </button>
          {showCreateMenu && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, zIndex: 100,
              marginTop: 4, borderRadius: 8, overflow: 'hidden',
              background: 'var(--glass-bg, #2a2a3e)',
              border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
              boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
              minWidth: 140,
            }}>
              {[
                { type: 'docx' as FileType, label: 'Word 文档', icon: <FileText size={14} style={{ color: '#4285f4' }} /> },
                { type: 'xlsx' as FileType, label: 'Excel 表格', icon: <FileSpreadsheet size={14} style={{ color: '#0f9d58' }} /> },
                { type: 'pptx' as FileType, label: 'PowerPoint 演示', icon: <Presentation size={14} style={{ color: '#db4437' }} /> },
              ].map(item => (
                <button
                  key={item.type}
                  onClick={() => handleCreate(item.type)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '8px 12px', width: '100%',
                    background: 'transparent', border: 'none',
                    color: 'var(--body, #e0e0e0)', fontSize: 12,
                    cursor: 'pointer', textAlign: 'left',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover, rgba(255,255,255,0.06))'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 从模板创建 */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => { setShowTemplateMenu(prev => !prev); setShowCreateMenu(false); }}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '5px 10px', borderRadius: 6, fontSize: 12,
              background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
              border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
              color: 'var(--body, #e0e0e0)', cursor: 'pointer',
            }}
          >
            <File size={13} />
            从模板创建
            <ChevronDown size={12} />
          </button>
          {showTemplateMenu && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, zIndex: 100,
              marginTop: 4, borderRadius: 8, overflow: 'hidden',
              background: 'var(--glass-bg, #2a2a3e)',
              border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
              boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
              minWidth: 200, maxHeight: 240, overflowY: 'auto',
            }}>
              {templates.length === 0 ? (
                <div style={{ padding: '12px', fontSize: 12, color: 'var(--mute, #888)', textAlign: 'center' }}>
                  暂无可用模板
                </div>
              ) : (
                templates.map(tpl => (
                  <button
                    key={tpl.id}
                    onClick={() => handleCreateFromTemplate(tpl)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '8px 12px', width: '100%',
                      background: 'transparent', border: 'none',
                      color: 'var(--body, #e0e0e0)', fontSize: 12,
                      cursor: 'pointer', textAlign: 'left',
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover, rgba(255,255,255,0.06))'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <FileTypeIcon type={tpl.file_type} />
                    <div>
                      <div>{tpl.name}</div>
                      {tpl.description && (
                        <div style={{ fontSize: 10, color: 'var(--mute, #888)' }}>{tpl.description}</div>
                      )}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* 文档列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: 200, color: 'var(--mute, #888)',
          }}>
            <Loader2 size={20} className="animate-spin" />
            <span style={{ marginLeft: 8, fontSize: 13 }}>加载中...</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          /* 空状态 */
          <div style={{
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            height: 200, color: 'var(--mute, #888)', gap: 8,
          }}>
            <FileText size={32} style={{ opacity: 0.3 }} />
            <span style={{ fontSize: 13 }}>暂无文档</span>
            <span style={{ fontSize: 11, opacity: 0.6 }}>点击「新建文档」创建你的第一个文档</span>
          </div>
        ) : (
          filteredDocs.map(doc => (
            <div
              key={doc.id}
              onClick={() => onOpenDocument?.(doc)}
              style={{
                padding: '10px 12px',
                borderBottom: '1px solid var(--hairline, rgba(255,255,255,0.04))',
                cursor: 'pointer',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover, rgba(255,255,255,0.04))'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <FileTypeIcon type={doc.file_type} />
                <span style={{
                  flex: 1, fontSize: 13, fontWeight: 500,
                  color: 'var(--body, #e0e0e0)',
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {doc.title}
                </span>
                <button
                  onClick={e => handleDelete(doc.id, e)}
                  title="删除"
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--mute, #888)', padding: 2, opacity: 0.5,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.opacity = '1'; e.currentTarget.style.color = '#ef4444'; }}
                  onMouseLeave={e => { e.currentTarget.style.opacity = '0.5'; e.currentTarget.style.color = 'var(--mute, #888)'; }}
                >
                  <Trash2 size={13} />
                </button>
              </div>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                fontSize: 11, color: 'var(--mute, #888)', paddingLeft: 24,
              }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                  <HardDrive size={10} /> {formatFileSize(doc.file_size)}
                </span>
                {doc.updated_at && (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                    <Clock size={10} /> {formatDate(doc.updated_at)}
                  </span>
                )}
                <span style={{
                  padding: '1px 6px', borderRadius: 3, fontSize: 10,
                  background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                  border: '1px solid var(--hairline, rgba(255,255,255,0.08))',
                }}>
                  {doc.file_type.toUpperCase()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
