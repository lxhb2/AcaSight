/**
 * TagsView — 标签云面板 (Chapter C 重构)
 *
 * 数据库驱动，显示真实标签统计数据，支持点击筛选。
 * 标签颜色系统，点击论文可打开阅读器。
 */

import React, { useState, useEffect, useCallback } from 'react';
import { X, Search, FileText, Star, RefreshCw } from 'lucide-react';
import { papersApi } from '@/services/api';
import type { PaperItem, TagInfo } from '@/services/api';
import { useFileOpen } from '@/contexts/FileOpenContext';

const TAG_PALETTE = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
];

function getTagColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return TAG_PALETTE[Math.abs(hash) % TAG_PALETTE.length];
}

export const TagsView: React.FC = () => {
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [papersByTag, setPapersByTag] = useState<PaperItem[]>([]);
  const [papersLoading, setPapersLoading] = useState(false);

  const { openFile } = useFileOpen();

  const loadTags = useCallback(async () => {
    setLoading(true);
    try {
      const res = await papersApi.tags();
      setTags(res.tags);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadTags(); }, [loadTags]);

  const handleTagClick = useCallback(async (tagName: string) => {
    if (selectedTag === tagName) {
      setSelectedTag(null);
      setPapersByTag([]);
      return;
    }
    setSelectedTag(tagName);
    setPapersLoading(true);
    try {
      const res = await papersApi.list({ tag: tagName, page_size: 30 });
      setPapersByTag(res.items);
    } catch { /* ignore */ }
    finally { setPapersLoading(false); }
  }, [selectedTag]);

  const handleOpenPaper = useCallback((paper: PaperItem) => {
    const meta = {
      abstract: paper.abstract || undefined,
      authors: (paper.authors || []).join(', ') || undefined,
      year: paper.year || undefined,
      journal: paper.journal || undefined,
    };
    if (paper.pdf_path) {
      openFile(paper.title + '.pdf', 'pdf', { pdfUrl: `http://localhost:9000/api/pdf/proxy?url=${encodeURIComponent(paper.pdf_path)}`, ...meta });
    } else {
      openFile(paper.title + '.pdf', 'pdf', meta);
    }
  }, [openFile]);

  const filteredTags = searchQuery
    ? tags.filter(t => t.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : tags;

  const maxCount = Math.max(...tags.map(t => t.count), 1);
  const getTagSize = (count: number) => {
    const ratio = count / maxCount;
    if (ratio > 0.7) return 16;
    if (ratio > 0.4) return 14;
    if (ratio > 0.2) return 12;
    return 11;
  };

  const totalPapers = tags.reduce((s, t) => s + t.count, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 搜索 */}
      <div style={{ padding: '6px 8px', borderBottom: '1px solid var(--hairline)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--bg-2)', borderRadius: 4, padding: '4px 8px' }}>
          <Search size={12} style={{ color: 'var(--mute)', flexShrink: 0 }} />
          <input
            type="text"
            placeholder="搜索标签..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--body)', fontSize: 11 }}
          />
          <button
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0 }}
            onClick={loadTags}
            title="刷新"
          >
            <RefreshCw size={10} />
          </button>
        </div>
      </div>

      {/* 标签云 */}
      <div style={{ flex: selectedTag ? undefined : 1, overflowY: 'auto', padding: '8px 12px' }}>
        {tags.length === 0 && !loading && (
          <div style={{ textAlign: 'center', color: 'var(--mute)', fontSize: 12, padding: 16 }}>
            暂无标签<br />
            <span style={{ fontSize: 10 }}>添加文献后标签会自动出现</span>
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center', justifyContent: 'center' }}>
          {filteredTags.map(tag => {
            const color = getTagColor(tag.name);
            const isSelected = selectedTag === tag.name;
            return (
              <span
                key={tag.name}
                className="acasight-tag-item"
                style={{
                  fontSize: getTagSize(tag.count),
                  cursor: 'pointer',
                  padding: '3px 8px',
                  borderRadius: 4,
                  background: isSelected ? color : `${color}18`,
                  color: isSelected ? '#fff' : color,
                  border: `1px solid ${isSelected ? color : 'transparent'}`,
                  transition: 'all 0.15s ease',
                }}
                onClick={() => handleTagClick(tag.name)}
              >
                #{tag.name}
                <span className="acasight-tag-count" style={{ marginLeft: 3, fontSize: 9 }}>{tag.count}</span>
              </span>
            );
          })}
        </div>
      </div>

      {/* 选中标签下的文献列表 */}
      {selectedTag && (
        <div style={{
          flex: 1,
          borderTop: '1px solid var(--hairline)',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--hairline)' }}>
            <span style={{ fontSize: 11, color: getTagColor(selectedTag), fontWeight: 600 }}>
              "#{selectedTag}" ({papersByTag.length})
            </span>
            <button
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0 }}
              onClick={() => { setSelectedTag(null); setPapersByTag([]); }}
            >
              <X size={12} />
            </button>
          </div>

          {papersLoading && (
            <div style={{ padding: 12, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}>
              加载中...
            </div>
          )}

          {!papersLoading && papersByTag.length === 0 && (
            <div style={{ padding: 12, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}>
              该标签下暂无文献
            </div>
          )}

          {!papersLoading && papersByTag.map(paper => (
            <div
              key={paper.id}
              className="acasight-tree-item"
              style={{ paddingLeft: 10, paddingRight: 8, display: 'flex', alignItems: 'center', gap: 6, minHeight: 32, cursor: 'pointer' }}
              onClick={() => handleOpenPaper(paper)}
            >
              <FileText size={12} style={{ color: paper.pdf_path ? 'var(--accent)' : 'var(--mute)', flexShrink: 0 }} />
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11, color: 'var(--body)' }}>
                {paper.title}
              </span>
              {paper.year && <span style={{ fontSize: 9, color: 'var(--mute)', flexShrink: 0 }}>{paper.year}</span>}
              {paper.is_favorite ? (
                <Star size={10} style={{ color: 'var(--warning, #f59e0b)', flexShrink: 0 }} fill="var(--warning, #f59e0b)" />
              ) : null}
            </div>
          ))}
        </div>
      )}

      {/* 底部统计 */}
      <div style={{ padding: '6px 12px', borderTop: '1px solid var(--hairline)', fontSize: 10, color: 'var(--mute)', textAlign: 'center' }}>
        {tags.length} 个标签 · {totalPapers} 篇文献
      </div>
    </div>
  );
};
