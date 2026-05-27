/**
 * AcaSight API 客户端
 * 与后端 FastAPI (http://localhost:8000/api) 通信
 */

const BASE_URL = 'http://localhost:9000/api';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const contentType = res.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return res.json();
  }
  return res as unknown as T;
}

// ==================== PDF API ====================

export interface PDFInfo {
  filename: string;
  pages: number;
  metadata: Record<string, string>;
  file_size: number;
  toc: Array<{ level: number; title: string; page: number }>;
  is_encrypted?: boolean;
}

export interface PDFText {
  filename?: string;
  pages: number;
  text: string;
  pages_text: Array<{ page: number; text: string }>;
}

export interface PDFReading {
  title: string;
  page_count: number;
  text: string;
  truncated: boolean;
}

export interface SearchMatch {
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export const pdfApi = {
  /** 上传 PDF */
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${BASE_URL}/pdf/upload`, { method: 'POST', body: form }).then(r => r.json());
  },

  /** 获取 PDF 信息 */
  info: (path: string) => request<PDFInfo>(`/pdf/${encodeURIComponent(path)}/info`),

  /** 提取全文文本 */
  text: (path: string, page?: number) => {
    let url = `/pdf/${encodeURIComponent(path)}/text`;
    if (page) url += `?page=${page}`;
    return request<PDFText>(url);
  },

  /** 提取用于 AI 精读的内容 */
  reading: (path: string, maxChars = 8000) =>
    request<PDFReading>(`/pdf/${encodeURIComponent(path)}/reading?max_chars=${maxChars}`),

  /** 获取 PDF 目录 */
  toc: (path: string) =>
    request<{ toc: Array<{ level: number; title: string; page: number }> }>(`/pdf/${encodeURIComponent(path)}/toc`),

  /** 计算 PDF SHA256 哈希（用于批注关联）*/
  hash: (url: string) =>
    request<{ hash: string; size: number }>(`/pdf/hash?url=${encodeURIComponent(url)}`),

  /** 在 PDF 中搜索文本 */
  search: (path: string, query: string) =>
    request<{ query: string; count: number; matches: SearchMatch[] }>('/pdf/search', {
      method: 'POST',
      body: JSON.stringify({ file_path: path, query }),
    }),

  /** 渲染页面为图片（返回 base64）*/
  pageImage: async (path: string, pageNum: number, zoom = 1.5): Promise<string> => {
    const res = await fetch(
      `${BASE_URL}/pdf/${encodeURIComponent(path)}/page/${pageNum}/image?zoom=${zoom}`
    );
    if (!res.ok) throw new Error('Failed to load page image');
    const blob = await res.blob();
    return URL.createObjectURL(blob);
  },

  /** 合并 PDF */
  merge: (paths: string[]) =>
    request<{ output: string; filename: string }>('/pdf/merge', {
      method: 'POST',
      body: JSON.stringify({ file_paths: paths }),
    }),

  /** 拆分 PDF */
  split: (path: string, pagesPerFile = 1) =>
    request<{ outputs: string[]; count: number }>('/pdf/split', {
      method: 'POST',
      body: JSON.stringify({ file_path: path, pages_per_file: pagesPerFile }),
    }),

  /** 旋转 */
  rotate: (path: string, rotation = 90) =>
    request<{ output: string; filename: string }>('/pdf/rotate', {
      method: 'POST',
      body: JSON.stringify({ file_path: path, rotation }),
    }),

  /** 水印 */
  watermark: (path: string, text: string, opacity = 0.3) =>
    request<{ output: string; filename: string }>('/pdf/watermark', {
      method: 'POST',
      body: JSON.stringify({ file_path: path, text, opacity }),
    }),

  /** 提取图片 */
  extractImages: (path: string) =>
    request<{ images: Array<{ page: number; index: number; format: string; width: number; height: number; path: string }>; count: number }>(
      `/pdf/${encodeURIComponent(path)}/images`
    ),

  /** 下载处理后的文件 */
  downloadUrl: (filename: string) => `${BASE_URL}/pdf/download/${filename}`,
};

// ==================== AI API ====================

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export const aiApi = {
  /** AI 对话（非流式）*/
  chat: (messages: ChatMessage[], provider?: string, model?: string) =>
    request<{ response: string }>('/chat/', {
      method: 'POST',
      body: JSON.stringify({ messages, provider, model }),
    }),

  /** AI 对话（流式）*/
  chatStream: async function* (messages: ChatMessage[], provider?: string, model?: string): AsyncGenerator<string> {
    const res = await fetch(`${BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, provider, model }),
    });
    const reader = res.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const text = decoder.decode(value);
      // SSE 格式解析
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          yield line.slice(6);
        }
      }
    }
  },

  /** AI 精读 */
  deepRead: (pdfPath: string, title: string) =>
    request<{ analysis: string }>('/chat/deep-read', {
      method: 'POST',
      body: JSON.stringify({ pdf_path: pdfPath, title }),
    }),

  /** 生成文献综述 */
  literatureReview: (papers: Array<{ title: string; authors: string[]; year: string; abstract: string }>, topic: string, instruction?: string) =>
    request<{ review: string }>('/chat/literature-review', {
      method: 'POST',
      body: JSON.stringify({ papers, topic, extra_instruction: instruction }),
    }),

  /** 实验设计 */
  experimentDesign: (topic: string, goal: string, method: string) =>
    request<{ design: string }>('/chat/experiment-design', {
      method: 'POST',
      body: JSON.stringify({ topic, goal, method }),
    }),

  /** 生成公式 */
  formula: (description: string) =>
    request<{ formula: string }>('/chat/formula', {
      method: 'POST',
      body: JSON.stringify({ description }),
    }),

  /** 生成摘要 */
  summary: (text: string, maxLength = 500) =>
    request<{ summary: string }>('/chat/summarize', {
      method: 'POST',
      body: JSON.stringify({ text, max_length: maxLength }),
    }),

  /** 翻译 */
  translate: (text: string, target = 'zh') =>
    request<{ translation: string }>('/chat/translate', {
      method: 'POST',
      body: JSON.stringify({ text, target_language: target }),
    }),

  /** 论文大纲 */
  outline: (topic: string, refs: Array<{ title: string; year: string }>, instructions?: string) =>
    request<{ outline: string }>('/chat/outline', {
      method: 'POST',
      body: JSON.stringify({ topic, refs, instructions }),
    }),

  /** 生成论文章节 */
  section: (topic: string, sectionTitle: string, outline: string, refs: Array<{ title: string; year: string }>, content: string, instructions?: string) =>
    request<{ content: string }>('/chat/section', {
      method: 'POST',
      body: JSON.stringify({ topic, section_title: sectionTitle, outline, refs, section_content: content, instructions }),
    }),
};

