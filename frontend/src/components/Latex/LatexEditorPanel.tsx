/**
 * LatexEditorPanel — Feature 6.5 LaTeX 编辑器
 *
 * 分屏布局：左侧 LaTeX 源码编辑器，右侧实时预览。
 * 支持模板加载、编译为 PDF、基本 LaTeX 语法预览。
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  FileText, Play, Download, BookTemplate, ChevronDown,
  SplitSquareVertical, Eye, Code2, Loader2, AlertCircle,
} from 'lucide-react';
import { saveFile } from '@/lib/tauri-adapter';

const BASE_URL = '/api';

// ==================== LaTeX 预览渲染 ====================

/** 简易 LaTeX → HTML 转换（基础预览，非完整渲染） */
function latexToHtml(source: string): string {
  let html = source;

  // 转义 HTML 特殊字符（保留后续替换的标签）
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // \title{...} → 标题
  html = html.replace(/\\title\{([^}]*)\}/g, '<h1 style="text-align:center;font-size:1.8em;margin:16px 0;color:var(--ink)">$1</h1>');

  // \section{...} → h2
  html = html.replace(/\\section\{([^}]*)\}/g, '<h2 style="font-size:1.4em;margin:14px 0 8px;padding-bottom:4px;border-bottom:1px solid var(--hairline);color:var(--ink)">$1</h2>');

  // \subsection{...} → h3
  html = html.replace(/\\subsection\{([^}]*)\}/g, '<h3 style="font-size:1.2em;margin:10px 0 6px;color:var(--ink)">$1</h3>');

  // \subsubsection{...} → h4
  html = html.replace(/\\subsubsection\{([^}]*)\}/g, '<h4 style="font-size:1.1em;margin:8px 0 4px;color:var(--ink)">$1</h4>');

  // \chapter{...} → h2 (report 类)
  html = html.replace(/\\chapter\{([^}]*)\}/g, '<h2 style="font-size:1.6em;margin:20px 0 10px;color:var(--ink)">$1</h2>');

  // \textbf{...} → <strong>
  html = html.replace(/\\textbf\{([^}]*)\}/g, '<strong>$1</strong>');

  // \textit{...} → <em>
  html = html.replace(/\\textit\{([^}]*)\}/g, '<em>$1</em>');

  // \underline{...} → <u>
  html = html.replace(/\\underline\{([^}]*)\}/g, '<u>$1</u>');

  // $$...$$ → 块级数学公式（样式化展示）
  html = html.replace(/\$\$([^$]+)\$\$/g, (_, expr) => {
    return `<div style="padding:10px 16px;margin:10px 0;background:var(--canvas-soft, #f8f9fa);border-radius:6px;font-family:serif;font-size:1.1em;text-align:center;overflow-x:auto;border:1px solid var(--hairline);">${expr}</div>`;
  });

  // $...$ → 行内数学公式
  html = html.replace(/\$([^$]+)\$/g, (_, expr) => {
    return `<span style="padding:2px 6px;background:var(--canvas-soft, #f8f9fa);border-radius:3px;font-family:serif;font-size:0.95em;border:1px solid var(--hairline);">${expr}</span>`;
  });

  // \begin{itemize}...\end{itemize} → <ul>
  html = html.replace(/\\begin\{itemize\}([\s\S]*?)\\end\{itemize\}/g, (_, content) => {
    const items = content.replace(/\\item\s+/g, '<li>').replace(/\n/g, '</li>\n');
    return `<ul style="padding-left:20px;margin:8px 0;">${items}</li></ul>`;
  });

  // \begin{enumerate}...\end{enumerate} → <ol>
  html = html.replace(/\\begin\{enumerate\}([\s\S]*?)\\end\{enumerate\}/g, (_, content) => {
    const items = content.replace(/\\item\s+/g, '<li>').replace(/\n/g, '</li>\n');
    return `<ol style="padding-left:20px;margin:8px 0;">${items}</li></ol>`;
  });

  // \begin{abstract}...\end{abstract}
  html = html.replace(/\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}/g, (_, content) => {
    return `<div style="padding:12px 16px;margin:10px 0;background:var(--canvas-soft, #f8f9fa);border-left:3px solid var(--accent);font-style:italic;border-radius:0 6px 6px 0;">${content.trim()}</div>`;
  });

  // \begin{quote}...\end{quote}
  html = html.replace(/\\begin\{quote\}([\s\S]*?)\\end\{quote\}/g, (_, content) => {
    return `<blockquote style="padding:8px 16px;margin:8px 0;border-left:3px solid var(--accent);color:var(--mute);">${content.trim()}</blockquote>`;
  });

  // \begin{block}{...}...\end{block} (Beamer)
  html = html.replace(/\\begin\{block\}\{([^}]*)\}([\s\S]*?)\\end\{block\}/g, (_, title, content) => {
    return `<div style="padding:10px 14px;margin:8px 0;background:var(--canvas-soft, #f8f9fa);border-radius:6px;border:1px solid var(--hairline);"><strong>${title}</strong><br/>${content.trim()}</div>`;
  });

  // \begin{alertblock}{...}...\end{alertblock} (Beamer)
  html = html.replace(/\\begin\{alertblock\}\{([^}]*)\}([\s\S]*?)\\end\{alertblock\}/g, (_, title, content) => {
    return `<div style="padding:10px 14px;margin:8px 0;background:#fef2f2;border-radius:6px;border:1px solid #fca5a5;"><strong style="color:#dc2626;">${title}</strong><br/>${content.trim()}</div>`;
  });

  // \begin{frame}...\end{frame} (Beamer 幻灯片)
  html = html.replace(/\\begin\{frame\}(?:\{([^}]*)\})?([\s\S]*?)\\end\{frame\}/g, (_, title, content) => {
    const titleHtml = title ? `<h3 style="margin:0 0 8px;color:var(--accent);">${title}</h3>` : '';
    return `<div style="padding:16px 20px;margin:10px 0;background:#fff;border-radius:8px;border:1px solid var(--hairline);box-shadow:0 2px 8px rgba(0,0,0,0.06);min-height:60px;">${titleHtml}${content.trim()}</div>`;
  });

  // \maketitle
  html = html.replace(/\\maketitle/g, '<div style="text-align:center;margin:20px 0;"><hr style="border:none;border-top:1px solid var(--hairline);"/></div>');

  // \tableofcontents
  html = html.replace(/\\tableofcontents/g, '<div style="padding:10px 16px;margin:8px 0;background:var(--canvas-soft, #f8f9fa);border-radius:6px;color:var(--mute);font-style:italic;">[目录]</div>');

  // \newpage
  html = html.replace(/\\newpage/g, '<hr style="border:none;border-top:2px dashed var(--hairline);margin:20px 0;"/>');

  // 清理未识别的 LaTeX 命令（显示为灰色文本）
  html = html.replace(/\\([a-zA-Z]+)/g, (match, cmd) => {
    const known = ['usepackage', 'documentclass', 'geometry', 'begin', 'end', 'item',
      'title', 'author', 'date', 'today', 'maketitle', 'tableofcontents', 'newpage',
      'section', 'subsection', 'subsubsection', 'chapter', 'textbf', 'textit', 'underline',
      'cite', 'ref', 'label', 'bibitem', 'centering', 'hline', 'toprule', 'midrule', 'bottomrule'];
    if (known.includes(cmd)) return match;
    return `<span style="color:var(--mute);font-size:0.85em;">${match}</span>`;
  });

  // 换行处理
  html = html.replace(/\n\n+/g, '<br/><br/>');
  html = html.replace(/\n/g, '<br/>');

  return html;
}


