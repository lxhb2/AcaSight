/**
 * LabNotebookPanel — Feature 6.6 实验笔记本
 *
 * 三栏布局：左侧实验列表、中间实验详情、右侧关联链接。
 * 支持实验 CRUD、条目管理（文本/数据/表格/图片/步骤）、关联链接、导出。
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Plus, Search, FlaskConical, Trash2, Edit3, Save,
  FileText, Table2, Image, ListChecks, Database,
  Link2, BookOpen, BarChart3, Download, X,
  ChevronRight, AlertCircle, Loader2, Tag,
} from 'lucide-react';
import {
  experimentApi,
  type ExperimentItem,
  type ExperimentEntryItem,
  type ExperimentStatus,
  type EntryType,
  type LinkedType,
} from '@/services/experimentService';
import { saveFile } from '@/lib/tauri-adapter';

// ==================== 状态颜色映射 ====================

const STATUS_CONFIG: Record<ExperimentStatus, { label: string; color: string; bg: string }> = {
  planning: { label: '规划中', color: '#3b82f6', bg: '#eff6ff' },
  running: { label: '进行中', color: '#f59e0b', bg: '#fffbeb' },
  completed: { label: '已完成', color: '#22c55e', bg: '#f0fdf4' },
  failed: { label: '已失败', color: '#ef4444', bg: '#fef2f2' },
};

const ENTRY_TYPE_CONFIG: Record<EntryType, { label: string; icon: React.ReactNode; color: string }> = {
  text: { label: '文本', icon: <FileText size={14} />, color: '#3b82f6' },
  data: { label: '数据', icon: <Database size={14} />, color: '#8b5cf6' },
  table: { label: '表格', icon: <Table2 size={14} />, color: '#f59e0b' },
  image: { label: '图片', icon: <Image size={14} />, color: '#ec4899' },
  procedure: { label: '步骤', icon: <ListChecks size={14} />, color: '#22c55e' },
};

const LINK_TYPE_CONFIG: Record<LinkedType, { label: string; icon: React.ReactNode }> = {
  literature: { label: '文献', icon: <BookOpen size={14} /> },
  document: { label: '文档', icon: <FileText size={14} /> },
  chart: { label: '图表', icon: <BarChart3 size={14} /> },
};

// ==================== 组件 ====================

export const LabNotebookPanel: React.FC = () => {
  // 实验列表状态
  const [experiments, setExperiments] = useState<ExperimentItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [currentExp, setCurrentExp] = useState<ExperimentItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // 编辑状态
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleValue, setTitleValue] = useState('');
  const [editingDesc, setEditingDesc] = useState(false);
  const [descValue, setDescValue] = useState('');

  // 新建实验
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newCategory, setNewCategory] = useState('');

  // 新建条目
  const [showAddEntry, setShowAddEntry] = useState(false);
  const [newEntryType, setNewEntryType] = useState<EntryType>('text');

  // 新建链接
  const [showAddLink, setShowAddLink] = useState(false);
  const [newLinkType, setNewLinkType] = useState<LinkedType>('literature');
  const [newLinkId, setNewLinkId] = useState('');
  const [newLinkNote, setNewLinkNote] = useState('');

  // 右侧面板
  const [showLinksPanel, setShowLinksPanel] = useState(false);

  // Toast
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);

  const showToast = useCallback((msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // 加载实验列表
  const loadExperiments = useCallback(async () => {
    setLoading(true);
    try {
      const res = await experimentApi.list({
        search: searchQuery || undefined,
        status: filterStatus || undefined,
      });
      setExperiments(res.data || []);
    } catch {
      showToast('加载实验列表失败', 'error');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterStatus, showToast]);

  // 加载实验详情
  const loadExperiment = useCallback(async (expId: string) => {
    try {
      const res = await experimentApi.get(expId);
      setCurrentExp(res.data);
      setTitleValue(res.data.title);
      setDescValue(res.data.description);
    } catch {
      showToast('加载实验详情失败', 'error');
    }
  }, [showToast]);

  useEffect(() => {
    loadExperiments();
  }, [loadExperiments]);

  useEffect(() => {
    if (selectedId) {
      loadExperiment(selectedId);
    } else {
      setCurrentExp(null);
    }
  }, [selectedId, loadExperiment]);

  // 创建实验
  const handleCreate = useCallback(async () => {
    if (!newTitle.trim()) {
      showToast('请输入实验标题', 'error');
      return;
    }
    try {
      const res = await experimentApi.create({
        title: newTitle,
        category: newCategory || undefined,
      });
      setShowCreateDialog(false);
      setNewTitle('');
      setNewCategory('');
      setSelectedId(res.data.id);
      showToast('实验已创建', 'success');
      loadExperiments();
    } catch {
      showToast('创建实验失败', 'error');
    }
  }, [newTitle, newCategory, showToast, loadExperiments]);

  // 更新实验
  const handleUpdateExp = useCallback(async (data: Partial<ExperimentItem>) => {
    if (!selectedId) return;
    try {
      const res = await experimentApi.update(selectedId, data);
      setCurrentExp(res.data);
      loadExperiments();
    } catch {
      showToast('更新失败', 'error');
    }
  }, [selectedId, showToast, loadExperiments]);

  // 删除实验
  const handleDeleteExp = useCallback(async (expId: string) => {
    try {
      await experimentApi.delete(expId);
      if (selectedId === expId) {
        setSelectedId(null);
        setCurrentExp(null);
      }
      showToast('实验已删除', 'success');
      loadExperiments();
    } catch {
      showToast('删除失败', 'error');
    }
  }, [selectedId, showToast, loadExperiments]);

  // 添加条目
  const handleAddEntry = useCallback(async () => {
    if (!selectedId) return;
    try {
      // 根据条目类型创建默认内容
      let defaultContent: Record<string, unknown> = {};
      switch (newEntryType) {
        case 'text':
          defaultContent = { text: '' };
          break;
        case 'data':
          defaultContent = { pairs: [{ key: '', value: '' }] };
          break;
        case 'table':
          defaultContent = { headers: ['列1', '列2', '列3'], rows: [['', '', '']] };
          break;
        case 'image':
          defaultContent = { url: '', caption: '' };
          break;
        case 'procedure':
          defaultContent = { steps: [{ text: '', checked: false }] };
          break;
      }

      await experimentApi.addEntry(selectedId, {
        entry_type: newEntryType,
        content: defaultContent,
      });
      // 刷新详情
      loadExperiment(selectedId);
      setShowAddEntry(false);
      showToast('条目已添加', 'success');
    } catch {
      showToast('添加条目失败', 'error');
    }
  }, [selectedId, newEntryType, showToast, loadExperiment]);

  // 更新条目内容
  const handleUpdateEntry = useCallback(async (entryId: string, content: Record<string, unknown>) => {
    if (!selectedId) return;
    try {
      await experimentApi.updateEntry(selectedId, entryId, { content });
      // 局部更新当前实验
      if (currentExp?.entries) {
        setCurrentExp({
          ...currentExp,
          entries: currentExp.entries.map(e =>
            e.id === entryId ? { ...e, content } : e
          ),
        });
      }
    } catch {
      showToast('更新条目失败', 'error');
    }
  }, [selectedId, currentExp, showToast]);

  // 删除条目
  const handleDeleteEntry = useCallback(async (entryId: string) => {
    if (!selectedId) return;
    try {
      await experimentApi.deleteEntry(selectedId, entryId);
      loadExperiment(selectedId);
      showToast('条目已删除', 'success');
    } catch {
      showToast('删除条目失败', 'error');
    }
  }, [selectedId, showToast, loadExperiment]);

  // 添加链接
  const handleAddLink = useCallback(async () => {
    if (!selectedId || !newLinkId.trim()) {
      showToast('请输入关联 ID', 'error');
      return;
    }
    try {
      await experimentApi.addLink(selectedId, {
        linked_type: newLinkType,
        linked_id: newLinkId,
        note: newLinkNote,
      });
      loadExperiment(selectedId);
      setShowAddLink(false);
      setNewLinkId('');
      setNewLinkNote('');
      showToast('链接已添加', 'success');
    } catch {
      showToast('添加链接失败', 'error');
    }
  }, [selectedId, newLinkType, newLinkId, newLinkNote, showToast, loadExperiment]);

  // 删除链接
  const handleDeleteLink = useCallback(async (linkId: string) => {
    if (!selectedId) return;
    try {
      await experimentApi.deleteLink(selectedId, linkId);
      loadExperiment(selectedId);
      showToast('链接已删除', 'success');
    } catch {
      showToast('删除链接失败', 'error');
    }
  }, [selectedId, showToast, loadExperiment]);

  // 导出为 Markdown
  const handleExportMarkdown = useCallback(async () => {
    if (!currentExp) return;
    let md = `# ${currentExp.title}\n\n`;
    md += `**状态**: ${STATUS_CONFIG[currentExp.status]?.label || currentExp.status}\n`;
    if (currentExp.category) md += `**分类**: ${currentExp.category}\n`;
    if (currentExp.description) md += `\n${currentExp.description}\n`;
    md += '\n---\n\n';

    if (currentExp.entries) {
      for (const entry of currentExp.entries) {
        const cfg = ENTRY_TYPE_CONFIG[entry.entry_type];
        md += `## [${cfg?.label || entry.entry_type}] ${entry.created_at || ''}\n\n`;
        const c = entry.content;
        switch (entry.entry_type) {
          case 'text':
            md += `${(c as { text?: string }).text || ''}\n\n`;
            break;
          case 'data':
            md += '| 键 | 值 |\n|---|---|\n';
            for (const p of (c as { pairs?: Array<{ key: string; value: string }> }).pairs || []) {
              md += `| ${p.key} | ${p.value} |\n`;
            }
            md += '\n';
            break;
          case 'table':
            const tc = c as { headers?: string[]; rows?: string[][] };
            if (tc.headers) md += `| ${tc.headers.join(' | ')} |\n| ${tc.headers.map(() => '---').join(' | ')} |\n`;
            for (const row of tc.rows || []) {
              md += `| ${row.join(' | ')} |\n`;
            }
            md += '\n';
            break;
          case 'image':
            const ic = c as { url?: string; caption?: string };
            if (ic.url) md += `![${ic.caption || ''}](${ic.url})\n\n`;
            if (ic.caption) md += `*${ic.caption}*\n\n`;
            break;
          case 'procedure':
            for (const step of (c as { steps?: Array<{ text: string; checked: boolean }> }).steps || []) {
              md += `- [${step.checked ? 'x' : ' '}] ${step.text}\n`;
            }
            md += '\n';
            break;
        }
        if (entry.tags?.length) md += `标签: ${entry.tags.join(', ')}\n\n`;
      }
    }

    if (currentExp.links?.length) {
      md += '---\n\n## 关联链接\n\n';
      for (const link of currentExp.links) {
        const lcfg = LINK_TYPE_CONFIG[link.linked_type as LinkedType];
        md += `- [${lcfg?.label || link.linked_type}] ${link.linked_id}${link.note ? ` — ${link.note}` : ''}\n`;
      }
    }

    try {
      await saveFile(md, {
        filters: [{ name: 'Markdown', extensions: ['md'] }],
        defaultPath: `${currentExp.title}.md`,
      });
      showToast('已导出 Markdown', 'success');
    } catch {
      showToast('导出失败', 'error');
    }
  }, [currentExp, showToast]);

  // 样式
  const glassBg = 'rgba(255,255,255,0.6)';
  const glassBlur = '12px';
  const glassShadow = '0 4px 16px rgba(0,0,0,0.08)';

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--canvas-soft)', color: 'var(--ink)' }}>
      {/* ═══ 左侧：实验列表 ═══ */}
      <div style={{
        width: 280, minWidth: 280,
        borderRight: '1px solid var(--hairline)',
        display: 'flex', flexDirection: 'column',
        background: glassBg, backdropFilter: `blur(${glassBlur})`,
      }}>
        {/* 列表头部 */}
        <div style={{ padding: '12px', borderBottom: '1px solid var(--hairline)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <FlaskConical size={16} style={{ color: 'var(--accent)' }} />
            <span style={{ fontWeight: 600, fontSize: 14 }}>实验笔记本</span>
            <div style={{ flex: 1 }} />
            <button
              onClick={() => setShowCreateDialog(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: 3,
                padding: '3px 10px', fontSize: 11, borderRadius: 6,
                border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer',
              }}
            >
              <Plus size={13} /> 新建
            </button>
          </div>
          {/* 搜索 */}
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 8, top: 8, color: 'var(--mute)' }} />
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="搜索实验..."
              style={{
                width: '100%', padding: '6px 8px 6px 28px', fontSize: 12,
                borderRadius: 6, border: '1px solid var(--hairline)',
                background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
              }}
            />
          </div>
          {/* 状态筛选 */}
          <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
            <button
              onClick={() => setFilterStatus('')}
              style={{
                padding: '2px 8px', fontSize: 10, borderRadius: 4,
                border: '1px solid var(--hairline)', background: !filterStatus ? 'var(--accent)' : 'transparent',
                color: !filterStatus ? '#fff' : 'var(--ink)', cursor: 'pointer',
              }}
            >
              全部
            </button>
            {(Object.entries(STATUS_CONFIG) as [ExperimentStatus, typeof STATUS_CONFIG[ExperimentStatus]][]).map(([key, cfg]) => (
              <button
                key={key}
                onClick={() => setFilterStatus(key)}
                style={{
                  padding: '2px 8px', fontSize: 10, borderRadius: 4,
                  border: `1px solid ${cfg.color}40`, background: filterStatus === key ? cfg.color : 'transparent',
                  color: filterStatus === key ? '#fff' : cfg.color, cursor: 'pointer',
                }}
              >
                {cfg.label}
              </button>
            ))}
          </div>
        </div>

        {/* 实验列表 */}
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--mute)' }}>
              <Loader2 size={20} className="animate-spin" />
            </div>
          ) : experiments.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 20, color: 'var(--mute)', fontSize: 12 }}>
              暂无实验，点击"新建"创建
            </div>
          ) : (
            experiments.map(exp => {
              const scfg = STATUS_CONFIG[exp.status as ExperimentStatus];
              return (
                <div
                  key={exp.id}
                  onClick={() => setSelectedId(exp.id)}
                  style={{
                    padding: '10px 12px', cursor: 'pointer',
                    borderBottom: '1px solid var(--hairline)',
                    background: selectedId === exp.id ? 'var(--accent-bg-soft)' : 'transparent',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={(e) => { if (selectedId !== exp.id) e.currentTarget.style.background = 'var(--canvas-soft)'; }}
                  onMouseLeave={(e) => { if (selectedId !== exp.id) e.currentTarget.style.background = 'transparent'; }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: scfg?.color || '#999', flexShrink: 0,
                    }} />
                    <span style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                      {exp.title}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteExp(exp.id); }}
                      style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--mute)', padding: 2 }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: scfg?.color, background: scfg?.bg, padding: '1px 6px', borderRadius: 3 }}>
                      {scfg?.label || exp.status}
                    </span>
                    {exp.category && (
                      <span style={{ fontSize: 10, color: 'var(--mute)' }}>
                        <Tag size={9} style={{ marginRight: 2 }} />{exp.category}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ═══ 中间：实验详情 ═══ */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {currentExp ? (
          <>
            {/* 详情头部 */}
            <div style={{
              padding: '16px 20px', borderBottom: '1px solid var(--hairline)',
              background: glassBg, backdropFilter: `blur(${glassBlur})`,
            }}>
              {/* 标题 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {editingTitle ? (
                  <input
                    value={titleValue}
                    onChange={e => setTitleValue(e.target.value)}
                    onBlur={() => { handleUpdateExp({ title: titleValue }); setEditingTitle(false); }}
                    onKeyDown={e => { if (e.key === 'Enter') { handleUpdateExp({ title: titleValue }); setEditingTitle(false); } }}
                    autoFocus
                    style={{
                      flex: 1, fontSize: 18, fontWeight: 600,
                      border: '1px solid var(--accent)', borderRadius: 4,
                      padding: '2px 8px', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                    }}
                  />
                ) : (
                  <h2
                    style={{ fontSize: 18, fontWeight: 600, flex: 1, cursor: 'pointer' }}
                    onClick={() => setEditingTitle(true)}
                  >
                    {currentExp.title}
                  </h2>
                )}
                <button onClick={() => setEditingTitle(!editingTitle)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--mute)' }}>
                  <Edit3 size={14} />
                </button>
              </div>

              {/* 状态 + 分类 + 操作 */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <select
                  value={currentExp.status}
                  onChange={e => handleUpdateExp({ status: e.target.value as ExperimentStatus })}
                  style={{
                    padding: '3px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)',
                  }}
                >
                  {(Object.entries(STATUS_CONFIG) as [ExperimentStatus, typeof STATUS_CONFIG[ExperimentStatus]][]).map(([key, cfg]) => (
                    <option key={key} value={key}>{cfg.label}</option>
                  ))}
                </select>

                <input
                  value={currentExp.category || ''}
                  onChange={e => setCurrentExp({ ...currentExp, category: e.target.value })}
                  onBlur={e => handleUpdateExp({ category: e.target.value })}
                  placeholder="分类标签"
                  style={{
                    padding: '3px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)',
                    width: 120, outline: 'none',
                  }}
                />

                <div style={{ flex: 1 }} />

                <button
                  onClick={() => setShowLinksPanel(!showLinksPanel)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '3px 10px', fontSize: 11, borderRadius: 6,
                    border: '1px solid var(--hairline)', background: showLinksPanel ? 'var(--accent-bg-soft)' : 'transparent',
                    color: 'var(--ink)', cursor: 'pointer',
                  }}
                >
                  <Link2 size={13} /> 关联
                </button>

                <button
                  onClick={handleExportMarkdown}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '3px 10px', fontSize: 11, borderRadius: 6,
                    border: '1px solid var(--hairline)', background: 'transparent',
                    color: 'var(--ink)', cursor: 'pointer',
                  }}
                >
                  <Download size={13} /> 导出
                </button>
              </div>

              {/* 描述 */}
              <div style={{ marginTop: 8 }}>
                {editingDesc ? (
                  <textarea
                    value={descValue}
                    onChange={e => setDescValue(e.target.value)}
                    onBlur={() => { handleUpdateExp({ description: descValue }); setEditingDesc(false); }}
                    autoFocus
                    rows={2}
                    style={{
                      width: '100%', padding: '6px 8px', fontSize: 12,
                      borderRadius: 4, border: '1px solid var(--accent)',
                      background: 'var(--canvas)', color: 'var(--ink)', outline: 'none', resize: 'vertical',
                    }}
                  />
                ) : (
                  <div
                    onClick={() => setEditingDesc(true)}
                    style={{ fontSize: 12, color: currentExp.description ? 'var(--ink)' : 'var(--mute)', cursor: 'pointer', fontStyle: currentExp.description ? 'normal' : 'italic' }}
                  >
                    {currentExp.description || '点击添加描述...'}
                  </div>
                )}
              </div>
            </div>

            {/* 条目时间线 */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px 20px' }}>
              {/* 添加条目按钮 */}
              <div style={{ marginBottom: 16 }}>
                {showAddEntry ? (
                  <div style={{
                    padding: 12, borderRadius: 8,
                    background: glassBg, backdropFilter: `blur(${glassBlur})`,
                    border: '1px solid var(--hairline)',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 500, marginBottom: 8 }}>选择条目类型</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {(Object.entries(ENTRY_TYPE_CONFIG) as [EntryType, typeof ENTRY_TYPE_CONFIG[EntryType]][]).map(([key, cfg]) => (
                        <button
                          key={key}
                          onClick={() => setNewEntryType(key)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 4,
                            padding: '5px 12px', fontSize: 11, borderRadius: 6,
                            border: `1px solid ${newEntryType === key ? cfg.color : 'var(--hairline)'}`,
                            background: newEntryType === key ? `${cfg.color}15` : 'transparent',
                            color: newEntryType === key ? cfg.color : 'var(--ink)',
                            cursor: 'pointer',
                          }}
                        >
                          {cfg.icon} {cfg.label}
                        </button>
                      ))}
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                      <button
                        onClick={handleAddEntry}
                        style={{
                          padding: '4px 16px', fontSize: 12, borderRadius: 6,
                          border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer',
                        }}
                      >
                        添加
                      </button>
                      <button
                        onClick={() => setShowAddEntry(false)}
                        style={{
                          padding: '4px 16px', fontSize: 12, borderRadius: 6,
                          border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer',
                        }}
                      >
                        取消
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowAddEntry(true)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 4,
                      padding: '6px 14px', fontSize: 12, borderRadius: 6,
                      border: '1px dashed var(--hairline)', background: 'transparent',
                      color: 'var(--mute)', cursor: 'pointer', width: '100%',
                      justifyContent: 'center',
                    }}
                  >
                    <Plus size={14} /> 添加条目
                  </button>
                )}
              </div>

              {/* 条目列表 */}
              {currentExp.entries?.map(entry => (
                <EntryCard
                  key={entry.id}
                  entry={entry}
                  onUpdate={handleUpdateEntry}
                  onDelete={handleDeleteEntry}
                />
              ))}

              {(!currentExp.entries || currentExp.entries.length === 0) && (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--mute)', fontSize: 13 }}>
                  <FlaskConical size={32} style={{ marginBottom: 8, opacity: 0.3 }} />
                  <div>暂无条目，点击上方按钮添加</div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--mute)' }}>
            <div style={{ textAlign: 'center' }}>
              <FlaskConical size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
              <div style={{ fontSize: 14 }}>选择或创建一个实验</div>
            </div>
          </div>
        )}
      </div>

      {/* ═══ 右侧：关联链接面板 ═══ */}
      {showLinksPanel && currentExp && (
        <div style={{
          width: 260, minWidth: 260,
          borderLeft: '1px solid var(--hairline)',
          display: 'flex', flexDirection: 'column',
          background: glassBg, backdropFilter: `blur(${glassBlur})`,
        }}>
          <div style={{ padding: '12px', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Link2 size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontWeight: 600, fontSize: 13 }}>关联链接</span>
            <div style={{ flex: 1 }} />
            <button onClick={() => setShowLinksPanel(false)} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--mute)' }}>
              <X size={14} />
            </button>
          </div>

          <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
            {/* 添加链接 */}
            {showAddLink ? (
              <div style={{
                padding: 10, borderRadius: 6,
                border: '1px solid var(--hairline)', marginBottom: 12,
                background: 'var(--canvas)',
              }}>
                <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
                  {(Object.entries(LINK_TYPE_CONFIG) as [LinkedType, typeof LINK_TYPE_CONFIG[LinkedType]][]).map(([key, cfg]) => (
                    <button
                      key={key}
                      onClick={() => setNewLinkType(key)}
                      style={{
                        padding: '2px 8px', fontSize: 10, borderRadius: 4,
                        border: `1px solid ${newLinkType === key ? 'var(--accent)' : 'var(--hairline)'}`,
                        background: newLinkType === key ? 'var(--accent-bg-soft)' : 'transparent',
                        color: 'var(--ink)', cursor: 'pointer',
                        display: 'flex', alignItems: 'center', gap: 3,
                      }}
                    >
                      {cfg.icon} {cfg.label}
                    </button>
                  ))}
                </div>
                <input
                  value={newLinkId}
                  onChange={e => setNewLinkId(e.target.value)}
                  placeholder="关联对象 ID"
                  style={{
                    width: '100%', padding: '4px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas-soft)', color: 'var(--ink)', outline: 'none', marginBottom: 4,
                  }}
                />
                <input
                  value={newLinkNote}
                  onChange={e => setNewLinkNote(e.target.value)}
                  placeholder="备注（可选）"
                  style={{
                    width: '100%', padding: '4px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas-soft)', color: 'var(--ink)', outline: 'none', marginBottom: 6,
                  }}
                />
                <div style={{ display: 'flex', gap: 4 }}>
                  <button onClick={handleAddLink} style={{ padding: '3px 10px', fontSize: 11, borderRadius: 4, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>
                    添加
                  </button>
                  <button onClick={() => setShowAddLink(false)} style={{ padding: '3px 10px', fontSize: 11, borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer' }}>
                    取消
                  </button>
                </div>
              </div>
            ) : (
              <button
                onClick={() => setShowAddLink(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '5px 12px', fontSize: 11, borderRadius: 6,
                  border: '1px dashed var(--hairline)', background: 'transparent',
                  color: 'var(--mute)', cursor: 'pointer', width: '100%', justifyContent: 'center',
                  marginBottom: 12,
                }}
              >
                <Plus size={12} /> 添加链接
              </button>
            )}

            {/* 链接列表（按类型分组） */}
            {(Object.entries(LINK_TYPE_CONFIG) as [LinkedType, typeof LINK_TYPE_CONFIG[LinkedType]][]).map(([type, cfg]) => {
              const links = currentExp.links?.filter(l => l.linked_type === type) || [];
              if (links.length === 0) return null;
              return (
                <div key={type} style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                    {cfg.icon} {cfg.label} ({links.length})
                  </div>
                  {links.map(link => (
                    <div
                      key={link.id}
                      style={{
                        padding: '6px 8px', borderRadius: 4,
                        border: '1px solid var(--hairline)', marginBottom: 4,
                        background: 'var(--canvas)', fontSize: 11,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <ChevronRight size={10} style={{ color: 'var(--accent)' }} />
                        <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {link.linked_id}
                        </span>
                        <button
                          onClick={() => handleDeleteLink(link.id)}
                          style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--mute)', padding: 0 }}
                        >
                          <Trash2 size={10} />
                        </button>
                      </div>
                      {link.note && <div style={{ fontSize: 10, color: 'var(--mute)', marginTop: 2, paddingLeft: 14 }}>{link.note}</div>}
                    </div>
                  ))}
                </div>
              );
            })}

            {(!currentExp.links || currentExp.links.length === 0) && !showAddLink && (
              <div style={{ textAlign: 'center', padding: 20, color: 'var(--mute)', fontSize: 11 }}>
                暂无关联链接
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══ 新建实验对话框 ═══ */}
      {showCreateDialog && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.3)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
        }}
          onClick={() => setShowCreateDialog(false)}
        >
          <div
            style={{
              padding: 20, borderRadius: 12, minWidth: 360,
              background: glassBg, backdropFilter: `blur(${glassBlur})`,
              border: '1px solid var(--hairline)', boxShadow: glassShadow,
            }}
            onClick={e => e.stopPropagation()}
          >
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>新建实验</h3>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: 'var(--mute)', display: 'block', marginBottom: 4 }}>实验标题 *</label>
              <input
                value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                placeholder="输入实验标题"
                autoFocus
                style={{
                  width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 6,
                  border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, color: 'var(--mute)', display: 'block', marginBottom: 4 }}>分类标签</label>
              <input
                value={newCategory}
                onChange={e => setNewCategory(e.target.value)}
                placeholder="例如：材料科学、有机合成"
                style={{
                  width: '100%', padding: '8px 10px', fontSize: 13, borderRadius: 6,
                  border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowCreateDialog(false)}
                style={{ padding: '6px 16px', fontSize: 12, borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer' }}
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                style={{ padding: '6px 16px', fontSize: 12, borderRadius: 6, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Toast ═══ */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24,
          padding: '10px 20px', borderRadius: 8, fontSize: 13, zIndex: 9999,
          display: 'flex', alignItems: 'center', gap: 8,
          background: toast.type === 'error' ? '#fef2f2' : '#f0fdf4',
          color: toast.type === 'error' ? '#991b1b' : '#166534',
          border: `1px solid ${toast.type === 'error' ? '#fca5a5' : '#86efac'}`,
          boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
        }}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <Save size={16} />}
          {toast.msg}
        </div>
      )}
    </div>
  );
};


// ==================== 条目卡片组件 ====================

interface EntryCardProps {
  entry: ExperimentEntryItem;
  onUpdate: (entryId: string, content: Record<string, unknown>) => void;
  onDelete: (entryId: string) => void;
}

const EntryCard: React.FC<EntryCardProps> = ({ entry, onUpdate, onDelete }) => {
  const cfg = ENTRY_TYPE_CONFIG[entry.entry_type];
  const content = entry.content;

  // 文本条目编辑
  const handleTextChange = useCallback((text: string) => {
    onUpdate(entry.id, { ...content, text });
  }, [entry.id, content, onUpdate]);

  // 数据条目编辑
  const handleDataChange = useCallback((index: number, field: 'key' | 'value', val: string) => {
    const pairs = [...((content as { pairs?: Array<{ key: string; value: string }> }).pairs || [])];
    pairs[index] = { ...pairs[index], [field]: val };
    onUpdate(entry.id, { ...content, pairs });
  }, [entry.id, content, onUpdate]);

  const handleAddDataRow = useCallback(() => {
    const pairs = [...((content as { pairs?: Array<{ key: string; value: string }> }).pairs || [])];
    pairs.push({ key: '', value: '' });
    onUpdate(entry.id, { ...content, pairs });
  }, [entry.id, content, onUpdate]);

  // 表格条目编辑
  const handleTableCellChange = useCallback((rowIdx: number, colIdx: number, val: string) => {
    const tc = content as { headers?: string[]; rows?: string[][] };
    const rows = (tc.rows || []).map((row, ri) =>
      ri === rowIdx ? row.map((cell, ci) => ci === colIdx ? val : cell) : row
    );
    onUpdate(entry.id, { ...content, rows });
  }, [entry.id, content, onUpdate]);

  const handleAddTableRow = useCallback(() => {
    const tc = content as { headers?: string[]; rows?: string[][] };
    const cols = tc.headers?.length || 3;
    const rows = [...(tc.rows || []), new Array(cols).fill('')];
    onUpdate(entry.id, { ...content, rows });
  }, [entry.id, content, onUpdate]);

  // 步骤条目编辑
  const handleStepChange = useCallback((index: number, text: string) => {
    const steps = [...((content as { steps?: Array<{ text: string; checked: boolean }> }).steps || [])];
    steps[index] = { ...steps[index], text };
    onUpdate(entry.id, { ...content, steps });
  }, [entry.id, content, onUpdate]);

  const handleStepToggle = useCallback((index: number) => {
    const steps = [...((content as { steps?: Array<{ text: string; checked: boolean }> }).steps || [])];
    steps[index] = { ...steps[index], checked: !steps[index].checked };
    onUpdate(entry.id, { ...content, steps });
  }, [entry.id, content, onUpdate]);

  const handleAddStep = useCallback(() => {
    const steps = [...((content as { steps?: Array<{ text: string; checked: boolean }> }).steps || [])];
    steps.push({ text: '', checked: false });
    onUpdate(entry.id, { ...content, steps });
  }, [entry.id, content, onUpdate]);

  // 图片条目编辑
  const handleImageChange = useCallback((field: 'url' | 'caption', val: string) => {
    onUpdate(entry.id, { ...content, [field]: val });
  }, [entry.id, content, onUpdate]);

  return (
    <div style={{
      marginBottom: 12, borderRadius: 8,
      border: '1px solid var(--hairline)',
      background: 'rgba(255,255,255,0.5)',
      backdropFilter: 'blur(8px)',
      overflow: 'hidden',
    }}>
      {/* 条目头部 */}
      <div style={{
        padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 6,
        borderBottom: '1px solid var(--hairline)',
        background: 'var(--canvas-soft)',
      }}>
        <span style={{ color: cfg?.color || '#999' }}>{cfg?.icon}</span>
        <span style={{ fontSize: 11, fontWeight: 500, color: cfg?.color || 'var(--ink)' }}>
          {cfg?.label || entry.entry_type}
        </span>
        <span style={{ fontSize: 10, color: 'var(--mute)', marginLeft: 4 }}>
          {entry.created_at ? new Date(entry.created_at).toLocaleString('zh-CN') : ''}
        </span>
        {entry.tags?.length > 0 && (
          <div style={{ display: 'flex', gap: 3, marginLeft: 4 }}>
            {entry.tags.map((tag, i) => (
              <span key={i} style={{ fontSize: 9, padding: '1px 5px', borderRadius: 3, background: 'var(--accent-bg-soft)', color: 'var(--accent)' }}>
                {tag}
              </span>
            ))}
          </div>
        )}
        <div style={{ flex: 1 }} />
        <button
          onClick={() => onDelete(entry.id)}
          style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--mute)', padding: 2 }}
        >
          <Trash2 size={12} />
        </button>
      </div>

      {/* 条目内容 */}
      <div style={{ padding: 12 }}>
        {entry.entry_type === 'text' && (
          <textarea
            value={(content as { text?: string }).text || ''}
            onChange={e => handleTextChange(e.target.value)}
            placeholder="输入文本内容..."
            rows={3}
            style={{
              width: '100%', padding: '6px 8px', fontSize: 12,
              borderRadius: 4, border: '1px solid var(--hairline)',
              background: 'var(--canvas)', color: 'var(--ink)', outline: 'none', resize: 'vertical',
            }}
          />
        )}

        {entry.entry_type === 'data' && (
          <div>
            {((content as { pairs?: Array<{ key: string; value: string }> }).pairs || []).map((pair, i) => (
              <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                <input
                  value={pair.key}
                  onChange={e => handleDataChange(i, 'key', e.target.value)}
                  placeholder="键"
                  style={{
                    flex: 1, padding: '4px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                  }}
                />
                <input
                  value={pair.value}
                  onChange={e => handleDataChange(i, 'value', e.target.value)}
                  placeholder="值"
                  style={{
                    flex: 2, padding: '4px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                  }}
                />
              </div>
            ))}
            <button onClick={handleAddDataRow} style={{ fontSize: 10, color: 'var(--accent)', border: 'none', background: 'transparent', cursor: 'pointer', padding: '2px 0' }}>
              + 添加行
            </button>
          </div>
        )}

        {entry.entry_type === 'table' && (() => {
          const tc = content as { headers?: string[]; rows?: string[][] };
          return (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                  <tr>
                    {tc.headers?.map((h, i) => (
                      <th key={i} style={{ padding: '4px 8px', borderBottom: '1px solid var(--hairline)', textAlign: 'left', fontWeight: 500, background: 'var(--canvas-soft)' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {tc.rows?.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) => (
                        <td key={ci} style={{ padding: '2px 4px', borderBottom: '1px solid var(--hairline)' }}>
                          <input
                            value={cell}
                            onChange={e => handleTableCellChange(ri, ci, e.target.value)}
                            style={{
                              width: '100%', padding: '2px 4px', fontSize: 11,
                              border: 'none', background: 'transparent', color: 'var(--ink)', outline: 'none',
                            }}
                          />
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <button onClick={handleAddTableRow} style={{ fontSize: 10, color: 'var(--accent)', border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px 0' }}>
                + 添加行
              </button>
            </div>
          );
        })()}

        {entry.entry_type === 'image' && (() => {
          const ic = content as { url?: string; caption?: string };
          return (
            <div>
              <input
                value={ic.url || ''}
                onChange={e => handleImageChange('url', e.target.value)}
                placeholder="图片 URL 或路径"
                style={{
                  width: '100%', padding: '6px 8px', fontSize: 11, borderRadius: 4,
                  border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none', marginBottom: 4,
                }}
              />
              <input
                value={ic.caption || ''}
                onChange={e => handleImageChange('caption', e.target.value)}
                placeholder="图片说明"
                style={{
                  width: '100%', padding: '6px 8px', fontSize: 11, borderRadius: 4,
                  border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                }}
              />
              {ic.url && (
                <div style={{ marginTop: 8, textAlign: 'center' }}>
                  <img
                    src={ic.url}
                    alt={ic.caption || ''}
                    style={{ maxWidth: '100%', maxHeight: 200, borderRadius: 6, border: '1px solid var(--hairline)' }}
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                </div>
              )}
            </div>
          );
        })()}

        {entry.entry_type === 'procedure' && (
          <div>
            {((content as { steps?: Array<{ text: string; checked: boolean }> }).steps || []).map((step, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <input
                  type="checkbox"
                  checked={step.checked}
                  onChange={() => handleStepToggle(i)}
                  style={{ cursor: 'pointer' }}
                />
                <span style={{ fontSize: 10, color: 'var(--mute)', minWidth: 20 }}>步骤{i + 1}</span>
                <input
                  value={step.text}
                  onChange={e => handleStepChange(i, e.target.value)}
                  placeholder="步骤描述"
                  style={{
                    flex: 1, padding: '4px 8px', fontSize: 11, borderRadius: 4,
                    border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none',
                    textDecoration: step.checked ? 'line-through' : 'none',
                    opacity: step.checked ? 0.6 : 1,
                  }}
                />
              </div>
            ))}
            <button onClick={handleAddStep} style={{ fontSize: 10, color: 'var(--accent)', border: 'none', background: 'transparent', cursor: 'pointer', padding: '2px 0' }}>
              + 添加步骤
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LabNotebookPanel;
