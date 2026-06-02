/**
 * AcaSight API 客户端
 * 与后端 FastAPI (http://localhost:8000/api) 通信
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

  extractText: (url: string, maxChars?: number) =>
    request<{ text: string; pages: number }>('/pdf/extract-text', {
      method: 'POST',
      body: JSON.stringify({ url, max_chars: maxChars || 50000 }),
    }),

  toc: (path: string) =>
    request<{ toc: Array<{ level: number; title: string; page: number }> }>(`/pdf/${encodeURIComponent(path)}/toc`),

  /** 计算 PDF SHA256 哈希（用于批注关联）*/
  hash: (url: string) => {
    // 如果 url 已经是 proxy URL（含 ?url=），直接传 query string 避免双重编码
    if (url.includes('proxy?url=')) {
      return request<{ hash: string; size: number }>(`/pdf/hash?${url.split('?')[1]}`);
    }
    return request<{ hash: string; size: number }>(`/pdf/hash?url=${encodeURIComponent(url)}`);
  },

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

export interface SearchResultItem {
  title: string;
  authors: string;
  year: string | number;
  abstract?: string;
  doi?: string;
  citation_count?: number;
  pdf_url?: string;
  source: string;
  journal?: string;
  url?: string;
}

export interface CoreSearchResult {
  title: string;
  authors: string;
  year: string | number;
  abstract?: string;
  doi?: string;
  citation_count?: number;
  pdf_url?: string;
  source: string;
  fulltext_link?: string;
}

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
    return request<{ query: string; sources: string[]; results: Record<string, SearchResultItem[]> }>(
      `/search/?${params}`
    );
  },

  byDOI: (doi: string) => request<PaperItem>(`/search/doi/${encodeURIComponent(doi)}`),

  coreSearch: (params: { q: string; title?: string; authors?: string; journal?: string; year_from?: number; year_to?: number; fulltext?: string; limit?: number; offset?: number }) =>
    request<{ totalHits: number; results: CoreSearchResult[] }>('/search/core', { method: 'POST', body: JSON.stringify(params) }),

  coreDiscover: (params: { doi?: string; title?: string; year?: number }) =>
    request<{ fullTextLink: string; source: string }>('/search/core/discover', { method: 'POST', body: JSON.stringify(params) }),

  sources: () => request<{ sources: Array<{ id: string; name: string; description: string; url: string }> }>('/search/sources'),

  /** C.2: 搜索结果→入库（单条） */
  importPaper: (paper: Partial<PaperItem> & { title: string; pdf_url?: string }) =>
    request<{ status: string; paper: PaperItem; message: string }>('/search/import', {
      method: 'POST',
      body: JSON.stringify(paper),
    }),

  /** C.2: 搜索结果→入库（批量） */
  batchImportPapers: (papers: (Partial<PaperItem> & { title: string })[], default_tag?: string) =>
    request<{ status: string; imported: number; skipped: number; imported_titles: string[]; skipped_details: Array<{ title: string; reason: string }> }>('/search/import/batch', {
      method: 'POST',
      body: JSON.stringify({ papers, default_tag }),
    }),
};

export interface AIProviderConfig {
  base_url: string;
  api_key: string;
  models?: string[];  // optional: some providers return model string instead
  model?: string;  // legacy compat
  has_api_key?: boolean;  // legacy compat
  enabled: boolean;
  [key: string]: unknown;  // allow dynamic provider fields
}

export interface AIConfig {
  default_provider: string;
  default_model: string;
  providers: Record<string, AIProviderConfig>;
}

// ==================== AI Config API ====================

export const aiConfigApi = {
  getConfig: () => request<AIConfig>('/ai/config'),

  saveConfig: (config: Record<string, unknown>) =>
    request<AIConfig>('/ai/config', { method: 'POST', body: JSON.stringify(config) }),

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
  extra_fields: Record<string, unknown>;
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

export interface PaperDimensions {
  id: number;
  paper_id: number;
  abstract: string | null;
  research_background: string | null;
  research_purpose: string | null;
  research_status: string | null;
  research_questions: string | null;
  basic_theory: string | null;
  research_methods: string | null;
  results_and_evaluation: string | null;
  innovation_points: string | null;
  limitations_and_suggestions: string | null;
  conclusions: string | null;
  graph_indexed: number;
  created_at: string | null;
  updated_at: string | null;
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

  // === 维度拆分 API (契约版本: v1.0, DEVLOG-001) ===

  /** 获取文献11维度拆分数据 */
  getDimensions: (id: number) =>
    request<PaperDimensions>(`/papers/${id}/dimensions`),

  /** 执行AI维度拆分（自动提取全文并拆分，直接存库） */
  createDimensions: (id: number) =>
    request<{ paper_id: number; dimensions: Record<string, string> }>(`/papers/${id}/dimensions`, { method: 'POST' }),

  /** AI维度拆分预览（不存库，仅返回结果供查看） */
  previewDimensions: (id: number) =>
    request<{ paper_id: number; dimensions: Record<string, string>; preview: boolean }>(`/papers/${id}/dimensions/preview`, { method: 'POST' }),

  /** 确认保存预览的维度拆分数据到数据库 */
  confirmDimensions: (id: number, dimensions: Record<string, string>) =>
    request<{ paper_id: number; dimensions: PaperDimensions; saved: boolean }>(`/papers/${id}/dimensions/confirm`, { method: 'POST', body: JSON.stringify({ dimensions }) }),

  /** 删除维度拆分数据 */
  deleteDimensions: (id: number) =>
    request<{ detail: string; paper_id: number }>(`/papers/${id}/dimensions`, { method: 'DELETE' }),

  /** 获取某个维度数据 */
  getSingleDimension: (id: number, dimensionKey: string) =>
    request<{ paper_id: number; dimension: string; label: string; content: string | null }>(`/papers/${id}/dimensions/${dimensionKey}`),

  /** 按维度搜索文献（精准引用匹配） */
  searchByDimension: (dimension: string, q: string, limit?: number) =>
    request<{ dimension: string; query: string; results: Array<{ paper_id: number; content: string | null }>; count: number }>(
      `/papers/dimensions/search?dimension=${encodeURIComponent(dimension)}&q=${encodeURIComponent(q)}&limit=${limit || 20}`
    ),

  batchSplit: (paperIds: number[]) =>
    request<{ results: Array<{ paper_id: number; status: string; filled?: number; error?: string }>; total: number }>('/papers/batch-split', {
      method: 'POST',
      body: JSON.stringify({ paper_ids: paperIds }),
    }),
};

export interface PreprocessColumn {
  name: string;
  type: string;
  min?: number;
  max?: number;
  mean?: number;
  unit?: string;
}

export interface PreprocessResult {
  ok: boolean;
  instrument_type: string;
  detected_type: string;
  filename: string;
  columns: PreprocessColumn[];
  row_count: number;
  data: Record<string, unknown>[];
  metadata: Record<string, unknown>;
}

export interface InstrumentInfo {
  type: string;
  name: string;
  description: string;
  extensions: string[];
}

export const dataPreprocessApi = {
  parse: (file: File, instrumentType = 'auto', exportFormat = 'chart_data') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('instrument_type', instrumentType);
    fd.append('export_format', exportFormat);
    return request<PreprocessResult>(
      '/data-preprocess/parse',
      { method: 'POST', body: fd },
    );
  },

  preview: (file: File, instrumentType = 'auto') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('instrument_type', instrumentType);
    return request<PreprocessResult>(
      '/data-preprocess/preview',
      { method: 'POST', body: fd },
    );
  },

  textParse: (content: string, filename: string, instrumentType = 'auto', exportFormat = 'chart_data') =>
    request<PreprocessResult>(
      '/data-preprocess/text-parse',
      { method: 'POST', body: JSON.stringify({ content, filename, instrument_type: instrumentType, export_format: exportFormat }) },
    ),

  getInstruments: () =>
    request<{ instruments: InstrumentInfo[] }>(
      '/data-preprocess/instruments',
      { method: 'GET' },
    ),

  exportFile: (file: File, instrumentType = 'auto', exportFormat = 'csv') => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('instrument_type', instrumentType);
    fd.append('export_format', exportFormat);
    return request<Blob>(
      '/data-preprocess/export',
      { method: 'POST', body: fd },
    );
  },
};

