import React, { useState, useRef, useCallback, useEffect, Suspense, lazy } from 'react';
import '@/dashboard.css';
import { useTranslation } from 'react-i18next';
import { Send } from 'lucide-react';
import { useTextSelection } from '@/hooks/useTextSelection';
import {
  FolderOpen, Search, Share2, List, Tag, Bookmark, Settings,
  X, ChevronsRight,
  MessageSquare, Sparkles,
  Sun, Moon,
  PenTool, Pencil, Menu,
  TrendingUp, GraduationCap, HardDrive,
  Image, Shapes, Puzzle, Activity, History, BookOpen,
  Database, LayoutGrid, Brain, Globe, Table2,
  Lightbulb, FlaskConical, HelpCircle, FileEdit,
  FileSearch, Sigma, Microscope, Network,
} from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { useApp } from '@/contexts/AppContext';
import { usePanels } from '@/contexts/AppContext';
import { usePanelSwitchStore } from '@/store/panelSwitchStore';
import { FileOpenProvider } from '@/contexts/FileOpenContext';
import { SettingsModal } from '@/components/Settings/SettingsModal';
import { MarkdownEditor } from '@/components/Notes/MarkdownEditor';
import { AgentPanel } from '@/components/Agent/AgentPanel';
import { ContextualAgentBar } from '@/components/Agent/ContextualAgentBar';
import { FloatingTranslate } from '@/components/Translate/FloatingTranslate';
import { FullPageTranslate } from '@/components/Translate/FullPageTranslate';
import { ZoteroPanel } from '@/components/Zotero/ZoteroPanel';
import { MaterialPanel } from '@/components/Views/MaterialPanel';
import { ErrorBoundary } from '@/components/Common/ErrorBoundary';
import { TauriDragDrop } from '@/components/Common/TauriDragDrop';

const SearchPage = lazy(() => import('@/components/Search/SearchPage').then(m => ({ default: m.SearchPage })));
const ChartPanel = lazy(() => import('@/components/Charts/ChartPanel').then(m => ({ default: m.ChartPanel })));
const ExcalidrawBoard = lazy(() => import('@/components/Whiteboard/ExcalidrawBoard').then(m => ({ default: m.ExcalidrawBoard })));
const WritingWorkspace = lazy(() => import('@/components/Writing/WritingWorkspace').then(m => ({ default: m.WritingWorkspace })));
const GraphView = lazy(() => import('@/components/Views/GraphView').then(m => ({ default: m.GraphView })));
const FigureGenerationPanel = lazy(() => import('@/components/Figure/FigureGenerationPanel').then(m => ({ default: m.FigureGenerationPanel })));
const SvgEditorPanel = lazy(() => import('@/components/Figure/SvgEditorPanel').then(m => ({ default: m.SvgEditorPanel })));
const PluginPanel = lazy(() => import('@/components/Settings/PluginPanel').then(m => ({ default: m.PluginPanel })));
const ArchPanel = lazy(() => import('@/components/Settings/ArchPanel').then(m => ({ default: m.ArchPanel })));
const VersionHistoryPanel = lazy(() => import('@/components/Writing/VersionHistoryPanel').then(m => ({ default: m.VersionHistoryPanel })));
const TemplateGallery = lazy(() => import('@/components/Writing/TemplateGallery').then(m => ({ default: m.TemplateGallery })));
const DataExportImportPanel = lazy(() => import('@/components/Settings/DataExportImportPanel').then(m => ({ default: m.DataExportImportPanel })));
const MonitoringDashboard = lazy(() => import('@/components/Monitor/MonitoringDashboard').then(m => ({ default: m.MonitoringDashboard })));
const PaperDimensionView = lazy(() => import('@/components/Papers/PaperDimensionView').then(m => ({ default: m.PaperDimensionView })));
const DBLPPanel = lazy(() => import('@/components/Papers/DBLPPanel').then(m => ({ default: m.DBLPPanel })));
const LiteratureTableView = lazy(() => import('@/components/LiteratureTable/LiteratureTableView').then(m => ({ default: m.LiteratureTableView })));
const LiteratureReviewView = lazy(() => import('@/components/LiteratureReview/LiteratureReviewView').then(m => ({ default: m.LiteratureReviewView })));
const DimensionDisplayView = lazy(() => import('@/components/DimensionDisplay/DimensionDisplayView').then(m => ({ default: m.DimensionDisplayView })));
const PaperWritingWorkbench = lazy(() => import('@/components/WritingWorkbench/PaperWritingWorkbench').then(m => ({ default: m.PaperWritingWorkbench })));
const PlotStudio = lazy(() => import('@/components/Charts/PlotStudio/PlotStudio').then(m => ({ default: m.PlotStudio })));
const HelpCenter = lazy(() => import('@/components/Help/HelpCenter').then(m => ({ default: m.HelpCenter })));
const DocumentList = lazy(() => import('@/components/Document/DocumentList').then(m => ({ default: m.DocumentList })));
const BatchLiteraturePanel = lazy(() => import('@/components/Literature/BatchLiteraturePanel').then(m => ({ default: m.BatchLiteraturePanel })));
const PlagiarismCheckPanel = lazy(() => import('@/components/Plagiarism/PlagiarismCheckPanel').then(m => ({ default: m.PlagiarismCheckPanel })));
const LatexEditorPanel = lazy(() => import('@/components/Latex/LatexEditorPanel').then(m => ({ default: m.LatexEditorPanel })));
const LabNotebookPanel = lazy(() => import('@/components/Experiment/LabNotebookPanel').then(m => ({ default: m.LabNotebookPanel })));
const KnowledgeGraphPanel = lazy(() => import('@/components/KnowledgeGraph/KnowledgeGraphPanel').then(m => ({ default: m.KnowledgeGraphPanel })));

