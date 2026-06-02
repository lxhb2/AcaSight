/**
 * AgentPanel — 学术 Agent 全量交互面板 (Cherry Studio 风格重写)
 *
 * 设计灵感: Cherry Studio + uiverse.io 组件
 * - 左侧会话列表 + 右侧聊天区
 * - 输入框底部胶囊式
 * - 渐变发光按钮 + 玻璃气泡
 * - 技能标签卡片
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Bot, Send, Sparkles, BookOpen, Search, PenTool, Languages,
  BarChart3, FileText, ChevronDown, ChevronRight, Play,
  Loader2, CheckCircle2, AlertCircle, Zap, Trash2,
  Plus, MessageSquare, PanelLeftClose, PanelLeft,
  Settings2, Library, Boxes,
} from 'lucide-react';
import { MarkdownRenderer } from '@/components/Common/MarkdownRenderer';
import { useAgentStore, type AgentStep, type AgentMessage, type SessionInfo } from '@/store/agentStore';
import { moduleApi, agentApi, ragApi, type ModuleStatus as ModuleStatusType } from '@/services/api';

const categoryIcons: Record<string, React.ReactNode> = {
  reading: <BookOpen size={13} />,
  writing: <PenTool size={13} />,
  translation: <Languages size={13} />,
  search: <Search size={13} />,
  figure: <BarChart3 size={13} />,
  citation: <FileText size={13} />,
  literature: <BookOpen size={13} />,
  analysis: <Zap size={13} />,
  formatting: <FileText size={13} />,
  response: <Send size={13} />,
  data: <BarChart3 size={13} />,
  paper2ppt: <FileText size={13} />,
};

const categoryColors: Record<string, string> = {
  reading: '#6366f1',
  writing: '#f59e0b',
  translation: '#3b82f6',
  search: '#10b981',
  figure: '#ec4899',
  citation: '#8b5cf6',
  literature: '#6366f1',
  analysis: '#ef4444',
  formatting: '#8b5cf6',
  response: '#06b6d4',
  data: '#f97316',
  paper2ppt: '#14b8a6',
};

const quickTasks = [
  { label: '论文问答', prompt: '请帮我分析这篇论文的研究方法和主要发现', icon: <BookOpen size={14} />, gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
  { label: '生成摘要', prompt: '请为这篇论文生成中文摘要', icon: <FileText size={14} />, gradient: 'linear-gradient(135deg, #06b6d4, #3b82f6)' },
  { label: '润色文本', prompt: '请润色以下文本，改为Nature期刊风格', icon: <Sparkles size={14} />, gradient: 'linear-gradient(135deg, #f59e0b, #f97316)' },
  { label: '学术翻译', prompt: '请将以下中文翻译为学术英语', icon: <Languages size={14} />, gradient: 'linear-gradient(135deg, #10b981, #06b6d4)' },
  { label: '生成图表', prompt: '请生成一个Nature风格的柱状图代码', icon: <BarChart3 size={14} />, gradient: 'linear-gradient(135deg, #ec4899, #8b5cf6)' },
  { label: '审稿回复', prompt: '请帮我起草审稿意见的逐条回复', icon: <Send size={14} />, gradient: 'linear-gradient(135deg, #ef4444, #f97316)' },
];

interface SkillInfo {
  name: string;
  description: string;
  category: string;
  examples?: string[];
}

// Module metadata
const moduleIcons: Record<string, React.ReactNode> = {
  knowledge: <BookOpen size={14} />,
  writing: <PenTool size={14} />,
  output: <FileText size={14} />,
  chart: <BarChart3 size={14} />,
  storage: <Boxes size={14} />,
};
const moduleColors: Record<string, string> = {
  knowledge: '#6366f1',
  writing: '#f59e0b',
  output: '#06b6d4',
  chart: '#ec4899',
  storage: '#10b981',
};
const moduleLabels: Record<string, string> = {
  knowledge: '知识',
  writing: '创作',
  output: '输出',
  chart: '绘图',
  storage: '存储',
};

interface AgentPanelProps {
  pdfId?: string;
  pdfTitle?: string;
  selectedText?: string;
  pdfText?: string;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({ pdfId, pdfTitle, selectedText, pdfText }) => {
  const [input, setInput] = useState('');
  const [showSkills, setShowSkills] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [ragMode, setRagMode] = useState(false);
  const [ragAvailable, setRagAvailable] = useState(false);
  const [ragDatasets, setRagDatasets] = useState<Array<{ id: string; name: string }>>([]);
  const [showModules, setShowModules] = useState(false);
  const [modules, setModules] = useState<ModuleStatusType[]>([]);
  const [modulesLoading, setModulesLoading] = useState(false);
  const [executingModule, setExecutingModule] = useState<string | null>(null);
  const [moduleTaskInput, setModuleTaskInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages, isRunning, sendTask, setContext, clearMessages,
    conversationId, sessions, sessionsLoading,
    loadSessions, switchSession, deleteSession, newSession,
  } = useAgentStore();

  const prevCtxRef = useRef<{ pdfId?: string; pdfTitle?: string; selectedText?: string; pdfText?: string } | null>(null);
  useEffect(() => {
    const prev = prevCtxRef.current;
    if (prev && prev.pdfId === pdfId && prev.pdfTitle === pdfTitle && prev.selectedText === selectedText && prev.pdfText === pdfText) return;
    prevCtxRef.current = { pdfId, pdfTitle, selectedText, pdfText };
    setContext({ panelId: 'agent', title: pdfTitle, selectedText, pdfFullText: pdfText, pdfId });
  }, [pdfId, pdfTitle, selectedText, pdfText, setContext]);

  const loadSkills = useCallback(async () => {
    setSkillsLoading(true);
    try {
      const data = await agentApi.listSkills();
      setSkills(data.skills || []);
    } catch {
      setSkills([
        { name: 'paper_qa', description: '基于PDF全文回答学术问题', category: 'reading' },
        { name: 'paper_summarize', description: '生成学术论文摘要', category: 'reading' },
        { name: 'polish_text', description: '学术文本润色（Nature风格）', category: 'writing' },
        { name: 'translate_text', description: '学术翻译', category: 'translation' },
        { name: 'draft_section', description: '起草论文章节', category: 'writing' },
        { name: 'generate_outline', description: '生成论文大纲', category: 'writing' },
        { name: 'format_citation', description: '格式化参考文献', category: 'citation' },
        { name: 'search_literature', description: '多源文献检索', category: 'search' },
        { name: 'generate_figure', description: '生成Nature标准图表代码', category: 'figure' },
        { name: 'draft_response', description: '起草审稿意见回复', category: 'response' },
        { name: 'check_data_availability', description: '审核数据可用性声明', category: 'data' },
        { name: 'paper_to_ppt', description: '论文转中文PPT大纲', category: 'paper2ppt' },
      ]);
    } finally { setSkillsLoading(false); }
  }, []);

  useEffect(() => { loadSkills(); }, [loadSkills]);

  // Check RAG status on mount
  useEffect(() => {
    ragApi.getStatus()
      .then(data => {
        setRagAvailable(data.available ?? false);
        setRagDatasets((data.datasets || []).map((d: { id: string; name: string }) => ({ id: d.id || d.name, name: d.name || d.id })));
      })
      .catch(() => { setRagAvailable(false); });
  }, []);

  // Load module agents
  const loadModules = useCallback(async () => {
    setModulesLoading(true);
    try {
      const data = await moduleApi.list();
      setModules(data.modules || []);
    } catch {
      setModules([]);
    } finally {
      setModulesLoading(false);
    }
  }, []);

  useEffect(() => { if (showModules) loadModules(); }, [showModules, loadModules]);

  useEffect(() => {
    if (selectedText && selectedText.length > 10) {
      const preview = selectedText.length > 100 ? `${selectedText.substring(0, 100)}...` : selectedText;
      setInput(prev => prev || `请解释这段文字: "${preview}"`);
    }
  }, [selectedText]);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [input]);

  const handleModuleExecute = useCallback(async (moduleName: string, task: string) => {
    setExecutingModule(moduleName);
    try {
      const result = await moduleApi.execute(moduleName, task, { pdfId, pdfTitle });
      if (result.interrupt_reason) {
        // Module interrupted — refresh status
        await loadModules();
      } else {
        await loadModules();
        // Also show result in agent chat
        const agentMsgId = `mod-${Date.now()}`;
        useAgentStore.setState(s => ({
          messages: [...s.messages, {
            id: `user-mod-${Date.now()}`,
            role: 'user' as const,
            content: `[${moduleLabels[moduleName] || moduleName}] ${task}`,
            steps: [],
            timestamp: new Date(),
          }, {
            id: agentMsgId,
            role: 'agent' as const,
            content: result.error ? `❌ 执行失败: ${result.error}` : (typeof result.data === 'string' ? result.data : JSON.stringify(result.data, null, 2)),
            steps: [],
            timestamp: new Date(),
          }],
        }));
      }
    } catch (_e: unknown) {
    } finally {
      setExecutingModule(null);
      setModuleTaskInput('');
    }
  }, [pdfId, pdfTitle, loadModules]);

  const handleModuleResume = useCallback(async (moduleName: string, choice: Record<string, any>) => {
    setExecutingModule(moduleName);
    try {
      await moduleApi.resume(moduleName, choice);
      await loadModules();
    } catch {
      // silently fail
    } finally {
      setExecutingModule(null);
    }
  }, [loadModules]);

  const handleSend = () => {
    if (!input.trim() || isRunning) return;
    if (ragMode && ragAvailable) {
      // RAG mode: query via /api/rag/query
      sendRagQuery(input);
    } else {
      sendTask(input);
    }
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const sendRagQuery = useCallback(async (question: string) => {
    const userMsgId = `rag-u-${Date.now()}`;
    const agentMsgId = `rag-a-${Date.now()}`;
    const now = new Date();
    const userMsg: AgentMessage = { id: userMsgId, role: 'user', content: question, steps: [], timestamp: now };
    const agentMsg: AgentMessage = { id: agentMsgId, role: 'agent', content: '', steps: [{ type: 'thinking', content: '正在从知识库检索相关文献...', name: '', timestamp: Date.now() }], timestamp: now };
    useAgentStore.setState(s => ({ messages: [...s.messages, userMsg, agentMsg], isRunning: true }));

    try {
      const data = await ragApi.query(question);
      const steps: AgentStep[] = [
        { type: 'thinking', content: data.available ? '✅ RAGFlow 知识库检索完成' : '⚠️ RAGFlow 未连接，使用回退模式', name: '', timestamp: Date.now() },
      ];
      if (data.reference) {
        steps.push({ type: 'tool_call', name: 'RAG检索', args: { question, datasets: ragDatasets.map(d => d.name) }, timestamp: Date.now() });
        steps.push({ type: 'tool_result', name: 'RAG结果', result: JSON.stringify(data.reference).slice(0, 500), timestamp: Date.now() });
      }
      useAgentStore.setState(s => ({
        messages: s.messages.map(m => m.id === agentMsgId ? { ...m, content: data.answer || '未获取到回答', steps } : m),
      }));
    } catch (e: unknown) {
      useAgentStore.setState(s => ({
        messages: s.messages.map(m => m.id === agentMsgId ? { ...m, content: `RAG 查询失败: ${e instanceof Error ? e.message : String(e)}`, steps: [{ type: 'error', content: e instanceof Error ? e.message : String(e), name: '', timestamp: Date.now() }] } : m),
      }));
    } finally {
      useAgentStore.setState({ isRunning: false });
    }
  }, [ragDatasets]);

  const handleNewSession = () => { newSession(); setInput(''); };

  const handleSwitchSession = async (sid: string) => { await switchSession(sid); setInput(''); };

  const handleDeleteSession = async (e: React.MouseEvent, sid: string) => { e.stopPropagation(); await deleteSession(sid); };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)' }}>
      {/* ── Session Sidebar ── */}
      {showSessions && (
        <div className="agent-sidebar">
          <div className="agent-sidebar-header">
            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body)' }}>会话历史</span>
            <div style={{ display: 'flex', gap: 4 }}>
              <button className="agent-icon-btn" onClick={handleNewSession} title="新建会话"><Plus size={14} /></button>
              <button className="agent-icon-btn" onClick={() => setShowSessions(false)}><PanelLeftClose size={14} /></button>
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {sessionsLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 20 }}><Loader2 size={14} className="animate-spin" style={{ color: 'var(--mute)' }} /></div>
            ) : sessions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: 20, fontSize: 11, color: 'var(--mute)' }}>暂无会话记录</div>
            ) : (
              sessions.map(s => (
                <SessionItem key={s.conversation_id} session={s} isActive={s.conversation_id === conversationId} onSelect={() => handleSwitchSession(s.conversation_id)} onDelete={e => handleDeleteSession(e, s.conversation_id)} />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Main Chat Area ── */}
      <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
        {/* Header */}
        <div className="agent-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button className="agent-icon-btn" onClick={() => { setShowSessions(!showSessions); loadSessions(); }} title="会话列表">
              {showSessions ? <PanelLeftClose size={15} /> : <PanelLeft size={15} />}
            </button>
            <div className="agent-avatar">
              <Bot size={16} />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--body)' }}>AcaSight Agent</div>
              <div style={{ fontSize: 10, color: 'var(--mute)' }}>
                {isRunning ? '思考中...' : '就绪'} {messages.length > 0 && `· ${messages.length} 条`}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button className={`agent-skill-toggle ${showModules ? 'active' : ''}`} onClick={() => { setShowModules(!showModules); setShowSkills(false); }} title="模块调度">
              <Boxes size={13} />
              <span>5</span>
              {showModules ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            </button>
            <button className="agent-icon-btn" onClick={handleNewSession} title="新建会话"><Plus size={14} /></button>
            {messages.length > 0 && (
              <button className="agent-icon-btn" onClick={clearMessages} title="清空对话" style={{ color: 'var(--danger)' }}><Trash2 size={14} /></button>
            )}
            <button className={`agent-skill-toggle ${showSkills ? 'active' : ''}`} onClick={() => setShowSkills(!showSkills)}>
              <Settings2 size={13} />
              <span>{skills.length}</span>
              {showSkills ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            </button>
          </div>
        </div>

        {/* Skills Panel */}
        {showSkills && !showModules && (
          <div className="agent-skills-panel">
            {skillsLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}><Loader2 size={16} className="animate-spin" style={{ color: 'var(--mute)' }} /></div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
                {skills.map(skill => (
                  <button key={skill.name} className="agent-skill-card" onClick={() => { setInput(`使用 ${skill.name}: `); setShowSkills(false); }}>
                    <span className="agent-skill-icon" style={{ background: categoryColors[skill.category] || '#6366f1' }}>
                      {categoryIcons[skill.category] || <Zap size={12} />}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--body)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{skill.name}</div>
                      <div style={{ fontSize: 9, color: 'var(--mute)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{skill.description}</div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Module Panel (visible when showModules && !showSkills) */}
        {showModules && !showSkills && (
          <div className="agent-skills-panel" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            {modulesLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}><Loader2 size={14} className="animate-spin" style={{ color: 'var(--mute)' }} /></div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {modules.map(m => {
                  const isRunning = m.status === 'running';
                  const isInterrupted = m.status === 'interrupted';
                  const isIdle = m.status === 'idle';
                  const statusColor: Record<string, string> = { idle: '#6b7280', running: '#3b82f6', interrupted: '#f59e0b', completed: '#10b981', failed: '#ef4444' };
                  return (
                    <div key={m.module} style={{ display: 'flex', flexDirection: 'column', gap: 4, padding: '8px 10px', borderRadius: 8, border: '1px solid var(--hairline)', background: isRunning ? 'rgba(59,130,246,0.06)' : 'transparent' }}>
                      {/* Header row */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ background: moduleColors[m.module] || '#6366f1', borderRadius: 6, padding: 4, display: 'flex', color: '#fff' }}>
                          {moduleIcons[m.module] || <Zap size={12} />}
                        </span>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--body)' }}>{moduleLabels[m.module] || m.module}</div>
                          <div style={{ fontSize: 9, color: statusColor[m.status] || '#6b7280' }}>{m.status} · {m.history_count} 次执行</div>
                        </div>
                        {isIdle && (
                          <button
                            onClick={() => { setExecutingModule(m.module); }}
                            style={{ padding: '3px 10px', fontSize: 10, borderRadius: 6, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer' }}
                          >执行</button>
                        )}
                        {isRunning && (
                          <span style={{ fontSize: 10, color: '#3b82f6', display: 'flex', alignItems: 'center', gap: 3 }}>
                            <Loader2 size={10} className="animate-spin" />执行中</span>
                        )}
                        {isInterrupted && (
                          <span style={{ fontSize: 10, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: 3 }}>
                            ⚠️ 等待确认</span>
                        )}
                      </div>
                      {/* Interrupt info + resume */}
                      {isInterrupted && m.interrupt_info && (
                        <div style={{ fontSize: 10, color: 'var(--body)', background: 'var(--canvas-soft)', padding: '6px 8px', borderRadius: 6, borderLeft: '3px solid #f59e0b' }}>
                          <div style={{ fontWeight: 600, marginBottom: 3 }}>⏸ 已中断：{m.interrupt_info.reason}</div>
                          {m.interrupt_info.section_title && (
                            <div style={{ marginBottom: 3 }}>章节：{m.interrupt_info.section_title}</div>
                          )}
                          {m.interrupt_info.options?.length > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 3, marginTop: 4 }}>
                              {m.interrupt_info.options.map((opt: Record<string, unknown>, idx: number) => (
                                <button
                                  key={idx}
                                  onClick={() => handleModuleResume(m.module, opt)}
                                  style={{ padding: '4px 8px', fontSize: 10, borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--body)', cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s' }}
                                  onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.background = 'var(--accent-bg-soft)'; }}
                                  onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--hairline)'; e.currentTarget.style.background = 'var(--canvas)'; }}
                                >✅ {(opt.label as string) || JSON.stringify(opt)}</button>
                              ))}
                            </div>
                          )}
                          {(!m.interrupt_info.options || m.interrupt_info.options.length === 0) && (
                            <button
                              onClick={() => handleModuleResume(m.module, { confirmed: true })}
                              style={{ marginTop: 4, padding: '4px 10px', fontSize: 10, borderRadius: 6, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}
                            >确认继续</button>
                          )}
                        </div>
                      )}
                      {/* Task input for idle module */}
                      {executingModule === m.module && isIdle && (
                        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                          <input
                            value={moduleTaskInput}
                            onChange={e => setModuleTaskInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleModuleExecute(m.module, moduleTaskInput); } }}
                            placeholder={`给${moduleLabels[m.module] || m.module}Agent 下达任务...`}
                            style={{ flex: 1, padding: '5px 8px', fontSize: 11, borderRadius: 6, border: '1px solid var(--hairline)', background: 'var(--canvas)', color: 'var(--ink)', outline: 'none' }}
                            onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; }}
                            onBlur={e => { e.currentTarget.style.borderColor = 'var(--hairline)'; }}
                          />
                          <button
                            onClick={() => handleModuleExecute(m.module, moduleTaskInput)}
                            disabled={!moduleTaskInput.trim() || executingModule !== null}
                            style={{ padding: '5px 10px', fontSize: 10, borderRadius: 6, border: 'none', background: moduleTaskInput.trim() ? 'var(--accent)' : 'var(--hairline)', color: moduleTaskInput.trim() ? '#fff' : 'var(--mute)', cursor: moduleTaskInput.trim() ? 'pointer' : 'not-allowed' }}
                          >发送</button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Messages Area */}
        <div className="agent-messages">
          {messages.length === 0 ? (
            <div className="agent-welcome">
              <div className="agent-welcome-avatar">
                <Bot size={28} />
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--body)', marginBottom: 4 }}>学术智能体已就绪</div>
              <div style={{ fontSize: 12, color: 'var(--mute)', marginBottom: 20 }}>输入任务或选择快捷操作开始</div>
              <div className="agent-quick-grid">
                {quickTasks.map(qt => (
                  <button key={qt.label} className="agent-quick-card" onClick={() => setInput(qt.prompt)}>
                    <span className="agent-quick-icon" style={{ background: qt.gradient }}>{qt.icon}</span>
                    <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--body)' }}>{qt.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: '16px 20px' }}>
              {messages.map(msg => (
                <div key={msg.id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  {msg.role === 'user' ? (
                    <div className="agent-bubble-user">
                      <span style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</span>
                    </div>
                  ) : (
                    <div style={{ maxWidth: '90%', display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {msg.steps.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {msg.steps.map((step, idx) => <StepBubble key={idx} step={step} isActive={false} />)}
                        </div>
                      )}
                      {msg.content && (
                        <div className="agent-bubble-agent">
                          <MarkdownRenderer content={msg.content} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {isRunning && messages.length > 0 && (() => {
                const last = messages[messages.length - 1];
                if (last.role === 'agent' && last.steps.length > 0) {
                  const lastStep = last.steps[last.steps.length - 1];
                  if (lastStep.type !== 'answer') return <div style={{ display: 'flex' }}><StepBubble step={lastStep} isActive /></div>;
                }
                return (
                  <div className="agent-typing">
                    <div className="agent-typing-dots">
                      <span /><span /><span />
                    </div>
                    <span style={{ fontSize: 11, color: 'var(--mute)' }}>思考中</span>
                  </div>
                );
              })()}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area (Bottom) */}
        <div className="agent-input-area">
          {pdfTitle && (
            <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
              <FileText size={10} /> {pdfTitle}
            </div>
          )}
          {/* RAG mode toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
            <button
              onClick={() => setRagMode(v => !v)}
              disabled={!ragAvailable}
              title={ragAvailable ? (ragMode ? 'RAG知识库模式已开启' : '点击开启RAG知识库模式') : 'RAGFlow服务未连接'}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '3px 10px', borderRadius: 20, fontSize: 10,
                border: ragMode ? '1px solid #10b981' : '1px solid var(--hairline)',
                background: ragMode ? 'rgba(16,185,129,0.1)' : 'transparent',
                color: ragMode ? '#10b981' : ragAvailable ? 'var(--mute)' : 'var(--hairline)',
                cursor: ragAvailable ? 'pointer' : 'not-allowed',
                transition: 'all 0.15s',
                opacity: ragAvailable ? 1 : 0.5,
              }}
            >
              <Library size={11} />
              RAG知识库
              {ragAvailable && ragDatasets.length > 0 && (
                <span style={{ fontSize: 9, color: 'var(--accent)', fontWeight: 600 }}>{ragDatasets.length}</span>
              )}
              {!ragAvailable && (
                <span style={{ fontSize: 8, color: 'var(--danger)', marginLeft: 2 }}>离线</span>
              )}
            </button>
            {ragMode && ragDatasets.length > 0 && (
              <span style={{ fontSize: 9, color: 'var(--body)', background: 'var(--canvas-soft)', padding: '2px 6px', borderRadius: 3 }}>
                {ragDatasets.map(d => d.name).join(', ')}
              </span>
            )}
          </div>
          <div className="agent-input-box">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="输入学术任务... (Shift+Enter 换行)"
              className="agent-input-textarea"
              rows={1}
              disabled={isRunning}
            />
            {isRunning ? (
              <button className="agent-send-btn loading" disabled>
                <Loader2 size={16} className="animate-spin" />
              </button>
            ) : (
              <button className="agent-send-btn" onClick={handleSend} disabled={!input.trim()}>
                <Send size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const SessionItem: React.FC<{
  session: SessionInfo;
  isActive: boolean;
  onSelect: () => void;
  onDelete: (e: React.MouseEvent) => void;
}> = ({ session, isActive, onSelect, onDelete }) => (
  <div className={`agent-session-item ${isActive ? 'active' : ''}`} onClick={onSelect}>
    <MessageSquare size={12} style={{ flexShrink: 0, opacity: 0.5, color: isActive ? 'var(--accent)' : 'var(--mute)' }} />
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: 11, color: isActive ? 'var(--accent)' : 'var(--body)' }}>{session.preview || '新会话'}</div>
      <div style={{ fontSize: 9, color: 'var(--mute)' }}>{session.message_count} 条消息</div>
    </div>
    <button className="agent-session-delete" onClick={onDelete} title="删除会话"><Trash2 size={10} /></button>
  </div>
);

const StepBubble: React.FC<{ step: AgentStep; isActive: boolean }> = ({ step, isActive }) => {
  const [expanded, setExpanded] = useState(false);

  if (step.type === 'thinking') {
    return (
      <div className={`agent-step-thinking ${isActive ? 'active' : ''}`}>
        {isActive ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
        <span>{step.content || '思考中...'}</span>
      </div>
    );
  }

  if (step.type === 'tool_call') {
    return (
      <div className="agent-step-tool">
        <button className="agent-step-toggle" onClick={() => setExpanded(!expanded)}>
          <Play size={10} />
          <span className="agent-step-name">{step.name}</span>
          {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </button>
        {expanded && step.args && (
          <pre className="agent-step-code">{JSON.stringify(step.args, null, 2)}</pre>
        )}
      </div>
    );
  }

  if (step.type === 'tool_result') {
    return (
      <div className="agent-step-tool">
        <button className="agent-step-toggle result" onClick={() => setExpanded(!expanded)}>
          <CheckCircle2 size={10} />
          <span>结果</span>
          {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        </button>
        {expanded && step.result && (
          <pre className="agent-step-code result">{step.result.length > 2000 ? step.result.substring(0, 2000) + '...' : step.result}</pre>
        )}
      </div>
    );
  }

  if (step.type === 'error') {
    return (
      <div className="agent-step-error">
        <AlertCircle size={11} />
        <span>{step.content || '执行出错'}</span>
      </div>
    );
  }

  return null;
};

export default AgentPanel;

