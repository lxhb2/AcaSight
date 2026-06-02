# AcaSight 学术视界 — 正式技术手册 v9.0

> **生成日期**: 2026-05-29
> **状态**: 定稿（取代 v8.2 及所有旧版计划文档）
> **适用范围**: 开发团队、技术评审、验收测试
>
> **权威级别**: 本文档是 AcaSight 唯一的正式技术手册，取代此前所有版本。
>
> **v9.0 更新要点**：
> - 整合 UPDF 竞品分析报告，标注差距与优化方向
> - 规范六步迭代开发流程（Step 1-6 明确定义）
> - 新增 Chapter C 搜索排序优化 + 空状态改版（P0）
> - 新增 Chapter D 引用关系图谱（Semantic Scholar + ECharts，P1）
> - 新增 Chapter E 笔记纲要 AI 生成 + 高亮定位（P1）
> - 明确 Markdown 编辑器替换方案：Milkdown（已确认）
> - 修正 Chapter 编号体系（原 A/B/C/D/E/F/G/H → 新 A~H 连续编号）
> - 所有「待开发」功能标注 UPDF 对标优先级
> - 新增 matt pock-skills 使用说明（开发加速）

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

### Step 5 技术复盘模板

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

---

## 第一部分：现状总览

### 1.1 项目定位

**AcaSight（学术视界）**：面向研究生的全能学术智能体应用，Web 单页应用 + FastAPI 后端，未来可 Tauri 打包为桌面应用。

核心场景：文献检索 → PDF 精读标注 → 知识图谱关联 → AI Agent 分析 → 学术写作排版导出

**与 UPDF 竞品差异化定位**：

| 维度 | UPDF | AcaSight |
|------|------|----------|
| 定位 | 通用 PDF 工具 | 学术专用智能体 |
| 文献管理 | ❌ | ✅ Zotero 集成 |
| 学术搜索 | 单源 | ✅ 6 源聚合 |
| 六步法写作 | ❌ | ✅ 专有工作流 |
| AI 对话 | 通用 | ✅ Nature 风格学术润色 |
| 知识图谱 | ❌ | 🔲 开发中（Chapter D） |
| RAG 问答 | 多文件 | 🔲 开发中（Chapter G） |

### 1.2 技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 前端框架 | React + TypeScript + Vite | React 18, TS 5, Vite 5 |
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

### 1.3 前端架构（v9.0 当前状态）

