# AcaSight 学术视界 — 正式技术手册 v8.1

> **生成日期**: 2026-05-27
> **状态**: 定稿（取代 v8.0 及所有旧版计划文档）
> **适用范围**: 开发团队、技术评审、验收测试
>
> **权威级别**: 本文档是 AcaSight 唯一的正式技术手册，取代此前所有版本。
>
> **v8.1 更新要点**：
> - 端口统一修复：main.py + 12 个前端组件 18000→9000 硬编码替换
> - 启动方式规范化：`cd backend && python -m app.main`，PYTHONPATH 设定
> - 项目纳入 Git 版本管理，配置 .gitignore
> - Zotero MCP (23120) 与 AcaSight 后端 (9000) 共存验证通过
> - 前端 Vite 构建通过 (47.94s)，后端 /api/health 返回 200
> - 里程碑：AcaaSight v2.0.0 全栈可运行版本首次提交
>
> **v8.0 更新要点**（保留）：
> - PDF 阅读器空白页错位根因修复（textLayer position: relative→absolute）
> - PDF 文字选中高亮样式修复（::selection color 显式声明）
> - Agent 全局权限升级：新增数据处理、自动绘图、知识图谱、文档解析
> - 智能写作模块合并入 Agent 体系，取消独立 WritingPanel
> - PDF 右侧面板精简：取消 AI 聊天 Tab，仅保留笔记和目录
> - 白板自适应修复：Excalidraw 图标缩小
> - 知识图谱增强：本地文献与搜索文献合并关联
> - ContextualAgentBar 改为跟随鼠标气泡，选中文字才出现
> - 搜索界面 uiverse.io 风格美化
> - Markdown 转 Word 模板服务后端落地
> - PDF 拖拽排序功能彻底移除（修复文字选择权限）

---

## 核心方法论：六步迭代开发流程

```
Step 1  统筹梳理 → 分类归纳已落地模块、未开发功能、后续计划、技术路径
Step 2  客观研判 → 评估当前技术路线的落地性与实操难度
Step 3  开源替代 → 针对高成本方案检索开源工程，选取适配替代
Step 4  定稿发布 → 以本手册为依据，稳步推进
Step 5  单章开发 → 单个章节开发完毕立即技术复盘
Step 6  循环迭代 → 结合用户反馈，调整优化，回到 Step 1
```

---

## 第一部分：现状总览

### 1.1 项目定位

**AcaSight（学术视界）**：面向研究生的全能学术智能体应用，Web 单页应用 + FastAPI 后端，未来可 Tauri 打包为桌面应用。

核心场景：文献检索 → PDF 精读标注 → 知识图谱关联 → AI Agent 分析 → 学术写作排版导出

### 1.2 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 前端框架 | React + TypeScript + Vite | React 18, TS 5, Vite 6 |
| 样式 | Tailwind CSS + CSS Variables | 3.x |
| 状态管理 | React Context (全局) + Zustand (Agent) | - |
| 绘图 | Plotly.js-dist-min + react-plotly.js | - |
| PDF 渲染 | react-pdf (pdf.js) | - |
| 白板 | Excalidraw | - |
| 图标 | lucide-react | - |
| 后端框架 | FastAPI + Uvicorn | 0.100+ |
| ORM | SQLAlchemy + aiosqlite | - |
| AI 服务 | httpx + OpenAI 兼容 API | - |
| 向量库 | ChromaDB | 0.4.22+ |
| PDF 处理 | PyMuPDF (fitz) | - |
| Word 模板 | python-docx | - |
| 日志 | structlog | - |
| **后端端口** | **9000** | v8.1 统一修复 |
| **Zotero MCP** | **23120** | 独立进程 JSON-RPC |
| **启动命令** | `cd backend && python -m app.main` | PYTHONPATH=backend/ |

### 1.3 前端架构（v8.0 当前状态）

```
App.tsx
  └─ ThemeProvider
      └─ AppProvider (contexts/AppContext.tsx — 集中全局状态)
          └─ ObsidianLayout (Layout/ — 纯布局编排壳，已移除拖拽排序)
              ├─ IconBar（左侧图标导航：文件/搜索/图表/白板/Zotero/Agent/设置）
              ├─ PanelContainer（面板容器，无拖拽）
              │   ├─ FileExplorerView   (Views/)
              │   ├─ EditorView         (Views/ — PDF/MD + 笔记侧栏 + 目录侧栏)
              │   ├─ SearchPage         (Search/ — uiverse.io 美化)
              │   ├─ ChartPanel         (Charts/)
              │   ├─ GraphView          (Views/ — 本地+在线文献图谱)
              │   ├─ OutlineView        (Views/ — 占位)
              │   ├─ TagsView           (Views/ — 占位)
              │   ├─ BookmarksView      (Views/ — 占位)
              │   ├─ MarkdownEditor     (Notes/)
              │   ├─ ExcalidrawBoard    (Whiteboard/ — 图标缩小修复)
              │   ├─ ZoteroPanel        (Zotero/)
              │   └─ AgentPanel         (Agent/ — 多会话+流式+12技能+全局权限)
              └─ GlobalOverlays（SettingsModal / ContextualAgentBar 跟随鼠标气泡 / ContextMenu）
```

