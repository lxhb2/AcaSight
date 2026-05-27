import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, BookOpen, TrendingUp, Search, Loader2, Languages, FlaskConical, Cpu, RefreshCcwDot } from 'lucide-react';
import { aiApi, type ChatMessage } from '@/services/api';
import { MarkdownRenderer } from '@/components/Common/MarkdownRenderer';
import { useAIModels } from '@/hooks/useAIModels';

interface AISidePanelProps {
  selectedText?: string;
  pdfPath?: string;
  pdfTitle?: string;
  pdfFullText?: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export const AISidePanel: React.FC<AISidePanelProps> = ({
  selectedText,
  pdfPath,
  pdfTitle = '当前文献',
  pdfFullText
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { models, currentModel, loading: modelsLoading, refreshModels, selectModel } = useAIModels();
  const [selectedModel, setSelectedModel] = useState<string>('');

  useEffect(() => { setSelectedModel(currentModel); }, [currentModel]);
  useEffect(() => { refreshModels(); }, []);

  useEffect(() => {
    if (selectedText && selectedText.length > 10) {
      const preview = selectedText.length > 150
        ? `"${selectedText.substring(0, 150)}..."`
        : `"${selectedText}"`;
      setInput(`请解释这段文字: ${preview}`);
    }
  }, [selectedText]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (role: 'user' | 'assistant', content: string) => {
    const msg: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, msg]);
    return msg;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userQuery = input;
    addMessage('user', userQuery);
    setInput('');
    setIsLoading(true);

    const chatMessages: ChatMessage[] = [
      {
        role: 'system',
        content: pdfFullText
          ? `你是一位学术研究助手，正在帮助用户阅读一篇学术文献。

以下是文献全文（基于 PDF 文本提取）：
--- 文献全文开始 ---
${pdfFullText.slice(0, 12000)}
--- 文献全文结束 ---

请基于以上文献全文内容回答用户的问题。如果用户让你翻译某段内容，优先从全文查找对应原文。如果需要引用，请标注大致页码或段落位置。
如果用户的问题与这篇文献无关，也请正常回答。`
          : '你是学术研究助手，帮助用户理解文献、回答问题、翻译文本、总结内容等。'
      },
      ...messages.slice(-6).map(m => ({
        role: m.role as 'user' | 'assistant',
        content: m.content
      })),
      { role: 'user' as const, content: userQuery }
    ];

    try {
      // 使用 api.ts 封装，不传 provider → 后端使用 default_provider
      const result = await aiApi.chat(chatMessages.slice(-8), undefined, selectedModel);
      addMessage('assistant', result.response || '无响应');
    } catch (error: any) {
      console.error('AI 对话失败:', error);
      addMessage('assistant', `⚠️ 请求失败: ${error?.message || '未知错误'}\n\n请检查后端服务 (端口 18000) 和 AI 配置`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = async (actionId: string) => {
    if (isLoading) return;

    let prompt = '';
    switch (actionId) {
      case 'summarize':
        prompt = `请总结这篇文献的核心内容：${pdfTitle}`;
        break;
      case 'methods':
        prompt = `请分析这篇文献的研究方法：${pdfTitle}`;
        break;
      case 'gaps':
        prompt = `请指出这篇文献的研究空白和未来方向：${pdfTitle}`;
        break;
      case 'related':
        prompt = `请推荐与「${pdfTitle}」相关的重要文献`;
        break;
      case 'translate':
        if (selectedText) {
          prompt = `请将以下英文翻译成中文：\n\n${selectedText}`;
        } else {
          prompt = '请选中需要翻译的文本后点击此按钮';
        }
        break;
      case 'deep-read':
        if (pdfPath) {
          prompt = `请对当前文献进行 AI 精读分析`;
        } else {
          prompt = '请先打开一篇 PDF 文献';
        }
        break;
      case 'experiment':
        prompt = `请基于当前文献的主题，帮我设计一个实验方案`;
        break;
      default:
        prompt = `请${actionId}`;
    }

    setInput(prompt);
    if (actionId !== 'translate' || selectedText) {
      setTimeout(() => {
        const sendBtn = document.querySelector('[data-send-btn]') as HTMLButtonElement;
        if (sendBtn) sendBtn.click();
      }, 100);
    }
  };

  const quickActions = [
    { id: 'summarize', label: '总结全文', icon: BookOpen },
    { id: 'methods', label: '研究方法', icon: Search },
    { id: 'gaps', label: '研究空白', icon: TrendingUp },
    { id: 'deep-read', label: 'AI精读', icon: Sparkles },
    { id: 'translate', label: '翻译选文', icon: Languages },
    { id: 'experiment', label: '实验设计', icon: FlaskConical },
  ];

  const borderColor = 'var(--color-border)';
  const userBg = 'var(--color-primary)';
  const assistantBg = 'var(--color-bg-tertiary)';
  const inputBg = 'var(--color-bg-tertiary)';
  const quickBtnBg = 'var(--color-bg-tertiary)';

  return (
    <div className="flex flex-col h-full">
      {/* Model selector header */}
      <div className="px-3 pt-2 pb-1 border-b theme-transition flex items-center gap-2" style={{ borderColor: borderColor }}>
        <div className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)' }}>
          <Cpu size={10} style={{ color: 'var(--color-text-muted)' }} />
          <select
            value={selectedModel}
            onChange={(e) => { setSelectedModel(e.target.value); selectModel(e.target.value); }}
            className="outline-none text-xs bg-transparent"
            style={{ color: 'var(--color-text-primary)', maxWidth: 140 }}
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
            <RefreshCcwDot size={10} className={modelsLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>
      <div className="p-3 border-b theme-transition" style={{ borderColor: borderColor }}>
        <div className="grid grid-cols-3 gap-2">
          {quickActions.map((action) => (
            <button
              key={action.id}
              onClick={() => handleQuickAction(action.id)}
              className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg transition-colors text-xs"
              style={{
                backgroundColor: quickBtnBg,
                color: 'var(--color-text-secondary)',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.backgroundColor = 'var(--color-bg-hover)';
                e.currentTarget.style.color = 'var(--color-text-primary)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = quickBtnBg;
                e.currentTarget.style.color = 'var(--color-text-secondary)';
              }}
            >
              <action.icon size={12} />
              {action.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-4">
        {messages.length === 0 && (
          <div className="text-center mt-8" style={{ color: 'var(--color-text-muted)' }}>
            <Sparkles size={32} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">点击快捷功能或输入问题</p>
            <p className="text-xs mt-1">AI 助手会帮助您理解文献</p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="max-w-[90%] rounded-lg px-3 py-2 text-sm"
              style={{
                backgroundColor: message.role === 'user' ? userBg : assistantBg,
                color: message.role === 'user' ? '#ffffff' : 'var(--color-text-primary)',
              }}
            >
              {message.role === 'assistant' ? (
                <MarkdownRenderer content={message.content} />
              ) : (
                <span className="whitespace-pre-wrap">{message.content}</span>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--color-text-muted)' }}>
            <Loader2 size={14} className="animate-spin" />
            AI 思考中...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="p-3 border-t theme-transition" style={{ borderColor: borderColor }}>
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入问题..."
            className="flex-1 rounded-lg px-3 py-2 text-sm outline-none transition-colors"
            style={{
              backgroundColor: inputBg,
              border: `1px solid ${borderColor}`,
              color: 'var(--color-text-primary)',
            }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            data-send-btn
            className="px-3 py-2 rounded-lg disabled:opacity-50 transition-colors"
            style={{ backgroundColor: 'var(--color-primary)', color: '#ffffff' }}
            onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'var(--color-primary-hover)'; }}
            onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'var(--color-primary)'; }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};