// ==================== Annotations API ====================

// === 统一存储 API (契约版本: v1.0, DEVLOG-002) ===

export interface MaterialItem {
  filename: string;
  path: string;
  rel_path: string;
  category: string;
  size: number;
  mtime: number;
  metadata: Record<string, unknown> | null;
}

export interface CacheEntry {
  cache_id: string;
  key: string;
  category: string;
  created_at: string;
  expires_at: string;
  persisted: boolean;
}

export const storageApi = {
  /** 统一存储统计 */
  unifiedStats: () =>
    request<{ total_files: number; total_size_bytes: number; total_size_mb: number; by_category: Record<string, { files: number; size_bytes: number }> }>('/storage/unified/stats'),

  /** 列出素材 */
  unifiedList: (params?: { category?: string; paper_id?: number; limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) p.set(k, String(v));
      });
    }
    return request<{ items: MaterialItem[]; count: number }>(`/storage/unified/list?${p}`);
  },

  /** 上传素材 */
  unifiedUpload: (file: File, category: string, paperId?: number) => {
    const form = new FormData();
    form.append('file', file);
    form.append('category', category);
    if (paperId) form.append('paper_id', String(paperId));
    return fetch(`${BASE_URL}/storage/unified/upload`, { method: 'POST', body: form }).then(r => r.json());
  },

  /** 删除素材 */
  unifiedDelete: (path: string) =>
    request<{ ok: boolean }>(`/storage/unified/delete?path=${encodeURIComponent(path)}`, { method: 'DELETE' }),

  /** 保存绘图成品 */
  saveChartProduct: (image: File, rawData?: File, editParams?: Record<string, unknown>, paperId?: number) => {
    const form = new FormData();
    form.append('image', image);
    if (rawData) form.append('raw_data', rawData);
    if (editParams) form.append('edit_params', JSON.stringify(editParams));
    if (paperId) form.append('paper_id', String(paperId));
    return fetch(`${BASE_URL}/storage/unified/chart-product`, { method: 'POST', body: form }).then(r => r.json());
  },

  /** 缓存统计 */
  cacheStats: () =>
    request<{ total: number; expired: number; persisted: number; active: number; by_category: Record<string, number> }>('/storage/cache/stats'),

  /** 列出缓存 */
  cacheList: (category?: string, limit?: number) => {
    const p = new URLSearchParams();
    if (category) p.set('category', category);
    if (limit) p.set('limit', String(limit));
    return request<{ items: CacheEntry[] }>(`/storage/cache/list?${p}`);
  },

  /** 存入缓存 */
  cachePut: (key: string, data: Record<string, unknown>, category?: string, ttlHours?: number) => {
    const p = new URLSearchParams();
    p.set('key', key);
    if (category) p.set('category', category);
    if (ttlHours) p.set('ttl_hours', String(ttlHours));
    return request<{ cache_id: string; key: string }>(`/storage/cache/put?${p}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** 获取缓存 */
  cacheGet: (cacheId: string) =>
    request<{ cache_id: string; data: Record<string, unknown> }>(`/storage/cache/${cacheId}`),

  /** 持久化缓存 */
  cachePersist: (cacheId: string) =>
    request<{ cache_id: string; data: Record<string, unknown>; persisted: boolean }>(`/storage/cache/${cacheId}/persist`, { method: 'POST' }),

  /** 删除缓存 */
  cacheDelete: (cacheId: string) =>
    request<{ ok: boolean }>(`/storage/cache/${cacheId}`, { method: 'DELETE' }),

  /** 清理过期缓存 */
  cacheCleanup: () =>
    request<{ removed: number }>('/storage/cache/cleanup', { method: 'POST' }),
};

// === 写作工作流 API (契约版本: v1.0, DEVLOG-003) ===

export interface WritingWorkspace {
  session_id: string;
  title: string;
  paper_type: string;
  word_count: number;
  data_mode: string;
  materials: MaterialItem[];
  references: PaperItem[];
  status: string;
}

export interface OutlineNode {
  level: number;
  title: string;
  estimated_words?: number;
  description?: string;
  sections?: OutlineNode[];
}

export interface PaperOutline {
  title: string;
  outline: OutlineNode[];
  keywords: string[];
  estimated_total_words: number;
}

export const writingApi = {
  /** 创建写作工作台会话 */
  createWorkspace: (params: {
    title: string;
    paper_type?: string;
    word_count?: number;
    material_ids?: string[];
    data_mode?: string;
    reference_paper_ids?: number[];
  }) =>
    request<WritingWorkspace>('/writing/workspace/create', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /** SSE 流式生成大纲 */
  streamOutline: (sessionId: string, params: {
    topic: string;
    subject?: string;
    paper_type?: string;
    word_count?: number;
    references?: Array<{ title: string; authors: string; year: string }>;
  }) =>
    fetch(`${BASE_URL}/writing/workspace/${sessionId}/outline/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }),

  /** SSE 流式撰写章节 */
  streamSection: (sessionId: string, params: {
    topic: string;
    outline: Array<{ level: number; title: string; description?: string }>;
    section_index: number;
    previous_content?: string;
    word_count?: number;
    reference_dimensions?: Array<{ paper_title: string; dimension_label: string; content: string }>;
  }) =>
    fetch(`${BASE_URL}/writing/workspace/${sessionId}/section/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }),

  /** 确认中断（用户选择素材后恢复写作） */
  confirmInterrupt: (sessionId: string, params: {
    section_index: number;
    material_type: 'upload' | 'chart' | 'existing';
    material_path?: string;
    chart_config?: Record<string, unknown>;
  }) =>
    request<{ session_id: string; section_index: number; confirmed: boolean; material: Record<string, unknown> }>(
      `/writing/workspace/${sessionId}/interrupt/confirm`,
      { method: 'POST', body: JSON.stringify(params) },
    ),

  /** 生成大纲（非流式） */
  generateOutline: (params: {
    topic: string;
    subject?: string;
    paper_type?: string;
    word_count?: number;
    references?: Array<{ title: string; authors?: string; year?: string | number; doi?: string }>;
  }) =>
    request<{ success: boolean; data: PaperOutline }>('/writing/generate-outline', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /** 生成章节（非流式） */
  generateSection: (params: {
    topic: string;
    outline: Array<{ level: number; title: string; description?: string }>;
    current_section: { title: string; description?: string };
    previous_content?: string;
    word_count?: number;
  }) =>
    request<{ success: boolean; content: string }>('/writing/generate-section', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /** 文本润色 */
  polish: (text: string, mode?: string) =>
    request<{ success: boolean; content: string }>('/writing/polish', {
      method: 'POST',
      body: JSON.stringify({ text, mode: mode || 'polish' }),
    }),

  process: (params: { text: string; action: string; target_lang?: string; context?: string; model?: string }) =>
    request<{ result: string; word_count_before?: number; word_count_after?: number }>('/writing/process', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  listTemplates: () =>
    request<{ templates: Array<{ id: string; name: string; font: string; body_size: number; line_spacing: number }> }>('/writing/templates'),

  /** 导出 Word */
  exportWord: (params: {
    content: string;
    template_id: string;
    title?: string;
    author?: string;
    institution?: string;
  }) =>
    request<{ success: boolean; filename: string; path: string; download_url: string; template: string }>('/writing/export-word', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /** 导出 Word（后端直接返回文件流） */
  exportWordFile: (params: {
    content: string;
    template_id: string;
    title?: string;
    author?: string;
    institution?: string;
  }) =>
    fetch(`${BASE_URL}/writing/export-word-via-backend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }),

  /** 文献搜索 */
  searchLiterature: (query: string, limit?: number) =>
    request<{ success: boolean; results: Array<{ title: string; authors: string; year: string; abstract: string; doi: string; citations: number; journal: string; source: string }> }>(
      '/writing/search-literature',
      { method: 'POST', body: JSON.stringify({ query, limit: limit || 15 }) },
    ),

  /** 下载 PPT 文件 */
  downloadPpt: (path: string) =>
    fetch(`${BASE_URL}/writing/download-ppt?path=${encodeURIComponent(path)}`),
};