```
App.tsx
  └─ ThemeProvider
       └─ AppProvider (contexts/AppContext.tsx — 集中全局状态)
           └─ ObsidianLayout (Layout/ — 纯布局编排壳，已移除拖拽排序)
               ├─ IconBar（左侧图标导航：文件/搜索/图表/白板/Zotero/Agent/设置）
               ├─ PanelContainer（面板容器，无拖拽）
               │   ├─ FileExplorerView   (Views/)
               │   ├─ EditorView         (Views/ — PDF/MD + 笔记侧栏 + 目录侧栏)
               │   ├─ SearchPage         (Search/ — uiverse.io 风格美化)
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

### 1.4 已落地模块清单（v9.0 精确清点）

> ✅ 可用  ⚠️ 部分可用  ❌ 未开发  🔲 待开发（标注 UPDF 对标）

| 模块 | 位置 | 真实状态 | UPDF 对标 | 说明 |
|------|------|----------|-----------|------|
| **前端架构** | frontend/ | ✅ 可用 | - | React 18 + TS + Vite + Tailwind |
| Obsidian 布局 | Layout/ObsidianLayout.tsx | ✅ 可用 | - | 图标栏 + 面板容器（拖拽已移除） |
| AppContext 全局状态 | contexts/AppContext.tsx | ✅ 可用 | - | 重构完成，构建通过，AI Tab 已移除 |
| 主题系统 | contexts/ThemeContext.tsx | ✅ 可用 | - | 深色/浅色切换，玻璃浮雕 UI |
| **Layer 1: 论文检索** | | ✅ 可用 | 🔲 排序需优化 | |
| 6 源并行检索 | services/search_service.py | ✅ 可用 | ✅ 已覆盖 | CORE/OpenAlex/Semantic Scholar/Crossref/Europe PMC/arXiv |
| 搜索结果页 | Search/SearchPage.tsx | ✅ 可用 | 🔲 空状态需改版 | uiverse.io 风格，去重排序 + Zotero 保存 |
| **Layer 2: 绘图** | | ⚠️ 部分可用 | - | |
| Plotly.js 图表 | Charts/ChartPanel.tsx | ✅ 可用 | - | 8 种图表 + AI 推荐 UI |
| 多格式数据解析 | ChartPanel.tsx | ✅ 可用 | - | CSV/JSON/Excel |
| 12 学术模板 | Charts/chartTemplates.ts | ✅ 可用 | - | XRD/TG/FTIR/CV/Nyquist 等 |
| 全自动绘图 API | routers/chart_auto.py | ✅ 可用 | - | 已验证端到端正常 |
| 半自动 AI 向导 | - | ❌ 未开发 | - | |
| **Layer 0: 数据存储** | | ✅ 可用 | - | |
| PDF 存储服务 | services/storage_service.py | ✅ 可用 | - | SHA256 去重 |
| Zotero 同步桥 | services/zotero_sync.py | ✅ 可用 | ✅ 独有 | MCP JSON-RPC |
| ChromaDB 向量服务 | services/vector_service.py | ✅ 可用 | 🔲 RAG 待深化 | 语义分块 + cosine 距离 |
| Markdown→Word 模板 | services/template_service.py | ✅ 可用 | - | python-docx 模板生成 |
| 模板 API | routers/template.py | ✅ 可用 | - | POST /api/template/generate |
| **AI 服务** | | ✅ 可用 | - | |
| AI 配置面板 | Settings/SettingsModal.tsx | ✅ 可用 | - | Cherry Studio 风格，7 提供商 |
| AI 服务核心 | services/ai_service.py | ✅ 可用 | - | 多 Provider 路由 + 动态配置 |
| 模型列表动态获取 | routers/ai_config.py | ✅ 可用 | - | /api/ai/test 返回 models 列表 |
| AI Key 存储脱敏 | routers/ai_config.py | ✅ 已修复 | - | 跳过含 `****` 的 key 更新 |
| **PDF 阅读器** | | ✅ 可用 | 🔲 笔记纲要缺失 | |
| PDF.js 连续滚动渲染 | Views/EditorView.tsx | ✅ 可用 | ✅ 已覆盖 | 上下滚动 + onScroll 页码追踪 |
| 文字选择与高亮 | Views/EditorView.tsx + index.css | ✅ 可用 | ✅ 已覆盖 | 拖拽移除 + textLayer pointer-events修复 |
| PDF 页面间隙修复 | index.css | ✅ 已修复 | - | textLayer position: relative→absolute |
| 选中高亮样式修复 | index.css | ✅ 已修复 | - | ::selection color: transparent 显式 |
| 标注工具栏 | Views/EditorView.tsx | ✅ 可用 | 🔲 缺笔记纲要 | 4色高亮 + 下划线 + 文本注释 + 橡皮擦 |
| AnnotationOverlay | AnnotationOverlay.tsx | ✅ 可用 | - | position: absolute 覆盖层 |
| 右侧面板 | EditorView.tsx | ✅ 可用 | 🔲 缺 AI 纲要 | 仅笔记 + 目录（AI Tab 已移除） |
| Zotero PDF 三级策略 | routers/zotero.py | ✅ 已修复 | - | MCP → base64 → 本地存储 |
| PDF 全文提取 | services/pdf_service.py | ✅ 可用 | - | PyMuPDF 提取 |
| **笔记系统** | | ⚠️ 基础可用 | 🔲 对标 UPDF | |
| 笔记面板 | EditorView.tsx | ✅ 可用 | 🔲 缺 AI 纲要生成 | 手动笔记 + 标签 |
| 高亮→原文定位 | - | ❌ 未开发 | 🔲 UPDF 有 | 存储页码 + 点击跳转 |
| **Agent 系统** | | ✅ 已打通 | - | |
| Agent Core | agent/core.py | ✅ 可用 | - | ReAct 循环 + 超时保护 + 纯文本回退 |
| Skill Registry | agent/skill_registry.py | ✅ 可用 | - | 12 个学术技能注册 |
| 12 学术技能 | agent/skills/nature_skills.py | ✅ 可用 | - | 全部有 try/except + _safe_chat |
| SSE 流式端点 | agent/router.py | ✅ 可用 | - | 8 个端点，多轮对话，会话持久化 |
| 前端 AgentPanel | Agent/AgentPanel.tsx | ✅ 可用 | - | 多会话侧边栏 + 流式渲染 + 技能面板 |
| ContextualAgentBar | Agent/ContextualAgentBar.tsx | ✅ 可用 | - | 跟随鼠标气泡，选中文字触发 |
| 全局权限升级 | agent/skills/ | ✅ 可用 | - | 数据处理 + 自动绘图 + 知识图谱 + 文档解析 |
| **知识图谱** | | ⚠️ 基础可用 | 🔲 最大差距 | |
| 本地文献图谱 | Views/GraphView.tsx | ✅ 可用 | 🔲 缺在线关联 | react-force-graph-2d |
| 引用关系图谱 | - | ❌ 未开发 | 🔲 UPDF 核心功能 | Semantic Scholar API + ECharts 力导向图 |
| **其他组件** | | | | |
| Markdown 编辑器 | Notes/MarkdownEditor.tsx | ⚠️ 基础可用 | 🔲 缺 KaTeX | Milkdown 替代方案已确定 |
| 白板 | Whiteboard/ExcalidrawBoard.tsx | ✅ 可用 | - | Excalidraw 集成，图标缩小修复 |
| 知识图谱 | Views/GraphView.tsx | ✅ 可用 | 🔲 待深化 | 本地+在线文献合并，react-force-graph-2d |
| 智能写作 | Agent 体系内 | ✅ 已合并 | - | 独立 WritingPanel 已取消，能力由 Agent 提供 |
| ZoteroPanel | Zotero/ZoteroPanel.tsx | ✅ 可用 | ✅ 独有 | 集合树+文献列表 |
| OutlineView | Views/OutlineView.tsx | ❌ 占位 | - | 空壳 |
| TagsView | Views/TagsView.tsx | ❌ 占位 | 🔲 标签系统待完善 | 空壳 |

### 1.5 已知缺陷（v9.0 更新）

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
| **搜索结果排序单一** | P1 | 🔲 待修 | 仅按时间，缺引用权重 + 语义相似度 |
| **搜索空状态简陋** | P2 | 🔲 待修 | 对标 UPDF「1分钟找100篇」引导 |
| **笔记无 AI 纲要** | P1 | 🔲 待修 | UPDF 核心亮点 |
| **高亮无原文定位** | P1 | 🔲 待修 | 点击笔记无法跳转 PDF 页码 |
| **引用图谱未开发** | P1 | 🔲 待修 | UPDF 核心功能，AcaSight 最大差距 |
| **Markdown 无 KaTeX** | P2 | 🔲 待修 | Milkdown 方案已确定，待实施 |

---

## 第二部分：技术路线可行性研判（v9.0）

### 2.1 开源替代方案决策矩阵

| 功能模块 | 自建方案 | 替代方案 | 节省工作量 | 风险 | 判定 |
|----------|----------|---------|-----------|------|------|
| PDF 标注系统 | 自建后端+前端渲染 | **react-pdf + AnnotationOverlay 自建** | 0% | 低 | ✅ 采用（已落地） |
| 引用图谱 | 自建 D3.js | **ECharts 力导向图**（+ Sigma.js 备选） | 50%+ | 低 | ✅ 采用（Chapter D） |
| RAG 引擎 | 自建3层 RAG | **RAGFlow**（Docker 部署） | 80%+ | 低 | ✅ 待落地（Chapter G） |
| 学术格式引擎 | python-docx 手动实现 | **Pandoc + citeproc + python-docx** | 70%+ | 低 | ⚠️ 混合（已部分落地） |
| Markdown+KaTeX | react-markdown | **Milkdown** | 70%+ | 低 | ✅ 待落地（Chapter F） |
| 以文搜文 | 自建 Embedding | **ChromaDB + BGE Embedding** | 60%+ | 低 | ✅ 已落地（Layer 0） |

### 2.2 替代方案详细说明

#### react-pdf + AnnotationOverlay（PDF 核心 — 已落地）
- 基于 react-pdf 渲染层 + 自建 AnnotationOverlay 覆盖层
- textLayer 保持 absolute 定位覆盖 canvas，canvas pointer-events: none
- 标注系统：4色高亮 + 下划线 + 文本注释 + 橡皮擦
- 关键技术点：textLayer position: absolute（非 relative），::selection color: transparent 显式
- 集成方式：EditorView.tsx 中 `<Page>` + `<AnnotationOverlay>` 双层结构

#### ECharts 力导向图（引用图谱 — Chapter D）
- 替代 D3.js，减少前端依赖
- ECharts 5.x 内置力导向布局，支持节点缩放/拖拽/点击事件
- 节点大小映射引用次数，颜色按研究领域聚类
- 点击节点 → 侧拉面板显示摘要 + 一键下载 PDF
- 数据来源：Semantic Scholar `/paper/{paper_id}/references` 和 `/citations` API

#### RAGFlow（RAG 引擎 — Chapter G）
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
- 待落地：pypandoc 全流程集成 + GB/T 7714 CSL 样式

#### Milkdown（Markdown 编辑器 — Chapter F）
- GitHub ~8k Stars，v7.21.1
- 插件驱动架构，KaTeX 原生支持
- 所见即所得（WYSIWYG），类 Typora 编辑体验
- 官方 React 组件 `@milkdown/react`
- 安装：`npm install @milkdown/react @milkdown/core @milkdown/preset-commonmark @milkdown/plugin-math`

### 2.3 功能研判矩阵（v9.0 更新）

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
| ~~玻璃浮雕 UI~~ | CSS glass morphism | 低 | 0 | 低 | ✅ | ✅ 已完成（Chapter B） |
| **搜索排序优化** | 混合排序算法 | 低 | 0 | 低 | ✅ | 🔲 Chapter C（P0） |
| **空状态改版** | 引导式 UI | 低 | 0 | 低 | ✅ | 🔲 Chapter C（P0） |
| **引用关系图谱** | ECharts 力导向图 | 中 | 1 | 中 | ✅ | 🔲 Chapter D（P1） |
| **笔记纲要 AI 生成** | LLM 聚合批注 | 中 | 0 | 低 | ✅ | 🔲 Chapter E（P1） |
| **高亮原文定位** | 存储页码 + scrollIntoView | 低 | 0 | 低 | ✅ | 🔲 Chapter E（P1） |
| **Markdown 增强** | Milkdown | 中 | 1 | 低 | ✅ | 🔲 Chapter F（P2） |
| **论文数据库 CRUD** | 后端 + 前端面板 | 中 | 0 | 低 | ✅ | 🔲 Chapter C（P1） |
| **RAG 引擎** | RAGFlow (Docker) | 中 | 1 | 低 | ⚠️ | 🔲 Chapter G（P2） |
| **学术格式引擎深化** | Pandoc + citeproc | 中 | 1 | 低 | ✅ | 🔲 Chapter H（P3） |
| **Zotero 窗口嵌入** | Tauri + SetParent | 高 | 3 | 高 | ❌ | ❌ 推迟至桌面化 |
| **系统全局悬浮窗** | Tauri 透明置顶 | 高 | 2 | 高 | ❌ | ❌ 推迟至桌面化 |
| **OnlyOffice 嵌入** | Docker | 高 | 3 | 高 | ❌ | ❌ 推迟至 Docker 环境 |

---

## 第三部分：正式开发手册 — 分章实施（v9.0）

### 章节进度总览

```
✅ Chapter A: 阻断修复 (P0)        ✅ Chapter B: 玻璃浮雕 UI (P1)
🔲 Chapter C: 搜索增强 + 论文数据库 (P0-P1)
🔲 Chapter D: 引用关系图谱 (P1)
🔲 Chapter E: 笔记纲要 + 高亮定位 (P1)
🔲 Chapter F: Markdown 增强 (P2)
🔲 Chapter G: RAG 引擎 (P2)
🔲 Chapter H: 学术格式引擎深化 (P3)
❌ Chapter I+: 推迟章节
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