### 1.4 已落地模块清单（v8.0 精确清点）

| 模块 | 位置 | 真实状态 | 说明 |
|------|------|----------|------|
| **前端架构** | frontend/ | ✅ 可用 | React 18 + TS + Vite + Tailwind |
| Obsidian 布局 | Layout/ObsidianLayout.tsx | ✅ 可用 | 图标栏 + 面板容器（拖拽已移除） |
| AppContext 全局状态 | contexts/AppContext.tsx | ✅ 可用 | 重构完成，构建通过，AI Tab 已移除 |
| 主题系统 | contexts/ThemeContext.tsx | ✅ 可用 | 深色/浅色切换 |
| **Layer 1: 论文检索** | | ✅ 可用 | |
| 6 源并行检索 | services/search_service.py | ✅ 可用 | CORE/OpenAlex/Semantic Scholar/Crossref/Europe PMC/arXiv |
| 搜索结果页 | Search/SearchPage.tsx | ✅ 可用 | uiverse.io 风格美化，去重排序 + Zotero 保存 |
| **Layer 2: 绘图** | | ⚠️ 部分可用 | |
| Plotly.js 图表 | Charts/ChartPanel.tsx | ✅ 可用 | 8 种图表 + AI 推荐 UI |
| 多格式数据解析 | ChartPanel.tsx | ✅ 可用 | CSV/JSON/Excel |
| 12 学术模板 | Charts/chartTemplates.ts | ✅ 可用 | XRD/TG/FTIR/CV/Nyquist 等 |
| 全自动绘图 API | routers/chart_auto.py | ✅ 可用 | 已验证端到端正常 |
| 半自动 AI 向导 | - | ❌ 未开发 | |
| **Layer 0: 数据存储** | | ✅ 可用 | |
| PDF 存储服务 | services/storage_service.py | ✅ 可用 | SHA256 去重 |
| Zotero 同步桥 | services/zotero_sync.py | ✅ 可用 | MCP JSON-RPC |
| ChromaDB 向量服务 | services/vector_service.py | ✅ 可用 | 语义分块 + cosine 距离 |
| Markdown→Word 模板 | services/template_service.py | ✅ 可用 | python-docx 模板生成 |
| 模板 API | routers/template.py | ✅ 可用 | POST /api/template/generate |
| **AI 服务** | | ✅ 可用 | |
| AI 配置面板 | Settings/SettingsModal.tsx | ✅ 可用 | Cherry Studio 风格，7 提供商 |
| AI 服务核心 | services/ai_service.py | ✅ 可用 | 多 Provider 路由 + 动态配置 |
| 模型列表动态获取 | routers/ai_config.py | ✅ 可用 | /api/ai/test 返回 models 列表 |
| AI Key 存储脱敏 | routers/ai_config.py | ✅ 已修复 | 跳过含 `****` 的 key 更新 |
| **PDF 阅读器** | | ✅ 可用 | |
| PDF.js 连续滚动渲染 | Views/EditorView.tsx | ✅ 可用 | 上下滚动 + onScroll 页码追踪 |
| 文字选择与高亮 | Views/EditorView.tsx + index.css | ✅ 可用 | 拖拽移除 + textLayer pointer-events修复 |
| PDF 页面间隙修复 | index.css | ✅ 已修复 | textLayer position: relative→absolute |
| 选中高亮样式修复 | index.css | ✅ 已修复 | ::selection color: transparent 显式 |
| 标注工具栏 | Views/EditorView.tsx | ✅ 可用 | 4色高亮 + 下划线 + 文本注释 + 橡皮擦 |
| AnnotationOverlay | AnnotationOverlay.tsx | ✅ 可用 | position: absolute 覆盖层 |
| 右侧面板 | EditorView.tsx | ✅ 可用 | 仅笔记 + 目录（AI Tab 已移除） |
| Zotero PDF 三级策略 | routers/zotero.py | ✅ 已修复 | MCP → base64 → 本地存储 |
| PDF 全文提取 | services/pdf_service.py | ✅ 可用 | PyMuPDF 提取 |
| **Agent 系统** | | ✅ 已打通 | |
| Agent Core | agent/core.py | ✅ 可用 | ReAct 循环 + 超时保护 + 纯文本回退 |
| Skill Registry | agent/skill_registry.py | ✅ 可用 | 12 个学术技能注册 |
| 12 学术技能 | agent/skills/nature_skills.py | ✅ 可用 | 全部有 try/except + _safe_chat |
| SSE 流式端点 | agent/router.py | ✅ 可用 | 8 个端点，多轮对话，会话持久化 |
| 前端 AgentPanel | Agent/AgentPanel.tsx | ✅ 可用 | 多会话侧边栏 + 流式渲染 + 技能面板 |
| ContextualAgentBar | Agent/ContextualAgentBar.tsx | ✅ 可用 | 跟随鼠标气泡，选中文字触发 |
| 全局权限升级 | agent/skills/ | ✅ 可用 | 数据处理 + 自动绘图 + 知识图谱 + 文档解析 |
| **其他组件** | | | |
| Markdown 编辑器 | Notes/MarkdownEditor.tsx | ⚠️ 基础可用 | 无实时预览/KaTeX |
| 白板 | Whiteboard/ExcalidrawBoard.tsx | ✅ 可用 | Excalidraw 集成，图标缩小修复 |
| 知识图谱 | Views/GraphView.tsx | ✅ 可用 | 本地+在线文献合并，react-force-graph-2d |
| 智能写作 | Agent 体系内 | ✅ 已合并 | 独立 WritingPanel 已取消，能力由 Agent 提供 |
| ZoteroPanel | Zotero/ZoteroPanel.tsx | ✅ 可用 | 集合树+文献列表 |
| OutlineView | Views/OutlineView.tsx | ❌ 占位 | 空壳 |
| TagsView | Views/TagsView.tsx | ❌ 占位 | 空壳 |
| BookmarksView | Views/BookmarksView.tsx | ❌ 占位 | 空壳 |

