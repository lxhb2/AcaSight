/**
 * agentStore — 跨面板共享 Agent 状态
 * 
 * 让 AgentPanel 和 ContextualAgentBar 共享：
 * - 会话历史（同一 conversation_id 延续对话）
 * - 当前上下文（用户正在看什么）
 * - 运行状态（避免冲突）
 * - SSE 流式发送逻辑
 * - 多会话管理（列表/切换/删除/加载）
 */

import { create } from 'zustand';

const BASE_URL = 'http://localhost:9000/api';

// ==================== Types ====================

// ==================== 智能 PDF 截断 ====================

const STOP_WORDS = new Set([
  '的','了','在','是','我','有','和','就','不','人','都','一',
  '上','也','很','到','说','要','去','你','会','着','没有','看','好','自己','这',
  'the','a','an','is','are','was','were','be','been','being','have','has','had',
  'do','does','did','will','would','shall','should','may','might','must','can','could',
  'of','to','in','for','on','with','at','by','from','as','into','through','during',
  'and','or','not','but','if','than','then','so','that','this','these','those',
  'it','its','they','them','their','we','us','our','he','she','him','her','his',
]);

function selectRelevantChunks(fullText: string, query: string, maxTotalChars: number = 20000): string {
  // 按段落切分
  const paragraphs = fullText.split(/\n\s*\n/).filter(p => p.trim().length > 10);
  if (paragraphs.length <= 1) return fullText.slice(0, maxTotalChars);

  // 构建 chunk（约 2000 字符/块，尊重段落边界）
  const CHUNK_SIZE = 2000;
  const chunks: string[] = [];
  let currentChunk = '';
  for (const para of paragraphs) {
    if (currentChunk.length + para.length < CHUNK_SIZE) {
      currentChunk += (currentChunk ? '\n\n' : '') + para;
    } else {
      if (currentChunk) chunks.push(currentChunk);
      currentChunk = para;
    }
  }
  if (currentChunk) chunks.push(currentChunk);
  if (chunks.length <= 1) return fullText.slice(0, maxTotalChars);

  // 提取查询关键词
  const queryWords = query
    .split(/[\s,，。！？、；：""''（）\(\)\[\]【】\{\}…\-—/@#$%\^&\*\+=|~`·\\]+/)
    .map(w => w.toLowerCase().trim())
    .filter(w => w.length > 1 && !STOP_WORDS.has(w));

  if (queryWords.length === 0) return fullText.slice(0, maxTotalChars);

  // 按关键词命中数评分
  const scored = chunks.map((chunk, idx) => {
    const lowerChunk = chunk.toLowerCase();
    let score = 0;
    for (const word of queryWords) {
      const escaped = word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const matches = lowerChunk.match(new RegExp(escaped, 'g'));
      score += matches ? matches.length : 0;
    }
    return { idx, score, chunk };
  });

  // 无匹配 → 取开头
  if (scored.every(s => s.score === 0)) return fullText.slice(0, maxTotalChars);

  // 按相关性排序，选取最相关 block
  scored.sort((a, b) => b.score - a.score);
  const selected: string[] = [];
  let totalLen = 0;
  for (const { chunk } of scored) {
    if (totalLen + chunk.length > maxTotalChars) break;
    selected.push(chunk);
    totalLen += chunk.length + 4;
  }

  if (selected.length === 0) return scored[0].chunk.slice(0, maxTotalChars);
  return selected.join('\n\n───\n\n');
}


export interface AgentStep {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'answer' | 'error' | 'meta';
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  timestamp: number;
}

export interface AgentMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  steps: AgentStep[];
  timestamp: Date;
}

export interface PanelContext {
  panelId: string;
  title?: string;
  selectedText?: string;
  pdfText?: string;
  pdfFullText?: string;
  sectionType?: string;
  searchQuery?: string;
}

export interface SessionInfo {
  conversation_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  preview: string;
}

// ==================== Store ====================

interface AgentStore {
  messages: AgentMessage[];
  conversationId: string | null;
  isRunning: boolean;
  currentContext: PanelContext | null;

  sessions: SessionInfo[];
  sessionsLoading: boolean;

  setContext: (ctx: PanelContext) => void;
  clearMessages: () => void;
  loadSessions: () => Promise<void>;
  switchSession: (conversationId: string) => Promise<void>;
  deleteSession: (conversationId: string) => Promise<void>;
  newSession: () => void;

  sendTask: (task: string) => Promise<void>;
}

export const useAgentStore = create<AgentStore>((set, get) => ({
  messages: [],
  conversationId: null,
  isRunning: false,
  currentContext: null,
  sessions: [],
  sessionsLoading: false,

  setContext: (ctx) => set({ currentContext: ctx }),

  clearMessages: () => set({ messages: [], conversationId: null }),

  loadSessions: async () => {
    set({ sessionsLoading: true });
    try {
      const res = await fetch(`${BASE_URL}/agent/sessions`);
      const data = await res.json();
      set({ sessions: data.sessions || [], sessionsLoading: false });
    } catch {
      set({ sessionsLoading: false });
    }
  },

  switchSession: async (conversationId: string) => {
    try {
      const res = await fetch(`${BASE_URL}/agent/sessions/${conversationId}`);
      const data = await res.json();
      const loadedMessages: AgentMessage[] = [];
      const rawMessages = data.messages || [];
      for (const m of rawMessages) {
        const id = `${m.role}-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
        if (m.role === 'user') {
          loadedMessages.push({
            id,
            role: 'user',
            content: m.content || '',
            steps: [],
            timestamp: new Date(),
          });
        } else if (m.role === 'assistant') {
          const content = m.content || '';
          const isErr = content.startsWith('[错误]');
          loadedMessages.push({
            id,
            role: 'agent',
            content: isErr ? '' : content,
            steps: isErr
              ? [{ type: 'error', content: content.slice(4), timestamp: Date.now() }]
              : content
                ? [{ type: 'answer', content, timestamp: Date.now() }]
                : [],
            timestamp: new Date(),
          });
        }
      }
      set({
        messages: loadedMessages,
        conversationId,
      });
    } catch {
      // ignore
    }
  },

  deleteSession: async (conversationId: string) => {
    try {
      await fetch(`${BASE_URL}/agent/sessions/${conversationId}`, { method: 'DELETE' });
    } catch {
      // ignore
    }
    const state = get();
    set({
      sessions: state.sessions.filter(s => s.conversation_id !== conversationId),
    });
    if (state.conversationId === conversationId) {
      set({ messages: [], conversationId: null });
    }
  },

  newSession: () => set({ messages: [], conversationId: null }),

  sendTask: async (task: string) => {
    const state = get();
    if (!task.trim() || state.isRunning) return;

    const userMsg: AgentMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: task,
      steps: [],
      timestamp: new Date(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isRunning: true }));

    const agentId = `agent-${Date.now()}`;
    const agentMsg: AgentMessage = {
      id: agentId,
      role: 'agent',
      content: '',
      steps: [],
      timestamp: new Date(),
    };
    set((s) => ({ messages: [...s.messages, agentMsg] }));

    const ctx = get().currentContext;

    try {
      const response = await fetch(`${BASE_URL}/agent/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task,
          context: {
            pdf_title: ctx?.title,
            selected_text: ctx?.selectedText,
            pdf_full_text: ctx?.pdfFullText
              ? selectRelevantChunks(ctx.pdfFullText, task, 20000)
              : undefined,
            pdf_text_truncated: ctx?.pdfFullText && ctx.pdfFullText.length > 20000 ? true : undefined,
            section_type: ctx?.sectionType,
            _bundle: ctx?.panelId === 'search' ? 'search' : undefined,
          },
          conversation_id: get().conversationId,
        }),
      });

      if (!response.ok || !response.body) throw new Error('Agent request failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
            continue;
          }
          if (!line.startsWith('data: ')) continue;

          const raw = line.slice(6);
          let data: Record<string, unknown>;
          try {
            data = JSON.parse(raw);
          } catch {
            continue;
          }

          const eventType = currentEvent || (data.type as string) || 'thinking';
          currentEvent = '';

          if (eventType === 'meta') {
            if (data.conversation_id) {
              set({ conversationId: data.conversation_id as string });
            }
            continue;
          }

          if (eventType === 'done') {
            get().loadSessions();
            continue;
          }

          const step: AgentStep = {
            type: eventType as AgentStep['type'],
            content: data.content as string | undefined,
            name: data.name as string | undefined,
            args: data.args as Record<string, unknown> | undefined,
            result: data.result as string | undefined,
            timestamp: Date.now(),
          };

          if (step.type === 'answer') {
            set((s) => ({
              messages: s.messages.map((m) =>
                m.id === agentId ? { ...m, content: data.content as string, steps: [...m.steps, step] } : m
              ),
            }));
          } else {
            set((s) => ({
              messages: s.messages.map((m) =>
                m.id === agentId ? { ...m, steps: [...m.steps, step] } : m
              ),
            }));
          }
        }
      }
    } catch (err: unknown) {
      const errorStep: AgentStep = {
        type: 'error',
        content: err instanceof Error ? err.message : '请求失败',
        timestamp: Date.now(),
      };
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === agentId ? { ...m, steps: [...m.steps, errorStep] } : m
        ),
      }));
    } finally {
      set({ isRunning: false });
    }
  },
}));
