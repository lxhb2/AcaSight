import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Loader2, Brain, FileText, CheckSquare, Square,
  Play, Pencil, Download, RotateCcw, ChevronRight, ChevronDown,
  Sparkles, BookOpen,
} from 'lucide-react';
import { papersApi, literatureReviewApi } from '@/services/api';
import type { PaperItem } from '@/services/api';

type Step = 'select' | 'outline' | 'writing' | 'complete';

interface OutlineSection {
  heading: string;
  paper_refs?: number[];
  subsections?: OutlineSection[];
}

export const LiteratureReviewView: React.FC = () => {
  const [papers, setPapers] = useState<PaperItem[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [topic, setTopic] = useState('');
  const [step, setStep] = useState<Step>('select');
  const [outline, setOutline] = useState<OutlineSection[]>([]);
  const [outlineRaw, setOutlineRaw] = useState('');
  const [editingOutline, setEditingOutline] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [progress, setProgress] = useState('');
  const [reviewContent, setReviewContent] = useState('');
  const [sections, setSections] = useState<Array<{ heading: string; content: string }>>([]);
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

  const handleGenerateOutline = useCallback(async () => {
    if (!topic.trim() || selectedIds.size === 0) return;
    setGenerating(true);
    setProgress('正在生成大纲...');
    try {
      const res = await literatureReviewApi.generateOutline(topic, Array.from(selectedIds));
      if (mountedRef.current) {
        const sections = (res.outline as { sections?: OutlineSection[] })?.sections || [];
        setOutline(sections);
        setOutlineRaw(JSON.stringify(sections, null, 2));
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
  }, [topic, selectedIds]);

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
  }, [topic, selectedIds]);

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
            <BookOpen size={14} style={{ color: 'var(--accent)' }} />
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>文献综述工作台</span>
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
      </div>
    </div>
  );
};