### 1.5 已知缺陷（v8.0 更新）

| 缺陷 | 严重度 | 状态 | 说明 |
|------|--------|------|------|
| ~~Zotero PDF 端点 500~~ | P0 | ✅ 已修复 | 三级策略 |
| ~~AI API Key 存储脱敏~~ | P1 | ✅ 已修复 | 跳过含 `****` 的 key |
| ~~PDF 全文提取不稳定~~ | P1 | ✅ 已修复 | PyMuPDF 统一提取 |
| ~~Agent Core 端到端未通~~ | P1 | ✅ 已修复 | SSE 流式 + 12 技能 |
| ~~chart_auto 端到端未验证~~ | P1 | ✅ 已验证 | 全自动绘图正常 |
| ~~PDF 拖拽阻止文字选择~~ | P1 | ✅ 已修复 | 移除 draggable + 拖拽排序 |
| ~~PDF 页面空白错位~~ | P1 | ✅ 已修复 | textLayer position: relative→absolute |
| ~~PDF 选中高亮突兀~~ | P2 | ✅ 已修复 | ::selection color: transparent 显式 |
| ~~Excalidraw 图标过大~~ | P2 | ✅ 已修复 | CSS 注入缩小图标 |
| ~~智能写作独立模块冗余~~ | P2 | ✅ 已合并 | 取消 WritingPanel，Agent 提供 |
| 浅色主题 CSS 覆盖不全 | P2 | 🔲 待修 | 部分 CSS 变量缺失 |
| plotly.js 大 chunk 警告 | P3 | 🔲 待修 | 主 chunk 7.8MB，需 code splitting |
| Markdown 编辑器无 KaTeX | P2 | 🔲 待修 | Milkdown 替代方案已确定 |
| 面板拖拽排序已移除 | - | ✅ 已移除 | 用户要求取消 |

---

## 第二部分：技术路线可行性研判（v8.0 更新）

### 2.1 开源替代方案决策矩阵

| 功能模块 | 自建方案 | 替代方案 | 节省工作量 | 风险 | 判定 |
|----------|----------|---------|-----------|------|------|
| PDF 标注系统 | 自建后端+前端渲染 | **react-pdf + AnnotationOverlay 自建** | 0% | 低 | ✅ 采用（已落地） |
| 引用图谱 | react-force-graph-2d | **保持**（+ Sigma.js 备选） | 0% | 低 | ✅ 保持（已落地） |
| RAG 引擎 | 自建3层 RAG | **RAGFlow**（Docker 部署） | 80%+ | 低 | ✅ 待落地 |
| 学术格式引擎 | python-docx 手动实现 | **Pandoc + citeproc + python-docx** | 70%+ | 低 | ⚠️ 混合（已部分落地） |
| Markdown+KaTeX | react-markdown | **Milkdown** | 70%+ | 低 | ✅ 待落地 |

