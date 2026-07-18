/**
 * TranslatorPopup — 内嵌翻译弹窗
 *
 * 借鉴 Readest 的 TranslatorPopup 设计：
 * - 紧凑卡片布局：原文在上，译文在下
 * - 精确锚定到选中文本位置
 * - 三角指示器指向选中区域
 * - 点击外部自动关闭
 * - 使用 Helsinki-NLP Opus-MT 学术翻译引擎（AI 降级兜底）
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Copy, Check, Loader2, Globe } from 'lucide-react';
import { translateApi } from '@/services/api';
import type { Position } from '@/utils/sel';

interface TranslatorPopupProps {
  /** 选中文本 */
  text: string;
  /** 锚点位置（三角形指示器位置） */
  anchorPosition: Position | null;
  /** 弹窗最大宽度 */
  maxWidth?: number;
  /** 关闭回调 */
  onDismiss: () => void;
}

const POPUP_WIDTH = 420;
const POPUP_HEIGHT = 260;
const TRIANGLE_SIZE = 8;

const ENGINE_LABELS: Record<string, string> = {
  google: 'Google 翻译',
  microsoft: '微软翻译',
  mymemory: 'MyMemory 翻译',
  ai: 'AI 翻译',
  cache: '缓存',
  identity: '原文',
  none: '翻译',
};

export const TranslatorPopup: React.FC<TranslatorPopupProps> = ({
  text,
  anchorPosition,
  maxWidth = 480,
  onDismiss,
}) => {
  const [translation, setTranslation] = useState('');
  const [engine, setEngine] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const popupRef = useRef<HTMLDivElement>(null);

  // Translate on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const doTranslate = async () => {
      try {
        const res = await translateApi.quick({
          text,
          source_lang: 'auto',
          target_lang: 'zh',
        });
        if (!cancelled && res.data) {
          setTranslation(res.data.translation || '翻译失败');
          setEngine(res.data.engine || '');
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '翻译失败');
          setLoading(false);
        }
      }
    };

    doTranslate();
    return () => { cancelled = true; };
  }, [text]);

  // Copy
  const handleCopy = useCallback(async () => {
    if (!translation) return;
    try {
      await navigator.clipboard.writeText(translation);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = translation;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [translation]);

  // Click outside to dismiss
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        onDismiss();
      }
    };
    setTimeout(() => document.addEventListener('mousedown', handler), 100);
    return () => document.removeEventListener('mousedown', handler);
  }, [onDismiss]);

  // Esc to dismiss
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onDismiss]);

  // Calculate popup position
  if (!anchorPosition) return null;

  const viewportW = window.innerWidth;
  const viewportH = window.innerHeight;
  const popupW = Math.min(POPUP_WIDTH, maxWidth);

  // Position centered on anchor point, above or below
  let popupX = anchorPosition.point.x - popupW / 2;
  let popupY: number;
  const isAbove = anchorPosition.dir === 'up';

  if (isAbove) {
    popupY = anchorPosition.point.y - POPUP_HEIGHT - TRIANGLE_SIZE;
  } else {
    popupY = anchorPosition.point.y + TRIANGLE_SIZE;
  }

  // Constrain to viewport
  popupX = Math.max(8, Math.min(popupX, viewportW - popupW - 8));
  popupY = Math.max(8, Math.min(popupY, viewportH - POPUP_HEIGHT - 8));

  // Triangle position relative to popup
  const triX = anchorPosition.point.x - popupX;

  return (
    <div
      ref={popupRef}
      className="translator-popup"
      style={{
        position: 'fixed',
        left: popupX,
        top: popupY,
        width: popupW,
        zIndex: 10001,
        background: 'var(--canvas, #1e1e2e)',
        border: '1px solid var(--hairline, #333)',
        borderRadius: 12,
        boxShadow: '0 16px 48px rgba(0,0,0,0.4), 0 2px 8px rgba(0,0,0,0.2)',
        overflow: 'hidden',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {/* Triangle pointer */}
      <div
        style={{
          position: 'absolute',
          ...(isAbove
            ? { bottom: -TRIANGLE_SIZE, borderTop: `${TRIANGLE_SIZE}px solid var(--canvas, #1e1e2e)` }
            : { top: -TRIANGLE_SIZE, borderBottom: `${TRIANGLE_SIZE}px solid var(--canvas, #1e1e2e)` }),
          left: Math.max(TRIANGLE_SIZE + 4, Math.min(triX, popupW - TRIANGLE_SIZE - 4)),
          borderLeft: `${TRIANGLE_SIZE}px solid transparent`,
          borderRight: `${TRIANGLE_SIZE}px solid transparent`,
        }}
      />

      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 12px', borderBottom: '1px solid var(--hairline, #333)',
        background: 'var(--accent-bg-soft, rgba(99,102,241,0.06))',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <Globe size={14} style={{ color: 'var(--accent, #6366f1)' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body, #ddd)' }}>
            {ENGINE_LABELS[engine] || '翻译'}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 2 }}>
          {translation && !loading && (
            <button onClick={handleCopy} title="复制" style={iconBtnStyle}>
              {copied ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
            </button>
          )}
          <button onClick={onDismiss} title="关闭" style={iconBtnStyle}>
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ display: 'flex', flexDirection: 'column', maxHeight: POPUP_HEIGHT - 40 }}>
        {/* Original */}
        <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--hairline, #333)' }}>
          <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            原文
          </div>
          <div style={{
            fontSize: 12, color: 'var(--body, #ccc)', lineHeight: 1.6,
            maxHeight: 60, overflow: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          }}>
            {text}
          </div>
        </div>

        {/* Translation */}
        <div style={{ padding: '8px 12px', flex: 1, overflow: 'auto' }}>
          <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
            翻译
          </div>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0', color: 'var(--mute)' }}>
              <Loader2 size={14} className="animate-spin" />
              <span style={{ fontSize: 13 }}>翻译中...</span>
            </div>
          ) : error ? (
            <div style={{ color: '#ef4444', fontSize: 12 }}>{error}</div>
          ) : (
            <div style={{
              fontSize: 13, color: 'var(--ink)', lineHeight: 1.7,
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {translation}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const iconBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 26, height: 26, borderRadius: 6, border: 'none',
  background: 'transparent', color: 'var(--mute, #888)',
  cursor: 'pointer', padding: 0,
};

export default TranslatorPopup;