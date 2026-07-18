/**
 * FloatingTranslate — 浮动翻译弹窗
 *
 * v2.0 重构:
 * - 使用 useTextSelection Hook 监听选区（防抖 + 精确定位）
 * - 使用 positionCalculator 计算弹窗位置（视口边界检测）
 * - 支持流式翻译（SSE）
 * - 滚动时自动隐藏，停止后重定位
 * - 保留原有工具：拖拽、复制、写作工具、AI 解释
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { translateApi } from '../../services/api';
import { useTextSelection } from '../../hooks/useTextSelection';
import { calculatePopoverPosition } from '../../utils/positionCalculator';
import { useFloatingTranslate } from '../../hooks/useFloatingTranslate';

interface FloatingTranslateProps {
  pdfUrl: string;
  pageNumber: number;
  scale: number;
}

export default function FloatingTranslate({ pdfUrl, pageNumber, scale }: FloatingTranslateProps) {
  const [visible, setVisible] = useState(false);
  const [translation, setTranslation] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [selectedText, setSelectedText] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [hasCopied, setHasCopied] = useState(false);

  const popupRef = useRef<HTMLDivElement>(null);
  const scrollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 使用 useFloatingTranslate 获取 AI 解释等高级功能
  const {
    aiExplanation,
    aiLoading,
    showAiExplanation,
    setShowAiExplanation,
    generateExplanation,
  } = useFloatingTranslate();

  // 选择监听的 store
  const { showTranslation, setShowTranslation } = useFloatingTranslateStore();

  const handleSelection = useCallback((sel: TextSelection) => {
    if (!sel || !sel.text || sel.text.length < 2) {
      if (visible) setVisible(false);
      return;
    }

    setSelectedText(sel.text);
    setError(null);

    // 计算位置（带视口边界检测）
    const pos = calculatePopoverPosition(sel.rects, {
      popoverWidth: 380,
      popoverHeight: 300,
      scale,
    });

    setPosition(pos);
    setVisible(true);
    setShowAiExplanation(false);

    // 触发翻译
    performTranslation(sel.text);
  }, [scale, visible]);

  const { selection, clearSelection } = useTextSelection({
    onSelect: handleSelection,
    debounceMs: 150,
  });

  const performTranslation = useCallback(async (text: string) => {
    setIsLoading(true);
    setTranslation('');
    setIsStreaming(false);

    // 取消之前的流式请求
    if (abortRef.current) {
      abortRef.current.abort();
    }
    abortRef.current = new AbortController();

    try {
      // 先尝试流式翻译
      setIsStreaming(true);
      let result = '';

      for await (const chunk of translateApi.translateStream({
        text,
        source_lang: 'auto',
        target_lang: 'zh',
      })) {
        if (abortRef.current?.signal.aborted) break;
        result += chunk;
        setTranslation(prev => prev + chunk);
      }

      if (!result) {
        // 流式失败，回退到普通接口
        const resp = await translateApi.text({ text, source_lang: 'auto', target_lang: 'zh' });
        setTranslation(resp.data.translation);
      }
    } catch (e) {
      // 流式失败，回退到普通接口
      try {
        const resp = await translateApi.text({ text, source_lang: 'auto', target_lang: 'zh' });
        setTranslation(resp.data.translation);
        setError(null);
      } catch (e2) {
        setError((e2 as Error).message || '翻译失败');
        setTranslation('');
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  }, []);

  // 滚动时隐藏，停止后重定位
  useEffect(() => {
    if (!visible) return;

    const handleScroll = () => {
      setVisible(false);

      if (scrollTimerRef.current) {
        clearTimeout(scrollTimerRef.current);
      }
      scrollTimerRef.current = setTimeout(() => {
        if (selection) {
          const pos = calculatePopoverPosition(selection.rects, {
            popoverWidth: 380,
            popoverHeight: 300,
            scale,
          });
          setPosition(pos);
          setVisible(true);
        }
      }, 500);
    };

    window.addEventListener('scroll', handleScroll, true);
    return () => {
      window.removeEventListener('scroll', handleScroll, true);
      if (scrollTimerRef.current) clearTimeout(scrollTimerRef.current);
    };
  }, [visible, selection, scale]);

  // 点击外部关闭
  useEffect(() => {
    if (!visible) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (popupRef.current && !popupRef.current.contains(e.target as Node)) {
        setVisible(false);
        clearSelection();
      }
    };

    setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 0);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [visible, clearSelection]);

  const handleCopy = useCallback(async () => {
    if (translation) {
      await navigator.clipboard.writeText(translation);
      setHasCopied(true);
      setTimeout(() => setHasCopied(false), 2000);
    }
  }, [translation]);

  const handleAiExplain = useCallback(() => {
    if (selectedText) {
      generateExplanation(selectedText);
    }
  }, [selectedText, generateExplanation]);

  // 拖拽
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target instanceof HTMLElement && e.target.closest('.drag-handle')) {
      setIsDragging(true);
      setDragOffset({
        x: e.clientX - position.left,
        y: e.clientY - position.top,
      });
      e.preventDefault();
    }
  }, [position]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isDragging) {
      setPosition({
        left: e.clientX - dragOffset.x,
        top: e.clientY - dragOffset.y,
      });
    }
  }, [isDragging, dragOffset]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  if (!visible) return null;

  return (
    <div
      ref={popupRef}
      className="floating-translate-popup"
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        zIndex: 10000,
        transform: 'translate(-50%, 0)',
        width: 380,
        maxHeight: 'calc(100vh - 40px)',
        background: 'white',
        borderRadius: 12,
        boxShadow: '0 8px 32px rgba(0,0,0,0.15), 0 2px 8px rgba(0,0,0,0.08)',
        border: '1px solid #e5e7eb',
        overflow: 'hidden',
        transition: 'opacity 0.15s ease',
        opacity: 1,
      }}
      onMouseDown={handleMouseDown}
    >
      {/* 拖拽手柄 */}
      <div
        className="drag-handle"
        style={{
          height: 36,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          cursor: 'grab',
          borderBottom: '1px solid #f3f4f6',
          background: '#fafafa',
          userSelect: 'none',
        }}
      >
        <span style={{ fontSize: 13, color: '#6b7280', fontWeight: 500 }}>翻译</span>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {translation && (
            <button
              onClick={handleCopy}
              title={hasCopied ? '已复制' : '复制译文'}
              style={{
                border: 'none',
                background: 'none',
                cursor: 'pointer',
                padding: '2px 6px',
                fontSize: 12,
                color: hasCopied ? '#10b981' : '#6b7280',
                borderRadius: 4,
              }}
            >
              {hasCopied ? '✓ 已复制' : '复制'}
            </button>
          )}
          <button
            onClick={handleAiExplain}
            title="AI 解释"
            style={{
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              padding: '2px 6px',
              fontSize: 12,
              color: '#6b7280',
              borderRadius: 4,
            }}
          >
            AI 解释
          </button>
          <button
            onClick={() => { setVisible(false); clearSelection(); }}
            title="关闭"
            style={{
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              padding: '2px 4px',
              fontSize: 16,
              color: '#9ca3af',
              borderRadius: 4,
              lineHeight: 1,
            }}
          >
            ×
          </button>
        </div>
      </div>

      {/* 原文 */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid #f3f4f6' }}>
        <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4 }}>原文</div>
        <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.6, maxHeight: 60, overflow: 'auto' }}>
          {selectedText}
        </div>
      </div>

      {/* 翻译结果 */}
      <div style={{ padding: '10px 14px', maxHeight: 200, overflow: 'auto', minHeight: 60 }}>
        {isLoading && !isStreaming && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#9ca3af', fontSize: 13 }}>
            <div className="animate-spin" style={{ width: 14, height: 14, border: '2px solid #e5e7eb', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
            翻译中...
          </div>
        )}
        {isStreaming && (
          <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.7 }}>
            {translation || '...'}
            <span className="animate-pulse" style={{ color: '#3b82f6' }}>|</span>
          </div>
        )}
        {!isLoading && translation && (
          <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.7 }}>
            {translation}
          </div>
        )}
        {error && (
          <div style={{ fontSize: 13, color: '#ef4444', lineHeight: 1.5 }}>
            翻译失败: {error}
          </div>
        )}
      </div>

      {/* AI 解释区域 */}
      {showAiExplanation && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f3f4f6', maxHeight: 180, overflow: 'auto' }}>
          <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 4 }}>AI 解释</div>
          {aiLoading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#9ca3af', fontSize: 13 }}>
              <div className="animate-spin" style={{ width: 14, height: 14, border: '2px solid #e5e7eb', borderTopColor: '#8b5cf6', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              生成解释...
            </div>
          ) : (
            <div style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.7 }}>
              {aiExplanation}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// 全局 store（简化版，避免循环依赖）
import { create } from 'zustand';

interface FloatingTranslateState {
  showTranslation: boolean;
  setShowTranslation: (v: boolean) => void;
}

const useFloatingTranslateStore = create<FloatingTranslateState>((set) => ({
  showTranslation: false,
  setShowTranslation: (v) => set({ showTranslation: v }),
}));