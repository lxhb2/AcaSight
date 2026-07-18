/**
 * useTextSelection — 文本选择监听 Hook
 *
 * 借鉴 pdf-reader-js 的选择监听设计：
 * - 监听 selectionchange / mousedown / mouseup 事件
 * - 防抖处理，避免频繁重算
 * - 自动识别选区所在的 PDF 页码
 * - 获取所有 DOMRect 用于精确定位弹窗
 */

import { useCallback, useEffect, useState, useRef } from 'react';

export interface TextSelection {
  text: string;
  pageNumber: number;
  rects: DOMRect[];
  range: Range | null;
}

export interface UseTextSelectionOptions {
  onSelect?: (selection: TextSelection) => void;
  debounceMs?: number;
}

export function useTextSelection(options: UseTextSelectionOptions = {}) {
  const { onSelect, debounceMs = 100 } = options;
  const [selection, setSelection] = useState<TextSelection | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  const handleSelectionChange = useCallback(() => {
    const windowSelection = window.getSelection();

    if (!windowSelection || windowSelection.isCollapsed) {
      setSelection(null);
      return;
    }

    const text = windowSelection.toString().trim();
    if (!text) {
      setSelection(null);
      return;
    }

    // 获取页码：从 anchorNode 向上查找 data-page-number
    const anchorNode = windowSelection.anchorNode;
    let pageElement: HTMLElement | null = anchorNode?.parentElement ?? null;
    while (pageElement && !pageElement.dataset.pageNumber) {
      pageElement = pageElement.parentElement;
    }
    const pageNumber = pageElement
      ? parseInt(pageElement.dataset.pageNumber || '1', 10)
      : 1;

    // 获取所有矩形
    const range = windowSelection.getRangeAt(0);
    const rects = Array.from(range.getClientRects());

    const newSelection: TextSelection = {
      text,
      pageNumber,
      rects,
      range,
    };

    // 防抖
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      setSelection(newSelection);
      onSelectRef.current?.(newSelection);
    }, debounceMs);
  }, [debounceMs]);

  const clearSelection = useCallback(() => {
    window.getSelection()?.removeAllRanges();
    setSelection(null);
  }, []);

  useEffect(() => {
    const handleMouseUp = () => {
      setIsSelecting(false);
      handleSelectionChange();
    };
    const handleMouseDown = () => setIsSelecting(true);

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('selectionchange', handleSelectionChange);

    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('selectionchange', handleSelectionChange);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [handleSelectionChange]);

  return {
    selection,
    isSelecting,
    clearSelection,
    hasSelection: selection !== null && selection.text.length > 0,
  };
}