import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Copy, Loader2, ChevronDown, ChevronUp, GripHorizontal, Volume2, Check, Sparkles, PenLine, Shrink, RefreshCw } from 'lucide-react';
import { aiApi, type ChatMessage } from '@/services/api';

interface FloatingTranslateProps {
  text: string;
  position: { x: number; y: number };
  onClose: () => void;
}

export const FloatingTranslate: React.FC<FloatingTranslateProps> = ({ text, position, onClose }) => {
  const [translation, setTranslation] = useState('');
  const [explanation, setExplanation] = useState('');
  const [loading, setLoading] = useState<'translate' | 'explain' | null>('translate');
  const [showExplain, setShowExplain] = useState(false);
  const [copied, setCopied] = useState(false);
  const [pos, setPos] = useState(position);
  const [isDragging, setIsDragging] = useState(false);
  const [writingLoading, setWritingLoading] = useState(false);
  const [writingResult, setWritingResult] = useState('');
  const dragStartRef = useRef({ x: 0, y: 0 });
  const panelRef = useRef<HTMLDivElement>(null);

  // 翻译
  useEffect(() => {
    let cancelled = false;
    const fetchTranslation = async () => {
      setLoading('translate');
      try {
        const msgs: ChatMessage[] = [
          { role: 'system', content: '你是一个精确的学术翻译助手。请将用户提供的英文文本翻译成自然流畅的中文，保持学术术语的准确性。只输出中文翻译，不需要额外说明。' },
          { role: 'user', content: `请将以下英文翻译成中文：\n\n${text}` },
        ];
        const res = await aiApi.chat(msgs);
        if (!cancelled) {
          setTranslation(res.response || '翻译失败');
          setLoading(null);
        }
      } catch (err: any) {
        if (!cancelled) {
          setTranslation(`翻译请求失败: ${err?.message || '未知错误'}`);
          setLoading(null);
        }
      }
    };
    fetchTranslation();
    return () => { cancelled = true; };
  }, [text]);

  // AI 解释
  const fetchExplanation = useCallback(async () => {
    if (explanation || loading === 'explain') return;
    setShowExplain(true);
    setLoading('explain');
    try {
      const msgs: ChatMessage[] = [
        { role: 'system', content: '你是一个学术研究助手。请用中文简要解释用户提供的英文文本的含义、上下文和重要术语（不超过 150 字）。' },
        { role: 'user', content: `请解释以下文本：\n\n${text}` },
      ];
      const res = await aiApi.chat(msgs);
      setExplanation(res.response || '解释失败');
    } catch (err: any) {
      setExplanation(`请求失败: ${err?.message || '未知错误'}`);
    } finally {
      setLoading(null);
    }
  }, [text, explanation, loading]);

  // 写作工具
  const handleWritingAction = useCallback(async (action: string) => {
    setWritingLoading(true);
    setWritingResult('');
    try {
      const resp = await fetch('http://localhost:9000/api/writing/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, action }),
      });
      if (!resp.ok) throw new Error(`请求失败 (${resp.status})`);
      const data = await resp.json();
      setWritingResult(data.result || '处理失败');
    } catch (e: any) {
      setWritingResult(`❌ ${e.message}`);
    } finally {
      setWritingLoading(false);
    }
  }, [text]);

  // Esc 关闭
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.altKey && e.key === 't') {
        e.preventDefault();
        // Alt+T 翻译已在选文 toolbar 触发，此处不做额外处理
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // 外部点击关闭
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    // 延迟绑定避免触发时的点击事件立即关闭
    const timer = setTimeout(() => {
      window.addEventListener('mousedown', handleClick);
    }, 100);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('mousedown', handleClick);
    };
  }, [onClose]);

  // 拖拽
  const handleDragStart = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
  };
  const handleDragMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    setPos({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y,
    });
  }, [isDragging]);
  const handleDragEnd = () => setIsDragging(false);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('mouseup', handleDragEnd);
      return () => {
        window.removeEventListener('mousemove', handleDragMove);
        window.removeEventListener('mouseup', handleDragEnd);
      };
    }
  }, [isDragging, handleDragMove]);

  // 复制
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(translation);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = translation;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // 朗读（如果浏览器支持）
  const handleSpeak = () => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(translation);
      utterance.lang = 'zh-CN';
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    }
  };

  // 限制窗口在可视范围内
  const safePos = {
    x: Math.max(10, Math.min(pos.x, window.innerWidth - 420)),
    y: Math.max(10, Math.min(pos.y, window.innerHeight - 300)),
  };

  return (
    <div
      ref={panelRef}
      className="acasight-floating-translate"
      style={{
        position: 'fixed',
        left: safePos.x,
        top: safePos.y,
        width: 380,
        maxHeight: 500,
        zIndex: 1000,
        background: 'var(--panel-bg)',
        border: '1px solid var(--hairline)',
        borderRadius: 12,
        boxShadow: '0 16px 48px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.05)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        userSelect: isDragging ? 'none' : 'auto',
      }}
    >
      {/* 标题栏 / 拖拽手柄 */}
      <div
        onMouseDown={handleDragStart}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '8px 12px',
          borderBottom: '1px solid var(--hairline)',
          background: 'var(--sidebar-hover)',
          cursor: 'grab',
          gap: 8,
        }}
      >
        <GripHorizontal size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', flex: 1 }}>
          🔤 翻译助手
        </span>
        <button
          onClick={() => { if ('speechSynthesis' in window) handleSpeak(); }}
          title="朗读"
          style={{
            background: 'none', border: 'none', padding: 2, cursor: 'pointer',
            color: 'var(--mute)', borderRadius: 4,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--sidebar-active)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
        >
          <Volume2 size={14} />
        </button>
        <button
          onClick={handleCopy}
          title="复制翻译"
          style={{
            background: 'none', border: 'none', padding: 2, cursor: 'pointer',
            color: copied ? '#10b981' : 'var(--mute)', borderRadius: 4,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--sidebar-active)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
        <button
          onClick={onClose}
          style={{
            background: 'none', border: 'none', padding: 2, cursor: 'pointer',
            color: 'var(--mute)', borderRadius: 4,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--sidebar-active)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
        >
          <X size={14} />
        </button>
      </div>

      {/* 原文 */}
      <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--hairline)' }}>
        <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          📄 原文
        </div>
        <div style={{
          fontSize: 12,
          color: 'var(--body)',
          maxHeight: 80,
          overflow: 'auto',
          lineHeight: 1.5,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {text.slice(0, 500)}{text.length > 500 ? '...' : ''}
        </div>
      </div>

      {/* 翻译结果 */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 12px' }}>
        <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
          🇨🇳 中文翻译
        </div>
        {loading === 'translate' ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0', color: 'var(--mute)' }}>
            <Loader2 size={16} className="animate-spin" />
            <span style={{ fontSize: 13 }}>正在翻译...</span>
          </div>
        ) : (
          <div style={{
            fontSize: 13,
            color: 'var(--ink)',
            lineHeight: 1.7,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {translation}
          </div>
        )}
      </div>

      {/* 写作工具栏 */}
      <div style={{ borderTop: '1px solid var(--hairline)', padding: '6px 8px', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 10, color: 'var(--mute)', width: '100%', marginBottom: 2 }}>✍️ 写作工具</span>
        {[
          { id: 'polish', label: '润色', icon: Sparkles },
          { id: 'expand', label: '扩写', icon: PenLine },
          { id: 'shrink', label: '缩写', icon: Shrink },
          { id: 'rewrite', label: '降重', icon: RefreshCw },
        ].map(tool => (
          <button
            key={tool.id}
            onClick={() => handleWritingAction(tool.id)}
            disabled={writingLoading}
            style={{
              display: 'flex', alignItems: 'center', gap: 3,
              padding: '3px 8px', borderRadius: 6,
              fontSize: 11, cursor: writingLoading ? 'wait' : 'pointer',
              background: 'var(--sidebar-hover)',
              border: '1px solid var(--hairline)',
              color: 'var(--body)',
              opacity: writingLoading ? 0.5 : 1,
            }}
          >
            <tool.icon size={11} />
            {tool.label}
          </button>
        ))}
        {writingResult && (
          <div style={{ width: '100%', marginTop: 4, padding: '6px 8px', borderRadius: 6, background: 'var(--sidebar-hover)', maxHeight: 120, overflow: 'auto' }}>
            <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>📝 结果</span>
              <button onClick={async () => { await navigator.clipboard.writeText(writingResult); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', fontSize: 10 }}><Copy size={10} /> 复制</button>
            </div>
            <div style={{ fontSize: 12, color: 'var(--ink)', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {writingResult}
            </div>
          </div>
        )}
      </div>

      {/* AI 解释（折叠） */}
      <div style={{ borderTop: '1px solid var(--hairline)' }}>
        <button
          onClick={() => {
            if (!showExplain) {
              fetchExplanation();
            } else {
              setShowExplain(false);
            }
          }}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 12px',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--mute)',
            fontSize: 12,
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--sidebar-hover)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
        >
          <span>💡 AI 解释</span>
          {showExplain ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {showExplain && (
          <div style={{ padding: '0 12px 10px' }}>
            {loading === 'explain' ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', color: 'var(--mute)' }}>
                <Loader2 size={14} className="animate-spin" />
                <span style={{ fontSize: 12 }}>AI 思考中...</span>
              </div>
            ) : (
              <div style={{
                fontSize: 12,
                color: 'var(--body)',
                lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {explanation}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};