### Chapter B: 玻璃浮雕 UI（P1）— ✅ 已完成（v8.2）

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| B.1 | CSS 变量体系 | index.css | ✅ |
| B.2 | 面板容器玻璃化 | ObsidianLayout.tsx + index.css | ✅ 使用 --glass-bg + backdrop-filter |
| B.3 | 图标栏玻璃化 | ObsidianLayout.tsx + index.css | ✅ 使用 --glass-icon-bar-bg + blur |
| B.4 | 设置面板玻璃化 | SettingsModal.tsx + index.css | ✅ 使用 CSS 变量 (var(--glass-bg) 等) |
| B.5 | 浅色主题适配 | index.css | ✅ v8.2: --glass-bg: rgba(255,255,255,0.95), blur: 4px, 柔和阴影 |
| B.6 | 绘图面板保持方框 | ChartPanel + index.css | ✅ .panel-charts { border-radius: 0; box-shadow: none; } |

**验收结果**: 全部通过 ✅

---

### Chapter C: 搜索增强 + 论文数据库 CRUD（P0-P1，预估 8h）

> 🆕 v9.0 新增：整合 UPDF 竞品分析，优化搜索体验 + 完善论文入库管理

#### C.1 搜索排序优化（P0，预估 2h）

**现状**：搜索结果仅按发表年份排序，缺失相关性、引用次数、语义相似度权重