### 2.2 替代方案详细说明

#### react-pdf + AnnotationOverlay（PDF 核心 — 已落地）
- 基于 react-pdf 渲染层 + 自建 AnnotationOverlay 覆盖层
- textLayer 保持 absolute 定位覆盖 canvas，canvas pointer-events: none
- 标注系统：4色高亮 + 下划线 + 文本注释 + 橡皮擦
- 关键技术点：textLayer position: absolute（非 relative），::selection color: transparent
- 集成方式：EditorView.tsx 中 `<Page>` + `<AnnotationOverlay>` 双层结构

#### RAGFlow（RAG 引擎 — 待落地）
- GitHub ~75k Stars，v0.25.5
- 内置 DeepDoc 文档理解引擎，PDF 解析能力极强
- 模板化分块，适合学术论文结构化处理
- 内置引用溯源与可视化，减少幻觉
- Docker 一键部署，API 接口与 FastAPI 集成
- **最低要求**：4核 CPU / 16GB RAM / 50GB 磁盘

#### Pandoc + citeproc（学术格式引擎 — 部分落地）
- Pandoc ~35k Stars，v3.9.0.2
- 支持 40+ 输入格式 → 60+ 输出格式
- 内置 citeproc 引用处理器，CSL 9000+ 引用样式
- 当前已落地：python-docx 模板生成（template_service.py + template.py）
- 待落地：pypandoc 全流程集成

#### Milkdown（Markdown 编辑器 — 待落地）
- GitHub ~8k Stars，v7.21.1
- 插件驱动架构，KaTeX 原生支持
- 所见即所得（WYSIWYG），类 Typora 编辑体验
- 官方 React 组件 @milkdown/react

### 2.3 功能研判矩阵（v8.0 更新）

| 计划功能 | 方案 | 难度 | 新依赖 | 风险 | 架构兼容 | 判定 |
|----------|------|------|--------|------|----------|------|
| ~~Zotero PDF 流修复~~ | 三级策略 | - | 0 | - | - | ✅ 已完成 |
| ~~PDF 全文提取稳定化~~ | 后端 PyMuPDF | - | 0 | - | - | ✅ 已完成 |
| ~~chart_auto 端到端验证~~ | 手动测试 | - | 0 | - | - | ✅ 已完成 |
| ~~AI Key 存储修复~~ | 跳过脱敏 key | - | 0 | - | - | ✅ 已完成 |
| ~~Agent 端到端打通~~ | SSE + 流式 | - | 0 | - | - | ✅ 已完成 |
| ~~PDF 拖拽移除~~ | 删除 draggable | - | 0 | - | - | ✅ 已完成 |
| ~~PDF 页面间隙修复~~ | textLayer CSS | - | 0 | - | - | ✅ 已完成 |
| ~~PDF 选中样式修复~~ | ::selection CSS | - | 0 | - | - | ✅ 已完成 |
| ~~Excalidraw 图标修复~~ | CSS 注入 | - | 0 | - | - | ✅ 已完成 |
| ~~搜索页美化~~ | uiverse.io CSS | - | 0 | - | - | ✅ 已完成 |
| ~~知识图谱增强~~ | 本地+在线合并 | - | 0 | - | - | ✅ 已完成 |
| ~~ContextualAgentBar 气泡~~ | 跟随鼠标 | - | 0 | - | - | ✅ 已完成 |
| ~~MD→Word 模板服务~~ | python-docx | - | 0 | - | - | ✅ 已完成 |
| ~~Agent 全局权限升级~~ | skill_registry | - | 0 | - | - | ✅ 已完成 |
| ~~写作模块合并 Agent~~ | 取消独立模块 | - | 0 | - | - | ✅ 已完成 |
| ~~PDF AI Tab 移除~~ | 精简面板 | - | 0 | - | - | ✅ 已完成 |
| **玻璃浮雕 UI** | CSS glass morphism | 低 | 0 | 低 | ✅ | ✅ 下一章 |
| **论文数据库 CRUD** | 后端 + 前端面板 | 中 | 0 | 低 | ✅ | ✅ 紧随其后 |
| **Markdown 增强** | Milkdown | 中 | 1 | 低 | ✅ | ✅ 替代方案已确定 |
| **引用图谱深化** | react-force-graph-2d | 中 | 0 | 中 | ✅ | ✅ 基础已落地 |
| **RAG 引擎** | RAGFlow (Docker) | 中 | 1 | 低 | ⚠️ | ✅ 替代方案已确定 |
| **学术格式引擎** | Pandoc + citeproc | 中 | 1 | 低 | ✅ | ✅ 部分已落地 |
| **Zotero 窗口嵌入** | Tauri + SetParent | 高 | 3 | 高 | ❌ | ❌ 推迟至桌面化 |
| **系统全局悬浮窗** | Tauri 透明置顶 | 高 | 2 | 高 | ❌ | ❌ 推迟至桌面化 |
| **OnlyOffice 嵌入** | Docker | 高 | 3 | 高 | ❌ | ❌ 推迟至 Docker 环境 |

