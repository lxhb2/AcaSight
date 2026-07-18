/**
 * AnnotationSidebar — 标注侧边栏
 *
 * 参考 Readest 的 Notebook + AnnotationNotes：
 * - 按颜色分类
 * - 搜索过滤
 * - 点击跳转到对应页面
 * - 删除标注
 * - 颜色筛选器
 */

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import {
  Search, Trash2, Highlighter, BookOpen, X, Pencil, StickyNote, Check,
} from 'lucide-react';

interface HighlightAnnotation {
  id: string;
  text: string;
  pageNumber: number;
  color: string;
  rect?: { top: number; right: number; bottom: number; left: number };
  note?: string;
  createdAt: number;
}

interface AnnotationSidebarProps {
  highlights: HighlightAnnotation[];
  onJumpTo: (pageNumber: number, id: string) => void;
  onDelete: (id: string) => void;
  /** 进入"编辑已有标注"态（让 Annotator 显示编辑工具栏） */
  onEdit?: (id: string) => void;
  /** 更新标注笔记（侧边栏内联编辑） */
  onUpdateNote?: (id: string, note: string) => void;
  selectedId: string | null;
}

const COLOR_FILTERS = [
  { key: 'all', label: '全部', color: 'var(--body, #ddd)' },
  { key: '#FFD700', label: '核心', color: '#FFD700' },
  { key: '#4CAF50', label: '方法', color: '#4CAF50' },
  { key: '#2196F3', label: '存疑', color: '#2196F3' },
  { key: '#E91E63', label: '重要', color: '#E91E63' },
];