**优化方案**：
```typescript
// 混合排序算法（前端 SearchPage.tsx）
type SortWeight = {
  relevance: number;    // 文本相关性 0-1
  citations: number;    // 引用次数（对数归一化）
  year: number;         // 发表年份（衰减函数）
  semantic: number;     // 语义相似度 0-1（ChromaDB）
};

function hybridSort(papers: PaperItem[]): PaperItem[] {
  return papers.sort((a, b) => {
    const scoreA = computeScore(a);
    const scoreB = computeScore(b);
    return scoreB - scoreA;
  });
}
```

**实施步骤**：
1. 后端 `search_service.py` 返回结果增加 `relevance_score`（关键词匹配度）
2. 前端 `SearchPage.tsx` 增加排序下拉框（相关度/引用数/年份/混合）
3. 调用 ChromaDB 获取语义相似度（可选，勾选「语义排序」时触发）

#### C.2 空状态改版（P0，预估 2h）

**现状**：搜索页空状态仅显示「暂无结果」，缺乏引导

**优化方案**（对标 UPDF「1分钟找到100篇」）：
```
┌─────────────────────────────────────────┐
│  🔍  学术搜索                        │
│  ┌─────────────────────────┐          │
│  │ 输入关键词 / DOI / 论文标题... │  │
│  └─────────────────────────┘          │
│                                       │
│  💡 搜索技巧：                        │
│  • 输入关键词 → 6 源并行检索          │
│  • 输入 DOI → 精确匹配单篇论文        │
│  • 上传 PDF → 以文搜文               │
│  • 支持中文 / 英文 / 中英混合        │
│                                       │
│  📊 已索引 2.2 亿+ 篇学术论文       │
│  🎯 平均响应时间 < 3 秒             │
└─────────────────────────────────────────┘
```

**实施步骤**：
1. 修改 `SearchPage.tsx` 空状态组件
2. 增加搜索技巧提示（动画渐入）
3. 增加实时索引统计（调用 `/api/search/stats` 端点）

