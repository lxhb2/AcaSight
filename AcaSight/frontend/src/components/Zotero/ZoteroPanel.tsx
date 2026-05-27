import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderOpen, FolderClosed, FileText, Search, RefreshCw, ChevronRight, ChevronDown,
  Loader2, ExternalLink, BookOpen, Calendar, Hash, X, Link as LinkIcon,
} from 'lucide-react';
import { zoteroApi } from '@/services/api';

/* ---------- Types ---------- */
interface ZoteroCollection {
  key: string;
  name: string;
  parent?: boolean;
  parentCollection?: string;
  meta?: { numItems?: number };
  children?: ZoteroCollection[];
}

interface ZoteroItem {
  key: string;
  itemType?: string;
  title?: string;
  creators?: Array<{ firstName?: string; lastName?: string; name?: string }>;
  date?: string;
  publicationTitle?: string;
  DOI?: string;
  url?: string;
  abstractNote?: string;
  tags?: Array<{ tag: string }>;
  attachments?: Array<{ contentType?: string; path?: string; title?: string; key?: string }>;
}

/* ---------- Helpers ---------- */
function parseItem(raw: any): ZoteroItem {
  const d = raw?.data || raw;
  return {
    key: d.key || raw?.key || '',
    itemType: d.itemType,
    title: d.title || '(无标题)',
    creators: d.creators || [],
    date: d.date || '',
    publicationTitle: d.publicationTitle || d.proceedingsTitle || '',
    DOI: d.DOI || '',
    url: d.url || '',
    abstractNote: d.abstractNote || '',
    tags: d.tags || [],
    attachments: d.attachments || d.relations?.attachments || [],
  };
}

function formatAuthors(creators: ZoteroItem['creators']): string {
  if (!creators?.length) return '未知作者';
  return creators.slice(0, 3).map(c => c.name || `${c.lastName || ''}${c.firstName ? ', ' + c.firstName : ''}`).join('; ')
    + (creators.length > 3 ? ' 等' : '');
}

