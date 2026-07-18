/**
 * FloatingTranslate — 统一翻译悬浮窗
 *
 * 合并了 PDFReader 版本和 Translate 版本的功能：
 * - Argos Translate 优先（离线快速），AI 后备
 * - 语言对切换
 * - AI 解释（折叠）
 * - 写作工具（润色/扩写/缩写/降重）
 * - 拖拽、复制、朗读
 * - 最小化/全文翻译
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  X, Copy, Check, Maximize2, Minimize2, Languages,
  ChevronDown, ChevronUp, Loader2, ExternalLink,
  GripHorizontal, Volume2, Sparkles, PenLine, Shrink, RefreshCw,
} from 'lucide-react';
import { aiApi, type ChatMessage, translateApi } from '@/services/api';
import { writingApi } from '@/services/api';

interface FloatingTranslateProps {
  /** 选中的文本 */
  text: string;
  /** 浮窗位置 */
  position: { x: number; y: number };
  /** 关闭回调 */
  onClose: () => void;
  /** 打开全文翻译回调 */
  onOpenFullPage?: (text: string) => void;
}

const LANG_PAIRS = [
  { label: '英 → 中', source: 'en', target: 'zh' },
  { label: '中 → 英', source: 'zh', target: 'en' },
  { label: '自动 → 中', source: 'auto', target: 'zh' },
  { label: '自动 → 英', source: 'auto', target: 'en' },
  { label: '英 → 日', source: 'en', target: 'ja' },
  { label: '日 → 中', source: 'ja', target: 'zh' },
];

