/**
 * AcaSight 文档管理 API 客户端
 * OnlyOffice 文档编辑器后端接口
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

/** 文档类型 */
export type FileType = 'docx' | 'xlsx' | 'pptx';

/** 文档信息 */
export interface Document {
  id: string;
  title: string;
  file_type: FileType;
  file_size: number;
  file_path: string;
  template_id: string | null;
  created_at: string;
  updated_at: string;
  onlyoffice_config?: OnlyOfficeConfig;
}

/** 文档版本 */
export interface DocumentVersion {
  version_id: string;
  document_id: string;
  version_num: number;
  created_at: string;
  file_size: number;
  changes: string | null;
}

/** 文档模板 */
export interface Template {
  id: string;
  name: string;
  description: string;
  file_type: FileType;
  thumbnail: string | null;
  created_at: string;
}

/** OnlyOffice 编辑器配置 */
export interface OnlyOfficeConfig {
  document: {
    fileType: string;
    key: string;
    title: string;
    url: string;
  };
  editorConfig: {
    mode: 'edit' | 'view';
    lang: string;
    callbackUrl: string;
    user?: {
      id: string;
      name: string;
    };
    customization?: Record<string, unknown>;
  };
  documentType: string;
  token?: string;
}

/** 文档列表响应 */
export interface DocumentListResponse {
  items: Document[];
  total: number;
}

// ==================== 文档管理 API ====================

export const documentApi = {
  /** 创建新文档 */
  createDocument: (title: string, fileType: FileType, templateId?: string) =>
    request<Document>('/documents', {
      method: 'POST',
      body: JSON.stringify({ title, file_type: fileType, template_id: templateId }),
    }),

  /** 获取文档列表 */
  listDocuments: (skip = 0, limit = 20, fileType?: FileType) => {
    const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    if (fileType) params.set('file_type', fileType);
    return request<DocumentListResponse>(`/documents?${params}`);
  },

  /** 获取文档详情（含 OnlyOffice 配置） */
  getDocument: (docId: string) =>
    request<Document>(`/documents/${docId}`),

  /** 更新文档 */
  updateDocument: (docId: string, data: Partial<Pick<Document, 'title'>>) =>
    request<Document>(`/documents/${docId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /** 删除文档 */
  deleteDocument: (docId: string) =>
    request<void>(`/documents/${docId}`, { method: 'DELETE' }),

  /** 获取文档版本列表 */
  getDocumentVersions: (docId: string) =>
    request<DocumentVersion[]>(`/documents/${docId}/versions`),

  /** 获取模板列表 */
  getTemplates: () =>
    request<Template[]>('/documents/templates'),

  /** 从模板创建文档 */
  createFromTemplate: (templateId: string, title: string) =>
    request<Document>('/documents/from-template', {
      method: 'POST',
      body: JSON.stringify({ template_id: templateId, title }),
    }),
};

// ==================== 格式转换 API ====================
// 后端路由挂载点: /api/convert/ （见 main.py: app.include_router(convert.router, prefix="/api/convert")）

export const convertApi = {
  /** Markdown 转 docx */
  mdToDocx: async (mdContent: string, templatePath?: string): Promise<Blob> => {
    const res = await fetch(`${BASE_URL}/convert/md-to-docx`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown: mdContent, template_path: templatePath }),
    });
    if (!res.ok) throw new Error('Markdown 转 docx 失败');
    return res.blob();
  },

  /** docx 转 Markdown */
  docxToMd: async (docxBase64: string): Promise<string> => {
    const res = await request<{ markdown: string }>('/convert/docx-to-md', {
      method: 'POST',
      body: JSON.stringify({ docx_base64: docxBase64 }),
    });
    return res.markdown;
  },

  /** Markdown 转 PDF */
  mdToPdf: async (mdContent: string, templatePath?: string): Promise<Blob> => {
    const res = await fetch(`${BASE_URL}/convert/md-to-pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown: mdContent, template_path: templatePath }),
    });
    if (!res.ok) throw new Error('Markdown 转 PDF 失败');
    return res.blob();
  },

  /** 获取转换模板列表 */
  getConvertTemplates: () =>
    request<Template[]>('/convert/templates'),
};

// ==================== 文档桥接 API ====================
// AI 写作台 ↔ Office 文档编辑器双向通信

/** 桥接 MD→Doc 响应 */
export interface BridgeMdToDocResult {
  id: string;
  title: string;
  file_type: string;
  file_path: string;
}

/** 桥接 Doc→MD 响应 */
export interface BridgeDocToMdResult {
  markdown: string;
  title: string;
}

export const bridgeApi = {
  /** Markdown → Office 文档（创建文档并写入转换后的内容） */
  bridgeMdToDoc: (
    markdown: string,
    title: string,
    fileType: 'docx' | 'xlsx' | 'pptx' = 'docx',
    templateId?: string,
    referenceDocx?: string,
  ) =>
    request<BridgeMdToDocResult>('/documents/bridge/md-to-doc', {
      method: 'POST',
      body: JSON.stringify({
        markdown,
        title,
        file_type: fileType,
        template_id: templateId,
        reference_docx: referenceDocx,
      }),
    }),

  /** Office 文档 → Markdown（提取文档内容为 Markdown） */
  bridgeDocToMd: (docId: string) =>
    request<BridgeDocToMdResult>('/documents/bridge/doc-to-md', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId }),
    }),

  /** 向文档插入章节 */
  bridgeInsertSection: (docId: string, content: string, position?: 'end' | 'cursor') =>
    request<{ success: boolean }>('/documents/bridge/insert-section', {
      method: 'POST',
      body: JSON.stringify({ doc_id: docId, content, position: position ?? 'end' }),
    }),
};
