# AcaSight 技术架构详解

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Electron 主进程                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ 窗口管理     │  │ 菜单/托盘    │  │ 系统服务 (文件/通知)     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ IPC 通信
┌─────────────────────────────────────────────────────────────────┐
│                      Electron 渲染进程                           │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    React 应用                              │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │ │
│  │  │ 路由管理  │  │ 状态管理  │  │ UI 组件  │  │ 服务层   │ │ │
│  │  │(Router)  │  │(Zustand) │  │(shadcn) │  │(API)    │ │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐  │ │
│  │  │              功能模块                                 │  │ │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │  │ │
│  │  │  │PDF阅读 │ │论文管理│ │AI助手  │ │笔记编辑│      │  │ │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘      │  │ │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │  │ │
│  │  │  │文献检索│ │数据分析│ │浏览器  │ │Office  │      │  │ │
│  │  │  └────────┘ └────────┘ └────────┘ └────────┘      │  │ │
│  │  └─────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                      本地服务层 (可选)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ FastAPI     │  │ 文件服务     │  │ AI 服务 (Ollama)        │ │
│  │ (复杂功能)   │  │ (静态文件)   │  │ (本地模型)              │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 二、核心设计决策

### 2.1 为什么用 Electron 而不是纯 Web？

| 需求 | Electron | 纯 Web |
|-----|----------|--------|
| 本地文件访问 | ✅ 直接访问 | ❌ 需要上传 |
| PDF 渲染性能 | ✅ 原生体验 | ⚠️ 受限 |
| 本地数据库 | ✅ SQLite | ❌ IndexedDB |
| 系统集成 | ✅ 深度集成 | ❌ 有限 |
| 离线使用 | ✅ 完全离线 | ⚠️ PWA |
| 打包分发 | ✅ 独立应用 | ❌ 依赖浏览器 |

### 2.2 为什么 AI 是被动触发？

```
主动式 AI (不推荐):
用户打开论文 → AI 自动分析 → 弹出总结
问题: 打扰用户，消耗资源，可能不需要

被动式 AI (推荐):
用户打开论文 → 安静阅读 → 用户选中文字 → 显示 AI 按钮 → 用户点击 → AI 响应
优势: 尊重用户，按需使用，节省资源
```

### 2.3 为什么参考 Obsidian？

- **侧边栏导航**: 功能清晰，快速切换
- **标签页系统**: 多文档同时打开
- **插件架构**: 易于扩展
- **本地优先**: 数据本地存储
- **Markdown**: 通用格式

## 三、模块详细设计

### 3.1 PDF 阅读器模块

```typescript
// PDFReader.tsx
interface PDFReaderProps {
  pdfPath: string;
  onTextSelect: (text: string, rect: DOMRect) => void;
}

// 三栏布局
const PDFReader: React.FC<PDFReaderProps> = ({ pdfPath }) => {
  const [thumbnails, setThumbnails] = useState<Thumbnail[]>();
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedText, setSelectedText] = useState('');
  const [showAIToolbar, setShowAIToolbar] = useState(false);
  
  return (
    <div className="flex h-full">
      {/* 缩略图栏 */}
      <ThumbnailPanel 
        pages={thumbnails}
        currentPage={currentPage}
        onPageClick={setCurrentPage}
      />
      
      {/* 主阅读区 */}
      <MainViewer
        pdfPath={pdfPath}
        currentPage={currentPage}
        onTextSelect={(text, rect) => {
          setSelectedText(text);
          setShowAIToolbar(true);
          setToolbarPosition(rect);
        }}
      />
      
      {/* AI/笔记区 */}
      <SidePanel>
        <AITab />
        <NotesTab />
      </SidePanel>
      
      {/* 悬浮 AI 工具栏 */}
      {showAIToolbar && (
        <AIToolbar
          position={toolbarPosition}
          onExplain={() => aiService.explain(selectedText)}
          onTranslate={() => aiService.translate(selectedText)}
          onSummarize={() => aiService.summarize(selectedText)}
        />
      )}
    </div>
  );
};
```

### 3.2 AI 服务模块

