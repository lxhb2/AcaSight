/**
 * AnnotationOverlay — PDF 批注叠加层 v3.0
 *
 * 精简版：仅负责渲染已有批注（高亮、下划线、删除线、文本批注）。
 * 文字选择、工具栏、翻译已迁移至 Annotator 组件。
 *
 * 关键设计：
 * - 批注层默认 pointer-events: none，不阻碍文本选择
 * - 仅批注元素自身可点击 (pointer-events: auto)
 */

import React, { useState } from 'react';
import { useApp } from '@/contexts/AppContext';
import type { AnnotationItem } from '@/services/api';
import { annotationsApi } from '@/services/api';

interface AnnotationOverlayProps {
  pageNumber: number;
  pageWidth: number;
  pageHeight: number;
  scale: number;
}

const AnnotationOverlay: React.FC<AnnotationOverlayProps> = ({
  pageNumber,
  pageWidth,
  pageHeight,
  scale,
}) => {
  const { annotations, deleteAnnotation } = useApp();
  const [editingAnnotation, setEditingAnnotation] = useState<number | null>(null);

  // 当前页的批注
  const pageAnnotations = annotations.filter(a => a.page === pageNumber);

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

    switch (ann.annotation_type) {
      case 'highlight':
        return (
          <div
            key={ann.id}
            data-annotation-id={ann.id}
            style={{
              ...style,
              backgroundColor: ann.color + '66',
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

  return (
    <div
      className="annotation-overlay"
      style={{
        position: 'absolute',
        top: 0, left: 0,
        width: pageWidth * scale,
        height: pageHeight * scale,
        pointerEvents: 'none',
        zIndex: 5,
        userSelect: 'none',
      }}
    >
      {pageAnnotations.map(renderAnnotation)}
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