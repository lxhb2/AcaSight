import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import {
  PenLine, FileText, Download,
  Loader2, Check, X, BookOpen,
  GraduationCap, Wand2, FileDown,
  Brain, Search, ListTree,
  Lightbulb, ArrowRight, Rocket, LucideIcon,
  Save,
} from 'lucide-react';

import { researchApi, workflowApi, pptApi, writingApi, citationApi, type ResearchDirection, type WritingFlowStatusType, type OutlineNode, type PaperOutline } from '@/services/api';
import { WritingInterruptDialog, detectInterruptPoint, type InterruptConfig, type InterruptResult } from './WritingInterruptDialog';
import { OutlineEditor } from './OutlineEditor';
import { useAutoSave } from '@/hooks/useAutoSave';
import { useWorkspaceStore } from '@/store/workspaceStore';

type WritingStep = 'topic' | 'outline' | 'draft' | 'polish' | 'export';

interface Literature {
  title: string;
  authors: string;
  year: string;
  abstract: string;
  doi: string;
  citations: number;
  journal: string;
  source: string;
  selected?: boolean;
}

const STEPS: { id: WritingStep; label: string; icon: LucideIcon }[] = [
  { id: 'topic', label: '选题与文献', icon: Lightbulb },
  { id: 'outline', label: '生成提纲', icon: ListTree },
  { id: 'draft', label: '撰写正文', icon: PenLine },
  { id: 'polish', label: '润色优化', icon: Wand2 },
  { id: 'export', label: '导出Word', icon: FileDown },
];

const PAPER_TYPES = ['课程论文', '本科毕业论文', '硕博毕业论文', '期刊论文'];

function useIsNarrow() {
  const [narrow, setNarrow] = useState(window.innerWidth < 768);
  useEffect(() => {
    const handler = () => setNarrow(window.innerWidth < 768);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);
  return narrow;
}
const WORD_COUNTS: Record<string, number> = {
  '课程论文': 5000,
  '本科毕业论文': 12000,
  '硕博毕业论文': 30000,
  '期刊论文': 8000,
};

// ─── Markdown 预览组件 ───

const MarkdownPreview: React.FC<{ content: string; onEdit: (v: string) => void }> = ({ content, onEdit }) => {
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <textarea
        value={content}
        onChange={e => onEdit(e.target.value)}
        placeholder="论文内容将在此显示..."
        style={{
          flex: 1,
          padding: 16,
          border: 'none',
          background: 'var(--bg-primary, #fff)',
          color: 'var(--ink, #1a1a2e)',
          fontSize: 14,
          lineHeight: 1.8,
          fontFamily: "'Noto Serif SC', serif",
          resize: 'none',
          outline: 'none',
        }}
      />
    </div>
  );
};

const findNodeByKey = (nodes: OutlineNode[], key: string): OutlineNode | null => {
  const parts = key.split('.').map(Number);
  let current: OutlineNode[] = nodes;
  let node: OutlineNode | null = null;
  for (const part of parts) {
    if (!current || part >= current.length) return null;
    node = current[part];
    current = node?.sections || [];
  }
  return node;
};

// ─── 主组件 ───

