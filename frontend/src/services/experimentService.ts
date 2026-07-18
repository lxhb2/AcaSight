/**
 * AcaSight 实验笔记本 API 客户端 — Feature 6.6
 *
 * 与后端 /api/experiments 通信，提供实验 CRUD、条目管理、关联链接管理。
 */

const BASE_URL = '/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData;
  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  if (options?.headers) {
    Object.assign(headers, options.headers as Record<string, string>);
  }
  const res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err);
    throw new Error(msg || `HTTP ${res.status}`);
  }
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return res.json();
  }
  return res as unknown as T;
}

// ==================== 类型定义 ====================

/** 实验状态 */
export type ExperimentStatus = 'planning' | 'running' | 'completed' | 'failed';

/** 条目类型 */
export type EntryType = 'text' | 'data' | 'table' | 'image' | 'procedure';

/** 链接类型 */
export type LinkedType = 'literature' | 'document' | 'chart';

/** 实验信息 */
export interface ExperimentItem {
  id: string;
  title: string;
  description: string;
  category: string;
  status: ExperimentStatus;
  created_at: string | null;
  updated_at: string | null;
  metadata_json: Record<string, unknown>;
  entries?: ExperimentEntryItem[];
  links?: ExperimentLinkItem[];
}

/** 实验条目 */
export interface ExperimentEntryItem {
  id: string;
  experiment_id: string;
  entry_type: EntryType;
  content: Record<string, unknown>;
  created_at: string | null;
  tags: string[];
}

/** 实验关联链接 */
export interface ExperimentLinkItem {
  id: string;
  experiment_id: string;
  linked_type: LinkedType;
  linked_id: string;
  note: string;
  created_at: string | null;
}

/** 实验列表响应 */
export interface ExperimentListResponse {
  success: boolean;
  data: ExperimentItem[];
  total: number;
  limit: number;
  offset: number;
}

// ==================== API ====================

export const experimentApi = {
  /** 创建实验 */
  create: (data: {
    title: string;
    description?: string;
    category?: string;
    status?: ExperimentStatus;
    metadata_json?: Record<string, unknown>;
  }) =>
    request<{ success: boolean; data: ExperimentItem }>('/experiments/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 列出实验 */
  list: (params?: {
    category?: string;
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const p = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) p.set(k, String(v));
      });
    }
    return request<ExperimentListResponse>(`/experiments/?${p}`);
  },

  /** 获取实验详情（含条目和链接） */
  get: (expId: string) =>
    request<{ success: boolean; data: ExperimentItem }>(`/experiments/${expId}`),

  /** 更新实验 */
  update: (expId: string, data: {
    title?: string;
    description?: string;
    category?: string;
    status?: ExperimentStatus;
    metadata_json?: Record<string, unknown>;
  }) =>
    request<{ success: boolean; data: ExperimentItem }>(`/experiments/${expId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** 删除实验 */
  delete: (expId: string) =>
    request<{ success: boolean; message: string }>(`/experiments/${expId}`, {
      method: 'DELETE',
    }),

  // ── 条目管理 ──

  /** 添加实验条目 */
  addEntry: (expId: string, data: {
    entry_type: EntryType;
    content?: Record<string, unknown>;
    tags?: string[];
  }) =>
    request<{ success: boolean; data: ExperimentEntryItem }>(`/experiments/${expId}/entries`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 更新实验条目 */
  updateEntry: (expId: string, entryId: string, data: {
    entry_type?: EntryType;
    content?: Record<string, unknown>;
    tags?: string[];
  }) =>
    request<{ success: boolean; data: ExperimentEntryItem }>(`/experiments/${expId}/entries/${entryId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** 删除实验条目 */
  deleteEntry: (expId: string, entryId: string) =>
    request<{ success: boolean; message: string }>(`/experiments/${expId}/entries/${entryId}`, {
      method: 'DELETE',
    }),

  // ── 关联链接管理 ──

  /** 添加关联链接 */
  addLink: (expId: string, data: {
    linked_type: LinkedType;
    linked_id: string;
    note?: string;
  }) =>
    request<{ success: boolean; data: ExperimentLinkItem }>(`/experiments/${expId}/links`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 获取实验的所有关联链接 */
  getLinks: (expId: string) =>
    request<{
      success: boolean;
      data: {
        all: ExperimentLinkItem[];
        grouped: Record<LinkedType, ExperimentLinkItem[]>;
      };
    }>(`/experiments/${expId}/links`),

  /** 删除关联链接 */
  deleteLink: (expId: string, linkId: string) =>
    request<{ success: boolean; message: string }>(`/experiments/${expId}/links/${linkId}`, {
      method: 'DELETE',
    }),
};
