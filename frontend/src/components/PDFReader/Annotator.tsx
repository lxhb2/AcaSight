/**
 * Annotator — 文字选择与标注编排组件
 *
 * 借鉴 Readest Annotator 的核心模式：
 * - 状态机：idle → toolbar → translate / note
 * - 集中化选择生命周期（usePDFTextSelector）
 * - 三角锚点定位（getPosition） + 弹窗约束定位（getPopupPosition）
 * - 4 色高亮选择器（HighlightOptions）
 * - 新建标注 / 编辑已有标注 两态合一
 * - 容器滚动时自动重定位弹窗（repositionPopups）
 * - 已存在标注的 click → 加载到弹窗（onShowAnnotation）
 * - 右键菜单 → 直接进入翻译弹窗
 *
 * 选区 → 工具栏 → 选择颜色/操作；新建标注后写入回调；
 * 点击已有标注 → 重新进入弹窗进行编辑/删除。
 */

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { AnnotationToolbar } from '@/components/PDFReader/AnnotationToolbar';
import { TranslatorPopup } from '@/components/PDFReader/TranslatorPopup';
import { AnnotationNotePopover } from '@/components/PDFReader/AnnotationNotePopover';
import { usePDFTextSelector } from '@/hooks/usePDFTextSelector';
import {
  getPosition,
  getPopupPosition,
  getRangeRect,
  snapRangeToWords,
  getTextFromRange,
  type TextSelection,
  type Position,
  type Rect,
} from '@/utils/sel';

/** 4 色高亮（Readest 的 "4-color rule" 简化为学术 4 含义） */
export const HIGHLIGHT_COLORS = [
  { key: 'yellow', hex: '#FFD700', label: '核心' },
  { key: 'green', hex: '#4CAF50', label: '方法' },
  { key: 'blue', hex: '#2196F3', label: '存疑' },
  { key: 'pink', hex: '#E91E63', label: '重要' },
] as const;
export type HighlightColorKey = (typeof HIGHLIGHT_COLORS)[number]['key'];
const DEFAULT_COLOR_KEY: HighlightColorKey = 'yellow';

export interface HighlightPayload {
  text: string;
  page: number;
  color: string;
  note?: string;
  cfi?: string;
  /** 选区 DOM 序列化信息（用于后续重新定位） */
  rect?: Rect;
  /** 编辑已有标注时携带的 id */
  annotationId?: string;
}

interface AnnotatorProps {
  containerRef: React.RefObject<HTMLElement | null>;
  /** 新建/更新标注回调。annotationId 为空时新建；否则更新 */
  onSaveAnnotation?: (payload: HighlightPayload) => void;
  /** 删除已有标注回调（点击 trash 时触发） */
  onDeleteAnnotation?: (id: string) => void;
  /** 询问"给定的文字是否已有标注"——用于 toolbar 切换"高亮/取消"状态 */
  findAnnotationByText?: (text: string, page: number) => HighlightPayload | undefined;
  /** 用户点击已有标注时由 PDFViewer 通知 Annotator 进入编辑态 */
  editToken?: { id: string; text: string; page: number; note?: string; color: string } | null;
}

type AnnotatorPhase = 'idle' | 'toolbar' | 'translate' | 'note' | 'edit';

function getPageNumberFromNode(node: Node | null): number {
  let el: Element | null =
    node?.nodeType === Node.TEXT_NODE ? (node as Text).parentElement : (node as Element | null);
  while (el) {
    const pn = el.getAttribute('data-page-number');
    if (pn) {
      const n = parseInt(pn, 10);
      if (!isNaN(n)) return n;
    }
    el = el.parentElement;
  }
  return 1;
}