// ==================== Search API ====================

export const searchApi = {
  search: (q: string, sources?: string[], limit = 20, yearFrom?: number, yearTo?: number) => {
    const params = new URLSearchParams({ q, limit: String(limit) });
    if (sources?.length) {
      for (const s of sources) params.append('sources', s);
    } else {
      // default: all sources
      for (const s of ['core','openalex','semanticscholar','crossref','europepmc','arxiv']) {
        params.append('sources', s);
      }
    }
    if (yearFrom) params.set('year_from', String(yearFrom));
    if (yearTo) params.set('year_to', String(yearTo));
    return request<{ query: string; sources: string[]; results: Record<string, any> }>(
      `/search/?${params}`
    );
  },

  byDOI: (doi: string) => request<any>(`/search/doi/${encodeURIComponent(doi)}`),

  coreSearch: (params: { q: string; title?: string; authors?: string; journal?: string; year_from?: number; year_to?: number; fulltext?: string; limit?: number; offset?: number }) =>
    request<{ totalHits: number; results: any[] }>('/search/core', { method: 'POST', body: JSON.stringify(params) }),

  coreDiscover: (params: { doi?: string; title?: string; year?: number }) =>
    request<{ fullTextLink: string; source: string }>('/search/core/discover', { method: 'POST', body: JSON.stringify(params) }),

  sources: () => request<{ sources: Array<{ id: string; name: string; description: string; url: string }> }>('/search/sources'),
};

// ==================== AI Config API ====================

export const aiConfigApi = {
  getConfig: () => request<any>('/ai/config'),

  saveConfig: (config: { default_provider?: string; default_model?: string; providers?: Record<string, any> }) =>
    request<any>('/ai/config', { method: 'POST', body: JSON.stringify(config) }),

  testProvider: (params: { provider: string; base_url?: string; api_key?: string; model?: string }) =>
    request<{ connected: boolean; models?: string[]; error?: string }>('/ai/test', { method: 'POST', body: JSON.stringify(params) }),

  getProviders: () => request<{ providers: Array<{ id: string; enabled: boolean; base_url: string; has_api_key: boolean }> }>('/ai/providers'),

  getModels: (provider: string) => request<{ models: string[] }>(`/ai/models/${provider}`),
};

// ==================== Papers API ====================

