/**
 * OnlyOffice Document Editor 连接器
 * 封装 OnlyOffice JavaScript API，提供 Promise 化的异步操作接口
 * 当 OnlyOffice 不可用时提供浏览器回退方案
 */

import type { OnlyOfficeConfig } from '@/services/documentService';

// OnlyOffice DocsAPI 全局类型声明
declare global {
  interface Window {
    DocsAPI?: {
      new (containerId: string, config: Record<string, unknown>): OnlyOfficeEditorInstance;
    };
  }
}

/** OnlyOffice 编辑器实例接口 */
interface OnlyOfficeEditorInstance {
  destroyEditor?: () => void;
  insertText?: (text: string) => void;
  setBookmark?: (name: string) => void;
  getSelectedText?: () => string;
  replaceTextSmart?: (text: string) => void;
}

/** 连接器配置 */
export interface ConnectorConfig {
  /** OnlyOffice Document Server 地址，如 http://localhost:8080 */
  serverUrl: string;
}

/** 编辑器事件回调 */
export interface EditorCallbacks {
  onReady?: () => void;
  onSave?: (data: { url: string }) => void;
  onError?: (error: { errorCode: number; errorDescription: string }) => void;
  onClose?: () => void;
  onDocumentChange?: () => void;
}

/** OnlyOffice 是否可用 */
let onlyOfficeAvailable = false;

/**
 * 动态加载 OnlyOffice API 脚本
 * @param serverUrl OnlyOffice Document Server 地址
 */
function loadOnlyOfficeScript(serverUrl: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.DocsAPI) {
      onlyOfficeAvailable = true;
      resolve();
      return;
    }

    const script = document.createElement('script');
    script.src = `${serverUrl}/web-apps/apps/api/documents/api.js`;
    script.async = true;
    script.onload = () => {
      onlyOfficeAvailable = !!window.DocsAPI;
      resolve();
    };
    script.onerror = () => {
      onlyOfficeAvailable = false;
      reject(new Error(`无法加载 OnlyOffice API: ${serverUrl}`));
    };
    document.head.appendChild(script);
  });
}

/**
 * OnlyOffice 连接器类
 * 封装编辑器初始化、文本操作、事件处理等
 */
export class OnlyOfficeConnector {
  private editorInstance: OnlyOfficeEditorInstance | null = null;
  private containerId: string | null = null;
  private callbacks: EditorCallbacks = {};
  private serverUrl: string;

  constructor(config: ConnectorConfig) {
    this.serverUrl = config.serverUrl;
  }

  /**
   * 初始化 OnlyOffice 编辑器
   * @param containerId 容器 div 的 id
   * @param config OnlyOffice 编辑器配置
   * @param callbacks 事件回调
   */
  async init(
    containerId: string,
    config: OnlyOfficeConfig,
    callbacks?: EditorCallbacks,
  ): Promise<void> {
    this.containerId = containerId;
    this.callbacks = callbacks || {};

    try {
      await loadOnlyOfficeScript(this.serverUrl);

      if (!window.DocsAPI) {
        throw new Error('OnlyOffice DocsAPI 不可用');
      }

      // 合并事件处理器到配置中
      const editorConfig: Record<string, unknown> = {
        ...config,
        events: {
          onAppReady: () => {
            this.callbacks.onReady?.();
          },
          onDocumentReady: () => {
            this.callbacks.onReady?.();
          },
          onSave: (event: { data: { url: string } }) => {
            this.callbacks.onSave?.({ url: event.data.url });
          },
          onError: (event: { data: { errorCode: number; errorDescription: string } }) => {
            this.callbacks.onError?.({
              errorCode: event.data.errorCode,
              errorDescription: event.data.errorDescription,
            });
          },
          onClose: () => {
            this.callbacks.onClose?.();
          },
          onDocumentChange: () => {
            this.callbacks.onDocumentChange?.();
          },
        },
      };

      this.editorInstance = new window.DocsAPI(containerId, editorConfig);
    } catch (error) {
      console.warn('OnlyOffice 初始化失败，使用回退模式:', error);
      onlyOfficeAvailable = false;
      this.callbacks.onError?.({
        errorCode: -1,
        errorDescription: error instanceof Error ? error.message : '初始化失败',
      });
    }
  }

  /** 销毁编辑器实例 */
  destroy(): void {
    if (this.editorInstance) {
      try {
        this.editorInstance.destroyEditor?.();
      } catch {
        // 忽略销毁错误
      }
      this.editorInstance = null;
    }

    // 清理容器 DOM
    if (this.containerId) {
      const container = document.getElementById(this.containerId);
      if (container) {
        container.innerHTML = '';
      }
    }
  }

  /** 在光标位置或指定位置插入文本 */
  async insertText(text: string, _position?: number): Promise<void> {
    if (!onlyOfficeAvailable || !this.editorInstance) {
      console.warn('[OnlyOffice 回退] insertText:', text);
      return;
    }
    this.editorInstance.insertText?.(text);
  }

  /** 获取当前选中的文本 */
  async getSelectedText(): Promise<string> {
    if (!onlyOfficeAvailable || !this.editorInstance) {
      console.warn('[OnlyOffice 回退] getSelectedText');
      return '';
    }
    return this.editorInstance.getSelectedText?.() || '';
  }

  /** 替换当前选中的文本 */
  async replaceSelection(text: string): Promise<void> {
    if (!onlyOfficeAvailable || !this.editorInstance) {
      console.warn('[OnlyOffice 回退] replaceSelection:', text);
      return;
    }
    this.editorInstance.replaceTextSmart?.(text);
  }

  /** 获取文档完整内容（OnlyOffice 不直接支持，需通过后端） */
  async getDocumentContent(): Promise<string> {
    if (!onlyOfficeAvailable) {
      console.warn('[OnlyOffice 回退] getDocumentContent');
      return '';
    }
    // OnlyOffice JS API 不直接提供获取全文的方法
    // 需要通过后端 API 获取文档内容
    return '';
  }

  /** 在当前位置设置书签 */
  async setBookmark(name: string): Promise<void> {
    if (!onlyOfficeAvailable || !this.editorInstance) {
      console.warn('[OnlyOffice 回退] setBookmark:', name);
      return;
    }
    this.editorInstance.setBookmark?.(name);
  }

  /** OnlyOffice 是否可用 */
  isAvailable(): boolean {
    return onlyOfficeAvailable;
  }
}

/**
 * 创建 OnlyOffice 连接器实例
 * @param serverUrl OnlyOffice Document Server 地址
 */
export function createOnlyOfficeConnector(serverUrl: string): OnlyOfficeConnector {
  return new OnlyOfficeConnector({ serverUrl });
}

/**
 * 检测 OnlyOffice 服务是否可用
 * @param serverUrl OnlyOffice Document Server 地址
 */
export async function checkOnlyOfficeAvailability(serverUrl: string): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(`${serverUrl}/healthcheck`, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    return false;
  }
}