export const WritingWorkspace: React.FC = () => {
  const [step, setStep] = useState<WritingStep>('topic');
  const isNarrow = useIsNarrow();
  const [topic, setTopic] = useState('');
  const [subject, setSubject] = useState('');
  const [paperType, setPaperType] = useState('本科毕业论文');
  const [wordCount, setWordCount] = useState(12000);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // 文献
  const [searchQuery, setSearchQuery] = useState('');
  const [references, setReferences] = useState<Literature[]>([]);
  const [searching, setSearching] = useState(false);

  // 提纲
  const [outlineData, setOutlineData] = useState<PaperOutline | null>(null);

  // 正文 (按章节存储)
  const [sections, setSections] = useState<Record<string, string>>({});
  const [currentSectionIdx, setCurrentSectionIdx] = useState(0);
  const [activeSectionKey, setActiveSectionKey] = useState('');
  const [activeSectionTitle, setActiveSectionTitle] = useState('');

  // 润色
  const [polishMode, setPolishMode] = useState('polish');
  const [, setPolishResult] = useState('');

  // 模板
  const [templates, setTemplates] = useState<Array<{ id: string; name: string; font: string; body_size: number; line_spacing: number }>>([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [exportMeta, setExportMeta] = useState({ title: '', author: '', institution: '' });

  // Research & Workflow state (DEVLOG-018)
  const [researchDirections, setResearchDirections] = useState<ResearchDirection[]>([]);
  const [generatingDirections, setGeneratingDirections] = useState(false);
  const [showDirections, setShowDirections] = useState(false);
  const [workflowStatus, setWorkflowStatus] = useState<WritingFlowStatusType | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineLog, setPipelineLog] = useState<string[]>([]);
  const [workflowSessionId, setWorkflowSessionId] = useState('');

  // Interrupt dialog state
  const [showInterruptDialog, setShowInterruptDialog] = useState(false);
  const [interruptConfig, setInterruptConfig] = useState<InterruptConfig | null>(null);

  const [citationRecs, setCitationRecs] = useState<Record<string, Array<{ paper_id: number; title: string; dimension_key: string; matched_content: string; relevance_score: number; citation_format: string; }>> | null>(null);
  const [citationLoading, setCitationLoading] = useState(false);
  const [showCitationPanel, setShowCitationPanel] = useState(false);

  const sectionOrderRef = useRef<string[]>([]);
  const workflowStatusRef = useRef<WritingFlowStatusType | null>(null);
  useEffect(() => { workflowStatusRef.current = workflowStatus; }, [workflowStatus]);

  const setWritingDraft = useWorkspaceStore((s) => s.setWritingDraft);
  const syncToServer = useWorkspaceStore((s) => s.syncToServer);

  const autoSaveData = useMemo(() => ({
    sections,
    outlineData,
    topic,
    subject,
    paperType,
    wordCount,
    references,
    activeSectionKey,
  }), [sections, outlineData, topic, subject, paperType, wordCount, references, activeSectionKey]);

  const { lastSaved, isSaving, hasUnsavedChanges } = useAutoSave({
    data: autoSaveData,
    saveFn: useCallback((data: typeof autoSaveData) => {
      setWritingDraft('writing-workspace', JSON.stringify(data));
      return syncToServer();
    }, [setWritingDraft, syncToServer]),
    intervalMs: 30000,
    debounceMs: 3000,
    enabled: step !== 'topic',
  });

  // 加载模板列表
  useEffect(() => {
    writingApi.listTemplates()
      .then(d => setTemplates(d.templates || []))
      .catch(() => {});
  }, []);

  // 论文类型联动字数
  useEffect(() => {
    setWordCount(WORD_COUNTS[paperType] || 12000);
  }, [paperType]);

  // 构建完整 Markdown
  const fullMarkdown = useCallback(() => {
    if (!outlineData) return '';
    let md = `# ${outlineData.title}\n\n`;
    md += `**关键词**：${outlineData.keywords.join('、')}\n\n---\n\n`;
    const keys = sectionOrderRef.current;
    for (const key of keys) {
      const content = sections[key] || '';
      if (content) md += content + '\n\n';
    }
    return md.trim();
  }, [outlineData, sections]);

  // ─── Step 1: 文献搜索 ───
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const data = await writingApi.searchLiterature(searchQuery, 15);
      if (data.success) {
        setReferences(prev => [...prev, ...data.results.map((r: Literature) => ({ ...r, selected: false }))]);
      }
    } catch { setErrorMsg('搜索失败'); }
    setSearching(false);
  }, [searchQuery]);

  // ─── Step 1b: 研究方向生成 ───
  const handleGenerateDirections = useCallback(async () => {
    if (!topic.trim()) return;
    setGeneratingDirections(true); setErrorMsg('');
    try {
      const refs = references.filter(r => r.selected).map(r => ({ title: r.title, authors: r.authors, year: r.year }));
      const data = await researchApi.generateDirections({ topic, subject: subject || undefined, existing_literature: refs.length > 0 ? refs : undefined });
      if (data.success) {
        setResearchDirections(data.data.directions || []);
        setShowDirections(true);
      }
    } catch { setErrorMsg('研究方向生成失败'); }
    setGeneratingDirections(false);
  }, [topic, subject, references]);

  const selectDirection = useCallback((dir: ResearchDirection) => {
    setTopic(dir.title);
    setSubject(dir.related_fields?.[0] || subject);
    setShowDirections(false);
  }, [subject]);

  // ─── Workflow pipeline ───
  const handleRunPipeline = useCallback(async () => {
    if (!outlineData) return;
    setPipelineRunning(true); setPipelineLog([]);
    const sid = `${Date.now()}`;
    setWorkflowSessionId(sid);
    try {
      await workflowApi.createFlow({ session_id: sid, title: outlineData.title });
      setWorkflowStatus('outlining');
      setPipelineLog(l => [...l, '📝 工作流已创建...']);
      
      const result = await workflowApi.runPipeline(sid, outlineData.outline, outlineData.title);
      if (result.interrupted) {
        setWorkflowStatus('interrupted');
        setPipelineLog(l => [...l, `⏸ 章节 ${result.section_title} 需要确认素材来源`]);
      } else if (result.completed) {
        setWorkflowStatus('completed');
        setPipelineLog(l => [...l, '✅ 管道执行完毕']);
      }
    } catch (e: unknown) {
      setWorkflowStatus('failed');
      setPipelineLog(l => [...l, `❌ 管道失败: ${e instanceof Error ? e.message : String(e)}`]);
    }
    setPipelineRunning(false);
  }, [outlineData]);

  const handleResumePipeline = useCallback(async () => {
    setPipelineRunning(true);
    try {
      await workflowApi.resumeAgent('writing', { confirmed: true });
      setWorkflowStatus('confirmed');
      setPipelineLog(l => [...l, '▶ 已确认，继续执行']);
    } catch (e: unknown) {
      setPipelineLog(l => [...l, `❌ 恢复失败: ${e instanceof Error ? e.message : String(e)}`]);
    }
    setPipelineRunning(false);
  }, []);

  // ─── Interrupt dialog handlers ───
  const handleInterruptConfirm = useCallback((result: InterruptResult) => {
    setShowInterruptDialog(false);
    setWorkflowStatus('confirmed');
    setPipelineLog(l => [...l, `✅ 素材确认: ${result.mode}`]);
    if (workflowSessionId) {
      const materialType = result.mode === 'upload' ? 'upload' : result.mode === 'auto_generate' ? 'chart' : 'existing';
      writingApi.confirmInterrupt(workflowSessionId, {
        section_index: 0,
        material_type: materialType as 'upload' | 'chart' | 'existing',
        material_path: result.filePaths?.[0],
        chart_config: result.chartIds ? { chart_ids: result.chartIds } : undefined,
      }).catch(() => {});
    }
  }, [workflowSessionId]);

  const handleInterruptSkip = useCallback(() => {
    setShowInterruptDialog(false);
    setWorkflowStatus('confirmed');
    setPipelineLog(l => [...l, '⏭ 跳过素材确认']);
  }, []);

  const handleInterruptCancel = useCallback(() => {
    setShowInterruptDialog(false);
    setPipelineLog(l => [...l, '❌ 取消素材确认']);
  }, []);

  const handleMatchCitations = useCallback(async () => {
    if (!outlineData?.outline?.length) return;
    setCitationLoading(true);
    setCitationRecs(null);
    try {
      const outline = outlineData.outline.map((s: OutlineNode, i: number) => ({
        level: s.level,
        title: s.title || `第${i + 1}章`,
        description: s.description,
      }));
      const data = await citationApi.matchOutline({
        outline,
        reference_paper_ids: [],
        top_k_per_section: 3,
      });
      setCitationRecs(data.matches || {});
      setShowCitationPanel(true);
    } catch (e: unknown) {
      setErrorMsg('引用匹配失败: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setCitationLoading(false);
    }
  }, [outlineData]);

  // ─── Step 2: 生成提纲 (SSE 流式) ───
  const handleGenOutline = useCallback(async () => {
    if (!topic.trim()) return;
    setLoading(true); setErrorMsg('');
    try {
      const refs = references.filter(r => r.selected);
      const sessionId = `${Date.now()}`;
      const resp = await writingApi.streamOutline(sessionId, {
        topic, subject, paper_type: paperType, word_count: wordCount,
        references: refs,
      });
      if (!resp.ok || !resp.body) { throw new Error('SSE connection failed'); }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let outlineText = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (line.startsWith('data: ')) {
            const payload = line.slice(6).trim();
            if (payload === '[DONE]') break;
            try {
              const event = JSON.parse(payload);
              if (event.type === 'outline_delta') outlineText += event.content || '';
              if (event.type === 'outline_complete' && event.data) outlineText = event.data;
              if (event.type === 'interrupt') { setWorkflowStatus('interrupted'); }
            } catch {/* non-JSON chunk, append as text */ outlineText += payload; }
          }
        }
      }
      // Try to parse the outline as JSON, fall back to raw text
      try {
        const parsed = JSON.parse(outlineText);
        if (parsed.outline) {
          setOutlineData(parsed);
          const keys: string[] = [];
          const newSections: Record<string, string> = {};
          const walkOutline = (nodes: OutlineNode[], prefix: string) => {
            nodes.forEach((node, idx) => {
              const key = `${prefix}${idx}`;
              keys.push(key);
              const mdHead = '#'.repeat(node.level);
              newSections[key] = `${mdHead} ${node.title}\n\n`;
              if (node.sections) walkOutline(node.sections, key + '.');
            });
          };
          walkOutline(parsed.outline, '');
          sectionOrderRef.current = keys;
          setSections(prev => ({ ...prev, ...newSections }));
          if (keys.length > 0) {
            setActiveSectionKey(keys[0]);
            setActiveSectionTitle(parsed.outline[0]?.title || '');
            setCurrentSectionIdx(0);
          }
          setStep('outline');
        }
      } catch {
        // Fallback: try non-streaming endpoint
        const data = await writingApi.generateOutline({
          topic, subject, paper_type: paperType, word_count: wordCount, references: refs,
        });
        if (data.success && data.data.outline) {
          setOutlineData(data.data);
          const keys: string[] = [];
          const newSections: Record<string, string> = {};
          const walkOutline = (nodes: OutlineNode[], prefix: string) => {
            nodes.forEach((node, idx) => {
              const key = `${prefix}${idx}`;
              keys.push(key);
              const mdHead = '#'.repeat(node.level);
              newSections[key] = `${mdHead} ${node.title}\n\n`;
              if (node.sections) walkOutline(node.sections, key + '.');
            });
          };
          walkOutline(data.data.outline, '');
          sectionOrderRef.current = keys;
          setSections(prev => ({ ...prev, ...newSections }));
          if (keys.length > 0) {
            setActiveSectionKey(keys[0]);
            setActiveSectionTitle(data.data.outline[0]?.title || '');
            setCurrentSectionIdx(0);
          }
          setStep('outline');
        }
      }
    } catch (e: unknown) { setErrorMsg('提纲生成失败: ' + (e instanceof Error ? e.message : String(e))); }
    setLoading(false);
  }, [topic, subject, paperType, wordCount, references]);

  // ─── Step 3: 生成本章节 (SSE 流式 + 中断检测) ───
  const handleGenSection = useCallback(async (sectionKey: string, sectionTitle: string) => {
    if (!outlineData || !sectionKey) return;
    setLoading(true);
    try {
      const allOutline: OutlineNode[] = [];
      const walk = (nodes: OutlineNode[]) => { nodes.forEach(n => { allOutline.push(n); if (n.sections) walk(n.sections); }); };
      walk(outlineData.outline);
      const prevKeys = sectionOrderRef.current.slice(0, sectionOrderRef.current.indexOf(sectionKey));
      const prevContent = prevKeys.map(k => sections[k] || '').join('\n');
      const sessionId = `${Date.now()}`;
      let sectionContent = '';
      let interrupted = false;
      const node = findNodeByKey(outlineData.outline, sectionKey);
      const level = node?.level || 1;
      const mdHead = '#'.repeat(level);
      const headerPrefix = `${mdHead} ${sectionTitle}\n\n`;
      // Live-update helper: update section content in real-time (typewriter effect)
      const liveUpdate = (text: string) => {
        setSections(prev => ({ ...prev, [sectionKey]: headerPrefix + text }));
      };
      try {
        const resp = await writingApi.streamSection(sessionId, {
          topic: outlineData.title, outline: allOutline,
          section_index: sectionOrderRef.current.indexOf(sectionKey),
          previous_content: prevContent, word_count: 1200,
        });
        if (resp.ok && resp.body) {
          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split('\n')) {
              if (line.startsWith('data: ')) {
                const payload = line.slice(6).trim();
                if (payload === '[DONE]') break;
                try {
                  const event = JSON.parse(payload);
                  if (event.type === 'section_delta') { sectionContent += event.content || ''; liveUpdate(sectionContent); }
                  if (event.type === 'section_complete' && event.content) { sectionContent = event.content; liveUpdate(sectionContent); }
                  if (event.type === 'interrupt') {
                    interrupted = true;
                    setWorkflowStatus('interrupted');
                    setInterruptConfig({ sectionTitle, sectionType: event.section_type || 'data', description: event.reason || '需要素材确认' });
                    setShowInterruptDialog(true);
                  }
                } catch {/* raw text */ sectionContent += payload; liveUpdate(sectionContent); }
              }
            }
          }
        } else { throw new Error('SSE failed'); }
      } catch {
        // Fallback to non-streaming
        const data = await writingApi.generateSection({
          topic: outlineData.title, outline: allOutline, current_section: { title: sectionTitle }, previous_content: prevContent, word_count: 1200,
        });
        if (data.success && data.content) { sectionContent = data.content; liveUpdate(sectionContent); }
        // Check if this section needs interrupt
        const ic = detectInterruptPoint(sectionTitle, sectionContent);
        if (ic) { interrupted = true; setInterruptConfig(ic); setShowInterruptDialog(true); }
      }
      if (sectionContent && !interrupted) {
        // Auto-advance to next section
        const idx = sectionOrderRef.current.indexOf(sectionKey);
        const nextKey = sectionOrderRef.current[idx + 1];
        if (nextKey) { setActiveSectionKey(nextKey); setActiveSectionTitle(findNodeByKey(outlineData.outline, nextKey)?.title || ''); setCurrentSectionIdx(idx + 1); }
        else { setStep('polish'); /* All sections done → auto-advance to polish */ }
      }
    } catch { setErrorMsg('章节生成失败'); }
    setLoading(false);
  }, [outlineData, sections]);

  // ─── Step 3.5: 一键全写 ───
  const [writingAll, setWritingAll] = useState(false);
  const [writtenCount, setWrittenCount] = useState(0);

  const handleWriteAll = useCallback(async () => {
    if (!outlineData) return;
    setWritingAll(true); setWrittenCount(0);
    const keys = sectionOrderRef.current;
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i];
      const node = findNodeByKey(outlineData.outline, key);
      if (!node) continue;
      if ((sections[key]?.length || 0) > 50) { setWrittenCount(c => c + 1); continue; }
      setActiveSectionKey(key);
      setActiveSectionTitle(node.title);
      setCurrentSectionIdx(i);
      await handleGenSection(key, node.title);
      setWrittenCount(c => c + 1);
      if (workflowStatusRef.current === 'interrupted') break;
    }
    setWritingAll(false);
    if (workflowStatusRef.current !== 'interrupted') setStep('polish');
  }, [outlineData, sections, sectionOrderRef, handleGenSection]);

  // ─── Step 4: 润色 ───
  const handlePolish = useCallback(async () => {
    const content = sections[activeSectionKey] || '';
    if (!content.trim()) return;
    setLoading(true); setPolishResult('');
    try {
      const data = await writingApi.polish(content, polishMode);
      if (data.success) {
        setPolishResult(data.content);
        setSections(prev => ({ ...prev, [activeSectionKey]: data.content }));
      }
    } catch { setErrorMsg('润色失败'); }
    setLoading(false);
  }, [activeSectionKey, sections, polishMode]);

  // ─── Step 5: Word 导出 ───
  const handleExport = useCallback(async () => {
    const md = fullMarkdown();
    if (!md.trim()) return;
    setLoading(true);
    try {
      const resp = await writingApi.exportWordFile({
        content: md,
        template_id: selectedTemplate,
        title: exportMeta.title || outlineData?.title || '论文',
        author: exportMeta.author,
        institution: exportMeta.institution,
      });
      if (!resp.ok) throw new Error('Export failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(exportMeta.title || outlineData?.title || '论文').replace(/[\/\\]/g, '_')}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { setErrorMsg('导出失败'); }
    setLoading(false);
  }, [fullMarkdown, selectedTemplate, exportMeta, outlineData]);

  // PPT state
  const [generatingPpt, setGeneratingPpt] = useState(false);

  const handleExportPpt = useCallback(async () => {
    if (!outlineData) return;
    setGeneratingPpt(true); setErrorMsg('');
    try {
      const result = await pptApi.generate({
        title: exportMeta.title || outlineData.title,
        subject: subject || undefined,
        outline: outlineData.outline.map(n => ({ title: n.title, description: n.description })),
        content: fullMarkdown(),
      });
      if (result.success) {
        if (result.data.filename) {
          const resp = await writingApi.downloadPpt(result.data.path || '');
          if (resp.ok) {
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = result.data.filename; a.click();
            URL.revokeObjectURL(url);
          }
        }
        setErrorMsg('');
      }
    } catch (e: unknown) { setErrorMsg('PPT生成失败: ' + (e instanceof Error ? e.message : String(e))); }
    setGeneratingPpt(false);
  }, [outlineData, exportMeta, subject, fullMarkdown]);

  const stepIdx = STEPS.findIndex(s => s.id === step);

  return (
    <div style={{ display: 'flex', flexDirection: isNarrow ? 'column' : 'row', height: '100%', background: 'var(--bg-primary, #fff)', color: 'var(--ink, #1a1a2e)' }}>
      {/* ===== Left Sidebar ===== */}
      {!isNarrow && (
      <div style={{ width: 220, borderRight: '1px solid var(--border-color, #e2e8f0)', display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
        {/* Steps */}
        <div style={{ padding: '12px 12px 8px', borderBottom: '1px solid var(--border-color, #e2e8f0)' }}>
          <div role="tablist" style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted, #888)', textTransform: 'uppercase', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
            <GraduationCap size={12} /> 写作流程
          </div>
          {STEPS.map((s, i) => (
            <div key={s.id}
              onClick={() => setStep(s.id)}
              role="tab"
              aria-label={s.label}
              aria-current={step === s.id ? 'step' : undefined}
              style={{
                padding: '6px 10px', marginBottom: 2, borderRadius: 6, cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 8,
                background: step === s.id ? 'var(--accent, #6366f1)' : 'transparent',
                color: step === s.id ? '#fff' : (i < stepIdx ? 'var(--success, #10b981)' : 'var(--ink, #1a1a2e)'),
                fontSize: 12, fontWeight: step === s.id ? 600 : 400,
                transition: 'all 0.15s',
              }}
            >
              <s.icon size={14} />
              <span style={{ flex: 1 }}>{s.label}</span>
              {i < stepIdx && <Check size={12} />}
            </div>
          ))}
          {step !== 'topic' && (
            <div style={{ marginTop: 8, padding: '4px 10px', fontSize: 10, color: 'var(--mute)', display: 'flex', alignItems: 'center', gap: 4 }}>
              {isSaving ? <><Loader2 size={10} className="animate-spin" /> 保存中...</> :
               hasUnsavedChanges ? <><Save size={10} /> 未保存</> :
               lastSaved ? <><Check size={10} style={{ color: '#10b981' }} /> {new Date(lastSaved).toLocaleTimeString()}</> : null}
            </div>
          )}        </div>

        {/* Outline navigation */}
        {outlineData && (step === 'draft' || step === 'polish') && (
          <div style={{ flex: 1, overflow: 'auto', padding: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--muted, #888)', marginBottom: 6, paddingLeft: 4 }}>
              章节导航
            </div>
            {sectionOrderRef.current.map((key, idx) => {
              const node = findNodeByKey(outlineData.outline, key);
              const isActive = activeSectionKey === key;
              const hasContent = (sections[key]?.length || 0) > 20;
              return (
                <div key={key}
                  onClick={() => { setActiveSectionKey(key); setActiveSectionTitle(node?.title || ''); setCurrentSectionIdx(idx); }}
                  style={{
                    padding: '4px 8px', marginBottom: 1, borderRadius: 4, cursor: 'pointer',
                    fontSize: 11, marginLeft: (node?.level || 1) > 1 ? 16 : 0,
                    background: isActive ? 'var(--accent-bg, rgba(99,102,241,0.1))' : 'transparent',
                    color: isActive ? 'var(--accent, #6366f1)' : (hasContent ? 'var(--ink, #1a1a2e)' : 'var(--muted, #888)'),
                    fontWeight: isActive ? 600 : 400,
                    borderLeft: isActive ? '2px solid var(--accent, #6366f1)' : '2px solid transparent',
                  }}
                >
                  {hasContent && <span style={{ marginRight: 4 }}>✓</span>}
                  {node?.title || key}
                </div>
              );
            })}
          </div>
        )}

        {/* References count */}
        {step === 'topic' && (
          <div style={{ padding: 8, borderTop: '1px solid var(--border-color)', fontSize: 11, color: 'var(--muted)' }}>
            已选文献: {references.filter(r => r.selected).length} 篇
          </div>
        )}
      </div>
      )}
      {isNarrow && (
      <div role="tablist" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 8px', borderBottom: '1px solid var(--border-color, #e2e8f0)', overflowX: 'auto', flexShrink: 0 }}>
        {STEPS.map((s, i) => (
          <div key={s.id}
            onClick={() => setStep(s.id)}
            role="tab"
            aria-label={s.label}
            aria-current={step === s.id ? 'step' : undefined}
            style={{
              padding: '4px 8px', borderRadius: 4, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 4,
              background: step === s.id ? 'var(--accent, #6366f1)' : 'transparent',
              color: step === s.id ? '#fff' : (i < stepIdx ? 'var(--success, #10b981)' : 'var(--ink, #1a1a2e)'),
              fontSize: 11, fontWeight: step === s.id ? 600 : 400,
              whiteSpace: 'nowrap',
            }}
          >
            <s.icon size={12} />
            {i < stepIdx && <Check size={10} />}
          </div>
        ))}
      </div>
      )}

      {/* ===== Main Area ===== */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, width: isNarrow ? '100%' : undefined }}>
        {/* Step 1: Topic & Literature */}
        {step === 'topic' && (
          <div style={{ padding: isNarrow ? 12 : 24, overflow: 'auto', height: '100%' }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Lightbulb size={20} color="var(--accent, #6366f1)" /> 选题与文献收集
            </h2>

            {/* Topic input */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>论文主题 *</label>
              <textarea value={topic} onChange={e => setTopic(e.target.value)}
                placeholder="例：基于深度学习的XRD物相自动识别方法研究"
                style={{ width: '100%', height: 60, marginTop: 4, padding: '8px 12px', borderRadius: 8,
                  border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)',
                  color: 'var(--ink)', fontSize: 14, resize: 'none', outline: 'none' }} />
            </div>

            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: isNarrow ? 'wrap' : 'nowrap' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>学科方向</label>
                <input value={subject} onChange={e => setSubject(e.target.value)}
                  placeholder="材料科学 / 计算机科学"
                  style={{ width: '100%', marginTop: 4, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)',
                    color: 'var(--ink)', fontSize: 13, outline: 'none' }} />
              </div>
              <div style={{ width: 160 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>论文类型</label>
                <select value={paperType} onChange={e => setPaperType(e.target.value)}
                  style={{ width: '100%', marginTop: 4, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)',
                    color: 'var(--ink)', fontSize: 13, outline: 'none' }}>
                  {PAPER_TYPES.map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
              <div style={{ width: 120 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>目标字数</label>
                <input type="number" value={wordCount} onChange={e => setWordCount(Number(e.target.value))}
                  style={{ width: '100%', marginTop: 4, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)',
                    color: 'var(--ink)', fontSize: 13, outline: 'none' }} />
              </div>
            </div>

            {/* Literature search */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Search size={12} /> 文献检索（Semantic Scholar + CrossRef）
              </label>
              <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSearch()}
                  placeholder="输入关键词检索相关文献..."
                  style={{ flex: 1, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)',
                    color: 'var(--ink)', fontSize: 13, outline: 'none' }} />
                <button onClick={handleSearch} disabled={searching || !searchQuery.trim()}
                  style={{ padding: '6px 16px', borderRadius: 6, border: 'none',
                    background: searching ? 'var(--muted, #ccc)' : 'var(--accent, #6366f1)',
                    color: '#fff', cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 4 }}>
                  {searching ? <Loader2 size={14} className="spin" /> : <Search size={14} />}
                  {searching ? '搜索中...' : '检索'}
                </button>
              </div>
            </div>

            {/* Reference list */}
            {references.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', marginBottom: 8 }}>
                  检索结果 ({references.length} 篇，勾选作为参考文献)
                </div>
                <div style={{ maxHeight: 300, overflow: 'auto', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                  {references.map((ref, i) => (
                    <div key={i} style={{
                      padding: '8px 12px', borderBottom: '1px solid var(--border-color)',
                      display: 'flex', gap: 8, alignItems: 'flex-start',
                      background: ref.selected ? 'rgba(99,102,241,0.05)' : 'transparent',
                    }}>
                      <input type="checkbox" checked={ref.selected || false}
                        onChange={() => setReferences(prev => prev.map((r, j) => j === i ? { ...r, selected: !r.selected } : r))}
                        style={{ marginTop: 2 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>{ref.title}</div>
                        <div style={{ fontSize: 11, color: 'var(--muted)' }}>
                          {ref.authors} ({ref.year}) {ref.journal && `· ${ref.journal}`}
                          {ref.citations > 0 && <span style={{ marginLeft: 8, color: '#f59e0b' }}>被引 {ref.citations}</span>}
                          <span style={{ marginLeft: 8, color: 'var(--accent)', fontSize: 10 }}>{ref.source}</span>
                        </div>
                        {ref.abstract && (
                          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2, overflow: 'hidden',
                            textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' }}>
                            {ref.abstract.slice(0, 200)}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Error */}
            {errorMsg && <div style={{ color: 'var(--danger, #ef4444)', fontSize: 12, marginBottom: 12 }}>{errorMsg}</div>}

            {/* Research direction generation */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              <button onClick={handleGenerateDirections} disabled={generatingDirections || !topic.trim()}
                style={{
                  padding: '7px 16px', borderRadius: 6, border: '1px solid var(--accent, #6366f1)',
                  background: 'transparent', color: 'var(--accent, #6366f1)',
                  cursor: 'pointer', fontSize: 13, display: 'flex', alignItems: 'center', gap: 5,
                }}>
                {generatingDirections ? <Loader2 size={14} className="spin" /> : <Rocket size={14} />}
                {generatingDirections ? '生成中...' : '研究方向探索'}
              </button>
            </div>

            {/* Research directions panel */}
            {showDirections && researchDirections.length > 0 && (
              <div style={{ marginBottom: 16, padding: 12, borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)' }}>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Brain size={14} color="var(--accent)" /> AI 推荐研究方向 ({researchDirections.length})
                  <button onClick={() => setShowDirections(false)} style={{ marginLeft: 'auto', padding: '2px 6px', fontSize: 10, borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--muted)', cursor: 'pointer' }}>收起</button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {researchDirections.map((dir, i) => (
                    <div key={i} style={{ padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-primary, #fff)', cursor: 'pointer', transition: 'border-color 0.15s' }}
                      onClick={() => selectDirection(dir)}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-color)'; }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>{dir.title}</span>
                        <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: dir.difficulty === '高' ? '#fef2f2' : dir.difficulty === '中' ? '#fffbeb' : '#f0fdf4', color: dir.difficulty === '高' ? '#ef4444' : dir.difficulty === '中' ? '#f59e0b' : '#10b981' }}>
                          {dir.difficulty}难度
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{dir.description}</div>
                      <div style={{ display: 'flex', gap: 12, marginTop: 4, fontSize: 10, color: 'var(--accent)' }}>
                        <span>✨ {dir.novelty}</span>
                        <span>🔑 {dir.key_questions?.[0] || ''}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Next button */}
            <button onClick={handleGenOutline} disabled={loading || !topic.trim()}
              style={{
                padding: '10px 24px', borderRadius: 8, border: 'none',
                background: loading || !topic.trim() ? 'var(--muted, #ccc)' : 'var(--accent, #6366f1)',
                color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600,
                display: 'flex', alignItems: 'center', gap: 8, marginLeft: 'auto',
              }}>
              {loading ? <><Loader2 size={16} className="spin" /> 生成中...</> : <>生成提纲 <ArrowRight size={16} /></>}
            </button>
          </div>
        )}

        {/* Step 2: Outline */}
        {step === 'outline' && outlineData && (
          <div style={{ padding: isNarrow ? 12 : 24, overflow: 'auto', height: '100%' }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
              <ListTree size={20} color="var(--accent, #6366f1)" /> 论文提纲
            </h2>

            {/* Workflow pipeline bar */}
            {workflowStatus ? (
              <div style={{ marginBottom: 12, padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-secondary, #f8fafc)', display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink)' }}>工作流:</span>
                <span style={{ padding: '2px 8px', borderRadius: 4, fontSize: 10, fontWeight: 600, background: workflowStatus === 'completed' ? '#dcfce7' : workflowStatus === 'interrupted' ? '#fef3c7' : workflowStatus === 'failed' ? '#fee2e2' : '#ede9fe', color: workflowStatus === 'completed' ? '#16a34a' : workflowStatus === 'interrupted' ? '#d97706' : workflowStatus === 'failed' ? '#dc2626' : '#7c3aed' }}>{workflowStatus}</span>
                {pipelineRunning && <Loader2 size={12} className="spin" style={{ color: 'var(--accent)' }} />}
                {pipelineLog.length > 0 && <span style={{ fontSize: 10, color: 'var(--muted)' }}>{pipelineLog[pipelineLog.length - 1]}</span>}
                {workflowStatus === 'interrupted' && (
                  <button onClick={handleResumePipeline} disabled={pipelineRunning} style={{ marginLeft: 'auto', padding: '4px 12px', borderRadius: 6, border: 'none', background: '#f59e0b', color: '#fff', cursor: 'pointer', fontSize: 11 }}>确认恢复</button>
                )}
              </div>
            ) : (
              <div style={{ marginBottom: 12 }}>
                <button onClick={handleRunPipeline} disabled={pipelineRunning} style={{ padding: '6px 14px', borderRadius: 6, border: '1px dashed var(--accent)', background: 'rgba(99,102,241,0.08)', color: 'var(--accent)', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 5 }}>
                  <Rocket size={13} /> 启动写作管道
                </button>
              </div>
            )}
            <div style={{ fontSize: 14, color: 'var(--muted)', marginBottom: 4 }}>
              目标字数: ~{outlineData.estimated_total_words} 字 · 关键词: {outlineData.keywords.join('、')}
            </div>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, color: 'var(--accent)' }}>
              {outlineData.title}
            </div>

            {/* Outline Editor */}
            <OutlineEditor
              outline={outlineData.outline}
              onChange={(newOutline) => setOutlineData(prev => prev ? { ...prev, outline: newOutline } : prev)}
              onConfirm={() => setStep('draft')}
              title={outlineData.title}
            />

            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
              <button onClick={() => setStep('topic')}
                style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--border-color)',
                  background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 13 }}>
                返回修改
              </button>
            </div>
          </div>
        )}

        {/* Step 3 & 4: Draft + Polish */}
        {(step === 'draft' || step === 'polish') && (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {/* Toolbar */}
            <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)' }}>{activeSectionTitle}</span>
              <div style={{ flex: 1 }} />

              {step === 'draft' && (
                <>
                  <button onClick={handleWriteAll}
                    disabled={loading || writingAll}
                    style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid var(--accent)',
                      background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 12,
                      display: 'flex', alignItems: 'center', gap: 4 }}>
                    {writingAll ? <><Loader2 size={12} className="spin" /> 全写中 {writtenCount}/{sectionOrderRef.current.length}</> : <><Rocket size={12} /> 一键全写</>}
                  </button>
                  <button onClick={() => handleGenSection(activeSectionKey, activeSectionTitle)}
                    disabled={loading || writingAll}
                    style={{ padding: '4px 12px', borderRadius: 6, border: 'none',
                      background: (loading || writingAll) ? 'var(--muted)' : 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 12,
                      display: 'flex', alignItems: 'center', gap: 4 }}>
                    {loading ? <Loader2 size={12} className="spin" /> : <Brain size={12} />}
                    AI 生成本节
                  </button>
                </>
              )}

              {step === 'polish' && (
                <>
                  <select value={polishMode} onChange={e => setPolishMode(e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid var(--border-color)',
                      background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 12, outline: 'none' }}>
                    <option value="polish">学术润色</option>
                    <option value="academic">正式改写</option>
                    <option value="shorten">精简压缩</option>
                    <option value="expand">扩写补充</option>
                    <option value="paraphrase">降重改写</option>
                  </select>
                  <button onClick={handlePolish} disabled={loading}
                    style={{ padding: '4px 12px', borderRadius: 6, border: 'none',
                      background: loading ? 'var(--muted)' : '#f59e0b', color: '#fff', cursor: 'pointer', fontSize: 12,
                      display: 'flex', alignItems: 'center', gap: 4 }}>
                    {loading ? <Loader2 size={12} className="spin" /> : <Wand2 size={12} />}
                    应用润色
                  </button>
                </>
              )}

              {/* Navigation */}
              <button onClick={() => {
                const prev = currentSectionIdx - 1;
                if (prev >= 0) {
                  const key = sectionOrderRef.current[prev];
                  const node = findNodeByKey(outlineData!.outline, key);
                  setActiveSectionKey(key); setActiveSectionTitle(node?.title || ''); setCurrentSectionIdx(prev);
                }
              }} disabled={currentSectionIdx === 0} style={{ padding: '4px 8px', borderRadius: 4, border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--ink)' }}>◀</button>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>{currentSectionIdx + 1} / {sectionOrderRef.current.length}</span>
              <button onClick={() => {
                const next = currentSectionIdx + 1;
                if (next < sectionOrderRef.current.length) {
                  const key = sectionOrderRef.current[next];
                  const node = findNodeByKey(outlineData!.outline, key);
                  setActiveSectionKey(key); setActiveSectionTitle(node?.title || ''); setCurrentSectionIdx(next);
                }
              }} disabled={currentSectionIdx >= sectionOrderRef.current.length - 1} style={{ padding: '4px 8px', borderRadius: 4, border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--ink)' }}>▶</button>

              <button
                onClick={handleMatchCitations}
                disabled={citationLoading || !outlineData?.outline?.length}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', borderRadius: 4,
                  border: '1px solid var(--hairline)', background: 'transparent',
                  color: citationLoading ? 'var(--mute)' : '#6366f1',
                  cursor: citationLoading || !outlineData?.outline?.length ? 'not-allowed' : 'pointer',
                  fontSize: 11, opacity: citationLoading || !outlineData?.outline?.length ? 0.5 : 1,
                }}
              >
                {citationLoading ? <Loader2 size={12} className="animate-spin" /> : <BookOpen size={12} />}
                引用推荐
              </button>

              <button onClick={() => setStep(step === 'draft' ? 'polish' : 'export')}
                style={{ padding: '4px 12px', borderRadius: 6, border: 'none',
                  background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 12, marginLeft: 8 }}>
                {step === 'draft' ? '下一步：润色' : '下一步：导出'} →
              </button>
            </div>

            {/* Editor */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <MarkdownPreview
                content={sections[activeSectionKey] || ''}
                onEdit={v => setSections(prev => ({ ...prev, [activeSectionKey]: v }))}
              />
            </div>

            {/* Word count bar */}
            <div style={{ padding: '4px 16px', borderTop: '1px solid var(--border-color)', fontSize: 11, color: 'var(--muted)',
              display: 'flex', justifyContent: 'space-between' }}>
              <span>本节字数: {(sections[activeSectionKey] || '').length}</span>
              <span>总字数: {Object.values(sections).join('').length}</span>
              {errorMsg && <span style={{ color: 'var(--danger)' }}>{errorMsg}</span>}
            </div>
          </div>
        )}

        {/* Step 5: Export */}
        {step === 'export' && (
          <div style={{ padding: isNarrow ? 12 : 24, overflow: 'auto', height: '100%' }}>
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <FileDown size={20} color="var(--accent, #6366f1)" /> 导出 Word 文档
            </h2>

            {/* Meta info */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: isNarrow ? 'wrap' : 'nowrap' }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>论文标题</label>
                <input value={exportMeta.title} onChange={e => setExportMeta(p => ({ ...p, title: e.target.value }))}
                  placeholder={outlineData?.title || ''}
                  style={{ width: '100%', marginTop: 4, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 13, outline: 'none' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>作者</label>
                <input value={exportMeta.author} onChange={e => setExportMeta(p => ({ ...p, author: e.target.value }))}
                  placeholder="张三"
                  style={{ width: '100%', marginTop: 4, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 13, outline: 'none' }} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)' }}>单位</label>
                <input value={exportMeta.institution} onChange={e => setExportMeta(p => ({ ...p, institution: e.target.value }))}
                  placeholder="XX大学"
                  style={{ width: '100%', marginTop: 4, padding: '6px 12px', borderRadius: 6,
                    border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 13, outline: 'none' }} />
              </div>
            </div>

            {/* Template selection */}
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <FileText size={12} /> 选择排版模板
              </label>
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {templates.map(t => (
                  <div key={t.id}
                    onClick={() => setSelectedTemplate(t.id)}
                    style={{
                      padding: '12px 16px', borderRadius: 8, cursor: 'pointer',
                      border: `2px solid ${selectedTemplate === t.id ? 'var(--accent, #6366f1)' : 'var(--border-color)'}`,
                      background: selectedTemplate === t.id ? 'var(--accent-bg, rgba(99,102,241,0.08)' : 'var(--bg-secondary, #f8fafc)',
                      minWidth: 160, textAlign: 'center',
                    }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{t.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{t.font} · {t.body_size}pt</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Preview stats */}
            <div style={{ padding: 16, background: 'var(--bg-secondary, #f8fafc)', borderRadius: 8, marginBottom: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>文档预览</div>
              <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                标题: {outlineData?.title || '未设置'} · 总字数: {fullMarkdown().length} · 
                章节完成: {sectionOrderRef.current.filter(k => (sections[k]?.length || 0) > 20).length}/{sectionOrderRef.current.length}
              </div>
            </div>

            {errorMsg && <div style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 12 }}>{errorMsg}</div>}

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button onClick={() => setStep('polish')}
                style={{ padding: '8px 20px', borderRadius: 8, border: '1px solid var(--border-color)',
                  background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 13 }}>
                ← 返回润色
              </button>
              <button onClick={handleExport} disabled={loading || !selectedTemplate}
                style={{ padding: '10px 28px', borderRadius: 8, border: 'none',
                  background: loading || !selectedTemplate ? 'var(--muted)' : 'var(--accent, #6366f1)',
                  color: '#fff', cursor: 'pointer', fontSize: 14, fontWeight: 600,
                  display: 'flex', alignItems: 'center', gap: 8 }}>
                {loading ? <><Loader2 size={16} className="spin" /> 生成中...</> : <><Download size={16} /> 导出 Word</>}
              </button>
              <button onClick={handleExportPpt} disabled={generatingPpt || !outlineData}
                style={{ padding: '10px 28px', borderRadius: 8, border: '1px solid var(--accent, #6366f1)',
                  background: 'transparent', color: 'var(--accent, #6366f1)', cursor: 'pointer', fontSize: 14, fontWeight: 600,
                  display: 'flex', alignItems: 'center', gap: 8 }}>
                {generatingPpt ? <><Loader2 size={16} className="spin" /> PPT生成中...</> : <><GraduationCap size={16} /> 生成 PPT</>}
              </button>
            </div>
          </div>
        )}
      </div>

      {showCitationPanel && (
        <div style={{
          position: isNarrow ? 'fixed' : 'absolute', right: 0, top: isNarrow ? 'auto' : 0, bottom: 0, width: isNarrow ? '100%' : 320, height: isNarrow ? '50vh' : 'auto',
          background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))',
          WebkitBackdropFilter: 'blur(var(--glass-blur))',
          borderLeft: '1px solid var(--hairline)',
          zIndex: 30, overflowY: 'auto', display: 'flex', flexDirection: 'column',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid var(--hairline)' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>引用推荐</span>
            <button onClick={() => setShowCitationPanel(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', padding: 0 }}>
              <X size={14} />
            </button>
          </div>
          {citationRecs === null ? (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--mute)', fontSize: 12 }}>
              {citationLoading ? '正在匹配引用...' : '暂无推荐'}
            </div>
          ) : (
            <div style={{ padding: '8px 12px', flex: 1, overflowY: 'auto' }}>
              {Object.entries(citationRecs).map(([sectionTitle, matches], si) => (
                <div key={si} style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--ink)', marginBottom: 4, padding: '2px 6px', background: 'var(--canvas-soft)', borderRadius: 3 }}>
                    {sectionTitle}
                  </div>
                  {matches.map((match, mi) => (
                    <div key={mi} style={{ padding: '4px 8px', marginBottom: 3, borderRadius: 4, border: '1px solid var(--hairline)', fontSize: 10 }}>
                      <div style={{ fontWeight: 500, color: 'var(--body)', marginBottom: 2, lineHeight: 1.3 }}>{match.title}</div>
                      <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', marginBottom: 2 }}>
                        <span style={{ fontSize: 8, padding: '0 4px', borderRadius: 2, background: 'rgba(99,102,241,0.1)', color: '#6366f1' }}>{match.dimension_key}</span>
                      </div>
                      <div style={{ fontSize: 9, color: 'var(--accent)', fontFamily: 'monospace', lineHeight: 1.4, wordBreak: 'break-all' }}>
                        {match.citation_format}
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Interrupt Dialog Overlay */}
      {showInterruptDialog && interruptConfig && (
        <WritingInterruptDialog
          config={interruptConfig}
          existingCharts={[]}
          onLoadExistingCharts={() => {}}
          onConfirm={handleInterruptConfirm}
          onSkip={handleInterruptSkip}
          onCancel={handleInterruptCancel}
        />
      )}
    </div>
  );
};
