/**
 * ObsidianLayout — AcaSight 主布局（重构版）
 *
 * 职责：
 * 1. 左侧图标栏（导航）
 * 2. 面板容器（拖拽排列、调整宽度、上下文菜单）
 * 3. 全局浮层（Settings、ContextualAgentBar、ContextMenu）
 *
 * 所有面板内容通过 Views/ 目录的独立组件渲染，
 * 状态通过 AppContext 共享。
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { useTextSelection } from '@/hooks/useTextSelection';
import {
  FolderOpen, Search, Share2, List, Tag, Bookmark, Settings,
  X, ChevronsRight,
  MessageSquare, Sparkles, BookOpen,
  Sun, Moon,
  PenTool, Pencil,
  TrendingUp,
} from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { useApp } from '@/contexts/AppContext';
import { FileOpenProvider } from '@/contexts/FileOpenContext';
import { SettingsModal } from '@/components/Settings/SettingsModal';
import { SearchPage } from '@/components/Search/SearchPage';
import { ChartPanel } from '@/components/Charts/ChartPanel';
import { MarkdownEditor } from '@/components/Notes/MarkdownEditor';
import { ExcalidrawBoard } from '@/components/Whiteboard/ExcalidrawBoard';
import { AgentPanel } from '@/components/Agent/AgentPanel';
import { ContextualAgentBar } from '@/components/Agent/ContextualAgentBar';
import { ZoteroPanel } from '@/components/Zotero/ZoteroPanel';

// ---- View Components (拆分后) ----
import {
  FileExplorerView,
  EditorView,
  GraphView,
  OutlineView,
  TagsView,
  BookmarksView,
} from '@/components/Views';

// ==================== Panel Definitions ====================

interface PanelDef { id: string; title: string; defaultWidth: number; minWidth: number }

const PANEL_DEFS: Record<string, PanelDef> = {
  'file-explorer': { id: 'file-explorer', title: '文献管理', defaultWidth: 260, minWidth: 180 },
  'search':        { id: 'search',        title: 'AI 检索',  defaultWidth: 320, minWidth: 220 },
  'graph':         { id: 'graph',         title: '引用图谱', defaultWidth: 350, minWidth: 250 },
  'outline':       { id: 'outline',       title: '大纲',     defaultWidth: 240, minWidth: 180 },
  'tags':          { id: 'tags',          title: '标签',     defaultWidth: 240, minWidth: 180 },
  'bookmarks':     { id: 'bookmarks',     title: '书签',     defaultWidth: 240, minWidth: 180 },
  'notes':         { id: 'notes',         title: 'Markdown 笔记', defaultWidth: 420, minWidth: 300 },
  'whiteboard':    { id: 'whiteboard',    title: '白板',     defaultWidth: 600, minWidth: 400 },
  'charts':        { id: 'charts',        title: 'Origin 绘图',  defaultWidth: 900, minWidth: 600 },
  'zotero':        { id: 'zotero',        title: 'Zotero 文献库', defaultWidth: 700, minWidth: 500 },
  'agent':         { id: 'agent',         title: '学术 Agent', defaultWidth: 500, minWidth: 360 },
};

// ==================== Layout Component ====================

export const ObsidianLayout: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const {
    editorTabs, activeTabId,
    openPanels, togglePanel, closePanel,
    showAIPanel, setShowAIPanel,
    openFile,
    handleFileUpload, fileInputRef,
    pdfFullText,
  } = useApp();

  // ---- Global text selection (for ContextualAgentBar) ----
  const { selection: globalSelection } = useTextSelection(2);

  // ---- Mouse position (for ContextualAgentBar float positioning) ----
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);
  const mousePosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  useEffect(() => {
    const onMove = (e: MouseEvent) => { mousePosRef.current = { x: e.clientX, y: e.clientY }; };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, []);
  useEffect(() => {
    if (globalSelection?.text) setMousePos(mousePosRef.current);
    else setMousePos(null);
  }, [globalSelection?.text]);

  // ---- Layout-only state (不进入 AppContext) ----
  const [showSettings, setShowSettings] = useState(false);
  const [panelWidths, setPanelWidths] = useState<Record<string, number>>({ 'file-explorer': 260 });
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; panelId: string } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const resizingPanelRef = useRef<string | null>(null);
  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(0);

  // ---- Derived ----
  const activeFile = editorTabs.find(t => t.id === activeTabId)?.name || '';

  // ---- Resizer Handlers ----
  const handleResizerMouseDown = useCallback((e: React.MouseEvent, leftPanelId: string) => {
    e.preventDefault();
    resizingPanelRef.current = leftPanelId;
    resizeStartXRef.current = e.clientX;
    resizeStartWidthRef.current = panelWidths[leftPanelId] || 260;
    document.addEventListener('mousemove', onResizerMove);
    document.addEventListener('mouseup', onResizerUp);
  }, [panelWidths]);

  const onResizerMove = useCallback((e: MouseEvent) => {
    if (!resizingPanelRef.current) return;
    const dx = e.clientX - resizeStartXRef.current;
    setPanelWidths(prev => ({ ...prev, [resizingPanelRef.current!]: Math.max(180, resizeStartWidthRef.current + dx) }));
  }, []);

  const onResizerUp = useCallback(() => {
    resizingPanelRef.current = null;
    document.removeEventListener('mousemove', onResizerMove);
    document.removeEventListener('mouseup', onResizerUp);
  }, [onResizerMove]);

  // ---- Context Menu ----
  const handleContextMenu = useCallback((e: React.MouseEvent, panelId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, panelId });
  }, []);

  useEffect(() => {
    const h = () => setContextMenu(null);
    window.addEventListener('click', h);
    return () => window.removeEventListener('click', h);
  }, []);

  const handleContextAction = useCallback((action: string, panelId: string) => {
    if (action === 'close') closePanel(panelId);
    setContextMenu(null);
  }, [openPanels, closePanel]);

  // ---- Panel Content Router ----
  const renderPanelContent = (panelId: string) => {
    switch (panelId) {
      case 'file-explorer': return <FileExplorerView />;
      case 'search':        return <SearchPage />;
      case 'graph':         return <GraphView />;
      case 'outline':       return <OutlineView />;
      case 'tags':          return <TagsView />;
      case 'bookmarks':     return <BookmarksView />;
      case 'editor':        return <EditorView />;
      case 'notes':         return <MarkdownEditor />;
      case 'whiteboard':    return <ExcalidrawBoard />;
      case 'charts':        return <ChartPanel />;
      case 'zotero':        return <ZoteroPanel onOpenPdf={(key, title) => openFile(title + '.pdf', 'pdf', { pdfUrl: `http://localhost:9000/api/zotero/items/${key}/pdf` })} />;
      case 'agent':         return <AgentPanel pdfId={activeFile || undefined} pdfTitle={activeFile || undefined} selectedText={globalSelection?.text} pdfText={pdfFullText} />;
      default:              return <div className="acasight-empty"><p>未知面板</p></div>;
    }
  };

  // ---- Context Menu Render ----
  const renderContextMenu = () => {
    if (!contextMenu) return null;
    const idx = openPanels.indexOf(contextMenu.panelId);
    const isEditor = contextMenu.panelId === 'editor';
    return (
      <div className="acasight-context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
        {idx > 0 && <div className="acasight-context-item" onClick={() => handleContextAction('move-left', contextMenu.panelId)}><ChevronsRight size={14} style={{ transform: 'rotate(180deg)' }} />向左移动</div>}
        {idx < openPanels.length - 1 && <div className="acasight-context-item" onClick={() => handleContextAction('move-right', contextMenu.panelId)}><ChevronsRight size={14} />向右移动</div>}
        {!isEditor && <div className="acasight-context-divider" />}
        {!isEditor && <div className="acasight-context-item" onClick={() => handleContextAction('close', contextMenu.panelId)}><X size={14} />关闭面板</div>}
        {openPanels.length > 1 && <div className="acasight-context-item" onClick={() => handleContextAction('close-others', contextMenu.panelId)}><ChevronsRight size={14} />关闭其他面板</div>}
      </div>
    );
  };

  // ==================== Main Render ====================

  return (
    <FileOpenProvider openFile={openFile}>
      <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
        {/* @ts-expect-error React 19 ref compatibility */}
        <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileUpload} style={{ display: 'none' }} />

        {/* ---- Left Icon Bar ---- */}
        <div className="acasight-icon-bar">
          <div className="acasight-logo">A</div>
          <div className="acasight-divider" />
          {[
            { id: 'file-explorer', icon: FolderOpen, tooltip: '文献管理' },
            { id: 'search',        icon: Search,     tooltip: 'AI 检索' },
            { id: 'graph',         icon: Share2,     tooltip: '引用图谱' },
            { id: 'outline',       icon: List,       tooltip: '大纲' },
            { id: 'tags',          icon: Tag,        tooltip: '标签' },
            { id: 'bookmarks',     icon: Bookmark,   tooltip: '书签' },
            { id: 'notes',         icon: PenTool,    tooltip: 'Markdown 笔记' },
            { id: 'whiteboard',    icon: Pencil,     tooltip: '白板' },
            { id: 'charts',        icon: TrendingUp, tooltip: 'Origin 绘图' },
            { id: 'zotero',        icon: BookOpen,   tooltip: 'Zotero 文献库' },
            { id: 'agent',         icon: Sparkles,   tooltip: '学术 Agent' },
          ].map(item => (
            <div
              key={item.id}
              className={`acasight-icon-item ${openPanels.includes(item.id) ? 'active' : ''}`}
              data-tooltip={item.tooltip}
              onClick={() => togglePanel(item.id)}
            >
              <item.icon size={20} />
            </div>
          ))}
          <div className="acasight-spacer" />
          <div
            className="acasight-icon-item"
            data-tooltip={showAIPanel ? '隐藏AI助手' : '显示AI助手'}
            onClick={() => setShowAIPanel(prev => !prev)}
            style={showAIPanel ? { color: 'var(--accent)' } : {}}
          >
            <MessageSquare size={20} />
          </div>
          <div className="acasight-icon-item" data-tooltip={theme === 'dark' ? '浅色模式' : '深色模式'} onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
          </div>
          <div className="acasight-icon-item" data-tooltip="设置" onClick={() => setShowSettings(true)}>
            <Settings size={20} />
          </div>
        </div>

        {/* ---- Panel Container ---- */}
        <div className="acasight-panel-container" ref={containerRef}>
          {openPanels.length === 0 ? (
            <div className="acasight-empty" style={{ flex: 1 }}><FolderOpen size={48} /><p>点击左侧图标打开功能面板</p></div>
          ) : (
            openPanels.map((panelId, index) => {
              const isEditor = panelId === 'editor';
              const def = PANEL_DEFS[panelId];
              const width = isEditor ? undefined : (panelWidths[panelId] || (def?.defaultWidth || 300));
              return (
                <React.Fragment key={panelId}>
                  <div
                    className={`acasight-panel ${panelId === 'charts' ? 'panel-charts' : ''}`}
                    style={isEditor ? { flex: '1', minWidth: '300px' } : { width, flex: 'none' }}
                    onContextMenu={(e) => handleContextMenu(e, panelId)}
                  >
                    <div className="acasight-panel-header">
                      <span className="acasight-panel-title">{isEditor ? (activeFile || '编辑器') : (def?.title || panelId)}</span>
                      <div className="acasight-panel-actions">
                        {!isEditor && <button className="acasight-panel-btn" title="关闭" onClick={() => closePanel(panelId)}><X size={14} /></button>}
                      </div>
                    </div>
                    <div className="acasight-panel-body">{renderPanelContent(panelId)}</div>
                  </div>
                  {index < openPanels.length - 1 && <div className="acasight-resizer" onMouseDown={(e) => handleResizerMouseDown(e, panelId)} />}
                </React.Fragment>
              );
            })
          )}
        </div>

        {/* ---- Global Overlays ---- */}
        {showSettings && <SettingsModal onClose={() => setShowSettings(false)} showAI={showAIPanel} onToggleAI={() => setShowAIPanel(prev => !prev)} />}

        {/* Contextual Agent 悬浮窗：选中文字后浮出 AI 气泡 */}
        <ContextualAgentBar
          panelId="editor"
          selectedText={globalSelection?.text}
          pdfText={pdfFullText}
          mousePosition={mousePos}
          onOpenAgentPanel={() => { if (!openPanels.includes('agent')) togglePanel('agent'); }}
        />

        {renderContextMenu()}
      </div>
    </FileOpenProvider>
  );
};