export const AnnotationSidebar: React.FC<AnnotationSidebarProps> = ({
  highlights, onJumpTo, onDelete, onEdit, onUpdateNote, selectedId,
}) => {
  const [search, setSearch] = useState('');
  const [colorFilter, setColorFilter] = useState('all');
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNote, setEditingNote] = useState('');
  const noteInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editingNoteId && noteInputRef.current) {
      noteInputRef.current.focus();
      noteInputRef.current.setSelectionRange(
        noteInputRef.current.value.length,
        noteInputRef.current.value.length,
      );
    }
  }, [editingNoteId]);

  const beginEditNote = useCallback((id: string, current: string) => {
    setEditingNoteId(id);
    setEditingNote(current ?? '');
  }, []);

  const commitEditNote = useCallback(() => {
    if (!editingNoteId) return;
    onUpdateNote?.(editingNoteId, editingNote);
    setEditingNoteId(null);
    setEditingNote('');
  }, [editingNoteId, editingNote, onUpdateNote]);

  const cancelEditNote = useCallback(() => {
    setEditingNoteId(null);
    setEditingNote('');
  }, []);

  const filtered = useMemo(() => {
    const noteHit = (h: HighlightAnnotation) =>
      !search ||
      h.text.toLowerCase().includes(search.toLowerCase()) ||
      (h.note ?? '').toLowerCase().includes(search.toLowerCase());
    return highlights
      .filter(h => colorFilter === 'all' || h.color === colorFilter)
      .filter(noteHit)
      .sort((a, b) => b.createdAt - a.createdAt);
  }, [highlights, search, colorFilter]);

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div style={{
        padding: '10px 12px', fontSize: 12, fontWeight: 600,
        color: 'var(--mute, #888)', borderBottom: '1px solid var(--hairline, #333)',
        textTransform: 'uppercase', letterSpacing: 0.5,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span>标注列表</span>
        <span style={{ fontSize: 11, color: 'var(--mute, #666)' }}>
          {highlights.length} 条
        </span>
      </div>

      {/* Search */}
      <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline, #333)' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6, padding: '4px 8px',
          borderRadius: 6, background: 'var(--bg-primary, #0f0f11)',
          border: '1px solid var(--hairline, #333)',
        }}>
          <Search size={13} style={{ color: 'var(--mute, #666)', flexShrink: 0 }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="搜索标注..."
            style={{
              flex: 1, border: 'none', background: 'transparent',
              fontSize: 12, color: 'var(--body, #ddd)', outline: 'none',
            }}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                color: 'var(--mute, #666)',
              }}
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Color filters */}
      <div style={{
        display: 'flex', gap: 4, padding: '6px 10px',
        borderBottom: '1px solid var(--hairline, #333)', flexWrap: 'wrap',
      }}>
        {COLOR_FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setColorFilter(f.key)}
            style={{
              padding: '2px 8px', borderRadius: 12, fontSize: 10, fontWeight: 500,
              border: colorFilter === f.key
                ? `1px solid ${f.color}`
                : '1px solid transparent',
              background: colorFilter === f.key
                ? `${f.color}15`
                : 'var(--bg-primary, #0f0f11)',
              color: colorFilter === f.key ? f.color : 'var(--mute, #888)',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
          >
            {f.key !== 'all' && (
              <span style={{
                display: 'inline-block', width: 8, height: 8, borderRadius: 2,
                background: f.color, marginRight: 4, verticalAlign: 'middle',
              }} />
            )}
            {f.label}
          </button>
        ))}
      </div>

      {/* Annotation list */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {filtered.length === 0 ? (
          <div style={{
            padding: 32, textAlign: 'center', color: 'var(--mute, #888)', fontSize: 12,
          }}>
            <Highlighter size={24} style={{ margin: '0 auto 8px', opacity: 0.3 }} />
            <p>{highlights.length === 0 ? '暂无标注' : '无匹配标注'}</p>
            <p style={{ fontSize: 10, marginTop: 4 }}>
              {highlights.length === 0 ? '选中文字后点击高亮按钮添加' : '尝试更改筛选条件'}
            </p>
          </div>
        ) : (
          filtered.map(hl => (
            <div
              key={hl.id}
              onClick={() => onJumpTo(hl.pageNumber, hl.id)}
              onMouseEnter={() => setHoverId(hl.id)}
              onMouseLeave={() => setHoverId(null)}
              style={{
                padding: '10px 12px', cursor: 'pointer',
                borderBottom: '1px solid var(--hairline, #222)',
                borderLeft: `3px solid ${hl.color}`,
                background: selectedId === hl.id
                  ? 'var(--accent-bg-soft, rgba(99,102,241,0.06))'
                  : hoverId === hl.id
                    ? 'var(--hover, rgba(255,255,255,0.03))'
                    : 'transparent',
                transition: 'background 0.1s',
              }}
            >
              {/* 文字高亮预览 */}
              <div style={{
                fontSize: 12, color: 'var(--body, #ccc)', lineHeight: 1.5,
                display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical',
                overflow: 'hidden', marginBottom: 4,
              }}>
                {hl.text}
              </div>

              {/* 笔记区（点击内联编辑） */}
              {editingNoteId === hl.id ? (
                <div
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    display: 'flex', flexDirection: 'column', gap: 4,
                    margin: '4px 0 6px',
                    padding: 6, borderRadius: 6,
                    background: 'var(--bg-primary, #0f0f11)',
                    border: '1px solid var(--hairline, #333)',
                  }}
                >
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    color: 'var(--mute, #888)', fontSize: 10, fontWeight: 600,
                  }}>
                    <StickyNote size={10} /> 笔记
                  </div>
                  <textarea
                    ref={noteInputRef}
                    value={editingNote}
                    onChange={(e) => setEditingNote(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) commitEditNote();
                      if (e.key === 'Escape') cancelEditNote();
                    }}
                    rows={3}
                    placeholder="写下你的笔记..."
                    style={{
                      width: '100%', boxSizing: 'border-box',
                      background: 'transparent', border: 'none', outline: 'none',
                      color: 'var(--body, #e0e0e0)', fontSize: 11, resize: 'vertical',
                      fontFamily: 'inherit', minHeight: 48,
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 4 }}>
                    <button
                      onClick={cancelEditNote}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 3,
                        padding: '2px 6px', fontSize: 10, borderRadius: 4,
                        background: 'transparent', border: '1px solid var(--hairline, #333)',
                        color: 'var(--mute, #888)', cursor: 'pointer',
                      }}
                    >
                      取消
                    </button>
                    <button
                      onClick={commitEditNote}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 3,
                        padding: '2px 6px', fontSize: 10, borderRadius: 4,
                        background: 'var(--accent, #6366f1)',
                        color: '#fff', border: 'none', cursor: 'pointer',
                      }}
                    >
                      <Check size={10} /> 保存
                    </button>
                  </div>
                </div>
              ) : hl.note ? (
                <div
                  onClick={(e) => {
                    e.stopPropagation();
                    beginEditNote(hl.id, hl.note ?? '');
                  }}
                  style={{
                    fontSize: 11, color: 'var(--body, #bbb)', lineHeight: 1.5,
                    padding: '4px 6px', margin: '2px 0 4px',
                    borderRadius: 4,
                    background: 'var(--bg-primary, #0f0f11)',
                    borderLeft: `2px solid ${hl.color}`,
                    cursor: 'text', fontStyle: 'italic',
                    whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  }}
                  title="点击编辑笔记"
                >
                  {hl.note}
                </div>
              ) : (
                hoverId === hl.id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      beginEditNote(hl.id, '');
                    }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 3,
                      padding: '2px 6px', fontSize: 10, borderRadius: 4,
                      background: 'transparent',
                      border: '1px dashed var(--hairline, #333)',
                      color: 'var(--mute, #666)', cursor: 'pointer',
                      margin: '2px 0 4px',
                    }}
                  >
                    <StickyNote size={10} /> 添加笔记
                  </button>
                )
              )}

              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <span style={{ fontSize: 10, color: 'var(--mute, #666)' }}>
                  <BookOpen size={10} style={{ marginRight: 2, display: 'inline' }} />
                  第 {hl.pageNumber} 页 · {formatTime(hl.createdAt)}
                </span>
                {hoverId === hl.id && (
                  <div style={{ display: 'flex', gap: 2 }} onClick={(e) => e.stopPropagation()}>
                    {onEdit && (
                      <button
                        onClick={() => onEdit(hl.id)}
                        style={{
                          background: 'none', border: 'none', padding: 2, cursor: 'pointer',
                          color: 'var(--mute, #666)', borderRadius: 4,
                        }}
                        title="在 PDF 中编辑"
                      >
                        <Pencil size={12} />
                      </button>
                    )}
                    <button
                      onClick={() => onDelete(hl.id)}
                      style={{
                        background: 'none', border: 'none', padding: 2, cursor: 'pointer',
                        color: 'var(--mute, #666)', borderRadius: 4,
                      }}
                      title="删除标注"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AnnotationSidebar;