export const Annotator: React.FC<AnnotatorProps> = ({
  containerRef,
  onSaveAnnotation,
  onDeleteAnnotation,
  findAnnotationByText,
  editToken,
}) => {
  const [phase, setPhase] = useState<AnnotatorPhase>('idle');
  const [selection, setSelection] = useState<TextSelection | null>(null);
  const [anchor, setAnchor] = useState<Position | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingColor, setEditingColor] = useState<HighlightColorKey>(DEFAULT_COLOR_KEY);
  const [pendingNote, setPendingNote] = useState('');

  const selectorRef = useRef<ReturnType<typeof usePDFTextSelector> | null>(null);
  const phaseRef = useRef<AnnotatorPhase>('idle');
  phaseRef.current = phase;

  const getContainerRect = useCallback((): Rect => {
    const el = containerRef.current;
    if (!el) {
      return { top: 0, left: 0, right: window.innerWidth, bottom: window.innerHeight };
    }
    return el.getBoundingClientRect();
  }, [containerRef]);

  // 把原生 Selection 转换为内部 TextSelection
  const buildSelectionFromNative = useCallback(
    (sel: Selection): TextSelection | null => {
      if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
      const range = sel.getRangeAt(0);
      if (!range) return null;
      try {
        snapRangeToWords(range);
      } catch {
        /* ignore */
      }
      const text = getTextFromRange(range);
      if (text.trim().length < 2) return null;
      const rect = getRangeRect(range) ?? undefined;
      const page = getPageNumberFromNode(range.startContainer);
      return { text, page, range, rect };
    },
    [],
  );

  // 同步选区到组件 state + 三角锚点
  const handleSelectionChange = useCallback(
    (sel: Selection | null) => {
      if (!sel) {
        if (phaseRef.current === 'toolbar') {
          // 保留 toolbar 状态：浏览器清空选区可能是点击工具栏副作用
        } else {
          setPhase('idle');
          setSelection(null);
          setAnchor(null);
        }
        return;
      }
      const built = buildSelectionFromNative(sel);
      if (!built) {
        return;
      }
      setSelection(built);
      const containerRect = getContainerRect();
      const pos = getPosition(built.range!, containerRect, 10);
      if (pos.point.x === 0 && pos.point.y === 0) return;
      setAnchor(pos);
      if (phaseRef.current === 'idle') {
        setPhase('toolbar');
        selectorRef.current?.setPopuped(true);
      }
    },
    [buildSelectionFromNative, getContainerRect],
  );

  const handleUpToPopup = useCallback(() => {
    if (phaseRef.current === 'idle') {
      setPhase('toolbar');
      selectorRef.current?.setPopuped(true);
    }
  }, []);

  const handleDismiss = useCallback(() => {
    setPhase('idle');
    setSelection(null);
    setAnchor(null);
    setPendingNote('');
    setEditingId(null);
    selectorRef.current?.setPopuped(false);
    try {
      window.getSelection()?.removeAllRanges();
    } catch {
      /* ignore */
    }
  }, []);

  // 绑定选择 Hook
  selectorRef.current = usePDFTextSelector({
    onSelectionChange: handleSelectionChange,
    onUpToPopup: handleUpToPopup,
    onDismiss: handleDismiss,
    containerRef,
    minLength: 2,
  });

  // ===== 操作回调 =====
  const handleCopy = useCallback(async () => {
    if (!selection?.text) return;
    try {
      await navigator.clipboard.writeText(selection.text);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = selection.text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
  }, [selection?.text]);

  const handleTranslate = useCallback(() => {
    if (!selection) return;
    setPhase('translate');
  }, [selection]);

  const handlePickColor = useCallback(
    (colorKey: HighlightColorKey) => {
      if (!selection) return;
      const color = HIGHLIGHT_COLORS.find((c) => c.key === colorKey)!.hex;
      onSaveAnnotation?.({
        text: selection.text,
        page: selection.page,
        color,
        note: pendingNote || undefined,
        cfi: undefined,
        rect: selection.rect,
        annotationId: editingId ?? undefined,
      });
      setPendingNote('');
      setEditingId(null);
      handleDismiss();
    },
    [selection, pendingNote, editingId, onSaveAnnotation, handleDismiss],
  );

  const handleAddNote = useCallback(() => {
    if (!selection) return;
    setPhase('note');
  }, [selection]);

  const handleSaveNote = useCallback(
    (note: string) => {
      if (!selection) return;
      setPendingNote(note);
      // 关闭 note popover，回到 toolbar 让用户选颜色
      setPhase('toolbar');
    },
    [selection],
  );

  const handleSpeak = useCallback(() => {
    if (!selection?.text || !('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(selection.text);
    u.lang = 'en-US';
    u.rate = 0.9;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  }, [selection?.text]);

  const handleSearch = useCallback(() => {
    if (!selection?.text) return;
    window.open(
      `https://scholar.google.com/scholar?q=${encodeURIComponent(selection.text)}`,
      '_blank',
    );
  }, [selection?.text]);

  const handleDeleteEditing = useCallback(() => {
    if (!editingId) return;
    onDeleteAnnotation?.(editingId);
    handleDismiss();
  }, [editingId, onDeleteAnnotation, handleDismiss]);

  // ===== 外部"编辑已有标注"入口 =====
  useEffect(() => {
    if (!editToken) return;
    setPhase('edit');
    setEditingId(editToken.id);
    setPendingNote(editToken.note ?? '');
    const known = HIGHLIGHT_COLORS.find((c) => c.hex === editToken.color);
    setEditingColor(known?.key ?? DEFAULT_COLOR_KEY);
    setSelection({
      text: editToken.text,
      page: editToken.page,
      annotated: true,
    });
    const containerRect = getContainerRect();
    // 用容器中央作为锚点（编辑态选区可能已被清空）
    setAnchor({
      point: {
        x: (containerRect.left + containerRect.right) / 2 - containerRect.left,
        y: Math.max(80, (containerRect.top + containerRect.bottom) / 2 - containerRect.top - 200),
      },
      dir: 'down',
    });
    selectorRef.current?.setPopuped(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editToken]);

  // 滚动重定位
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let raf = 0;
    const onScroll = () => {
      if (phaseRef.current === 'idle' || !selection?.range) return;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const containerRect = getContainerRect();
        const pos = getPosition(selection.range!, containerRect, 10);
        if (pos.point.x || pos.point.y) setAnchor(pos);
      });
    };
    container.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      container.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      cancelAnimationFrame(raf);
    };
  }, [containerRef, getContainerRect, selection]);

  // 计算弹窗最终位置
  const toolbarPos = useMemo<Position | null>(() => {
    if (!anchor) return null;
    const containerRect = getContainerRect();
    return getPopupPosition(anchor, containerRect, 280, 40, 8);
  }, [anchor, getContainerRect]);

  const notePos = useMemo<Position | null>(() => {
    if (!anchor) return null;
    const containerRect = getContainerRect();
    return getPopupPosition(anchor, containerRect, 320, 180, 8);
  }, [anchor, getContainerRect]);

  const existingHighlight = useMemo(() => {
    if (!selection) return null;
    return findAnnotationByText?.(selection.text, selection.page) ?? null;
  }, [selection, findAnnotationByText]);

  return (
    <>
      {phase === 'toolbar' && toolbarPos && selection && (
        <AnnotationToolbar
          anchorPosition={toolbarPos}
          onDismiss={handleDismiss}
          onCopy={handleCopy}
          onTranslate={handleTranslate}
          onPickColor={handlePickColor}
          onAddNote={handleAddNote}
          onSearch={handleSearch}
          onSpeak={handleSpeak}
          editingColor={editingColor}
          defaultColor={existingHighlight ? undefined : DEFAULT_COLOR_KEY}
          hasHighlight={!!existingHighlight}
        />
      )}

      {phase === 'translate' && selection && toolbarPos && (
        <TranslatorPopup
          text={selection.text}
          anchorPosition={toolbarPos}
          onDismiss={() => setPhase('toolbar')}
        />
      )}

      {phase === 'note' && selection && notePos && (
        <AnnotationNotePopover
          anchorPosition={notePos}
          initialNote={pendingNote}
          onSave={handleSaveNote}
          onDismiss={() => setPhase('toolbar')}
        />
      )}

      {phase === 'edit' && editToken && toolbarPos && (
        <AnnotationToolbar
          anchorPosition={toolbarPos}
          onDismiss={handleDismiss}
          onCopy={handleCopy}
          onTranslate={handleTranslate}
          onPickColor={(colorKey) => {
            const color = HIGHLIGHT_COLORS.find((c) => c.key === colorKey)!.hex;
            onSaveAnnotation?.({
              text: editToken.text,
              page: editToken.page,
              color,
              note: pendingNote || editToken.note || undefined,
              annotationId: editToken.id,
            });
            handleDismiss();
          }}
          onAddNote={() => setPhase('note')}
          onDelete={editingId ? handleDeleteEditing : undefined}
          editingColor={editingColor}
          isEdit
        />
      )}
    </>
  );
};

export default Annotator;
