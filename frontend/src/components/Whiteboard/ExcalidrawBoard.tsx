import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Excalidraw, MainMenu, Footer, convertToExcalidrawElements } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import '@excalidraw/excalidraw/index.css';
import {
  Loader2, X, Sparkles,
  CheckSquare, Square, Lightbulb, BookOpen,
  ImageIcon,
} from 'lucide-react';
import { papersApi } from '@/services/api';
import { plotApi } from '@/services/plotService';
import { usePlotStore } from '@/store/plotStore';
import type { PaperItem } from '@/services/api';

interface ExcalidrawBoardProps {
  boardId?: string;
}

type SidebarMode = 'none' | 'papers' | 'brainstorm';

export const ExcalidrawBoard: React.FC<ExcalidrawBoardProps> = ({
  boardId,
}) => {
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light'
  );
  const storageKey = boardId || 'default';
  void storageKey;

  const [sidebarMode, setSidebarMode] = useState<SidebarMode>('none');
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [focus, setFocus] = useState('');
  const [generating, setGenerating] = useState(false);
  const [brainstormContent, setBrainstormContent] = useState('');
  const [papersLoading, setPapersLoading] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => { mountedRef.current = true; return () => { mountedRef.current = false; }; }, []);

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  const loadPapers = useCallback(async () => {
    setPapersLoading(true);
    try {
      const res = await papersApi.list({ page_size: 100, sort_by: 'created_at', sort_order: 'desc' });
      if (mountedRef.current) setPapers(res.items || []);
    } catch {
      if (mountedRef.current) setPapers([]);
    } finally {
      if (mountedRef.current) setPapersLoading(false);
    }
  }, []);

  const togglePaper = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const handleImportPapersToCanvas = useCallback(() => {
    if (!excalidrawAPI || selectedIds.size === 0) return;
    const selectedPapers = papers.filter(p => selectedIds.has(p.id));
    const newElements: any[] = [];
    let startY = 50;
    const startX = 50;

    for (const paper of selectedPapers) {
      const meta = [
        paper.authors?.slice(0, 2).join(', '),
        paper.year ? String(paper.year) : '',
        paper.journal || '',
      ].filter(Boolean).join(' · ');

      const code = (paper as any).paper_code || `P${paper.id}`;

      const elements = convertToExcalidrawElements([
        {
          type: 'rectangle',
          id: `paper-${paper.id}-bg`,
          x: startX, y: startY, width: 360, height: 120,
          strokeColor: '#6366f1',
          backgroundColor: '#6366f120',
          fillStyle: 'solid',
          strokeWidth: 2,
          roughness: 0,
          roundness: { type: 3 },
        },
        {
          type: 'text',
          id: `paper-${paper.id}-code`,
          x: startX + 280, y: startY + 8, width: 70,
          text: code,
          fontSize: 9, fontFamily: 3, textAlign: 'right',
          strokeColor: '#6366f1',
        },
        {
          type: 'text',
          id: `paper-${paper.id}-title`,
          x: startX + 12, y: startY + 12, width: 260,
          text: paper.title || 'Untitled',
          fontSize: 14, fontFamily: 3, textAlign: 'left',
          strokeColor: theme === 'dark' ? '#e0e0e0' : '#1a1a1a',
        },
        ...(meta ? [{
          type: 'text' as const,
          id: `paper-${paper.id}-meta`,
          x: startX + 12, y: startY + 42, width: 336,
          text: meta,
          fontSize: 11, fontFamily: 3, textAlign: 'left',
          strokeColor: '#888888',
        }] : []),
        ...(paper.abstract ? [{
          type: 'text' as const,
          id: `paper-${paper.id}-abstract`,
          x: startX + 12, y: startY + 64, width: 336,
          text: paper.abstract.slice(0, 120) + (paper.abstract.length > 120 ? '...' : ''),
          fontSize: 10, fontFamily: 3, textAlign: 'left',
          strokeColor: '#666666',
        }] : []),
      ]);

      // 添加 customData 关联论文
      const bgEl = elements.find((e: any) => e.id === `paper-${paper.id}-bg`);
      if (bgEl) {
        (bgEl as any).customData = { paperId: paper.id, paperCode: code };
      }

      newElements.push(...elements);
      startY += 150;
    }

    const existing = excalidrawAPI.getSceneElements();
    excalidrawAPI.updateScene({ elements: [...existing, ...newElements] });
    excalidrawAPI.scrollToContent(newElements, { fitToContent: true });
    setSidebarMode('none');
  }, [excalidrawAPI, selectedIds, papers, theme]);

  const handleBrainstorm = useCallback(async () => {
    if (selectedIds.size < 2) return;
    setGenerating(true);
    setBrainstormContent('');
    try {
      const response = await fetch('/api/brainstorm/generate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ paper_ids: Array.from(selectedIds), focus: focus || null }),
      });
      if (!response.body) throw new Error('No response body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'chunk') {
                setBrainstormContent(prev => prev + data.content);
              } else if (data.type === 'complete') {
                setBrainstormContent(data.content);
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch (e) {
              if (e instanceof Error && !e.message.includes('JSON')) throw e;
            }
          }
        }
      }
    } catch (err) {
      alert('头脑风暴生成失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) setGenerating(false);
    }
  }, [selectedIds, focus]);

  const handleImportChart = useCallback(async () => {
    if (!excalidrawAPI) return;
    const schema = usePlotStore.getState().plotSchema;
    if (!schema) {
      alert('请先生成图表');
      return;
    }
    try {
      const result = await plotApi.exportPlot(schema, 'svg', 800, 500, 2);
      const imageUrl = result.image_url;
      excalidrawAPI.updateScene({
        elements: [
          ...excalidrawAPI.getSceneElements(),
          ...convertToExcalidrawElements([{
            type: 'image',
            x: 100 + Math.random() * 200,
            y: 100 + Math.random() * 200,
            width: 800,
            height: 500,
            fileId: imageUrl as any,
            status: 'saved',
          }]),
        ],
      });
    } catch (err) {
      console.error('Chart import failed:', err);
    }
  }, [excalidrawAPI]);

  const handleRenderBrainstormToCanvas = useCallback(() => {
    if (!excalidrawAPI || !brainstormContent) return;
    const lines = brainstormContent.split('\n').filter(l => l.trim());
    const newElements: any[] = [];
    const startX = 600;
    let nodeY = 50;

    // Title block
    const titleElements = convertToExcalidrawElements([
      {
        type: 'rectangle', id: 'brainstorm-title-bg',
        x: startX - 20, y: nodeY - 20, width: 500, height: 50,
        strokeColor: '#f59e0b', backgroundColor: '#f59e0b18',
        fillStyle: 'solid', strokeWidth: 2, roughness: 0, roundness: { type: 3 },
      },
      {
        type: 'text', id: 'brainstorm-title-text',
        x: startX, y: nodeY - 8, width: 460,
        text: 'AI头脑风暴',
        fontSize: 20, fontFamily: 3, textAlign: 'left', strokeColor: '#f59e0b',
      },
    ]);
    newElements.push(...titleElements);
    nodeY += 50;

    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim();
      if (!trimmed) continue;
      const isHeading = trimmed.startsWith('#') || trimmed.startsWith('##');
      const isBullet = trimmed.startsWith('-') || trimmed.startsWith('*') || /^\d+\./.test(trimmed);
      const cleanText = trimmed.replace(/^#{1,4}\s*/, '').replace(/^[-*]\s*/, '').replace(/^\d+\.\s*/, '');

      if (isHeading) {
        const headingElements = convertToExcalidrawElements([
          {
            type: 'rectangle', id: `bs-h-${i}`,
            x: startX - 10, y: nodeY - 4, width: 460, height: 28,
            strokeColor: '#f59e0b', backgroundColor: '#f59e0b10',
            fillStyle: 'solid', strokeWidth: 1, roughness: 0, roundness: { type: 3 },
          },
          {
            type: 'text', id: `bs-ht-${i}`,
            x: startX + 4, y: nodeY, width: 440,
            text: cleanText,
            fontSize: 14, fontFamily: 3, textAlign: 'left', strokeColor: '#f59e0b',
          },
        ]);
        newElements.push(...headingElements);
        nodeY += 38;
      } else if (isBullet) {
        const bulletElements = convertToExcalidrawElements([
          {
            type: 'text', id: `bs-b-${i}`,
            x: startX + 16, y: nodeY, width: 420,
            text: cleanText,
            fontSize: 12, fontFamily: 3, textAlign: 'left',
            strokeColor: theme === 'dark' ? '#cccccc' : '#333333',
          },
        ]);
        newElements.push(...bulletElements);
        nodeY += 22;
      } else {
        const textElements = convertToExcalidrawElements([
          {
            type: 'text', id: `bs-t-${i}`,
            x: startX, y: nodeY, width: 440,
            text: cleanText,
            fontSize: 12, fontFamily: 3, textAlign: 'left',
            strokeColor: theme === 'dark' ? '#cccccc' : '#333333',
          },
        ]);
        newElements.push(...textElements);
        nodeY += 20;
      }
    }

    const existing = excalidrawAPI.getSceneElements();
    excalidrawAPI.updateScene({ elements: [...existing, ...newElements] });
    excalidrawAPI.scrollToContent(newElements, { fitToContent: true });
    setSidebarMode('none');
    setBrainstormContent('');
  }, [excalidrawAPI, brainstormContent, theme]);

  const openSidebar = useCallback((mode: SidebarMode) => {
    if (sidebarMode === mode) { setSidebarMode('none'); return; }
    setSidebarMode(mode);
    if (mode === 'papers' || mode === 'brainstorm') {
      if (papers.length === 0) loadPapers();
    }
  }, [sidebarMode, papers.length, loadPapers]);

  const filteredPapers = searchQuery
    ? papers.filter(p => (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()))
    : papers;

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', background: 'var(--bg-primary)', color: 'var(--ink)' }}>
      {/* Sidebar: Paper selector / Brainstorm */}
      {sidebarMode !== 'none' && (
        <div style={{
          width: 280, minWidth: 240, borderRight: '1px solid var(--border-color)',
          display: 'flex', flexDirection: 'column', background: 'var(--canvas-soft)',
          flexShrink: 0, zIndex: 100,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 10px', borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {sidebarMode === 'brainstorm' ? <Lightbulb size={14} style={{ color: '#f59e0b' }} /> : <BookOpen size={14} style={{ color: 'var(--accent)' }} />}
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>
                {sidebarMode === 'brainstorm' ? 'AI头脑风暴' : '文献导入'}
              </span>
            </div>
            <button onClick={() => setSidebarMode('none')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 2 }}>
              <X size={14} />
            </button>
          </div>

          <div style={{ padding: '6px 10px' }}>
            <input
              type="text" placeholder="搜索论文..." value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={{
                width: '100%', background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {sidebarMode === 'brainstorm' && (
            <div style={{ padding: '4px 10px' }}>
              <input
                type="text" placeholder="聚焦方向（可选）" value={focus}
                onChange={e => setFocus(e.target.value)}
                style={{
                  width: '100%', background: 'var(--bg-2)', border: '1px solid var(--hairline)',
                  borderRadius: 4, padding: '4px 8px', fontSize: 11, color: 'var(--body)', outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
          )}

          <div style={{ padding: '2px 10px', fontSize: 10, color: 'var(--mute)' }}>
            已选 {selectedIds.size} 篇{sidebarMode === 'brainstorm' ? '（至少2篇）' : ''}
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {papersLoading && <div style={{ padding: 16, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}><Loader2 size={14} className="animate-spin" style={{ display: 'inline', marginRight: 4 }} />加载中...</div>}
            {!papersLoading && filteredPapers.map(paper => (
              <div
                key={paper.id}
                onClick={() => togglePaper(paper.id)}
                style={{
                  padding: '5px 10px', cursor: 'pointer', fontSize: 11,
                  background: selectedIds.has(paper.id) ? 'var(--accent-bg-soft)' : 'transparent',
                  borderBottom: '1px solid var(--hairline)',
                  display: 'flex', alignItems: 'flex-start', gap: 6,
                }}
              >
                {selectedIds.has(paper.id) ? <CheckSquare size={12} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 2 }} /> : <Square size={12} style={{ color: 'var(--mute)', flexShrink: 0, marginTop: 2 }} />}
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: selectedIds.has(paper.id) ? 'var(--accent)' : 'var(--body)' }}>
                  {paper.title}
                </div>
              </div>
            ))}
          </div>

          <div style={{ padding: '8px 10px', borderTop: '1px solid var(--border-color)', display: 'flex', gap: 6 }}>
            {sidebarMode === 'papers' && (
              <button
                onClick={handleImportPapersToCanvas}
                disabled={selectedIds.size === 0}
                style={{
                  flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                  padding: '6px 8px', fontSize: 11, borderRadius: 4, border: 'none',
                  background: 'var(--accent)', color: '#fff', cursor: selectedIds.size === 0 ? 'not-allowed' : 'pointer',
                  opacity: selectedIds.size === 0 ? 0.5 : 1,
                }}
              >
                <BookOpen size={12} /> 导入到白板
              </button>
            )}
            {sidebarMode === 'brainstorm' && (
              <>
                <button
                  onClick={handleBrainstorm}
                  disabled={generating || selectedIds.size < 2}
                  style={{
                    flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                    padding: '6px 8px', fontSize: 11, borderRadius: 4, border: 'none',
                    background: '#f59e0b', color: '#fff', cursor: generating ? 'wait' : 'pointer',
                    opacity: generating || selectedIds.size < 2 ? 0.5 : 1,
                  }}
                >
                  {generating ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                  {generating ? '生成中...' : '生成'}
                </button>
                {brainstormContent && (
                  <button
                    onClick={handleRenderBrainstormToCanvas}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                      padding: '6px 8px', fontSize: 11, borderRadius: 4, border: '1px solid var(--hairline)',
                      background: 'transparent', color: 'var(--body)', cursor: 'pointer',
                    }}
                  >
                    渲染到白板
                  </button>
                )}
              </>
            )}
          </div>

          {sidebarMode === 'brainstorm' && brainstormContent && (
            <div style={{
              maxHeight: 200, overflowY: 'auto', padding: '6px 10px',
              borderTop: '1px solid var(--border-color)',
              fontSize: 11, lineHeight: 1.6, color: 'var(--body)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {brainstormContent}
            </div>
          )}

          {/* Chart import button */}
          <div style={{ padding: '4px 10px', borderTop: '1px solid var(--border-color)' }}>
            <button
              onClick={handleImportChart}
              style={{ width: '100%', padding: '6px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, marginTop: 4 }}
            >
              <ImageIcon size={12} /> 导入图表到白板
            </button>
          </div>
        </div>
      )}

      {/* Excalidraw canvas — must have explicit height */}
      <div style={{ flex: 1, height: '100%', minWidth: 800 }}>
        <Excalidraw
          excalidrawAPI={(api: ExcalidrawImperativeAPI) => setExcalidrawAPI(api)}
          initialData={{
            elements: [],
            appState: {
              theme,
              viewBackgroundColor: theme === 'dark' ? '#1a1a1a' : '#ffffff',
            },
          }}
          onChange={() => {}}
          viewModeEnabled={false}
          langCode="zh-CN"
          theme={theme}
          UIOptions={{
            canvasActions: {
              changeViewBackgroundColor: true,
              clearCanvas: true,
              export: { saveFileToDisk: true },
              loadScene: true,
              saveToActiveFile: true,
              toggleTheme: true,
            },
            tools: { image: true },
          }}
        >
          <MainMenu>
            <MainMenu.Item icon={<span>📖</span>} onSelect={() => openSidebar('papers')}>
              导入文献到白板
            </MainMenu.Item>
            <MainMenu.Item icon={<span>💡</span>} onSelect={() => openSidebar('brainstorm')}>
              AI头脑风暴
            </MainMenu.Item>
            <MainMenu.DefaultItems.ClearCanvas />
            <MainMenu.DefaultItems.ToggleTheme />
            <MainMenu.DefaultItems.Export />
          </MainMenu>
          <Footer>
            <div style={{ display: 'flex', gap: 8, padding: '4px 8px', fontSize: 11, color: 'var(--mute)' }}>
              <span>AcaSight AI白板</span>
            </div>
          </Footer>
        </Excalidraw>
      </div>
    </div>
  );
};
