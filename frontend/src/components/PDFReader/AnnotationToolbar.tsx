/**
 * AnnotationToolbar — 选中文字操作工具栏
 *
 * 借鉴 Readest 的 AnnotationPopup + HighlightOptions：
 * - 一行操作按钮 + 内联 4 色高亮选择器
 * - 选中即出现，Esc/外部点击关闭
 * - 支持"已有高亮"切换（显示当前颜色 + 取消按钮）
 * - 编辑模式下显示删除按钮
 */

import React, { useEffect, useRef, useCallback, useState } from 'react';
import {
  Copy, Check, Highlighter, Languages, Search, Volume2, Trash2, StickyNote, X,
} from 'lucide-react';
import type { Position } from '@/utils/sel';
import { HIGHLIGHT_COLORS, type HighlightColorKey } from './Annotator';

interface AnnotationToolbarProps {
  anchorPosition: Position;
  onDismiss: () => void;
  onCopy: () => void;
  onTranslate: () => void;
  onPickColor: (colorKey: HighlightColorKey) => void;
  onAddNote?: () => void;
  onSearch?: () => void;
  onSpeak?: () => void;
  onDelete?: () => void;
  /** 当前编辑态选中的颜色（编辑模式 / 已有高亮时） */
  editingColor?: HighlightColorKey;
  /** 新建时默认高亮色（无则不预选） */
  defaultColor?: HighlightColorKey;
  hasHighlight?: boolean;
  isEdit?: boolean;
}

const BUTTON_W = 32;

