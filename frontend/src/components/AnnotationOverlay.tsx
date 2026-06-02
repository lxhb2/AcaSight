/**
 * AnnotationOverlay — PDF 批注叠加层 v2.0
 *
 * 在 PDF 页面上渲染高亮、下划线、删除线、文本批注。
 * 使用 PDF 坐标系直接映射到页面元素。
 *
 * v2.0 关键改进：
 * - 批注层默认 pointer-events: none，不阻碍文本选择
 * - 仅批注元素自身可点击 (pointer-events: auto)
 * - 支持浏览器原生文本选择 → 选中后弹出浮动工具栏创建批注
 * - 标注模式下仍可拖拽创建矩形批注
 */

import React, { useCallback, useRef, useState, useEffect } from 'react';
import { useApp } from '@/contexts/AppContext';
import type { AnnotationItem } from '@/services/api';
import { annotationsApi } from '@/services/api';

interface AnnotationOverlayProps {
  pageNumber: number;
  pageWidth: number;
  pageHeight: number;
  scale: number;
}

// 颜色选择器
const HIGHLIGHT_COLORS = [
  { name: '黄', value: '#FFEB3B' },
  { name: '绿', value: '#66BB6A' },
  { name: '蓝', value: '#42A5F5' },
  { name: '粉', value: '#EF5350' },
  { name: '橙', value: '#FFA726' },
  { name: '紫', value: '#AB47BC' },
];

interface TextSelectionState {
  text: string;
  pageNumber: number;
  rects: DOMRect[];
}