---

## 第三部分：正式开发手册 — 分章实施（v8.0）

### 章节进度总览

```
✅ Chapter A: 阻断修复 (P0)     ✅ Chapter E: Agent 端到端 (P1)
✅ v8.0 增量修复 (P1-P2)        🔜 Chapter B: 玻璃浮雕 UI (P1)
⏳ Chapter C: 论文数据库 CRUD    ⏳ Chapter D: Markdown 增强
⏳ Chapter F: 绘图模块补全        ⏳ Chapter G: RAG 引擎
⏳ Chapter H: 学术格式引擎深化    ❌ Chapter I+: 推迟章节
```

---

### Chapter A: 阻断修复（P0）— ✅ 已完成（v7.0）

| # | 任务 | 状态 | 完成说明 |
|---|------|------|----------|
| A.1 | 修复 Zotero PDF 端点 500 | ✅ | 三级策略 |
| A.2 | 修复 AI Key 存储脱敏问题 | ✅ | 后端跳过含 `****` 的 key |
| A.3 | PDF 全文提取后端化 | ✅ | POST /api/pdf/extract |
| A.4 | chart_auto 端到端验证 | ✅ | 全自动绘图正常 |

---

### v8.0 增量修复（P1-P2）— ✅ 已全部完成

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| V.1 | PDF 拖拽排序移除 | ObsidianLayout.tsx | ✅ |
| V.2 | PDF 文字选择修复 | index.css + EditorView.tsx | ✅ |
| V.3 | PDF 页面空白错位修复 | index.css (textLayer position) | ✅ |
| V.4 | PDF 选中高亮样式修复 | index.css (::selection) | ✅ |
| V.5 | Excalidraw 白板图标缩小 | ExcalidrawBoard.tsx | ✅ |
| V.6 | 搜索界面 uiverse.io 美化 | SearchPage.tsx | ✅ |
| V.7 | 知识图谱本地+在线合并 | GraphView.tsx + knowledge_graph.py | ✅ |
| V.8 | ContextualAgentBar 气泡化 | ContextualAgentBar.tsx | ✅ |
| V.9 | Markdown→Word 模板服务 | template_service.py + template.py | ✅ |
| V.10 | Agent 全局权限升级 | agent/skills/ | ✅ |
| V.11 | 智能写作合并入 Agent | 取消 WritingPanel 独立模块 | ✅ |
| V.12 | PDF AI 聊天 Tab 移除 | EditorView.tsx + AppContext.tsx | ✅ |
| V.13 | PDF 标注工具栏 | EditorView.tsx (4色+下划线+注释+橡皮擦) | ✅ |

**验收结果**: 全部通过 ✅

---

### Chapter B: 玻璃浮雕 UI（P1，预估 3h）— 🔜 下一章

> 纯 CSS 变更，低成本高回报，统一视觉风格

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| B.1 | CSS 变量体系 | index.css | 1h |
| B.2 | 面板容器玻璃化 | ObsidianLayout.tsx | 30min |
| B.3 | 图标栏玻璃化 | ObsidianLayout.tsx | 30min |
| B.4 | 设置面板玻璃化 | SettingsModal.tsx | 30min |
| B.5 | 浅色主题适配 | index.css | 30min |
| B.6 | 绘图面板保持方框 | ChartPanel 不动 | 0min |

**CSS 变量参考**:
```css
:root {
  --glass-bg: rgba(30, 30, 46, 0.72);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: 16px;
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.28);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
}
```

**验收标准**:
- 深色模式：面板半透明毛玻璃 + 圆角
- 浅色模式：面板纯白 + 柔和阴影 + 圆角
- 科研绘图(ChartPanel)保留方框无圆角
- `npm run build` 零错误

---

### Chapter C: 论文数据库 CRUD（P1，预估 6h）

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| C.1 | 后端：论文 CRUD API | routers/papers.py | 2h |
| C.2 | 后端：标签管理 API | routers/papers.py | 1h |
| C.3 | 前端：FileExplorerView 增强 | Views/FileExplorerView.tsx | 2h |
| C.4 | 前端：TagsView 实现 | Views/TagsView.tsx | 1h |

