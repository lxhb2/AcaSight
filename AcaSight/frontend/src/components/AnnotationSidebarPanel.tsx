/**
 * AnnotationSidebarPanel — 标注侧边栏
 *
 * 对标 PDF 阅读器开发手册第4章功能：
 * - 按颜色/类型分组展示标注
 * - 颜色语义标签（黄=核心观点/绿=方法论/蓝=存疑/粉=重要）
 * - 点击标注项跳转到对应页面并高亮闪烁
 * - 支持搜索过滤标注
 * - 可折叠分组
 */

import React, { useMemo, useState, useCallback } from 'react';
import { useApp } from '@/contexts/AppContext';
import type { AnnotationItem } from '@/services/api';
import {
  Highlighter,
  Underline as UnderlineIcon,
  MessageCircle,
  Trash2,
  ChevronDown,
  ChevronRight,
  Search,
  Filter,
  Type,
  BookOpen,
  Palette,
} from 'lucide-react';

// 颜色语义映射（对标手册4.2颜色分类法则）
const COLOR_SEMANTICS: Record<string, { label: string; bg: string; border: string; dot: string }> = {
  '#FFEB3B': { label: '核心观点', bg: 'rgba(255,235,59,0.12)', border: 'rgba(255,235,59,0.3)', dot: '#FFEB3B' },
  '#66BB6A': { label: '方法论', bg: 'rgba(102,187,106,0.12)', border: 'rgba(102,187,106,0.3)', dot: '#66BB6A' },
  '#42A5F5': { label: '存疑', bg: 'rgba(66,165,245,0.12)', border: 'rgba(66,165,245,0.3)', dot: '#42A5F5' },
  '#EF5350': { label: '重要', bg: 'rgba(239,83,80,0.12)', border: 'rgba(239,83,80,0.3)', dot: '#EF5350' },
  '#FFA726': { label: '待确认', bg: 'rgba(255,167,38,0.12)', border: 'rgba(255,167,38,0.3)', dot: '#FFA726' },
  '#AB47BC': { label: '想法', bg: 'rgba(171,71,188,0.12)', border: 'rgba(171,71,188,0.3)', dot: '#AB47BC' },
};

const DEFAULT_SEMANTIC = { label: '标注', bg: 'rgba(128,128,128,0.12)', border: 'rgba(128,128,128,0.3)', dot: '#888' };

// 标注类型配置
const TYPE_CONFIG: Record<string, { label: string; icon: React.ReactNode }> = {
  highlight: { label: '高亮', icon: <Highlighter size={12} /> },
  underline: { label: '下划线', icon: <UnderlineIcon size={12} /> },
  strikethrough: { label: '删除线', icon: <Type size={12} /> },
  note: { label: '注释', icon: <MessageCircle size={12} /> },
};

// 分组方式
type GroupMode = 'color' | 'type' | 'page';

