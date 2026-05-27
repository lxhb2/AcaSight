import { useState, useEffect, useCallback, useRef } from 'react';

interface SelectionInfo {
  text: string;
  position: { x: number; y: number };
}

export function useTextSelection(minLength = 2) {
  const [selection, setSelection] = useState<SelectionInfo | null>(null);
  const [enabled, setEnabled] = useState(true);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const lastTextRef = useRef('');
  const lastMousePosRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      lastMousePosRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('mousemove', onMouseMove);
    return () => window.removeEventListener('mousemove', onMouseMove);
  }, []);

  // ── 从 input/textarea 获取选中 ──
  const getInputSelection = (): SelectionInfo | null => {
    const el = document.activeElement;
    if (!el) return null;
    if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA') return null;
    const input = el as HTMLInputElement | HTMLTextAreaElement;
    const start = input.selectionStart ?? 0;
    const end = input.selectionEnd ?? 0;
    if (start === end) return null;
    const text = input.value.slice(start, end).trim();
    if (text.length < minLength) return null;

    // 获取光标在屏幕上的位置
    const rect = input.getBoundingClientRect();
    // 估算文本位置 (在 input 内取左上角)
    const lines = input.value.slice(0, start).split('\n');
    const lineNum = lines.length;
    const colNum = lines[lines.length - 1].length;
    const lineHeight = parseInt(getComputedStyle(input).lineHeight) || 20;
    const charWidth = 8;

    return {
      text,
      position: {
        x: rect.left + Math.min(colNum * charWidth, rect.width - 20),
        y: rect.top + lineNum * lineHeight - 8,
      },
    };
  };

  const getDomSelection = (): SelectionInfo | null => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) return null;
    const text = sel.toString().trim();
    if (text.length < minLength) return null;

    // Prefer selection range bounding rect for accuracy; fall back to mouse position
    let pos: { x: number; y: number } = lastMousePosRef.current;
    try {
      if (sel.rangeCount > 0) {
        const range = sel.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        if (rect && (rect.width > 0 || rect.height > 0)) {
          pos = { x: rect.right + 4, y: rect.bottom + 4 };
        }
      }
    } catch {
      // Silently fall back to mouse position
    }
    return { text, position: pos };
  };

  // ── 统一检测选中 ──
  const detectSelection = useCallback(() => {
    if (!enabled) return;

    // 先试 input/textarea，再试普通 DOM
    const info = getInputSelection() || getDomSelection();
    if (info) {
      lastTextRef.current = info.text;
      setSelection(info);
    }
    // 注意：不再这里清除 — 让 clearTimer 处理
  }, [enabled, minLength]);

  // ── 清除选中 ──
  const scheduleClear = useCallback((delayMs = 150) => {
    if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    clearTimerRef.current = setTimeout(() => {
      // 检查选区是否真的消失了
      const inputSel = getInputSelection();
      const domSel = getDomSelection();
      if (!inputSel && !domSel) {
        setSelection(null);
        lastTextRef.current = '';
      }
    }, delayMs);
  }, []);

  useEffect(() => {
    // ── selectionchange: 任何选中的变化 → 检测 ──
    const onSelectChange = () => {
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
      clearTimerRef.current = setTimeout(detectSelection, 80);
    };

    // ── mouseup: 确保 mouse 拖拽选中也能捕获 ──
    const onMouseUp = () => {
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
      clearTimerRef.current = setTimeout(detectSelection, 120);
    };

    // ── mousedown: 点击浮动气泡内部不清除；点击外部立即调度清除 ──
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const insideFloating =
        target.closest('.acasight-floating-bubble') ||
        target.closest('.acasight-floating-translate') ||
        target.closest('.acasight-ai-toolbar') ||
        target.closest('[class*="floating-bubble"]');
      if (!insideFloating) {
        scheduleClear(120);
      }
    };

    // ── keydown: Escape 立即清除 ──
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
        setSelection(null);
        lastTextRef.current = '';
      }
    };

    // ── scroll: 页面滚动时清除（位置会偏移） ──
    const onScroll = () => {
      scheduleClear(200);
    };

    document.addEventListener('selectionchange', onSelectChange);
    document.addEventListener('mouseup', onMouseUp);
    document.addEventListener('mousedown', onMouseDown);
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('scroll', onScroll, true);

    return () => {
      document.removeEventListener('selectionchange', onSelectChange);
      document.removeEventListener('mouseup', onMouseUp);
      document.removeEventListener('mousedown', onMouseDown);
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('scroll', onScroll, true);
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    };
  }, [detectSelection, scheduleClear]);

  const clearSelection = useCallback(() => {
    setSelection(null);
    lastTextRef.current = '';
  }, []);

  return { selection, clearSelection, setEnabled };
}
