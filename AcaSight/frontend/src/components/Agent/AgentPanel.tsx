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
  Settings2,
} from 'lucide-react';
import { MarkdownRenderer } from '@/components/Common/MarkdownRenderer';
import { useAgentStore, type AgentStep, type SessionInfo } from '@/store/agentStore';

const BASE_URL = 'http://localhost:9000/api';

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

interface AgentPanelProps {
  pdfId?: string;
  pdfTitle?: string;
  selectedText?: string;
  pdfText?: string;
}

export const AgentPanel: React.FC<AgentPanelProps> = ({ pdfTitle, selectedText, pdfText }) => {
  const [input, setInput] = useState('');
  const [showSkills, setShowSkills] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages, isRunning, sendTask, setContext, clearMessages,
    conversationId, sessions, sessionsLoading,
    loadSessions, switchSession, deleteSession, newSession,
  } = useAgentStore();

  useEffect(() => { setContext({ panelId: 'agent', title: pdfTitle, selectedText, pdfFullText: pdfText }); }, [pdfTitle, selectedText, pdfText, setContext]);

  const loadSkills = useCallback(async () => {
    setSkillsLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/agent/skills`);
      const data = await res.json();
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

  const handleSend = () => {
    if (!input.trim() || isRunning) return;
    sendTask(input);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

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
        {showSkills && (
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
