/**
 * 文档桥接 Store — AI 写作台 ↔ Office 文档编辑器双向通信
 * 支持 Markdown→Office、Office→Markdown、插入章节、格式转换等跨面板操作
 */

import { create } from 'zustand';
import { bridgeApi } from '@/services/documentService';

/** 桥接消息类型 */
export interface BridgeMessage {
  id: string;
  type: 'md-to-office' | 'office-to-md' | 'insert-section' | 'open-convert';
  payload: {
    markdown?: string;
    docId?: string;
    title?: string;
    fileType?: 'docx' | 'xlsx' | 'pptx';
    sectionContent?: string;
    sectionTitle?: string;
    sourceFormat?: 'markdown' | 'docx';
    targetFormat?: 'docx' | 'pdf' | 'markdown';
  };
  timestamp: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result?: {
    docId?: string;
    markdown?: string;
    title?: string;
  };
  error?: string;
}

interface DocumentBridgeState {
  /** 桥接消息列表 */
  messages: BridgeMessage[];
  /** 当前活跃文档 ID */
  activeDocId: string | null;

  // ── Actions ──

  /** 发送 Markdown 到 Office 编辑器（MD→docx 转换 + 创建文档） */
  sendToOffice: (markdown: string, title: string, fileType?: 'docx' | 'xlsx' | 'pptx') => string;
  /** 从 Office 文档提取 Markdown */
  extractFromOffice: (docId: string) => string;
  /** 向文档插入章节 */
  insertSection: (docId: string, content: string, sectionTitle?: string) => string;
  /** 打开格式转换对话框 */
  openConvertDialog: (sourceContent: string, sourceFormat: 'markdown' | 'docx') => string;
  /** 更新消息状态 */
  updateMessage: (id: string, update: Partial<BridgeMessage>) => void;
  /** 移除消息 */
  removeMessage: (id: string) => void;
  /** 设置当前活跃文档 */
  setActiveDocId: (docId: string | null) => void;
  /** 清空所有消息 */
  clearMessages: () => void;
}

/** 生成唯一 ID */
function genId(): string {
  return `bridge-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export const useDocumentBridgeStore = create<DocumentBridgeState>((set, get) => ({
  messages: [],
  activeDocId: null,

  sendToOffice: (markdown, title, fileType = 'docx') => {
    const id = genId();
    const msg: BridgeMessage = {
      id,
      type: 'md-to-office',
      payload: { markdown, title, fileType },
      timestamp: Date.now(),
      status: 'processing',
    };

    set(s => ({ messages: [...s.messages, msg] }));

    // 异步调用后端桥接 API
    bridgeApi
      .bridgeMdToDoc(markdown, title, fileType)
      .then(result => {
        get().updateMessage(id, {
          status: 'completed',
          result: { docId: result.id, title: result.title },
        });
        get().setActiveDocId(result.id);
      })
      .catch((err: unknown) => {
        const errMsg = err instanceof Error ? err.message : '发送到 Office 失败';
        get().updateMessage(id, { status: 'failed', error: errMsg });
      });

    return id;
  },

  extractFromOffice: (docId) => {
    const id = genId();
    const msg: BridgeMessage = {
      id,
      type: 'office-to-md',
      payload: { docId },
      timestamp: Date.now(),
      status: 'processing',
    };

    set(s => ({ messages: [...s.messages, msg] }));

    // 异步调用后端桥接 API
    bridgeApi
      .bridgeDocToMd(docId)
      .then(result => {
        get().updateMessage(id, {
          status: 'completed',
          result: { markdown: result.markdown, title: result.title },
        });
      })
      .catch((err: unknown) => {
        const errMsg = err instanceof Error ? err.message : '提取 Markdown 失败';
        get().updateMessage(id, { status: 'failed', error: errMsg });
      });

    return id;
  },

  insertSection: (docId, content, sectionTitle) => {
    const id = genId();
    const msg: BridgeMessage = {
      id,
      type: 'insert-section',
      payload: { docId, sectionContent: content, sectionTitle },
      timestamp: Date.now(),
      status: 'processing',
    };

    set(s => ({ messages: [...s.messages, msg] }));

    bridgeApi
      .bridgeInsertSection(docId, content)
      .then(() => {
        get().updateMessage(id, { status: 'completed' });
      })
      .catch((err: unknown) => {
        const errMsg = err instanceof Error ? err.message : '插入章节失败';
        get().updateMessage(id, { status: 'failed', error: errMsg });
      });

    return id;
  },

  openConvertDialog: (sourceContent, sourceFormat) => {
    const id = genId();
    const msg: BridgeMessage = {
      id,
      type: 'open-convert',
      payload: { markdown: sourceContent, sourceFormat },
      timestamp: Date.now(),
      status: 'pending',
    };

    set(s => ({ messages: [...s.messages, msg] }));
    return id;
  },

  updateMessage: (id, update) => {
    set(s => ({
      messages: s.messages.map(m => (m.id === id ? { ...m, ...update } : m)),
    }));
  },

  removeMessage: (id) => {
    set(s => ({ messages: s.messages.filter(m => m.id !== id) }));
  },

  setActiveDocId: (docId) => {
    set({ activeDocId: docId });
  },

  clearMessages: () => {
    set({ messages: [] });
  },
}));
