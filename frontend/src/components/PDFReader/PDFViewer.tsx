/**
 * PDFViewer — 学术 PDF 阅读器主组件
 *
 * 参考 Readest Reader.tsx + BabelDOC BilingualPDFViewer 架构:
 * - react-pdf 渲染 + 文本选择层
 * - 左侧: 缩略图/TOC 切换面板
 * - 中央: PDF 渲染区 + Annotator 覆盖层
 * - 右侧: 标注面板 / AI 对话 切换
 * - 顶部: 缩放控制工具栏
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/AnnotationLayer.css';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import type { PDFDocumentProxy } from 'pdfjs-dist';

import {
  BookOpen,
} from 'lucide-react';

import { Annotator, type HighlightPayload } from '@/components/PDFReader/Annotator';
import { AISidePanel } from '@/components/PDFReader/AISidePanel';
import { FloatingTranslate } from '@/components/PDFReader/FloatingTranslate';
import { PageThumbnails } from '@/components/PDFReader/PageThumbnails';
import { TOCSidebar } from '@/components/PDFReader/TOCSidebar';
import { AnnotationSidebar } from '@/components/PDFReader/AnnotationSidebar';
import { ReaderToolbar } from '@/components/PDFReader/ReaderToolbar';

// PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

// ==================== Types ====================

interface PDFViewerProps {
  /** PDF 文件 URL */
  url: string;
  /** PDF 文件路径（后端） */
  filePath?: string;
  /** PDF 标题 */
  title?: string;
  /** 关闭回调 */
  onClose?: () => void;
}

type LeftPanel = 'thumbnails' | 'toc' | 'none';
type RightPanel = 'annotations' | 'ai' | 'none';

interface HighlightAnnotation {
  id: string;
  text: string;
  pageNumber: number;
  color: string;
  rect?: { top: number; right: number; bottom: number; left: number };
  note?: string;
  createdAt: number;
}

// ==================== Component ====================

