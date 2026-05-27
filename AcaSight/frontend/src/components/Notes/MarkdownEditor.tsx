/**
 * MarkdownEditor — Milkdown WYSIWYG 编辑器 (Chapter D)
 *
 * 基于 Milkdown v7，替代 react-markdown textarea 方案。
 * 支持 LaTeX 数学公式实时渲染、代码高亮、分屏预览、导出 Word/LaTeX/PDF。
 *
 * LaTeX 公式输入格式：
 *   - 行内公式: $E = mc^2$
 *   - 块级公式: $$\int_a^b f(x)dx$$
 *
 * 技术架构：
 *   Milkdown (WYSIWYG core) + math plugin (KaTeX 公式渲染)
 *   + prism plugin (代码高亮) + react-markdown (分屏预览)
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Editor, rootCtx, defaultValueCtx } from '@milkdown/core';
import { commonmark } from '@milkdown/preset-commonmark';
import { gfm } from '@milkdown/preset-gfm';
import { math } from '@milkdown/plugin-math';
import { prism } from '@milkdown/plugin-prism';
import { history } from '@milkdown/plugin-history';
import { listener, listenerCtx } from '@milkdown/plugin-listener';
import { nord } from '@milkdown/theme-nord';
import { Milkdown, MilkdownProvider, useEditor } from '@milkdown/react';
import '@milkdown/theme-nord/style.css';
import 'katex/dist/katex.min.css';

import {
  FileDown, Save, Undo2, Redo2,
} from 'lucide-react';
import { useApp } from '@/contexts/AppContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';

export interface MarkdownEditorProps {
  noteId?: string;
  initialContent?: string;
  onSave?: (id: string, content: string) => void;
}

// ── Inner Editor ──

interface MilkEditorInnerProps {
  content: string;
  setContent: (c: string) => void;
  saving: boolean;
  onSave: () => void;
  exporting: boolean;
  selectedCsl: string;
  setSelectedCsl: (s: string) => void;
  cslStyles: { id: string; name: string }[];
  showExportMenu: boolean;
  setShowExportMenu: (v: boolean) => void;
  handleFormatExport: (fmt: 'docx' | 'latex' | 'pdf') => void;
  toast: { msg: string; type: string } | null;
  activeTab: 'edit' | 'preview' | 'split';
  setActiveTab: (t: 'edit' | 'preview' | 'split') => void;
}

const MilkEditorInner: React.FC<MilkEditorInnerProps> = ({
  content, setContent, saving, onSave, exporting,
  selectedCsl, setSelectedCsl, cslStyles,
  showExportMenu, setShowExportMenu, handleFormatExport,
  toast, activeTab, setActiveTab,
}) => {
  useEditor((root) => {
    return (Editor.make() as any)
      .config((ctx: any) => {
        ctx.set(rootCtx, root);
        ctx.set(defaultValueCtx, content);
        ctx.get(listenerCtx).markdownUpdated((_: any, md: string) => {
          setContent(md);
        });
      })
      .use(nord)
      .use(commonmark)
      .use(gfm)
      .use(math)
      .use(prism)
      .use(history)
      .use(listener);
  }, []);

  const handleUndo = useCallback(() => { document.execCommand('undo'); }, []);
  const handleRedo = useCallback(() => { document.execCommand('redo'); }, []);

  const handleKeySave = useCallback((e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      onSave();
    }
  }, [onSave]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeySave);
    return () => window.removeEventListener('keydown', handleKeySave);
  }, [handleKeySave]);

  const tabBtnStyle = (active: boolean) =>
    `px-3 py-1.5 text-xs font-medium border-none bg-transparent cursor-pointer transition-colors ${active ? 'border-b-2 border-[var(--accent)] text-[var(--ink)]' : 'text-[var(--mute)] hover:text-[var(--ink)]'}`;

  const btnHoverBg = (el: HTMLButtonElement) => { el.style.background = 'var(--canvas-soft-2)'; };
  const btnHoverReset = (el: HTMLButtonElement) => { el.style.background = 'transparent'; };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--canvas-soft)', color: 'var(--ink)' }}>
      {/* Toolbar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderBottom: '1px solid var(--hairline)' }}>
        <button title="撤销 (Ctrl+Z)" onClick={handleUndo}
          className="mk-toolbar-btn" onMouseEnter={(e) => btnHoverBg(e.currentTarget)} onMouseLeave={(e) => btnHoverReset(e.currentTarget)}>
          <Undo2 size={14} />
        </button>
        <button title="重做 (Ctrl+Y)" onClick={handleRedo}
          className="mk-toolbar-btn" onMouseEnter={(e) => btnHoverBg(e.currentTarget)} onMouseLeave={(e) => btnHoverReset(e.currentTarget)}>
          <Redo2 size={14} />
        </button>

        <div style={{ flex: 1 }} />

        <button onClick={onSave} disabled={saving}
          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 14px', fontSize: 12, borderRadius: 6, background: 'var(--accent)', color: '#fff', border: 'none', cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1 }}>
          <Save size={13} /> {saving ? '保存中...' : '保存'}
        </button>

        <div style={{ position: 'relative' }}>
          <button onClick={() => setShowExportMenu(!showExportMenu)} disabled={exporting}
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 14px', fontSize: 12, borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', opacity: exporting ? 0.6 : 1 }}>
            <FileDown size={13} /> 导出
          </button>
          {showExportMenu && (
            <div style={{ position: 'absolute', right: 0, top: '100%', marginTop: 6, background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))', border: '1px solid var(--hairline)', borderRadius: 8, padding: 8, minWidth: 200, zIndex: 50, boxShadow: 'var(--glass-shadow)' }}
              onMouseLeave={() => setShowExportMenu(false)}>
              {cslStyles.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 2 }}>引用格式</div>
                  <select value={selectedCsl} onChange={e => setSelectedCsl(e.target.value)}
                    style={{ width: '100%', padding: 3, borderRadius: 4, border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', fontSize: 11 }}>
                    <option value="">无</option>
                    {cslStyles.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
              )}
              {(['docx', 'latex', 'pdf'] as const).map(fmt => (
                <button key={fmt} onClick={() => { handleFormatExport(fmt); setShowExportMenu(false); }} disabled={exporting}
                  className="mk-export-item"
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-bg-soft)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}>
                  <FileDown size={12} /> 导出 {fmt === 'docx' ? 'Word (.docx)' : fmt === 'latex' ? 'LaTeX (.tex)' : 'PDF (.pdf)'}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', padding: '0 10px', borderBottom: '1px solid var(--hairline)' }}>
        {(['edit', 'split', 'preview'] as const).map(t => (
          <button key={t} onClick={() => setActiveTab(t)} className={tabBtnStyle(activeTab === t)}>
            {t === 'edit' ? '编辑' : t === 'split' ? '分屏' : '预览'}
          </button>
        ))}
      </div>

      {/* Body */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {(activeTab === 'edit' || activeTab === 'split') && (
          <div style={activeTab === 'split' ? { width: '50%', borderRight: '1px solid var(--hairline)', overflow: 'auto' } : { flex: 1, overflow: 'auto' }}
            className="mk-editor-wrapper">
            <Milkdown />
          </div>
        )}

        {(activeTab === 'preview' || activeTab === 'split') && (
          <div style={activeTab === 'split' ? { width: '50%', overflow: 'auto' } : { flex: 1, overflow: 'auto' }}>
            <div style={{ padding: 20 }}>
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex, rehypeHighlight]}>
                {content || '*开始输入 Markdown 内容...*'}
              </ReactMarkdown>
            </div>
          </div>
        )}
      </div>

      {toast && (
        <div style={{ position: 'fixed', bottom: 24, right: 24, padding: '8px 18px', borderRadius: 8, fontSize: 13, zIndex: 9999, animation: 'fadeIn 0.2s', background: toast.type === 'error' ? '#fee2e2' : '#d1fae5', color: toast.type === 'error' ? '#991b1b' : '#065f46', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
};

// ── Outer Component ──

export const MarkdownEditor: React.FC<MarkdownEditorProps> = ({
  noteId,
  initialContent = '',
  onSave,
}) => {
  const [content, setContent] = useState(initialContent);
  const [activeTab, setActiveTab] = useState<'edit' | 'preview' | 'split'>('edit');
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: string } | null>(null);
  const { pendingNoteContent, setPendingNoteContent } = useApp();
  const [cslStyles, setCslStyles] = useState<{ id: string; name: string }[]>([]);
  const [selectedCsl, setSelectedCsl] = useState('');
  const [showExportMenu, setShowExportMenu] = useState(false);

  useEffect(() => {
    if (pendingNoteContent) {
      setContent(prev => prev ? prev + '\n\n---\n\n' + pendingNoteContent : pendingNoteContent);
      setPendingNoteContent('');
      setActiveTab('edit');
    }
  }, [pendingNoteContent, setPendingNoteContent]);

  useEffect(() => {
    fetch('http://localhost:9000/api/format/styles')
      .then(r => r.json())
      .then(d => { if (d.styles) setCslStyles(d.styles); })
      .catch(() => {});
  }, []);

  const showToast = (msg: string, type: string) => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSave = async () => {
    if (!content.trim()) { showToast('内容为空', 'error'); return; }
    setSaving(true);
    try {
      const title = content.split('\n').find(l => l.startsWith('#'))?.replace(/^#+\s*/, '') || 'Untitled';
      const resp = await fetch('http://localhost:9000/api/notes/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_id: noteId || null, content, title }),
      });
      const data = await resp.json();
      showToast('笔记已保存', 'success');
      onSave?.(data.id, content);
    } catch (e: any) { showToast('保存失败: ' + e.message, 'error'); }
    finally { setSaving(false); }
  };

  const handleFormatExport = async (format: 'docx' | 'latex' | 'pdf') => {
    setExporting(true);
    try {
      const title = content.split('\n').find(l => l.startsWith('#'))?.replace(/^#+\s*/, '') || 'document';
      const resp = await fetch('http://localhost:9000/api/format/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown: content, title, format, csl_style: selectedCsl || null }),
      });
      if (!resp.ok) { const err = await resp.json().catch(() => ({})); throw new Error(err.detail || `导出失败 (${resp.status})`); }
      const blob = await resp.blob();
      const ext = format === 'docx' ? 'docx' : format === 'latex' ? 'tex' : 'pdf';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${title}.${ext}`; a.click();
      URL.revokeObjectURL(url);
      showToast(`${format.toUpperCase()} 已导出`, 'success');
    } catch (e: any) { showToast('导出失败: ' + e.message, 'error'); }
    finally { setExporting(false); }
  };

  return (
    <MilkdownProvider>
      <MilkEditorInner
        content={content} setContent={setContent}
        saving={saving} onSave={handleSave}
        exporting={exporting} selectedCsl={selectedCsl} setSelectedCsl={setSelectedCsl}
        cslStyles={cslStyles} showExportMenu={showExportMenu} setShowExportMenu={setShowExportMenu}
        handleFormatExport={handleFormatExport} toast={toast}
        activeTab={activeTab} setActiveTab={setActiveTab}
      />
    </MilkdownProvider>
  );
};