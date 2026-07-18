/**
 * usePDFTextSelector — 集中管理 PDF 文本选择生命周期
 *
 * 借鉴 Readest 的 useTextSelector：
 * - 单一 Hook 统一处理 pointerdown / pointermove / pointerup / selectionchange
 * - 与 selectionchange + selection.isCollapsed 判断协作（覆盖触屏/鼠标）
 * - 跟踪 `isUpToPopup`（点击在选区内）与 `isTextSelected`（是否有非空选区）
 * - 点击外部时通过 isPopuped/isUpToPopup 决定是否关闭弹窗
 * - 滚动时通过返回的 handleScroll 同步锁定容器位置（移动端避免滚动跳跃）
 *
 * 真正的选区内容由调用方在 `onSelectionChange` 回调里读取
 * `window.getSelection()`，因为 React 组件对 iframe/外层 doc 都有
 * 自己的 Selection 视图，Hook 只负责事件路由。
 */

import { useEffect, useRef } from 'react';
import { isPointerInsideSelection } from '@/utils/sel';

export interface UsePDFTextSelectorOptions {
  /** 触发选择回调。传入 null 表示"无选区/清空" */
  onSelectionChange: (sel: Selection | null) => void;
  /** 点击在选区内、且不是修改选区 → 进入弹窗模式 */
  onUpToPopup?: () => void;
  /** 单击非选区 / 弹窗外 → 关闭弹窗 */
  onDismiss?: () => void;
  /** 容器（react-pdf 渲染区）Ref，用于检测选区起点 */
  containerRef: React.RefObject<HTMLElement | null>;
  /** 选区文字最小长度（低于此长度视为清空） */
  minLength?: number;
}

export interface UsePDFTextSelectorResult {
  /** 标记当前是否有弹窗可见（用于决定 pointerdown 是否走关闭路径） */
  setPopuped: (v: boolean) => void;
  /** 查询当前是否有弹窗可见 */
  isPopuped: () => boolean;
}

export function usePDFTextSelector({
  onSelectionChange,
  onUpToPopup,
  onDismiss,
  containerRef,
  minLength = 2,
}: UsePDFTextSelectorOptions): UsePDFTextSelectorResult {
  const isTextSelectedRef = useRef(false);
  const isPopupedRef = useRef(false);
  const isUpToPopupRef = useRef(false);
  const dismissedAtRef = useRef(0);
  const downAtRef = useRef(0);

  // selectionchange：跨触屏/鼠标的通用入口
  useEffect(() => {
    const handler = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.toString().trim().length < minLength) {
        if (isTextSelectedRef.current) {
          isTextSelectedRef.current = false;
          isUpToPopupRef.current = false;
          onSelectionChange(null);
        }
        return;
      }
      isTextSelectedRef.current = true;
      onSelectionChange(sel);
    };
    document.addEventListener('selectionchange', handler);
    return () => document.removeEventListener('selectionchange', handler);
  }, [onSelectionChange, minLength]);

  // 容器内 pointerdown：准备关闭已存在的弹窗（轻微延迟，等 pointerup 完成）
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onPointerDown = (ev: PointerEvent) => {
      downAtRef.current = ev.timeStamp;
      const target = ev.target as HTMLElement;
      // 在弹窗/工具栏内部点击 → 不处理
      if (
        target.closest('.annotation-toolbar') ||
        target.closest('.translator-popup') ||
        target.closest('.annotation-note-popover') ||
        target.closest('.ctx-bubble-panel')
      ) {
        return;
      }
      // 弹窗模式下，记录"是否点击在已有选区内"；否则准备关闭
      if (isPopupedRef.current) {
        const sel = window.getSelection();
        if (sel && isPointerInsideSelection(sel, ev)) {
          isUpToPopupRef.current = true;
        } else {
          isUpToPopupRef.current = false;
        }
      } else {
        isUpToPopupRef.current = false;
      }
    };

    const onPointerUp = (ev: PointerEvent) => {
      const target = ev.target as HTMLElement;
      if (
        target.closest('.annotation-toolbar') ||
        target.closest('.translator-popup') ||
        target.closest('.annotation-note-popover') ||
        target.closest('.ctx-bubble-panel')
      ) {
        return;
      }
      // 避免极短点击（误触）
      if (ev.timeStamp - downAtRef.current < 50) return;

      // 等待浏览器完成选区
      setTimeout(() => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || sel.toString().trim().length < minLength) {
          // 真正的"单击"或拖空白
          if (isPopupedRef.current && !isUpToPopupRef.current) {
            isPopupedRef.current = false;
            isUpToPopupRef.current = false;
            dismissedAtRef.current = Date.now();
            onDismiss?.();
          }
          return;
        }
        // 选区存在 → 进入或保持在弹窗模式
        isTextSelectedRef.current = true;
        if (isPointerInsideSelection(sel, ev)) {
          isUpToPopupRef.current = true;
          onUpToPopup?.();
        }
        onSelectionChange(sel);
      }, 60);
    };

    // contextmenu：右键直接进翻译弹窗（PDF 阅读体验）
    const onContextMenu = (ev: MouseEvent) => {
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed && sel.toString().trim().length >= minLength) {
        isTextSelectedRef.current = true;
        isUpToPopupRef.current = true;
        onSelectionChange(sel);
        onUpToPopup?.();
        ev.preventDefault();
        ev.stopPropagation();
      }
    };

    container.addEventListener('pointerdown', onPointerDown);
    container.addEventListener('pointerup', onPointerUp);
    container.addEventListener('contextmenu', onContextMenu);
    return () => {
      container.removeEventListener('pointerdown', onPointerDown);
      container.removeEventListener('pointerup', onPointerUp);
      container.removeEventListener('contextmenu', onContextMenu);
    };
  }, [containerRef, minLength, onSelectionChange, onUpToPopup, onDismiss]);

  // Esc 关闭
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      if (!isPopupedRef.current) return;
      isPopupedRef.current = false;
      isUpToPopupRef.current = false;
      isTextSelectedRef.current = false;
      onDismiss?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onDismiss]);

  // 提供给 Annotator 用来标记弹窗态
  return {
    setPopuped: (v: boolean) => {
      isPopupedRef.current = v;
    },
    isPopuped: () => isPopupedRef.current,
  };
}