```typescript
// aiService.ts
interface AIService {
  // 文本功能
  explain(text: string): Promise<string>;
  translate(text: string, targetLang: string): Promise<string>;
  summarize(text: string): Promise<string>;
  
  // 论文功能
  analyzePaper(paperId: string): Promise<PaperAnalysis>;
  findResearchGaps(papers: Paper[]): Promise<string>;
  recommendPapers(paperId: string): Promise<Paper[]>;
  
  // 写作功能
  continueWriting(text: string): Promise<string>;
  polishText(text: string): Promise<string>;
  
  // 对话
  chat(messages: Message[]): AsyncGenerator<string>;
}

// 本地优先策略
class LocalFirstAIService implements AIService {
  private ollama: OllamaClient;
  private cloud: CloudAIClient;
  
  async explain(text: string): Promise<string> {
    // 优先使用本地模型
    if (await this.ollama.isAvailable()) {
      return this.ollama.explain(text);
    }
    // 回退到云端
    return this.cloud.explain(text);
  }
}
```

### 3.3 文献检索模块

```typescript
// searchService.ts
interface SearchService {
  search(query: string, options: SearchOptions): Promise<SearchResult>;
  downloadPDF(paperId: string): Promise<string>; // 返回本地路径
  importToLibrary(paperId: string, projectId?: string): Promise<void>;
}

// 多源聚合
class AggregatedSearchService implements SearchService {
  private sources: SearchSource[] = [
    new OpenAlexSource(),
    new SemanticScholarSource(),
    new ArxivSource(),
  ];
  
  async search(query: string, options: SearchOptions): Promise<SearchResult> {
    // 并行搜索
    const results = await Promise.all(
      this.sources.map(s => s.search(query, options))
    );
    
    // 去重合并
    return this.mergeAndDeduplicate(results);
  }
}
```

## 四、数据存储设计

### 4.1 SQLite 数据库

```sql
-- 核心表
CREATE TABLE papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors JSON,
    abstract TEXT,
    doi TEXT,
    year INTEGER,
    journal TEXT,
    pdf_path TEXT,
    local_path TEXT, -- 本地存储路径
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_papers (
    project_id TEXT REFERENCES projects(id),
    paper_id TEXT REFERENCES papers(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, paper_id)
);

CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    paper_id TEXT REFERENCES papers(id),
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE annotations (
    id TEXT PRIMARY KEY,
    paper_id TEXT REFERENCES papers(id),
    page INTEGER,
    type TEXT, -- highlight, underline, note
    rect JSON, -- {x, y, width, height}
    color TEXT,
    content TEXT
);
```

### 4.2 文件系统

```
~/AcaSight/
├── config.json
├── database.sqlite
├── papers/
│   ├── {paper_id}/
│   │   ├── paper.pdf
│   │   ├── notes.md
│   │   └── annotations.json
│   └── ...
├── projects/
│   ├── {project_id}/
│   │   ├── papers/ (symlink)
│   │   ├── notes/
│   │   └── exports/
│   └── ...
└── vectors/ (Qdrant 数据)
```

## 五、AI 集成架构

### 5.1 本地优先策略

```
用户请求
    │
    ▼
检查本地 Ollama
    │
    ├──→ 可用 ──→ 使用本地模型
    │               (Llama/Qwen/DeepSeek)
    │
    └──→ 不可用 ──→ 检查云端配置
                    │
                    ├──→ 有配置 ──→ 使用云端 API
                    │               (OpenRouter/DeepSeek)
                    │
                    └──→ 无配置 ──→ 提示用户配置
```

### 5.2 RAG 流程

```
用户提问
    │
    ▼
向量化查询
    │
    ▼
检索相关文献片段 (Qdrant)
    │
    ▼
构建上下文
    │
    ▼
调用 LLM 生成回答
    │
    ▼
返回结果 + 引用来源
```

## 六、扩展性设计

### 6.1 插件系统

```typescript
// 插件接口
interface Plugin {
  id: string;
  name: string;
  version: string;
  
  // 生命周期
  activate(): void;
  deactivate(): void;
  
  // 扩展点
  registerSidebarItem?(): SidebarItem;
  registerCommand?(): Command[];
  registerSetting?(): SettingTab;
}

// 加载插件
class PluginManager {
  private plugins: Map<string, Plugin> = new Map();
  
  async loadPlugin(path: string): Promise<void> {
    const plugin = await import(path);
    plugin.activate();
    this.plugins.set(plugin.id, plugin);
  }
}
```

### 6.2 主题系统