#### C.3 论文数据库 CRUD（P1，预估 4h）

**API 设计**：
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

**后端实施**（预估 2h）：
- `routers/papers.py`：实现上述 7 个端点
- `services/paper_service.py`：CRUD 逻辑 + ChromaDB 同步

**前端实施**（预估 2h）：
- `Views/FileExplorerView.tsx`：论文列表 + 排序 + 筛选
- `Views/TagsView.tsx`：标签云 + 点击筛选（从占位改为实装）

**验收标准**：
- 论文列表加载正常，支持按标题/年份/期刊排序
- 搜索结果 → 一键入库
- 标签云渲染 + 点击筛选
- `npm run build` 零错误 + 后端 Swagger 文档更新

---

### Chapter D: 引用关系图谱（P1，预估 10h）

> 🆕 v9.0 新增：对标 UPDF 核心功能，实现学术文献引用关系可视化

#### D.1 数据流架构

```
用户输入（论文标题/DOI/上传PDF）
         │
         ├──→ Semantic Scholar API
         │     ├── /paper/{paper_id}/references  (引用文献)
         │     └── /paper/{paper_id}/citations   (被引文献)
         └──→ OpenAlex API（备用）
               └── /works/{doi}  (引用关系)
                    │
                    ▼
        后端 FastAPI /api/graph/references
                    │
                    ▼
        NetworkX 构建图结构
                    │
         ┌──────────┼──────────┐
         ▼          ▼          ▼
    节点数据   边数据    聚类数据
         │          │          │
         └──────────┼──────────┘
                    ▼
            前端 ECharts 力导向图
```

#### D.2 后端实施（预估 4h）

**API 端点**：
```python
# routers/knowledge_graph.py（扩展现有）

@router.get("/api/graph/references")
async def get_references(doi: str, max_depth: int = 2):
    """获取论文引用/被引关系图谱"""
    # 1. 调用 Semantic Scholar API
    # 2. NetworkX 构建图结构
    # 3. Louvain 算法主题聚类
    # 4. 返回节点+边+聚类数据
    pass

@router.get("/api/graph/co_citation")
async def get_co_citation(doi: str, max_nodes: int = 200):
    """共引分析：找到经常被一起引用的论文"""
    pass
```

**关键技术点**：
- Semantic Scholar API 限流：免费版 100 req/5min，需加缓存
- 图谱规模控制：限制最大节点数 200，避免前端卡顿
- WebWorker 计算布局：力导向图布局计算放入 WebWorker

#### D.3 前端实施（预估 6h）

**组件架构**：
```
Views/GraphView.tsx（改造现有）
    ├── GraphToolbar.tsx       — 缩放/筛选/聚类切换
    ├── GraphNodeDetail.tsx    — 点击节点侧拉面板
    └── GraphLegend.tsx       — 图例（颜色=聚类，大小=引用次数）
```

**ECharts 配置要点**：
```typescript
// 力导向图配置
const graphOption: EChartsOption = {
  series: [{
    type: 'graph',
    layout: 'force',
    data: nodes.map(n => ({
      name: n.title,
      symbolSize: Math.log(n.citations + 1) * 10,  // 引用次数→节点大小
      itemStyle: { color: clusterColors[n.cluster_id] },  // 聚类→颜色
      label: { show: n.citations > 100 },  // 高引论文显示标签
    })),
    edges: edges.map(e => ({
      source: e.source,
      target: e.target,
      lineStyle: { width: e.weight * 2 },  // 共引强度→边粗细
    })),
    force: {
      repulsion: 300,   // 节点斥力
      edgeLength: [80, 200],  // 边长度范围
    },
    emphasis: {
      focus: 'adjacency',  // 悬停高亮相邻节点
    },
  }],
};
```

**交互设计**：
| 交互 | 行为 |
|------|------|
| 悬停节点 | 显示论文标题、作者、年份、引用次数 |
| 点击节点 | 侧拉面板显示摘要、关键词、PDF 下载按钮 |
| 滚动滚轮 | 缩放图谱 |
| 拖拽节点 | 固定位置 |
| 筛选器 | 按年份/聚类/最小引用次数筛选 |

**验收标准**：
- 输入 DOI → 生成引用关系图谱（≤200 节点）
- 节点大小 = 引用次数，颜色 = 主题聚类
- 点击节点 → 侧拉面板显示详情 + 一键下载 PDF
- 图谱渲染流畅（FPS ≥ 30）
- `npm run build` 零错误

---

### Chapter E: 笔记纲要 AI 生成 + 高亮定位（P1，预估 6h）

> 🆕 v9.0 新增：对标 UPDF AI 精读功能

#### E.1 笔记纲要 AI 生成（P1，预估 3h）

**功能描述**：收集用户所有高亮标注，用 LLM 生成结构化纲要

**实施步骤**：

