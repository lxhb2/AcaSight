# AcaSight 学术视界 - 使用指南

> 版本：1.0 | 更新：2026-05-28
> 架构：Vite + React 前端 + FastAPI 后端 + SQLite + RAG 知识库

---

## 一、系统要求

| 组件 | 要求 |
|------|------|
| OS | Windows 10/11、macOS 12+、Linux |
| Node.js | v18+（推荐 v22） |
| Python | 3.10+（推荐 3.12） |
| 内存 | ≥8GB |
| 浏览器 | Chrome/Edge 90+（本地访问用） |

---

## 二、快速启动

### 2.1 一键启动（推荐）

直接双击运行项目根目录的 `start.bat`（Windows），会自动启动前后端。

```bash
# 手动启动（分两个终端）

# 终端1：启动后端
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# 终端2：启动前端
cd frontend
npm run dev
```

启动后访问：**http://localhost:5173**

---

## 三、后端 API 文档

后端启动后，自动生成交互式文档：

- **Swagger UI**：http://localhost:9000/api/docs
- **ReDoc**：http://localhost:9000/api/redoc

### 主要 API 路由

| 路由 | 功能 |
|------|------|
| `/api/papers` | 文献 CRUD（列表、创建、更新、删除） |
| `/api/papers/tags` | 标签管理 |
| `/api/papers/search` | 本地文献全文搜索 |
| `/api/papers/stats` | 文献库统计 |
| `/api/search` | 外部学术搜索（OpenAlex、Semantic Scholar等） |
| `/api/search/import` | 搜索结果→本地库（C.2 入库） |
| `/api/zotero` | Zotero 集成 |
| `/api/notes` | 笔记管理 |
| `/api/storage` | 文件存储 |
| `/api/sync` | 数据同步 |
| `/api/chart/auto` | 智能图表生成 |

---

## 四、前端界面说明

### 4.1 主界面布局

```
┌─────────────────────────────────────────────┐
│  顶部工具栏：搜索框 | 通知 | 设置          │
├──────────┬──────────────────────────────────┤
│          │                                  │
│  左侧    │  主内容区                        │
│  侧边栏  │  （根据选中的视图动态切换）       │
│          │                                  │
│ • 文件   │  FileExplorerView：文献管理      │
│ • 标签   │  TagsView：标签云               │
│ • 大纲   │  OutlineView：文档大纲          │
│ • 书签   │  BookmarksView：收藏            │
│ • 图谱   │  GraphView：知识图谱            │
│ • 搜索   │  SearchPage：学术搜索 + 入库    │
│ • AI    │  AIChatPanel：AI 对话           │
└──────────┴──────────────────────────────────┘
```

### 4.2 各视图功能

**FileExplorerView（文献管理）**
- 文献列表：支持搜索、标签筛选、收藏筛选、年份筛选
- 右键菜单：修改阅读状态、评分、标签管理
- 操作：导入 Zotero、删除、打开 PDF

**SearchPage（学术搜索）**
- 支持 6 个数据源：CORE、OpenAlex、Semantic Scholar、Crossref、Europe PMC、arXiv
- 可按年份、来源筛选
- 搜索结果支持一键「入库」（写入本地数据库，自动 DOI 去重）
- 支持「保存至 Zotero」
- 可展开查看摘要、引用数、期刊等信息
- 底部图表：引用数 Top15、数据源分布、年份分布

**TagsView（标签云）**
- 显示所有标签及对应文献数
- 点击标签：筛选该标签下的所有文献
- 颜色自动分配

**AIChatPanel（AI 对话）**
- 支持 Markdown 渲染（react-markdown + remark-gfm + rehype-katex）
- 支持多轮对话
- 可选联网搜索

---

## 五、配置说明

### 5.1 后端配置

编辑 `backend/.env`（参考 `.env.example`）：

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./data/acasight.db

# AI 模型（可选）
DEFAULT_PROVIDER=ollama
DEFAULT_MODEL=qwen3.5:0.8b
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1

# Zotero（可选）
ZOTERO_API_KEY=xxx
ZOTERO_USER_ID=xxx

