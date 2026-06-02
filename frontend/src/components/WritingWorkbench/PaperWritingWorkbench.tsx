import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  PenLine, Shrink, Sparkles, Languages, RefreshCw,
  Copy, Check, ChevronDown, Loader2, ArrowRight, BookOpen, Cpu, RefreshCcwDot,
  PenTool, LucideIcon,
  Brain, FileText, CheckSquare, Square,
  Play, Pencil, Download, RotateCcw, ChevronRight,
} from 'lucide-react';
import { useAIModels } from '@/hooks/useAIModels';
import { useApp, usePanels } from '@/contexts/AppContext';
import { writingApi, papersApi, literatureReviewApi } from '@/services/api';
import type { PaperItem } from '@/services/api';

type WritingAction = 'expand' | 'shrink' | 'polish' | 'translate' | 'rewrite';

interface ActionConfig {
  id: WritingAction;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;
}

const ACTIONS: ActionConfig[] = [
  { id: 'expand', label: '扩写', description: '补充细节、论据，扩展 2-3 倍', icon: PenLine, color: '#6366f1' },
  { id: 'shrink', label: '缩写', description: '精炼核心观点，压缩至 1/3', icon: Shrink, color: '#06b6d4' },
  { id: 'polish', label: '润色', description: '口语化→学术语言，改善句式', icon: Sparkles, color: '#f59e0b' },
  { id: 'translate', label: '翻译', description: '中→英 / 英→中，术语准确', icon: Languages, color: '#10b981' },
  { id: 'rewrite', label: '降重', description: '改写句式，降低查重率至 15%', icon: RefreshCw, color: '#ef4444' },
];

const LANG_OPTIONS = [
  { value: 'en', label: '英文' },
  { value: 'zh', label: '中文' },
  { value: 'ja', label: '日文' },
  { value: 'de', label: '德文' },
  { value: 'fr', label: '法文' },
];

type ReviewStep = 'select' | 'outline' | 'writing' | 'complete';

interface OutlineSection {
  heading: string;
  paper_refs?: number[];
  subsections?: OutlineSection[];
}

type WorkbenchTab = 'review' | 'writing';