1. 后端新增端点 `POST /api/notes/generate_outline`：
   ```python
   @router.post("/api/notes/generate_outline")
   async def generate_outline(req: OutlineRequest):
       """根据高亮标注生成阅读纲要"""
       # 1. 获取该 PDF 的所有 annotations（高亮+注释）
       # 2. 按页码排序
       # 3. 构造 Prompt：论文标题 + 所有高亮文本
       # 4. 调用 LLM 生成结构化纲要
       # 5. 返回 Markdown 格式纲要
       pass
   ```

2. 前端 `EditorView.tsx` 笔记面板增加「✨ AI 生成纲要」按钮：
   ```typescript
   // NotesPanel.tsx
   <button onClick={handleGenerateOutline}>
     ✨ AI 生成纲要
   </button>
   ```

3. 纲要展示：生成后插入笔记列表顶部（可手动编辑）

**Prompt 模板**：
```
你是一位学术助手。请根据以下论文高亮标注，生成结构化阅读纲要。

论文标题：{title}
高亮标注（按页码排序）：
{page 1}: {highlight_1}
{page 3}: {highlight_2}
...

要求：
1. 按「研究背景→问题→方法→结果→结论」结构组织
2. 每条用一句话概括
3. 输出 Markdown 格式
```

#### E.2 高亮原文定位（P1，预估 3h）

**功能描述**：点击笔记中的高亮记录，自动跳转到 PDF 对应页码 + 脉冲高亮动画

**数据存储改造**：
```typescript
// types/annotation.ts
interface Annotation {
  id: string;
  pageNumber: number;      // 🆕 存储页码
  rects: Rect[];           // 坐标
  color: string;
  note?: string;
  createdAt: string;
}
```

**实施步骤**：

1. `AnnotationOverlay.tsx` 创建标注时记录 `pageNumber`：
   ```typescript
   // 在 PDF Page 组件内创建标注时
   const pageNum = getCurrentPageNumber();  // 从 Page 组件获取
   const annotation = { ..., pageNumber: pageNum };
   ```

2. 笔记面板点击标注 → 跳转：
   ```typescript
   // NotesPanel.tsx
   const handleClickAnnotation = (annotation: Annotation) => {
     // 1. 切换到 PDF 标签页
     setActiveTabId(annotation.tabId);
     // 2. 跳转到对应页码
     setCurrentPage(annotation.pageNumber);
     // 3. 脉冲高亮动画
     triggerPulseAnimation(annotation.rects);
   };
   ```

3. 脉冲高亮动画（CSS）：
   ```css
   @keyframes pulse-highlight {
     0% { background: rgba(59, 130, 246, 0.6); }
     50% { background: rgba(59, 130, 246, 0.2); }
     100% { background: rgba(59, 130, 246, 0.6); }
   }
   .annotation-pulse {
     animation: pulse-highlight 1.5s ease-in-out 2;
   }
   ```

**验收标准**：
- 点击「✨ AI 生成纲要」→ 生成 Markdown 纲要
- 点击笔记中的高亮记录 → 跳转到 PDF 对应页码
- 跳转后脉冲高亮动画播放 2 次
- `npm run build` 零错误

---

### Chapter F: Markdown 增强（P2，预估 6h）

> 从 react-markdown 改为 Milkdown，节省 70% 工作量

#### F.1 Milkdown 集成（预估 2h）

**安装依赖**：
```bash
cd frontend
npm install @milkdown/react @milkdown/core @milkdown/preset-commonmark \
  @milkdown/plugin-math @milkdown/theme-nord
```

**组件改造**：
```tsx
// Notes/MarkdownEditor.tsx
import { ReactEditor } from '@milkdown/react';
import { commonmark } from '@milkdown/preset-commonmark';
import { math } from '@milkdown/plugin-math';
import { nord } from '@milkdown/theme-nord';

const MarkdownEditor: React.FC = () => {
  return (
    <ReactEditor
      plugins={[commonmark, math, nord]}
      initialValue="# 开始写作...\n\n支持 KaTeX: $E=mc^2$"
    />
  );
};
```

#### F.2 KaTeX 数学公式支持（预估 30min）

Milkdown 内置 `@milkdown/plugin-math`，自动渲染：

```markdown
行内公式：$E=mc^2$

块级公式：
$$
\\frac{\\partial f}{\\partial t} = D \\nabla^2 f
$$
```

#### F.3 实时预览（预估 0min）

Milkdown 是所见即所得（WYSIWYG），无需单独预览模式。

#### F.4 导出 Word（预估 1.5h）

对接已有 `template_service.py`：

```typescript
const handleExportWord = async () => {
  const markdown = editor.getMarkdown();
  const res = await fetch('/api/template/generate', {
    method: 'POST',
    body: JSON.stringify({ markdown, template: 'default' }),
  });
  // 下载 .docx 文件
};
```

**验收标准**：
- Markdown 编辑器支持实时预览（WYSIWYG）
- KaTeX 数学公式渲染正确
- 导出 Word 套用模板成功
- `npm run build` 零错误

---

### Chapter G: RAG 引擎（P2，预估 8h）

> 从自建3层 RAG 改为 RAGFlow，节省 80%+ 工作量