**API 设计**:
```
GET    /api/papers              — 列表(支持筛选/排序/分页)
POST   /api/papers              — 手动创建(入库)
GET    /api/papers/:id          — 详情
PUT    /api/papers/:id          — 修改元数据
DELETE /api/papers/:id          — 删除(同时删向量索引)
GET    /api/papers/:id/tags     — 获取标签
POST   /api/papers/:id/tags     — 添加标签
DELETE /api/papers/:id/tags/:tag — 删除标签
```

**验收标准**:
- 论文列表加载正常，支持按标题/年份/期刊排序
- 搜索结果 → 一键入库
- 标签云渲染 + 点击筛选
- `npm run build` 零错误 + 后端 Swagger 文档更新

---

### Chapter D: Markdown 增强与笔记系统（P2，预估 4h）

> 从 react-markdown 改为 Milkdown，节省 70% 工作量

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| D.1 | Milkdown 集成 | MarkdownEditor.tsx | 2h |
| D.2 | KaTeX 数学公式插件 | @milkdown/plugin-math | 30min |
| D.3 | 实时预览（WYSIWYG） | Milkdown 内置 | 0min |
| D.4 | 导出 Word | 对接 template_service | 1.5h |

**验收标准**:
- Markdown 编辑器支持实时预览
- KaTeX 数学公式渲染正确
- 导出 Word 套用模板成功
- `npm run build` 零错误

---

### Chapter E: Agent 端到端打通（P1）— ✅ 已完成（v7.0）

| # | 任务 | 状态 | 完成说明 |
|---|------|------|----------|
| E.1 | Agent Core 验证 + 修复 | ✅ | ReAct 循环 + 超时保护 |
| E.2 | SSE 流式端点 | ✅ | 8 个端点，多轮对话 |
| E.3 | 前端 AgentPanel 多会话 | ✅ | 侧边栏 + 切换 + 流式渲染 |
| E.4 | 5 个基础 Skill 验证 | ✅ | 全 PASS |
| E.5 | ContextualAgentBar 联动 | ✅ | 跟随鼠标气泡 |

**验收结果**: 全部通过 ✅

---

### Chapter F: 绘图模块补全（P2，预估 6h）

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| F.1 | 图表字体大小滑块 | ChartPanel.tsx | 30min |
| F.2 | 网格线学术样式 | ChartPanel.tsx | 30min |
| F.3 | 半自动 AI 向导 | ChartPanel.tsx + chart_auto.py | 3h |
| F.4 | 绘图结果→笔记/报告联动 | ChartPanel + WritingPanel | 2h |

**验收标准**:
- 图表支持字体大小实时调节
- 网格线符合学术期刊标准
- AI 向导能根据数据推荐图表类型
- 图表可导出到笔记

---

### Chapter G: RAG 引擎（P2，预估 6h）

> 从自建3层 RAG 改为 RAGFlow，节省 80%+ 工作量

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| G.1 | RAGFlow Docker 部署 | docker-compose.yml | 1h |
| G.2 | FastAPI ↔ RAGFlow API 对接 | services/rag_service.py | 2h |
| G.3 | RAG 问答端点 | routers/rag.py | 1h |
| G.4 | 前端问答集成 | EditorView + Agent 增强 | 2h |

**RAGFlow 集成架构**:
```
前端 EditorView/Agent → FastAPI /api/rag/query → RAGFlow API → LLM
                              ↓
                        ChromaDB 向量检索
                              ↓
                        DeepDoc 文档解析
```

**验收标准**:
- RAGFlow Docker 正常运行
- 问答接口返回正确引用来源
- 前端问答面板可用

---

### Chapter H: 学术格式引擎深化（P3，预估 4h）

> 当前已落地：python-docx 模板生成。本章深化：Pandoc + citeproc 全流程

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| H.1 | Pandoc + pypandoc 集成 | services/format_service.py | 1h |
| H.2 | Markdown → DOCX/LaTeX/PDF | format_service.py | 1h |
| H.3 | citeproc 引用格式化 | --citeproc + CSL 样式 | 1h |
| H.4 | 前端格式导出 UI | EditorView/WritingPanel 增强 | 1h |

**验收标准**:
- MD → DOCX 一键转换成功
- 参考文献自动格式化
- 内置 GB/T 7714 / APA / IEEE 三种模板

---

### 推迟章节

