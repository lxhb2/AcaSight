/**
 * OutlineEditor — 大纲编辑器
 * 
 * 功能：
 * - 可视化大纲展示（层级缩进 + 编号）
 * - 拖拽排序（上下移动按钮代替 HTML5 drag，更稳定）
 * - 增删改（添加/删除章节 + 编辑标题/描述）
 * - 确认大纲 → 传递回父组件
 */

import React, { useState } from 'react';
import {
  Plus, Trash2, Edit3, Check, X,
  ChevronUp, ChevronDown, ListTree,
} from 'lucide-react';

export interface OutlineItem {
  level: number;
  title: string;
  estimated_words?: number;
  description?: string;
  sections?: OutlineItem[];
}

interface OutlineEditorProps {
  outline: OutlineItem[];
  onChange: (outline: OutlineItem[]) => void;
  onConfirm: () => void;
  title: string;
}

export const OutlineEditor: React.FC<OutlineEditorProps> = ({ outline, onChange, onConfirm, title }) => {
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');

  const updateNode = (items: OutlineItem[], path: number[], updater: (item: OutlineItem) => OutlineItem): OutlineItem[] => {
    return items.map((item, i) => {
      if (i === path[0]) {
        if (path.length === 1) return updater(item);
        return { ...item, sections: updateNode(item.sections || [], path.slice(1), updater) };
      }
      return item;
    });
  };

  const removeNode = (items: OutlineItem[], path: number[]): OutlineItem[] => {
    return items.filter((_, i) => i !== path[0]).map((item, i) => {
      if (i === path[0] || (path.length > 1 && i === path[0])) {
        if (path.length === 1) return item; // already filtered
        return { ...item, sections: removeNode(item.sections || [], path.slice(1)) };
      }
      return item;
    });
  };

  // Actually, removeNode logic above is flawed. Let me rewrite:
  const removeAtPath = (items: OutlineItem[], path: number[]): OutlineItem[] => {
    if (path.length === 1) return items.filter((_, i) => i !== path[0]);
    return items.map((item, i) => {
      if (i === path[0]) return { ...item, sections: removeAtPath(item.sections || [], path.slice(1)) };
      return item;
    });
  };

  const insertAfter = (items: OutlineItem[], path: number[]): OutlineItem[] => {
    if (path.length === 1) {
      const newItem: OutlineItem = { level: items[path[0]]?.level || 1, title: '新章节', estimated_words: 500 };
      return [...items.slice(0, path[0] + 1), newItem, ...items.slice(path[0] + 1)];
    }
    return items.map((item, i) => {
      if (i === path[0]) return { ...item, sections: insertAfter(item.sections || [], path.slice(1)) };
      return item;
    });
  };

  const moveNode = (items: OutlineItem[], path: number[], direction: 'up' | 'down'): OutlineItem[] => {
    if (path.length === 1) {
      const idx = path[0];
      const swapIdx = direction === 'up' ? idx - 1 : idx + 1;
      if (swapIdx < 0 || swapIdx >= items.length) return items;
      const newItems = [...items];
      [newItems[idx], newItems[swapIdx]] = [newItems[swapIdx], newItems[idx]];
      return newItems;
    }
    return items.map((item, i) => {
      if (i === path[0]) return { ...item, sections: moveNode(item.sections || [], path.slice(1), direction) };
      return item;
    });
  };

  const startEdit = (path: string, item: OutlineItem) => {
    setEditingKey(path);
    setEditTitle(item.title);
    setEditDesc(item.description || '');
  };

  const confirmEdit = (path: number[]) => {
    onChange(updateNode(outline, path, item => ({ ...item, title: editTitle, description: editDesc || undefined })));
    setEditingKey(null);
  };

  const LEVEL_NUMS = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十'];

  const renderItems = (items: OutlineItem[], path: number[] = []) => {
    return items.map((item, i) => {
      const currentPath = [...path, i];
      const pathStr = currentPath.join('.');
      const isEditing = editingKey === pathStr;
      const isFirst = i === 0;
      const isLast = i === items.length - 1;

      return (
        <div key={pathStr} style={{ marginBottom: 6 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 10px', borderRadius: 6,
            border: isEditing ? '1px solid var(--accent, #6366f1)' : '1px solid var(--border-color)',
            background: isEditing ? 'rgba(99,102,241,0.05)' : item.level === 1 ? 'var(--bg-secondary, #f8fafc)' : 'transparent',
            transition: 'all 0.15s',
          }}>
            {/* Move buttons */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <button onClick={() => onChange(moveNode(outline, currentPath, 'up'))} disabled={isFirst}
                style={{ padding: 0, border: 'none', background: 'transparent', cursor: isFirst ? 'default' : 'pointer', color: isFirst ? 'transparent' : 'var(--muted)', lineHeight: 1 }}>
                <ChevronUp size={12} />
              </button>
              <button onClick={() => onChange(moveNode(outline, currentPath, 'down'))} disabled={isLast}
                style={{ padding: 0, border: 'none', background: 'transparent', cursor: isLast ? 'default' : 'pointer', color: isLast ? 'transparent' : 'var(--muted)', lineHeight: 1 }}>
                <ChevronDown size={12} />
              </button>
            </div>

            {/* Level indicator */}
            <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 600, minWidth: 16 }}>
              {item.level === 1 ? (LEVEL_NUMS[i] || i + 1) : `${path[path.length - 1] + 1}.${i + 1}`}
            </span>

            {/* Title */}
            {isEditing ? (
              <input value={editTitle} onChange={e => setEditTitle(e.target.value)}
                style={{ flex: 1, padding: '2px 6px', border: '1px solid var(--accent)', borderRadius: 4, fontSize: 13, fontWeight: item.level === 1 ? 600 : 500, outline: 'none', background: 'var(--bg-primary)' }}
                onKeyDown={e => { if (e.key === 'Enter') confirmEdit(currentPath); if (e.key === 'Escape') setEditingKey(null); }} />
            ) : (
              <span style={{ flex: 1, fontSize: item.level === 1 ? 14 : 13, fontWeight: item.level === 1 ? 600 : 500, color: 'var(--ink)' }}>
                {item.title}
              </span>
            )}

            {/* Word count */}
            {item.estimated_words && <span style={{ fontSize: 10, color: 'var(--muted)' }}>~{item.estimated_words}字</span>}

            {/* Actions */}
            {isEditing ? (
              <>
                <button onClick={() => confirmEdit(currentPath)} style={{ padding: 2, border: 'none', background: 'transparent', color: '#10b981', cursor: 'pointer' }}><Check size={14} /></button>
                <button onClick={() => setEditingKey(null)} style={{ padding: 2, border: 'none', background: 'transparent', color: '#ef4444', cursor: 'pointer' }}><X size={14} /></button>
              </>
            ) : (
              <>
                <button onClick={() => startEdit(pathStr, item)} style={{ padding: 2, border: 'none', background: 'transparent', color: 'var(--muted)', cursor: 'pointer' }}><Edit3 size={12} /></button>
                <button onClick={() => onChange(insertAfter(outline, currentPath))} style={{ padding: 2, border: 'none', background: 'transparent', color: 'var(--muted)', cursor: 'pointer' }}><Plus size={12} /></button>
                <button onClick={() => onChange(removeAtPath(outline, currentPath))} style={{ padding: 2, border: 'none', background: 'transparent', color: 'var(--muted)', cursor: 'pointer' }}><Trash2 size={12} /></button>
              </>
            )}
          </div>

          {/* Description */}
          {isEditing && (
            <div style={{ marginLeft: 40, marginTop: 4 }}>
              <input value={editDesc} onChange={e => setEditDesc(e.target.value)} placeholder="章节描述（可选）"
                style={{ width: '100%', padding: '4px 8px', border: '1px solid var(--border-color)', borderRadius: 4, fontSize: 12, color: 'var(--ink)', outline: 'none' }} />
            </div>
          )}
          {!isEditing && item.description && (
            <div style={{ marginLeft: 40, fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{item.description}</div>
          )}

          {/* Sub-sections */}
          {item.sections && item.sections.length > 0 && (
            <div style={{ marginLeft: 24, marginTop: 4 }}>
              {renderItems(item.sections, currentPath)}
            </div>
          )}
        </div>
      );
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <ListTree size={16} color="var(--accent)" />
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)' }}>{title}</span>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>{outline.length} 章</span>
        <div style={{ flex: 1 }} />
        <button onClick={() => onChange([...outline, { level: 1, title: '新章节', estimated_words: 500 }])}
          style={{ padding: '3px 10px', borderRadius: 6, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3 }}>
          <Plus size={12} /> 添加章节
        </button>
        <button onClick={onConfirm}
          style={{ padding: '3px 10px', borderRadius: 6, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
          确认大纲 ✓
        </button>
      </div>
      {renderItems(outline)}
    </div>
  );
};

export default OutlineEditor;