# CORE API（可选，免费注册 core.ac.uk）
CORE_API_KEY=xxx
```

### 5.2 前端配置

前端通过 `api.ts` 中的 `BASE_URL` 连接后端，默认：
```
http://localhost:9000/api
```
如需修改，编辑 `frontend/src/services/api.ts` 第 5 行。

### 5.3 AI 配置（SettingsModal）

在界面右上角点击「设置」→「AI 配置」：
- 支持多个 Provider：OpenAI、Ollama、DeepSeek、Claude 等
- 可配置 API Key、Base URL、默认模型
- 配置自动保存到后端数据库

---

## 六、数据源说明

| 数据源 | 说明 | 免费 |
|--------|------|------|
| CORE | 3亿+开放获取论文全文 | ✅ |
| OpenAlex | 开放学术数据，引用数准确 | ✅ |
| Semantic Scholar | AI 驱动的学术搜索 | ✅ |
| Crossref | DOI 官方注册机构 | ✅ |
| Europe PMC | 欧洲 PubMed Central | ✅ |
| arXiv | 预印本论文库 | ✅ |

> 无需 API Key 即可使用。CORE 全文下载需注册免费 API Key。

---

## 七、常见问题

### Q1：端口 5173 或 9000 被占用？
修改前端端口：`frontend/vite.config.ts` 中 `server.port`
修改后端端口：启动时 `--port 9001`

### Q2：搜索无结果？
检查后端是否正常运行，查看 http://localhost:9000/api/docs 的 `/api/search` 端点。

### Q3：PDF 无法打开？
确认 PDF 文件路径正确，且文件存在。AcaSight 支持 PDF.js 渲染。

### Q4：如何备份文献数据库？
直接复制 `backend/data/acasight.db` 文件。

### Q5：Zotero 连接失败？
确认 Zotero 桌面版正在运行，且已安装「Better BibTeX」插件（如需引用导出）。

---

## 八、开发指南

### 8.1 项目结构

```
AcaSight/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── routers/             # API 路由
│   │   ├── services/            # 业务逻辑
│   │   └── database.py         # 数据库连接
│   ├── data/                    # SQLite 数据库
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/         # React 组件
│   │   │   ├── Views/          # 各主视图
│   │   │   ├── Search/         # 搜索页面
│   │   │   └── ...
│   │   ├── services/           # API 客户端
│   │   ├── contexts/           # React Context
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── docs/                        # 设计文档
├── task-artifacts/              # 开发记录
└── start.bat                    # 一键启动脚本
```

### 8.2 技术栈

**前端**
- React 18 + TypeScript
- Vite（构建工具）
- Tailwind CSS（样式）
- Plotly.js（图表）
- PDF.js（PDF 渲染）
- react-markdown + remark-gfm + rehype-katex（Markdown 渲染）

**后端**
- FastAPI（Python Web 框架）
- SQLAlchemy + AsyncSession（ORM）
- SQLite（开发）/ PostgreSQL（生产）
- httpx（异步 HTTP 客户端）
- PyPDF2 / pdfplumber（PDF 处理）

### 8.3 常用命令

```bash
# 前端开发
cd frontend && npm run dev        # 开发模式（HMR）
cd frontend && npm run build      # 生产构建
cd frontend && npm run preview   # 预览生产构建

# 后端开发
cd backend
python -m uvicorn app.main:app --reload   # 热重载

# 数据库迁移（手动）
# 删除 backend/data/acasight.db 后重启后端，自动重建表结构
```

---

## 九、更新日志

### v1.0（2026-05-28）
- ✅ Chapter B：数据库驱动重构（FileExplorerView、TagsView、OutlineView 等）
- ✅ Chapter C：搜索→入库（SearchPage 集成 6 大数据源）
- ✅ C.2：searchApi.importPaper 后端端点（DOI 去重）
- ✅ C.3：前端入库 UI（已入库/已存在状态区分）
- ✅ AI 聊天面板 Markdown 渲染
- ✅ SettingsModal Cherry Studio 风格重构
- ✅ 学术搜索图表（引用数 Top15、数据源饼图、年份分布）

---

## 十、联系方式

- 问题反馈：通过 Gitee Issues 或 GitHub Issues
- Gitee：https://gitee.com/lxhb1/AcaSight
- GitHub：https://github.com/lxhb2/AcaSight
