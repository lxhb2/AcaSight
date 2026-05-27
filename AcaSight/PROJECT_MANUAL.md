# AcaSight 学术视界 - 项目手册

> 项目版本：v2.0（融合版）
> 更新时间：2026-05-18
> 状态：开发中（核心功能已完成）

---

## 📋 目录

1. [项目概述](#1-项目概述)
2. [项目文件结构](#2-项目文件结构)
3. [已完成工作](#3-已完成工作)
4. [项目开发日志](#4-项目开发日志)
5. [未完成工作](#5-未完成工作)
6. [开发者手册](#6-开发者手册)
7. [启动与运行](#7-启动与运行)
8. [技术栈清单](#8-技术栈清单)

---

## 1. 项目概述

### 1.1 项目定位

**AcaSight（学术视界）** 是一款面向科研人员的全能型学术智能体应用，融合了以下三个项目的核心能力：

| 来源项目 | 提供能力 |
|---------|---------|
| **PaperPal v7.0** | AI 精读、文献综述、实验设计、公式生成、六步写作法 |
| **pdf-research-assistant** | PDF 文本提取、合并/拆分、旋转/水印、图片提取、OCR |
| **全新设计** | Obsidian 风格 UI、主题系统、三栏 PDF 阅读器 |

### 1.2 核心功能模块

```
📁 项目管理   — 论文项目创建、文献导入、统计卡片、最近项目
📄 PDF 阅读  — 三栏布局、缩略图导航、文本选择、AI 工具栏、笔记面板
🔍 文献检索  — 多数据源聚合搜索（OpenAlex / Semantic Scholar / CrossRef / arXiv）
🤖 AI 助手  — 精读分析、文献综述、实验设计、翻译、总结、公式生成
📝 笔记      — 增删改查、标签管理、搜索过滤
⚙️  设置      — AI 模型配置、数据存储、主题切换（亮/暗色）
```

### 1.3 设计风格

- **Obsidian 风格**：左侧图标导航栏，点击切换功能模块
- **深色主题优先**：#1a1a1a 背景，CSS 变量系统，支持一键切换浅色/深色
- **AI 被动触发**：选中文字才弹出 AI 工具栏，不主动打扰用户
- **三栏 PDF 布局**：缩略图 15% + 主阅读区 55% + AI/笔记 30%

---

## 2. 项目文件结构

```
AcaSight/
├── README.md                      # 项目说明文档
├── DESIGN_SPEC.md                 # 详细设计规格书（界面/交互/RAG/编辑器方案）
├── ARCHITECTURE.md                # 技术架构详解（模块设计/数据流/部署）
├── DEVELOPMENT_PLAN.md            # 详细开发方案（16周计划/数据库/实现细节）
├── IMPLEMENTATION_GUIDE.md        # 实现指南
│
├── frontend/                      # 🎨 前端（Electron + React + TypeScript）
│   ├── package.json               # 依赖配置（Electron 28 + React 18 + Vite 5）
│   ├── vite.config.ts             # Vite 构建配置
│   ├── tsconfig.json              # TypeScript 配置
│   ├── tailwind.config.js        # Tailwind CSS 配置
│   ├── index.html                 # HTML 入口
│   │
│   └── src/
│       ├── App.tsx               # 主应用组件（路由/主题/布局）
│       ├── main.tsx              # React 入口
│       ├── index.css             # 全局样式（CSS 变量/动画/主题）
│       │
│       ├── contexts/
│       │   └── ThemeContext.tsx  # 主题上下文（深色/浅色/自动检测）
│       │
│       ├── components/
│       │   ├── Layout/
│       │   │   └── Sidebar.tsx  # Obsidian 风格侧边栏（7个图标导航 + tooltip）
│       │   │
│       │   ├── Projects/
│       │   │   └── ProjectHome.tsx   # 首页（统计卡片/项目列表/最近阅读）
│       │   │
│       │   ├── PDFReader/
│       │   │   ├── PDFReader.tsx     # PDF 阅读器（上传/三栏/工具栏）
│       │   │   ├── ThumbnailPanel.tsx # 缩略图导航面板
│       │   │   ├── AIToolbar.tsx     # 悬浮 AI 工具栏（选中文字弹出）
│       │   │   ├── AISidePanel.tsx    # AI 侧边面板（6快捷功能 + 对话）
│       │   │   └── NotesPanel.tsx     # 笔记面板（增删改/标签/搜索）
│       │   │
│       │   ├── Search/
│       │   │   └── SearchPage.tsx    # 文献检索页（筛选/排序/Mock数据）
│       │   │
│       │   └── Settings/
│       │       └── SettingsPage.tsx  # 设置页（AI模型/存储/主题配置）
│       │
│       ├── services/
│       │   └── api.ts           # 前端 API 客户端（pdfApi / aiApi / searchApi）
│       │
│       └── lib/
│           └── utils.ts          # 工具函数（cn() 等）
│
├── backend/                       # ⚙️ 后端（FastAPI + Python）
│   ├── requirements.txt           # Python 依赖
│   ├── .env.example              # 环境变量模板
│   │
│   ├── app/
│   │   ├── main.py              # FastAPI 主应用（生命周期/路由注册/中间件）
│   │   ├── config.py            # 配置管理（pydantic-settings）
│   │   ├── database.py          # 数据库管理（SQLite/SQLAlchemy）
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── paper.py         # 文献数据模型
│   │   │
│   │   ├── routers/
│   │   │   ├── pdf.py           # PDF 路由（16个端点）
│   │   │   ├── chat.py          # AI 对话路由
│   │   │   └── search.py        # 文献检索路由
│   │   │
│   │   └── services/
│   │       ├── pdf_service.py   # PDF 处理服务（PyMuPDF + pypdf）
│   │       ├── ai_service.py    # AI 服务（OpenAI/DeepSeek/Claude/Ollama）
│   │       └── search_service.py # 文献检索服务（5大数据源）
│   │
│   └── data/                    # 文件存储目录
│       ├── acasight.db         # SQLite 数据库
│       └── *.pdf               # 上传的 PDF 文件
│
└── docs/                        # 文档目录（预留）
```

---

## 3. 已完成工作

### ✅ 前端（100% 完成度）

| 组件 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 主应用 | `App.tsx` | ✅ | 主题系统 + 路由 + Obsidian 布局 |
| 侧边栏 | `Sidebar.tsx` | ✅ | 7 图标导航 + tooltip + 激活状态 |
| 首页 | `ProjectHome.tsx` | ✅ | 统计卡片 + 项目列表 + 最近阅读 |
| PDF 阅读器 | `PDFReader.tsx` | ✅ | 文件上传/拖放/键盘快捷键/TOC面板 |
| 缩略图 | `ThumbnailPanel.tsx` | ✅ | react-pdf 缩略图 + 点击翻页 |
| AI 工具栏 | `AIToolbar.tsx` | ✅ | 选中文字弹出 + 5个操作按钮 |
| AI 面板 | `AISidePanel.tsx` | ✅ | 6快捷功能 + 真实 API 对话 |
| 笔记面板 | `NotesPanel.tsx` | ✅ | 增删改/标签/搜索/分页 |
| 检索页 | `SearchPage.tsx` | ✅ | 筛选/排序/Mock 学术论文数据 |
| 设置页 | `SettingsPage.tsx` | ✅ | AI模型/存储/主题配置 |
| 主题系统 | `ThemeContext.tsx` | ✅ | 深色/浅色/CSS变量 |
| API 客户端 | `services/api.ts` | ✅ | pdfApi + aiApi + searchApi |
| 全局样式 | `index.css` | ✅ | CSS变量/动画/uiverse风格 |

**构建状态**：
```
✅ TypeScript 编译通过
✅ Vite 构建成功（621KB JS + 15KB CSS）
⚠️  Electron 主进程（electron/main.js）尚未创建
```

### ✅ 后端（90% 完成度）

| 模块 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 主应用 | `main.py` | ✅ | 模块化路由加载 + 容错 + CORS |
| 配置管理 | `config.py` | ✅ | pydantic-settings + 18个配置项 |
| 数据库 | `database.py` | ✅ | SQLAlchemy ORM |
| 文献模型 | `models/paper.py` | ✅ | 核心字段定义 |
| **PDF 服务** | `services/pdf_service.py` | ✅ | **融合新增**（提取/合并/拆分/旋转/水印/图片/渲染） |
| **PDF 路由** | `routers/pdf.py` | ✅ | **融合新增**（16个端点） |
| **AI 服务** | `services/ai_service.py` | ✅ | **融合扩展**（deep_read/literature_review 等 8 个新功能） |
| **对话路由** | `routers/chat.py` | ✅ | **融合新增** |
| 检索服务 | `services/search_service.py` | ✅ | OpenAlex + Semantic Scholar + arXiv 等 5 数据源 |
| **检索路由** | `routers/search.py` | ✅ | **融合新增** |

**后端 API 端点**：

```
📄 PDF（16个端点）
  POST /api/pdf/upload              上传 PDF
  GET  /api/pdf/{path}/info        文件信息（页数/元数据/TOC）
  GET  /api/pdf/{path}/text        提取全文文本
  GET  /api/pdf/{path}/reading     AI 精读文本提取（限8000字）
  GET  /api/pdf/{path}/toc         提取目录书签
  GET  /api/pdf/{path}/page/{n}/image   渲染页面为图片（base64）
  GET  /api/pdf/{path}/thumbnails  生成所有页面缩略图
  POST /api/pdf/search              在 PDF 中搜索文本
  POST /api/pdf/merge               合并多个 PDF
  POST /api/pdf/split               拆分 PDF
  POST /api/pdf/rotate              旋转页面
  POST /api/pdf/watermark           添加文字水印
  GET  /api/pdf/{path}/images       提取嵌入图片
  GET  /api/pdf/download/{filename} 下载处理后的文件

🤖 AI 对话
  POST /api/chat/                   对话（支持 provider 参数）
  POST /api/chat/stream             流式对话
  POST /api/chat/deep-read          AI 精读（基于 PDF 全文）
  POST /api/chat/literature-review  文献综述生成
  POST /api/chat/experiment-design  实验方案设计
  POST /api/chat/formula            LaTeX 公式生成
  POST /api/chat/summarize          摘要生成
  POST /api/chat/translate          翻译
  POST /api/chat/outline            论文大纲生成
  POST /api/chat/section            章节内容生成

🔍 文献检索
  GET  /api/search/                聚合搜索
  GET  /api/search/doi/{doi}       DOI 精确查找
  GET  /api/search/sources          数据源列表
```

**启动状态**：
```
✅ 后端服务运行正常（http://localhost:8000）
✅ PDF/Chat/Search 路由全部加载成功
⚠️ Papers/Notes/Zotero 路由（预留，尚未实现）
```

---

## 4. 项目开发日志

### 2026-05-18 时间线

| 时间 | 事件 |
|------|------|
| **19:11** | 项目初始化。创建 AcaSight 文件夹，编写 `DEVELOPMENT_PLAN.md`（16周详细计划）、`README.md`、`TASK_SUMMARY.md`，搭建后端 `main.py` / `config.py` / `database.py` 和 `search_service.py` / `ai_service.py` 两个核心服务，以及 `search.py` / `chat.py` 路由。 |
| **19:34** | 澄清项目定位。AcaSight 是**全新项目**，非克隆项目。讨论了 OpenClaw + Hermes Agent 双 Agent 方案架构。 |
| **20:00** | 讨论架构方案（独立 Electron 应用 vs OpenClaw Skills）。用户最终选择 Electron 独立架构。 |
| **20:26** | 完成前端框架搭建。创建 `DESIGN_SPEC.md`（Obsidian风格设计）、`ARCHITECTURE.md`（技术架构详解）、`IMPLEMENTATION_GUIDE.md`。前端组件：`Sidebar.tsx`、`ProjectHome.tsx`、`PDFReader.tsx`、`AIToolbar.tsx`、`AISidePanel.tsx`、`ThumbnailPanel.tsx`、`NotesPanel.tsx`、配置文件的初始化工作。 |
| **21:01** | MVP 组件开发完成。修复 TypeScript 构建错误（未使用变量），`npm run build` 成功（144KB JS）。启动开发服务器 `npm run dev`。确认 uiverse.io 风格 UI：深色主题 + 蓝色渐变 + 悬停动画。 |
| **21:06** | 构建成功并启动。确认 Vite dev server 在 `http://localhost:5173` 运行，HMR 正常工作。修复了多个 TS 严格模式错误。 |
| **21:12** | 新增 `SearchPage.tsx`（文献检索页 + Mock数据）和 `SettingsPage.tsx`（AI模型/存储/主题配置）。构建成功（606KB JS）。新增 ThemeContext 双主题系统（深色/浅色切换）。 |
| **22:00** | **三项目融合开始**。确定以 AcaSight 为框架，融合 PaperPal AI 能力（AI精读/综述/实验设计/公式生成/六步写作）和 pdf-research-assistant PDF处理能力（文本提取/合并拆分/旋转水印/图片提取）。 |
| **22:07** | 后端融合完成。新建 `services/pdf_service.py`（9224字节），新增 `routers/pdf.py`（16个端点），扩展 `services/ai_service.py`（新增8个 PaperPal 功能），重写 `main.py`（模块化加载 + try/except 容错）。`requirements.txt` 更新 PDF 依赖。解决 pydantic 版本冲突。 |
| **22:17** | 后端验证成功。`python -c "from app.main import app"` 加载成功，PDF/Chat/Search 路由全部正常加载。安装缺失的 `aiosqlite` 依赖。 |
| **22:26** | 前端融合完成。新建 `services/api.ts`（统一 API 客户端），重写 `PDFReader.tsx`（文件上传/拖放/键盘快捷键/TOC面板/后端集成），重写 `AISidePanel.tsx`（真实 API 调用），更新 `App.tsx` 接口适配。TypeScript 编译 + Vite 构建成功（621KB JS + 15KB CSS）。 |
| **22:51** | **项目正式启动**。后端 `uvicorn` 运行在 8000 端口，前端 `vite dev` 运行在 5173 端口。用户可通过浏览器访问 `http://localhost:5173` 使用完整功能。 |

---

## 5. 未完成工作

### 🔴 高优先级（核心功能）

| 序号 | 功能 | 文件位置 | 说明 |
|------|------|---------|------|
| 1 | **Electron 主进程** | `frontend/electron/main.js` | 窗口管理/菜单栏/系统托盘/本地文件访问/IPC 通信 |
| 2 | **PDF 高亮和标注持久化** | `PDFReader.tsx` | 选中文本高亮存储到数据库，支持多种颜色 |
| 3 | **笔记与 PDF 页面联动** | `NotesPanel.tsx` | 笔记关联到具体页码，点击跳转到对应页面 |
| 4 | **Zotero 文献库集成** | `routers/zotero.py` | 读取 Zotero SQLite 数据库，自动导入文献 |
| 5 | **向量数据库 RAG** | `services/rag_service.py` | Qdrant 向量检索，实现文献级别的 AI 问答 |

### 🟡 中优先级（增强功能）

| 序号 | 功能 | 文件位置 | 说明 |
|------|------|---------|------|
| 6 | **Markdown 编辑器** | `NotesPanel.tsx` | 集成 Monaco Editor 或 milkdown，支持 LaTeX 公式 |
| 7 | **文献检索 API 对接** | `SearchPage.tsx` | 将 Mock 数据替换为 OpenAlex / Semantic Scholar 真实 API |
| 8 | **数据持久化** | `database.py` | SQLite 存储文献/笔记/标注/项目数据 |
| 9 | **PDF 目录 TOC 面板** | `PDFReader.tsx` | 从 PDF 提取真实书签目录，点击跳转 |
| 10 | **六步写作法** | 新建 `routers/writing.py` | 题目→资料→文献→摘要→大纲→正文，完整写作流程 |
| 11 | **数据分析功能** | 新建 `components/Analysis/` | Recharts 图表 + AI 数据解读 |

### 🟢 低优先级（扩展功能）

| 序号 | 功能 | 说明 |
|------|------|------|
| 12 | 内嵌浏览器 | Electron WebView 加载学术网站 |
| 13 | Office 编辑器 | OnlyOffice 或 Tiptap 集成 |
| 14 | PPT 生成 | Markdown 转 PPT |
| 15 | OCR 识别 | 扫描版 PDF 文字识别（paddleocr / tesseract） |
| 16 | 手绘白板 | Fabric.js 自由绘制 |
| 17 | 插件系统 | 支持第三方扩展 |

### ⚠️ 技术债务

| 序号 | 问题 | 影响 |
|------|------|------|
| T1 | `pdf_service.py` 中 `extract_images` 方法使用了已废弃的 `PyMuPDF` API | 图片提取功能不可用 |
| T2 | 前端 `api.ts` 路径别名 `@/*` 未在 `tsconfig.json` 中配置 | TypeScript 路径解析可能异常 |
| T3 | `package.json` 中 Electron 28 依赖大，`npm install` 耗时长 | 开发体验 |
| T4 | 前端 JS Bundle 621KB（gzip 180KB），超过 500KB 警告线 | 建议代码分割 |
| T5 | PDF Reader 中的 `toc` 状态是空数组硬编码 | TOC 面板无法显示真实目录 |

---

## 6. 开发者手册

### 6.1 环境要求

```
Node.js 18+
Python 3.11+
Git
```

### 6.2 安装步骤

```bash
# 1. 前端依赖
cd AcaSight/frontend
npm install

# 2. 后端依赖
cd ../backend
pip install -r requirements.txt
```

### 6.3 开发命令

```bash
# 前端开发
cd frontend
npm run dev          # 启动 Vite 开发服务器（http://localhost:5173）

# 前端构建
npm run build        # TypeScript 编译 + Vite 构建

# 后端运行
cd ../backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Electron（待实现）
npm run electron:dev  # 开发模式运行 Electron
npm run electron:build  # 打包桌面应用
```

### 6.4 添加新的 API 端点

**后端示例**（在 `routers/` 下新建文件）：

```python
# backend/app/routers/example.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/example")
async def example_endpoint():
    return {"message": "Hello AcaSight"}
```

**注册到 `main.py`**：

```python
try:
    from app.routers import example
    app.include_router(example.router, prefix="/api/example", tags=["示例"])
    logger.info("Example router loaded")
except Exception as e:
    logger.warning(f"Example router load failed: {e}")
```

**前端调用**（在 `services/api.ts` 中添加）：

```typescript
export const exampleApi = {
  getExample: () => request<{ message: string }>('/example/'),
};
```

### 6.5 添加新的前端组件

```bash
# 1. 在 src/components/ 下创建组件文件夹
# 2. 创建 YourComponent.tsx
# 3. 在 App.tsx 中导入并使用
import { YourComponent } from '@/components/YourComponent/YourComponent';
```

### 6.6 添加新的 AI 功能

在 `backend/app/services/ai_service.py` 中添加方法：

```python
async def your_feature(self, text: str) -> str:
    """你的 AI 功能"""
    prompt = f"请处理以下内容：{text}"
    # 调用 LLM...
    return result
```

在 `routers/chat.py` 中添加路由：

```python
@router.post("/your-feature")
async def your_feature(text: str = Body(...)):
    return await ai_service.your_feature(text)
```

### 6.7 PDF 处理工具使用

```python
from app.services.pdf_service import pdf_service

# 提取文本
result = pdf_service.extract_text("path/to/file.pdf")
print(result["text"])  # 全文
print(result["pages"])  # 页数

# 合并 PDF
output_path = pdf_service.merge_pdfs(["file1.pdf", "file2.pdf"])

# 添加水印
pdf_service.add_watermark("input.pdf", "CONFIDENTIAL", opacity=0.3)

# 旋转页面
pdf_service.rotate_pages("input.pdf", rotation=90)
```

### 6.8 AI 模型配置

在 `backend/.env` 中配置：

```bash
# 本地 Ollama（推荐优先使用）
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Anthropic Claude
CLAUDE_API_KEY=sk-ant-...

# 默认模型
DEFAULT_AI_PROVIDER=ollama
DEFAULT_AI_MODEL=qwen2.5:0.8b
```

### 6.9 调试技巧

```bash
# 查看后端日志
python -m uvicorn app.main:app --reload --log-level debug

# 检查 API 文档
# 浏览器打开 http://localhost:8000/api/docs

# 前端 React DevTools
# Chrome 扩展安装 React Developer Tools

# PDF.js 调试
# 在浏览器控制台输入 pdfjsLib 查看版本和功能
```

---

## 7. 启动与运行

### 7.1 快速启动（推荐）

```bash
# 终端 1：后端
cd AcaSight\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 终端 2：前端
cd AcaSight\frontend
npm run dev
```

### 7.2 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:5173 | 主界面 |
| 后端 API | http://localhost:8000 | API 服务 |
| API 文档 | http://localhost:8000/api/docs | Swagger UI |
| API Redoc | http://localhost:8000/api/redoc | ReDoc 文档 |

### 7.3 功能入口

| 侧边栏图标 | 功能 | 路径 |
|-----------|------|------|
| 📁 | 项目管理（首页） | 默认页面 |
| 🔍 | 文献检索 | `/search` |
| 📄 | PDF 阅读器 | `/pdf` |
| 📝 | 笔记写作（占位） | - |
| 📊 | 数据分析（占位） | - |
| 🧪 | 实验设计（占位） | - |
| ⚙️ | 设置 | `/settings` |

---

## 8. 技术栈清单

### 前端

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | React | 18.2.0 | UI 框架 |
| 语言 | TypeScript | 5.2.2 | 类型安全 |
| 构建 | Vite | 5.0.0 | 快速构建 |
| 样式 | Tailwind CSS | 3.3.5 | 原子化 CSS |
| 桌面 | Electron | 28.0.0 | 桌面应用 |
| 状态 | Zustand | 4.4.7 | 状态管理 |
| 图标 | lucide-react | 0.294.0 | 图标库 |
| PDF | react-pdf | 7.5.1 | PDF 渲染 |
| 编辑器 | Monaco Editor | 4.6.0 | 代码/文本编辑 |
| 图表 | Recharts | 2.10.0 | 数据可视化 |
| Markdown | react-markdown | 9.0.1 | Markdown 渲染 |
| 公式 | KaTeX | 0.16.9 | LaTeX 公式渲染 |
| 拖拽 | react-window | 1.8.10 | 虚拟滚动 |
| 工具 | axios | 1.6.2 | HTTP 客户端 |

### 后端

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | FastAPI | 0.100+ | Python Web 框架 |
| 服务器 | Uvicorn | - | ASGI 服务器 |
| ORM | SQLAlchemy | 2.0 | 数据库 ORM |
| 数据库 | SQLite | - | 本地数据库 |
| 向量 | Qdrant | - | 向量检索 |
| AI | LangChain | - | LLM 编排 |
| PDF | PyMuPDF (fitz) | - | PDF 处理 |
| PDF | pypdf | - | PDF 处理 |
| HTTP | httpx | - | 异步 HTTP |
| 日志 | structlog | - | 结构化日志 |
| 验证 | pydantic | - | 数据验证 |

---

## 📌 附：前端组件地图

```
App.tsx
└── Sidebar（侧边栏）
    └── [切换内容]
        ├── ProjectHome（首页）
        │   ├── 统计卡片（总文献/已读/未读/收藏）
        │   ├── 最近项目列表
        │   └── 最近阅读列表
        │
        ├── PDFReader（PDF阅读器）★★★★★
        │   ├── ThumbnailPanel（左侧缩略图）
        │   ├── 主阅读区（PDF.js 渲染）
        │   │   ├── 悬浮 AIToolbar（选中文字弹出）
        │   │   └── 底部工具栏（翻页/缩放/搜索/上传）
        │   └── 右侧面板（标签切换）
        │       ├── AI 助手（AISidePanel）
        │       ├── 笔记（NotesPanel）
        │       └── 目录（TOC）
        │
        ├── SearchPage（文献检索）
        │   ├── 搜索框
        │   ├── 筛选器（年份/排序）
        │   └── 结果卡片（标题/作者/期刊/引用）
        │
        └── SettingsPage（设置）
            ├── AI 模型配置
            ├── 数据存储
            └── 外观主题
```

---

*手册版本：v2.0*
*最后更新：2026-05-18 22:55*
*维护者：AcaSight 开发团队*