export const AnnotationToolbar: React.FC<AnnotationToolbarProps> = ({
  anchorPosition,
  onDismiss,
  onCopy,
  onTranslate,
  onPickColor,
  onAddNote,
  onSearch,
  onSpeak,
  onDelete,
  editingColor,
  defaultColor,
  hasHighlight,
  isEdit,
}) => {
  const toolbarRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [hoverColor, setHoverColor] = useState<HighlightColorKey | null>(null);

  const handleCopy = useCallback(() => {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [onCopy]);

  // Click outside to dismiss
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (toolbarRef.current && !toolbarRef.current.contains(e.target as Node)) {
        onDismiss();
      }
    };
    setTimeout(() => document.addEventListener('mousedown', handler), 100);
    return () => document.removeEventListener('mousedown', handler);
  }, [onDismiss]);

  // Esc 关闭（已由 hook 处理；此处保留以防双绑）
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onDismiss]);

  // 计算尺寸
  const leftButtons = [
    { id: 'copy', label: copied ? '已复制' : '复制', icon: copied ? Check : Copy, onClick: handleCopy },
    ...(onAddNote ? [{ id: 'note', label: '笔记', icon: StickyNote, onClick: onAddNote }] : []),
    { id: 'translate', label: '翻译', icon: Languages, onClick: onTranslate },
    ...(onSearch ? [{ id: 'search', label: '搜索', icon: Search, onClick: onSearch }] : []),
    ...(onSpeak ? [{ id: 'speak', label: '朗读', icon: Volume2, onClick: onSpeak }] : []),
  ];
  const rightButtons = isEdit && onDelete
    ? [{ id: 'delete', label: '删除', icon: Trash2, onClick: onDelete, danger: true }]
    : [];

  // 总宽度
  const dividerW = 8;
  const colorStripW = HIGHLIGHT_COLORS.length * 24;
  const leftW = leftButtons.length * BUTTON_W;
  const rightW = rightButtons.length * BUTTON_W;
  const totalW = leftW + (rightW ? dividerW + rightW : 0) + (colorStripW ? dividerW + colorStripW : 0) + 16;

  // 居中到锚点
  let popupX = anchorPosition.point.x - totalW / 2;
  const popupY = anchorPosition.point.y;
  popupX = Math.max(8, Math.min(popupX, window.innerWidth - totalW - 8));

  // 当前应高亮的颜色（编辑 / 已有标注 → editingColor；新建 → defaultColor）
  const currentColor: HighlightColorKey | undefined = hasHighlight
    ? editingColor ?? (defaultColor ?? 'yellow')
    : editingColor ?? defaultColor;

  return (
    <div
      ref={toolbarRef}
      className="annotation-toolbar"
      style={{
        position: 'fixed',
        left: popupX,
        top: popupY,
        zIndex: 10001,
        display: 'flex', alignItems: 'center',
        padding: 4,
        background: 'var(--canvas, #1e1e2e)',
        border: '1px solid var(--hairline, #333)',
        borderRadius: 10,
        boxShadow: '0 8px 24px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.05)',
        transform: anchorPosition.dir === 'up' ? 'translateY(-100%)' : undefined,
      }}
    >
      {/* 左侧操作按钮 */}
      <div style={{ display: 'flex', alignItems: 'center' }}>
        {leftButtons.map((btn) => (
          <ToolbarIconBtn
            key={btn.id}
            label={btn.label}
            Icon={btn.icon}
            onClick={btn.onClick}
          />
        ))}
      </div>

      {/* 颜色分隔 */}
      {colorStripW > 0 && (
        <div style={{
          width: 1, height: 20, margin: '0 6px',
          background: 'var(--hairline, #333)',
        }} />
      )}

      {/* 4 色高亮选择器 */}
      {colorStripW > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Highlighter
            size={13}
            style={{ color: 'var(--mute, #888)', marginRight: 4, marginLeft: 2 }}
          />
          {HIGHLIGHT_COLORS.map((c) => {
            const active = currentColor === c.key;
            return (
              <button
                key={c.key}
                onClick={() => onPickColor(c.key)}
                onMouseEnter={() => setHoverColor(c.key)}
                onMouseLeave={() => setHoverColor(null)}
                title={c.label}
                style={{
                  width: 22, height: 22, borderRadius: '50%',
                  background: c.hex,
                  border: active
                    ? '2px solid var(--body, #fff)'
                    : '2px solid transparent',
                  outline: hoverColor === c.key ? '2px solid var(--accent, #6366f1)' : 'none',
                  outlineOffset: 1,
                  cursor: 'pointer', padding: 0,
                  transition: 'transform 0.1s, outline 0.1s',
                  transform: hoverColor === c.key ? 'scale(1.1)' : 'scale(1)',
                  boxShadow: active ? '0 0 0 1px rgba(0,0,0,0.3)' : undefined,
                }}
              />
            );
          })}
          {hasHighlight && (
            <button
              onClick={onDismiss}
              title="取消高亮"
              style={{
                width: 22, height: 22, borderRadius: '50%',
                background: 'transparent',
                border: '1px dashed var(--hairline, #555)',
                color: 'var(--mute, #888)',
                cursor: 'pointer', padding: 0, marginLeft: 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>
      )}

      {/* 删除按钮分隔 */}
      {rightW > 0 && (
        <div style={{
          width: 1, height: 20, margin: '0 6px',
          background: 'var(--hairline, #333)',
        }} />
      )}

      {/* 删除按钮（编辑模式） */}
      {rightButtons.map((btn) => (
        <ToolbarIconBtn
          key={btn.id}
          label={btn.label}
          Icon={btn.icon}
          onClick={btn.onClick}
          danger
        />
      ))}

      {/* 三角指示器 */}
      <div
        style={{
          position: 'absolute',
          ...(anchorPosition.dir === 'up'
            ? { bottom: -6, borderTop: '6px solid var(--canvas, #1e1e2e)' }
            : { top: -6, borderBottom: '6px solid var(--canvas, #1e1e2e)' }),
          left: Math.max(8, Math.min(anchorPosition.point.x - popupX, totalW - 8)) - 6,
          borderLeft: '6px solid transparent',
          borderRight: '6px solid transparent',
        }}
      />
    </div>
  );
};

const ToolbarIconBtn: React.FC<{
  label: string;
  Icon: React.ElementType;
  onClick: () => void;
  danger?: boolean;
}> = ({ label, Icon, onClick, danger }) => {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      title={label}
      aria-label={label}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: BUTTON_W, height: 28, borderRadius: 6, border: 'none',
        background: 'transparent',
        color: danger
          ? (hover ? '#ef4444' : 'var(--mute, #888)')
          : (hover ? 'var(--accent, #6366f1)' : 'var(--mute, #888)'),
        cursor: 'pointer', padding: 0,
        transition: 'color 0.12s, background 0.12s',
      }}
    >
      <Icon size={15} />
    </button>
  );
};

export default AnnotationToolbar;