export const FloatingTranslate: React.FC<FloatingTranslateProps> = ({
  text,
  position,
  onClose,
  onOpenFullPage,
}) => {
  // ---- 翻译状态 ----
  const [translation, setTranslation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('zh');
  const [engineStatus, setEngineStatus] = useState<string>('checking');

  // ---- AI 解释 ----
  const [explanation, setExplanation] = useState('');
  const [explainLoading, setExplainLoading] = useState(false);
  const [showExplain, setShowExplain] = useState(false);

  // ---- 写作工具 ----
  const [writingLoading, setWritingLoading] = useState(false);
  const [writingResult, setWritingResult] = useState('');

  // ---- UI 状态 ----
  const [copied, setCopied] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [showLangMenu, setShowLangMenu] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [pos, setPos] = useState(position);

  const panelRef = useRef<HTMLDivElement>(null);
  const langBtnRef = useRef<HTMLButtonElement>(null);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const translateTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // ---- 检查翻译引擎状态 ----
  useEffect(() => {
    translateApi.status()
      .then((res) => {
        const engines = res.data?.engines;
        if (engines?.google || engines?.microsoft || engines?.mymemory) {
          setEngineStatus('ready');
        } else if (engines?.ai) {
          setEngineStatus('need_lang');
        } else {
          setEngineStatus('unavailable');
        }
      })
      .catch(() => setEngineStatus('unavailable'));
  }, []);

  // ---- 翻译：短词用 Argos，句子/段落用 AI ----
  const doTranslate = useCallback(async (src: string, tgt: string, txt: string) => {
    if (!txt.trim()) return;
    setLoading(true);
    setError(null);

    // 判断是否为短词/短语（≤5 个单词且无句号）→ 用 Argos（快速）
    const wordCount = txt.split(/\s+/).length;
    const isShortPhrase = wordCount <= 5 && !txt.includes('.') && !txt.includes('?') && !txt.includes('!');

    if (isShortPhrase) {
      // 短词/短语：尝试 Argos
      try {
        const argosRes = await translateApi.text({
          text: txt,
          source_lang: src,
          target_lang: tgt,
        });
        const result = argosRes.data;
        if (result?.translation && result.translation.trim() !== txt.trim()) {
          setTranslation(result.translation);
          setLoading(false);
          if (src === 'auto' && result.from_lang && result.from_lang !== 'auto') {
            setSourceLang(result.from_lang);
          }
          return;
        }
      } catch {
        // Argos 失败，回退到 AI
      }
    }

    // 句子/段落或 Argos 失败：使用 AI 翻译（质量更高）
    try {
      const targetLangName = tgt === 'zh' ? '中文' : tgt === 'en' ? '英文' : tgt === 'ja' ? '日文' : tgt;
      const msgs: ChatMessage[] = [
        { role: 'system', content: `你是一个精确的学术翻译助手。请将用户提供的文本翻译成自然流畅的${targetLangName}，保持学术术语的准确性。只输出翻译结果，不需要额外说明。` },
        { role: 'user', content: `请将以下文本翻译成${targetLangName}：\n\n${txt}` },
      ];
      const res = await aiApi.chat(msgs);
      setTranslation(res.response || '翻译失败');
    } catch (err) {
      setError(err instanceof Error ? err.message : '翻译失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // ---- 自动翻译 ----
  useEffect(() => {
    if (translateTimeoutRef.current) clearTimeout(translateTimeoutRef.current);
    translateTimeoutRef.current = setTimeout(() => {
      doTranslate(sourceLang, targetLang, text);
    }, 300);
    return () => {
      if (translateTimeoutRef.current) clearTimeout(translateTimeoutRef.current);
    };
  }, [text, sourceLang, targetLang, doTranslate]);

  // ---- AI 解释 ----
  const fetchExplanation = useCallback(async () => {
    if (explanation || explainLoading) return;
    setShowExplain(true);
    setExplainLoading(true);
    try {
      const msgs: ChatMessage[] = [
        { role: 'system', content: '你是一个学术研究助手。请用中文简要解释用户提供的文本的含义、上下文和重要术语（不超过 150 字）。' },
        { role: 'user', content: `请解释以下文本：\n\n${text}` },
      ];
      const res = await aiApi.chat(msgs);
      setExplanation(res.response || '解释失败');
    } catch (err) {
      setExplanation(`请求失败: ${err instanceof Error ? err.message : '未知错误'}`);
    } finally {
      setExplainLoading(false);
    }
  }, [text, explanation, explainLoading]);

  // ---- 写作工具 ----
  const handleWritingAction = useCallback(async (action: string) => {
    setWritingLoading(true);
    setWritingResult('');
    try {
      const data = await writingApi.process({ text, action });
      setWritingResult(data.result || '处理失败');
    } catch (e) {
      setWritingResult(`${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setWritingLoading(false);
    }
  }, [text]);

  // ---- 拖拽 ----
  const handleDragStart = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragStartRef.current = { x: e.clientX - pos.x, y: e.clientY - pos.y };
  };
  const handleDragMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    setPos({ x: e.clientX - dragStartRef.current.x, y: e.clientY - dragStartRef.current.y });
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

  // ---- 复制 ----
  const handleCopy = async () => {
    if (!translation) return;
    try {
      await navigator.clipboard.writeText(translation);
    } catch {
      const ta = document.createElement('textarea');
      ta.value = translation;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ---- 朗读 ----
  const handleSpeak = () => {
    if ('speechSynthesis' in window && translation) {
      const utterance = new SpeechSynthesisUtterance(translation);
      utterance.lang = targetLang === 'zh' ? 'zh-CN' : 'en-US';
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    }
  };

  // ---- 语言对切换 ----
  const handleLangPair = (pair: { source: string; target: string }) => {
    setSourceLang(pair.source);
    setTargetLang(pair.target);
    setShowLangMenu(false);
  };

  // ---- Esc 关闭 ----
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // ---- 外部点击关闭 ----
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        if (langBtnRef.current && langBtnRef.current.contains(e.target as Node)) return;
        onClose();
      }
    };
    setTimeout(() => document.addEventListener('mousedown', handler), 100);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  // ---- 限制窗口在可视范围内 ----
  const safePos = {
    x: Math.max(10, Math.min(pos.x, window.innerWidth - (minimized ? 320 : 420))),
    y: Math.max(10, Math.min(pos.y, window.innerHeight - 300)),
  };

  const currentPairLabel = LANG_PAIRS.find(p => p.source === sourceLang && p.target === targetLang)?.label || `${sourceLang} → ${targetLang}`;
  const isLongText = text.length > 500;

  return (
    <div
      ref={panelRef}
      style={{
        position: 'fixed',
        left: safePos.x,
        top: safePos.y,
        zIndex: 10000,
        width: minimized ? 320 : 400,
        maxHeight: minimized ? 'auto' : 520,
        background: 'var(--canvas, #1e1e2e)',
        border: '1px solid var(--hairline, #333)',
        borderRadius: 12,
        boxShadow: '0 16px 48px rgba(0,0,0,0.35), 0 0 0 1px rgba(255,255,255,0.05)',
        overflow: 'hidden',
        fontFamily: 'Inter, system-ui, sans-serif',
        userSelect: isDragging ? 'none' : 'auto',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* ── 标题栏 / 拖拽手柄 ── */}
      <div
        onMouseDown={handleDragStart}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '8px 10px',
          borderBottom: minimized ? 'none' : '1px solid var(--hairline, #333)',
          background: 'var(--accent-bg-soft, rgba(99,102,241,0.08))',
          cursor: 'grab',
        }}
      >
        <GripHorizontal size={14} style={{ color: 'var(--mute)', flexShrink: 0 }} />
        <Languages size={14} style={{ color: 'var(--accent, #6366f1)', flexShrink: 0 }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--body, #ddd)', flex: 1 }}>
          翻译
        </span>

        {/* 引擎状态 */}
        {engineStatus === 'ready' && (
          <span style={{ fontSize: 9, color: '#10b981', background: 'rgba(16,185,129,0.12)', padding: '1px 6px', borderRadius: 8 }}>
            Argos
          </span>
        )}
        {engineStatus === 'need_lang' && (
          <span style={{ fontSize: 9, color: '#f59e0b', background: 'rgba(245,158,11,0.12)', padding: '1px 6px', borderRadius: 8 }}>
            需下载
          </span>
        )}

        {isLongText && onOpenFullPage && (
          <button
            onClick={() => onOpenFullPage(text)}
            title="全文翻译"
            style={iconBtnStyle}
          >
            <ExternalLink size={12} />
          </button>
        )}

        <button onClick={() => handleSpeak()} title="朗读" style={iconBtnStyle}>
          <Volume2 size={12} />
        </button>
        <button onClick={() => setMinimized(!minimized)} title={minimized ? '展开' : '最小化'} style={iconBtnStyle}>
          {minimized ? <Maximize2 size={12} /> : <Minimize2 size={12} />}
        </button>
        <button onClick={onClose} title="关闭" style={iconBtnStyle}>
          <X size={12} />
        </button>
      </div>

      {!minimized && (
        <>
          {/* ── 语言选择器 ── */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px' }}>
            <div style={{ position: 'relative' }}>
              <button
                ref={langBtnRef}
                onClick={() => setShowLangMenu(!showLangMenu)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 10px', borderRadius: 6,
                  background: 'transparent', border: '1px solid var(--hairline, #444)',
                  color: 'var(--body, #ccc)', cursor: 'pointer', fontSize: 11,
                }}
              >
                <Languages size={11} />
                {currentPairLabel}
                <ChevronDown size={10} />
              </button>
              {showLangMenu && (
                <div style={{
                  position: 'absolute', top: '100%', left: 0, marginTop: 4,
                  background: 'var(--canvas, #1e1e2e)', border: '1px solid var(--hairline, #444)',
                  borderRadius: 8, boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
                  padding: 4, zIndex: 100, minWidth: 140,
                }}>
                  {LANG_PAIRS.map((pair) => (
                    <button
                      key={`${pair.source}-${pair.target}`}
                      onClick={() => handleLangPair(pair)}
                      style={{
                        display: 'block', width: '100%', textAlign: 'left',
                        padding: '6px 10px', borderRadius: 4, border: 'none',
                        background: sourceLang === pair.source && targetLang === pair.target
                          ? 'var(--accent-bg-soft, rgba(99,102,241,0.15))' : 'transparent',
                        color: 'var(--body, #ccc)', cursor: 'pointer', fontSize: 11,
                      }}
                    >
                      {pair.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── 原文 ── */}
          <div style={{ padding: '0 10px', borderBottom: '1px solid var(--hairline, #333)' }}>
            <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              原文
            </div>
            <div style={{
              fontSize: 12, color: 'var(--body, #ccc)', lineHeight: 1.5,
              maxHeight: 80, overflow: 'auto', wordBreak: 'break-word',
              whiteSpace: 'pre-wrap', paddingBottom: 8,
            }}>
              {text.slice(0, 500)}{text.length > 500 ? '...' : ''}
            </div>
          </div>

          {/* ── 翻译结果 ── */}
          <div style={{ flex: 1, overflow: 'auto', padding: '8px 10px' }}>
            <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              🇨🇳 翻译
            </div>
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0', color: 'var(--mute)' }}>
                <Loader2 size={16} className="animate-spin" />
                <span style={{ fontSize: 13 }}>翻译中...</span>
              </div>
            ) : error ? (
              <div style={{ color: '#ef4444', fontSize: 12 }}>{error}</div>
            ) : (
              <div style={{
                fontSize: 13, color: 'var(--ink)', lineHeight: 1.7,
                whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}>
                {translation}
              </div>
            )}
            {/* 复制按钮 */}
            {translation && !loading && (
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 6 }}>
                <button
                  onClick={handleCopy}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '4px 10px', borderRadius: 6, border: 'none',
                    background: copied ? 'rgba(16,185,129,0.15)' : 'transparent',
                    color: copied ? '#10b981' : 'var(--mute, #888)',
                    cursor: 'pointer', fontSize: 10,
                  }}
                >
                  {copied ? <Check size={11} /> : <Copy size={11} />}
                  {copied ? '已复制' : '复制'}
                </button>
              </div>
            )}
          </div>

          {/* ── 写作工具栏 ── */}
          <div style={{ borderTop: '1px solid var(--hairline, #333)', padding: '6px 8px', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 10, color: 'var(--mute)', width: '100%', marginBottom: 2 }}>写作工具</span>
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
                  background: 'var(--sidebar-hover, rgba(255,255,255,0.05))',
                  border: '1px solid var(--hairline, #333)',
                  color: 'var(--body, #ccc)',
                  opacity: writingLoading ? 0.5 : 1,
                }}
              >
                <tool.icon size={11} />
                {tool.label}
              </button>
            ))}
            {writingResult && (
              <div style={{ width: '100%', marginTop: 4, padding: '6px 8px', borderRadius: 6, background: 'var(--sidebar-hover, rgba(255,255,255,0.05))', maxHeight: 100, overflow: 'auto' }}>
                <div style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span>结果</span>
                  <button onClick={async () => { await navigator.clipboard.writeText(writingResult); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', fontSize: 10 }}><Copy size={10} /> 复制</button>
                </div>
                <div style={{ fontSize: 12, color: 'var(--ink)', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {writingResult}
                </div>
              </div>
            )}
          </div>

          {/* ── AI 解释（折叠） ── */}
          <div style={{ borderTop: '1px solid var(--hairline, #333)' }}>
            <button
              onClick={() => {
                if (!showExplain) fetchExplanation();
                else setShowExplain(false);
              }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 12px', background: 'none', border: 'none',
                cursor: 'pointer', color: 'var(--mute)', fontSize: 12,
              }}
            >
              <span>AI 解释</span>
              {showExplain ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
            {showExplain && (
              <div style={{ padding: '0 12px 10px' }}>
                {explainLoading ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0', color: 'var(--mute)' }}>
                    <Loader2 size={14} className="animate-spin" />
                    <span style={{ fontSize: 12 }}>AI 思考中...</span>
                  </div>
                ) : (
                  <div style={{ fontSize: 12, color: 'var(--body)', lineHeight: 1.6, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                    {explanation}
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

const iconBtnStyle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  width: 22, height: 22, borderRadius: 4, border: 'none',
  background: 'transparent', color: 'var(--mute, #888)',
  cursor: 'pointer', padding: 0,
};

export default FloatingTranslate;