#### G.1 RAGFlow Docker 部署（预估 1h）

**docker-compose.yml**：
```yaml
version: '3'
services:
  ragflow:
    image: infiniflow/ragflow:v0.25.5
    ports:
      - "9380:9380"
    volumes:
      - ./ragflow/data:/ragflow/data
      - ./ragflow/logs:/ragflow/logs
    environment:
      - HF_ENDPOINT=https://huggingface.co
    deploy:
      resources:
        limits:
          memory: 16G
```

**启动**：
```bash
cd backend
docker-compose up -d ragflow
```

#### G.2 FastAPI ↔ RAGFlow API 对接（预估 2h）

**服务封装**：
```python
# services/rag_service.py
import httpx

RAGFLOW_BASE = "http://localhost:9380"

async def rag_query(question: str, dataset_id: str):
    """RAG 问答"""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{RAGFLOW_BASE}/api/retrieve",
            json={"question": question, "dataset_id": dataset_id}
        )
        return res.json()
```

#### G.3 RAG 问答端点（预估 1h）

```python
# routers/rag.py
@router.post("/api/rag/query")
async def rag_query(req: RAGQueryRequest):
    """RAG 问答（对接 RAGFlow）"""
    result = await rag_service.rag_query(req.question, req.dataset_id)
    return {"answer": result["answer"], "sources": result["sources"]}
```

#### G.4 前端问答集成（预估 2h）

**Agent 面板增强**：增加「RAG 模式」切换按钮：

```tsx
// Agent/AgentPanel.tsx
const [ragMode, setRagMode] = useState(false);

<AiModeSwitch>
  <button onClick={() => setRagMode(!ragMode)}>
    {ragMode ? '📚 RAG 模式' : '💬 普通模式'}
  </button>
</AiModeSwitch>
```

**验收标准**：
- RAGFlow Docker 正常运行
- 问答接口返回正确引用来源
- 前端问答面板可用（RAG 模式切换）
- `npm run build` 零错误

---

### Chapter H: 学术格式引擎深化（P3，预估 6h）

> 当前已落地：python-docx 模板生成。本章深化：Pandoc + citeproc 全流程

#### H.1 Pandoc + pypandoc 集成（预估 1h）

**系统安装 Pandoc**：
```bash
# Windows
choco install pandoc

# 验证
pandoc --version
```

**Python 绑定**：
```bash
pip install pypandoc
```

#### H.2 Markdown → DOCX/LaTeX/PDF（预估 1h）

```python
# services/format_service.py
import pypandoc

def md_to_docx(md_text: str, output_path: str, reference_doc: str = None):
    """Markdown → DOCX"""
    extra_args = []
    if reference_doc:
        extra_args += [f"--reference-doc={reference_doc}"]
    return pypandoc.convert_text(
        md_text, 'docx', format='markdown',
        outputfile=output_path, extra_args=extra_args
    )

def md_to_latex(md_text: str, output_path: str):
    """Markdown → LaTeX"""
    return pypandoc.convert_text(
        md_text, 'latex', format='markdown',
        outputfile=output_path
    )
```

#### H.3 citeproc 引用格式化（预估 1h）

```python
def md_to_docx_with_citations(md_text: str, output_path: str, csl_style: str = 'apa'):
    """Markdown → DOCX（含引用格式化）"""
    return pypandoc.convert_text(
        md_text, 'docx', format='markdown',
        outputfile=output_path,
        extra_args=[
            f"--csl={csl_style}.csl",
            "--citeproc",
            f"--bibliography=references.bib"
        ]
    )
```

#### H.4 前端格式导出 UI（预估 1h）

```tsx
// Views/EditorView.tsx（写作面板）
<ExportDropdown>
  <option value="docx">导出 DOCX</option>
  <option value="latex">导出 LaTeX</option>
  <option value="pdf">导出 PDF</option>
  <option value="html">导出 HTML</option>
</ExportDropdown>
```

**验收标准**：
- MD → DOCX 一键转换成功
- 参考文献自动格式化（CSL 样式）
- 内置 GB/T 7714 / APA / IEEE 三种模板
- `npm run build` 零错误

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

## 第四部分：开发优先级与时间线（v9.0）

