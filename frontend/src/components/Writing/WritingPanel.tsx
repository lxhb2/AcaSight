import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  PenLine, Shrink, Sparkles, Languages, RefreshCw,
  Copy, Check, ChevronDown, Loader2, ArrowRight, BookOpen, Cpu, RefreshCcwDot,
  PenTool, LucideIcon,
} from 'lucide-react';
import { useAIModels } from '@/hooks/useAIModels';
import { useApp, usePanels } from '@/contexts/AppContext';
import { writingApi } from '@/services/api';

// ─── 类型 ───

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

// ─── 组件 ───

export const WritingPanel: React.FC = () => {
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

  // 同步 currentModel 到本地 state
  useEffect(() => { setSelectedModel(currentModel); }, [currentModel]);
  // 首次加载模型列表
  useEffect(() => { refreshModels(); }, []);

  const handleProcess = useCallback(async () => {
    const text = inputText.trim();
    if (!text) return;
    setIsProcessing(true);
    setOutputText('');
    setCopied(false);

    try {
      // 构建请求参数，附加模型信息
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
  }, [inputText, action, targetLang, context]);

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

  // CSS variables
  const borderColor = 'var(--color-border)';
  const cardBg = 'var(--color-card-bg)';

  return (
    <div className="h-full flex flex-col theme-transition" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      {/* Header */}
      <div className="p-5 pb-3" style={{ borderBottom: `1px solid ${borderColor}` }}>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold flex items-center gap-2" style={{ color: 'var(--color-text-primary)' }}>
            <PenLine size={24} /> 智能写作助手
          </h1>
          <div className="flex items-center gap-2">
            {/* 模型选择器 */}
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs" style={{ backgroundColor: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
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

        {/* Settings panel */}
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

      {/* Action selector */}
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

      {/* Content area */}
      <div className="flex-1 flex min-h-0 p-5 gap-4">
        {/* Input */}
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

        {/* Arrow */}
        <div className="flex items-center">
          <ArrowRight size={20} style={{ color: 'var(--color-text-muted)' }} />
        </div>

        {/* Output */}
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