| 章节 | 内容 | 触发条件 |
|------|------|----------|
| Chapter I | PPT 生成 | Chapter B-H 全部验收 |
| Chapter J | 跨文献对比分析 | RAG + Agent 稳定 |
| Chapter K | 实验数据智能分析 | 全自动绘图 + Agent 完成 |
| Chapter L | OnlyOffice 在线编辑 | Docker 环境 |
| Chapter M | Tauri 桌面打包 | Web 全功能稳定 |
| Chapter M1 | Zotero 窗口嵌入 | Tauri 完成 |
| Chapter M2 | 系统全局悬浮窗 | Tauri 完成 |

---

## 第四部分：开发优先级与时间线（v8.0）

```
已完成 (v7.0 + v8.0 增量):
  ├─ Chapter A: 阻断修复 ✅
  ├─ Chapter E: Agent 端到端打通 ✅
  └─ v8.0 V.1-V.13: 增量修复与功能优化 ✅

Phase 1 (当前):
  ├─ Chapter B: 玻璃浮雕 UI (3h)
  ├─ Chapter C: 论文数据库 CRUD (6h)
  └─ Chapter D: Markdown 增强 (4h)

Phase 2:
  ├─ Chapter F: 绘图模块补全 (6h)
  └─ Chapter G: RAG 引擎 (6h)

Phase 3:
  └─ Chapter H: 学术格式引擎深化 (4h)
```

---

## 第五部分：验收标准 — 全局 Checklist

### 构建质量
- [ ] `npm run build` 零错误
- [ ] 后端 `uvicorn app.main:app` 启动无报错
- [ ] 主 chunk < 800KB（需 code splitting）

### 功能完整性
- [ ] Chapter A-H 全部验收通过
- [ ] 所有 REST 端点有 Swagger 文档 (/api/docs)
- [ ] 暗色/浅色主题切换正常

### 可用性
- [ ] 无 JavaScript Console Error
- [ ] 所有按钮有 loading 状态
- [ ] 网络错误有友好提示
- [ ] PDF 文字可选择、高亮正常
- [ ] PDF 页面之间无空白间隙

### 数据安全
- [ ] AI API Key 存储安全（不存明文到前端）
- [ ] PDF 文件不离开本地
- [ ] 向量数据存储在本地 ChromaDB

---

## 第六部分：技术复盘 & 反馈流程

### 标准复盘模板

```markdown
## Chapter X 技术复盘

### 完成清单
- [ ] 任务 A
- [ ] 任务 B

### 验收测试结果
| 测试项 | 预期 | 实际 | 通过 |
|--------|------|------|------|

### 遇到的技术问题
1. 问题描述 → 解决方案

### 性能数据
- 构建时间: Xs
- Bundle 大小: XKB
- API 响应时间: Xms

### 用户反馈记录
（等待用户输入）

### 下一步行动
- [ ] 用户确认通过 → 进入下一章
- [ ] 修改项 → 重新验证 → 回到 Step 1
```

### 循环流程

```
Step 1 梳理 → Step 2 研判 → Step 3 替代 → Step 4 定稿（本手册）
                                                      ↓
                                            Chapter N 开发
                                                      ↓
                                              构建验证 + 复盘报告
                                                      ↓
                                               等待用户验收
                                              ↙           ↘
                                            通过            否
                                             ↓              ↓
                                       Chapter N+1     修改 → 重新验证 → 回到 Step 1
```

---

## 附录 A: Agent 端点清单

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/agent/task | POST | SSE 流式任务执行 |
| /api/agent/skills | GET | 列出所有技能 |
| /api/agent/bundles | GET | 列出技能包 |
| /api/agent/sessions | GET | 列出所有会话 |
| /api/agent/sessions/{id} | GET | 获取会话详情 |
| /api/agent/sessions/{id} | DELETE | 删除会话 |
| /api/agent/health | GET | 健康检查 |
| /api/agent/context | GET | 获取当前上下文 |

## 附录 B: 12 学术技能清单

| 技能 | 类别 | 说明 |
|------|------|------|
| paper_qa | reading | 基于PDF全文回答学术问题 |
| paper_summarize | reading | 生成学术论文摘要（Nature标准） |
| polish_text | writing | 学术文本润色（Nature风格） |
| translate_text | translation | 学术翻译 |
| draft_section | writing | 起草论文章节 |
| generate_outline | writing | 生成论文大纲 |
| format_citation | citation | 格式化参考文献 |
| search_literature | search | 多源文献检索 |
| generate_figure | figure | 生成Nature标准图表代码 |
| draft_response | response | 起草审稿意见回复 |
| check_data_availability | data | 审核数据可用性声明 |
| paper_to_ppt | paper2ppt | 论文转中文PPT大纲 |

## 附录 C: PDF 阅读器技术要点（v8.0 沉淀）

