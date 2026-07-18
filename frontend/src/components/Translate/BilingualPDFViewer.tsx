/**
 * BilingualPDFViewer — 双语 PDF 对照阅读器 v3.1
 *
 * 借鉴 BabelDOC 的双语 PDF 生成流程，提供：
 * - 并排对照模式：原文 + 译文同步滚动
 * - 交替页模式：BabelDOC 生成的 dual.pdf（原文/译文交替页）
 * - 文本选择：选中文字可翻译（renderTextLayer 启用）
 * - 同步滚动：左右面板联动
 * - 翻译进度：实时显示翻译阶段和进度
 * - 一键翻译：从阅读器内启动 BabelDOC 全文翻译
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page } from 'react-pdf';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import {
  X, Columns, BookOpen, Loader2, Languages,
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw,
  Play, AlertCircle, CheckCircle2,
} from 'lucide-react';
import { babeldocApi } from '@/services/api';
import type { BabelDOCTaskStatus } from '@/services/api';

// ==================== Types ====================

type ViewMode = 'side-by-side' | 'alternating' | 'overlay';

interface BilingualPDFViewerProps {
  /** 原始 PDF 文件路径（后端） */
  pdfPath: string;
  /** 原始 PDF 的代理 URL */
  proxyUrl: string;
  /** 总页数 */
  numPages: number;
  /** 关闭回调 */
  onClose: () => void;
}

// ==================== Helpers ====================

/** 从 URL 中提取原始 PDF 文件路径 */
function extractOriginalPath(url: string): string {
  try {
    const u = new URL(url, window.location.origin);
    const pathParam = u.searchParams.get('path');
    if (pathParam) return pathParam;
    const urlParam = u.searchParams.get('url');
    if (urlParam) return decodeURIComponent(urlParam);
  } catch { /* ignore */ }
  return url;
}

// ==================== Component ====================