/* ---------- Collection Tree ---------- */
const CollectionTree: React.FC<{
  collections: ZoteroCollection[];
  selectedKey: string | null;
  onSelect: (key: string) => void;
  expandedKeys: Set<string>;
  toggleExpand: (key: string) => void;
  depth?: number;
}> = ({ collections, selectedKey, onSelect, expandedKeys, toggleExpand, depth = 0 }) => {
  if (!collections?.length) return null;
  return (
    <div>
      {collections.map(col => {
        const isExpanded = expandedKeys.has(col.key);
        const isSelected = selectedKey === col.key;
        const hasChildren = (col.children?.length ?? 0) > 0;
        return (
          <div key={col.key}>
            <div
              onClick={() => { onSelect(col.key); if (hasChildren) toggleExpand(col.key); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '5px 8px 5px ' + (8 + depth * 16) + 'px',
                cursor: 'pointer', fontSize: 12,
                background: isSelected ? 'var(--sidebar-active, rgba(255,255,255,0.12))' : 'transparent',
                color: isSelected ? 'var(--text-primary, #e0e0e0)' : 'var(--text-secondary, #aaa)',
                borderRadius: 4, margin: '1px 4px',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'var(--sidebar-hover, rgba(255,255,255,0.06))'; }}
              onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
            >
              {hasChildren ? (
                isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
              ) : (
                <span style={{ width: 12, display: 'inline-block' }} />
              )}
              {isExpanded ? (
                <FolderOpen size={13} style={{ color: '#f0a030', flexShrink: 0 }} />
              ) : (
                <FolderClosed size={13} style={{ color: '#c08020', flexShrink: 0 }} />
              )}
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {col.name}
              </span>
              {col.meta?.numItems != null && (
                <span style={{ fontSize: 10, color: 'var(--text-muted, #666)', flexShrink: 0 }}>
                  {col.meta.numItems}
                </span>
              )}
            </div>
            {hasChildren && isExpanded && (
              <CollectionTree
                collections={col.children!}
                selectedKey={selectedKey}
                onSelect={onSelect}
                expandedKeys={expandedKeys}
                toggleExpand={toggleExpand}
                depth={depth + 1}
              />
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ---------- Item List ---------- */
const ItemList: React.FC<{
  items: ZoteroItem[];
  selectedItemKey: string | null;
  onSelect: (item: ZoteroItem) => void;
  onOpenPdf: (item: ZoteroItem) => void;
  loading: boolean;
}> = ({ items, selectedItemKey, onSelect, onOpenPdf, loading }) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--text-muted, #666)' }}>
        <Loader2 size={20} className="animate-spin" /> <span style={{ marginLeft: 8, fontSize: 13 }}>加载中...</span>
      </div>
    );
  }
  if (!items.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--text-muted, #666)', fontSize: 13 }}>
        暂无文献
      </div>
    );
  }
  return (
    <div style={{ overflow: 'auto', flex: 1 }}>
      {items.map(item => {
        const isSelected = selectedItemKey === item.key;
        const hasPdf = item.attachments?.some(a => a.contentType === 'application/pdf');
        return (
          <div
            key={item.key}
            onClick={() => onSelect(item)}
            style={{
              padding: '8px 12px',
              borderBottom: '1px solid var(--panel-border, rgba(255,255,255,0.06))',
              cursor: 'pointer',
              background: isSelected ? 'var(--sidebar-active, rgba(255,255,255,0.08))' : 'transparent',
              transition: 'background 0.1s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--sidebar-hover, rgba(255,255,255,0.04))'; }}
            onMouseLeave={e => { e.currentTarget.style.background = isSelected ? 'var(--sidebar-active, rgba(255,255,255,0.08))' : 'transparent'; }}
          >
            <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary, #e0e0e0)', lineHeight: 1.4, marginBottom: 4 }}>
              {item.title}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', fontSize: 11, color: 'var(--text-muted, #888)' }}>
              <span>{formatAuthors(item.creators)}</span>
              {item.date && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Calendar size={10} /> {item.date.slice(0, 4)}
                </span>
              )}
              {item.publicationTitle && (
                <span style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <BookOpen size={10} /> {item.publicationTitle}
                </span>
              )}
              {hasPdf && (
                <button
                  onClick={e => { e.stopPropagation(); onOpenPdf(item); }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 2,
                    padding: '1px 6px', borderRadius: 3, fontSize: 10,
                    background: 'var(--sidebar-hover, rgba(255,255,255,0.06))',
                    border: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
                    color: '#10b981', cursor: 'pointer',
                  }}
                >
                  <FileText size={10} /> PDF
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

/* ---------- Item Detail ---------- */
const ItemDetail: React.FC<{
  item: ZoteroItem;
  onOpenPdf: (item: ZoteroItem) => void;
  onClose: () => void;
}> = ({ item, onOpenPdf, onClose }) => {
  const hasPdf = item.attachments?.some(a => a.contentType === 'application/pdf');
  return (
    <div style={{ padding: 12, overflow: 'auto', flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary, #e0e0e0)', lineHeight: 1.4, flex: 1 }}>
          {item.title}
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted, #888)', padding: 2 }}>
          <X size={14} />
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 12, marginBottom: 12 }}>
        <div><span style={{ color: 'var(--text-muted, #888)' }}>作者: </span><span style={{ color: 'var(--text-secondary, #aaa)' }}>{formatAuthors(item.creators)}</span></div>
        {item.date && <div><span style={{ color: 'var(--text-muted, #888)' }}>年份: </span><span style={{ color: 'var(--text-secondary, #aaa)' }}>{item.date}</span></div>}
        {item.publicationTitle && <div style={{ gridColumn: 'span 2' }}><span style={{ color: 'var(--text-muted, #888)' }}>期刊: </span><span style={{ color: 'var(--text-secondary, #aaa)' }}>{item.publicationTitle}</span></div>}
        {item.DOI && (
          <div style={{ gridColumn: 'span 2' }}>
            <span style={{ color: 'var(--text-muted, #888)' }}>DOI: </span>
            <a href={`https://doi.org/${item.DOI}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--accent, #6366f1)', textDecoration: 'none', fontSize: 11 }}>
              {item.DOI}
            </a>
          </div>
        )}
        {item.itemType && <div><span style={{ color: 'var(--text-muted, #888)' }}>类型: </span><span style={{ color: 'var(--text-secondary, #aaa)' }}>{item.itemType}</span></div>}
      </div>

      {(item.tags?.length ?? 0) > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted, #888)', marginBottom: 4, textTransform: 'uppercase' }}>标签</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {item.tags!.map((t, i) => (
              <span key={i} style={{
                padding: '2px 8px', borderRadius: 10, fontSize: 10,
                background: 'var(--sidebar-hover, rgba(255,255,255,0.06))',
                border: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
                color: 'var(--text-secondary, #aaa)',
              }}>
                <Hash size={9} style={{ marginRight: 2, verticalAlign: -1 }} />{t.tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {item.abstractNote && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted, #888)', marginBottom: 4, textTransform: 'uppercase' }}>摘要</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary, #aaa)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {item.abstractNote}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {hasPdf && (
          <button
            onClick={() => onOpenPdf(item)}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '6px 12px', borderRadius: 6, fontSize: 12,
              background: '#10b981', color: '#fff', border: 'none', cursor: 'pointer',
            }}
          >
            <FileText size={13} /> 在阅读器中打开
          </button>
        )}
        {item.DOI && (
          <a
            href={`https://doi.org/${item.DOI}`}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '6px 12px', borderRadius: 6, fontSize: 12,
              background: 'var(--sidebar-hover, rgba(255,255,255,0.06))',
              border: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
              color: 'var(--text-secondary, #aaa)', textDecoration: 'none',
            }}
          >
            <ExternalLink size={13} /> DOI
          </a>
        )}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '6px 12px', borderRadius: 6, fontSize: 12,
              background: 'var(--sidebar-hover, rgba(255,255,255,0.06))',
              border: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
              color: 'var(--text-secondary, #aaa)', textDecoration: 'none',
            }}
          >
            <LinkIcon size={13} /> 来源
          </a>
        )}
      </div>
    </div>
  );
};

/* ---------- Main Panel ---------- */
export const ZoteroPanel: React.FC<{
  onOpenPdf?: (itemKey: string, title: string) => void;
}> = ({ onOpenPdf }) => {
  const [connected, setConnected] = useState(false);
  const [collections, setCollections] = useState<ZoteroCollection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [items, setItems] = useState<ZoteroItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<ZoteroItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [colLoading, setColLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchMode, setSearchMode] = useState(false);

  // 检查连接状态
  const checkStatus = useCallback(async () => {
    try {
      const res = await zoteroApi.status();
      setConnected(res.connected);
      return res.connected;
    } catch {
      setConnected(false);
      return false;
    }
  }, []);

  // 加载集合树
  const loadCollections = useCallback(async () => {
    setColLoading(true);
    try {
      const result = await zoteroApi.getCollections();
      // MCP 返回的格式可能是 content[0].text (JSON)
      let parsed: any[] = [];
      const content = result?.content || result;
      if (Array.isArray(content)) {
        const textItem = content.find((c: any) => c.type === 'text');
        if (textItem?.text) {
          try { parsed = JSON.parse(textItem.text); } catch { parsed = content; }
        } else {
          parsed = content;
        }
      } else if (typeof content === 'string') {
        try { parsed = JSON.parse(content); } catch { parsed = []; }
      }
      setCollections(buildTree(parsed));
    } catch (e) {
      console.error('Failed to load collections:', e);
      setCollections([]);
    } finally {
      setColLoading(false);
    }
  }, []);

  // 构建集合树
  function buildTree(flat: any[]): ZoteroCollection[] {
    if (!Array.isArray(flat)) return [];
    const map = new Map<string, ZoteroCollection>();
    const roots: ZoteroCollection[] = [];
    for (const item of flat) {
      const d = item.data || item;
      const col: ZoteroCollection = {
        key: d.key || d.collectionKey || '',
        name: d.name || '(未命名)',
        parentCollection: d.parentCollection || d.parent || '',
        meta: d.meta,
        children: [],
      };
      map.set(col.key, col);
    }
    for (const col of map.values()) {
      if (col.parentCollection && map.has(col.parentCollection)) {
        map.get(col.parentCollection)!.children!.push(col);
      } else {
        roots.push(col);
      }
    }
    return roots;
  }

  // 加载集合内条目
  const loadCollectionItems = useCallback(async (colKey: string) => {
    setLoading(true);
    setItems([]);
    try {
      const result = await zoteroApi.getCollectionItems(colKey, 50);
      let parsed: any[] = [];
      const content = result?.content || result;
      if (Array.isArray(content)) {
        const textItem = content.find((c: any) => c.type === 'text');
        if (textItem?.text) {
          try { parsed = JSON.parse(textItem.text); } catch { parsed = content; }
        } else {
          parsed = content;
        }
      } else if (typeof content === 'string') {
        try { parsed = JSON.parse(content); } catch { parsed = []; }
      }
      setItems(parsed.map(parseItem));
    } catch (e) {
      console.error('Failed to load items:', e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 搜索
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setSearchMode(true);
    setLoading(true);
    setItems([]);
    try {
      const result = await zoteroApi.search({ q: searchQuery, limit: 30, mode: 'standard' });
      let parsed: any[] = [];
      const content = result?.content || result;
      if (Array.isArray(content)) {
        const textItem = content.find((c: any) => c.type === 'text');
        if (textItem?.text) {
          try { parsed = JSON.parse(textItem.text); } catch { parsed = content; }
        } else {
          parsed = content;
        }
      } else if (typeof content === 'string') {
        try { parsed = JSON.parse(content); } catch { parsed = []; }
      }
      setItems(parsed.map(parseItem));
    } catch (e) {
      console.error('Search failed:', e);
    } finally {
      setLoading(false);
    }
  }, [searchQuery]);

  // 打开 PDF
  const handleOpenPdf = useCallback((item: ZoteroItem) => {
    if (onOpenPdf) {
      onOpenPdf(item.key, item.title || '(无标题)');
    } else {
      // 默认行为：通过后端 API 直接打开
      window.open(`http://localhost:9000/api/zotero/items/${item.key}/pdf`, '_blank');
    }
  }, [onOpenPdf]);

  // 初始化
  useEffect(() => {
    checkStatus().then(ok => { if (ok) loadCollections(); });
  }, [checkStatus, loadCollections]);

  // 切换集合展开
  const toggleExpand = useCallback((key: string) => {
    setExpandedKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }, []);

  // 选择集合
  const handleSelectCollection = useCallback((key: string) => {
    setSelectedCollection(key);
    setSelectedItem(null);
    setSearchMode(false);
    loadCollectionItems(key);
  }, [loadCollectionItems]);

  // 清除搜索
  const clearSearch = useCallback(() => {
    setSearchQuery('');
    setSearchMode(false);
    if (selectedCollection) loadCollectionItems(selectedCollection);
  }, [selectedCollection, loadCollectionItems]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--panel-bg, #1e1e2e)' }}>
      {/* Header */}
      <div style={{
        padding: '8px 12px',
        borderBottom: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <BookOpen size={16} style={{ color: '#6366f1' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary, #e0e0e0)' }}>Zotero 文献库</span>
        <div style={{ flex: 1 }} />
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 10,
          background: connected ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
          color: connected ? '#10b981' : '#ef4444',
        }}>
          {connected ? '已连接' : '未连接'}
        </span>
        <button
          onClick={() => { checkStatus().then(ok => { if (ok) loadCollections(); }); }}
          title="刷新"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted, #888)', padding: 2 }}
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Search */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--panel-border, rgba(255,255,255,0.06))' }}>
        <div style={{ display: 'flex', gap: 4 }}>
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            placeholder="搜索文献..."
            style={{
              flex: 1, padding: '5px 10px', borderRadius: 6, fontSize: 12,
              background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
              border: '1px solid var(--panel-border, rgba(255,255,255,0.1))',
              color: 'var(--text-primary, #e0e0e0)', outline: 'none',
            }}
          />
          <button
            onClick={handleSearch}
            disabled={!searchQuery.trim()}
            style={{
              padding: '5px 10px', borderRadius: 6, fontSize: 12,
              background: 'var(--accent, #6366f1)', color: '#fff',
              border: 'none', cursor: searchQuery.trim() ? 'pointer' : 'default',
              opacity: searchQuery.trim() ? 1 : 0.5,
            }}
          >
            <Search size={13} />
          </button>
          {searchMode && (
            <button onClick={clearSearch} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted, #888)', padding: 2 }}>
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Main content: tree + items */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left: Collection tree */}
        <div style={{
          width: 200, minWidth: 150, borderRight: '1px solid var(--panel-border, rgba(255,255,255,0.06))',
          overflow: 'auto', flexShrink: 0,
        }}>
          {colLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 100, color: 'var(--text-muted, #666)' }}>
              <Loader2 size={16} className="animate-spin" />
            </div>
          ) : (
            <CollectionTree
              collections={collections}
              selectedKey={selectedCollection}
              onSelect={handleSelectCollection}
              expandedKeys={expandedKeys}
              toggleExpand={toggleExpand}
            />
          )}
        </div>

        {/* Right: Items or Detail */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {selectedItem ? (
            <ItemDetail item={selectedItem} onOpenPdf={handleOpenPdf} onClose={() => setSelectedItem(null)} />
          ) : (
            <>
              {/* Items header */}
              <div style={{
                padding: '6px 12px', fontSize: 11, color: 'var(--text-muted, #888)',
                borderBottom: '1px solid var(--panel-border, rgba(255,255,255,0.06))',
                display: 'flex', alignItems: 'center', gap: 4,
              }}>
                {searchMode ? (
                  <><Search size={11} /> 搜索结果: {items.length} 篇</>
                ) : selectedCollection ? (
                  <><FolderOpen size={11} /> 文献列表: {items.length} 篇</>
                ) : (
                  '选择集合或搜索查看文献'
                )}
              </div>
              <ItemList
                items={items}
                selectedItemKey={null}
                onSelect={(item) => setSelectedItem(item)}
                onOpenPdf={handleOpenPdf}
                loading={loading}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
};