import {
  FileExplorerView,
  EditorView,
  OutlineView,
  TagsView,
  BookmarksView,
} from '@/components/Views';

/* ──────────────────── types ──────────────────── */

interface PanelDef { id: string; titleKey: string; defaultWidth: number; minWidth: number }

interface FeatureItem {
  id: string;
  icon: typeof FolderOpen;
  labelKey: string;
  color: string;        // 莫兰迪色系玻璃图标渐变色
  group: 'core' | 'academic' | 'visual' | 'system';
}

/* ──────────────────── constants ──────────────────── */

function PanelSkeleton() {
  return (
    <div className="acasight-panel-skeleton" style={{ padding: 16 }}>
      <div style={{ width: '60%', height: 18, background: 'var(--bg-secondary)', borderRadius: 4, marginBottom: 12 }} />
      <div style={{ width: '100%', height: 14, background: 'var(--bg-secondary)', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ width: '85%', height: 14, background: 'var(--bg-secondary)', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ width: '70%', height: 14, background: 'var(--bg-secondary)', borderRadius: 4, marginBottom: 8 }} />
      <div style={{ width: '90%', height: 14, background: 'var(--bg-secondary)', borderRadius: 4 }} />
    </div>
  );
}

const OVERLAY_CONFIG: Record<string, { icon: React.ReactNode; titleKey: string }> = {
  'dimension-display': { icon: <Table2 size={16} style={{ color: 'var(--accent)' }} />, titleKey: 'layout.panelDimensionDisplay' },
  'writing-workbench': { icon: <Brain size={16} style={{ color: 'var(--accent)' }} />, titleKey: 'layout.panelWritingWorkbench' },
  'dblp': { icon: <Globe size={16} style={{ color: 'var(--accent)' }} />, titleKey: 'layout.panelDBLP' },
  'paper-dimensions': { icon: <Brain size={16} style={{ color: 'var(--accent)' }} />, titleKey: 'layout.panelPaperDimensions' },
  'literature-table': { icon: <Table2 size={16} style={{ color: 'var(--accent)' }} />, titleKey: 'layout.panelLiteratureTable' },
  'literature-review': { icon: <BookOpen size={16} style={{ color: 'var(--accent)' }} />, titleKey: 'layout.panelLiteratureReview' },
};