export const PaperWritingWorkbench: React.FC = () => {
  const [activeTab, setActiveTab] = useState<WorkbenchTab>('review');

  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const res = await papersApi.list({ page_size: 100, sort_by: 'created_at', sort_order: 'desc' });
        if (!cancelled && mountedRef.current) setPapers(res.items || []);
      } catch {
        if (!cancelled && mountedRef.current) setPapers([]);
      } finally {
        if (!cancelled && mountedRef.current) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; mountedRef.current = false; };
  }, []);

  const togglePaper = useCallback((id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const filteredPapers = searchQuery
    ? papers.filter(p => (p.title || '').toLowerCase().includes(searchQuery.toLowerCase()))
    : papers;

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      <div style={{
        width: 260, minWidth: 200, borderRight: '1px solid var(--hairline)',
        display: 'flex', flexDirection: 'column', background: 'var(--canvas-soft)',
      }}>
        <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--hairline)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
            <PenTool size={14} style={{ color: '#8b5cf6' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>论文撰写工作台</span>
          </div>
          <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
            <button
              onClick={() => setActiveTab('review')}
              style={{
                flex: 1, padding: '4px 0', fontSize: 10, borderRadius: 4, border: '1px solid',
                borderColor: activeTab === 'review' ? '#8b5cf6' : 'var(--hairline)',
                background: activeTab === 'review' ? 'rgba(139,92,246,0.1)' : 'transparent',
                color: activeTab === 'review' ? '#8b5cf6' : 'var(--mute)',
                cursor: 'pointer', fontWeight: 600,
              }}
            >
              文献综述
            </button>
            <button
              onClick={() => setActiveTab('writing')}
              style={{
                flex: 1, padding: '4px 0', fontSize: 10, borderRadius: 4, border: '1px solid',
                borderColor: activeTab === 'writing' ? '#8b5cf6' : 'var(--hairline)',
                background: activeTab === 'writing' ? 'rgba(139,92,246,0.1)' : 'transparent',
                color: activeTab === 'writing' ? '#8b5cf6' : 'var(--mute)',
                cursor: 'pointer', fontWeight: 600,
              }}
            >
              AI写作
            </button>
          </div>
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
        <div style={{ padding: '4px 10px', fontSize: 10, color: 'var(--mute)' }}>
          已选 {selectedIds.size} 篇文献
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading && <div style={{ padding: 16, textAlign: 'center', color: 'var(--mute)', fontSize: 11 }}><Loader2 size={14} className="animate-spin" style={{ display: 'inline', marginRight: 4 }} />加载中...</div>}
          {!loading && filteredPapers.map(paper => (
            <div
              key={paper.id}
              onClick={() => togglePaper(paper.id)}
              style={{
                padding: '6px 10px', cursor: 'pointer', fontSize: 11,
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
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {activeTab === 'review' ? (
          <LiteratureReviewTab papers={papers} selectedIds={selectedIds} mountedRef={mountedRef} />
        ) : (
          <AIWritingTab />
        )}
      </div>
    </div>
  );
};

const LiteratureReviewTab: React.FC<{
  papers: PaperItem[];
  selectedIds: Set<number>;
  mountedRef: React.MutableRefObject<boolean>;
}> = ({ papers, selectedIds, mountedRef }) => {
  const [topic, setTopic] = useState('');
  const [step, setStep] = useState<ReviewStep>('select');
  const [outline, setOutline] = useState<OutlineSection[]>([]);
  const [outlineRaw, setOutlineRaw] = useState('');
  const [editingOutline, setEditingOutline] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const [reviewContent, setReviewContent] = useState('');
  const [sections, setSections] = useState<Array<{ heading: string; content: string }>>([]);

  const handleGenerateOutline = useCallback(async () => {
    if (!topic.trim() || selectedIds.size === 0) return;
    setGenerating(true);
    setProgress('正在生成大纲...');
    try {
      const res = await literatureReviewApi.generateOutline(topic, Array.from(selectedIds));
      if (mountedRef.current) {
        const secs = (res.outline as { sections?: OutlineSection[] })?.sections || [];
        setOutline(secs);
        setOutlineRaw(JSON.stringify(secs, null, 2));
        setStep('outline');
      }
    } catch (err) {
      alert('大纲生成失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      if (mountedRef.current) {
        setGenerating(false);
        setProgress('');
      }
    }
  }, [topic, selectedIds, mountedRef]);

  const handleStartWriting = useCallback(async () => {
    setStep('writing');
    setGenerating(true);
    setProgress('正在生成综述...');
    setReviewContent('');
    setSections([]);
    try {
      const url = literatureReviewApi.generateStream(topic, Array.from(selectedIds));
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, paper_ids: Array.from(selectedIds), style: 'narrative' }),
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
              if (data.type === 'start') {
                setProgress(`开始生成，共 ${data.paper_count} 篇文献...`);
              } else if (data.type === 'outline') {
                setProgress('大纲已生成，开始写作...');
              } else if (data.type === 'section_complete') {
                setProgress(`章节完成: ${data.heading}`);
              } else if (data.type === 'complete') {
                if (mountedRef.current) {
                  setReviewContent(data.content);
                  setSections(data.sections || []);
                  setStep('complete');
                  setGenerating(false);
                  setProgress('');
                }
              } else if (data.type === 'error') {
                throw new Error(data.message);
              }
            } catch { /* skip invalid JSON */ }
          }
        }
      }
    } catch (err) {
      alert('综述生成失败: ' + (err instanceof Error ? err.message : String(err)));
      if (mountedRef.current) {
        setGenerating(false);
        setProgress('');
      }
    }
  }, [topic, selectedIds, mountedRef]);

  const handleExport = useCallback(() => {
    if (!reviewContent) return;
    const blob = new Blob([reviewContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${topic || '文献综述'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }, [reviewContent, topic]);

  const handleReset = useCallback(() => {
    setStep('select');
    setOutline([]);
    setOutlineRaw('');
    setReviewContent('');
    setSections([]);
    setEditingOutline(false);
  }, []);

  return (
    <>
      <div style={{
        padding: '8px 16px', borderBottom: '1px solid var(--hairline)',
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'var(--glass-bg, var(--bg-2))',
      }}>
        {([
          { key: 'select', label: '1. 选择文献', icon: <CheckSquare size={12} /> },
          { key: 'outline', label: '2. 生成大纲', icon: <FileText size={12} /> },
          { key: 'writing', label: '3. 生成综述', icon: <Brain size={12} /> },
          { key: 'complete', label: '4. 完成', icon: <Sparkles size={12} /> },
        ] as const).map((s, idx) => (
          <React.Fragment key={s.key}>
            {idx > 0 && <ChevronRight size={10} style={{ color: 'var(--mute)' }} />}
            <div style={{
              display: 'flex', alignItems: 'center', gap: 4,
              fontSize: 11, fontWeight: step === s.key ? 600 : 400,
              color: step === s.key ? 'var(--accent)' : ['select', 'outline', 'writing', 'complete'].indexOf(step) >= idx ? 'var(--body)' : 'var(--mute)',
            }}>
              {s.icon} {s.label}
            </div>
          </React.Fragment>
        ))}
        <div style={{ flex: 1 }} />
        {step !== 'select' && (
          <button onClick={handleReset} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', fontSize: 10, borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--mute)', cursor: 'pointer' }}>
            <RotateCcw size={10} /> 重置
          </button>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {step === 'select' && (
          <div style={{ maxWidth: 600, margin: '0 auto' }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--body)', marginBottom: 16 }}>
              创建文献综述
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 500, color: 'var(--body)', marginBottom: 6 }}>
                综述主题
              </label>
              <input
                type="text" value={topic}
                onChange={e => setTopic(e.target.value)}
                placeholder="例如：知识图谱与深度学习融合研究综述"
                style={{
                  width: '100%', padding: '8px 12px', fontSize: 13,
                  borderRadius: 6, border: '1px solid var(--hairline)',
                  background: 'var(--bg-2)', color: 'var(--body)', outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--body)', marginBottom: 6 }}>
                已选择 {selectedIds.size} 篇文献
              </div>
              {selectedIds.size === 0 && (
                <div style={{ fontSize: 11, color: 'var(--mute)', fontStyle: 'italic' }}>
                  请从左侧列表中选择文献
                </div>
              )}
              {selectedIds.size > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {papers.filter(p => selectedIds.has(p.id)).map(p => (
                    <span key={p.id} style={{
                      fontSize: 10, padding: '2px 6px', borderRadius: 3,
                      background: 'var(--accent-bg-soft)', color: 'var(--accent)',
                      maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {p.title}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <button
              onClick={handleGenerateOutline}
              disabled={generating || !topic.trim() || selectedIds.size === 0}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px',
                fontSize: 13, borderRadius: 6, border: 'none',
                background: 'var(--accent)', color: '#fff', cursor: generating ? 'wait' : 'pointer',
                opacity: generating || !topic.trim() || selectedIds.size === 0 ? 0.5 : 1,
              }}
            >
              {generating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {generating ? '生成中...' : '生成大纲'}
            </button>
          </div>
        )}

        {step === 'outline' && (
          <div style={{ maxWidth: 700, margin: '0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>综述大纲</div>
              <button
                onClick={() => setEditingOutline(!editingOutline)}
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', fontSize: 10, borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer' }}
              >
                <Pencil size={10} /> {editingOutline ? '完成编辑' : '编辑大纲'}
              </button>
            </div>
            {editingOutline ? (
              <textarea
                value={outlineRaw}
                onChange={e => { setOutlineRaw(e.target.value); try { setOutline(JSON.parse(e.target.value)); } catch { /* ignore */ } }}
                style={{
                  width: '100%', minHeight: 300, padding: 12, fontSize: 12,
                  borderRadius: 6, border: '1px solid var(--hairline)',
                  background: 'var(--bg-2)', color: 'var(--body)', outline: 'none',
                  fontFamily: 'monospace', boxSizing: 'border-box', resize: 'vertical',
                }}
              />
            ) : (
              <div style={{ padding: 12, borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--bg-2)' }}>
                {outline.map((section, idx) => (
                  <div key={idx} style={{ marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <ChevronDown size={12} style={{ color: 'var(--accent)' }} />
                      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--body)' }}>{idx + 1}. {section.heading}</span>
                      {section.paper_refs && (
                        <span style={{ fontSize: 9, color: 'var(--mute)' }}>
                          引用: 论文{section.paper_refs.join(', ')}
                        </span>
                      )}
                    </div>
                    {section.subsections?.map((sub, sIdx) => (
                      <div key={sIdx} style={{ marginLeft: 24, marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <ChevronRight size={10} style={{ color: 'var(--mute)' }} />
                        <span style={{ fontSize: 12, color: 'var(--body)' }}>{sub.heading}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
            <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
              <button
                onClick={handleStartWriting}
                disabled={generating}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px',
                  fontSize: 13, borderRadius: 6, border: 'none',
                  background: 'var(--accent)', color: '#fff', cursor: generating ? 'wait' : 'pointer',
                  opacity: generating ? 0.7 : 1,
                }}
              >
                {generating ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                开始写作
              </button>
            </div>
          </div>
        )}

        {step === 'writing' && (
          <div style={{ maxWidth: 700, margin: '0 auto', textAlign: 'center', paddingTop: 40 }}>
            <Loader2 size={32} className="animate-spin" style={{ color: 'var(--accent)', marginBottom: 16 }} />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)', marginBottom: 8 }}>
              正在生成文献综述...
            </div>
            <div style={{ fontSize: 12, color: 'var(--mute)' }}>{progress}</div>
            {sections.length > 0 && (
              <div style={{ marginTop: 16, textAlign: 'left' }}>
                {sections.map((s, idx) => (
                  <div key={idx} style={{ padding: '4px 0', fontSize: 11, color: 'var(--body)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Sparkles size={10} style={{ color: '#10b981' }} /> {s.heading}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 'complete' && (
          <div style={{ maxWidth: 800, margin: '0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--body)' }}>
                文献综述: {topic}
              </div>
              <button onClick={handleExport} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', fontSize: 10, borderRadius: 4, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer' }}>
                <Download size={10} /> 导出Markdown
              </button>
            </div>
            <div style={{
              padding: 16, borderRadius: 8, border: '1px solid var(--hairline)',
              background: 'var(--bg-2)', fontSize: 13, lineHeight: 1.8, color: 'var(--body)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            }}>
              {reviewContent}
            </div>
          </div>
        )}
      </div>
    </>
  );
};

const AIWritingTab: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');
  const [action, setAction] = useState<WritingAction>('polish');
  const [targetLang, setTargetLang] = useState('en');
  const [context, setContext] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [wordCountBefore, setWordCountBefore] = useState(0);
  const [wordCountAfter, setWordCountAfter] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { models, currentModel, loading: modelsLoading, refreshModels, selectModel } = useAIModels();
  const { setPendingNoteContent } = useApp();
  const { togglePanel, openPanels } = usePanels();
  const [selectedModel, setSelectedModel] = useState<string>('');

  useEffect(() => { setSelectedModel(currentModel); }, [currentModel]);
  useEffect(() => { refreshModels(); }, [refreshModels]);

  const handleProcess = useCallback(async () => {
    const text = inputText.trim();
    if (!text) return;
    setIsProcessing(true);
    setOutputText('');
    setCopied(false);
    try {
      const reqBody: { text: string; action: string; target_lang?: string; context?: string; model?: string } = {
        text,
        action,
        target_lang: targetLang,
      };
      if (context) reqBody.context = context;
      if (selectedModel) reqBody.model = selectedModel;
      const data = await writingApi.process(reqBody);
      setOutputText(data.result || '');
      setWordCountBefore(data.word_count_before || 0);
      setWordCountAfter(data.word_count_after || 0);
    } catch (e: unknown) {
      setOutputText(`❌ 处理失败: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setIsProcessing(false);
    }
  }, [inputText, action, targetLang, context, selectedModel]);

  const handleCopy = useCallback(async () => {
    if (!outputText) return;
    try {
      await navigator.clipboard.writeText(outputText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* fallback */ }
  }, [outputText]);

  const handleUseAsInput = useCallback(() => {
    if (!outputText || outputText.startsWith('❌')) return;
    setInputText(outputText);
    setOutputText('');
    inputRef.current?.focus();
  }, [outputText]);

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      setInputText(prev => prev + text);
    } catch { /* denied */ }
  }, []);

  const currentAction = ACTIONS.find(a => a.id === action)!;
  const borderColor = 'var(--color-border)';
  const cardBg = 'var(--color-card-bg)';

  return (
    <div className="h-full flex flex-col theme-transition" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      <div className="p-5 pb-3" style={{ borderBottom: `1px solid ${borderColor}` }}>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
            <PenLine size={24} /> 智能写作助手
          </h1>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs" style={{ backgroundColor: 'var(--color-bg-tertiary)', border: `1px solid var(--color-border)` }}>
              <Cpu size={12} style={{ color: 'var(--color-text-muted)' }} />
              <select
                value={selectedModel}
                onChange={(e) => { setSelectedModel(e.target.value); selectModel(e.target.value); }}
                className="outline-none text-xs bg-transparent"
                style={{ color: 'var(--color-text-primary)', maxWidth: 180 }}
                title={selectedModel}
              >
                {models.length === 0 && <option value="">默认模型</option>}
                {models.map(m => (
                  <option key={m.id} value={m.id}>{m.label}</option>
                ))}
              </select>
              <button
                onClick={() => refreshModels()}
                className="p-0.5 rounded transition-colors"
                style={{ color: 'var(--color-text-muted)' }}
                title="刷新模型列表"
              >
                <RefreshCcwDot size={11} className={modelsLoading ? 'animate-spin' : ''} />
              </button>
            </div>
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs transition-colors"
              style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-secondary)' }}
            >
              <BookOpen size={12} />
              高级设置
              <ChevronDown size={12} className={`transition-transform ${showSettings ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>
        {showSettings && (
          <div className="mt-3 p-3 rounded-xl animate-fade-in" style={{ backgroundColor: 'var(--color-bg-tertiary)', border: `1px solid ${borderColor}` }}>
            <div className="flex items-center gap-4">
              {action === 'translate' && (
                <div className="flex items-center gap-2">
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>目标语言:</span>
                  <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="rounded-lg px-3 py-1.5 text-sm outline-none"
                    style={{
                      backgroundColor: 'var(--color-card-bg)',
                      border: `1px solid ${borderColor}`,
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {LANG_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="flex-1">
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>写作背景（可选）:</span>
                <input
                  type="text"
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="例如：材料学 XRD 分析报告"
                  className="w-full mt-1 px-3 py-1.5 rounded-lg text-sm outline-none"
                  style={{
                    backgroundColor: 'var(--color-card-bg)',
                    border: `1px solid ${borderColor}`,
                    color: 'var(--color-text-primary)',
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="px-5 py-3" style={{ borderBottom: `1px solid ${borderColor}` }}>
        <div className="flex gap-2 flex-wrap">
          {ACTIONS.map((act) => {
            const Icon = act.icon;
            const isActive = action === act.id;
            return (
              <button
                key={act.id}
                onClick={() => setAction(act.id)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition-all"
                style={{
                  backgroundColor: isActive ? `${act.color}15` : 'var(--color-bg-tertiary)',
                  border: `1px solid ${isActive ? act.color : borderColor}`,
                  color: isActive ? act.color : 'var(--color-text-secondary)',
                }}
                title={act.description}
              >
                <Icon size={14} />
                {act.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex-1 flex min-h-0 p-5 gap-4">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>输入文本</span>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePaste}
                className="px-2 py-1 rounded text-xs transition-colors"
                style={{ color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)' }}
              >
                粘贴
              </button>
              <button
                onClick={() => { setInputText(''); setOutputText(''); }}
                className="px-2 py-1 rounded text-xs transition-colors"
                style={{ color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)' }}
              >
                清空
              </button>
            </div>
          </div>
          <textarea
            ref={inputRef}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="在此输入或粘贴需要处理的文本...&#10;&#10;支持：扩写、缩写、润色、翻译、降重"
            className="flex-1 w-full p-4 rounded-xl text-sm leading-relaxed resize-none outline-none theme-transition"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
              color: 'var(--color-text-primary)',
            }}
          />
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {inputText.length} 字符
            </span>
            <button
              onClick={handleProcess}
              disabled={isProcessing || !inputText.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-white text-sm font-medium transition-all disabled:opacity-50"
              style={{ backgroundColor: currentAction.color }}
            >
              {isProcessing ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  处理中...
                </>
              ) : (
                <>
                  {React.createElement(currentAction.icon, { size: 16 })}
                  {currentAction.label}
                </>
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center">
          <ArrowRight size={20} style={{ color: 'var(--color-text-muted)' }} />
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>输出结果</span>
            {outputText && !outputText.startsWith('❌') && (
              <div className="flex items-center gap-2">
                {wordCountBefore > 0 && (
                  <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    {wordCountBefore} → {wordCountAfter} 字
                  </span>
                )}
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                  style={{ color: copied ? '#10b981' : 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)' }}
                >
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? '已复制' : '复制'}
                </button>
                <button
                  onClick={handleUseAsInput}
                  className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                  style={{ color: 'var(--color-text-muted)', backgroundColor: 'var(--color-bg-tertiary)' }}
                >
                  <ArrowRight size={12} />
                  作为输入
                </button>
                <button
                  onClick={() => {
                    if (!outputText || outputText.startsWith('❌')) return;
                    const actionLabel = ACTIONS.find(a => a.id === action)?.label || '写作';
                    const md = `## ${actionLabel}结果\n\n### 原文\n\n${inputText}\n\n### ${actionLabel}后\n\n${outputText}\n`;
                    setPendingNoteContent(md);
                    if (!openPanels.includes('notes')) togglePanel('notes');
                  }}
                  className="flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors"
                  style={{ color: 'var(--accent)', backgroundColor: 'var(--color-bg-tertiary)' }}
                >
                  <PenTool size={12} />
                  发送到笔记
                </button>
              </div>
            )}
          </div>
          <div
            className="flex-1 w-full p-4 rounded-xl text-sm leading-relaxed overflow-auto theme-transition"
            style={{
              backgroundColor: cardBg,
              border: `1px solid ${borderColor}`,
              color: outputText.startsWith('❌') ? '#ef4444' : 'var(--color-text-primary)',
            }}
          >
            {outputText || (
              <span style={{ color: 'var(--color-text-muted)' }}>
                处理结果将显示在此处...
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
