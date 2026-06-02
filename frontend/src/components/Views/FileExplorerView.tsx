/**
 * FileExplorerView — 文献管理面板 (Chapter C 重构)
 *
 * 数据库驱动，支持搜索、标签筛选、收藏、阅读状态管理。
 * 右键上下文菜单：修改阅读状态、评分、标签。
 * Zotero 集成文献导入。
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Upload, FolderPlus, FilePlus,
  FileText, Loader2, Star,
  Bookmark, Trash2, X, MoreHorizontal, Plus,
} from 'lucide-react';
import { papersApi, zoteroApi } from '@/services/api';
import type { PaperItem, TagInfo } from '@/services/api';
import { useApp } from '@/contexts/AppContext';
import { type ZoteroItem } from '@/contexts/AppContext';

type SortField = 'created_at' | 'title' | 'year' | 'citation_count';

const READ_STATUS_LABELS: Record<string, string> = {
  unread: '未读',
  reading: '在读',
  read: '已读',
};

const READ_STATUS_COLORS: Record<string, string> = {
  unread: 'var(--mute)',
  reading: 'var(--accent)',
  read: 'var(--success, #10b981)',
};

interface ContextMenuState {
  x: number;
  y: number;
  paper: PaperItem;
}

export const FileExplorerView: React.FC = () => {
  const {
    openFile, fileInputRef,
    zoteroConnected, setZoteroConnected,
    setZoteroCollections,
    zoteroItems,
  } = useApp();

  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const [activeStatus, setActiveStatus] = useState<string | null>(null);
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [sortBy, setSortBy] = useState<SortField>('created_at');
  const [page, setPage] = useState(1);
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [selectedPaper, setSelectedPaper] = useState<PaperItem | null>(null);
  const [newTagInput, setNewTagInput] = useState('');
  const [showTagInput, setShowTagInput] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const loadPapers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await papersApi.list({
        page,
        page_size: 50,
        sort_by: sortBy,
        sort_order: 'desc',
        search: searchQuery || undefined,
        tag: activeTag || undefined,
        read_status: activeStatus || undefined,
        is_favorite: showFavoritesOnly ? 1 : undefined,
      });
      setPapers(res.items);
      setTotalCount(res.total);
    } catch (err) {
      console.error('Failed to load papers:', err);
    } finally {
      setLoading(false);
    }
  }, [page, sortBy, searchQuery, activeTag, activeStatus, showFavoritesOnly]);

  const loadTags = useCallback(async () => {
    try {
      const res = await papersApi.tags();
      setTags(res.tags);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadPapers(); }, [loadPapers]);
  useEffect(() => { loadTags(); }, [loadTags]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1);
      loadPapers();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  const handleToggleFavorite = useCallback(async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await papersApi.toggleFavorite(id);
      loadPapers();
    } catch { /* ignore */ }
  }, [loadPapers]);

  const handleDelete = useCallback(async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    try {
      await papersApi.delete(id);
      loadPapers();
      loadTags();
      if (selectedPaper?.id === id) setSelectedPaper(null);
    } catch { /* ignore */ }
  }, [loadPapers, loadTags, selectedPaper]);

  const handleOpenPaper = useCallback((paper: PaperItem) => {
    setSelectedPaper(paper);
    const meta = {
      abstract: paper.abstract || undefined,
      authors: (paper.authors || []).join(', ') || undefined,
      year: paper.year || undefined,
      journal: paper.journal || undefined,
    };
    if (paper.pdf_path) {
      openFile(paper.title + '.pdf', 'pdf', { pdfUrl: `/api/pdf/proxy?url=${encodeURIComponent(paper.pdf_path)}`, ...meta });
    } else {
      openFile(paper.title + '.pdf', 'pdf', meta);
    }
  }, [openFile]);

  const handleContextMenu = useCallback((e: React.MouseEvent, paper: PaperItem) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY, paper });
  }, []);

  const handleSetReadStatus = useCallback(async (paperId: number, status: string) => {
    try {
      await papersApi.updateReadStatus(paperId, status);
      loadPapers();
    } catch { /* ignore */ }
    setContextMenu(null);
  }, [loadPapers]);

  const handleSetRating = useCallback(async (paperId: number, rating: number) => {
    try {
      await papersApi.updateRating(paperId, rating);
      loadPapers();
    } catch { /* ignore */ }
    setContextMenu(null);
  }, [loadPapers]);

  const handleAddTag = useCallback(async () => {
    if (!contextMenu?.paper || !newTagInput.trim()) return;
    try {
      await papersApi.addTag(contextMenu.paper.id, newTagInput.trim());
      loadPapers();
      loadTags();
    } catch { /* ignore */ }
    setNewTagInput('');
    setShowTagInput(false);
    setContextMenu(null);
  }, [contextMenu, newTagInput, loadPapers, loadTags]);

  const handleRemoveTag = useCallback(async (paperId: number, tagName: string) => {
    try {
      await papersApi.removeTag(paperId, tagName);
      loadPapers();
      loadTags();
    } catch { /* ignore */ }
    setContextMenu(null);
  }, [loadPapers, loadTags]);

  const parseMcpResult = (data: Record<string, unknown>): unknown => {
    if (data?.content && Array.isArray(data.content)) {
      const textItem = (data.content as Array<Record<string, unknown>>).find((c) => c.type === 'text');
      if (textItem?.text) {
        try { return JSON.parse(textItem.text as string); } catch { return textItem.text; }
      }
    }
    return data;
  };

  const importFromZotero = useCallback(async () => {
    if (!zoteroItems.length) return;
    const papersToImport = zoteroItems.map((item: ZoteroItem) => ({
      title: item.title || '未命名文献',
      authors: (item.creators || []).map((c) => c.name || `${c.firstName || ''} ${c.lastName || ''}`.trim()).filter(Boolean),
      abstract: item.abstractNote || null,
      doi: item.DOI || null,
      year: item.date ? parseInt(item.date.substring(0, 4)) || null : null,
      journal: item.publicationTitle || null,
      tags: (item.tags || []).map((t) => (typeof t === 'string' ? t : t.tag || '')).filter(Boolean),
      keywords: (item.tags || []).map((t) => (typeof t === 'string' ? t : t.tag || '')).filter(Boolean),
    }));
    try {
      await papersApi.batchImport(papersToImport);
      loadPapers();
      loadTags();
    } catch { /* ignore */ }
  }, [zoteroItems, loadPapers, loadTags]);

  return (
    <>
      {/* 工具栏 */}
      <div className="acasight-tree-toolbar">
        <button className="acasight-tree-btn" title="导入 PDF" onClick={() => fileInputRef.current?.click()}>
          <Upload size={14} />
        </button>
        <button className="acasight-tree-btn" title="新建文件夹"><FolderPlus size={14} /></button>
        <button className="acasight-tree-btn" title="新建笔记"><FilePlus size={14} /></button>
        <button
          className={`acasight-tree-btn ${showFavoritesOnly ? 'active' : ''}`}
          title="仅显示收藏"
          onClick={() => setShowFavoritesOnly(v => !v)}
          style={showFavoritesOnly ? { color: 'var(--accent)' } : {}}
        >
          <Bookmark size={14} />
        </button>
        <input
          className="acasight-tree-search"
          type="text"
          placeholder="搜索文献..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
      </div>

      {/* 标签云 */}
      {tags.length > 0 && (
        <div style={{ padding: '4px 8px', borderBottom: '1px solid var(--hairline)', display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {activeTag && (
            <span
              className="acasight-tag-item"
              style={{ background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 10 }}
              onClick={() => setActiveTag(null)}
            >
              清除 <X size={8} />
            </span>
          )}
          {tags.slice(0, 15).map(t => (
            <span
              key={t.name}
              className="acasight-tag-item"
              style={{
                fontSize: 10,
                cursor: 'pointer',
                background: activeTag === t.name ? 'var(--accent)' : 'var(--accent-bg-soft)',
                color: activeTag === t.name ? '#fff' : 'var(--body)',
              }}
              onClick={() => setActiveTag(activeTag === t.name ? null : t.name)}
            >
              #{t.name}<span className="acasight-tag-count">{t.count}</span>
            </span>
          ))}
        </div>
      )}

      {/* 阅读状态筛选 */}
      <div style={{ padding: '4px 8px', borderBottom: '1px solid var(--hairline)', display: 'flex', gap: 4, fontSize: 10 }}>
        {Object.entries(READ_STATUS_LABELS).map(([key, label]) => (
          <button
            key={key}
            style={{
              padding: '2px 6px',
              borderRadius: 3,
              border: 'none',
              background: activeStatus === key ? 'var(--accent)' : 'transparent',
              color: activeStatus === key ? '#fff' : READ_STATUS_COLORS[key],
              cursor: 'pointer',
              fontSize: 10,
            }}
            onClick={() => setActiveStatus(activeStatus === key ? null : key)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Zotero 连接状态 */}
      {zoteroConnected && (
        <div style={{ padding: '4px 8px', background: 'var(--accent-bg-soft)', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }} />
          <span style={{ color: 'var(--body)' }}>Zotero 已连接</span>
          <span style={{ flex: 1 }} />
          <button style={{ fontSize: 10, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }} onClick={importFromZotero}>导入</button>
        </div>
      )}

      {!zoteroConnected && (
        <div style={{ padding: '4px 8px', background: 'rgba(243,139,168,0.08)', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--danger)', display: 'inline-block' }} />
          <span style={{ color: 'var(--mute)' }}>Zotero 未连接</span>
          <span style={{ flex: 1 }} />
          <button
            style={{ fontSize: 10, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}
            onClick={async () => {
              try {
                const res = await zoteroApi.status();
                setZoteroConnected(res.connected);
                if (res.connected) {
                  const colsRaw = await zoteroApi.getCollections();
                  const cols = parseMcpResult(colsRaw);
                  setZoteroCollections(Array.isArray(cols) ? cols : []);
                }
              } catch { /* ignore */ }
            }}
          >重试</button>
        </div>
      )}

      {/* 排序 */}
      <div style={{ padding: '4px 8px', borderBottom: '1px solid var(--hairline)', display: 'flex', gap: 4, fontSize: 10, color: 'var(--mute)' }}>
        <span>排序:</span>
        {([['created_at', '时间'], ['title', '标题'], ['year', '年份'], ['citation_count', '引用']] as [SortField, string][]).map(([field, label]) => (
          <button
            key={field}
            style={{
              padding: '1px 4px',
              borderRadius: 2,
              border: 'none',
              background: sortBy === field ? 'var(--accent-bg-soft)' : 'transparent',
              color: sortBy === field ? 'var(--accent)' : 'var(--mute)',
              cursor: 'pointer',
              fontSize: 10,
            }}
            onClick={() => setSortBy(field)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 文献列表 */}
      <div ref={containerRef} style={{ flex: 1, overflowY: 'auto' }}>
        {loading && (
          <div style={{ padding: 12, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
            <Loader2 size={14} className="animate-spin" style={{ display: 'inline', marginRight: 4 }} />加载中...
          </div>
        )}

        {!loading && papers.length === 0 && (
          <div style={{ padding: 16, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
            {searchQuery ? '未找到匹配的文献' : '暂无文献，上传 PDF 或从 Zotero 导入'}
          </div>
        )}

        {papers.map(paper => (
          <div
            key={paper.id}
            className="acasight-tree-item"
            style={{
              paddingLeft: 12, paddingRight: 8, display: 'flex', alignItems: 'center', gap: 6, minHeight: 36,
              background: selectedPaper?.id === paper.id ? 'var(--accent-bg-soft)' : undefined,
            }}
            onClick={() => handleOpenPaper(paper)}
            onContextMenu={e => handleContextMenu(e, paper)}
          >
            <span
              style={{
                width: 4, height: 4, borderRadius: '50%', flexShrink: 0,
                background: READ_STATUS_COLORS[paper.read_status] || 'var(--mute)',
              }}
            />

            <FileText size={14} style={{ flexShrink: 0, color: paper.pdf_path ? 'var(--accent)' : 'var(--mute)' }} />

            <span style={{
              flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              fontSize: 12, color: 'var(--body)',
            }}>
              {paper.title}
            </span>

            {paper.tags && paper.tags.length > 0 && (
              <span style={{ fontSize: 8, color: 'var(--accent)', flexShrink: 0, maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                #{paper.tags[0]}
              </span>
            )}

            {paper.year && (
              <span style={{ fontSize: 9, color: 'var(--mute)', flexShrink: 0 }}>{paper.year}</span>
            )}

            <button
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, flexShrink: 0, color: paper.is_favorite ? 'var(--warning, #f59e0b)' : 'var(--mute)' }}
              onClick={e => handleToggleFavorite(e, paper.id)}
            >
              <Star size={12} fill={paper.is_favorite ? 'var(--warning, #f59e0b)' : 'none'} />
            </button>

            <button
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, flexShrink: 0, color: 'var(--mute)', opacity: 0.5 }}
              onClick={e => { e.stopPropagation(); handleContextMenu(e, paper); }}
            >
              <MoreHorizontal size={12} />
            </button>
          </div>
        ))}

        {totalCount > 50 && (
          <div style={{ padding: 8, textAlign: 'center', fontSize: 10, color: 'var(--mute)' }}>
            显示 {papers.length} / {totalCount} 篇
            {page > 1 && <button style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)' }} onClick={() => setPage(p => p - 1)}>上一页</button>}
            {page * 50 < totalCount && <button style={{ marginLeft: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)' }} onClick={() => setPage(p => p + 1)}>下一页</button>}
          </div>
        )}

        {/* 空状态 + 论文统计 */}
        {!loading && papers.length === 0 && !searchQuery && (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
            <FileText size={32} style={{ opacity: 0.2, margin: '0 auto 8px' }} />
            <p>暂无文献</p>
            <p style={{ fontSize: 10, marginTop: 4 }}>上传 PDF 或从搜索结果入库</p>
          </div>
        )}
      </div>

      {/* 论文统计底栏 */}
      <div style={{
        padding: '4px 10px',
        borderTop: '1px solid var(--hairline)',
        fontSize: 10,
        color: 'var(--mute)',
        display: 'flex',
        gap: 8,
        alignItems: 'center',
        background: 'var(--canvas-soft)',
        flexShrink: 0,
      }}>
        <span>{totalCount} 篇文献</span>
        <span>·</span>
        <span>{tags.length} 个标签</span>
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 9, color: 'var(--accent)' }}>右键管理阅读状态/标签</span>
      </div>

      {/* 论文详情预览 */}
      {selectedPaper && (
        <div style={{
          borderTop: '1px solid var(--hairline)',
          padding: '6px 10px',
          fontSize: 10,
          maxHeight: 120,
          overflowY: 'auto',
          background: 'var(--glass-bg, var(--bg-2))',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <span style={{ fontWeight: 600, color: 'var(--body)', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, marginRight: 8 }}>
              {selectedPaper.title}
            </span>
            <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0 }} onClick={() => setSelectedPaper(null)}>
              <X size={10} />
            </button>
          </div>
          {selectedPaper.authors && selectedPaper.authors.length > 0 && (
            <div style={{ color: 'var(--mute)', marginBottom: 2 }}>
              {selectedPaper.authors.slice(0, 3).join(', ')}{selectedPaper.authors.length > 3 ? ` +${selectedPaper.authors.length - 3}` : ''}
            </div>
          )}
          <div style={{ display: 'flex', gap: 8, color: 'var(--mute)', marginBottom: 4 }}>
            {selectedPaper.journal && <span>{selectedPaper.journal}</span>}
            {selectedPaper.year && <span>{selectedPaper.year}</span>}
            {selectedPaper.doi && <span style={{ color: 'var(--accent)' }}>DOI: {selectedPaper.doi}</span>}
          </div>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center', marginBottom: 4 }}>
            <span style={{ color: READ_STATUS_COLORS[selectedPaper.read_status], fontSize: 9 }}>
              {READ_STATUS_LABELS[selectedPaper.read_status]}
            </span>
            {selectedPaper.rating > 0 && (
              <span style={{ color: 'var(--warning, #f59e0b)', fontSize: 9 }}>
                {'★'.repeat(selectedPaper.rating)}
              </span>
            )}
            {selectedPaper.tags && selectedPaper.tags.map(t => (
              <span key={t} className="acasight-tag-item" style={{ fontSize: 8 }}>#{t}</span>
            ))}
          </div>
          {selectedPaper.abstract && (
            <div style={{ color: 'var(--mute)', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {selectedPaper.abstract}
            </div>
          )}
        </div>
      )}

      {/* 右键上下文菜单 */}
      {contextMenu && (
        <div
          className="acasight-context-menu"
          style={{
            position: 'fixed',
            left: contextMenu.x,
            top: contextMenu.y,
            zIndex: 1000,
            minWidth: 160,
          }}
          onClick={e => e.stopPropagation()}
        >
          {/* 阅读状态 */}
          <div style={{ padding: '4px 8px', fontSize: 9, color: 'var(--mute)', fontWeight: 600 }}>阅读状态</div>
          {Object.entries(READ_STATUS_LABELS).map(([key, label]) => (
            <button
              key={key}
              className="acasight-context-menu-item"
              style={{
                display: 'flex', alignItems: 'center', gap: 6, width: '100%',
                padding: '4px 10px', border: 'none', background: contextMenu.paper.read_status === key ? 'var(--accent-bg-soft)' : 'transparent',
                color: contextMenu.paper.read_status === key ? 'var(--accent)' : 'var(--body)', cursor: 'pointer', fontSize: 11, textAlign: 'left',
              }}
              onClick={() => handleSetReadStatus(contextMenu.paper.id, key)}
            >
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: READ_STATUS_COLORS[key] }} />
              {label}
            </button>
          ))}

          <div style={{ height: 1, background: 'var(--hairline)', margin: '2px 8px' }} />

          {/* 评分 */}
          <div style={{ padding: '4px 8px', fontSize: 9, color: 'var(--mute)', fontWeight: 600 }}>评分</div>
          <div style={{ display: 'flex', padding: '2px 10px', gap: 2 }}>
            {[0, 1, 2, 3, 4, 5].map(r => (
              <button
                key={r}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: r <= contextMenu.paper.rating ? 'var(--warning, #f59e0b)' : 'var(--mute)',
                  fontSize: 12, padding: '1px 2px',
                }}
                onClick={() => handleSetRating(contextMenu.paper.id, r)}
              >
                {r === 0 ? '✕' : '★'}
              </button>
            ))}
          </div>

          <div style={{ height: 1, background: 'var(--hairline)', margin: '2px 8px' }} />

          {/* 标签 */}
          <div style={{ padding: '4px 8px', fontSize: 9, color: 'var(--mute)', fontWeight: 600 }}>标签</div>
          {contextMenu.paper.tags && contextMenu.paper.tags.map(t => (
            <div
              key={t}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '3px 10px', fontSize: 11, color: 'var(--body)' }}
            >
              <span>#{t}</span>
              <button
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0, fontSize: 10 }}
                onClick={() => handleRemoveTag(contextMenu.paper.id, t)}
              >
                <X size={10} />
              </button>
            </div>
          ))}
          {showTagInput ? (
            <div style={{ display: 'flex', padding: '3px 10px', gap: 4 }}>
              <input
                autoFocus
                style={{ flex: 1, background: 'var(--bg-2)', border: '1px solid var(--hairline)', borderRadius: 3, padding: '2px 6px', fontSize: 10, color: 'var(--body)', outline: 'none' }}
                value={newTagInput}
                onChange={e => setNewTagInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleAddTag(); }}
                placeholder="标签名"
              />
              <button
                style={{ background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 3, padding: '2px 6px', fontSize: 9, cursor: 'pointer' }}
                onClick={handleAddTag}
              >
                添加
              </button>
            </div>
          ) : (
            <button
              style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%', padding: '4px 10px', border: 'none', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 11, textAlign: 'left' }}
              onClick={() => setShowTagInput(true)}
            >
              <Plus size={10} /> 添加标签
            </button>
          )}

          <div style={{ height: 1, background: 'var(--hairline)', margin: '2px 8px' }} />

          {/* 删除 */}
          <button
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '4px 10px', border: 'none', background: 'transparent',
              color: 'var(--danger)', cursor: 'pointer', fontSize: 11, textAlign: 'left',
            }}
            onClick={e => handleDelete(e, contextMenu.paper.id)}
          >
            <Trash2 size={11} /> 删除
          </button>
        </div>
      )}
    </>
  );
};

