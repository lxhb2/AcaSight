import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Bot, Send, Sparkles, BookOpen, PenTool, Languages,
  X, Maximize2, Highlighter, Pen, Lightbulb,
  Database, BarChart3, Loader2,
} from 'lucide-react';
import { useAgentStore, type PanelContext } from '@/store/agentStore';

interface ContextAction {
  label: string;
  icon: React.ReactNode;
  prompt: string;
  gradient: string;
  isAI?: boolean;
}

function getContextActions(panelId: string, _title?: string): ContextAction[] {
  if (panelId === 'editor' || panelId === 'pdf') {
    return [
      { label: '翻译', icon: <Languages size={13} />, prompt: '请将选中的文本翻译为中文', gradient: 'linear-gradient(135deg, #3b82f6, #06b6d4)', isAI: true },
      { label: '解释', icon: <Lightbulb size={13} />, prompt: '请解释这段文字的核心含义', gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)', isAI: true },
      { label: '总结', icon: <Sparkles size={13} />, prompt: '请为这篇论文生成中文摘要', gradient: 'linear-gradient(135deg, #10b981, #06b6d4)', isAI: true },
      { label: '问答', icon: <BookOpen size={13} />, prompt: '根据这篇论文回答我的问题', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
      { label: '高亮', icon: <Highlighter size={13} />, prompt: 'highlight', gradient: 'linear-gradient(135deg, #eab308, #f97316)' },
      { label: '笔记', icon: <Pen size={13} />, prompt: 'note', gradient: 'linear-gradient(135deg, #f97316, #ef4444)' },
      { label: '数据处理', icon: <Database size={13} />, prompt: '请对以下数据进行预处理：清洗冗余内容、分列整理', gradient: 'linear-gradient(135deg, #0ea5e9, #6366f1)', isAI: true },
      { label: '自动绘图', icon: <BarChart3 size={13} />, prompt: '请根据以下数据推荐合适的图表类型并生成绘图建议', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)', isAI: true },
    ];
  }
  if (panelId === 'writing') {
    return [
      { label: '润色', icon: <PenTool size={13} />, prompt: '请润色以下文本，改为Nature期刊风格', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)', isAI: true },
      { label: '扩写', icon: <PenTool size={13} />, prompt: '请扩写以下段落，增加细节和论证', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)', isAI: true },
      { label: '缩写', icon: <PenTool size={13} />, prompt: '请将以下文本缩写到一半长度', gradient: 'linear-gradient(135deg, #10b981, #06b6d4)', isAI: true },
      { label: '引用', icon: <Sparkles size={13} />, prompt: '请检查这段文字中的引用格式', gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)', isAI: true },
    ];
  }
  if (panelId === 'search') {
    return [
      { label: '扩展查询', icon: <Sparkles size={13} />, prompt: '请根据搜索结果建议更精确的查询词', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
      { label: '分析趋势', icon: <Sparkles size={13} />, prompt: '请分析这些搜索结果的研究趋势', gradient: 'linear-gradient(135deg, #10b981, #06b6d4)' },
    ];
  }
  if (panelId === 'notes') {
    return [
      { label: '润色笔记', icon: <PenTool size={13} />, prompt: '请润色这段笔记', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)', isAI: true },
      { label: '整理要点', icon: <Sparkles size={13} />, prompt: '请整理这些笔记的关键点', gradient: 'linear-gradient(135deg, #10b981, #06b6d4)', isAI: true },
      { label: '数据处理', icon: <Database size={13} />, prompt: '请对以下数据进行预处理：清洗冗余内容、分列整理', gradient: 'linear-gradient(135deg, #0ea5e9, #6366f1)', isAI: true },
      { label: '自动绘图', icon: <BarChart3 size={13} />, prompt: '请根据以下数据推荐合适的图表类型并生成绘图建议', gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)', isAI: true },
    ];
  }
  return [
    { label: '分析', icon: <Sparkles size={13} />, prompt: '请分析当前内容', gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)' },
    { label: '问答', icon: <BookOpen size={13} />, prompt: '请回答关于当前内容的问题', gradient: 'linear-gradient(135deg, #10b981, #06b6d4)' },
  ];
}

interface ContextualAgentBarProps {
  panelId: string;
  title?: string;
  selectedText?: string;
  pdfText?: string;
  sectionType?: string;
  searchQuery?: string;
  onOpenAgentPanel?: () => void;
  mousePosition?: { x: number; y: number } | null;
}

export const ContextualAgentBar: React.FC<ContextualAgentBarProps> = ({
  panelId,
  title,
  selectedText,
  pdfText,
  sectionType,
  searchQuery,
  onOpenAgentPanel,
  mousePosition,
}) => {
  const [showBubble, setShowBubble] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const { isRunning, setContext, sendTask } = useAgentStore();

  const actions = getContextActions(panelId, title);

  useEffect(() => {
    const ctx: PanelContext = { panelId, title, selectedText, pdfText: pdfText || undefined, pdfFullText: pdfText || undefined, sectionType, searchQuery };
    setContext(ctx);
  }, [panelId, title, selectedText, pdfText, sectionType, searchQuery, setContext]);

  useEffect(() => {
    if (selectedText && selectedText.trim().length > 1) {
      setShowBubble(true);
      setShowPanel(false);
      setActiveAction(null);
    } else {
      setShowBubble(false);
      setShowPanel(false);
      setActiveAction(null);
    }
  }, [selectedText]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowPanel(false);
        setShowBubble(false);
        setActiveAction(null);
      }
    };
    if (showPanel) {
      const timer = setTimeout(() => {
        window.addEventListener('mousedown', handleClickOutside);
      }, 100);
      return () => {
        clearTimeout(timer);
        window.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showPanel]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowPanel(false);
        setShowBubble(false);
        setActiveAction(null);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  // 所有操作统一走 Agent（不再用直调 API）
  const handleQuickAction = useCallback((action: ContextAction) => {
    if (action.prompt === 'highlight' || action.prompt === 'note') {
      setActiveAction(action.label);
      return;
    }
    // Route through Agent
    const contextText = selectedText || pdfText || '';
    const fullPrompt = contextText
      ? `${action.prompt}：\n\n${contextText}`
      : action.prompt;
    sendTask(fullPrompt);
    if (onOpenAgentPanel) onOpenAgentPanel();
    setShowPanel(false);
  }, [selectedText, pdfText, sendTask, onOpenAgentPanel]);

  // unused helpers removed (inline result display removed — results now go to Agent Panel)

  const handleSend = () => {
    if (!input.trim() || isRunning) return;
    sendTask(input);
    setInput('');
    if (onOpenAgentPanel) onOpenAgentPanel();
    setShowPanel(false);
  };

  if (!showBubble && !showPanel) return null;

  const pos = mousePosition || { x: 200, y: 200 };

  if (!showPanel) {
    const bubbleX = Math.max(10, Math.min(pos.x + 12, window.innerWidth - 50));
    const bubbleY = Math.max(10, pos.y - 40);

    return (
      <div
        ref={panelRef}
        className="ctx-bubble-trigger"
        style={{ position: 'fixed', left: bubbleX, top: bubbleY, zIndex: 9999 }}
        onClick={(e) => {
          e.stopPropagation();
          setShowPanel(true);
        }}
      >
        <div className="ctx-bubble-orb">
          <Bot size={14} />
        </div>
      </div>
    );
  }

  const panelX = Math.max(10, Math.min(pos.x - 150, window.innerWidth - 340));
  const panelY = Math.max(10, pos.y - 120);

  return (
    <div
      ref={panelRef}
      className="ctx-bubble-panel"
      style={{ position: 'fixed', left: panelX, top: panelY, zIndex: 9999 }}
    >
      <div className="ctx-bubble-header">
        <div className="ctx-bubble-header-icon">
          <Bot size={12} />
        </div>
        <span className="ctx-bubble-header-title">AI 助手</span>
        <button className="ctx-bubble-expand" onClick={() => { if (onOpenAgentPanel) onOpenAgentPanel(); setShowPanel(false); }} title="打开 Agent 面板">
          <Maximize2 size={12} />
        </button>
        <button className="ctx-bubble-close" onClick={() => { setShowPanel(false); setShowBubble(false); setActiveAction(null); }}>
          <X size={12} />
        </button>
      </div>

      <div className="ctx-bubble-actions">
        {actions.map((action, idx) => {
          const isActive = activeAction === action.label;
          return (
            <button
              key={idx}
              onClick={() => handleQuickAction(action)}
              className={`ctx-bubble-action-btn ${isActive ? 'active' : ''}`}
            >
              <div className="ctx-bubble-action-icon" style={{ background: action.gradient }}>
                {action.icon}
              </div>
              <span>{action.label}</span>
            </button>
          );
        })}
      </div>

      {selectedText && (
        <div className="ctx-bubble-preview">
          {selectedText.slice(0, 80)}{selectedText.length > 80 ? '...' : ''}
        </div>
      )}

      <div className="ctx-bubble-input-row">
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
          }}
          placeholder="询问 Agent..."
          className="ctx-bubble-input"
          rows={1}
          disabled={isRunning}
        />
        {isRunning ? (
          <Loader2 size={16} className="animate-spin text-blue-500 flex-shrink-0" />
        ) : (
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="ctx-bubble-send-btn"
          >
            <Send size={13} />
          </button>
        )}
      </div>
    </div>
  );
};

export default ContextualAgentBar;