const AnnotationOverlay: React.FC<AnnotationOverlayProps> = ({
  pageNumber,
  pageWidth,
  pageHeight,
  scale,
}) => {
  const { annotations, createAnnotation, deleteAnnotation, pdfHash, annotationTool, annotationColor } = useApp();

  // --- 拖拽绘制状态（仅标注模式激活时使用） ---
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<{ x: number; y: number } | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<{ x: number; y: number } | null>(null);

  // --- 文本选择工具栏状态 ---
  const [textSelection, setTextSelection] = useState<TextSelectionState | null>(null);
  const [showSelectionToolbar, setShowSelectionToolbar] = useState(false);
  const [toolbarPos, setToolbarPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });

  // --- 通用 UI 状态 ---
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [pendingRect, setPendingRect] = useState<number[] | null>(null);
  const [editingAnnotation, setEditingAnnotation] = useState<number | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // 当前是否有标注工具激活
  const isAnnotationMode = !!annotationTool;

  // --- 监听浏览器文本选择（仅非标注模式时） ---
  useEffect(() => {
    if (isAnnotationMode) return;

    const handleMouseUp = () => {
      // 短暂延迟让浏览器完成选择
      setTimeout(() => {
        const sel = window.getSelection();
        if (!sel || sel.isCollapsed || !sel.toString().trim()) {
          setTextSelection(null);
          setShowSelectionToolbar(false);
          return;
        }

        const text = sel.toString().trim();

        // 查找选区所在页码
        const anchorNode = sel.anchorNode;
        let pageEl = anchorNode?.parentElement;
        while (pageEl && !pageEl.dataset?.pageNumber) {
          pageEl = pageEl.parentElement;
        }
        const selPage = pageEl ? parseInt(pageEl.dataset.pageNumber || '1', 10) : pageNumber;

        if (selPage !== pageNumber) return;

        const range = sel.getRangeAt(0);
        const rects = Array.from(range.getClientRects());

        if (rects.length === 0) return;

        setTextSelection({ text, pageNumber: selPage, rects });

        // 计算工具栏位置：选区上方居中
        const firstRect = rects[0];
        const containerRect = overlayRef.current?.parentElement?.getBoundingClientRect();
        if (containerRect) {
          setToolbarPos({
            top: firstRect.top - containerRect.top - 44,
            left: firstRect.left - containerRect.left + firstRect.width / 2,
          });
        }
        setShowSelectionToolbar(true);
      }, 10);
    };

    const handleMouseDown = (e: MouseEvent) => {
      // 点击页面其他区域时关闭工具栏
      const target = e.target as HTMLElement;
      if (!target.closest('.selection-toolbar-popup')) {
        setShowSelectionToolbar(false);
      }
    };

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousedown', handleMouseDown);
    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, [isAnnotationMode, pageNumber]);

  // --- 从文本选择创建批注 ---
  const handleCreateFromSelection = useCallback(async (type: string, color: string) => {
    if (!textSelection || !pdfHash) return;

    const containerRect = overlayRef.current?.parentElement?.getBoundingClientRect();
    if (!containerRect) return;

    const pdfRects = textSelection.rects.map(r => ({
      x: (r.left - containerRect.left) / scale,
      y: (r.top - containerRect.top) / scale,
      width: r.width / scale,
      height: r.height / scale,
    }));

    const minX = Math.min(...pdfRects.map(r => r.x));
    const minY = Math.min(...pdfRects.map(r => r.y));
    const maxX = Math.max(...pdfRects.map(r => r.x + r.width));
    const maxY = Math.max(...pdfRects.map(r => r.y + r.height));

    await createAnnotation({
      pdf_hash: pdfHash,
      annotation_type: type as 'highlight' | 'underline' | 'strikethrough' | 'note',
      page: pageNumber,
      rect: [minX, minY, maxX, maxY],
      color,
      selected_text: textSelection.text,
      note: undefined,
      paper_id: undefined,
    });

    // 清除选择
    window.getSelection()?.removeAllRanges();
    setTextSelection(null);
    setShowSelectionToolbar(false);
  }, [textSelection, pdfHash, pageNumber, scale, createAnnotation]);

  // 当前页的批注
  const pageAnnotations = annotations.filter(a => a.page === pageNumber);

  // --- 拖拽绘制鼠标事件（仅标注模式） ---
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (!isAnnotationMode) return; // 非标注模式不拦截
    if (e.button !== 0) return;
    const rect = overlayRef.current?.getBoundingClientRect();
    if (!rect) return;
    setIsSelecting(true);
    setSelectionStart({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setSelectionEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }, [isAnnotationMode]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isSelecting) return;
    const rect = overlayRef.current?.getBoundingClientRect();
    if (!rect) return;
    setSelectionEnd({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  }, [isSelecting]);

  const handleMouseUp = useCallback(() => {
    if (!isSelecting || !selectionStart || !selectionEnd) {
      setIsSelecting(false);
      return;
    }

    const x0 = Math.min(selectionStart.x, selectionEnd.x) / scale;
    const y0 = Math.min(selectionStart.y, selectionEnd.y) / scale;
    const x1 = Math.max(selectionStart.x, selectionEnd.x) / scale;
    const y1 = Math.max(selectionStart.y, selectionEnd.y) / scale;

    if (Math.abs(x1 - x0) < 5 || Math.abs(y1 - y0) < 5) {
      setIsSelecting(false);
      setSelectionStart(null);
      setSelectionEnd(null);
      return;
    }

    if (annotationTool === 'eraser') {
      setIsSelecting(false);
      setSelectionStart(null);
      setSelectionEnd(null);
      return;
    }

    if (annotationTool) {
      const type = annotationTool as 'highlight' | 'underline' | 'note';
      const color = annotationColor;
      if (pdfHash) {
        createAnnotation({
          pdf_hash: pdfHash,
          annotation_type: type as 'highlight' | 'underline' | 'strikethrough' | 'note',
          page: pageNumber,
          rect: [x0, y0, x1, y1],
          color,
          selected_text: undefined,
          note: undefined,
          paper_id: undefined,
        });
      }
      setIsSelecting(false);
      setSelectionStart(null);
      setSelectionEnd(null);
      return;
    }

    setPendingRect([x0, y0, x1, y1]);
    setShowColorPicker(true);
    setIsSelecting(false);
    setSelectionStart(null);
    setSelectionEnd(null);
  }, [isSelecting, selectionStart, selectionEnd, scale, annotationTool, annotationColor, pdfHash, pageNumber, createAnnotation]);

  // 创建批注
  const handleCreateAnnotation = useCallback(async (type: string, color: string) => {
    if (!pendingRect || !pdfHash) return;
    await createAnnotation({
      pdf_hash: pdfHash,
      annotation_type: type as 'highlight' | 'underline' | 'strikethrough' | 'note',
      page: pageNumber,
      rect: pendingRect,
      color,
      selected_text: undefined,
      note: undefined,
      paper_id: undefined,
    });
    setShowColorPicker(false);
    setPendingRect(null);
  }, [pendingRect, pdfHash, pageNumber, createAnnotation]);

  // 渲染批注
  const renderAnnotation = (ann: AnnotationItem) => {
    if (!ann.rect || ann.rect.length !== 4) return null;

    const [x0, y0, x1, y1] = ann.rect;
    const left = x0 * scale;
    const top = y0 * scale;
    const width = (x1 - x0) * scale;
    const height = (y1 - y0) * scale;

    const isEditing = editingAnnotation === ann.id;

    const handleClick = () => {
      if (annotationTool === 'eraser') {
        deleteAnnotation(ann.id);
        return;
      }
      setEditingAnnotation(isEditing ? null : ann.id);
    };

    const style: React.CSSProperties = {
      position: 'absolute',
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      height: `${height}px`,
      cursor: 'pointer',
      transition: 'opacity 0.15s',
      pointerEvents: 'auto',
    };

    if (annotationTool === 'eraser') {
      return (
        <div
          key={ann.id}
          data-annotation-id={ann.id}
          style={{
            ...style,
            backgroundColor: 'rgba(244, 67, 54, 0.35)',
            border: '2px dashed #EF5350',
            borderRadius: '2px',
            zIndex: 35,
          }}
          onClick={handleClick}
          title="点击擦除此标注"
        />
      );
    }

    // 根据类型渲染不同样式
    switch (ann.annotation_type) {
      case 'highlight':
        return (
          <div
            key={ann.id}
            data-annotation-id={ann.id}
            style={{
              ...style,
              backgroundColor: ann.color + '66', // 40% opacity
              border: isEditing ? `2px solid ${ann.color}` : 'none',
              borderRadius: '2px',
            }}
            onClick={handleClick}
            title={ann.note || ann.selected_text || '高亮'}
          >
            {isEditing && (
              <AnnotationPopup
                annotation={ann}
                onClose={() => setEditingAnnotation(null)}
                onDelete={() => { deleteAnnotation(ann.id); setEditingAnnotation(null); }}
              />
            )}
          </div>
        );
      case 'underline':
        return (
          <div
            key={ann.id}
            data-annotation-id={ann.id}
            style={{
              ...style,
              borderBottom: `3px solid ${ann.color}`,
              backgroundColor: 'transparent',
            }}
            onClick={handleClick}
            title={ann.note || ann.selected_text || '下划线'}
          >
            {isEditing && (
              <AnnotationPopup
                annotation={ann}
                onClose={() => setEditingAnnotation(null)}
                onDelete={() => { deleteAnnotation(ann.id); setEditingAnnotation(null); }}
              />
            )}
          </div>
        );
      case 'strikethrough':
        return (
          <div
            key={ann.id}
            data-annotation-id={ann.id}
            style={{
              ...style,
              textDecoration: `line-through ${ann.color}`,
              backgroundColor: 'transparent',
              textDecorationThickness: '3px',
            }}
            onClick={handleClick}
            title={ann.note || ann.selected_text || '删除线'}
          >
            {isEditing && (
              <AnnotationPopup
                annotation={ann}
                onClose={() => setEditingAnnotation(null)}
                onDelete={() => { deleteAnnotation(ann.id); setEditingAnnotation(null); }}
              />
            )}
          </div>
        );
      case 'note':
        return (
          <div
            key={ann.id}
            data-annotation-id={ann.id}
            style={{
              ...style,
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: ann.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              color: '#fff',
              fontWeight: 'bold',
              boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
            }}
            onClick={handleClick}
            title={ann.note || '笔记'}
          >
            📝
            {isEditing && (
              <AnnotationPopup
                annotation={ann}
                onClose={() => setEditingAnnotation(null)}
                onDelete={() => { deleteAnnotation(ann.id); setEditingAnnotation(null); }}
              />
            )}
          </div>
        );
      default:
        return null;
    }
  };

  // 渲染选择框
  const renderSelection = () => {
    if (!isSelecting || !selectionStart || !selectionEnd) return null;
    const left = Math.min(selectionStart.x, selectionEnd.x);
    const top = Math.min(selectionStart.y, selectionEnd.y);
    const width = Math.abs(selectionEnd.x - selectionStart.x);
    const height = Math.abs(selectionEnd.y - selectionStart.y);
    return (
      <div
        style={{
          position: 'absolute',
          left, top, width, height,
          border: '2px dashed #42A5F5',
          backgroundColor: 'rgba(66, 165, 245, 0.15)',
          pointerEvents: 'none',
          zIndex: 100,
        }}
      />
    );
  };

  return (
    <div
      ref={overlayRef}
      className="annotation-overlay"
      style={{
        position: 'absolute',
        top: 0, left: 0,
        width: pageWidth * scale,
        height: pageHeight * scale,
        // 关键：批注层默认不拦截鼠标，让文本层可选中
        // 仅在标注模式激活时拦截拖拽
        pointerEvents: isAnnotationMode ? 'auto' : 'none',
        zIndex: isAnnotationMode ? 30 : 5,
        // 非标注模式时不影响文本选择
        userSelect: isAnnotationMode ? 'none' : 'text',
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* 渲染已有批注（始终可点击，pointer-events: auto） */}
      {pageAnnotations.map(renderAnnotation)}

      {/* 选择框（仅标注模式） */}
      {renderSelection()}

      {/* 文本选择浮动工具栏（非标注模式） */}
      {showSelectionToolbar && textSelection && !isAnnotationMode && (
        <div
          className="selection-toolbar-popup"
          style={{
            position: 'absolute',
            top: toolbarPos.top,
            left: toolbarPos.left,
            transform: 'translateX(-50%)',
            zIndex: 200,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            padding: '4px 6px',
            background: 'var(--bg-primary, #1e1e2e)',
            border: '1px solid var(--border-color, #444)',
            borderRadius: 8,
            boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
            pointerEvents: 'auto', // 工具栏自身需要点击
          }}
          onMouseDown={e => { e.preventDefault(); e.stopPropagation(); }} // 防止丢失选区
        >
          {/* 高亮颜色按钮 */}
          {HIGHLIGHT_COLORS.map(c => (
            <button
              key={c.value}
              onClick={() => handleCreateFromSelection('highlight', c.value)}
              title={`${c.name}高亮`}
              style={{
                width: 22, height: 22, borderRadius: '50%',
                backgroundColor: c.value, border: '2px solid transparent',
                cursor: 'pointer', transition: 'transform 0.1s',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.15)'; e.currentTarget.style.borderColor = '#fff'; }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.borderColor = 'transparent'; }}
            />
          ))}
          <div style={{ width: 1, height: 18, background: 'var(--hairline, #444)', margin: '0 2px' }} />
          {/* 下划线 */}
          <button
            onClick={() => handleCreateFromSelection('underline', '#42A5F5')}
            title="下划线"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 22, borderRadius: 4, border: 'none',
              background: 'var(--accent-bg-soft, rgba(66,165,245,0.1))',
              cursor: 'pointer', color: 'var(--accent, #42A5F5)',
              borderBottom: '3px solid #42A5F5', fontWeight: 'bold', fontSize: 11,
            }}
          >U</button>
          {/* 复制 */}
          <button
            onClick={() => {
              navigator.clipboard.writeText(textSelection.text);
              setShowSelectionToolbar(false);
            }}
            title="复制文本"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 22, borderRadius: 4, border: 'none',
              background: 'var(--accent-bg-soft, rgba(66,165,245,0.1))',
              cursor: 'pointer', color: 'var(--body)', fontSize: 11,
            }}
          >📋</button>
          {/* 翻译 */}
          <button
            onClick={() => {
              window.open(`https://translate.google.com/?sl=auto&tl=zh-CN&text=${encodeURIComponent(textSelection.text)}&op=translate`, '_blank');
              setShowSelectionToolbar(false);
            }}
            title="翻译选中文本"
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 22, borderRadius: 4, border: 'none',
              background: 'var(--accent-bg-soft, rgba(66,165,245,0.1))',
              cursor: 'pointer', color: 'var(--accent, #42A5F5)', fontSize: 11,
              fontWeight: 600,
            }}
          >译</button>
        </div>
      )}

      {/* 颜色选择器（拖拽模式） */}
      {showColorPicker && pendingRect && (
        <div
          style={{
            position: 'absolute',
            left: pendingRect[0] * scale,
            top: (pendingRect[3] * scale) + 8,
            zIndex: 200,
            background: 'var(--bg-primary, #1e1e2e)',
            border: '1px solid var(--border-color, #333)',
            borderRadius: '8px',
            padding: '8px',
            display: 'flex',
            gap: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
          }}
        >
          {HIGHLIGHT_COLORS.map(c => (
            <div
              key={c.value}
              onClick={() => handleCreateAnnotation('highlight', c.value)}
              style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                backgroundColor: c.value,
                cursor: 'pointer',
                border: '2px solid transparent',
              }}
              title={c.name}
              onMouseEnter={e => (e.currentTarget.style.border = '2px solid white')}
              onMouseLeave={e => (e.currentTarget.style.border = '2px solid transparent')}
            />
          ))}
          <div
            onClick={() => handleCreateAnnotation('underline', '#42A5F5')}
            style={{
              width: '24px', height: '24px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', fontSize: '14px',
              borderBottom: '3px solid #42A5F5',
            }}
            title="下划线"
          >
            U̲
          </div>
          <div
            onClick={() => handleCreateAnnotation('note', '#FFA726')}
            style={{
              width: '24px', height: '24px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', fontSize: '14px',
              backgroundColor: '#FFA726', borderRadius: '50%',
              color: 'white', fontWeight: 'bold',
            }}
            title="文本批注"
          >
            📝
          </div>
        </div>
      )}
    </div>
  );
};

