/**
 * BilingualReader — 双语对照阅读器 v4.0
 *
 * 借鉴 BabelDOC 的双语对照理念 + STranslate 的内嵌翻译：
 * - 模式1: 并排对照 — 左原文右译文，逐页实时翻译
 * - 模式2: 全文翻译 — BabelDOC 生成 dual.pdf（保留布局）
 * - 模式3: 段落对照 — 原文段落+译文段落穿插显示
 *
 * 翻译引擎：内嵌 STranslate 风格（Google→MS→MyMemory→AI）
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import {
  X, Columns, BookOpen, Loader2, Languages,
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut,
  Play, CheckCircle2,
} from 'lucide-react';
import { translateApi, babeldocApi } from '@/services/api';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url
).toString();

// ==================== Types ====================

type ViewMode = 'side-by-side' | 'paragraph' | 'full-translate';

interface PageTranslation {
  pageNum: number;
  original: string;
  translated: string;
  loading: boolean;
  error?: string;
}

interface BilingualReaderProps {
  pdfPath: string;
  proxyUrl: string;
  numPages: number;
  title?: string;
  onClose: () => void;
}

// ==================== Helpers ====================

async function extractPageText(page: any): Promise<string> {
  try {
    const content = await page.getTextContent();
    return content.items
      .map((item: any) => item.str)
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();
  } catch { return ''; }
}

function splitParagraphs(text: string): string[] {
  // 按双换行分割段落
  return text
    .split(/\n\s*\n/)
    .map(p => p.trim())
    .filter(p => p.length > 20);
}

// ==================== Component ====================

export const BilingualReader: React.FC<BilingualReaderProps> = ({
  pdfPath, proxyUrl, numPages, title = '双语对照', onClose,
}) => {
  // View
  const [viewMode, setViewMode] = useState<ViewMode>('side-by-side');
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);

  // Translation cache: pageNum → translation
  const [translations, setTranslations] = useState<Map<number, PageTranslation>>(new Map());
  const [isTranslatingAll, setIsTranslatingAll] = useState(false);
  const [translateProgress, setTranslateProgress] = useState({ done: 0, total: 0 });

  // Paragraph mode state
  const [paragraphs, setParagraphs] = useState<Array<{original: string; translated: string; loading: boolean}>>([]);

  // BabelDOC mode
  const [babeldocTask, setBabeldocTask] = useState<any>(null);
  const [dualPdfUrl, setDualPdfUrl] = useState<string | null>(null);
  const [babeldocAvailable, setBabeldocAvailable] = useState(false);

  // PDF document
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);

  // Scroll sync
  const leftRef = useRef<HTMLDivElement>(null);
  const rightRef = useRef<HTMLDivElement>(null);
  const syncing = useRef(false);

  // Check BabelDOC
  useEffect(() => {
    babeldocApi.status().then(r => {
      if (r?.data?.available) setBabeldocAvailable(true);
    }).catch(() => {});
  }, []);

  // ==================== Translate single page ====================

  const translatePage = useCallback(async (pageNum: number, doc: PDFDocumentProxy) => {
    const existing = translations.get(pageNum);
    if (existing?.translated || existing?.loading) return existing;

    // Mark as loading
    setTranslations(prev => {
      const next = new Map(prev);
      next.set(pageNum, { pageNum, original: '', translated: '', loading: true });
      return next;
    });

    try {
      const page = await doc.getPage(pageNum);
      const text = await extractPageText(page);

      if (!text || text.length < 5) {
        setTranslations(prev => {
          const next = new Map(prev);
          next.set(pageNum, { pageNum, original: text, translated: '(本页无文本内容)', loading: false });
          return next;
        });
        return;
      }

      const res = await translateApi.long({ text, source_lang: 'auto', target_lang: 'zh' });
      const translated = res.data?.translation || text;

      setTranslations(prev => {
        const next = new Map(prev);
        next.set(pageNum, { pageNum, original: text, translated, loading: false });
        return next;
      });
    } catch (err: any) {
      setTranslations(prev => {
        const next = new Map(prev);
        next.set(pageNum, { pageNum, original: '', translated: '', loading: false, error: err?.message });
        return next;
      });
    }
  }, [translations]);

  // ==================== Translate all pages ====================

  const translateAllPages = useCallback(async () => {
    if (!pdfDoc || isTranslatingAll) return;
    setIsTranslatingAll(true);
    setTranslateProgress({ done: 0, total: numPages });

    for (let i = 1; i <= numPages; i++) {
      await translatePage(i, pdfDoc);
      setTranslateProgress({ done: i, total: numPages });
    }
    setIsTranslatingAll(false);
  }, [pdfDoc, numPages, isTranslatingAll, translatePage]);

  // ==================== Paragraph Mode ====================

  const loadParagraphs = useCallback(async () => {
    if (!pdfDoc) return;
    setParagraphs([]);
    const page = await pdfDoc.getPage(currentPage);
    const text = await extractPageText(page);
    const paras = splitParagraphs(text);

    setParagraphs(paras.map(p => ({ original: p, translated: '', loading: true })));

    // Translate paragraphs sequentially
    for (let i = 0; i < paras.length; i++) {
      try {
        const res = await translateApi.text({ text: paras[i], source_lang: 'auto', target_lang: 'zh' });
        setParagraphs(prev => {
          const next = [...prev];
          next[i] = { ...next[i], translated: res.data?.translation || '', loading: false };
          return next;
        });
      } catch {
        setParagraphs(prev => {
          const next = [...prev];
          next[i] = { ...next[i], loading: false, translated: '(翻译失败)' };
          return next;
        });
      }
    }
  }, [pdfDoc, currentPage]);

  useEffect(() => {
    if (viewMode === 'paragraph') loadParagraphs();
  }, [viewMode, currentPage, loadParagraphs]);

  // ==================== BabelDOC full translation ====================

  const startBabelDOC = useCallback(async () => {
    try {
      const res = await babeldocApi.translate({
        pdf_path: pdfPath,
        lang_in: 'en', lang_out: 'zh',
        no_dual: false, no_mono: true,
        use_alternating_pages_dual: true,
      });
      const taskId = res.data.task_id;
      setBabeldocTask({ task_id: taskId, status: 'pending', progress: 0 });

      const poll = setInterval(async () => {
        try {
          const status = await babeldocApi.taskStatus(taskId);
          setBabeldocTask(status.data);
          if (['completed', 'failed', 'cancelled'].includes(status.data.status)) {
            clearInterval(poll);
            if (status.data.status === 'completed') {
              setDualPdfUrl(`/api/translate/babeldoc/result/${taskId}/dual`);
            }
          }
        } catch { clearInterval(poll); }
      }, 2000);

      return () => clearInterval(poll);
    } catch (err) {
      setBabeldocTask({ status: 'failed', error: String(err) });
    }
  }, [pdfPath]);

  // ==================== Scroll Sync ====================

  const syncScroll = (source: 'left' | 'right') => {
    if (syncing.current) return;
    syncing.current = true;
    const src = source === 'left' ? leftRef.current : rightRef.current;
    const dst = source === 'left' ? rightRef.current : leftRef.current;
    if (src && dst) {
      const ratio = src.scrollTop / (src.scrollHeight - src.clientHeight || 1);
      dst.scrollTop = ratio * (dst.scrollHeight - dst.clientHeight);
    }
    requestAnimationFrame(() => { syncing.current = false; });
  };

  // ==================== Keyboard ====================

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === 'ArrowRight') setCurrentPage(p => Math.min(numPages, p + 1));
      if (e.key === 'ArrowLeft') setCurrentPage(p => Math.max(1, p - 1));
    };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [numPages, onClose]);

  // ==================== Current page translation ====================

  const currentTr = translations.get(currentPage);

  // ==================== Render ====================

  const iconBtn: React.CSSProperties = {
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    width: 28, height: 28, borderRadius: 6, border: 'none',
    background: 'transparent', color: 'var(--mute, #888)', cursor: 'pointer',
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'var(--bg-primary, #0f0f11)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* ===== Toolbar ===== */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', borderBottom: '1px solid var(--hairline, #333)',
        background: 'var(--glass-bg)', flexShrink: 0, height: 40,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Languages size={14} style={{ color: 'var(--accent, #6366f1)' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink, #ddd)' }}>{title}</span>
          {/* Mode switches */}
          <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', border: '1px solid var(--hairline, #333)', marginLeft: 8 }}>
            {[
              { v: 'side-by-side' as ViewMode, icon: <Columns size={11} />, label: '并排' },
              { v: 'paragraph' as ViewMode, icon: <BookOpen size={11} />, label: '段落' },
            ].map(m => (
              <button key={m.v} onClick={() => setViewMode(m.v)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 2, padding: '3px 8px',
                  fontSize: 10, border: 'none', cursor: 'pointer',
                  background: viewMode === m.v ? 'var(--accent, #6366f1)' : 'transparent',
                  color: viewMode === m.v ? '#fff' : 'var(--mute)',
                }}>
                {m.icon}{m.label}
              </button>
            ))}
          </div>
          {/* Translate All / BabelDOC */}
          {viewMode === 'side-by-side' && (
            <button onClick={translateAllPages} disabled={isTranslatingAll}
              style={{
                display: 'flex', alignItems: 'center', gap: 3, padding: '3px 8px',
                fontSize: 10, borderRadius: 6, border: 'none', cursor: isTranslatingAll ? 'not-allowed' : 'pointer',
                background: 'var(--accent-bg-soft, rgba(99,102,241,0.08))', color: 'var(--accent, #6366f1)',
                opacity: isTranslatingAll ? 0.6 : 1,
              }}>
              {isTranslatingAll ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
              {isTranslatingAll ? `${translateProgress.done}/${translateProgress.total}` : '翻译全部'}
            </button>
          )}
          {babeldocAvailable && !dualPdfUrl && (
            <button onClick={startBabelDOC} disabled={babeldocTask?.status === 'running'}
              style={{
                display: 'flex', alignItems: 'center', gap: 3, padding: '3px 8px',
                fontSize: 10, borderRadius: 6, border: '1px solid var(--hairline, #333)',
                background: 'transparent', color: 'var(--mute)', cursor: 'pointer',
              }}>
              <BookOpen size={11} /> BabelDOC 全文
            </button>
          )}
          {dualPdfUrl && (
            <span style={{ fontSize: 10, color: '#10b981', display: 'flex', alignItems: 'center', gap: 2 }}>
              <CheckCircle2 size={11} /> 译文就绪
            </span>
          )}
        </div>
        {/* Right controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} style={iconBtn}><ZoomOut size={14} /></button>
          <span style={{ fontSize: 10, color: 'var(--mute)', minWidth: 32, textAlign: 'center' }}>{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(2, s + 0.1))} style={iconBtn}><ZoomIn size={14} /></button>
          <button onClick={onClose} style={iconBtn}><X size={16} /></button>
        </div>
      </div>

      {/* ===== BabelDOC Progress ===== */}
      {babeldocTask && ['pending', 'running'].includes(babeldocTask.status) && (
        <div style={{ padding: '3px 12px', background: 'var(--accent-bg-soft)', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />
          <div style={{ flex: 1, height: 3, background: 'var(--hairline)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', background: 'var(--accent)', borderRadius: 2, width: `${babeldocTask.progress || 0}%`, transition: 'width 0.3s' }} />
          </div>
          <span style={{ fontSize: 10, color: 'var(--mute)' }}>{babeldocTask.stage || '翻译中...'}</span>
        </div>
      )}

      {/* ===== Page Navigation ===== */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12,
        padding: '4px 0', borderBottom: '1px solid var(--hairline)', flexShrink: 0,
      }}>
        <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} style={iconBtn} disabled={currentPage <= 1}>
          <ChevronLeft size={16} />
        </button>
        <span style={{ fontSize: 12, color: 'var(--ink)', fontWeight: 600, minWidth: 60, textAlign: 'center' }}>
          {currentPage} / {numPages}
        </span>
        <button onClick={() => setCurrentPage(p => Math.min(numPages, p + 1))} style={iconBtn} disabled={currentPage >= numPages}>
          <ChevronRight size={16} />
        </button>
      </div>

      {/* ===== Side-by-Side Mode ===== */}
      {viewMode === 'side-by-side' && (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Original */}
          <div ref={leftRef} onScroll={() => syncScroll('left')}
            style={{ flex: 1, overflow: 'auto', borderRight: '1px solid var(--hairline, #333)', padding: '12px' }}>
            <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              📄 原文 · 第 {currentPage} 页
            </div>
            <Document file={proxyUrl} onLoadSuccess={setPdfDoc} loading={null}>
              <Page pageNumber={currentPage} scale={scale} renderTextLayer={true} renderAnnotationLayer={false}
                loading={<div style={{ color: 'var(--mute)', fontSize: 11 }}>加载中...</div>} />
            </Document>
          </div>
          {/* Translation */}
          <div ref={rightRef} onScroll={() => syncScroll('right')}
            style={{ flex: 1, overflow: 'auto', padding: '12px', background: 'var(--bg-secondary, #141416)' }}>
            <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              🌐 译文 · 第 {currentPage} 页
            </div>
            {!currentTr || currentTr.loading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: 20, color: 'var(--mute)', fontSize: 12 }}>
                <Loader2 size={14} className="animate-spin" />
                {currentTr ? '翻译中...' : '点击上方"翻译全部"或等待自动翻译'}
              </div>
            ) : currentTr.error ? (
              <div style={{ padding: 20, color: '#ef4444', fontSize: 12 }}>翻译失败: {currentTr.error}</div>
            ) : (
              <div style={{
                fontSize: 13, color: 'var(--ink, #ddd)', lineHeight: 1.8,
                whiteSpace: 'pre-wrap', padding: '12px',
                background: 'var(--bg-primary, #0f0f11)', borderRadius: 8,
                border: '1px solid var(--hairline, #222)',
              }}>
                {currentTr.translated}
              </div>
            )}
            {/* Original text reference */}
            {currentTr?.original && (
              <details style={{ marginTop: 12 }}>
                <summary style={{ fontSize: 10, color: 'var(--mute)', cursor: 'pointer' }}>原文文本</summary>
                <div style={{ fontSize: 11, color: 'var(--mute)', whiteSpace: 'pre-wrap', marginTop: 4, opacity: 0.7 }}>
                  {currentTr.original}
                </div>
              </details>
            )}
          </div>
        </div>
      )}

      {/* ===== Paragraph Mode ===== */}
      {viewMode === 'paragraph' && (
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
          <Document file={proxyUrl} loading={null}>
            <Page pageNumber={currentPage} scale={0.6} renderTextLayer={false} renderAnnotationLayer={false}
              loading={null} />
          </Document>
          <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {paragraphs.map((p, i) => (
              <div key={i} style={{
                border: '1px solid var(--hairline, #333)', borderRadius: 8, overflow: 'hidden',
              }}>
                <div style={{
                  padding: '8px 12px', fontSize: 11, color: 'var(--mute)', background: 'var(--bg-secondary)',
                  borderBottom: '1px solid var(--hairline, #222)', display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <BookOpen size={10} /> 原文
                </div>
                <div style={{ padding: '8px 12px', fontSize: 12, color: 'var(--ink)', lineHeight: 1.6 }}>
                  {p.original}
                </div>
                <div style={{
                  padding: '6px 12px', fontSize: 10, color: 'var(--mute)', background: 'var(--accent-bg-soft)',
                  borderTop: '1px solid var(--hairline)', borderBottom: '1px solid var(--hairline)',
                  display: 'flex', alignItems: 'center', gap: 4,
                }}>
                  <Languages size={10} /> 译文{p.loading && <Loader2 size={10} className="animate-spin" />}
                </div>
                <div style={{ padding: '8px 12px', fontSize: 13, color: 'var(--ink)', lineHeight: 1.8 }}>
                  {p.loading ? '翻译中...' : p.translated || '(翻译失败)'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default BilingualReader;
