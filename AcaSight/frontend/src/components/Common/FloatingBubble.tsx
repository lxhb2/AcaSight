import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Languages, Sparkles, Lightbulb, Copy, Check, Volume2, X, Loader2, Highlighter, Pen, BookOpen } from 'lucide-react';
import { aiApi, type ChatMessage } from '@/services/api';
import { useAIModels } from '@/hooks/useAIModels';

interface FloatingBubbleProps {
  text: string;
  position: { x: number; y: number };
  onClose: () => void;
}

type ActionType = 'translate' | 'polish' | 'explain' | 'highlight' | 'note' | 'summarize';

const ACTION_CONFIG: Record<ActionType, { label: string; icon: React.ElementType; systemPrompt: string; gradient: string }> = {
  translate: {
    label: '翻译',
    icon: Languages,
    gradient: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
    systemPrompt: '你是一个精确的学术翻译助手。请将用户提供的文本翻译成自然流畅的中文，保持学术术语的准确性。只输出翻译结果，不需要额外说明。如果文本已经是中文，请翻译成英文。',
  },
  polish: {
    label: '润色',
    icon: Sparkles,
    gradient: 'linear-gradient(135deg, #8b5cf6, #ec4899)',
    systemPrompt: '你是一个学术写作润色助手。请对用户提供的文本进行润色，使其更加流畅、专业和准确。保持原意不变，只输出润色后的结果。',
  },
  explain: {
    label: '解释',
    icon: Lightbulb,
    gradient: 'linear-gradient(135deg, #f59e0b, #ef4444)',
    systemPrompt: '你是一个学术研究助手。请用中文简要解释用户提供的文本的含义、上下文和重要术语（不超过 150 字）。',
  },
  highlight: {
    label: '高亮',
    icon: Highlighter,
    gradient: 'linear-gradient(135deg, #eab308, #f97316)',
    systemPrompt: '',
  },
  note: {
    label: '笔记',
    icon: Pen,
    gradient: 'linear-gradient(135deg, #f97316, #ef4444)',
    systemPrompt: '',
  },
  summarize: {
    label: '总结',
    icon: BookOpen,
    gradient: 'linear-gradient(135deg, #10b981, #06b6d4)',
    systemPrompt: '你是一个学术研究助手。请用中文简要总结用户提供的文本的核心要点（不超过 100 字）。',
  },
};

export const FloatingBubble: React.FC<FloatingBubbleProps> = ({ text, position, onClose }) => {
  const [expanded, setExpanded] = useState<ActionType | null>(null);
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showPanel, setShowPanel] = useState(false);
  const { currentModel } = useAIModels();
  const panelRef = useRef<HTMLDivElement>(null);

  const executeAction = useCallback(async (action: ActionType) => {
    if (action === 'highlight' || action === 'note') {
      setExpanded(action);
      setResult(ACTION_CONFIG[action].label + '功能已标记');
      return;
    }
    setExpanded(action);
    setLoading(true);
    setResult('');
    const config = ACTION_CONFIG[action];
    try {
      const msgs: ChatMessage[] = [
        { role: 'system', content: config.systemPrompt },
        { role: 'user', content: text },
      ];
      const res = await aiApi.chat(msgs, undefined, currentModel);
      setResult(res.response || '处理失败');
    } catch (err: any) {
      setResult(`❌ ${err?.message || '请求失败'}`);
    } finally {
      setLoading(false);
    }
  }, [text, currentModel]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const timer = setTimeout(() => {
      window.addEventListener('mousedown', handleClick);
    }, 100);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('mousedown', handleClick);
    };
  }, [onClose]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  };

  const handleSpeak = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(result);
      utterance.lang = 'zh-CN';
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    }
  };

  const bubbleX = Math.max(10, Math.min(position.x + 12, window.innerWidth - 50));
  const bubbleY = Math.max(10, position.y - 40);

  if (!showPanel) {
    return (
      <div
        ref={panelRef}
        className="floating-bubble-trigger acasight-floating-bubble"
        style={{
          position: 'fixed',
          left: bubbleX,
          top: bubbleY,
          zIndex: 9999,
        }}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          setShowPanel(true);
        }}
      >
        <div className="floating-bubble-orb">
          <Sparkles size={14} />
        </div>
      </div>
    );
  }

  const panelX = Math.max(10, Math.min(position.x - 140, window.innerWidth - 320));
  const panelY = Math.max(10, position.y - (expanded ? 240 : 60));

  return (
    <div
      ref={panelRef}
      className="floating-bubble-panel acasight-floating-bubble"
      style={{
        position: 'fixed',
        left: panelX,
        top: panelY,
        zIndex: 9999,
      }}
    >
      <div className="floating-bubble-header">
        <div className="floating-bubble-header-icon">
          <Sparkles size={12} />
        </div>
        <span className="floating-bubble-header-title">AI 助手</span>
        <button className="floating-bubble-close" onClick={onClose}>
          <X size={12} />
        </button>
      </div>

      <div className="floating-bubble-actions">
        {(Object.entries(ACTION_CONFIG) as [ActionType, typeof ACTION_CONFIG[ActionType]][]).map(([key, cfg]) => {
          const isActive = expanded === key;
          return (
            <button
              key={key}
              onClick={() => executeAction(key)}
              className={`floating-bubble-action-btn ${isActive ? 'active' : ''}`}
            >
              <div
                className="floating-bubble-action-icon"
                style={{ background: cfg.gradient }}
              >
                <cfg.icon size={11} />
              </div>
              <span>{cfg.label}</span>
            </button>
          );
        })}
      </div>

      {expanded && (
        <div className="floating-bubble-result">
          <div className="floating-bubble-result-header">
            <span className="floating-bubble-result-label">
              {ACTION_CONFIG[expanded].label}结果
            </span>
            <div className="floating-bubble-result-actions">
              <button className="floating-bubble-mini-btn" onClick={handleCopy}>
                {copied ? <Check size={11} /> : <Copy size={11} />}
              </button>
              <button className="floating-bubble-mini-btn" onClick={handleSpeak}>
                <Volume2 size={11} />
              </button>
            </div>
          </div>
          {loading ? (
            <div className="floating-bubble-loading">
              <Loader2 size={14} className="animate-spin" />
              <span>处理中...</span>
            </div>
          ) : (
            <div className="floating-bubble-result-text">
              {result}
            </div>
          )}
        </div>
      )}

      <div className="floating-bubble-preview">
        {text.slice(0, 80)}{text.length > 80 ? '...' : ''}
      </div>
    </div>
  );
};
