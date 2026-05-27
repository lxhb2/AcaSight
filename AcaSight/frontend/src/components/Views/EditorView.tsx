/**
 * EditorView — PDF/Markdown 编辑器面板
 *
 * 从 ObsidianLayout 拆分出的独立组件。
 * 包含多标签管理、PDF 渲染、AI 助手侧栏、笔记侧栏、目录侧栏。
 */

import React from 'react';
import { Document, Page } from 'react-pdf';
import 'react-pdf/dist/esm/Page/TextLayer.css';
import {
  X, Plus, ZoomIn, ZoomOut,
  FileText, FileCode, Upload, Download,
  Loader2, Highlighter,
  Clock, Trash2, Save, MessageSquare,
  Eraser, MessageCircle,
} from 'lucide-react';
import { useApp } from '@/contexts/AppContext';
import AnnotationOverlay from '@/components/AnnotationOverlay';
import { OutlineView } from '@/components/Views/OutlineView';

export const EditorView: React.FC = () => {
  const {
    editorTabs, activeTabId,
    pdfFile, pdfFullText, setPdfFullText, pdfDocRef, pdfTextPagesRef,
    numPages, setNumPages, currentPage, setCurrentPage, scale, setScale,
    showAIPanel, editorRightTab,
    fileInputRef,
    annotations,
    annotationTool, setAnnotationTool, annotationColor, setAnnotationColor,
  } = useApp();

  const activeTab = editorTabs.find(t => t.id === activeTabId);

  // ---- Empty State ----
  if (!activeTab) {
    return (
      <div className="acasight-empty">
        <Upload size={48} />
        <p>打开 PDF 文件或从文献树选择论文</p>
        <button onClick={() => fileInputRef.current?.click()} style={{ marginTop: 8, padding: '8px 16px', borderRadius: 'var(--radius-sm)', background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13 }}>选择 PDF 文件</button>
      </div>
    );
  }

  // ---- Markdown Tab ----
  if (activeTab.type === 'md') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <EditorTabBar />
        <div className="acasight-editor-content">
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8, color: 'var(--ink)' }}>{activeTab.name.replace('.md', '')}</h1>
          <p style={{ color: 'var(--body)' }}>Markdown 笔记编辑器（开发中）</p>
        </div>
      </div>
    );
  }

  // ---- PDF Tab ----
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <EditorTabBar />

      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* PDF Scroll Container */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Annotation Toolbar */}
          {pdfFile && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '4px 8px',
              borderBottom: '1px solid var(--hairline)',
              background: 'var(--glass-bg)',
              backdropFilter: 'blur(var(--glass-blur))',
              WebkitBackdropFilter: 'blur(var(--glass-blur))',
            }}>
              <span style={{ fontSize: 11, color: 'var(--mute)', marginRight: 4 }}>标注</span>
              <div style={{ width: 1, height: 16, background: 'var(--hairline)', margin: '0 2px' }} />
              {/* Highlight buttons - 4 colors */}
              {[
                { color: '#FFEB3B', label: '黄色高亮' },
                { color: '#66BB6A', label: '绿色高亮' },
                { color: '#42A5F5', label: '蓝色高亮' },
                { color: '#F48FB1', label: '粉色高亮' },
              ].map(({ color, label }) => (
                <button
                  key={color}
                  title={label}
                  onClick={() => {
                    setAnnotationTool(annotationTool === 'highlight' && annotationColor === color ? null : 'highlight');
                    setAnnotationColor(color);
                  }}
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 4,
                    border: annotationTool === 'highlight' && annotationColor === color ? '2px solid var(--ink)' : '2px solid transparent',
                    background: color,
                    cursor: 'pointer',
                    opacity: annotationTool === 'eraser' ? 0.4 : 1,
                    transition: 'all 0.15s',
                  }}
                />
              ))}
              <div style={{ width: 1, height: 16, background: 'var(--hairline)', margin: '0 2px' }} />
              {/* Underline button */}
              <button
                title="下划线"
                onClick={() => setAnnotationTool(annotationTool === 'underline' ? null : 'underline')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 28,
                  height: 22,
                  borderRadius: 4,
                  border: 'none',
                  background: annotationTool === 'underline' ? 'var(--accent-bg-soft)' : 'transparent',
                  cursor: 'pointer',
                  color: annotationTool === 'underline' ? 'var(--accent)' : 'var(--body)',
                  borderBottom: annotationTool === 'underline' ? '3px solid var(--accent)' : '3px solid var(--body)',
                  fontWeight: 'bold',
                  fontSize: 12,
                  transition: 'all 0.15s',
                }}
              >
                U
              </button>
              {/* Text annotation button */}
              <button
                title="文本注释"
                onClick={() => setAnnotationTool(annotationTool === 'note' ? null : 'note')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 28,
                  height: 22,
                  borderRadius: 4,
                  border: 'none',
                  background: annotationTool === 'note' ? 'var(--accent-bg-soft)' : 'transparent',
                  cursor: 'pointer',
                  color: annotationTool === 'note' ? 'var(--accent)' : 'var(--body)',
                  transition: 'all 0.15s',
                }}
              >
                <MessageCircle size={14} />
              </button>
              <div style={{ width: 1, height: 16, background: 'var(--hairline)', margin: '0 2px' }} />
              {/* Eraser button */}
              <button
                title="橡皮擦（删除标注）"
                onClick={() => setAnnotationTool(annotationTool === 'eraser' ? null : 'eraser')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 28,
                  height: 22,
                  borderRadius: 4,
                  border: 'none',
                  background: annotationTool === 'eraser' ? 'var(--accent-bg-soft)' : 'transparent',
                  cursor: 'pointer',
                  color: annotationTool === 'eraser' ? 'var(--accent)' : 'var(--body)',
                  transition: 'all 0.15s',
                }}
              >
                <Eraser size={14} />
              </button>
              {annotationTool && (
                <>
                  <div style={{ width: 1, height: 16, background: 'var(--hairline)', margin: '0 2px' }} />
                  <span style={{ fontSize: 10, color: 'var(--accent)' }}>
                    {annotationTool === 'highlight' ? '高亮模式' : annotationTool === 'underline' ? '下划线模式' : annotationTool === 'note' ? '注释模式' : '擦除模式'}
                  </span>
                </>
              )}
            </div>
          )}
          {/* PDF Scroll Area */}
          <div
            id="pdf-scroll-container"
            style={{ flex: 1, overflow: 'auto', position: 'relative', userSelect: 'text', cursor: annotationTool ? 'crosshair' : 'text', display: 'flex', flexDirection: 'column', alignItems: 'center' }}
          onScroll={(e) => {
            const container = e.currentTarget;
            const pages = container.querySelectorAll('.react-pdf__Page');
            let closestPage = 1;
            let minDistance = Infinity;
            const containerTop = container.scrollTop;
            pages.forEach((page, idx) => {
              const rect = page.getBoundingClientRect();
              const pageTop = rect.top - container.getBoundingClientRect().top + containerTop;
              const distance = Math.abs(pageTop - containerTop);
              if (distance < minDistance) { minDistance = distance; closestPage = idx + 1; }
            });
            if (closestPage !== currentPage) setCurrentPage(closestPage);
          }}
          onWheel={(e) => {
            if (e.ctrlKey) {
              e.preventDefault();
              e.stopPropagation();
              setScale(s => Math.min(3, Math.max(0.5, s - e.deltaY * 0.002)));
            }
          }}
        >
          {!pdfFile ? (
            <PDFEmptyState />
          ) : (
            <Document
              file={pdfFile}
              onLoadSuccess={(pdf: any) => { setNumPages(pdf.numPages); pdfDocRef.current = pdf; }}
              loading={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, color: 'var(--mute)' }}><Loader2 className="animate-spin" style={{ marginRight: 8 }} />加载 PDF...</div>}
            >
              {Array.from({ length: numPages }, (_, i) => (
                <div key={i + 1} className="pdf-page-wrapper" style={{ position: 'relative', margin: '0 auto', lineHeight: 0, fontSize: 0 }}>
                  <Page
                    pageNumber={i + 1}
                    scale={scale}
                    renderTextLayer
                    renderAnnotationLayer={false}
                    onRenderSuccess={() => {
                      const pageNum = i + 1;
                      if (!pdfFullText && !pdfTextPagesRef.current.has(pageNum) && pdfDocRef.current) {
                        pdfDocRef.current.getPage(pageNum).then((page: any) => {
                          page.getTextContent().then((content: any) => {
                            const pageText = content.items.map((item: any) => item.str).join(' ');
                            pdfTextPagesRef.current.add(pageNum);
                            setPdfFullText((prev: string) => prev + (prev ? ' ' : '') + pageText);
                          });
                        });
                      }
                      if (pageNum === currentPage) {
                        const el = document.querySelector(`[data-page-number="${pageNum}"]`);
                        el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                      }
                    }}
                  />
                  <AnnotationOverlay
                    pageNumber={i + 1}
                    pageWidth={612}  // US Letter default; react-pdf adjusts by scale
                    pageHeight={792}
                    scale={scale}
                  />
                </div>
              ))}
            </Document>
          )}

          {/* Bottom PDF Toolbar */}
          {pdfFile && (
            <div style={{ position: 'fixed', bottom: 16, left: '50%', transform: 'translateX(-50%)', display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px', borderRadius: 'var(--radius-md)', background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))', WebkitBackdropFilter: 'blur(var(--glass-blur))', border: '1px solid var(--hairline)', boxShadow: 'var(--glass-shadow)', zIndex: 10 }}>
              <span style={{ fontSize: 12, minWidth: 60, textAlign: 'center', color: 'var(--ink)' }}>{currentPage}/{numPages}</span>
              <div style={{ width: 1, height: 14, background: 'var(--hairline)' }} />
              <button onClick={() => setScale(s => Math.max(0.5, s - 0.1))} style={{ color: 'var(--icon-color)', background: 'none', border: 'none', cursor: 'pointer' }}><ZoomOut size={14} /></button>
              <span style={{ fontSize: 11, minWidth: 36, textAlign: 'center', color: 'var(--ink)' }}>{Math.round(scale * 100)}%</span>
              <button onClick={() => setScale(s => Math.min(3, s + 0.1))} style={{ color: 'var(--icon-color)', background: 'none', border: 'none', cursor: 'pointer' }}><ZoomIn size={14} /></button>
              {annotations.length > 0 && (
                <>
                  <div style={{ width: 1, height: 14, background: 'var(--hairline)' }} />
                  <span style={{ fontSize: 11, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 3 }}>
                    <Highlighter size={12} />{annotations.length}
                  </span>
                </>
              )}
            </div>
          )}
        </div>
        </div>

        {/* Right AI/Notes/TOC Panel */}
        {showAIPanel && (
          <div style={{ width: 280, display: 'flex', flexDirection: 'column', borderLeft: '1px solid var(--hairline)', background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))', WebkitBackdropFilter: 'blur(var(--glass-blur))' }}>
            <RightPanelTabs />
            <div style={{ flex: 1, overflow: 'hidden' }}>
              {editorRightTab === 'notes' && <NotesPanel />}
              {editorRightTab === 'toc' && <OutlineView />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ==================== Sub-Components ====================

/** Editor Tab Bar */
const EditorTabBar: React.FC = () => {
  const { editorTabs, activeTabId, setActiveTabId, closeTab, fileInputRef } = useApp();
  return (
    <div className="acasight-editor-tabs">
      {editorTabs.map(tab => (
        <div key={tab.id} className={`acasight-editor-tab ${tab.id === activeTabId ? 'active' : ''}`} onClick={() => setActiveTabId(tab.id)}>
          {tab.type === 'pdf' ? <FileText size={12} /> : <FileCode size={12} />}
          <span>{tab.name}</span>
          <span className="acasight-editor-tab-close" onClick={e => { e.stopPropagation(); closeTab(tab.id); }}><X size={10} /></span>
        </div>
      ))}
      <div style={{ width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', color: 'var(--mute)' }} onClick={() => fileInputRef.current?.click()}><Plus size={14} /></div>
    </div>
  );
};

/** PDF Empty State */
const PDFEmptyState: React.FC = () => {
  const { activeTabId, editorTabs, setPdfFile, fileInputRef } = useApp();
  const activeTab = editorTabs.find(t => t.id === activeTabId);
  if (!activeTab) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: 32 }}>
      <div style={{ maxWidth: 520, width: '100%', textAlign: 'center' }}>
        <FileText size={48} style={{ color: 'var(--mute)', margin: '0 auto 12px' }} />
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--ink)', marginBottom: 4, lineHeight: 1.4 }}>{activeTab.name.replace(/\.pdf$/, '')}</h2>
        {activeTab.authors && <p style={{ fontSize: 13, color: 'var(--body)', marginBottom: 4 }}>{activeTab.authors}</p>}
        {activeTab.journal && <p style={{ fontSize: 12, color: 'var(--mute)', marginBottom: 8 }}>{activeTab.journal}{activeTab.year ? ` · ${activeTab.year}` : ''}</p>}
        {activeTab.abstract && (
          <div style={{ textAlign: 'left', background: 'var(--canvas-soft)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)', border: '1px solid var(--hairline)', borderRadius: 'var(--radius-sm)', padding: 12, marginBottom: 16, maxHeight: 200, overflow: 'auto' }}>
            <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>摘要</p>
            <p style={{ fontSize: 13, color: 'var(--body)', lineHeight: 1.6 }}>{activeTab.abstract}</p>
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
          <button onClick={() => fileInputRef.current?.click()} style={{ padding: '8px 16px', borderRadius: 'var(--radius-sm)', background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}><Upload size={14} />上传本地 PDF</button>
          {activeTab.pdfUrl && (
            <button onClick={() => {
              const proxyUrl = `http://localhost:9000/api/pdf/proxy?url=${encodeURIComponent(activeTab.pdfUrl!)}`;
              setPdfFile(proxyUrl);
            }} style={{ padding: '8px 16px', borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', color: 'var(--ink)', border: '1px solid var(--hairline)', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}><Download size={14} />在线加载全文</button>
          )}
        </div>
      </div>
    </div>
  );
};

/** Right Panel Tab Switcher */
const RightPanelTabs: React.FC = () => {
  const { editorRightTab, setEditorRightTab } = useApp();
  return (
    <div style={{ display: 'flex', borderBottom: '1px solid var(--hairline)' }}>
      {([{ id: 'notes' as const, label: '笔记' }, { id: 'toc' as const, label: '目录' }]).map(t => (
        <button key={t.id} onClick={() => setEditorRightTab(t.id)} style={{ flex: 1, padding: '8px 0', fontSize: 12, fontWeight: editorRightTab === t.id ? 600 : 400, color: editorRightTab === t.id ? 'var(--ink)' : 'var(--mute)', background: 'none', border: 'none', borderBottom: editorRightTab === t.id ? '2px solid var(--accent)' : '2px solid transparent', cursor: 'pointer', transition: 'all 0.15s', whiteSpace: 'nowrap' }}>{t.label}</button>
      ))}
    </div>
  );
};

/** Notes Panel */
const NotesPanel: React.FC = () => {
  const { notes, addNote, deleteNote } = useApp();
  const [newNote, setNewNote] = React.useState('');
  const [newNoteTags, setNewNoteTags] = React.useState('');
  const [isAddingNote, setIsAddingNote] = React.useState(false);

  const handleAddNote = () => {
    if (!newNote.trim()) return;
    addNote(newNote, newNoteTags.split(',').map(t => t.trim()).filter(Boolean));
    setNewNote('');
    setNewNoteTags('');
    setIsAddingNote(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {isAddingNote ? (
        <div style={{ padding: 8, borderBottom: '1px solid var(--hairline)' }}>
          <textarea value={newNote} onChange={e => setNewNote(e.target.value)} placeholder="输入笔记内容..." style={{ width: '100%', height: 60, background: 'var(--canvas-soft)', backdropFilter: 'blur(8px)', border: '1px solid var(--hairline)', borderRadius: 'var(--radius-sm)', padding: 6, color: 'var(--ink)', fontSize: 12, resize: 'none', outline: 'none' }} autoFocus />
          <input value={newNoteTags} onChange={e => setNewNoteTags(e.target.value)} placeholder="标签 (逗号分隔)" style={{ width: '100%', height: 24, background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', borderRadius: 'var(--radius-xs)', padding: '0 6px', color: 'var(--ink)', fontSize: 11, outline: 'none', marginTop: 4 }} />
          <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end', marginTop: 4 }}>
            <button onClick={() => setIsAddingNote(false)} style={{ fontSize: 11, color: 'var(--mute)', background: 'none', border: 'none', cursor: 'pointer' }}>取消</button>
            <button onClick={handleAddNote} disabled={!newNote.trim()} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 'var(--radius-xs)', background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 2, opacity: !newNote.trim() ? 0.5 : 1 }}><Save size={10} />保存</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setIsAddingNote(true)} style={{ margin: 8, padding: 8, borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', border: '1px dashed var(--hairline)', color: 'var(--mute)', fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}><Plus size={14} />添加笔记</button>
      )}
      <div style={{ flex: 1, overflow: 'auto', padding: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {notes.length === 0 && <div style={{ textAlign: 'center', marginTop: 24, color: 'var(--mute)', fontSize: 12 }}><MessageSquare size={24} style={{ opacity: 0.3, margin: '0 auto 4px' }} /><p>暂无笔记</p></div>}
        {notes.map(n => (
          <div key={n.id} style={{ padding: 8, borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', border: '1px solid var(--hairline)' }} className="group">
            <p style={{ fontSize: 12, whiteSpace: 'pre-wrap', color: 'var(--ink)', lineHeight: 1.5 }}>{n.content}</p>
            {n.tags.length > 0 && <div style={{ display: 'flex', gap: 2, flexWrap: 'wrap', marginTop: 4 }}>{n.tags.map(t => <span key={t} style={{ fontSize: 10, padding: '1px 6px', borderRadius: 'var(--radius-xl)', background: 'var(--accent-bg-soft)', color: 'var(--accent)' }}>#{t}</span>)}</div>}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, paddingTop: 4, borderTop: '1px solid var(--hairline)' }}>
              <span style={{ fontSize: 10, color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: 2 }}><Clock size={10} />{n.createdAt}</span>
              <button onClick={() => deleteNote(n.id)} style={{ opacity: 0, color: 'var(--mute)', border: 'none', background: 'none', cursor: 'pointer', transition: 'all 0.15s' }} className="group-hover:!opacity-100"><Trash2 size={12} /></button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