export interface PaperItem {
  id: number;
  title: string;
  authors: string[];
  abstract: string | null;
  doi: string | null;
  pmid: string | null;
  arxiv_id: string | null;
  openalex_id: string | null;
  semanticscholar_id: string | null;
  journal: string | null;
  year: number | null;
  volume: string | null;
  issue: string | null;
  pages: string | null;
  publisher: string | null;
  pdf_path: string | null;
  file_size: number | null;
  page_count: number | null;
  keywords: string[];
  tags: string[];
  extra_fields: Record<string, any>;
  citation_count: number;
  reference_count: number;
  is_favorite: number;
  read_status: 'unread' | 'reading' | 'read';
  rating: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface PaperListResponse {
  items: PaperItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface TagInfo {
  name: string;
  count: number;
}

export interface PaperStats {
  total: number;
  favorites: number;
  by_status: Record<string, number>;
  by_year: Record<string, number>;
}

export const papersApi = {
  /** 获取文献列表（分页+筛选+搜索）*/
  list: (params?: {
    page?: number; page_size?: number; sort_by?: string; sort_order?: string;
    tag?: string; read_status?: string; is_favorite?: number;
    year_from?: number; year_to?: number; search?: string;
  }) => {
    const p = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) p.set(k, String(v));
      });
    }
    return request<PaperListResponse>(`/papers?${p}`);
  },

  /** 搜索文献 */
  search: (q: string, limit?: number) =>
    request<{ query: string; results: PaperItem[]; count: number }>(`/papers/search?q=${encodeURIComponent(q)}&limit=${limit || 20}`),

  /** 获取单个文献 */
  get: (id: number) => request<PaperItem>(`/papers/${id}`),

  /** 创建文献 */
  create: (data: Partial<PaperItem> & { title: string }) =>
    request<PaperItem>('/papers', { method: 'POST', body: JSON.stringify(data) }),

  /** 批量导入 */
  batchImport: (papers: Partial<PaperItem> & { title: string }[]) =>
    request<{ imported: number; papers: PaperItem[] }>('/papers/batch', {
      method: 'POST', body: JSON.stringify({ papers }),
    }),

  /** 更新文献 */
  update: (id: number, data: Partial<PaperItem>) =>
    request<PaperItem>(`/papers/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** 删除文献 */
  delete: (id: number) =>
    request<{ detail: string; id: number }>(`/papers/${id}`, { method: 'DELETE' }),

  /** 获取所有标签 */
  tags: () => request<{ tags: TagInfo[] }>('/papers/tags'),

  /** 更新标签 */
  updateTags: (id: number, tags: string[]) =>
    request<PaperItem>(`/papers/${id}/tags`, { method: 'PUT', body: JSON.stringify({ tags }) }),

  /** 添加标签 */
  addTag: (id: number, tagName: string) =>
    request<PaperItem>(`/papers/${id}/tags/${encodeURIComponent(tagName)}`, { method: 'POST' }),

  /** 移除标签 */
  removeTag: (id: number, tagName: string) =>
    request<PaperItem>(`/papers/${id}/tags/${encodeURIComponent(tagName)}`, { method: 'DELETE' }),

  /** 更新阅读状态 */
  updateReadStatus: (id: number, readStatus: string) =>
    request<PaperItem>(`/papers/${id}/read-status`, { method: 'PUT', body: JSON.stringify({ read_status: readStatus }) }),

  /** 更新评分 */
  updateRating: (id: number, rating: number) =>
    request<PaperItem>(`/papers/${id}/rating`, { method: 'PUT', body: JSON.stringify({ rating }) }),

  /** 切换收藏 */
  toggleFavorite: (id: number) =>
    request<PaperItem>(`/papers/${id}/favorite`, { method: 'PUT' }),

  /** 统计 */
  stats: () => request<PaperStats>('/papers/stats'),
};

// ==================== Annotations API ====================

export interface AnnotationItem {
  id: number;
  paper_id: number | null;
  pdf_hash: string;
  annotation_type: 'highlight' | 'underline' | 'note' | 'strikethrough';
  page: number;
  rect: number[];  // [x0, y0, x1, y1]
  selected_text: string | null;
  note: string | null;
  color: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface AnnotationStats {
  pdf_hash: string;
  total: number;
  by_type: Record<string, number>;
  by_page: Record<string, number>;
}

export const annotationsApi = {
  /** 获取批注列表 */
  list: (params?: { pdf_hash?: string; paper_id?: number; page?: number; annotation_type?: string }) => {
    const p = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) p.set(k, String(v));
      });
    }
    return request<AnnotationItem[]>(`/annotations?${p}`);
  },

  /** 创建批注 */
  create: (data: {
    pdf_hash: string;
    paper_id?: number;
    annotation_type?: string;
    page: number;
    rect: number[];
    selected_text?: string;
    note?: string;
    color?: string;
  }) => request<AnnotationItem>('/annotations', { method: 'POST', body: JSON.stringify(data) }),

  /** 获取单个批注 */
  get: (id: number) => request<AnnotationItem>(`/annotations/${id}`),

  /** 更新批注 */
  update: (id: number, data: Partial<Pick<AnnotationItem, 'annotation_type' | 'rect' | 'selected_text' | 'note' | 'color'>>) =>
    request<AnnotationItem>(`/annotations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  /** 删除批注 */
  delete: (id: number) =>
    request<{ detail: string; id: number }>(`/annotations/${id}`, { method: 'DELETE' }),

  /** 获取批注统计 */
  stats: (pdfHash: string) => request<AnnotationStats>(`/annotations/stats/${pdfHash}`),
};