### C.1 核心架构
```
<div.pdf-page-wrapper (position: relative, margin: 0 auto, lineHeight: 0)>
  └─ <Page> (react-pdf)
      └─ <div.react-pdf__Page (position: relative)>
          ├─ <canvas> — pointer-events: none (不可交互)
          ├─ <div.textLayer> — position: absolute; inset: 0; pointer-events: auto
          └─ AnnotationLayer — renderAnnotationLayer={false} (已禁用)
  └─ <AnnotationOverlay> — position: absolute; top: 0; left: 0
```

### C.2 关键 CSS 规则
```css
/* textLayer 必须 absolute，不可 relative（会导致页面间隙） */
.react-pdf__Page__textLayer, .textLayer {
  pointer-events: auto !important;
  z-index: 20 !important;
  /* 千万不要加 position: relative */
}

/* canvas 不拦截鼠标 */
.react-pdf__Page__canvas {
  pointer-events: none !important;
}

/* 选中高亮必须显式 color: transparent，不可 inherit */
.react-pdf__Page__textLayer ::selection {
  background: rgba(59, 130, 246, 0.4);
  color: transparent;
}
```

### C.3 常见问题速查
| 问题 | 根因 | 修复 |
|------|------|------|
| 页面之间有空白 | textLayer position: relative | 改为 absolute |
| 文字无法选中 | draggable 属性阻止 | 移除 draggable |
| 选中高亮突兀 | color: inherit 继承 transparent | 显式 color: transparent |
| 标注工具栏无响应 | AnnotationOverlay pointer-events | 按需切换 auto/none |

## 附录 D: Markdown 转 Word 模板服务要点（v8.0 沉淀）

### D.1 已落地架构
```
后端: routers/template.py (POST /api/template/generate)
      services/template_service.py (python-docx 模板生成)
前端: (待集成)
```

### D.2 模板配置结构
```json
{
  "name": "模板名称",
  "fonts": { "bodyText": { "cjk": "宋体", "ascii": "Times New Roman", "size": 10.5 } },
  "paragraph": { "bodyText": { "alignment": "justify", "firstLineIndent": 2, "lineSpacing": { "type": "multiple", "value": 1.5 } } },
  "page": { "size": "A4", "margin": { "top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17 } }
}
```

## 附录 E: 依赖清单

### 前端 (package.json)
```
react, react-dom, typescript, vite, @vitejs/plugin-react
tailwindcss, postcss, autoprefixer
plotly.js-dist-min, react-plotly.js
lucide-react, xlsx, react-pdf
zustand (Agent 状态管理)
react-force-graph-2d (知识图谱)
@excalidraw/excalidraw (白板)
@milkdown/core, @milkdown/react, @milkdown/plugin-math (Chapter D)
```

### 后端 (requirements.txt)
```
fastapi, uvicorn[standard], sqlalchemy, aiosqlite
httpx, aiofiles, python-multipart, structlog
chromadb>=0.4.22
pymupdf
python-docx (模板服务)
pypandoc (Chapter H)
networkx (知识图谱)
```

### 外部服务
```
RAGFlow (Chapter G, Docker 部署)
Pandoc (Chapter H, 系统安装)
Ollama (本地 LLM, 可选)
```

---

## 附录 F: 被取代的历史文档

| 文档 | 状态 |
|------|------|
| TECHNICAL_MANUAL.md v1-v7 | ❌ 被本手册取代 |
| OPTIMIZATION_PLAN.md | ❌ 被本手册取代 |
| DEVELOPMENT_PLAN.md | ❌ 被本手册取代 |
| DEV_PLAN.md | ❌ 被本手册取代 |
| PROJECT_MANUAL.md | ❌ 被本手册取代 |
| ARCHITECTURE.md | ❌ 被本手册取代 |
| DESIGN_SPEC.md | ❌ 被本手册取代 |
| REDESIGN_PLAN.md | ❌ 被本手册取代 |
| AGENT_INTEGRATION_PLAN.md | ⚠️ 互补参考 |
| IMPLEMENTATION_GUIDE.md | ❌ 被本手册取代 |
| TASK_SUMMARY.md | ❌ 被本手册取代 |
| Markdown转Word模板系统开发手册.md | ⚠️ 互补参考（附录 D 已浓缩） |
| PDF阅读器开发手册.md | ⚠️ 互补参考（附录 C 已浓缩） |

---

> **文档版本**: v8.0 正式版
> **核心原则**:
> - 先修复后增量，确保基础链路通畅
> - 以落地可执行为最高优先级
> - 复杂方案必须找到简化的开源替代品
> - 每个章节独立开发、独立验收、独立复盘
> - 技术手册是唯一权威参考
> - 用户反馈驱动迭代，闭环循环推进
> - 推迟不等于放弃，等待架构条件成熟后实施