export const PDFViewer: React.FC<PDFViewerProps> = ({
  url,
  filePath,
  title = 'PDF 文献',
  onClose,
}) => {
  // PDF 文档
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.2);
  const [rotation, setRotation] = useState(0);
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);

  // 面板
  const [leftPanel, setLeftPanel] = useState<LeftPanel>('none');
  const [rightPanel, setRightPanel] = useState<RightPanel>('none');

  // 全文本（用于 AI 面板上下文）
  const [fullText, setFullText] = useState('');

  // 标注
  const [highlights, setHighlights] = useState<HighlightAnnotation[]>([]);
  const [selectedHighlight, setSelectedHighlight] = useState<string | null>(null);
  /** 触发 Annotator 进入"编辑已有标注"态的令牌 */
  const [editToken, setEditToken] = useState<HighlightAnnotation | null>(null);

  // 浮动翻译（保留接口，后续从 Annotator 触发）
  const [showTranslate, setShowTranslate] = useState(false);
  const translateTextRef = useRef('');

  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // PDF 加载
  const onDocumentLoadSuccess = useCallback((pdf: PDFDocumentProxy) => {
    setNumPages(pdf.numPages);
    setPdfDoc(pdf);
    setCurrentPage(1);
  }, []);

  // 提取全文本
  useEffect(() => {
    if (!pdfDoc) return;
    let cancelled = false;
    const extract = async () => {
      const parts: string[] = [];
      for (let i = 1; i <= Math.min(pdfDoc.numPages, 20); i++) {
        if (cancelled) break;
        try {
          const page = await pdfDoc.getPage(i);
          const content = await page.getTextContent();
          const text = content.items
            .map((item: any) => item.str)
            .join(' ')
            .replace(/\s+/g, ' ')
            .trim();
          if (text) parts.push(`[Page ${i}] ${text}`);
        } catch { /* skip */ }
      }
      if (!cancelled) setFullText(parts.join('\n\n'));
    };
    extract();
    return () => { cancelled = true; };
  }, [pdfDoc]);

  // 缩放
  const zoomIn = () => setScale(s => Math.min(s + 0.2, 3.0));
  const zoomOut = () => setScale(s => Math.max(s - 0.2, 0.4));
  const rotate = () => setRotation(r => (r + 90) % 360);

  // 翻页
  const goToPage = (n: number) => {
    const p = Math.max(1, Math.min(n, numPages));
    setCurrentPage(p);
    // 滚动到对应页
    const el = pageRefs.current.get(p);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // 标注保存/更新/删除
  const handleSaveAnnotation = useCallback((payload: HighlightPayload) => {
    setHighlights(prev => {
      if (payload.annotationId) {
        return prev.map(h =>
          h.id === payload.annotationId
            ? { ...h, text: payload.text, color: payload.color, note: payload.note, cfi: payload.cfi }
            : h,
        );
      }
      const hl: HighlightAnnotation = {
        id: `hl-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        text: payload.text,
        pageNumber: payload.page,
        color: payload.color,
        rect: payload.rect,
        note: payload.note,
        cfi: payload.cfi,
        createdAt: Date.now(),
      };
      return [...prev, hl];
    });
  }, []);

  const handleDeleteAnnotation = useCallback((id: string) => {
    setHighlights(prev => prev.filter(h => h.id !== id));
    setSelectedHighlight(prev => (prev === id ? null : prev));
  }, []);

  const handleUpdateNote = useCallback((id: string, note: string) => {
    setHighlights(prev =>
      prev.map(h => (h.id === id ? { ...h, note } : h)),
    );
  }, []);

  const findAnnotationByText = useCallback(
    (text: string, page: number) => {
      const hit = highlights.find(h => h.text === text && h.pageNumber === page);
      if (!hit) return undefined;
      return {
        text: hit.text,
        page: hit.pageNumber,
        color: hit.color,
        note: hit.note,
        cfi: hit.cfi,
        rect: hit.rect,
        annotationId: hit.id,
      };
    },
    [highlights],
  );

  const handleEditAnnotation = useCallback((id: string) => {
    const target = highlights.find(h => h.id === id);
    if (!target) return;
    setSelectedHighlight(id);
    setEditToken(target);
  }, [highlights]);

  // 清空 editToken（让 Annotator 离开编辑态）
  const handleAnnotatorDismiss = useCallback(() => {
    setEditToken(null);
  }, []);

  // 浮动翻译回调（在 Annotator 扩展中使用）
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleFullTranslate = useCallback(
    (_text: string, _x: number, _y: number) => {
      // 预留: 后续从 Annotator/TranslatorPopup 触发全尺寸翻译面板
    },
    [],
  );
  void handleFullTranslate;

  // 键盘快捷键
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowTranslate(false);
        setLeftPanel('none');
        setRightPanel('none');
      }
      if (e.ctrlKey || e.metaKey) return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'ArrowRight':
        case 'PageDown':
          e.preventDefault();
          goToPage(currentPage + 1);
          break;
        case 'ArrowLeft':
        case 'PageUp':
          e.preventDefault();
          goToPage(currentPage - 1);
          break;
        case 'Home':
          e.preventDefault();
          goToPage(1);
          break;
        case 'End':
          e.preventDefault();
          goToPage(numPages);
          break;
        case '+':
        case '=':
          zoomIn();
          break;
        case '-':
          zoomOut();
          break;
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [currentPage, numPages]);

  // 标注点击跳转
  const handleJumpToAnnotation = useCallback((pageNumber: number, id: string) => {
    setSelectedHighlight(id);
    goToPage(pageNumber);
  }, []);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      display: 'flex', flexDirection: 'column',
      background: 'var(--bg-primary, #0f0f11)',
      color: 'var(--body, #e0e0e0)',
    }}>
      {/* 顶部工具栏 */}
      <ReaderToolbar
        title={title}
        currentPage={currentPage}
        numPages={numPages}
        scale={scale}
        onPageChange={goToPage}
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onRotate={rotate}
        onClose={onClose}
        leftPanel={leftPanel}
        rightPanel={rightPanel}
        onToggleLeft={(p) => setLeftPanel(p === leftPanel ? 'none' : p)}
        onToggleRight={(p) => setRightPanel(p === rightPanel ? 'none' : p)}
        hasAnnotations={highlights.length > 0}
      />

      {/* 主体 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 左侧面板 */}
        {leftPanel !== 'none' && (
          <div style={{
            width: 220, minWidth: 220, borderRight: '1px solid var(--hairline, #333)',
            overflow: 'hidden', display: 'flex', flexDirection: 'column',
            background: 'var(--bg-secondary, #141416)',
          }}>
            {leftPanel === 'thumbnails' && (
              <PageThumbnails
                pdfDoc={pdfDoc}
                numPages={numPages}
                currentPage={currentPage}
                onPageClick={goToPage}
              />
            )}
            {leftPanel === 'toc' && (
              <TOCSidebar
                pdfDoc={pdfDoc}
                onPageClick={goToPage}
              />
            )}
          </div>
        )}

        {/* 中央 PDF 渲染区 */}
        <div
          ref={containerRef}
          style={{
            flex: 1, overflow: 'auto',
            background: 'var(--bg-secondary, #1a1a1e)',
            position: 'relative',
          }}
        >
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            padding: '16px 0',
          }}>
            <Document
              file={url}
              onLoadSuccess={onDocumentLoadSuccess}
              loading={
                <div style={{ padding: 40, color: 'var(--mute, #888)', textAlign: 'center' }}>
                  <BookOpen size={32} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                  <p>加载 PDF 中...</p>
                </div>
              }
              error={
                <div style={{ padding: 40, color: '#ef4444', textAlign: 'center' }}>
                  <p>PDF 加载失败，请检查文件路径</p>
                </div>
              }
            >
              {Array.from({ length: numPages }, (_, i) => {
                const pageNum = i + 1;
                return (
                  <div
                    key={`page-${pageNum}`}
                    ref={(el) => { if (el) pageRefs.current.set(pageNum, el); }}
                    style={{
                      marginBottom: 16,
                      boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                      position: 'relative',
                      background: '#fff',
                    }}
                    data-page-number={pageNum}
                  >
                    <Page
                      pageNumber={pageNum}
                      scale={scale}
                      rotate={rotation}
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                      loading={
                        <div style={{
                          width: 595 * scale,
                          height: 842 * scale,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          color: '#999',
                        }}>
                          加载第 {pageNum} 页...
                        </div>
                      }
                    />
                    {/* 页码标签 */}
                    <div style={{
                      position: 'absolute', bottom: 4, left: '50%', transform: 'translateX(-50%)',
                      fontSize: 10, color: '#999', background: 'rgba(0,0,0,0.5)',
                      padding: '2px 8px', borderRadius: 4, pointerEvents: 'none',
                    }}>
                      {pageNum}
                    </div>
                  </div>
                );
              })}
            </Document>
          </div>

          {/* Annotator 覆盖层 */}
          <Annotator
            containerRef={containerRef}
            onSaveAnnotation={handleSaveAnnotation}
            onDeleteAnnotation={handleDeleteAnnotation}
            findAnnotationByText={findAnnotationByText}
            editToken={
              editToken
                ? {
                    id: editToken.id,
                    text: editToken.text,
                    page: editToken.pageNumber,
                    note: editToken.note,
                    color: editToken.color,
                  }
                : null
            }
          />
        </div>

        {/* 右侧面板 */}
        {rightPanel !== 'none' && (
          <div style={{
            width: 360, minWidth: 360, borderLeft: '1px solid var(--hairline, #333)',
            overflow: 'hidden', display: 'flex', flexDirection: 'column',
            background: 'var(--bg-secondary, #141416)',
          }}>
            {rightPanel === 'annotations' && (
              <AnnotationSidebar
                highlights={highlights}
                onJumpTo={handleJumpToAnnotation}
                onDelete={(id) => handleDeleteAnnotation(id)}
                onEdit={handleEditAnnotation}
                onUpdateNote={handleUpdateNote}
                selectedId={selectedHighlight}
              />
            )}
            {rightPanel === 'ai' && (
              <AISidePanel
                pdfPath={filePath}
                pdfTitle={title}
                pdfFullText={fullText}
              />
            )}
          </div>
        )}
      </div>

      {/* 浮动翻译弹窗 */}
      {showTranslate && translateTextRef.current && (
        <FloatingTranslate
          text={translateTextRef.current}
          position={{ x: window.innerWidth / 2 - 200, y: 60 }}
          onClose={() => setShowTranslate(false)}
        />
      )}
    </div>
  );
};

export default PDFViewer;