// ==================== Zotero MCP API ====================

export const zoteroApi = {
  status: () => request<{ connected: boolean; url: string }>('/zotero/status'),

  search: (params: { q?: string; title?: string; yearRange?: string; fulltext?: string; itemType?: string; mode?: string; limit?: number; sort?: string }) =>
    request<any>('/zotero/search', { method: 'POST', body: JSON.stringify(params) }),

  searchAnnotations: (params: { q?: string; colors?: string[]; tags?: string[]; mode?: string }) =>
    request<any>('/zotero/annotations', { method: 'POST', body: JSON.stringify(params) }),

  searchFulltext: (q: string, itemKeys?: string[], mode?: string) =>
    request<any>('/zotero/fulltext', { method: 'POST', body: JSON.stringify({ q, itemKeys, mode }) }),

  getCollections: (mode?: string) =>
    request<any>(`/zotero/collections?mode=${mode || 'standard'}`),

  getCollectionDetails: (key: string) =>
    request<any>(`/zotero/collections/${key}`),

  getCollectionItems: (key: string, limit?: number) =>
    request<any>(`/zotero/collections/${key}/items?limit=${limit || 50}`),

  getItemDetails: (key: string, mode?: string) =>
    request<any>(`/zotero/items/${key}?mode=${mode || 'standard'}`),

  getItemAbstract: (key: string) =>
    request<any>(`/zotero/items/${key}/abstract`),

  getContent: (params: { itemKey?: string; attachmentKey?: string; mode?: string }) =>
    request<any>('/zotero/content', { method: 'POST', body: JSON.stringify(params) }),

  writeNote: (params: { action: string; content: string; parentKey?: string; noteKey?: string; tags?: string[] }) =>
    request<any>('/zotero/notes', { method: 'POST', body: JSON.stringify(params) }),

  writeTag: (params: { action: string; itemKey: string; tags: string[] }) =>
    request<any>('/zotero/tags', { method: 'POST', body: JSON.stringify(params) }),

  writeMetadata: (params: { itemKey: string; fields?: Record<string, any>; creators?: any[] }) =>
    request<any>('/zotero/metadata', { method: 'POST', body: JSON.stringify(params) }),

  semanticSearch: (query: string, topK?: number, minScore?: number) =>
    request<any>('/zotero/semantic-search', { method: 'POST', body: JSON.stringify({ query, topK, minScore }) }),

  // ── 新增 6 个 ──
  searchCollections: (q: string, limit?: number) =>
    request<any>(`/zotero/collections/search?q=${encodeURIComponent(q)}&limit=${limit || 20}`),

  getSubcollections: (collectionKey: string, limit?: number, recursive?: boolean) =>
    request<any>(`/zotero/collections/${collectionKey}/subcollections?limit=${limit || 50}&recursive=${recursive || false}`),

  findSimilar: (itemKey: string, topK?: number, minScore?: number) =>
    request<any>(`/zotero/items/${itemKey}/similar?top_k=${topK || 10}&min_score=${minScore || 0.3}`),

  semanticStatus: () =>
    request<any>('/zotero/semantic-status'),

  fulltextDatabase: (action: string, query?: string, limit?: number) => {
    const params = new URLSearchParams({ action, limit: String(limit || 20) });
    if (query) params.set('query', query);
    return request<any>(`/zotero/fulltext-database?${params.toString()}`);
  },

  writeItem: (params: { action: string; itemType?: string; fields?: Record<string, any>; creators?: any[]; tags?: string[]; attachmentKeys?: string[]; parentKey?: string }) =>
    request<any>('/zotero/items', { method: 'POST', body: JSON.stringify(params) }),
};