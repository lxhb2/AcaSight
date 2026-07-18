/**
 * TOCSidebar — 大纲/目录导航侧边栏
 *
 * 使用 PDF.js 内置的 getOutline() 提取文档大纲
 * 点击跳转到对应页码
 */

import React, { useState, useEffect } from 'react';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { ChevronRight, BookOpen } from 'lucide-react';

interface TOCItem {
  title: string;
  pageNumber: number;
  children: TOCItem[];
}

interface TOCSidebarProps {
  pdfDoc: PDFDocumentProxy | null;
  onPageClick: (page: number) => void;
}

async function extractTOC(pdfDoc: PDFDocumentProxy): Promise<TOCItem[]> {
  try {
    const outline = await pdfDoc.getOutline();
    if (!outline || outline.length === 0) return [];

    const mapItems = async (items: any[]): Promise<TOCItem[]> => {
      const result: TOCItem[] = [];
      for (const item of items) {
        let pageNumber = 1;
        try {
          if (item.dest) {
            const dest = typeof item.dest === 'string'
              ? await pdfDoc.getDestination(item.dest)
              : item.dest;
            if (dest) {
              const pageIndex = await pdfDoc.getPageIndex(dest[0]);
              pageNumber = pageIndex + 1;
            }
          }
        } catch { /* use default page 1 */ }

        result.push({
          title: item.title || `Page ${pageNumber}`,
          pageNumber,
          children: item.items ? await mapItems(item.items) : [],
        });
      }
      return result;
    };
    return mapItems(outline);
  } catch {
    return [];
  }
}

export const TOCSidebar: React.FC<TOCSidebarProps> = ({ pdfDoc, onPageClick }) => {
  const [toc, setToc] = useState<TOCItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [activePage, setActivePage] = useState(1);

  useEffect(() => {
    if (!pdfDoc) return;
    setLoading(true);
    extractTOC(pdfDoc).then(items => {
      setToc(items);
      setLoading(false);
    });
  }, [pdfDoc]);

  const toggleExpand = (title: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title);
      else next.add(title);
      return next;
    });
  };

  const handleClick = (item: TOCItem) => {
    setActivePage(item.pageNumber);
    onPageClick(item.pageNumber);
  };

  const renderItem = (item: TOCItem, depth: number = 0) => {
    const hasChildren = item.children.length > 0;
    const isExpanded = expanded.has(item.title);
    const isActive = item.pageNumber === activePage;

    return (
      <div key={`${item.title}-${item.pageNumber}`}>
        <div
          onClick={() => {
            if (hasChildren) toggleExpand(item.title);
            handleClick(item);
          }}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: `6px 12px 6px ${12 + depth * 16}px`,
            cursor: 'pointer', fontSize: 12, lineHeight: 1.5,
            color: isActive ? 'var(--accent, #6366f1)' : 'var(--body, #ccc)',
            background: isActive ? 'var(--accent-bg-soft, rgba(99,102,241,0.08))' : 'transparent',
            borderRadius: 4, margin: '1px 4px',
            transition: 'all 0.1s',
          }}
          onMouseEnter={(e) => {
            if (!isActive) e.currentTarget.style.background = 'var(--hover, rgba(255,255,255,0.05))';
          }}
          onMouseLeave={(e) => {
            if (!isActive) e.currentTarget.style.background = 'transparent';
          }}
        >
          {hasChildren && (
            <ChevronRight
              size={12}
              style={{
                transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.15s', flexShrink: 0,
              }}
            />
          )}
          <span style={{
            flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {item.title}
          </span>
          <span style={{ fontSize: 10, color: 'var(--mute, #666)', flexShrink: 0 }}>
            {item.pageNumber}
          </span>
        </div>
        {hasChildren && isExpanded && item.children.map(c => renderItem(c, depth + 1))}
      </div>
    );
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        padding: '10px 12px', fontSize: 12, fontWeight: 600,
        color: 'var(--mute, #888)', borderBottom: '1px solid var(--hairline, #333)',
        textTransform: 'uppercase', letterSpacing: 0.5,
      }}>
        目录 / 大纲
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 0' }}>
        {loading ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--mute, #888)', fontSize: 12 }}>
            解析目录中...
          </div>
        ) : toc.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--mute, #888)', fontSize: 12 }}>
            <BookOpen size={20} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
            <p>此 PDF 没有大纲/目录</p>
          </div>
        ) : (
          toc.map(item => renderItem(item))
        )}
      </div>
    </div>
  );
};

export default TOCSidebar;