const AnnotationSidebarPanel: React.FC = () => {
  const { annotations, deleteAnnotation, setCurrentPage } = useApp();
  const [groupMode, setGroupMode] = useState<GroupMode>('color');
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  // 过滤标注
  const filteredAnnotations = useMemo(() => {
    if (!searchQuery.trim()) return annotations;
    const q = searchQuery.toLowerCase();
    return annotations.filter(
      (a) =>
        (a.selected_text && a.selected_text.toLowerCase().includes(q)) ||
        (a.note && a.note.toLowerCase().includes(q))
    );
  }, [annotations, searchQuery]);

  // 分组
  const grouped = useMemo(() => {
    const groups: Record<string, { key: string; label: string; icon?: React.ReactNode; dot?: string; items: AnnotationItem[] }> = {};

    for (const ann of filteredAnnotations) {
      let groupKey: string;
      let groupLabel: string;
      let groupIcon: React.ReactNode | undefined;
      let groupDot: string | undefined;

      if (groupMode === 'color') {
        const sem = COLOR_SEMANTICS[ann.color] || DEFAULT_SEMANTIC;
        groupKey = `color:${ann.color}`;
        groupLabel = sem.label;
        groupDot = sem.dot;
      } else if (groupMode === 'type') {
        const tc = TYPE_CONFIG[ann.annotation_type] || { label: ann.annotation_type, icon: <BookOpen size={12} /> };
        groupKey = `type:${ann.annotation_type}`;
        groupLabel = tc.label;
        groupIcon = tc.icon;
      } else {
        groupKey = `page:${ann.page}`;
        groupLabel = `第 ${ann.page} 页`;
      }

      if (!groups[groupKey]) {
        groups[groupKey] = { key: groupKey, label: groupLabel, icon: groupIcon, dot: groupDot, items: [] };
      }
      groups[groupKey].items.push(ann);
    }

    // 排序：颜色按固定顺序，类型按固定顺序，页码按数字
    const entries = Object.values(groups);
    if (groupMode === 'page') {
      entries.sort((a, b) => {
        const pa = parseInt(a.key.split(':')[1]);
        const pb = parseInt(b.key.split(':')[1]);
        return pa - pb;
      });
    }
    return entries;
  }, [filteredAnnotations, groupMode]);

  // 折叠切换
  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  // 跳转到标注（对标手册4.3点击跳转定位实现）
  const jumpToAnnotation = useCallback(
    (ann: AnnotationItem) => {
      // 滚动到目标页面 — react-pdf 使用 data-page-number 属性
      const pageEl = document.querySelector(`[data-page-number="${ann.page}"]`);
      if (pageEl) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }

      // 更新当前页码状态
      setCurrentPage(ann.page);

      // 高亮闪烁目标标注
      setTimeout(() => {
        const overlays = document.querySelectorAll(`[data-annotation-id="${ann.id}"]`);
        overlays.forEach((overlay) => {
          overlay.classList.add('acasight-annotation-jump');
          // 2秒后移除高亮
          setTimeout(() => overlay.classList.remove('acasight-annotation-jump'), 2000);
        });
      }, 500);
    },
    [setCurrentPage]
  );

  // 删除标注
  const handleDelete = useCallback(
    async (e: React.MouseEvent, id: number) => {
      e.stopPropagation();
      await deleteAnnotation(id);
    },
    [deleteAnnotation]
  );

  // 标注统计
  const stats = useMemo(() => {
    const byType: Record<string, number> = {};
    for (const a of filteredAnnotations) {
      byType[a.annotation_type] = (byType[a.annotation_type] || 0) + 1;
    }
    return { total: filteredAnnotations.length, byType };
  }, [filteredAnnotations]);

  // 获取标注类型图标
  const getTypeIcon = (type: string) => TYPE_CONFIG[type]?.icon || <BookOpen size={12} />;

  // 获取标注类型标签
  const getTypeLabel = (type: string) => TYPE_CONFIG[type]?.label || type;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 搜索栏 */}
      <div style={{ padding: '8px 8px 4px', borderBottom: '1px solid var(--hairline)' }}>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search
              size={12}
              style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--mute)' }}
            />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索标注内容..."
              style={{
                width: '100%',
                height: 28,
                background: 'var(--canvas-soft)',
                border: '1px solid var(--hairline)',
                borderRadius: 'var(--radius-sm)',
                padding: '0 8px 0 26px',
                color: 'var(--ink)',
                fontSize: 12,
                outline: 'none',
              }}
            />
          </div>
        </div>
        {/* 分组模式切换 */}
        <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
          {([
            { mode: 'color' as GroupMode, icon: <Palette size={11} />, label: '颜色' },
            { mode: 'type' as GroupMode, icon: <Filter size={11} />, label: '类型' },
            { mode: 'page' as GroupMode, icon: <BookOpen size={11} />, label: '页码' },
          ]).map((g) => (
            <button
              key={g.mode}
              onClick={() => setGroupMode(g.mode)}
              style={{
                flex: 1,
                padding: '3px 0',
                borderRadius: 'var(--radius-xs)',
                fontSize: 11,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 3,
                background: groupMode === g.mode ? 'var(--accent)' : 'var(--canvas-soft)',
                color: groupMode === g.mode ? '#fff' : 'var(--mute)',
                border: groupMode === g.mode ? '1px solid var(--accent)' : '1px solid var(--hairline)',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {g.icon}
              {g.label}
            </button>
          ))}
        </div>
        {/* 统计 */}
        <div style={{ display: 'flex', gap: 6, marginTop: 4, fontSize: 10, color: 'var(--mute)', flexWrap: 'wrap' }}>
          <span>共 {stats.total} 条</span>
          {Object.entries(stats.byType).map(([t, c]) => (
            <span key={t}>
              {getTypeLabel(t)} {c}
            </span>
          ))}
        </div>
      </div>

      {/* 标注列表 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '4px 8px 8px' }}>
        {filteredAnnotations.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: 32, color: 'var(--mute)' }}>
            <Highlighter size={28} style={{ opacity: 0.3, margin: '0 auto 8px' }} />
            <p style={{ fontSize: 12 }}>{annotations.length === 0 ? '暂无标注' : '无匹配结果'}</p>
            {annotations.length === 0 && (
              <p style={{ fontSize: 11, marginTop: 4, opacity: 0.7 }}>选中文本后可创建标注</p>
            )}
          </div>
        )}

        {grouped.map((group) => {
          const isCollapsed = collapsedGroups.has(group.key);
          return (
            <div key={group.key} style={{ marginBottom: 6 }}>
              {/* 分组标题 */}
              <div
                onClick={() => toggleGroup(group.key)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 8px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--canvas-soft)',
                  cursor: 'pointer',
                  userSelect: 'none',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--accent-bg-soft)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--canvas-soft)';
                }}
              >
                {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                {group.dot && (
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      background: group.dot,
                      display: 'inline-block',
                      flexShrink: 0,
                    }}
                  />
                )}
                {group.icon}
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', flex: 1 }}>{group.label}</span>
                <span style={{ fontSize: 10, color: 'var(--mute)' }}>{group.items.length}</span>
              </div>

              {/* 标注项列表 */}
              {!isCollapsed && (
                <div style={{ marginTop: 2, marginLeft: 4 }}>
                  {group.items.map((ann) => {
                    const sem = COLOR_SEMANTICS[ann.color] || DEFAULT_SEMANTIC;
                    return (
                      <div
                        key={ann.id}
                        onClick={() => jumpToAnnotation(ann)}
                        onMouseEnter={() => setHoveredId(ann.id)}
                        onMouseLeave={() => setHoveredId(null)}
                        style={{
                          padding: '6px 8px',
                          marginBottom: 2,
                          borderRadius: 'var(--radius-sm)',
                          background: hoveredId === ann.id ? sem.bg : 'transparent',
                          borderLeft: `3px solid ${sem.dot}`,
                          cursor: 'pointer',
                          transition: 'all 0.15s',
                          position: 'relative',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 4 }}>
                          <span
                            style={{
                              fontSize: 10,
                              color: 'var(--mute)',
                              flexShrink: 0,
                              marginTop: 1,
                              display: 'flex',
                              alignItems: 'center',
                              gap: 2,
                            }}
                          >
                            {getTypeIcon(ann.annotation_type)}
                            <span style={{ opacity: 0.7 }}>P{ann.page}</span>
                          </span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            {ann.selected_text && (
                              <p
                                style={{
                                  fontSize: 12,
                                  color: 'var(--ink)',
                                  lineHeight: 1.4,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  display: '-webkit-box',
                                  WebkitLineClamp: 2,
                                  WebkitBoxOrient: 'vertical',
                                  margin: 0,
                                }}
                              >
                                {ann.selected_text}
                              </p>
                            )}
                            {ann.note && (
                              <p
                                style={{
                                  fontSize: 11,
                                  color: 'var(--mute)',
                                  lineHeight: 1.4,
                                  marginTop: ann.selected_text ? 2 : 0,
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  margin: ann.selected_text ? 2 : 0,
                                }}
                              >
                                📝 {ann.note}
                              </p>
                            )}
                          </div>
                          <button
                            onClick={(e) => handleDelete(e, ann.id)}
                            style={{
                              opacity: hoveredId === ann.id ? 0.7 : 0,
                              background: 'none',
                              border: 'none',
                              color: 'var(--mute)',
                              cursor: 'pointer',
                              padding: 0,
                              transition: 'opacity 0.15s',
                              flexShrink: 0,
                            }}
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default AnnotationSidebarPanel;
