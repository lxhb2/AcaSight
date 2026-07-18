/**
 * PageThumbnails — 页面缩略图侧边栏
 *
 * 参考 Readest 的缩略图导航:
 * - 使用 react-pdf Page 组件渲染缩略图
 * - 点击跳转到对应页
 * - 高亮当前页
 */

import React, { useRef, useEffect } from 'react';
import { Page } from 'react-pdf';
import type { PDFDocumentProxy } from 'pdfjs-dist';

interface PageThumbnailsProps {
  pdfDoc: PDFDocumentProxy | null;
  numPages: number;
  currentPage: number;
  onPageClick: (page: number) => void;
}

const THUMB_WIDTH = 180;

export const PageThumbnails: React.FC<PageThumbnailsProps> = ({
  pdfDoc: _pdfDoc, numPages, currentPage, onPageClick,
}) => {
  const listRef = useRef<HTMLDivElement>(null);

  // 自动滚动到当前页
  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-thumb-page="${currentPage}"]`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [currentPage]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px', fontSize: 12, fontWeight: 600,
        color: 'var(--mute, #888)', borderBottom: '1px solid var(--hairline, #333)',
        textTransform: 'uppercase', letterSpacing: 0.5,
      }}>
        页面缩略图
      </div>

      {/* Thumbnails list */}
      <div ref={listRef} style={{
        flex: 1, overflow: 'auto', padding: '8px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
      }}>
        {Array.from({ length: numPages }, (_, i) => {
          const pageNum = i + 1;
          const isActive = pageNum === currentPage;
          return (
            <div
              key={pageNum}
              data-thumb-page={pageNum}
              onClick={() => onPageClick(pageNum)}
              style={{
                cursor: 'pointer',
                border: isActive
                  ? '2px solid var(--accent, #6366f1)'
                  : '2px solid transparent',
                borderRadius: 4,
                overflow: 'hidden',
                transition: 'border-color 0.15s',
                background: '#fff',
                boxShadow: isActive
                  ? '0 2px 12px rgba(99,102,241,0.3)'
                  : '0 1px 4px rgba(0,0,0,0.2)',
                position: 'relative',
              }}
            >
              <Page
                pageNumber={pageNum}
                width={THUMB_WIDTH}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                loading={
                  <div style={{
                    width: THUMB_WIDTH, height: THUMB_WIDTH * 1.414,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: '#f0f0f0', color: '#999', fontSize: 12,
                  }}>
                    {pageNum}
                  </div>
                }
              />
              {/* Page number overlay */}
              <div style={{
                position: 'absolute', bottom: 2, right: 4,
                fontSize: 10, color: '#fff', background: 'rgba(0,0,0,0.6)',
                padding: '1px 6px', borderRadius: 3, fontWeight: 600,
              }}>
                {pageNum}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PageThumbnails;
