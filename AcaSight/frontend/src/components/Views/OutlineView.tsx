/**
 * OutlineView — 文档大纲面板（D.4）
 *
 * 从后端获取 PDF 目录（TOC），支持点击导航到对应页面。
 * 无目录时显示页面缩略图列表。
 * 玻璃浮雕 UI 适配。
 */

import React, { useMemo, useCallback } from 'react';
import { List, FileText } from 'lucide-react';
import { useApp } from '@/contexts/AppContext';

export const OutlineView: React.FC = () => {
  const { outline, currentPage, setCurrentPage, numPages } = useApp();

  const outlineItems = useMemo(() => {
    if (!outline || outline.length === 0) {
      const pages = [];
      for (let i = 1; i <= numPages; i++) {
        pages.push({ level: 1, title: `第 ${i} 页`, page: i });
      }
      return pages;
    }
    return outline;
  }, [outline, numPages]);

  const handleClick = useCallback((page: number) => {
    if (page >= 1 && page <= numPages) {
      setCurrentPage(page);
      const el = document.querySelector(`[data-page-number="${page}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }, [numPages, setCurrentPage]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        padding: '6px 10px',
        fontSize: 11,
        color: 'var(--mute)',
        borderBottom: '1px solid var(--hairline)',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}>
        <List size={12} />
        <span style={{ fontWeight: 600 }}>{outline.length > 0 ? '文档大纲' : '页面导航'}</span>
        <span style={{ marginLeft: 'auto', fontSize: 10 }}>
          {outline.length > 0 ? `${outline.length} 项` : `${numPages} 页`}
        </span>
      </div>

      {outlineItems.length === 0 ? (
        <div style={{
          padding: 20,
          textAlign: 'center',
          color: 'var(--mute)',
          fontSize: 12,
        }}>
          <FileText size={24} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
          打开 PDF 后显示大纲
        </div>
      ) : (
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
          {outlineItems.map((item, i) => {
            const isActive = item.page === currentPage;
            const indent = (item.level - 1) * 14;

            return (
              <div
                key={i}
                style={{
                  paddingLeft: `${10 + indent}px`,
                  paddingRight: 10,
                  paddingTop: 3,
                  paddingBottom: 3,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  background: isActive ? 'var(--accent-bg-soft)' : 'transparent',
                  borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                  transition: 'all 0.15s ease',
                }}
                onClick={() => handleClick(item.page)}
                onMouseEnter={e => {
                  if (!isActive) e.currentTarget.style.background = 'var(--accent-bg-soft)';
                }}
                onMouseLeave={e => {
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
              >
                {item.level === 1 && <span style={{ fontSize: 6, opacity: 0.6, color: 'var(--accent)' }}>●</span>}
                {item.level === 2 && <span style={{ fontSize: 5, opacity: 0.4, color: 'var(--accent)' }}>○</span>}
                {item.level >= 3 && <span style={{ fontSize: 4, opacity: 0.3, color: 'var(--accent)' }}>·</span>}
                <span style={{
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontWeight: item.level === 1 ? 600 : 400,
                  fontSize: item.level === 1 ? 12 : 11,
                  color: isActive ? 'var(--accent)' : 'var(--body)',
                }}>
                  {item.title}
                </span>
                <span style={{
                  fontSize: 9,
                  color: 'var(--mute)',
                  flexShrink: 0,
                }}>
                  {item.page}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