```
已完成 (v7.0 + v8.0 + v8.2):
  ├─ Chapter A: 阻断修复 ✅
  ├─ Chapter B: 玻璃浮雕 UI ✅
  └─ 增量修复与功能优化 ✅

Phase 1 (当前):
  ├─ Chapter C: 搜索排序优化 + 空状态改版 (P0, 4h)
  ├─ Chapter C: 论文数据库 CRUD (P1, 4h)
  ├─ Chapter E: 笔记纲要 AI 生成 (P1, 3h)
  └─ Chapter E: 高亮原文定位 (P1, 3h)

Phase 2:
  ├─ Chapter D: 引用关系图谱 (P1, 10h)
  └─ Chapter F: Markdown 增强 (P2, 6h)

Phase 3:
  ├─ Chapter G: RAG 引擎 (P2, 8h)
  └─ Chapter H: 学术格式引擎深化 (P3, 6h)
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

## 第六部分：matt pock-skills 使用说明

> 🆕 v9.0 新增：启用 matt pock-skills 技能包加速开发

### 安装（仅需一次）

```bash
# 在 QClaw 控制界面执行
/skillhub_install install_skill matt pock-skills
```

### 可用技能清单（18 个）

| 技能 | 用途 | 适用 Chapter |
|------|------|---------------|
| `code-review` | 代码审查 | 所有 Chapter |
| `debugging` | 调试助手 | 所有 Chapter |
| `documentation` | 文档生成 | Chapter C/H |
| `refactoring` | 代码重构 | Chapter D/G |
| `testing` | 测试编写 | 所有 Chapter |
| `performance` | 性能优化 | Chapter D/F |
| `security` | 安全检查 | Chapter G/H |
| `accessibility` | 无障碍优化 | Chapter F |
| `i18n` | 国际化 | - |
| `ci-cd` | CI/CD 配置 | - |
| `docker` | Docker 优化 | Chapter G |
| `database` | 数据库优化 | Chapter C |
| `api-design` | API 设计 | Chapter C/D |
| `frontend` | 前端优化 | Chapter F |
| `backend` | 后端优化 | Chapter C/D/G |
| `ml` | 机器学习 | Chapter D/G |
| `data-viz` | 数据可视化 | Chapter D |
| `git` | Git 工作流 | 所有 Chapter |

### 使用示例

```
用户：用 code-review 技能审查 Chapter C 的搜索排序代码

Agent：
  1. 调用 skillhub matt pock-skills code-review
  2. 读取 SearchPage.tsx + search_service.py
  3. 输出审查报告（性能/安全/可维护性）
  4. 提出优化建议
```

---

## 第七部分：技术复盘 & 反馈流程

### 标准复盘模板

（同 Step 5 模板，此处省略）

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
| /api/agent/ask | POST | SSE 流式任务执行 |
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

## 附录 C: PDF 阅读器技术要点（v9.0 沉淀）

### C.1 核心架构
```
<div.pdf-page-wrapper (position: relative, margin:0 auto, lineHeight:0)>
  └─ <Page> (react-pdf)
       └─ <div.react-pdf__Page (position: relative)>
           ├─ <canvas> — pointer-events: none (不可交互)
           ├─ <div.textLayer> — position: absolute; inset:0; pointer-events: auto
           └─ AnnotationLayer — renderAnnotationLayer={false} (已禁用)
  └─ <AnnotationOverlay> — position: absolute; top:0; left:0
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

## 附录 D: Markdown 转 Word 模板服务要点（v9.0 沉淀）

### D.1 已落地架构
```
后端: routers/template.py (POST /api/template/generate)
      services/template_service.py (python-docx 模板生成)
前端: (待集成 Milkdown 导出)
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
@milkdown/react, @milkdown/core, @milkdown/preset-commonmark, @milkdown/plugin-math (Chapter F)
echarts (Chapter D, 引用图谱)
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
| TECHNICAL_MANUAL.md v1-v8.2 | ❌ 被本手册取代 |
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
| UPDF科研文献工具功能分析与实现方案.md | ⚠️ 互补参考（已整合到本文档） |

---

## 附录 G: UPDF 竞品对标速查表

| UPDF 功能 | AcaSight 对标状态 | 对应 Chapter | 优先级 |
|-----------|-------------------|---------------|--------|
| AI 总结摘要 | ✅ 已覆盖（Agent 面板） | - | - |
| AI 多文件问答 | 🔲 待开发 | Chapter G (RAG) | P2 |
| 13 种注释工具 | ✅ 已覆盖（4色+下划线+注释+橡皮擦） | - | - |
| 像 Word 一样编辑 | ❌ 非学术需求 | - | - |
| 16 种格式互转 | ✅ 已覆盖（MD→DOCX/LaTeX/PDF） | Chapter H | P3 |
| 发票管理 | ❌ 无关 | - | - |
| 文档对比 | 🔲 待开发 | Chapter J | P2 |
| 批量处理 | ✅ 已覆盖（合并/拆分/提取图片） | - | - |
| 多端可用 | ✅ Web（未来 Tauri 桌面） | - | - |
| 思维导图生成 | 🔲 待开发 | Chapter D（图谱） | P1 |
| OCR + 翻译 | 🔲 待开发 | Chapter E（AI 精读） | P2 |

---

> **文档版本**: v9.0 正式版
> **核心原则**:
> - 先修复后增量，确保基础链路通畅
> - 以落地可执行为最高优先级
> - 复杂方案必须找到简化的开源替代品
> - 每个章节独立开发、独立验收、独立复盘
> - 技术手册是唯一权威参考
> - 用户反馈驱动迭代，闭环循环推进
> - 推迟不等于放弃，等待架构条件成熟后实施
> - **竞品对标驱动优化**：UPDF 核心功能必须在 AcaSight 中找到对应或差异化替代