const DashboardOverlay: React.FC<{ panel: string; onClose: () => void; t: (key: string) => string }> = ({ panel, onClose, t }) => {
  const isFullScreen = panel === 'plot-studio' || panel === 'help-center';
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div
        style={{
          width: isFullScreen ? '96vw' : '90vw',
          maxWidth: isFullScreen ? 1600 : 1100,
          height: isFullScreen ? '92vh' : '80vh',
          borderRadius: 12, background: 'var(--canvas)',
          border: '1px solid var(--hairline)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          overflow: 'hidden', display: 'flex', flexDirection: 'column',
        }}
        onClick={e => e.stopPropagation()}
      >
        {isFullScreen ? (
          <ErrorBoundary><Suspense fallback={<PanelSkeleton />}>
            {panel === 'plot-studio' && <PlotStudio onClose={onClose} />}
            {panel === 'help-center' && <HelpCenter onClose={onClose} />}
          </Suspense></ErrorBoundary>
        ) : (
          <>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 16px', borderBottom: '1px solid var(--hairline)',
              background: 'var(--glass-bg, var(--bg-2))',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {(() => {
                  const config = OVERLAY_CONFIG[panel];
                  return config ? (
                    <>
                      {config.icon}
                      <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>
                        {t(config.titleKey)}
                      </span>
                    </>
                  ) : null;
                })()}
              </div>
              <button
                onClick={onClose}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--mute)', padding: 4, borderRadius: 4,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <X size={18} />
              </button>
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              {panel === 'dimension-display' && (
                <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><DimensionDisplayView /></Suspense></ErrorBoundary>
              )}
              {panel === 'writing-workbench' && (
                <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><PaperWritingWorkbench /></Suspense></ErrorBoundary>
              )}
              {panel === 'dblp' && (
                <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><DBLPPanel /></Suspense></ErrorBoundary>
              )}
              {panel === 'paper-dimensions' && (
                <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><PaperDimensionView /></Suspense></ErrorBoundary>
              )}
              {panel === 'literature-table' && (
                <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><LiteratureTableView /></Suspense></ErrorBoundary>
              )}
              {panel === 'literature-review' && (
                <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><LiteratureReviewView /></Suspense></ErrorBoundary>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const PANEL_DEFS: Record<string, PanelDef> = {
  'file-explorer': { id: 'file-explorer', titleKey: 'layout.panelFileExplorer', defaultWidth: 260, minWidth: 180 },
  'search':        { id: 'search',        titleKey: 'layout.panelSearch',  defaultWidth: 320, minWidth: 220 },
  'graph':         { id: 'graph',         titleKey: 'layout.panelGraph', defaultWidth: 350, minWidth: 250 },
  'outline':       { id: 'outline',       titleKey: 'layout.panelOutline', defaultWidth: 240, minWidth: 180 },
  'tags':          { id: 'tags',          titleKey: 'layout.panelTags', defaultWidth: 240, minWidth: 180 },
  'bookmarks':     { id: 'bookmarks',     titleKey: 'layout.panelBookmarks', defaultWidth: 240, minWidth: 180 },
  'notes':         { id: 'notes',         titleKey: 'layout.panelNotes', defaultWidth: 420, minWidth: 300 },
  'whiteboard':    { id: 'whiteboard',    titleKey: 'layout.panelWhiteboard', defaultWidth: 600, minWidth: 400 },
  'charts':        { id: 'charts',        titleKey: 'layout.panelCharts',  defaultWidth: 900, minWidth: 600 },
  'zotero':        { id: 'zotero',        titleKey: 'layout.panelZotero', defaultWidth: 700, minWidth: 500 },
  'agent':         { id: 'agent',         titleKey: 'layout.panelAgent', defaultWidth: 500, minWidth: 360 },
  'writing':       { id: 'writing',       titleKey: 'layout.panelWriting', defaultWidth: 1000, minWidth: 700 },
  'figure':        { id: 'figure',        titleKey: 'layout.panelFigure', defaultWidth: 500, minWidth: 360 },
  'svg-editor':    { id: 'svg-editor',    titleKey: 'layout.panelSvgEditor', defaultWidth: 600, minWidth: 400 },
  'plugins':       { id: 'plugins',       titleKey: 'layout.panelPlugins', defaultWidth: 500, minWidth: 360 },
  'arch':          { id: 'arch',          titleKey: 'layout.panelArch', defaultWidth: 500, minWidth: 360 },
  'version-history': { id: 'version-history', titleKey: 'layout.panelVersionHistory', defaultWidth: 400, minWidth: 280 },
  'templates':     { id: 'templates',     titleKey: 'layout.panelTemplates', defaultWidth: 400, minWidth: 280 },
  'data-export':   { id: 'data-export',   titleKey: 'layout.panelDataExport', defaultWidth: 400, minWidth: 280 },
  'monitoring':    { id: 'monitoring',    titleKey: 'layout.panelMonitoring', defaultWidth: 400, minWidth: 280 },
  'paper-dimensions': { id: 'paper-dimensions', titleKey: 'layout.panelPaperDimensions', defaultWidth: 700, minWidth: 500 },
  'dblp':          { id: 'dblp',          titleKey: 'layout.panelDBLP', defaultWidth: 700, minWidth: 500 },
  'literature-table': { id: 'literature-table', titleKey: 'layout.panelLiteratureTable', defaultWidth: 900, minWidth: 600 },
  'literature-review': { id: 'literature-review', titleKey: 'layout.panelLiteratureReview', defaultWidth: 900, minWidth: 600 },
  'dimension-display': { id: 'dimension-display', titleKey: 'layout.panelDimensionDisplay', defaultWidth: 900, minWidth: 600 },
  'writing-workbench': { id: 'writing-workbench', titleKey: 'layout.panelWritingWorkbench', defaultWidth: 900, minWidth: 600 },
  'documents':     { id: 'documents',     titleKey: 'layout.panelDocuments', defaultWidth: 800, minWidth: 600 },
  'batch-literature': { id: 'batch-literature', titleKey: 'layout.panelBatchLiterature', defaultWidth: 800, minWidth: 600 },
  'plagiarism':    { id: 'plagiarism',    titleKey: 'layout.panelPlagiarism', defaultWidth: 700, minWidth: 500 },
  'latex-editor':  { id: 'latex-editor',  titleKey: 'layout.panelLatexEditor', defaultWidth: 900, minWidth: 600 },
  'lab-notebook':  { id: 'lab-notebook',  titleKey: 'layout.panelLabNotebook', defaultWidth: 900, minWidth: 600 },
  'knowledge-graph': { id: 'knowledge-graph', titleKey: 'layout.panelKnowledgeGraph', defaultWidth: 900, minWidth: 600 },
};

/** 看板功能卡片 — 莫兰迪色系 */
const FEATURE_ITEMS: FeatureItem[] = [
  // ── 核心功能 ──
  { id: 'file-explorer', icon: FolderOpen,   labelKey: 'layout.panelFileExplorer', color: '#9DB4AB', group: 'core' },
  { id: 'search',        icon: Search,       labelKey: 'layout.panelSearch',       color: '#8EA8C3', group: 'core' },
  { id: 'outline',       icon: List,         labelKey: 'layout.panelOutline',      color: '#B8A9C9', group: 'core' },
  { id: 'tags',          icon: Tag,          labelKey: 'layout.panelTags',         color: '#8FB8C0', group: 'core' },
  { id: 'bookmarks',     icon: Bookmark,     labelKey: 'layout.panelBookmarks',    color: '#C4A8A1', group: 'core' },
  // ── 学术工具 ──
  { id: 'zotero',        icon: BookOpen,     labelKey: 'layout.panelZotero',       color: '#8EA8C3', group: 'academic' },
  { id: 'agent',         icon: Sparkles,     labelKey: 'layout.panelAgent',        color: '#B8A9C9', group: 'academic' },
  { id: 'writing',       icon: GraduationCap,labelKey: 'layout.panelWriting',      color: '#C4A8A1', group: 'academic' },
  { id: 'dimension-display', icon: Table2,  labelKey: 'layout.panelDimensionDisplay', color: '#0ea5e9', group: 'academic' },
  { id: 'writing-workbench', icon: Brain,   labelKey: 'layout.panelWritingWorkbench', color: '#8b5cf6', group: 'academic' },
  { id: 'whiteboard',    icon: Lightbulb,   labelKey: 'layout.panelWhiteboard',   color: '#f59e0b', group: 'academic' },
  { id: 'dblp',          icon: Globe,        labelKey: 'layout.panelDBLP',          color: '#8EA8C3', group: 'academic' },
  { id: 'plot-studio',   icon: FlaskConical, labelKey: 'layout.panelPlotStudio',    color: '#059669', group: 'academic' },
  { id: 'notes',         icon: PenTool,      labelKey: 'layout.panelNotes',        color: '#9DB4AB', group: 'academic' },
  { id: 'documents',     icon: FileEdit,     labelKey: 'layout.panelDocuments',    color: '#6366f1', group: 'academic' },
  { id: 'batch-literature', icon: FileSearch, labelKey: 'layout.panelBatchLiterature', color: '#0ea5e9', group: 'academic' },
  { id: 'plagiarism',    icon: FileSearch,   labelKey: 'layout.panelPlagiarism',  color: '#ef4444', group: 'academic' },
  { id: 'latex-editor',  icon: Sigma,        labelKey: 'layout.panelLatexEditor', color: '#14b8a6', group: 'academic' },
  { id: 'lab-notebook',  icon: Microscope,   labelKey: 'layout.panelLabNotebook', color: '#a855f7', group: 'academic' },
  { id: 'knowledge-graph', icon: Network,    labelKey: 'layout.panelKnowledgeGraph', color: '#f59e0b', group: 'visual' },
  { id: 'material',      icon: HardDrive,    labelKey: 'layout.panelMaterials',    color: '#B5A68E', group: 'academic' },
  // ── 可视化 & 绘图 ──
  { id: 'graph',         icon: Share2,       labelKey: 'layout.panelGraph',        color: '#8FB8C0', group: 'visual' },
  { id: 'charts',        icon: TrendingUp,   labelKey: 'layout.panelCharts',       color: '#9DB4AB', group: 'visual' },
  { id: 'figure',        icon: Image,        labelKey: 'layout.panelFigure',       color: '#B8A9C9', group: 'visual' },
  { id: 'svg-editor',    icon: Shapes,       labelKey: 'layout.panelSvgEditor',    color: '#8EA8C3', group: 'visual' },
  { id: 'whiteboard',    icon: Pencil,       labelKey: 'layout.panelWhiteboard',   color: '#B5A68E', group: 'visual' },
  // ── 系统 ──
  { id: 'plugins',       icon: Puzzle,       labelKey: 'layout.panelPlugins',      color: '#C4A8A1', group: 'system' },
  { id: 'arch',          icon: Activity,     labelKey: 'layout.panelArch',         color: '#8FB8C0', group: 'system' },
  { id: 'version-history',icon: History,     labelKey: 'layout.panelVersionHistory',color: '#B8A9C9', group: 'system' },
  { id: 'templates',     icon: BookOpen,     labelKey: 'layout.panelTemplates',    color: '#9DB4AB', group: 'system' },
  { id: 'data-export',   icon: Database,     labelKey: 'layout.panelDataExport',   color: '#8EA8C3', group: 'system' },
  { id: 'monitoring',    icon: Activity,     labelKey: 'layout.panelMonitoring',   color: '#B5A68E', group: 'system' },
  { id: 'help-center',  icon: HelpCircle,   labelKey: 'layout.panelHelpCenter',   color: '#6366f1', group: 'system' },
];

/** 侧边栏窄条模式下的图标（精简版） */
const SIDEBAR_COMPACT_ITEMS = [
  { id: 'file-explorer', icon: FolderOpen,   tooltipKey: 'layout.panelFileExplorer' },
  { id: 'search',        icon: Search,       tooltipKey: 'layout.panelSearch' },
  { id: 'zotero',        icon: BookOpen,     tooltipKey: 'layout.panelZotero' },
  { id: 'agent',         icon: Sparkles,     tooltipKey: 'layout.panelAgent' },
  { id: 'writing',       icon: GraduationCap,tooltipKey: 'layout.panelWriting' },
  { id: 'notes',         icon: PenTool,      tooltipKey: 'layout.panelNotes' },
  { id: 'documents',     icon: FileEdit,     tooltipKey: 'layout.panelDocuments' },
  { id: 'graph',         icon: Share2,       tooltipKey: 'layout.panelGraph' },
  { id: 'figure',        icon: Image,        tooltipKey: 'layout.panelFigure' },
  { id: 'charts',        icon: TrendingUp,   tooltipKey: 'layout.panelCharts' },
  { id: 'knowledge-graph', icon: Network,    tooltipKey: 'layout.panelKnowledgeGraph' },
  { id: 'latex-editor',  icon: Sigma,        tooltipKey: 'layout.panelLatexEditor' },
  { id: 'lab-notebook',  icon: Microscope,   tooltipKey: 'layout.panelLabNotebook' },
];

const GROUP_LABELS: Record<string, string> = {
  core: '核心功能',
  academic: '学术工具',
  visual: '可视化 & 绘图',
  system: '系统',
};

/* ──────────────────── component ──────────────────── */

type ViewMode = 'dashboard' | 'workspace';

export const ObsidianLayout: React.FC = () => {
  const { t } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const {
    editorTabs, activeTabId,
    showAIPanel, setShowAIPanel,
    openFile,
    pdfFile, pdfFullText,
    showFloatingTranslate, floatTranslateText, floatTranslatePos,
    setShowFloatingTranslate, setFloatTranslateText,
  } = useApp();

  const {
    openPanels, togglePanel, closePanel, setOpenPanels,
  } = usePanels();

  // 面板切换 store — 监听跨组件面板切换请求
  const consumePanelSwitch = usePanelSwitchStore((s) => s.consumeSwitch);
  const panelSwitchTarget = usePanelSwitchStore((s) => s.targetPanel);

  // 消费面板切换请求
  useEffect(() => {
    const target = consumePanelSwitch();
    if (target) {
      // 切换到工作区模式
      setViewMode('workspace');
      // 如果面板未打开则打开
      if (!openPanelsRef.current.includes(target)) {
        togglePanel(target);
      }
      setAnimatingPanels(prev => ({ ...prev, [target]: 'in' }));
      setTimeout(() => {
        setAnimatingPanels(prev => {
          const next = { ...prev };
          delete next[target];
          return next;
        });
      }, 450);
    }
  }, [panelSwitchTarget]); // eslint-disable-line react-hooks/exhaustive-deps

  const openPanelsRef = useRef(openPanels);
  openPanelsRef.current = openPanels;

  const { selection: globalSelection } = useTextSelection(2);

  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');
  /* translate window state */
  const [translateText, setTranslateText] = useState<string | null>(null);
  const [showFullPage, setShowFullPage] = useState<string | null>(null);
  const [translatePosition, setTranslatePosition] = useState<{ x: number; y: number } | null>(null);

  /* ── 面板与看板联动 ── */
  useEffect(() => {
    if (openPanels.length === 0 && viewMode === 'workspace') {
      setViewMode('dashboard');
    } else if (openPanels.length > 0 && viewMode === 'dashboard') {
      setViewMode('workspace');
    }
  }, [openPanels.length, viewMode]);

  /* ── 鼠标追踪（浮动AgentBar用） ── */
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

  /* ── 面板动画 ── */
  const [showSettings, setShowSettings] = useState(false);
  const [panelWidths, setPanelWidths] = useState<Record<string, number>>({ 'file-explorer': 260 });
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; panelId: string } | null>(null);
  const [animatingPanels, setAnimatingPanels] = useState<Record<string, 'in' | 'out'>>({});

  const containerRef = useRef<HTMLDivElement>(null);
  const resizingPanelRef = useRef<string | null>(null);
  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(0);

  /* ── 进入工作区 ── */
  const enterWorkspace = useCallback((panelId: string) => {
    setViewMode('workspace');
    if (!openPanelsRef.current.includes(panelId)) {
      togglePanel(panelId);
    }
    setAnimatingPanels(prev => ({ ...prev, [panelId]: 'in' }));
    setTimeout(() => {
      setAnimatingPanels(prev => {
        const next = { ...prev };
        delete next[panelId];
        return next;
      });
    }, 450);
  }, [togglePanel]);

  /* ── 返回看板 ── */
  const goDashboard = useCallback(() => {
    setOpenPanels([]);
    setViewMode('dashboard');
  }, [setOpenPanels]);

  /* ── 看板底部轻量对话 ── */
  const [dashInput, setDashInput] = useState('');
  const [dashMessages, setDashMessages] = useState<Array<{ role: 'user' | 'ai'; text: string }>>([]);
  const dashChatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (dashChatRef.current) {
      dashChatRef.current.scrollTop = dashChatRef.current.scrollHeight;
    }
  }, [dashMessages]);

  const handleDashSend = useCallback(() => {
    const text = dashInput.trim();
    if (!text) return;
    setDashMessages(prev => [...prev, { role: 'user', text }]);
    setDashInput('');
    // 跳转到完整 Agent 面板
    setTimeout(() => enterWorkspace('agent'), 300);
  }, [dashInput, enterWorkspace]);

  /* ── 看板模式下点击功能卡片 ── */
  const [overlayPanel, setOverlayPanel] = useState<string | null>(null);

  const handleFeatureClick = useCallback((itemId: string) => {
    setSidebarExpanded(false);
    if (itemId === 'dimension-display' || itemId === 'dblp' || itemId === 'writing-workbench' || itemId === 'plot-studio' || itemId === 'help-center') {
      setOverlayPanel(itemId);
    } else {
      enterWorkspace(itemId);
    }
  }, [enterWorkspace]);

  /* ── 面板动画开关 ── */
  const animatedTogglePanel = useCallback((panelId: string) => {
    if (openPanelsRef.current.includes(panelId)) {
      setAnimatingPanels(prev => ({ ...prev, [panelId]: 'out' }));
      setTimeout(() => {
        togglePanel(panelId);
        setAnimatingPanels(prev => {
          const next = { ...prev };
          delete next[panelId];
          return next;
        });
      }, 280);
    } else {
      togglePanel(panelId);
      setAnimatingPanels(prev => ({ ...prev, [panelId]: 'in' }));
      setTimeout(() => {
        setAnimatingPanels(prev => {
          const next = { ...prev };
          delete next[panelId];
          return next;
        });
      }, 450);
    }
  }, [togglePanel]);

  const handleOpenAgentPanel = useCallback(() => {
    if (!openPanelsRef.current.includes('agent')) togglePanel('agent');
  }, [togglePanel]);

  const handleTranslate = useCallback((text: string) => {
    if (!text) return;
    setTranslateText(text);
    setTranslatePosition(mousePosRef.current);
  }, []);
  const handleOpenPdf = useCallback((key: string, title: string) => {
    openFile(title + '.pdf', 'pdf', { pdfUrl: `/api/zotero/items/${key}/pdf` });
  }, [openFile]);

  const activeFile = editorTabs.find(tab => tab.id === activeTabId)?.name || '';

  /* ── resize ── */
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

  /* ── 右键菜单 ── */
  const handleContextMenu = useCallback((e: React.MouseEvent, panelId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, panelId });
  }, []);

  useEffect(() => {
    const h = () => setContextMenu(null);
    window.addEventListener('click', h);
    return () => window.removeEventListener('click', h);
  }, []);

  /* ── 快捷键 ── */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === 'k') {
        e.preventDefault();
        enterWorkspace('search');
      }
      if (mod && e.key === 'n') {
        e.preventDefault();
        enterWorkspace('notes');
      }
      if (mod && e.shiftKey && e.key === 'g') {
        e.preventDefault();
        enterWorkspace('graph');
      }
      if (mod && e.shiftKey && e.key === 'w') {
        e.preventDefault();
        enterWorkspace('writing');
      }
      if (e.key === 'Escape') {
        const active = document.activeElement as HTMLElement;
        if (active && active.blur) active.blur();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [enterWorkspace]);

  const handleContextAction = useCallback((action: string, panelId: string) => {
    if (action === 'close') {
      setAnimatingPanels(prev => ({ ...prev, [panelId]: 'out' }));
      setTimeout(() => {
        closePanel(panelId);
        setAnimatingPanels(prev => {
          const next = { ...prev };
          delete next[panelId];
          return next;
        });
      }, 280);
    }
    setContextMenu(null);
  }, [closePanel]);

  /* ──────────── 面板内容渲染 ──────────── */
  const renderPanelContent = (panelId: string) => {
    switch (panelId) {
      case 'file-explorer': return <FileExplorerView />;
      case 'material':       return <MaterialPanel />;
      case 'search':        return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><SearchPage /></Suspense></ErrorBoundary>;
      case 'graph':         return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><GraphView /></Suspense></ErrorBoundary>;
      case 'outline':       return <OutlineView />;
      case 'tags':          return <TagsView />;
      case 'bookmarks':     return <BookmarksView />;
      case 'editor':        return <EditorView />;
      case 'notes':         return <MarkdownEditor />;
      case 'whiteboard':    return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><ExcalidrawBoard /></Suspense></ErrorBoundary>;
      case 'charts':        return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><ChartPanel /></Suspense></ErrorBoundary>;
      case 'zotero':        return <ZoteroPanel onOpenPdf={handleOpenPdf} />;
      case 'agent':         return <AgentPanel pdfId={pdfFile && typeof pdfFile === 'string' ? pdfFile : undefined} pdfTitle={activeFile || undefined} selectedText={globalSelection?.text} pdfText={pdfFullText} />;
      case 'writing':       return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><WritingWorkspace /></Suspense></ErrorBoundary>;
      case 'figure':        return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><FigureGenerationPanel /></Suspense></ErrorBoundary>;
      case 'svg-editor':    return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><SvgEditorPanel /></Suspense></ErrorBoundary>;
      case 'plugins':       return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><PluginPanel /></Suspense></ErrorBoundary>;
      case 'arch':          return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><ArchPanel /></Suspense></ErrorBoundary>;
      case 'version-history': return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><VersionHistoryPanel documentId="default" /></Suspense></ErrorBoundary>;
      case 'templates':     return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><TemplateGallery /></Suspense></ErrorBoundary>;
      case 'data-export':   return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><DataExportImportPanel /></Suspense></ErrorBoundary>;
      case 'monitoring':    return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><MonitoringDashboard /></Suspense></ErrorBoundary>;
      case 'paper-dimensions': return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><PaperDimensionView /></Suspense></ErrorBoundary>;
      case 'dblp':          return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><DBLPPanel /></Suspense></ErrorBoundary>;
      case 'dimension-display': return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><DimensionDisplayView /></Suspense></ErrorBoundary>;
      case 'writing-workbench': return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><PaperWritingWorkbench /></Suspense></ErrorBoundary>;
      case 'documents':     return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><DocumentList /></Suspense></ErrorBoundary>;
      case 'batch-literature': return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><BatchLiteraturePanel /></Suspense></ErrorBoundary>;
      case 'plagiarism':    return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><PlagiarismCheckPanel /></Suspense></ErrorBoundary>;
      case 'latex-editor':  return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><LatexEditorPanel /></Suspense></ErrorBoundary>;
      case 'lab-notebook':  return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><LabNotebookPanel /></Suspense></ErrorBoundary>;
      case 'knowledge-graph': return <ErrorBoundary><Suspense fallback={<PanelSkeleton />}><KnowledgeGraphPanel /></Suspense></ErrorBoundary>;
      default:              return <div className="acasight-empty"><p>{t('layout.unknownPanel')}</p></div>;
    }
  };

  const renderContextMenu = () => {
    if (!contextMenu) return null;
    const idx = openPanels.indexOf(contextMenu.panelId);
    const isEditor = contextMenu.panelId === 'editor';
    return (
      <div className="acasight-context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
        {idx > 0 && <div className="acasight-context-item" onClick={() => handleContextAction('move-left', contextMenu.panelId)}><ChevronsRight size={14} style={{ transform: 'rotate(180deg)' }} />{t('layout.moveLeft')}</div>}
        {idx < openPanels.length - 1 && <div className="acasight-context-item" onClick={() => handleContextAction('move-right', contextMenu.panelId)}><ChevronsRight size={14} />{t('layout.moveRight')}</div>}
        {!isEditor && <div className="acasight-context-divider" />}
        <div className="acasight-context-item" onClick={() => handleContextAction('close', contextMenu.panelId)}><X size={14} />{t('layout.closePanel')}</div>
        {openPanels.length > 1 && <div className="acasight-context-item" onClick={() => handleContextAction('close-others', contextMenu.panelId)}><ChevronsRight size={14} />{t('layout.closeOthers')}</div>}
      </div>
    );
  };

  /* ──────────── 看板首页 ──────────── */
  const renderDashboard = () => {
    const groups = ['core', 'academic', 'visual', 'system'] as const;
    return (
      <div className="acasight-dashboard">
        {/* 左侧展开菜单覆盖层 */}
        {sidebarExpanded && (
          <div className="acasight-menu-overlay" onClick={() => setSidebarExpanded(false)} />
        )}

        {/* 顶部导航条 */}
        <div className="acasight-dashboard-topbar">
          <div className="acasight-topbar-left">
            <button className="acasight-topbar-btn" onClick={() => setSidebarExpanded(s => !s)} data-tooltip="展开菜单">
              <Menu size={20} />
            </button>
            <span className="acasight-topbar-brand">AcaSight</span>
          </div>
          <div className="acasight-topbar-right">
            <button className="acasight-topbar-btn" onClick={toggleTheme}>
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="acasight-topbar-btn" onClick={() => setShowSettings(true)}>
              <Settings size={18} />
            </button>
          </div>
        </div>

        {/* 展开侧边菜单（全屏覆盖） */}
        <div className={`acasight-expand-menu ${sidebarExpanded ? 'expanded' : ''}`}>
          <div className="acasight-expand-menu-header">
            <span className="acasight-topbar-brand">AcaSight</span>
            <button className="acasight-topbar-btn" onClick={() => setSidebarExpanded(false)}>
              <X size={20} />
            </button>
          </div>
          <nav className="acasight-expand-menu-nav">
            {groups.map(group => (
              <div key={group} className="acasight-menu-group">
                <div className="acasight-menu-group-label">{GROUP_LABELS[group]}</div>
                {FEATURE_ITEMS.filter(f => f.group === group).map(item => (
                  <button
                    key={item.id}
                    className="acasight-menu-item"
                    onClick={() => handleFeatureClick(item.id)}
                  >
                    <item.icon size={18} />
                    <span>{t(item.labelKey)}</span>
                  </button>
                ))}
              </div>
            ))}
          </nav>
        </div>

        {/* 功能图标网格区 */}
        <div className="acasight-dashboard-content">
          <div className="acasight-dashboard-hero">
            <h1 className="acasight-dashboard-title">AcaSight</h1>
            <p className="acasight-dashboard-subtitle">学术视界 · 智能研究工作台</p>
          </div>

          {groups.map(group => (
            <div key={group} className="acasight-feature-group">
              <div className="acasight-feature-group-label">{GROUP_LABELS[group]}</div>
              <div className="acasight-feature-grid">
                {FEATURE_ITEMS.filter(f => f.group === group).map(item => (
                  <button
                    key={item.id}
                    className="acasight-glass-card"
                    style={{ '--card-accent': item.color } as React.CSSProperties}
                    onClick={() => handleFeatureClick(item.id)}
                  >
                    <div className="acasight-glass-icon">
                      <item.icon size={22} strokeWidth={1.5} />
                    </div>
                    <span className="acasight-glass-label">{t(item.labelKey)}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* 底部轻量对话框 — 发送后跳转完整Agent面板 */}
        <div className="acasight-dashboard-chat">
          <div className="dashboard-chat-messages" ref={dashChatRef}>
            {dashMessages.length === 0 && (
              <div className="dashboard-chat-empty">
                <Sparkles size={24} style={{ opacity: 0.4, marginBottom: 8 }} />
                <p>向 AI 助手提问，开始你的研究</p>
              </div>
            )}
            {dashMessages.map((msg, i) => (
              <div key={i} className={`dashboard-chat-bubble ${msg.role}`}>
                {msg.text}
              </div>
            ))}
          </div>
          <div className="dashboard-chat-input-bar">
            <input
              className="dashboard-chat-input"
              type="text"
              placeholder="输入消息，按 Enter 发送…"
              value={dashInput}
              onChange={e => setDashInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey && dashInput.trim()) {
                  e.preventDefault();
                  handleDashSend();
                }
              }}
            />
            <button
              className="dashboard-chat-send"
              disabled={!dashInput.trim()}
              onClick={handleDashSend}
            >
              <Send size={18} />
            </button>
          </div>
      </div>
      </div>

    );
  };

  /* ── 看板覆盖层（独立渲染，避免嵌套在 dashboard div 内） ── */
  const renderOverlay = () => {
    if (!overlayPanel) return null;
    return <DashboardOverlay panel={overlayPanel} onClose={() => setOverlayPanel(null)} t={t} />;
  };

  /* ──────────── 工作区（PDF阅读器+面板） ──────────── */
  const renderWorkspace = () => (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden' }}>
      {/* 左侧窄图标栏 */}
      <div className="acasight-icon-bar" role="navigation" aria-label={t('layout.sidebar')}>
        <button
          className="acasight-icon-item"
          data-tooltip="返回看板"
          onClick={goDashboard}
          style={{ color: 'var(--accent)' }}
        >
          <LayoutGrid size={20} />
        </button>
        <div className="acasight-divider" />
        {SIDEBAR_COMPACT_ITEMS.map(item => (
          <div
            key={item.id}
            className={`acasight-icon-item ${openPanels.includes(item.id) ? 'active' : ''}`}
            data-tooltip={t(item.tooltipKey)}
            onClick={() => animatedTogglePanel(item.id)}
          >
            <item.icon size={20} />
          </div>
        ))}
        <div className="acasight-spacer" />
        <div
          className="acasight-icon-item"
          data-tooltip={showAIPanel ? t('layout.hideAI') : t('layout.showAI')}
          onClick={() => setShowAIPanel(prev => !prev)}
          style={showAIPanel ? { color: 'var(--accent)' } : {}}
        >
          <MessageSquare size={20} />
        </div>
        <div className="acasight-icon-item" data-tooltip={theme === 'dark' ? t('layout.lightMode') : t('layout.darkMode')} onClick={toggleTheme}>
          {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
        </div>
        <div className="acasight-icon-item" data-tooltip={t('common.settings')} onClick={() => setShowSettings(true)}>
          <Settings size={20} />
        </div>
      </div>

      {/* 主内容区 */}
      <div className="acasight-panel-container" ref={containerRef} role="main" aria-label={t('layout.mainContent')}>
        {openPanels.length === 0 ? (
          /* 看板页面（所有面板关闭时的过渡状态，useEffect 会自动跳转到完整看板） */
          <div className="acasight-panel" style={{ flex: 1 }}>
            <div className="acasight-panel-header">
              <span className="acasight-panel-title">
                <LayoutGrid size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                看板
              </span>
            </div>
            <div className="acasight-panel-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 16 }}>
              <div style={{ fontSize: 48, opacity: 0.15 }}>📊</div>
              <p style={{ color: 'var(--mute)', fontSize: 14 }}>从左侧功能栏选择功能开始使用</p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 600 }}>
                {FEATURE_ITEMS.slice(0, 8).map((f: FeatureItem) => (
                  <button
                    key={f.id}
                    onClick={() => enterWorkspace(f.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '8px 14px', borderRadius: 8,
                      background: 'var(--accent-bg-soft)', border: '1px solid var(--hairline)',
                      color: 'var(--body)', cursor: 'pointer', fontSize: 12,
                    }}
                  >
                    <f.icon size={14} style={{ color: f.color }} />
                    {t(f.labelKey)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          openPanels.map((panelId, index) => {
            const isEditor = panelId === 'editor';
            const def = PANEL_DEFS[panelId];
            const width = isEditor ? undefined : (panelWidths[panelId] || (def?.defaultWidth || 300));
            return (
              <React.Fragment key={panelId}>
                <div
                  className={`acasight-panel ${panelId === 'charts' ? 'panel-charts' : ''} ${animatingPanels[panelId] === 'in' ? 'panel-ripple-in' : ''} ${animatingPanels[panelId] === 'out' ? 'panel-ripple-out' : ''}`}
                  style={isEditor ? { flex: '1', minWidth: '300px' } : { width, flex: 'none' }}
                  onContextMenu={(e) => handleContextMenu(e, panelId)}
                >
                  <div className="acasight-panel-header">
                    <span className="acasight-panel-title">{isEditor ? (activeFile || t('layout.panelEditor')) : (def ? t(def.titleKey) : panelId)}</span>
                    <div className="acasight-panel-actions">
                      <button className="acasight-panel-btn" title={t('common.close')} onClick={() => animatedTogglePanel(panelId)}><X size={14} /></button>
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

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} showAI={showAIPanel} onToggleAI={() => setShowAIPanel(prev => !prev)} />}

      <ContextualAgentBar
        panelId="editor"
        selectedText={globalSelection?.text}
        pdfText={pdfFullText}
        mousePosition={mousePos}
        onOpenAgentPanel={handleOpenAgentPanel}
        onTranslate={handleTranslate}
      />

      {translateText && translatePosition && (
        <FloatingTranslate
          text={translateText}
          position={translatePosition}
          onClose={() => setTranslateText(null)}
          onOpenFullPage={(t: string) => { setShowFullPage(t); setTranslateText(null); }}
        />
      )}

      {showFloatingTranslate && floatTranslateText && (
        <FloatingTranslate
          text={floatTranslateText}
          position={floatTranslatePos}
          onClose={() => { setShowFloatingTranslate(false); setFloatTranslateText(''); }}
          onOpenFullPage={(t: string) => { setShowFullPage(t); setShowFloatingTranslate(false); setFloatTranslateText(''); }}
        />
      )}

      {showFullPage && (
        <FullPageTranslate
          text={showFullPage}
          onClose={() => setShowFullPage(null)}
        />
      )}

      {renderContextMenu()}
    </div>
  );

  /* ──────────── main render ──────────── */
  return (
    <FileOpenProvider openFile={openFile}>
      {/* Tauri drag & drop handler */}
      <TauriDragDrop onFilesDropped={(paths) => {
        const pdfPaths = paths.filter(p => p.toLowerCase().endsWith('.pdf'));
        if (pdfPaths.length > 0) {
          const name = pdfPaths[0].split(/[/\\]/).pop() || 'document.pdf';
          openFile(name, 'pdf', { file: pdfPaths[0] });
        }
      }} />
      {viewMode === 'dashboard' ? renderDashboard() : renderWorkspace()}
      {viewMode === 'dashboard' && renderOverlay()}
      {viewMode === 'dashboard' && showSettings && <SettingsModal onClose={() => setShowSettings(false)} showAI={showAIPanel} onToggleAI={() => setShowAIPanel(prev => !prev)} />}
    </FileOpenProvider>
  );
};