// === Agent Skills API (契约版本: v1.0, DEVLOG-026) ===

export interface SkillInfo {
  name: string;
  description: string;
  category: string;
  examples?: string[];
}

export const agentApi = {
  listSkills: () =>
    request<{ skills: SkillInfo[] }>('/agent/skills'),

  callTool: (params: { tool_name: string; arguments: Record<string, unknown> }) =>
    request<{ success: boolean; result: unknown; error?: string }>('/agent/tools/call', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  listSessions: () =>
    request<{ sessions: Array<{ conversation_id: string; created_at: string; updated_at: string; message_count: number; preview: string }> }>('/agent/sessions'),

  getSession: (conversationId: string) =>
    request<{ conversation_id: string; messages: Array<{ role: string; content: string }> }>(`/agent/sessions/${conversationId}`),

  deleteSession: (conversationId: string) =>
    request<void>(`/agent/sessions/${conversationId}`, { method: 'DELETE' }),

  sendTask: (params: { task: string; context: Record<string, unknown>; conversation_id?: string | null }) =>
    fetch(`${BASE_URL}/agent/task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }),

  toolChat: (params: { messages: Array<{ role: string; content: string }>; conversation_id?: string | null }) =>
    fetch(`${BASE_URL}/agent/tool-chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }),
};

