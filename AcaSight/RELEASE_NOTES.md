# AcaSight v2.0.0 — Release Notes

> **发布日期**: 2026-05-27
> **版本号**: v2.0.0 全栈可运行版
> **对应技术手册**: TECHNICAL_MANUAL.md v8.1
> **类型**: 里程碑版本 — 首次全栈可运行提交

---

## 版本概述

AcaaSight v2.0.0 是学术视界项目的第一个全栈可运行完整版本。本版本实现了从文献检索到 AI 学术辅助的完整闭环，核心链路已验证通过。

---

## 核心亮点

### 🚀 全栈就绪
- **前端**: React 18 + TypeScript + Vite 6 + Tailwind CSS，`npm run build` 通过
- **后端**: FastAPI + Uvicorn，端口 9000，AI 服务 + PDF 服务 running
- **数据库**: SQLAlchemy + aiosqlite + ChromaDB 向量库
- **启动**: `cd backend && python -m app.main` 一键启动

### 📚 6 源并行文献检索
- CORE / OpenAlex / Semantic Scholar / Crossref / Europe PMC / arXiv
- 智能去重排序 + Zotero 一键保存
- uiverse.io 风格搜索界面

### 📖 PDF 学术阅读器
- pdf.js 连续滚动渲染 + 文字选择高亮
- 4 色高亮 + 下划线 + 文本注释 + 橡皮擦标注工具栏
- 笔记面板 + 目录导航侧栏
- Zotero PDF 三级策略加载（MCP → base64 → 本地存储）

### 🤖 12 技能学术 Agent
- ReAct 循环 + SSE 流式响应 + 多会话管理
- 技能覆盖：论文问答/摘要/润色/翻译/章节起草/大纲/引用/检索/图表/审稿回复/数据审核/论文转PPT
- ContextualAgentBar 跟随鼠标气泡，选中文字即触发

### 📊 学术图表系统
- 8 种图表类型 + AI 推荐 UI + 12 学术模板
- 多格式数据解析 (CSV/JSON/Excel)
- 全自动 AI 绘图 API (routers/chart_auto.py)

### 🧠 知识图谱
- 本地文献 + 在线检索文献合并关联
- react-force-graph-2d 交互式可视化

### 📝 Markdown 转 Word 模板
- python-docx 模板生成服务
- 支持 中文学/英文学/学术报告/课程作业模板
- POST /api/template/generate

---

## 已修复 (v8.0→v8.1)

| 修复项 | 说明 |
|--------|------|
| 端口统一 | main.py + 12 个前端组件中的 18000→9000 硬编码 |
| 启动规范化 | `python -m app.main` + PYTHONPATH 设定 |
| Git 初始化 | .gitignore 配置，排除构建产物 |
| 依赖共存 | Zotero MCP (23120) 独立运行不受影响 |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 18, TypeScript 5, Vite 6, Tailwind CSS 3, Plotly.js, react-pdf, Excalidraw, lucide-react |
| 后端 | FastAPI 0.100+, Uvicorn, SQLAlchemy, aiosqlite, ChromaDB 0.4.22+ |
| AI | httpx + OpenAI 兼容 API (7 提供商) |
| PDF | PyMuPDF (fitz) |
| 文档 | python-docx |
| 端口 | 后端 9000, Zotero MCP 23120 |

---

## 项目结构

```
AcaSight/
├── frontend/           # React SPA (Vite)
│   └── src/
│       ├── components/ # Agent, Charts, Common, Layout, Notes,
│       │               # PDFReader, Search, Settings, Views,
│       │               # Whiteboard, Writing, Zotero
│       ├── contexts/   # AppContext, ThemeContext
│       ├── hooks/      # useTemplates, useAgent, etc.
│       ├── services/   # API 客户端
│       ├── store/      # Zustand Agent 状态
│       └── types/      # TypeScript 类型定义
├── backend/            # FastAPI 后端
│   └── app/
│       ├── main.py     # 应用入口 (port 9000)
│       ├── routers/    # 14 个路由模块
│       ├── services/   # AI, PDF, RAG, Search, Template, Zotero
│       ├── agent/      # Agent Core + Skill Registry + 12 Skills
│       ├── models/     # SQLAlchemy 数据模型
│       └── database/   # 数据库初始化
├── docs/               # 技术文档
├── refs/               # 参考代码
├── TECHNICAL_MANUAL.md # v8.1 正式技术手册
└── .gitignore
```

---

## 已落地模块清单 (44 个)

### 前端 (24 个组件/视图)
- ObsidianLayout (图标栏 + 面板容器)
- FileExplorerView, EditorView, SearchPage
- ChartPanel, GraphView, ZoteroPanel
- AgentPanel (多会话 + 流式)
- ContextualAgentBar (跟随鼠标气泡)
- MarkdownEditor, ExcalidrawBoard
- SettingsModal (7 提供商 AI 配置)
- AnnotationOverlay (PDF 标注覆盖层)
- FloatingTranslate (AI 翻译气泡)
- OutlineView, TagsView, BookmarksView (占位)

### 后端 (14 个路由 + 5 个服务)
- PDF, Chart Auto, Chat, Search, Notes, Zotero
- Storage, Sync, Writing, AI Config, Papers
- Annotations, Knowledge Graph, RAG, Format Export, Template
- AI Service, PDF Service, RAG Service, Search Service, Template Service, Vector Service, Zotero Sync

### Agent (1 Core + 12 Skills)
- Agent Core (ReAct 循环 + 超时保护)
- 12 学术技能 (全部已验证)

---

## 已知限制

| 限制 | 优先级 | 计划 |
|------|--------|------|
| Markdown 编辑器无 KaTeX | P2 | Chapter D → Milkdown |
| 浅色主题 CSS 覆盖不全 | P2 | Chapter B → 玻璃浮雕 |
| plotly.js 主 chunk 7.8MB | P3 | Code splitting |
| 论文数据库 CRUD 未实现 | P1 | Chapter C |
| RAGFlow 未部署 | P2 | Chapter G |
| Pandoc 未集成 | P3 | Chapter H |
| Outline/Tags/Bookmarks 占位 | P2 | 后续章节 |
| 半自动 AI 图表向导 | P2 | Chapter F |

---

## 如何运行

```bash
# 1. 启动 Zotero MCP (如果使用 Zotero 功能)
# Zotero → Tools → Zotero MCP Bridge, 确认 23120 监听

# 2. 启动 AcaSight 后端
cd AcaSight/backend
python -m app.main

# 3. 浏览器打开
http://localhost:9000

# 4. 开发模式下前端热更新
cd AcaSight/frontend
npm run dev
# 然后打开 http://localhost:5173
```

---

> ✨ AcaSight 学术视界 v2.0.0 — 面向研究生的全能学术智能体
