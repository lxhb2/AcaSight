/**
 * ReaderToolbar — PDF 阅读器顶部工具栏
 *
 * 参考 Readest 的工具栏布局:
 * - 左侧: 菜单按钮 (缩略图/TOC) + 标题
 * - 中间: 页面导航 (上一页/页码/下一页)
 * - 右侧: 缩放/旋转/右侧面板切换/关闭
 */

import React, { useState, useCallback } from 'react';
import {
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw,
  Highlighter, MessageSquare,
  X, Image, List,
} from 'lucide-react';

interface ReaderToolbarProps {
  title: string;
  currentPage: number;
  numPages: number;
  scale: number;
  onPageChange: (page: number) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onRotate: () => void;
  onClose?: () => void;
  leftPanel: string;
  rightPanel: string;
  onToggleLeft: (panel: 'thumbnails' | 'toc') => void;
  onToggleRight: (panel: 'annotations' | 'ai') => void;
  hasAnnotations?: boolean;
}

const btnBase: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 32, height: 32, borderRadius: 6, border: 'none',
  background: 'transparent', color: 'var(--mute, #aaa)',
  cursor: 'pointer', transition: 'all 0.15s',
};

const btnActive: React.CSSProperties = {
  ...btnBase,
  color: 'var(--accent, #6366f1)',
  background: 'var(--accent-bg-soft, rgba(99,102,241,0.1))',
};

export const ReaderToolbar: React.FC<ReaderToolbarProps> = ({
  title, currentPage, numPages, scale,
  onPageChange, onZoomIn, onZoomOut, onRotate, onClose,
  leftPanel, rightPanel, onToggleLeft, onToggleRight,
  hasAnnotations,
}) => {
  const [pageInput, setPageInput] = useState('');

  const handlePageSubmit = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') {
        const n = parseInt(pageInput, 10);
        if (!isNaN(n) && n >= 1 && n <= numPages) {
          onPageChange(n);
          setPageInput('');
        }
      }
    },
    [pageInput, numPages, onPageChange],
  );

  return (
    <div style={{
      display: 'flex', alignItems: 'center', height: 44,
      padding: '0 12px', gap: 8,
      borderBottom: '1px solid var(--hairline, #333)',
      background: 'var(--bg-primary, #0f0f11)',
      userSelect: 'none', flexShrink: 0,
    }}>
      {/* 左侧 — 面板切换 + 标题 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        {/* 缩略图 */}
        <button
          style={leftPanel === 'thumbnails' ? btnActive : btnBase}
          onClick={() => onToggleLeft('thumbnails')}
          title="页面缩略图"
        >
          <Image size={16} />
        </button>
        {/* TOC */}
        <button
          style={leftPanel === 'toc' ? btnActive : btnBase}
          onClick={() => onToggleLeft('toc')}
          title="目录/大纲"
        >
          <List size={16} />
        </button>
      </div>

      {/* 标题 */}
      <div style={{
        flex: 1, fontSize: 13, fontWeight: 500,
        color: 'var(--body, #ddd)', overflow: 'hidden',
        textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        padding: '0 8px',
      }}>
        {title}
      </div>

      {/* 中间 — 页面导航 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <button style={btnBase} onClick={() => onPageChange(currentPage - 1)} disabled={currentPage <= 1} title="上一页">
          <ChevronLeft size={16} />
        </button>
        <input
          value={pageInput || currentPage}
          onChange={(e) => setPageInput(e.target.value)}
          onKeyDown={handlePageSubmit}
          onBlur={() => setPageInput('')}
          style={{
            width: 40, height: 26, textAlign: 'center',
            fontSize: 12, fontWeight: 600, borderRadius: 4,
            border: '1px solid var(--hairline, #333)',
            background: 'var(--bg-secondary, #1a1a1e)',
            color: 'var(--body, #ddd)',
            outline: 'none',
          }}
        />
        <span style={{ fontSize: 11, color: 'var(--mute, #888)', minWidth: 30, textAlign: 'center' }}>
          / {numPages}
        </span>
        <button style={btnBase} onClick={() => onPageChange(currentPage + 1)} disabled={currentPage >= numPages} title="下一页">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* 缩放 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <button style={btnBase} onClick={onZoomOut} disabled={scale <= 0.4} title="缩小">
          <ZoomOut size={16} />
        </button>
        <span style={{ fontSize: 11, color: 'var(--mute, #888)', minWidth: 36, textAlign: 'center' }}>
          {Math.round(scale * 100)}%
        </span>
        <button style={btnBase} onClick={onZoomIn} disabled={scale >= 3.0} title="放大">
          <ZoomIn size={16} />
        </button>
        <button style={btnBase} onClick={onRotate} title="旋转">
          <RotateCw size={16} />
        </button>
      </div>

      {/* 分隔线 */}
      <div style={{ width: 1, height: 20, background: 'var(--hairline, #333)' }} />

      {/* 右侧面板切换 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <button
          style={rightPanel === 'annotations' ? btnActive : btnBase}
          onClick={() => onToggleRight('annotations')}
          title={`标注列表${hasAnnotations ? ` (${hasAnnotations ? '有' : '无'}标注)` : ''}`}
        >
          <Highlighter size={16} />
        </button>
        <button
          style={rightPanel === 'ai' ? btnActive : btnBase}
          onClick={() => onToggleRight('ai')}
          title="AI 助手"
        >
          <MessageSquare size={16} />
        </button>
      </div>

      {/* 关闭 */}
      {onClose && (
        <button
          style={{ ...btnBase, color: 'var(--mute, #aaa)' }}
          onClick={onClose}
          title="关闭 (Esc)"
        >
          <X size={18} />
        </button>
      )}
    </div>
  );
};

export default ReaderToolbar;