export const BilingualPDFViewer: React.FC<BilingualPDFViewerProps> = ({
  pdfPath: _pdfPath,
  proxyUrl,
  numPages,
  onClose,
}) => {
  // View
  const [viewMode, setViewMode] = useState<ViewMode>('side-by-side');
  const [leftPage, setLeftPage] = useState(1);
  const [rightPage, setRightPage] = useState(2);
  const [scale, setScale] = useState(1.0);

  // Scroll sync
  const leftScrollRef = useRef<HTMLDivElement>(null);
  const rightScrollRef = useRef<HTMLDivElement>(null);
  const isSyncing = useRef(false);

  // Translation
  const [translationTask, setTranslationTask] = useState<BabelDOCTaskStatus | null>(null);
  const [translatedDualPdf, setTranslatedDualPdf] = useState<string | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>();

  // Check BabelDOC availability
  const [babeldocAvailable, setBabeldocAvailable] = useState(false);
  useEffect(() => {
    babeldocApi.status().then(r => {
      if (r?.data?.available) setBabeldocAvailable(true);
    }).catch(() => {});
  }, []);

  // ==================== Sync Scroll ====================

  const handleLeftScroll = useCallback(() => {
    if (isSyncing.current || !rightScrollRef.current || !leftScrollRef.current) return;
    isSyncing.current = true;
    const left = leftScrollRef.current;
    const right = rightScrollRef.current;
    const ratio = left.scrollTop / (left.scrollHeight - left.clientHeight || 1);
    right.scrollTop = ratio * (right.scrollHeight - right.clientHeight);
    requestAnimationFrame(() => { isSyncing.current = false; });
  }, []);

  const handleRightScroll = useCallback(() => {
    if (isSyncing.current || !leftScrollRef.current || !rightScrollRef.current) return;
    isSyncing.current = true;
    const left = leftScrollRef.current;
    const right = rightScrollRef.current;
    const ratio = right.scrollTop / (right.scrollHeight - right.clientHeight || 1);
    left.scrollTop = ratio * (left.scrollHeight - left.clientHeight);
    requestAnimationFrame(() => { isSyncing.current = false; });
  }, []);

  // ==================== Translation ====================

  const startTranslation = useCallback(async () => {
    if (!babeldocAvailable || isTranslating) return;

    const originalPath = extractOriginalPath(proxyUrl);
    setIsTranslating(true);

    try {
      const res = await babeldocApi.translate({
        pdf_path: originalPath,
        lang_in: 'en',
        lang_out: 'zh',
        no_dual: false,
        no_mono: true,
        use_alternating_pages_dual: true,
      });

      const taskId = res.data.task_id;
      setTranslationTask({ task_id: taskId, status: 'pending', progress: 0, stage: '初始化', created_at: Date.now(), completed_at: null, error: null, result: null });

      // Poll status
      pollRef.current = setInterval(async () => {
        try {
          const status = await babeldocApi.taskStatus(taskId);
          setTranslationTask(status.data);
          if (['completed', 'failed', 'cancelled'].includes(status.data.status)) {
            clearInterval(pollRef.current!);
            setIsTranslating(false);
            if (status.data.status === 'completed' && status.data.result) {
              const dual = status.data.result.dual_pdf;
              if (dual) setTranslatedDualPdf(dual);
            }
          }
        } catch {
          clearInterval(pollRef.current!);
          setIsTranslating(false);
        }
      }, 2000);
    } catch (err) {
      setIsTranslating(false);
      setTranslationTask(t => t ? { ...t, status: 'failed', error: String(err) } : null);
    }
  }, [babeldocAvailable, isTranslating, proxyUrl]);

  // Cleanup poll on unmount
  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  // ==================== Page Navigation ====================

  const goToPrevPair = () => {
    if (viewMode === 'side-by-side') {
      setLeftPage(p => Math.max(1, p - 2));
      setRightPage(p => Math.max(3, p - 2));
    } else {
      setLeftPage(p => Math.max(1, p - 2));
    }
  };

  const goToNextPair = () => {
    if (viewMode === 'side-by-side') {
      setLeftPage(p => Math.min(numPages - 1, p + 2));
      setRightPage(p => Math.min(numPages, p + 2));
    } else {
      setLeftPage(p => Math.min(numPages - 1, p + 2));
    }
  };

  // ==================== Dual PDF URL ====================

  const dualUrl = translatedDualPdf
    ? `/api/translate/babeldoc/result/${translationTask?.task_id}/dual`
    : null;

  const originalUrl = proxyUrl;

  // ==================== Render ====================

  const commonPageProps = {
    scale,
    renderTextLayer: true,
    renderAnnotationLayer: false,
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'var(--bg-primary, #14141e)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* ===== Top Bar ===== */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', borderBottom: '1px solid var(--hairline, #333)',
        background: 'var(--glass-bg)', backdropFilter: 'blur(12px)',
        minHeight: 40, flexShrink: 0,
      }}>
        {/* Left: title + mode */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>
            双语对照
          </span>
          <div style={{ display: 'flex', borderRadius: 6, overflow: 'hidden', border: '1px solid var(--hairline, #333)' }}>
            {([
              { value: 'side-by-side' as ViewMode, icon: <Columns size={12} />, label: '并排' },
              { value: 'alternating' as ViewMode, icon: <BookOpen size={12} />, label: '交替' },
            ]).map(m => (
              <button
                key={m.value}
                onClick={() => {
                  setViewMode(m.value);
                  setLeftPage(1);
                  setRightPage(2);
                }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 3,
                  padding: '3px 8px', fontSize: 10, border: 'none',
                  background: viewMode === m.value ? 'var(--accent, #6366f1)' : 'transparent',
                  color: viewMode === m.value ? '#fff' : 'var(--mute)',
                  cursor: 'pointer', transition: 'all 0.15s',
                }}
              >
                {m.icon} {m.label}
              </button>
            ))}
          </div>
          {/* Translation button */}
          {babeldocAvailable && !dualUrl && (
            <button
              onClick={startTranslation}
              disabled={isTranslating}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '3px 10px', fontSize: 10, border: 'none',
                borderRadius: 6, cursor: isTranslating ? 'not-allowed' : 'pointer',
                background: 'var(--accent, #6366f1)', color: '#fff',
                opacity: isTranslating ? 0.7 : 1,
              }}
            >
              {isTranslating ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              {isTranslating ? '翻译中...' : '全文翻译'}
            </button>
          )}
          {dualUrl && (
            <span style={{ fontSize: 10, color: '#10b981', display: 'flex', alignItems: 'center', gap: 3 }}>
              <CheckCircle2 size={12} /> 翻译完成
            </span>
          )}
        </div>

        {/* Right: zoom + close */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} style={iconBtnStyle}><ZoomOut size={14} /></button>
          <span style={{ fontSize: 11, minWidth: 36, textAlign: 'center', color: 'var(--mute)' }}>{Math.round(scale * 100)}%</span>
          <button onClick={() => setScale(s => Math.min(2, s + 0.1))} style={iconBtnStyle}><ZoomIn size={14} /></button>
          <div style={{ width: 1, height: 16, background: 'var(--hairline)', margin: '0 4px' }} />
          <button onClick={onClose} style={iconBtnStyle} title="关闭 (Esc)"><X size={16} /></button>
        </div>
      </div>

      {/* ===== Translation Progress Bar ===== */}
      {translationTask && ['pending', 'running'].includes(translationTask.status) && (
        <div style={{
          padding: '4px 12px', background: 'var(--accent-bg-soft, rgba(99,102,241,0.06))',
          borderBottom: '1px solid var(--hairline, #333)', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Loader2 size={12} className="animate-spin" style={{ color: 'var(--accent)' }} />
          <div style={{ flex: 1, height: 4, background: 'var(--hairline)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{
              height: '100%', background: 'var(--accent, #6366f1)', borderRadius: 2,
              width: `${translationTask.progress}%`, transition: 'width 0.3s',
            }} />
          </div>
          <span style={{ fontSize: 10, color: 'var(--mute)', minWidth: 80, textAlign: 'right' }}>
            {translationTask.stage} ({Math.round(translationTask.progress)}%)
          </span>
        </div>
      )}

      {/* ===== Translation Error ===== */}
      {translationTask?.status === 'failed' && (
        <div style={{
          padding: '6px 12px', background: 'rgba(239,68,68,0.1)',
          borderBottom: '1px solid rgba(239,68,68,0.2)', display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <AlertCircle size={14} style={{ color: '#ef4444' }} />
          <span style={{ fontSize: 11, color: '#ef4444', flex: 1 }}>翻译失败: {translationTask.error}</span>
          <button onClick={() => { setTranslationTask(null); setTranslatedDualPdf(null); }} style={{ ...iconBtnStyle, color: 'var(--mute)' }}>
            <RotateCw size={12} />
          </button>
        </div>
      )}

      {/* ===== Main Content ===== */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {viewMode === 'side-by-side' ? (
          <>
            {/* Left panel: Original */}
            <div
              ref={leftScrollRef}
              onScroll={handleLeftScroll}
              style={{
                flex: 1, overflow: 'auto', borderRight: '1px solid var(--hairline, #333)',
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                padding: '12px 0',
              }}
            >
              <div style={{
                fontSize: 10, color: 'var(--mute)', padding: '4px 8px',
                textAlign: 'center', position: 'sticky', top: 0, zIndex: 1,
                background: 'var(--bg-primary, #14141e)',
              }}>
                原文 (第 {leftPage} 页)
              </div>
              <Document file={originalUrl} loading={<Loader2 size={24} className="animate-spin" style={{ margin: 40 }} />}>
                <Page pageNumber={leftPage} {...commonPageProps} />
              </Document>
            </div>

            {/* Right panel: Translated */}
            <div
              ref={rightScrollRef}
              onScroll={handleRightScroll}
              style={{
                flex: 1, overflow: 'auto',
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                padding: '12px 0',
              }}
            >
              {dualUrl ? (
                <>
                  <div style={{
                    fontSize: 10, color: 'var(--mute)', padding: '4px 8px',
                    textAlign: 'center', position: 'sticky', top: 0, zIndex: 1,
                    background: 'var(--bg-primary, #14141e)',
                  }}>
                    译文 (第 {rightPage} 页)
                  </div>
                  <Document file={dualUrl} loading={<Loader2 size={24} className="animate-spin" style={{ margin: 40 }} />}>
                    <Page pageNumber={leftPage * 2} {...commonPageProps} />
                  </Document>
                </>
              ) : (
                <div style={{
                  flex: 1, display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', gap: 12,
                  color: 'var(--mute)',
                }}>
                  <Languages size={32} style={{ opacity: 0.3 }} />
                  <span style={{ fontSize: 13 }}>需要先翻译</span>
                  {babeldocAvailable ? (
                    <button
                      onClick={startTranslation}
                      disabled={isTranslating}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 6,
                        padding: '8px 20px', borderRadius: 8, border: 'none',
                        background: 'var(--accent, #6366f1)', color: '#fff',
                        fontSize: 13, cursor: 'pointer',
                      }}
                    >
                      <Play size={14} /> 开始全文翻译
                    </button>
                  ) : (
                    <span style={{ fontSize: 11, color: 'var(--mute)', opacity: 0.6 }}>
                      BabelDOC 未安装，请先在服务器安装 babeldoc
                    </span>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          /* Alternating pages mode: single PDF scroll */
          <div
            style={{
              flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column',
              alignItems: 'center', padding: '12px 0',
            }}
          >
            <Document file={dualUrl || originalUrl} loading={<Loader2 size={24} className="animate-spin" style={{ margin: 40 }} />}>
              {Array.from({ length: dualUrl ? numPages * 2 : numPages }, (_, i) => {
                const pageNum = i + 1;
                const isOriginal = dualUrl ? pageNum % 2 === 1 : true;
                return (
                  <div key={pageNum} style={{ position: 'relative', marginBottom: 8 }}>
                    {dualUrl && (
                      <div style={{
                        fontSize: 9, color: 'var(--mute)', padding: '2px 6px',
                        textAlign: 'center', background: isOriginal ? 'var(--bg-primary, #14141e)' : 'var(--accent-bg-soft, rgba(99,102,241,0.06))',
                        position: 'sticky', top: 0, zIndex: 1,
                      }}>
                        {isOriginal ? `原文 第 ${Math.ceil(pageNum / 2)} 页` : `译文 第 ${Math.ceil(pageNum / 2)} 页`}
                      </div>
                    )}
                    <Page pageNumber={pageNum} {...commonPageProps} />
                  </div>
                );
              })}
            </Document>
          </div>
        )}
      </div>

      {/* ===== Bottom Nav ===== */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 8, padding: '6px 12px', borderTop: '1px solid var(--hairline, #333)',
        background: 'var(--glass-bg)', backdropFilter: 'blur(12px)',
        flexShrink: 0,
      }}>
        <button onClick={goToPrevPair} disabled={leftPage <= 1} style={navBtnStyle}><ChevronLeft size={14} /></button>
        <span style={{ fontSize: 11, color: 'var(--mute)', minWidth: 80, textAlign: 'center' }}>
          {viewMode === 'side-by-side'
            ? `${leftPage}–${Math.min(rightPage, numPages)} / ${numPages}`
            : `${leftPage} / ${dualUrl ? numPages * 2 : numPages}`
          }
        </span>
        <button onClick={goToNextPair} disabled={viewMode === 'side-by-side' ? rightPage >= numPages : leftPage >= (dualUrl ? numPages * 2 - 1 : numPages - 1)} style={navBtnStyle}><ChevronRight size={14} /></button>
      </div>
    </div>
  );
};

// ==================== Styles ====================

const iconBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 28, height: 28, borderRadius: 6, border: 'none',
  background: 'transparent', color: 'var(--mute, #888)',
  cursor: 'pointer', padding: 0,
};

const navBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 32, height: 32, borderRadius: 8, border: '1px solid var(--hairline, #333)',
  background: 'var(--glass-bg)', color: 'var(--mute, #888)',
  cursor: 'pointer', padding: 0,
};

export default BilingualPDFViewer;