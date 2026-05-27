/**
 * AppContext — AcaSight 全局状态管理
 *
 * 参考 scholar-wiki 的 AppContext 设计，集中管理跨组件共享的状态。
 * ObsidianLayout 不再持有所有状态，各子面板通过 useApp() 获取/更新状态。
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { pdfApi, aiApi, zoteroApi, annotationsApi } from '@/services/api';
import type { ChatMessage, AnnotationItem } from '@/services/api';

// ==================== Types ====================

export interface EditorTab {
  id: string;
  name: string;
  type: 'pdf' | 'md';
  file?: string | File | null;
  pdfUrl?: string;
  abstract?: string;
  authors?: string;
  year?: number | string;
  journal?: string;
}

export interface Note {
  id: string;
  content: string;
  tags: string[];
  createdAt: string;
  pageNumber?: number;
}

export interface AIMsg {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface FileOpenMeta {
  file?: string | File;
  pdfUrl?: string;
  abstract?: string;
  authors?: string;
  year?: number | string;
  journal?: string;
}

interface AppContextType {
  // ---- Editor Tabs ----
  editorTabs: EditorTab[];
  activeTabId: string | null;
  setActiveTabId: (id: string | null) => void;
  openFile: (name: string, type: 'pdf' | 'md', meta?: FileOpenMeta) => void;
  closeTab: (tabId: string) => void;

  // ---- PDF ----
  pdfFile: string | File | null;
  setPdfFile: (f: string | File | null) => void;
  pdfFullText: string;
  setPdfFullText: React.Dispatch<React.SetStateAction<string>>;
  pdfDocRef: React.MutableRefObject<any>;
  pdfTextPagesRef: React.MutableRefObject<Set<number>>;
  numPages: number;
  setNumPages: (n: number) => void;
  currentPage: number;
  setCurrentPage: (p: number) => void;
  scale: number;
  setScale: (s: number | ((prev: number) => number)) => void;

  // ---- AI Panel ----
  aiMessages: AIMsg[];
  aiInput: string;
  setAiInput: (v: string) => void;
  aiLoading: boolean;
  sendAI: (msg?: string) => void;
  quickAI: (action: string) => void;

  // ---- AI Panel visibility ----
  showAIPanel: boolean;
  setShowAIPanel: (v: boolean | ((prev: boolean) => boolean)) => void;
  editorRightTab: 'notes' | 'toc';
  setEditorRightTab: (v: 'notes' | 'toc') => void;

  // ---- Notes ----
  notes: Note[];
  addNote: (content: string, tags: string[]) => void;
  deleteNote: (id: string) => void;

  // ---- Text Selection ----
  selectedText: string;
  setSelectedText: (v: string) => void;
  showAIToolbar: boolean;
  setShowAIToolbar: (v: boolean) => void;
  toolbarPos: { x: number; y: number };
  setToolbarPos: (v: { x: number; y: number }) => void;
  showFloatingTranslate: boolean;
  setShowFloatingTranslate: (v: boolean) => void;
  floatTranslateText: string;
  setFloatTranslateText: (v: string) => void;
  floatTranslatePos: { x: number; y: number };
  setFloatTranslatePos: (v: { x: number; y: number }) => void;

  // ---- Panels ----
  openPanels: string[];
  setOpenPanels: (v: string[] | ((prev: string[]) => string[])) => void;
  togglePanel: (panelId: string) => void;
  closePanel: (panelId: string) => void;

  // ---- Zotero ----
  zoteroConnected: boolean;
  setZoteroConnected: (v: boolean) => void;
  zoteroCollections: any[];
  setZoteroCollections: (v: any[]) => void;
  zoteroItems: any[];
  setZoteroItems: (v: any[]) => void;
  zoteroLoading: boolean;
  setZoteroLoading: (v: boolean) => void;

  // ---- Annotations ----
  pdfHash: string;
  setPdfHash: (v: string) => void;
  annotations: import('@/services/api').AnnotationItem[];
  setAnnotations: React.Dispatch<React.SetStateAction<import('@/services/api').AnnotationItem[]>>;
  loadAnnotations: (pdfHash: string) => Promise<void>;
  createAnnotation: (data: Omit<import('@/services/api').AnnotationItem, 'id' | 'created_at' | 'updated_at'>) => Promise<void>;
  deleteAnnotation: (id: number) => Promise<void>;
  annotationTool: 'highlight' | 'underline' | 'note' | 'eraser' | null;
  setAnnotationTool: (v: 'highlight' | 'underline' | 'note' | 'eraser' | null) => void;
  annotationColor: string;
  setAnnotationColor: (v: string) => void;

  // ---- Outline ----
  outline: Array<{ level: number; title: string; page: number }>;
  setOutline: React.Dispatch<React.SetStateAction<Array<{ level: number; title: string; page: number }>>>;

  // ---- Cross-panel Linkage ----
  pendingNoteContent: string;
  setPendingNoteContent: (v: string) => void;

  // ---- File Upload ----
  handleFileUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
}

const AppContext = createContext<AppContextType | null>(null);

export const useApp = (): AppContextType => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
};

// ==================== Provider ====================

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // ---- Editor Tabs ----
  const [editorTabs, setEditorTabs] = useState<EditorTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [openPanels, setOpenPanels] = useState<string[]>(['file-explorer', 'editor']);

  // ---- PDF ----
  const [pdfFile, setPdfFile] = useState<string | File | null>(null);
  const [pdfFullText, setPdfFullText] = useState('');
  const pdfDocRef = useRef<any>(null);
  const pdfTextPagesRef = useRef<Set<number>>(new Set());
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.2);

  // ---- AI Panel ----
  const [showAIPanel, setShowAIPanel] = useState<boolean>(() => {
    const saved = localStorage.getItem('acasight-ai-panel');
    return saved !== null ? saved === 'true' : true;
  });
  const [editorRightTab, setEditorRightTab] = useState<'notes' | 'toc'>('notes');
  const [aiMessages, setAiMessages] = useState<AIMsg[]>([]);
  const [aiInput, setAiInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const aiEndRef = useRef<HTMLDivElement>(null);

  // ---- Notes ----
  const [notes, setNotes] = useState<Note[]>([]);

  // ---- Text Selection ----
  const [selectedText, setSelectedText] = useState('');
  const [showAIToolbar, setShowAIToolbar] = useState(false);
  const [toolbarPos, setToolbarPos] = useState({ x: 0, y: 0 });
  const [showFloatingTranslate, setShowFloatingTranslate] = useState(false);
  const [floatTranslateText, setFloatTranslateText] = useState('');
  const [floatTranslatePos, setFloatTranslatePos] = useState({ x: 0, y: 0 });

  // ---- Zotero ----
  const [zoteroConnected, setZoteroConnected] = useState(false);
  const [zoteroCollections, setZoteroCollections] = useState<any[]>([]);
  const [zoteroItems, setZoteroItems] = useState<any[]>([]);
  const [zoteroLoading, setZoteroLoading] = useState(false);

  // ---- Annotations ----
  const [pdfHash, setPdfHash] = useState('');
  const [annotations, setAnnotations] = useState<AnnotationItem[]>([]);
  const [annotationTool, setAnnotationTool] = useState<'highlight' | 'underline' | 'note' | 'eraser' | null>(null);
  const [annotationColor, setAnnotationColor] = useState('#FFEB3B');

  // ---- Outline ----
  const [outline, setOutline] = useState<Array<{ level: number; title: string; page: number }>>([]);

  // ---- Cross-panel Linkage ----
  const [pendingNoteContent, setPendingNoteContent] = useState('');

  // ---- File Upload ----
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // ---- Derived ----
  const activeFile = editorTabs.find(t => t.id === activeTabId)?.name || '';
  const activeTab = editorTabs.find(t => t.id === activeTabId);

  // ==================== Annotations Callbacks ====================

  const loadAnnotations = useCallback(async (hash: string) => {
    if (!hash) return;
    try {
      const items = await annotationsApi.list({ pdf_hash: hash });
      setAnnotations(items);
    } catch {
      setAnnotations([]);
    }
  }, []);

  const createAnnotation = useCallback(async (data: Omit<AnnotationItem, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      const created = await annotationsApi.create(data as any);
      setAnnotations(prev => [...prev, created]);
    } catch (err: any) {
      console.error('Failed to create annotation:', err.message);
    }
  }, []);

  const deleteAnnotation = useCallback(async (id: number) => {
    try {
      await annotationsApi.delete(id);
      setAnnotations(prev => prev.filter(a => a.id !== id));
    } catch (err: any) {
      console.error('Failed to delete annotation:', err.message);
    }
  }, []);

  // ==================== Effects ====================

  // Sync PDF when active tab changes
  useEffect(() => {
    if (activeTab?.type === 'pdf') {
      if (activeTab.file) {
        setPdfFile(activeTab.file);
      } else if (activeTab.pdfUrl) {
        const proxyUrl = `http://localhost:9000/api/pdf/proxy?url=${encodeURIComponent(activeTab.pdfUrl)}`;
        setPdfFile(proxyUrl);
      } else {
        setPdfFile(null);
      }
    } else {
      setPdfFile(null);
    }
    setCurrentPage(1);
  }, [activeTabId]);

  // Clear PDF text cache on file change → trigger backend extraction
  useEffect(() => {
    pdfTextPagesRef.current.clear();
    setPdfFullText('');

    // 后端 PyMuPDF 全文提取（替代前端 onRenderSuccess 逐页提取）
    if (pdfFile) {
      const extractUrl = pdfFile;
      (async () => {
        try {
          const res = await fetch('http://localhost:9000/api/pdf/extract-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: extractUrl, max_chars: 50000 }),
          });
          if (res.ok) {
            const data = await res.json();
            if (data.text) {
              setPdfFullText(data.text);
              return; // 后端提取成功，无需前端逐页提取
            }
          }
        } catch {
          // 后端提取失败，前端 onRenderSuccess 仍然可用作兜底
        }
      })();
    }
  }, [pdfFile]);

  // Load outline + hash + annotations when PDF file changes
  useEffect(() => {
    if (!pdfFile) {
      setOutline([]);
      setPdfHash('');
      setAnnotations([]);
      return;
    }
    // Compute hash and load outline/annotations
    const loadPdfMeta = async () => {
      try {
        // Get hash for annotation association
        const hashRes = await pdfApi.hash(String(pdfFile));
        setPdfHash(hashRes.hash);
        // Load annotations for this PDF
        await loadAnnotations(hashRes.hash);
      } catch {
        setPdfHash('');
      }
      try {
        // Try to load TOC from backend
        const path = String(pdfFile).replace('http://localhost:9000/api/pdf/proxy?url=', '');
        const decodedPath = decodeURIComponent(path);
        const tocRes = await pdfApi.toc(decodedPath);
        setOutline(tocRes.toc || []);
      } catch {
        setOutline([]);
      }
    };
    loadPdfMeta();
  }, [pdfFile, loadAnnotations]);

  // Auto-scroll AI messages
  useEffect(() => {
    aiEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [aiMessages]);

  // Persist AI panel visibility
  useEffect(() => {
    localStorage.setItem('acasight-ai-panel', String(showAIPanel));
  }, [showAIPanel]);

  // Zotero periodic check
  const parseMcpResult = (data: any): any => {
    if (data?.content && Array.isArray(data.content)) {
      const textItem = data.content.find((c: any) => c.type === 'text');
      if (textItem?.text) {
        try { return JSON.parse(textItem.text); } catch { return textItem.text; }
      }
    }
    return data;
  };

  useEffect(() => {
    let cancelled = false;
    const checkZotero = async () => {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 3000);
        const res = await fetch('http://localhost:9000/api/zotero/status', { signal: controller.signal });
        clearTimeout(timer);
        if (cancelled) return;
        const data = await res.json();
        setZoteroConnected(data.connected);
        if (data.connected) {
          try {
            const colsRaw = await zoteroApi.getCollections();
            const cols = parseMcpResult(colsRaw);
            if (!cancelled) setZoteroCollections(Array.isArray(cols) ? cols : []);
          } catch { /* ignore */ }
        }
      } catch {
        if (!cancelled) setZoteroConnected(false);
      }
    };
    checkZotero();
    const interval = setInterval(checkZotero, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  // ==================== Callbacks ====================

  const openFile = useCallback((name: string, type: 'pdf' | 'md', meta?: FileOpenMeta) => {
    const id = Date.now().toString();
    const tab: EditorTab = { id, name, type, ...meta };
    setEditorTabs(prev => {
      const existing = prev.find(t => t.name === name);
      if (existing) {
        setActiveTabId(existing.id);
        return meta ? prev.map(t => t.name === name ? { ...t, ...meta } : t) : prev;
      }
      setActiveTabId(id);
      return [...prev, tab];
    });
    setOpenPanels(p => p.includes('editor') ? p : [...p, 'editor']);
  }, []);

  const closeTab = useCallback((tabId: string) => {
    setEditorTabs(prev => {
      const next = prev.filter(t => t.id !== tabId);
      if (activeTabId === tabId) setActiveTabId(next.length > 0 ? next[next.length - 1].id : null);
      return next;
    });
  }, [activeTabId]);

  const togglePanel = useCallback((panelId: string) => {
    setOpenPanels(prev => {
      if (prev.includes(panelId)) return prev.filter(id => id !== panelId);
      const ei = prev.indexOf('editor');
      if (ei >= 0) return [...prev.slice(0, ei), panelId, ...prev.slice(ei)];
      return [...prev, panelId];
    });
  }, []);

  const closePanel = useCallback((panelId: string) => {
    setOpenPanels(prev => prev.filter(id => id !== panelId));
  }, []);

  // ==================== AI Callbacks ====================

  const sendAI = useCallback(async (msg?: string) => {
    const query = msg || aiInput;
    if (!query.trim() || aiLoading) return;
    const userMsg: AIMsg = { id: Date.now().toString(), role: 'user', content: query };
    setAiMessages(prev => [...prev, userMsg]);
    setAiInput('');
    setAiLoading(true);
    try {
      const msgs: ChatMessage[] = [
        { role: 'system', content: pdfFullText
          ? `你是一位学术研究助手，正在帮助用户阅读一篇学术文献。

以下是文献全文（基于 PDF 文本提取）：
--- 文献全文开始 ---
${pdfFullText.slice(0, 12000)}
--- 文献全文结束 ---

请基于以上文献全文内容回答用户的问题。如果用户让你翻译某段内容，优先从全文查找对应原文。如果需要引用，请标注大致段落位置。
如果用户的问题与这篇文献无关，也请正常回答。`
          : '你是学术研究助手，帮助用户理解文献、翻译、总结、分析。' },
        ...aiMessages.slice(-6).map(m => ({ role: m.role as 'user' | 'assistant', content: m.content })),
        { role: 'user', content: query },
      ];
      const res = await aiApi.chat(msgs);
      setAiMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: res.response || JSON.stringify(res) }]);
    } catch (err: any) {
      setAiMessages(prev => [...prev, { id: (Date.now() + 1).toString(), role: 'assistant', content: `请求失败: ${err.message}\n\n请检查后端服务是否运行。` }]);
    } finally {
      setAiLoading(false);
    }
  }, [aiInput, aiLoading, aiMessages, pdfFullText]);

  const quickAI = useCallback((action: string) => {
    const prompts: Record<string, string> = {
      summarize: `请总结这篇文献的核心内容：${activeFile}`,
      methods: `请分析这篇文献的研究方法：${activeFile}`,
      gaps: `请指出这篇文献的研究空白和未来方向：${activeFile}`,
      deepread: `请对当前文献进行 AI 精读分析：${activeFile}`,
    };
    if (prompts[action]) sendAI(prompts[action]);
  }, [activeFile, sendAI]);

  const addNote = useCallback((content: string, tags: string[]) => {
    if (!content.trim()) return;
    setNotes(prev => [{
      id: Date.now().toString(),
      content,
      tags: tags.filter(Boolean),
      createdAt: new Date().toLocaleString('zh-CN'),
    }, ...prev]);
  }, []);

  const deleteNote = useCallback((id: string) => {
    setNotes(prev => prev.filter(n => n.id !== id));
  }, []);

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const id = Date.now().toString();
    const tab: EditorTab = { id, name: file.name, type: 'pdf', file };
    setEditorTabs(prev => [...prev, tab]);
    setActiveTabId(id);
    setPdfFile(file);
    setCurrentPage(1);
    setOpenPanels(p => p.includes('editor') ? p : [...p, 'editor']);
    try { await pdfApi.upload(file); } catch { /* ignore */ }
    e.target.value = '';
  }, []);

  // ==================== Context Value ====================

  const value: AppContextType = {
    editorTabs, activeTabId, setActiveTabId, openFile, closeTab,
    pdfFile, setPdfFile, pdfFullText, setPdfFullText, pdfDocRef, pdfTextPagesRef,
    numPages, setNumPages, currentPage, setCurrentPage, scale, setScale,
    aiMessages, aiInput, setAiInput, aiLoading, sendAI, quickAI,
    showAIPanel, setShowAIPanel, editorRightTab, setEditorRightTab,
    notes, addNote, deleteNote,
    selectedText, setSelectedText,
    showAIToolbar, setShowAIToolbar, toolbarPos, setToolbarPos,
    showFloatingTranslate, setShowFloatingTranslate,
    floatTranslateText, setFloatTranslateText,
    floatTranslatePos, setFloatTranslatePos,
    openPanels, setOpenPanels, togglePanel, closePanel,
    zoteroConnected, setZoteroConnected,
    zoteroCollections, setZoteroCollections,
    zoteroItems, setZoteroItems,
    zoteroLoading, setZoteroLoading,
    pdfHash, setPdfHash, annotations, setAnnotations, loadAnnotations, createAnnotation, deleteAnnotation, annotationTool, setAnnotationTool, annotationColor, setAnnotationColor,
    outline, setOutline,
    pendingNoteContent, setPendingNoteContent,
    handleFileUpload, fileInputRef,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
};