```typescript
// 主题配置
interface Theme {
  name: string;
  colors: {
    background: string;
    surface: string;
    primary: string;
    text: string;
    border: string;
  };
  typography: {
    fontFamily: string;
    fontSize: number;
    lineHeight: number;
  };
}

// 内置主题
const themes: Theme[] = [
  {
    name: 'light',
    colors: {
      background: '#ffffff',
      surface: '#f5f5f5',
      primary: '#3b82f6',
      text: '#1f2937',
      border: '#e5e7eb',
    },
    // ...
  },
  {
    name: 'dark',
    colors: {
      background: '#1a1a1a',
      surface: '#2d2d2d',
      primary: '#60a5fa',
      text: '#e5e7eb',
      border: '#404040',
    },
    // ...
  },
  {
    name: 'obsidian',
    colors: {
      background: '#202020',
      surface: '#2a2a2a',
      primary: '#7c3aed',
      text: '#dcddde',
      border: '#333333',
    },
    // ...
  },
];
```

## 七、性能优化

### 7.1 PDF 渲染优化

```typescript
// 虚拟滚动
const VirtualPDFViewer: React.FC = () => {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 5 });
  
  return (
    <VirtualList
      itemCount={totalPages}
      itemHeight={800}
      renderItem={(index) => (
        <PDFPage
          pageNumber={index + 1}
          isVisible={index >= visibleRange.start && index <= visibleRange.end}
        />
      )}
      onVisibleRangeChange={setVisibleRange}
    />
  );
};

// 懒加载页面
const PDFPage: React.FC<{ pageNumber: number; isVisible: boolean }> = ({
  pageNumber,
  isVisible,
}) => {
  const [rendered, setRendered] = useState(false);
  
  useEffect(() => {
    if (isVisible && !rendered) {
      renderPage(pageNumber).then(() => setRendered(true));
    }
  }, [isVisible]);
  
  if (!rendered) return <Placeholder />;
  return <canvas ref={canvasRef} />;
};
```

### 7.2 搜索优化

```typescript
// 本地索引
class LocalSearchIndex {
  private index: MiniSearch;
  
  constructor() {
    this.index = new MiniSearch({
      fields: ['title', 'abstract', 'authors', 'tags'],
      storeFields: ['title', 'year', 'journal'],
    });
  }
  
  addPaper(paper: Paper): void {
    this.index.add({
      id: paper.id,
      title: paper.title,
      abstract: paper.abstract,
      authors: paper.authors.join(' '),
      tags: paper.tags.join(' '),
    });
  }
  
  search(query: string): SearchResult[] {
    return this.index.search(query, {
      fuzzy: 0.2,
      prefix: true,
    });
  }
}
```

## 八、安全设计

### 8.1 本地数据安全

```typescript
// 数据加密
class SecureStorage {
  private key: CryptoKey;
  
  async encrypt(data: string): Promise<Buffer> {
    const encoder = new TextEncoder();
    const encrypted = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv: this.generateIV() },
      this.key,
      encoder.encode(data)
    );
    return Buffer.from(encrypted);
  }
  
  async decrypt(data: Buffer): Promise<string> {
    const decrypted = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: this.extractIV(data) },
      this.key,
      data
    );
    return new TextDecoder().decode(decrypted);
  }
}
```

### 8.2 AI 数据隐私

```
本地模型 (Ollama):
- 数据完全本地处理
- 不上传任何信息
- 适合敏感研究

云端模型:
- 仅发送必要文本
- 不发送完整文档
- 支持自托管 API
```

## 九、部署方案

### 9.1 开发环境

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/acasight.git
cd acasight

# 2. 安装依赖
npm install

# 3. 安装 Ollama (本地 AI)
# macOS
brew install ollama
# Windows
winget install Ollama.Ollama
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# 4. 拉取模型
ollama pull llama2
ollama pull qwen

# 5. 启动开发
npm run dev
```

### 9.2 生产构建

```bash
# 构建桌面应用
npm run build:electron

# 打包
npm run dist

# 输出
/dist/
  ├── AcaSight-1.0.0.dmg      (macOS)
  ├── AcaSight-1.0.0.exe      (Windows)
  └── AcaSight-1.0.0.AppImage (Linux)
```

---

*文档版本: v1.0*
*最后更新: 2026-05-18*
*状态: 架构设计完成*