export const notesApi = {
  save: (params: { note_id: string | null; content: string; title: string }) =>
    request<{ id: string; title: string }>('/notes/save', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};

// === RAG API (契约版本: v1.0, DEVLOG-026) ===

export interface RAGDataset {
  id: string;
  name: string;
}

export const ragApi = {
  /** 获取 RAG 服务状态 */
  getStatus: () =>
    request<{ available: boolean; datasets: RAGDataset[] }>('/rag/status'),

  /** RAG 知识库查询 */
  query: (question: string, datasetIds?: string[], chatId?: string) =>
    request<{ answer: string; available: boolean; reference?: { source: string; content: string; score: number } }>('/rag/query', {
      method: 'POST',
      body: JSON.stringify({ question, dataset_ids: datasetIds, chat_id: chatId }),
    }),
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

  /** AI 纲要生成 (IFACE-REQ-001, DEVLOG-005) */
  generateOutline: (params: {
    annotations: Array<{ page: number; selected_text?: string | null; note?: string | null; color?: string | null; annotation_type?: string | null }>;
    paper_title?: string;
  }) =>
    request<{ outline: string; sections: string[] }>('/annotations/generate-outline', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};

// === Chart AI API (契约版本: v1.0, DEVLOG-031) ===

export const chartApi = {
  /** AI 自动生成图表配置 */
  autoGenerate: (params: {
    description: string;
    columns: Array<{ key: string; label: string; type: string }>;
    sample_data: Record<string, unknown>[];
    total_rows: number;
  }) =>
    request<{
      chart_type: string;
      x_col: string;
      y_cols: string[];
      reason: string;
      academic_mode: boolean;
      show_grid: boolean;
    }>('/chart/auto', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /** AI 优化当前图表配置 */
  refine: (params: {
    description: string;
    current_config: Record<string, unknown>;
    columns: Array<{ key: string; label: string; type: string }>;
    sample_data: Record<string, unknown>[];
    total_rows: number;
  }) =>
    request<{
      chart_type: string;
      x_col: string;
      y_cols: string[];
      reason: string;
    }>('/chart/auto/refine', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};

// ==================== Zotero MCP API ====================

export interface ZoteroItem {
  key: string;
  title: string;
  itemType: string;
  creators: Array<{ firstName: string; lastName: string; creatorType: string }>;
  year: string | number;
  abstractNote?: string;
  doi?: string;
  journal?: string;
  tags: Array<{ tag: string }>;
  dateAdded: string;
  dateModified: string;
}

export interface ZoteroCollection {
  key: string;
  name: string;
  parentCollection?: string;
  numItems: number;
  subcollections?: ZoteroCollection[];
  content?: ZoteroItem[];  // legacy compat
  data?: ZoteroCollection & { meta?: Record<string, unknown> };  // legacy compat
}

export interface ZoteroAnnotation {
  key: string;
  parentItem: string;
  annotationType: string;
  annotationText: string;
  annotationComment: string;
  annotationColor: string;
  annotationPageLabel: string;
}

export const zoteroApi = {
  status: () => request<{ connected: boolean; url: string }>('/zotero/status'),

  search: (params: { q?: string; title?: string; yearRange?: string; fulltext?: string; itemType?: string; mode?: string; limit?: number; sort?: string }) =>
    request<Record<string, unknown> & { results?: ZoteroItem[]; count?: number }>('/zotero/search', { method: 'POST', body: JSON.stringify(params) }),

  searchAnnotations: (params: { q?: string; colors?: string[]; tags?: string[]; mode?: string }) =>
    request<{ results: ZoteroAnnotation[]; count: number }>('/zotero/annotations', { method: 'POST', body: JSON.stringify(params) }),

  searchFulltext: (q: string, itemKeys?: string[], mode?: string) =>
    request<{ results: Array<{ itemKey: string; text: string; score: number }>; count: number }>('/zotero/fulltext', { method: 'POST', body: JSON.stringify({ q, itemKeys, mode }) }),

  getCollections: (mode?: string) =>
    request<Record<string, unknown> & { collections?: ZoteroCollection[] }>(`/zotero/collections?mode=${mode || 'standard'}`),

  getCollectionDetails: (key: string) =>
    request<ZoteroCollection>(`/zotero/collections/${key}`),

  getCollectionItems: (key: string, limit?: number) =>
    request<Record<string, unknown> & { items?: ZoteroItem[]; count?: number }>(`/zotero/collections/${key}/items?limit=${limit || 50}`),

  getItemDetails: (key: string, mode?: string) =>
    request<ZoteroItem>(`/zotero/items/${key}?mode=${mode || 'standard'}`),

  getItemAbstract: (key: string) =>
    request<{ key: string; abstract: string }>(`/zotero/items/${key}/abstract`),

  getContent: (params: { itemKey?: string; attachmentKey?: string; mode?: string }) =>
    request<{ content: string; format: string; length: number }>('/zotero/content', { method: 'POST', body: JSON.stringify(params) }),

  writeNote: (params: { action: string; content: string; parentKey?: string; noteKey?: string; tags?: string[] }) =>
    request<{ success: boolean; key: string }>('/zotero/notes', { method: 'POST', body: JSON.stringify(params) }),

  writeTag: (params: { action: string; itemKey: string; tags: string[] }) =>
    request<{ success: boolean; key: string }>('/zotero/tags', { method: 'POST', body: JSON.stringify(params) }),

  writeMetadata: (params: { itemKey: string; fields?: Record<string, string>; creators?: Array<{ firstName: string; lastName: string; creatorType: string }> }) =>
    request<{ success: boolean; key: string }>('/zotero/metadata', { method: 'POST', body: JSON.stringify(params) }),

  semanticSearch: (query: string, topK?: number, minScore?: number) =>
    request<{ results: Array<{ itemKey: string; title: string; score: number }>; count: number }>('/zotero/semantic-search', { method: 'POST', body: JSON.stringify({ query, topK, minScore }) }),

  // ── 新增 6 个 ──
  searchCollections: (q: string, limit?: number) =>
    request<{ collections: ZoteroCollection[]; count: number }>(`/zotero/collections/search?q=${encodeURIComponent(q)}&limit=${limit || 20}`),

  getSubcollections: (collectionKey: string, limit?: number, recursive?: boolean) =>
    request<{ subcollections: ZoteroCollection[] }>(`/zotero/collections/${collectionKey}/subcollections?limit=${limit || 50}&recursive=${recursive || false}`),

  findSimilar: (itemKey: string, topK?: number, minScore?: number) =>
    request<{ results: Array<{ itemKey: string; title: string; score: number }> }>(`/zotero/items/${itemKey}/similar?top_k=${topK || 10}&min_score=${minScore || 0.3}`),

  semanticStatus: () =>
    request<{ available: boolean; index_count: number }>('/zotero/semantic-status'),

  fulltextDatabase: (action: string, query?: string, limit?: number) => {
    const params = new URLSearchParams({ action, limit: String(limit || 20) });
    if (query) params.set('query', query);
    return request<{ results: Array<{ itemKey: string; text: string }>; count: number }>(`/zotero/fulltext-database?${params.toString()}`);
  },

  writeItem: (params: { action: string; itemType?: string; fields?: Record<string, string>; creators?: Array<{ firstName: string; lastName: string; creatorType: string }>; tags?: string[]; attachmentKeys?: string[]; parentKey?: string }) =>
    request<{ success: boolean; key: string }>('/zotero/items', { method: 'POST', body: JSON.stringify(params) }),
};

// === 模块Agent调度 API (契约版本: v1.0, DEVLOG-008) ===

export interface ModuleStatus {
  module: string;
  description: string;
  status: 'idle' | 'running' | 'interrupted' | 'completed' | 'failed';
  interrupt_info: {
    reason: string;
    section_index: number;
    section_title: string;
    required_type: string;
    options: Array<{ key: string; label: string; description: string }>;
  } | null;
  last_result: { success: boolean; error: string } | null;
  history_count: number;
}

export const moduleApi = {
  /** 列出所有模块Agent及其状态 */
  list: () =>
    request<{ success: boolean; modules: ModuleStatus[]; count: number }>('/agent/modules'),

  /** 获取指定模块Agent状态 */
  getStatus: (moduleName: string) =>
    request<{ success: boolean } & ModuleStatus>(`/agent/modules/${moduleName}`),

  /** 通过模块Agent执行任务 */
  execute: (moduleName: string, task: string, context?: Record<string, unknown>) =>
    request<{ success: boolean; module: string; data: Record<string, unknown>; error: string; interrupt_reason: string; interrupt_data: Record<string, unknown> }>(
      '/agent/modules/execute',
      { method: 'POST', body: JSON.stringify({ module: moduleName, task, context: context || {} }) },
    ),

  /** 恢复被中断的模块Agent */
  resume: (moduleName: string, userChoice?: Record<string, unknown>) =>
    request<{ success: boolean; module: string; data: Record<string, unknown>; error: string }>(
      '/agent/modules/resume',
      { method: 'POST', body: JSON.stringify({ module: moduleName, user_choice: userChoice }) },
    ),
};

// === 格式导出 API (契约版本: v1.0, DEVLOG-012) ===

export interface CslStyleItem {
  id: string;
  name: string;
}

export const formatApi = {
  /** 列出可用的 CSL 引用格式样式 */
  listStyles: () =>
    request<{ styles: CslStyleItem[]; pandoc_available: boolean }>('/format/styles'),

  /** 导出文档（docx / latex / pdf / html） */
  exportDocument: (params: {
    markdown: string;
    title?: string;
    format: 'docx' | 'latex' | 'pdf' | 'html';
    csl_style?: string;
    bibliography?: string;
  }) =>
    fetch(`${BASE_URL}/format/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }),

  /** 从论文数据生成 BibTeX 文件 */
  generateBib: (papers: Array<{ title: string; authors?: string; year?: string | number; doi?: string; journal?: string; volume?: string; pages?: string; abstract?: string }>) =>
    fetch(`${BASE_URL}/format/generate-bib`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ papers }),
    }),
};

// === 写作流管理 API (契约版本: v1.0, DEVLOG-013) ===

export type WritingFlowStatusType = 'created' | 'outlining' | 'outline_review' | 'writing' | 'interrupted' | 'confirmed' | 'completed' | 'failed';

export interface WritingFlowSummary {
  session_id: string;
  title: string;
  status: WritingFlowStatusType;
  current_section_index: number;
  sections_written: number;
  data_mode: string;
  created_at: number;
  updated_at: number;
}

export interface WritingFlowDetail {
  session_id: string;
  title: string;
  status: WritingFlowStatusType;
  outline: Array<{ title: string; description?: string }> | null;
  current_section_index: number;
  sections_written: Array<{ section_index: number; section_title: string; content: string }>;
  interrupt_info: {
    section_index: number;
    section_title: string;
    reason: string;
    options: Array<{ key: string; label: string }>;
  } | null;
  data_mode: string;
  material_ids: string[];
  reference_paper_ids: number[];
  created_at: number;
  updated_at: number;
}

// === 引用网络 API (契约版本: v1.0, DEVLOG-031) ===

export interface CitationNode {
  id: string;
  paperId: string;
  doi: string;
  title: string;
  label: string;
  year: number | null;
  citationCount: number;
  referenceCount: number;
  authors: string[];
  journal: string;
  fieldsOfStudy: string[];
  group: 'center' | 'reference' | 'citation' | 'indirect';
}

export interface CitationLink {
  source: string;
  target: string;
  type: 'references' | 'cites';
}

export interface CitationNetworkResponse {
  center_doi: string;
  nodes: CitationNode[];
  links: CitationLink[];
  stats: {
    total_nodes: number;
    total_links: number;
    by_group: Record<string, number>;
  };
}

export interface BatchCitationResult {
  doi: string;
  title?: string;
  citation_count?: number;
  reference_count?: number;
  top_citations?: Array<{
    paperId: string;
    title: string;
    year: number | null;
    citationCount: number;
  }>;
  error?: string;
}

export const citationApi = {
  /** 获取引用关系网络 */
  getNetwork: (doi: string, params?: { max_depth?: number; max_nodes?: number; direction?: string }) => {
    const p = new URLSearchParams();
    if (params?.max_depth) p.set('max_depth', String(params.max_depth));
    if (params?.max_nodes) p.set('max_nodes', String(params.max_nodes));
    if (params?.direction) p.set('direction', params.direction);
    return request<CitationNetworkResponse>(`/knowledge/graph/citations/${encodeURIComponent(doi)}?${p}`);
  },

  /** 批量获取引用信息 */
  batchFetch: (dois: string[], maxPerPaper?: number) =>
    request<{ success: boolean; results: Record<string, BatchCitationResult> }>(
      `/knowledge/citations/batch?${dois.map(d => `dois=${encodeURIComponent(d)}`).join('&')}${maxPerPaper ? `&max_per_paper=${maxPerPaper}` : ''}`,
    ),

  /** 章节引用匹配 */
  matchSection: (params: { section_title: string; section_content?: string; reference_paper_ids?: number[]; top_k?: number }) =>
    request<{ success: boolean; section_title: string; matches: Array<{
      paper_id: number; title: string; authors: string[] | string; year: number | null;
      doi: string | null; dimension_key: string; dimension_label: string;
      matched_content: string; relevance_score: number; citation_format: string;
    }> }>('/knowledge/match/section', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  /** 大纲引用匹配 */
  matchOutline: (params: { outline: Array<{ level: number; title: string; description?: string }>; reference_paper_ids?: number[]; top_k_per_section?: number }) =>
    request<{ success: boolean; matches: Record<string, Array<{
      paper_id: number; title: string; dimension_key: string; matched_content: string;
      relevance_score: number; citation_format: string;
    }>> }>('/knowledge/match/outline', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};

export const knowledgeApi = {
  graph: (includeSearch?: boolean) =>
    request<{ nodes: Array<{ id: string; label: string; group: string; citation_count?: number; doi?: string; journal?: string; year?: number }>; links: Array<{ source: string; target: string; value?: number }> }>(`/knowledge/graph?include_search=${includeSearch || false}`),

  stats: (includeSearch?: boolean) =>
    request<{ node_count: number; link_count: number; groups: Record<string, number> }>(`/knowledge/graph/stats?include_search=${includeSearch || false}`),

  references: (doi: string, maxDepth?: number, maxNodes?: number) =>
    request<{ nodes: Array<{ id: string; label: string; group: string; citation_count?: number; doi?: string }>; links: Array<{ source: string; target: string }>; error?: string }>(`/knowledge/references/${encodeURIComponent(doi)}?max_depth=${maxDepth || 2}&max_nodes=${maxNodes || 150}`),

  paperByDoi: (doi: string) =>
    request<{ id: number; title: string; pdf_path?: string; doi?: string; authors?: string; year?: number; journal?: string }>(`/papers/by_doi/${encodeURIComponent(doi)}`),
};

export const workflowApi = {
  /** 列出所有写作流 */
  listFlows: () =>
    request<{ success: boolean; flows: WritingFlowSummary[] }>('/system/writing-flows'),

  /** 创建写作流 */
  createFlow: (params: { session_id: string; title: string; data_mode?: string; material_ids?: string[]; reference_paper_ids?: number[] }) =>
    request<{ success: boolean; flow: { session_id: string; title: string; status: WritingFlowStatusType; data_mode: string } }>(
      '/system/writing-flows/create',
      { method: 'POST', body: JSON.stringify(params) },
    ),

  /** 获取写作流详情 */
  getFlow: (sessionId: string) =>
    request<{ success: boolean; flow: WritingFlowDetail }>(`/system/writing-flows/${sessionId}`),

  /** 转换写作流状态 */
  transitionFlow: (sessionId: string, newStatus: WritingFlowStatusType, opts?: { outline?: Array<{ title: string; description?: string }>; interrupt_info?: Record<string, unknown> }) =>
    request<{ success: boolean; session_id: string; status: WritingFlowStatusType }>(
      `/system/writing-flows/${sessionId}/transition`,
      { method: 'POST', body: JSON.stringify({ new_status: newStatus, ...opts }) },
    ),

  /** 执行写作流管道 */
  runPipeline: (sessionId: string, outline: Array<{ title: string; description?: string }>, topic: string) =>
    request<{ success: boolean; interrupted?: boolean; completed?: boolean; section_index?: number; section_title?: string; sections?: Array<{ section_index: number; section_title: string; content: string }>; message?: string; error?: string }>(
      `/system/writing-flows/${sessionId}/pipeline`,
      { method: 'POST', body: JSON.stringify({ outline, topic }) },
    ),

  /** 通过引擎执行Agent任务 */
  executeAgent: (agentName: string, task: string, context?: Record<string, unknown>) =>
    request<{ success: boolean; data: Record<string, unknown>; error: string; interrupted?: boolean; interrupt_reason?: string; interrupt_data?: Record<string, unknown> }>(
      '/system/agent-chain/execute',
      { method: 'POST', body: JSON.stringify({ agent_name: agentName, task, context: context || {} }) },
    ),

  /** 恢复被中断的Agent */
  resumeAgent: (agentName: string, userChoice?: Record<string, unknown>) =>
    request<{ success: boolean; data: Record<string, unknown>; error: string }>(
      '/system/agent-chain/resume',
      { method: 'POST', body: JSON.stringify({ agent_name: agentName, user_choice: userChoice || {} }) },
    ),
};

// === 研究方向 & 试验方案 API (契约版本: v1.0, DEVLOG-014) ===

export interface ResearchDirection {
  title: string;
  description: string;
  novelty: string;
  feasibility: string;
  key_questions: string[];
  suggested_methods: string[];
  difficulty: string;
  related_fields: string[];
}

export interface ExperimentDesign {
  title: string;
  objective: string;
  hypothesis: string;
  design_type: string;
  variables: { independent: string[]; dependent: string[]; controlled: string[] };
  procedure: Array<{ step: number; title: string; description: string; duration: string }>;
  data_collection: { methods: string[]; instruments: string[]; sample_size: string };
  analysis_plan: { methods: string[]; tools: string[]; significance_level: string };
  validity: { internal: string; external: string };
  ethics: string;
  timeline: string;
  risks: string[];
  alternatives: string[];
}

export const researchApi = {
  /** 生成研究方向 */
  generateDirections: (params: { topic: string; subject?: string; background?: string; existing_literature?: Array<{ title: string; authors?: string; year?: string | number }>; count?: number }) =>
    request<{ success: boolean; data: { directions: ResearchDirection[]; raw?: string } }>(
      '/writing/research-direction',
      { method: 'POST', body: JSON.stringify(params) },
    ),

  /** 生成试验/实验方案 */
  generateExperimentDesign: (params: { topic: string; research_question?: string; methodology?: string; variables?: string[]; constraints?: string; existing_data?: string }) =>
    request<{ success: boolean; data: { experiment_design: ExperimentDesign; raw?: string } }>(
      '/writing/experiment-design',
      { method: 'POST', body: JSON.stringify(params) },
    ),
};

// === PPT 生成 API (契约版本: v1.0, DEVLOG-019) ===

export interface PptSlide {
  type: 'title' | 'content' | 'two_column' | 'image' | 'table' | 'conclusion';
  title: string;
  content?: string[];
  left_column?: string[];
  right_column?: string[];
  notes?: string;
}

export const pptApi = {
  /** 生成学术PPT */
  generate: (params: { title: string; subject?: string; outline?: Array<{ title: string; description?: string }>; content?: string; style?: string; slide_count?: number }) =>
    request<{ success: boolean; data: { filename?: string; path?: string; slide_count: number; theme?: Record<string, unknown>; slides?: PptSlide[]; note?: string; raw?: string } }>(
      '/writing/generate-ppt',
      { method: 'POST', body: JSON.stringify(params) },
    ),
};

// === PaperBanana 图表生成 Pipeline API (契约版本: v1.0, DEVLOG-046) ===

export interface PaperBananaPlotResult {
  image_base64: string;
  code: string;
  description: string;
  critic_reports: Array<{ suggestions: string; revised_description: string }>;
  rounds_completed: number;
  task_type: string;
  style_guide: string;
}

export interface PaperBananaStyle {
  id: string;
  name: string;
  supports: string[];
}

export const paperBananaApi = {
  /** 统计图生成 Pipeline (数据→描述→代码→执行→评估→修正) */
  generatePlot: (params: { data: string; visual_intent: string; style_guide?: string; max_critic_rounds?: number; references?: Array<Record<string, unknown>> }) =>
    request<{ success: boolean; data: PaperBananaPlotResult }>(
      '/paper-banana/generate-plot',
      { method: 'POST', body: JSON.stringify(params) },
    ),

  /** 方法图生成 Pipeline (文本→描述→图像→评估→修正) */
  generateDiagram: (params: { methodology: string; caption: string; style_guide?: string; max_critic_rounds?: number }) =>
    request<{ success: boolean; data: PaperBananaPlotResult }>(
      '/paper-banana/generate-diagram',
      { method: 'POST', body: JSON.stringify(params) },
    ),

  /** 直接执行 matplotlib 代码 */
  executePlotCode: (params: { code: string }) =>
    request<{ success: boolean; image_base64?: string; error?: string }>(
      '/paper-banana/execute-plot-code',
      { method: 'POST', body: JSON.stringify(params) },
    ),

  /** 获取可用的 SCI 期刊风格指南列表 */
  getStyles: () =>
    request<{ styles: PaperBananaStyle[] }>(
      '/paper-banana/styles',
      { method: 'GET' },
    ),
};


// === Deep Research 深度研究 Pipeline API (契约版本: v1.0, DEVLOG-049) ===

export interface DeepResearchSource {
  id: string;
  name: string;
  available: boolean;
  type: string;
}

export interface DeepResearchMode {
  id: string;
  breadth: number;
  depth: number;
  concurrency: number;
  max_learnings: number;
  label: string;
  est_time: string;
}

export interface DeepResearchPaper {
  title: string;
  authors: string[];
  year: string;
  url: string;
  doi: string;
  citation_count: number;
  key_finding: string;
  source: string;
  relevance: number;
}

export interface DeepResearchInsight {
  title: string;
  description: string;
  relatedPapers: string[];
}

export interface DeepResearchGap {
  area: string;
  description: string;
  potentialQuestions: string[];
}

export interface DeepResearchResult {
  summary: string;
  papers: DeepResearchPaper[];
  insights: DeepResearchInsight[];
  gaps: DeepResearchGap[];
  citations: Record<string, string>;
  context: string;
  metadata: {
    mode: string;
    breadth: number;
    depth: number;
    total_queries: number;
    total_papers: number;
    total_insights: number;
    elapsed_seconds: number;
    sources_used: string[];
  };
}

export interface PubMedArticle {
  title: string;
  abstract: string;
  url: string;
  authors: string[];
  year: string;
  doi: string;
  source: string;
  content: string;
}

export const deepResearchApi = {
  /** 启动深度研究 (SSE 流式) */
  start: (query: string, mode: string = 'deep') =>
    request<{ success: boolean; data: DeepResearchResult }>(
      '/deep-research/start-sync',
      { method: 'POST', body: JSON.stringify({ query, mode }) },
    ),

  /** PubMed / PMC 搜索 */
  searchPubMed: (query: string, maxResults: number = 10, db: string = 'pmc') =>
    request<{ success: boolean; data: PubMedArticle[]; total: number }>(
      '/deep-research/pubmed',
      { method: 'POST', body: JSON.stringify({ query, max_results: maxResults, db }) },
    ),

  /** 获取可用检索源和模式 */
  getSources: () =>
    request<{ success: boolean; data: { sources: DeepResearchSource[]; modes: DeepResearchMode[]; total_sources: number } }>(
      '/deep-research/sources',
      { method: 'GET' },
    ),
};


// === Figure Edit SVG 矢量图编辑 API (契约版本: v1.0, DEVLOG-050) ===

export interface MethodToSvgResult {
  svg_content: string;
  icon_count: number;
  files: {
    figure: string;
    samed: string;
    boxlib: string;
    template_svg: string;
    final_svg: string;
  };
}

export interface SegmentResult {
  detections: Array<{
    bbox: number[];
    area: number;
    label: string;
    score: number;
    prompt: string;
  }>;
  image_size: [number, number];
  total: number;
}

export interface FigureEditStatus {
  sam3_available: boolean;
  sam3_backend: string;
  placeholder_modes: string[];
  features: Record<string, boolean>;
}

export const figureEditApi = {
  /** 完整流程: Method 文本 → SVG 矢量图 */
  methodToSvg: (methodText: string, options?: {
    samPrompts?: string;
    placeholderMode?: string;
    minScore?: number;
    mergeThreshold?: number;
    optimizeIterations?: number;
  }) =>
    request<{ success: boolean; data: MethodToSvgResult }>(
      '/figure-edit/method-to-svg',
      { method: 'POST', body: JSON.stringify({
        method_text: methodText,
        sam_prompts: options?.samPrompts ?? 'icon',
        placeholder_mode: options?.placeholderMode ?? 'label',
        min_score: options?.minScore ?? 0.5,
        merge_threshold: options?.mergeThreshold ?? 0.9,
        optimize_iterations: options?.optimizeIterations ?? 2,
      }) },
    ),

  /** SAM3 图标分割 */
  segment: (imageBase64: string, prompts?: string, minScore?: number) =>
    request<{ success: boolean; data: SegmentResult }>(
      '/figure-edit/segment',
      { method: 'POST', body: JSON.stringify({
        image_base64: imageBase64,
        prompts: prompts ?? 'icon',
        min_score: minScore ?? 0.5,
      }) },
    ),

  /** SVG 语法修复 */
  fixSvg: (svgCode: string) =>
    request<{ success: boolean; data: { svg_code: string; was_valid: boolean; errors: string[] } }>(
      '/figure-edit/fix-svg',
      { method: 'POST', body: JSON.stringify({ svg_code: svgCode }) },
    ),

  /** 服务状态 */
  getStatus: () =>
    request<{ success: boolean; data: FigureEditStatus }>(
      '/figure-edit/status',
      { method: 'GET' },
    ),
};


// === Architecture 架构优化 API (契约版本: v1.0, DEVLOG-053) ===

export interface VisualEvalResult {
  passed: boolean;
  feedback: string | null;
  retry_count: number;
  history: Array<{
    attempt: number;
    passed: boolean;
    feedback: string | null;
  }>;
}

export interface PipelineStageResult {
  status: string;
  error: string | null;
  attempts: number;
  duration_seconds: number;
}

export interface PipelineResult {
  pipeline_id: string;
  success: boolean;
  duration_seconds: number;
  stages: Record<string, PipelineStageResult>;
}

export interface ArchStatus {
  visual_evaluator: boolean;
  stage_orchestrator: boolean;
  loop_detector: boolean;
  ai_formatter: boolean;
  sci_styles: string[];
  output_formats: string[];
}

export const archApi = {
  /** 图表视觉评估 */
  evaluateVisual: (imageBase64: string, options?: {
    criteria?: string;
    style?: string;
    maxRetries?: number;
  }) =>
    request<{ success: boolean; data: VisualEvalResult }>(
      '/arch/evaluate-visual',
      { method: 'POST', body: JSON.stringify({
        image_base64: imageBase64,
        criteria: options?.criteria,
        style: options?.style ?? 'default',
        max_retries: options?.maxRetries ?? 3,
      }) },
    ),

  /** AI 响应格式化 */
  format: (rawResponse: string, expectedFormat?: string, strict?: boolean) =>
    request<{ success: boolean; data: { format: string; content: any; warnings: string[] } }>(
      '/arch/format',
      { method: 'POST', body: JSON.stringify({
        raw_response: rawResponse,
        expected_format: expectedFormat ?? 'text',
        strict: strict ?? false,
      }) },
    ),

  /** 架构服务状态 */
  getStatus: () =>
    request<{ success: boolean; data: ArchStatus }>(
      '/arch/status',
      { method: 'GET' },
    ),
};


// === Plugin System 插件系统 API (契约版本: v1.0, DEVLOG-054) ===

export interface PluginInfo {
  name: string;
  version: string;
  state: string;
  hooks: string[];
  loaded_at: number | null;
  error: string | null;
}

export interface HookResult {
  plugin: string;
  success: boolean;
  result: any;
  error: string | null;
  duration_ms: number;
}

export const pluginsApi = {
  /** 列出已安装插件 */
  list: () =>
    request<{ success: boolean; data: PluginInfo[] }>(
      '/plugins/',
      { method: 'GET' },
    ),

  /** 发现可用插件 */
  discover: () =>
    request<{ success: boolean; data: { plugins_dir: string; discovered: string[]; count: number } }>(
      '/plugins/discover',
      { method: 'GET' },
    ),

  /** 加载插件 */
  load: (pluginPath: string, config?: Record<string, any>) =>
    request<{ success: boolean; data: PluginInfo | null }>(
      '/plugins/load',
      { method: 'POST', body: JSON.stringify({ plugin_path: pluginPath, config }) },
    ),

  /** 启用插件 */
  enable: (pluginName: string) =>
    request<{ success: boolean; data: PluginInfo }>(
      `/plugins/${encodeURIComponent(pluginName)}/enable`,
      { method: 'POST' },
    ),

  /** 禁用插件 */
  disable: (pluginName: string) =>
    request<{ success: boolean; data: PluginInfo }>(
      `/plugins/${encodeURIComponent(pluginName)}/disable`,
      { method: 'POST' },
    ),

  /** 卸载插件 */
  unload: (pluginName: string) =>
    request<{ success: boolean; message: string }>(
      `/plugins/${encodeURIComponent(pluginName)}`,
      { method: 'DELETE' },
    ),

  /** 触发钩子 */
  triggerHook: (hookName: string, kwargs?: Record<string, any>) =>
    request<{ success: boolean; data: { hook_name: string; handlers_called: number; results: HookResult[] } }>(
      '/plugins/hook',
      { method: 'POST', body: JSON.stringify({ hook_name: hookName, kwargs: kwargs ?? {} }) },
    ),

  /** 插件状态 */
  getStatus: (pluginName: string) =>
    request<{ success: boolean; data: PluginInfo }>(
      `/plugins/${encodeURIComponent(pluginName)}/status`,
      { method: 'GET' },
    ),
};


// === Workspace State API (契约版本: v1.0, DEVLOG-055) ===

export interface WorkspaceSaveResult {
  workspace_id: string;
  saved_at: number;
  update_count: number;
}

export interface WorkspaceInfo {
  id: string;
  name: string;
  created_at: number;
  updated_at: number;
  update_count: number;
  tags: string[];
}

export interface WorkspaceSnapshot {
  timestamp: number;
  filename: string;
  size_bytes: number;
}

export const workspaceStateApi = {
  save: (workspaceId: string, state: Record<string, any>, name?: string, tags?: string[]) =>
    request<{ success: boolean; data: WorkspaceSaveResult }>(
      '/workspace-state/save',
      { method: 'POST', body: JSON.stringify({ workspace_id: workspaceId, state, name, tags }) },
    ),

  restore: (workspaceId: string, snapshotTimestamp?: number) =>
    request<{ success: boolean; data: { workspace_id: string; saved_at: number; state: any } }>(
      '/workspace-state/restore',
      { method: 'POST', body: JSON.stringify({ workspace_id: workspaceId, snapshot_timestamp: snapshotTimestamp }) },
    ),

  list: (_tag?: string) =>
    request<{ success: boolean; data: WorkspaceInfo[] }>(
      '/workspace-state/list',
      { method: 'GET' },
    ),

  delete: (workspaceId: string) =>
    request<{ success: boolean; message: string }>(
      `/workspace-state/${workspaceId}`,
      { method: 'DELETE' },
    ),

  getSnapshots: (workspaceId: string) =>
    request<{ success: boolean; data: WorkspaceSnapshot[] }>(
      `/workspace-state/${workspaceId}/snapshots`,
      { method: 'GET' },
    ),

  export: (workspaceId: string, includeSnapshots = false) =>
    request<{ success: boolean; data: any }>(
      '/workspace-state/export',
      { method: 'POST', body: JSON.stringify({ workspace_id: workspaceId, include_snapshots: includeSnapshots }) },
    ),

  import: (workspaceId: string, data: any, overwrite = false) =>
    request<{ success: boolean; data: WorkspaceSaveResult }>(
      '/workspace-state/import',
      { method: 'POST', body: JSON.stringify({ workspace_id: workspaceId, data, overwrite }) },
    ),
};


// === Version History API (契约版本: v1.0, DEVLOG-055) ===

export interface VersionInfo {
  version_id: string;
  version_num: number;
  timestamp: number;
  note: string;
  author: string;
  is_full: boolean;
  content_length: number;
}

export interface VersionDetail {
  version_id: string;
  version_num: number;
  timestamp: number;
  note: string;
  author: string;
  content: string;
}

export interface VersionCompareResult {
  version_a: string;
  version_b: string;
  diff: string;
  stats: { added: number; removed: number };
}

export const versionHistoryApi = {
  save: (documentId: string, content: string, note?: string, author?: string) =>
    request<{ success: boolean; data: VersionInfo }>(
      '/version-history/save',
      { method: 'POST', body: JSON.stringify({ document_id: documentId, content, note, author }) },
    ),

  getLatest: (documentId: string) =>
    request<{ success: boolean; data: VersionDetail }>(
      `/version-history/${documentId}/latest`,
      { method: 'GET' },
    ),

  getVersion: (documentId: string, versionId: string) =>
    request<{ success: boolean; data: VersionDetail }>(
      `/version-history/${documentId}/versions/${versionId}`,
      { method: 'GET' },
    ),

  list: (documentId: string) =>
    request<{ success: boolean; data: VersionInfo[] }>(
      `/version-history/${documentId}/list`,
      { method: 'GET' },
    ),

  compare: (documentId: string, versionA: string, versionB: string) =>
    request<{ success: boolean; data: VersionCompareResult }>(
      '/version-history/compare',
      { method: 'POST', body: JSON.stringify({ document_id: documentId, version_a: versionA, version_b: versionB }) },
    ),

  restore: (documentId: string, versionId: string, note?: string) =>
    request<{ success: boolean; data: VersionInfo }>(
      '/version-history/restore',
      { method: 'POST', body: JSON.stringify({ document_id: documentId, version_id: versionId, note }) },
    ),
};


// === Writing Templates API (契约版本: v1.0, DEVLOG-055) ===

export interface WritingTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  sections: { title: string; description: string; required: boolean }[];
  style: Record<string, any>;
  is_builtin: boolean;
  created_at?: number;
}

export const writingTemplatesApi = {
  list: (_category?: string, _tag?: string, _search?: string) =>
    request<{ success: boolean; data: WritingTemplate[] }>(
      '/writing-templates/list',
      { method: 'GET' },
    ),

  get: (templateId: string) =>
    request<{ success: boolean; data: WritingTemplate }>(
      `/writing-templates/${templateId}`,
      { method: 'GET' },
    ),

  create: (template: Partial<WritingTemplate>) =>
    request<{ success: boolean; data: { id: string; created: boolean } }>(
      '/writing-templates/create',
      { method: 'POST', body: JSON.stringify(template) },
    ),

  update: (templateId: string, updates: Partial<WritingTemplate>) =>
    request<{ success: boolean; data: WritingTemplate }>(
      `/writing-templates/${templateId}`,
      { method: 'PUT', body: JSON.stringify(updates) },
    ),

  delete: (templateId: string) =>
    request<{ success: boolean; message: string }>(
      `/writing-templates/${templateId}`,
      { method: 'DELETE' },
    ),

  getCategories: () =>
    request<{ success: boolean; data: string[] }>(
      '/writing-templates/categories',
      { method: 'GET' },
    ),
};


// === Monitoring API (契约版本: v1.0, DEVLOG-059) ===

export interface HealthScore {
  overall: number;
  api_latency: number;
  error_rate: number;
  resource_usage: number;
  details: Record<string, any>;
}

export interface RequestStats {
  total_requests: number;
  period_minutes: number;
  error_count: number;
  error_rate: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p99_latency_ms: number;
  by_status: Record<number, number>;
  by_endpoint: Record<string, {
    count: number;
    avg_ms: number;
    p50_ms: number;
    p99_ms: number;
    max_ms: number;
    error_count: number;
  }>;
}

export interface SystemStats {
  current: {
    timestamp: number;
    cpu_percent: number;
    memory_percent: number;
    memory_used_mb: number;
    memory_total_mb: number;
    disk_percent: number;
    disk_used_gb: number;
    disk_total_gb: number;
    thread_count: number;
  } | null;
  period_minutes: number;
  avg_cpu?: number;
  peak_cpu?: number;
  avg_memory_percent?: number;
  peak_memory_percent?: number;
}

export interface WebVitalsStats {
  total_reports: number;
  period_minutes: number;
  metrics: Record<string, {
    count: number;
    avg: number;
    p50: number;
    p75: number;
    p99: number;
    worst: number;
  }>;
}

export interface DashboardData {
  health: HealthScore;
  requests: RequestStats;
  system: SystemStats;
  web_vitals: WebVitalsStats;
  slowest_endpoints: { path: string; count: number; avg_ms: number; p99_ms: number; max_ms: number; error_count: number }[];
  top_errors: { error: string; count: number }[];
}

export const monitoringApi = {
  getDashboard: () =>
    request<{ success: boolean; data: DashboardData }>(
      '/monitoring/dashboard',
      { method: 'GET' },
    ),

  getHealth: () =>
    request<{ success: boolean; data: HealthScore }>(
      '/monitoring/health',
      { method: 'GET' },
    ),

  getRequests: (minutes = 60) =>
    request<{ success: boolean; data: RequestStats }>(
      `/monitoring/requests?minutes=${minutes}`,
      { method: 'GET' },
    ),

  getSystem: (minutes = 60) =>
    request<{ success: boolean; data: SystemStats }>(
      `/monitoring/system?minutes=${minutes}`,
      { method: 'GET' },
    ),

  getWebVitals: (minutes = 60) =>
    request<{ success: boolean; data: WebVitalsStats }>(
      `/monitoring/web-vitals?minutes=${minutes}`,
      { method: 'GET' },
    ),

  reportWebVital: (metricName: string, value: number, url?: string) =>
    request<{ success: boolean; message: string }>(
      '/monitoring/web-vitals',
      { method: 'POST', body: JSON.stringify({ metric_name: metricName, value, url: url || '' }) },
    ),

  getSlowest: (limit = 5) =>
    request<{ success: boolean; data: { path: string; count: number; avg_ms: number; p99_ms: number; max_ms: number; error_count: number }[] }>(
      `/monitoring/slowest?limit=${limit}`,
      { method: 'GET' },
    ),

  getErrors: (limit = 5) =>
    request<{ success: boolean; data: { error: string; count: number }[] }>(
      `/monitoring/errors?limit=${limit}`,
      { method: 'GET' },
    ),
};

// === DBLP 会议论文检索 API ===

export interface DBLPPaper {
  title: string;
  authors: string[];
  year: number;
  venue: string;
  doi: string;
  url: string;
  type: string;
  key: string;
}

export interface DBLPSearchResult {
  results: DBLPPaper[];
  total: number;
  returned: number;
  query: string;
  error?: string;
}

export const dblpApi = {
  search: (q: string, limit = 30, yearFrom?: number, yearTo?: number, venue?: string) => {
    const params = new URLSearchParams({ q, limit: String(limit) });
    if (yearFrom) params.set('year_from', String(yearFrom));
    if (yearTo) params.set('year_to', String(yearTo));
    if (venue) params.set('venue', venue);
    return request<DBLPSearchResult>(`/dblp/search?${params}`);
  },

  searchByAuthor: (author: string, limit = 30) =>
    request<DBLPSearchResult>(`/dblp/search-by-author?author=${encodeURIComponent(author)}&limit=${limit}`),

  conferencePapers: (conference: string, year: number, keyword?: string, limit = 50) => {
    const params = new URLSearchParams({ conference, year: String(year), limit: String(limit) });
    if (keyword) params.set('keyword', keyword);
    return request<DBLPSearchResult>(`/dblp/conference?${params}`);
  },

  listConferences: () =>
    request<{ conferences: Record<string, string[]> }>('/dblp/conferences'),

  importPapers: (papers: DBLPPaper[]) =>
    request<{ imported: number; skipped: number }>('/dblp/import', {
      method: 'POST',
      body: JSON.stringify({ papers }),
    }),
};

// ==================== Citations API ====================
export const citationsApi = {
  extract: (paperId: number, format: string = 'gbt7714') =>
    request<{ references: Array<Record<string, unknown>>; count: number; format: string }>('/citations/extract', {
      method: 'POST',
      body: JSON.stringify({ paper_id: paperId, format }),
    }),
};

// ==================== Literature Table API ====================
export const literatureTableApi = {
  generate: (paperIds: number[], columns?: string[]) =>
    request<{ columns: Array<{ key: string; label: string; source: string }>; data: Array<Record<string, unknown>>; paper_count: number }>('/literature-table/generate', {
      method: 'POST',
      body: JSON.stringify({ paper_ids: paperIds, columns }),
    }),
  exportCsv: (paperIds: number[], columns?: string[]) =>
    fetch('/api/literature-table/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paper_ids: paperIds, columns }),
    }),
};

// ==================== Literature Review API ====================
export const literatureReviewApi = {
  generateOutline: (topic: string, paperIds: number[]) =>
    request<{ outline: Record<string, unknown>; paper_count: number }>('/literature-review/outline', {
      method: 'POST',
      body: JSON.stringify({ topic, paper_ids: paperIds }),
    }),
  writeSection: (topic: string, sectionHeading: string, paperIds: number[]) =>
    request<{ section: string; content: string }>('/literature-review/section', {
      method: 'POST',
      body: JSON.stringify({ topic, section_heading: sectionHeading, paper_ids: paperIds }),
    }),
  generateStream: (topic: string, paperIds: number[], style: string = 'narrative') =>
    `/api/literature-review/generate?topic=${encodeURIComponent(topic)}&paper_ids=${paperIds.join(',')}&style=${style}`,
};

export const brainstormApi = {
  generate: (paperIds: number[], focus?: string) =>
    request<{ content: string; paper_count: number; focus?: string }>('/brainstorm/generate', {
      method: 'POST',
      body: JSON.stringify({ paper_ids: paperIds, focus: focus || null }),
    }),
  generateStream: () => '/api/brainstorm/generate/stream',
};
