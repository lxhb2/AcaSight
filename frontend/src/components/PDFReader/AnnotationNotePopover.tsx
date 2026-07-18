/**
 * AnnotationNotePopover — 标注便签编辑器
 *
 * 借鉴 Readest 的 AnnotationNotes 简化版：
 * - 单行 textarea + 保存/取消
 * - 锚定到选区上方
 * - Esc 关闭，Ctrl+Enter 保存
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Check, X, StickyNote } from 'lucide-react';
import type { Position } from '@/utils/sel';

interface AnnotationNotePopoverProps {
  anchorPosition: Position;
  initialNote?: string;
  onSave: (note: string) => void;
  onDismiss: () => void;
}

const POPUP_W = 320;
const POPUP_H = 180;

export const AnnotationNotePopover: React.FC<AnnotationNotePopoverProps> = ({
  anchorPosition,
  initialNote = '',
  onSave,
  onDismiss,
}) => {
  const [note, setNote] = useState(initialNote);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
    textareaRef.current?.select();
  }, []);

  // 关闭交互
  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onDismiss();
      }
    };
    setTimeout(() => document.addEventListener('mousedown', onClickOutside), 60);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, [onDismiss]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') onSave(note);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [note, onSave, onDismiss]);

  const handleSave = useCallback(() => {
    onSave(note);
  }, [note, onSave]);

  return (
    <div
      ref={popoverRef}
      className="annotation-note-popover"
      style={{
        position: 'fixed',
        left: anchorPosition.point.x,
        top: anchorPosition.point.y,
        zIndex: 10002,
        width: POPUP_W,
        background: 'var(--canvas, #1e1e2e)',
        border: '1px solid var(--hairline, #333)',
        borderRadius: 12,
        boxShadow: '0 16px 48px rgba(0,0,0,0.4)',
        padding: 10,
        transform: anchorPosition.dir === 'up'
          ? `translate(-50%, calc(-100% - 12px))`
          : `translate(-50%, 12px)`,
        display: 'flex', flexDirection: 'column', gap: 8,
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <StickyNote size={13} style={{ color: 'var(--accent, #6366f1)' }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body, #ddd)' }}>添加笔记</span>
      </div>
      <textarea
        ref={textareaRef}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="输入笔记内容（可选）"
        rows={5}
        style={{
          width: '100%', boxSizing: 'border-box',
          background: 'var(--bg-primary, #0f0f11)',
          color: 'var(--body, #e0e0e0)',
          border: '1px solid var(--hairline, #333)',
          borderRadius: 8, padding: '6px 8px', fontSize: 12,
          fontFamily: 'inherit', resize: 'vertical', minHeight: 80,
          outline: 'none',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
        <button
          onClick={onDismiss}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', fontSize: 12, borderRadius: 6,
            background: 'transparent', border: '1px solid var(--hairline, #333)',
            color: 'var(--mute, #888)', cursor: 'pointer',
          }}
        >
          <X size={12} /> 取消
        </button>
        <button
          onClick={handleSave}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', fontSize: 12, borderRadius: 6,
            background: 'var(--accent, #6366f1)',
            color: '#fff', border: 'none', cursor: 'pointer',
          }}
        >
          <Check size={12} /> 保存
        </button>
      </div>
    </div>
  );
};

export default AnnotationNotePopover;