// ==================== Annotation Popup ====================

interface AnnotationPopupProps {
  annotation: AnnotationItem;
  onClose: () => void;
  onDelete: () => void;
}

const AnnotationPopup: React.FC<AnnotationPopupProps> = ({ annotation, onClose, onDelete }) => {
  const [noteText, setNoteText] = useState(annotation.note || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    if (noteText === annotation.note) { onClose(); return; }
    setIsSaving(true);
    try {
      await annotationsApi.update(annotation.id, { note: noteText });
    } catch { /* ignore */ }
    setIsSaving(false);
    onClose();
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: '100%',
        left: 0,
        marginTop: '4px',
        minWidth: '200px',
        background: 'var(--bg-primary, #1e1e2e)',
        border: '1px solid var(--border-color, #444)',
        borderRadius: '8px',
        padding: '8px',
        zIndex: 300,
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
        pointerEvents: 'auto',
      }}
      onClick={e => e.stopPropagation()}
    >
      {annotation.selected_text && (
        <div style={{
          fontSize: '11px', color: '#aaa', marginBottom: '4px',
          padding: '4px', background: 'rgba(255,255,255,0.05)',
          borderRadius: '4px', maxHeight: '60px', overflow: 'auto',
        }}>
          {annotation.selected_text}
        </div>
      )}
      <textarea
        value={noteText}
        onChange={e => setNoteText(e.target.value)}
        placeholder="添加备注..."
        style={{
          width: '100%', minHeight: '50px',
          background: 'var(--bg-secondary, #2a2a3e)',
          color: 'var(--text-primary, #e0e0e0)',
          border: '1px solid var(--border-color, #444)',
          borderRadius: '4px', padding: '6px',
          fontSize: '12px', resize: 'vertical',
        }}
      />
      <div style={{ display: 'flex', gap: '4px', marginTop: '6px', justifyContent: 'flex-end' }}>
        <button
          onClick={onDelete}
          style={{
            padding: '3px 8px', fontSize: '11px',
            background: '#EF5350', color: 'white',
            border: 'none', borderRadius: '4px', cursor: 'pointer',
          }}
        >
          删除
        </button>
        <button
          onClick={onClose}
          style={{
            padding: '3px 8px', fontSize: '11px',
            background: '#555', color: 'white',
            border: 'none', borderRadius: '4px', cursor: 'pointer',
          }}
        >
          取消
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving}
          style={{
            padding: '3px 8px', fontSize: '11px',
            background: '#42A5F5', color: 'white',
            border: 'none', borderRadius: '4px', cursor: 'pointer',
          }}
        >
          {isSaving ? '...' : '保存'}
        </button>
      </div>
    </div>
  );
};

export default AnnotationOverlay;