// ==================== 模板类型 ====================

interface LatexTemplate {
  id: string;
  name: string;
  description: string;
  content?: string;
}


// ==================== 组件 ====================

export const LatexEditorPanel: React.FC = () => {
  // 状态
  const [content, setContent] = useState('% 在此输入 LaTeX 源码\n\\documentclass[12pt,a4paper]{article}\n\\usepackage[UTF8]{ctex}\n\\usepackage{amsmath}\n\n\\title{我的论文}\n\\author{作者}\n\\date{\\today}\n\n\\begin{document}\n\\maketitle\n\n\\begin{abstract}\n这是摘要。\n\\end{abstract}\n\n\\section{引言}\n爱因斯坦质能方程 $E = mc^2$ 是物理学最著名的公式之一。\n\n块级公式示例：\n$$\\int_a^b f(x)\\,dx = F(b) - F(a)$$\n\n\\section{方法}\n\\textbf{重点内容}和\\textit{斜体内容}。\n\n\\begin{itemize}\n  \\item 第一个要点\n  \\item 第二个要点\n  \\item 第三个要点\n\\end{itemize}\n\n\\section{结论}\n结论内容。\n\n\\end{document}');
  const [previewHtml, setPreviewHtml] = useState('');
  const [compiling, setCompiling] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const [viewMode, setViewMode] = useState<'split' | 'edit' | 'preview'>('split');
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const [templates, setTemplates] = useState<LatexTemplate[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 显示提示
  const showToast = useCallback((msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // 加载模板列表
  useEffect(() => {
    fetch(`${BASE_URL}/latex/templates`)
      .then(r => r.json())
      .then(data => {
        if (data.templates) setTemplates(data.templates);
      })
      .catch(() => {
        // 回退到硬编码模板
        setTemplates([
          { id: 'article', name: '学术论文 (Article)', description: '标准学术论文模板' },
          { id: 'report', name: '研究报告 (Report)', description: '较长的文档模板' },
          { id: 'beamer', name: '学术演示 (Beamer)', description: 'Beamer 幻灯片模板' },
        ]);
      });
  }, []);

  // 实时预览
  useEffect(() => {
    const timer = setTimeout(() => {
      setPreviewHtml(latexToHtml(content));
    }, 300);
    return () => clearTimeout(timer);
  }, [content]);

  // 加载模板内容
  const handleLoadTemplate = useCallback(async (templateId: string) => {
    try {
      const res = await fetch(`${BASE_URL}/latex/templates/${templateId}`);
      const data = await res.json();
      if (data.content) {
        setContent(data.content);
        setSelectedTemplate(templateId);
        showToast(`已加载模板: ${data.name}`, 'success');
      }
    } catch {
      showToast('加载模板失败', 'error');
    }
    setShowTemplateMenu(false);
  }, [showToast]);

  // 编译为 PDF
  const handleCompile = useCallback(async () => {
    if (!content.trim()) {
      showToast('LaTeX 源码为空', 'error');
      return;
    }
    setCompiling(true);
    try {
      const res = await fetch(`${BASE_URL}/latex/compile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latex_source: content, engine: 'xelatex' }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '编译失败' }));
        const msg = typeof err.detail === 'string'
          ? err.detail
          : err.detail?.message || JSON.stringify(err.detail);
        showToast(`编译失败: ${msg}`, 'error');
        return;
      }

      // 下载 PDF
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'output.pdf';
      a.click();
      URL.revokeObjectURL(url);
      showToast('PDF 编译成功，已下载', 'success');
    } catch (e: unknown) {
      showToast(`编译出错: ${e instanceof Error ? e.message : String(e)}`, 'error');
    } finally {
      setCompiling(false);
    }
  }, [content, showToast]);

  // 导出 .tex 文件
  const handleExportTex = useCallback(async () => {
    try {
      await saveFile(content, {
        filters: [{ name: 'LaTeX', extensions: ['tex'] }],
        defaultPath: 'document.tex',
      });
      showToast('已导出 .tex 文件', 'success');
    } catch {
      showToast('导出失败', 'error');
    }
  }, [content, showToast]);

  // Tab 键支持
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newContent = content.substring(0, start) + '  ' + content.substring(end);
      setContent(newContent);
      // 恢复光标位置
      requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
      });
    }
    // Ctrl+S 保存
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleExportTex();
    }
  }, [content, handleExportTex]);

  // 行号计算
  const lineCount = content.split('\n').length;

  // 样式变量
  const glassBg = 'rgba(255,255,255,0.6)';
  const glassBlur = '12px';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--canvas-soft)', color: 'var(--ink)' }}>
      {/* ── 工具栏 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '6px 12px',
        borderBottom: '1px solid var(--hairline)',
        background: glassBg,
        backdropFilter: `blur(${glassBlur})`,
      }}>
        {/* 视图切换 */}
        <div style={{ display: 'flex', gap: 2, background: 'var(--canvas)', borderRadius: 6, padding: 2 }}>
          {([
            { key: 'edit', icon: <Code2 size={14} />, label: '编辑' },
            { key: 'split', icon: <SplitSquareVertical size={14} />, label: '分屏' },
            { key: 'preview', icon: <Eye size={14} />, label: '预览' },
          ] as const).map(({ key, icon, label }) => (
            <button
              key={key}
              onClick={() => setViewMode(key)}
              style={{
                display: 'flex', alignItems: 'center', gap: 3,
                padding: '3px 10px', fontSize: 11, borderRadius: 4,
                border: 'none', cursor: 'pointer',
                background: viewMode === key ? 'var(--accent)' : 'transparent',
                color: viewMode === key ? '#fff' : 'var(--ink)',
                transition: 'all 0.15s',
              }}
            >
              {icon} {label}
            </button>
          ))}
        </div>

        <div style={{ width: 1, height: 20, background: 'var(--hairline)' }} />

        {/* 模板选择 */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowTemplateMenu(!showTemplateMenu)}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '4px 12px', fontSize: 11, borderRadius: 6,
              border: '1px solid var(--hairline)', background: 'transparent',
              color: 'var(--ink)', cursor: 'pointer',
            }}
          >
            <BookTemplate size={13} /> 模板 <ChevronDown size={12} />
          </button>
          {showTemplateMenu && (
            <div style={{
              position: 'absolute', left: 0, top: '100%', marginTop: 4,
              background: glassBg, backdropFilter: `blur(${glassBlur})`,
              border: '1px solid var(--hairline)', borderRadius: 8,
              padding: 6, minWidth: 220, zIndex: 50,
              boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            }}
              onMouseLeave={() => setShowTemplateMenu(false)}
            >
              {templates.map(tpl => (
                <button
                  key={tpl.id}
                  onClick={() => handleLoadTemplate(tpl.id)}
                  style={{
                    display: 'block', width: '100%', textAlign: 'left',
                    padding: '8px 12px', fontSize: 12, borderRadius: 4,
                    border: 'none', background: selectedTemplate === tpl.id ? 'var(--accent-bg-soft)' : 'transparent',
                    color: 'var(--ink)', cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-bg-soft)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = selectedTemplate === tpl.id ? 'var(--accent-bg-soft)' : 'transparent'; }}
                >
                  <div style={{ fontWeight: 500 }}>{tpl.name}</div>
                  <div style={{ fontSize: 10, color: 'var(--mute)', marginTop: 2 }}>{tpl.description}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div style={{ flex: 1 }} />

        {/* 导出 .tex */}
        <button
          onClick={handleExportTex}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 12px', fontSize: 11, borderRadius: 6,
            border: '1px solid var(--hairline)', background: 'transparent',
            color: 'var(--ink)', cursor: 'pointer',
          }}
        >
          <FileText size={13} /> 导出 .tex
        </button>

        {/* 编译按钮 */}
        <button
          onClick={handleCompile}
          disabled={compiling}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 16px', fontSize: 12, borderRadius: 6,
            border: 'none', background: 'var(--accent)', color: '#fff',
            cursor: compiling ? 'not-allowed' : 'pointer',
            opacity: compiling ? 0.6 : 1,
          }}
        >
          {compiling ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
          {compiling ? '编译中...' : '编译 PDF'}
        </button>
      </div>

      {/* ── 主内容区 ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 编辑器 */}
        {(viewMode === 'edit' || viewMode === 'split') && (
          <div style={{
            ...(viewMode === 'split' ? { width: '50%' } : { flex: 1 }),
            display: 'flex', overflow: 'hidden',
            borderRight: viewMode === 'split' ? '1px solid var(--hairline)' : 'none',
          }}>
            {/* 行号 */}
            <div style={{
              padding: '12px 8px', textAlign: 'right', userSelect: 'none',
              fontFamily: 'monospace', fontSize: 12, lineHeight: '1.6',
              color: 'var(--mute)', background: 'var(--canvas)',
              minWidth: 40, borderRight: '1px solid var(--hairline)',
              overflow: 'hidden',
            }}>
              {Array.from({ length: lineCount }, (_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>
            {/* 文本编辑区 */}
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck={false}
              style={{
                flex: 1, padding: '12px', border: 'none', outline: 'none',
                fontFamily: "'Consolas', 'Fira Code', 'Source Code Pro', monospace",
                fontSize: 13, lineHeight: '1.6', resize: 'none',
                background: 'var(--canvas)', color: 'var(--ink)',
                tabSize: 2,
              }}
              placeholder="在此输入 LaTeX 源码..."
            />
          </div>
        )}

        {/* 预览区 */}
        {(viewMode === 'preview' || viewMode === 'split') && (
          <div style={{
            ...(viewMode === 'split' ? { width: '50%' } : { flex: 1 }),
            overflow: 'auto', padding: '20px 24px',
            background: 'var(--canvas)',
          }}>
            <div style={{
              maxWidth: 800, margin: '0 auto',
              fontSize: 14, lineHeight: '1.8',
            }}
              dangerouslySetInnerHTML={{ __html: previewHtml || '<div style="color:var(--mute);font-style:italic;">预览区域 — 在左侧输入 LaTeX 源码</div>' }}
            />
          </div>
        )}
      </div>

      {/* ── 状态栏 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '3px 12px', fontSize: 11, color: 'var(--mute)',
        borderTop: '1px solid var(--hairline)',
        background: glassBg,
      }}>
        <span>行: {lineCount}</span>
        <span>字符: {content.length}</span>
        <span>引擎: XeLaTeX</span>
        {selectedTemplate && <span>模板: {selectedTemplate}</span>}
      </div>

      {/* ── Toast ── */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24,
          padding: '10px 20px', borderRadius: 8, fontSize: 13, zIndex: 9999,
          display: 'flex', alignItems: 'center', gap: 8,
          background: toast.type === 'error' ? '#fef2f2' : '#f0fdf4',
          color: toast.type === 'error' ? '#991b1b' : '#166534',
          border: `1px solid ${toast.type === 'error' ? '#fca5a5' : '#86efac'}`,
          boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
          animation: 'fadeIn 0.2s',
        }}>
          {toast.type === 'error' ? <AlertCircle size={16} /> : <Download size={16} />}
          {toast.msg}
        </div>
      )}
    </div>
  );
};

export default LatexEditorPanel;
