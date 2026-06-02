# AcaSight 双人并行开发协作规范 v7.0

> **版本日期**: 2026-05-31
> **前置版本**: v6.0 (2026-05-31)
> **适用范围**: 两位开发者同时开发不同模块时的协作约束
> **核心目标**: 零文件冲突、接口契约先行、开发日志同步、前后端协议对齐、代码质量零容忍

---

## 一、角色分配

| 角色 | 职责范围 | 核心原则 |
|------|----------|----------|
| **开发者 A** (后端主导 + 前端数据层) | 后端全部模块 + `frontend/src/services/api.ts` + `frontend/src/types/` | A 是接口的定义者 |
| **开发者 B** (前端主导) | 前端全部组件 + `contexts/` + `hooks/` + `store/` + `index.css` | B 是接口的消费者，发现需求变更时通过日志通知 A |

---

## 二、项目当前状态（Phase 1-10 已完成，进入 Phase 11 质量深化与智能进化）

### 2.1 已完成模块状态矩阵

| 模块 | 后端 | 前端 | Agent | 状态 |
|------|------|------|-------|------|
| 论文搜索(6源+混合排序) | ✅ search_service | ✅ SearchPage | ✅ search_literature | 完成 |
| 用户上传文档 | ✅ storage_service | ✅ FileExplorer | - | 完成 |
| PDF阅读+标注 | ✅ pdf_service + annotations | ✅ EditorView + AnnotationOverlay | ✅ paper_qa | 完成 |
| 知识图谱 | ✅ knowledge_graph | ✅ GraphView | - | 完成 |
| 科研绘图 | ✅ chart_auto | ✅ ChartPanel | ✅ generate_figure | 完成 |
| AI写作 | ✅ chat/writing | ✅ AgentPanel + WritingWorkspace | ✅ draft_section/outline | 完成 |
| 文档导出(4格式+BibTeX) | ✅ format_service (DOCX/LaTeX/PDF/HTML) | ✅ MarkdownEditor | - | 完成 |
| Zotero同步 | ✅ zotero_sync | ✅ ZoteroPanel | - | 完成 |
| RAG问答 | ✅ rag_service | ✅ AgentPanel(RAG模式) | - | 完成 |
| RAG结构化拆分 | ✅ dimension_service + paper_dimensions | ✅ papersApi.getDimensions | - | 完成 |
| 人机交互中断 | ✅ writing.py SSE中断信号 | ✅ WritingInterruptDialog | ✅ WritingAgent.interrupt | 完成 |
| 统一存储服务 | ✅ unified_storage_service + cache_manager | ✅ storageApi + MaterialPanel | ✅ StorageAgent | 完成 |
| 六大模块Agent | ✅ base_module + 5个Agent + agent_orchestration | ✅ moduleApi + AgentPanel调度面板 | ✅ 全部5个Agent | 完成 |
| citeproc引用 | ✅ format_service (GB/T 7714 + BibTeX) | ✅ formatApi | - | 完成 |
| 降重润色(5模式) | ✅ writing.py /polish | ✅ WritingWorkspace | - | 完成 |
| 研究方向生成 | ✅ writing.py /research-direction | ✅ researchApi | - | 完成 |
| 试验方案生成 | ✅ writing.py /experiment-design | ✅ researchApi | - | 完成 |
| PPT生成 | ✅ writing.py /generate-ppt (python-pptx) | ✅ pptApi | - | 完成 |
| 写作流WorkflowEngine | ✅ workflow_engine.py (8状态+DAG) | ✅ workflowApi | - | 完成 |
| SSE流式大纲/章节 | ✅ writing.py SSE端点 | ✅ WritingWorkspace | - | 完成 |
| 一键全写+打字机效果 | ✅ writing.py | ✅ WritingWorkspace | - | 完成 |
| 大纲编辑器 | - | ✅ OutlineEditor.tsx | - | 完成 |
| 交叉审查修复 | ✅ 端点审计+协议对齐 | ✅ 裸fetch消除+类型安全 | - | 完成 |
| 引用关系图谱 | ✅ citation_network.py (Semantic Scholar) | ✅ GraphView引用网络检索栏 | - | 完成 |
| 精准引用匹配器 | ✅ citation_matcher.py (11维度+三因子打分) | ✅ WritingWorkspace引用推荐面板 | - | 完成 |
| 高亮→原文定位 | ✅ annotations已有页码 | ✅ EditorView标注Tab+AnnotationSidebarPanel | - | 完成 |
| APScheduler定时缓存清理 | ✅ main.py startup + apscheduler | - | - | 完成 |
| 浅色主题CSS补全 | - | ✅ .light块38个变量 | - | 完成 |
| 搜索空状态改版 | - | ✅ SearchPage搜索技巧+快捷操作 | - | 完成 |
| 笔记AI纲要生成 | ✅ annotations.py /generate-outline | ✅ NotesPanel→annotationsApi | - | 完成 |
| 全面裸fetch消除 | - | ✅ 全部替换为api.ts接口(0残留) | - | 完成 |
| 全面e:any消除 | - | ✅ catch块全部e:unknown(0残留) | - | 完成 |
| 组件any类型收窄(E.1-E.4) | - | ✅ STEPS icon/GraphView/ChartPanel/Zotero MCP | - | 完成 |
| api.ts any→精确类型(E.5) | ✅ AIConfig/PaperOutline等 | ✅ WritingWorkspace从api.ts导入类型 | - | 完成 |
| 半自动AI绘图向导(E.6) | ✅ chart_auto已有全自动API | ✅ ChartPanel 3步骤式向导UI | - | 完成 |
| 写作面板响应式适配(F.1) | - | ✅ useIsNarrow 768px断点 | - | 完成 |
| 键盘快捷键系统(F.2) | - | ✅ ObsidianLayout 5组全局快捷键 | - | 完成 |
| 无障碍基础a11y(F.3) | - | ✅ ARIA标签+焦点管理 | - | 完成 |
| 加载骨架屏(F.4) | - | ✅ 各面板Skeleton动画 | - | 完成 |
| RAGFlow Docker部署方案(G.1) | ✅ docker-compose.ragflow.yml 5容器 | - | - | 完成 |
| LangChain评估POC(G.2) | ✅ 评估结论:渐进式增强 | - | - | 完成 |
| CI/CD流水线(G.4) | ✅ GitHub Actions双任务 | - | - | 完成 |
| LangSmith可观测集成(G.4) | ✅ @traceable装饰器+降级 | - | - | 完成 |
| 后端API测试(119项) | ✅ pytest+httpx 20/20路由全覆盖 | - | - | 完成 |
| 前端测试框架Vitest | - | ✅ Vitest+RTL+组件测试 | - | 完成 |
| Bundle拆分+ErrorBoundary | - | ✅ Plotly/Mermaid动态import+全局错误边界 | - | 完成 |
| i18n国际化 | - | ✅ react-i18next+中英语言包(~454键) | - | 完成 |
| 外部项目集成评估 | ✅ 6项目评估完成 | - | - | 完成 |
| PaperBanana插图Pipeline | ✅ paper_banana_service+figure_executor+critic+style_guides | ✅ FigureGenerationPanel+Critic集成 | ✅ 6-Agent Pipeline | 完成 |
| SVG矢量图编辑 | ✅ figure_edit_service+sam_segmenter+SVG API | ✅ SvgEditorPanel | - | 完成 |
| Deep Research检索增强 | ✅ retriever_pubmed+retriever_searx_tavily+deep_research_service | ✅ DeepResearchPanel | - | 完成 |
| 架构优化(视觉评估+编排+循环检测+Formatter) | ✅ visual_evaluator+stage_orchestrator+ai_formatter | ✅ ArchPanel | - | 完成 |
| 插件系统+性能基准 | ✅ plugin_system+slow_query_analyzer+bench | ✅ PluginPanel+E2E测试 | - | 完成 |

### 2.2 代码质量现状

| 指标 | 数值 | 说明 |
|------|------|------|
| 前端组件裸 fetch | **0** | 全部走 api.ts 接口 |
| catch 块 e:any | **0** | 全部改为 e:unknown + instanceof Error 缩窄 |
| api.ts 接口总数 | **~134** | 覆盖全部后端端点 |
| npm run build | ✅ 零错误 | TypeScript 严格模式通过 |
| 后端API测试 | **119项通过** | 20/20路由100%覆盖(Phase 10新路由待补) |
| 前端组件残留 any | **6** | 第三方库5 + Milkdown 1（不可修复） |
| api.ts 残留 any | **5处** | B-side依赖4 + 合理Record 1 |
| 前端组件文件 | **39+** | 12目录覆盖全部功能 |
| i18n键总数 | **~454** | 中英双语完整覆盖 |
| 后端路由文件 | **25** | 全部功能端点 |
| 后端服务文件 | **34** | 含Phase 10新增7个 |
| 前端单元测试 | **5文件49用例** | 待扩展 |
| E2E测试 | **1文件11用例** | Playwright+Chromium |

### 2.3 Phase 11 聚焦方向

Phase 10 完成了能力跃升（插图Pipeline/SVG编辑/Deep Research/架构优化/插件系统），项目功能已趋完整。Phase 11 聚焦**质量深化**与**智能进化**：

| 聚焦领域 | 核心问题 | 目标 |
|----------|----------|------|
| **测试覆盖** | 前端仅5个单元测试文件，E2E仅11用例；后端缺Phase 10新路由测试 | 测试覆盖率显著提升 |
| **前端性能** | 无Bundle分析、无虚拟滚动、无渲染优化 | 首屏<2s、交互<100ms |
| **数据持久化** | 前端状态全内存，刷新丢失；无自动保存 | 状态持久化+自动保存+可恢复 |
| **写作体验** | 无版本历史、无Diff视图、无模板系统 | 版本可追溯+模板可复用 |
| **安全监控** | 无认证、无前端错误追踪、无性能监控 | 安全加固+可观测性 |

---

## 三、Phase 11 开发方向规划

### 3.1 方向总览

```
┌──────────────────────────────────────────────────────────────────────────┐
│                Phase 11: 质量深化与智能进化                               │
│                                                                          │
│  🔴 方向R: 测试覆盖深化                                                  │
│  优先级: P1 ｜ 依赖: 无                                                  │
│  目标: Phase10新路由测试 + 前端组件测试扩展 + E2E场景扩展 + 契约测试     │
│                                                                          │
│  🟠 方向S: 前端性能优化                                                  │
│  优先级: P1 ｜ 依赖: 无                                                  │
│  目标: Bundle分析+分割优化 + 虚拟滚动 + 渲染优化 + 资源懒加载           │
│                                                                          │
│  🟡 方向T: 数据持久化与恢复                                              │
│  优先级: P2 ｜ 依赖: 方向R                                               │
│  目标: 工作区状态持久化API + zustand-persist + 自动保存 + 数据导出导入   │
│                                                                          │
│  🟢 方向U: 写作体验升级                                                  │
│  优先级: P2 ｜ 依赖: 方向T                                               │
│  目标: 版本历史(diff存储+对比+恢复) + 写作模板系统(CRUD+分类+分享)      │
│                                                                          │
│  🔵 方向V: 安全与监控                                                    │
│  优先级: P3 ｜ 依赖: 方向R                                               │
│  目标: API密钥加密增强 + 前端错误追踪 + 性能监控 + 限流+CORS加固        │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 方向R: 测试覆盖深化 — 详细任务

| 阶段 | 功能 | 开发者 | 开发方式 | 依赖 |
|------|------|--------|----------|------|
| R.1 | Phase 10新路由后端测试(arch/plugins/paper_banana/figure_edit/deep_research 5个路由) | A | pytest+httpx新增5个test文件 | 无 |
| R.2 | 前端核心组件单元测试扩展(SearchPage/WritingWorkspace/GraphView/AgentPanel/ChartPanel/SvgEditorPanel) | B | Vitest+RTL新增6个test文件 | 无 |
| R.3 | E2E测试场景扩展(插图生成/SVG编辑/Deep Research/插件管理/架构工具/写作全流程) | B | Playwright新增15+用例 | 无 |
| R.4 | API契约自动化测试(api.ts路径vs后端路由一致性校验脚本) | A | 新增contract_test.py | R.1 |

### 3.3 方向S: 前端性能优化 — 详细任务

| 阶段 | 功能 | 开发者 | 开发方式 | 依赖 |
|------|------|--------|----------|------|
| S.1 | Bundle分析+代码分割优化(rollup-plugin-visualizer+chunk策略调优+tree-shaking验证) | B | vite.config.ts优化+分析报告 | 无 |
| S.2 | 虚拟滚动(搜索结果/论文列表/引用列表大数据渲染，react-window或自研) | B | 新增useVirtualScroll hook | 无 |
| S.3 | React渲染优化(React.memo/useMemo/useCallback审查+Profiler重渲染检测+key优化) | B | 逐组件审查优化 | S.1 |
| S.4 | 图片与资源懒加载(PDF缩略图/图表预览懒加载+SVG sprite优化+字体预加载) | B | 新增useLazyImage hook | S.1 |

### 3.4 方向T: 数据持久化与恢复 — 详细任务

| 阶段 | 功能 | 开发者 | 开发方式 | 依赖 |
|------|------|--------|----------|------|
| T.1 | 工作区状态持久化API(workspace state save/restore/list/delete) | A | 新增workspace_state.py | 无 |
| T.2 | 前端状态持久化(zustand-persist + localStorage + IndexedDB大对象) | B | store层改造 | T.1 |
| T.3 | 自动保存机制(写作内容定时保存+冲突检测+离线队列) | B | 新增useAutoSave hook | T.2 |
| T.4 | 数据导出导入(workspace backup/restore JSON+选择性导入) | A+B | A:后端端点 B:前端UI | T.1 |

### 3.5 方向U: 写作体验升级 — 详细任务

| 阶段 | 功能 | 开发者 | 开发方式 | 依赖 |
|------|------|--------|----------|------|
| U.1 | 版本历史后端(diff存储+版本列表+版本对比+一键恢复) | A | 新增version_history.py | T.1 |
| U.2 | 版本历史前端(时间线UI+Diff视图+一键恢复+版本备注) | B | 新增VersionHistoryPanel | U.1 |
| U.3 | 写作模板系统后端(模板CRUD+分类标签+分享+默认模板) | A | 新增writing_template_service.py | 无 |
| U.4 | 写作模板系统前端(模板浏览+应用+自定义+导入导出) | B | 新增TemplateGallery | U.3 |

### 3.6 方向V: 安全与监控 — 详细任务

| 阶段 | 功能 | 开发者 | 开发方式 | 依赖 |
|------|------|--------|----------|------|
| V.1 | API密钥加密增强(crypto.py扩展+密钥轮换+环境变量隔离) | A | 扩展crypto.py | 无 |
| V.2 | 前端错误追踪(全局错误收集+错误边界上报+用户反馈弹窗) | B | 新增useErrorTracker hook | 无 |
| V.3 | 性能监控仪表盘(后端指标收集+前端Web Vitals+健康度评分) | A | 新增monitoring_service.py | V.1 |
| V.4 | 请求限流与CORS加固(rate limiting中间件+origin白名单+请求大小限制) | A | main.py中间件 | V.1 |

### 3.7 Phase 11 任务分配

**开发者 A (后端)**:
- R.1+R.4: Phase 10新路由测试+API契约自动化测试
- T.1+T.4(后端): 工作区状态持久化API+数据导出导入端点
- U.1+U.3: 版本历史后端+写作模板系统后端
- V.1+V.3+V.4: 密钥加密增强+性能监控+限流CORS

**开发者 B (前端)**:
- R.2+R.3: 前端组件测试扩展+E2E场景扩展
- S.1~S.4: Bundle优化+虚拟滚动+渲染优化+资源懒加载
- T.2+T.3+T.4(前端): 状态持久化+自动保存+数据导出导入UI
- U.2+U.4: 版本历史前端+写作模板前端
- V.2: 前端错误追踪

---

## 四、模块拆分与文件归属

### 4.1 后端文件归属（开发者 A 独占）

```
backend/app/
├── agent/                          ← A 独占
│   ├── base_module.py
│   ├── modules/                    ← A 独占 (五大Agent)
│   │   ├── __init__.py
│   │   ├── knowledge_agent.py
│   │   ├── writing_agent.py
│   │   ├── output_agent.py
│   │   ├── chart_agent.py
│   │   └── storage_agent.py
│   ├── skills/
│   │   ├── nature_skills.py        ← A 独占
│   │   └── paper_banana_skills.py  ← A 独占
│   ├── core.py / context_compressor.py / message_sanitization.py
│   ├── retry_utils.py / router.py / skill_registry.py
├── models/                         ← A 独占
├── routers/                        ← A 独占（全部路由文件）
├── services/                       ← A 独占（全部服务文件）
│   ├── figure_edit_service.py      ← A 独占 (Phase 10)
│   ├── sam_segmenter.py            ← A 独占 (Phase 10)
│   ├── figure_executor.py          ← A 独占 (Phase 10)
│   ├── retriever_pubmed.py         ← A 独占 (Phase 10)
│   ├── retriever_searx_tavily.py   ← A 独占 (Phase 10)
│   ├── deep_research_service.py    ← A 独占 (Phase 10)
│   ├── paper_banana_service.py     ← A 独占 (Phase 10)
│   ├── visual_evaluator.py         ← A 独占 (Phase 10)
│   ├── stage_orchestrator.py       ← A 独占 (Phase 10)
│   ├── ai_formatter.py             ← A 独占 (Phase 10)
│   ├── plugin_system.py            ← A 独占 (Phase 10)
│   ├── slow_query_analyzer.py      ← A 独占 (Phase 10)
│   ├── workspace_state.py          ← A 独占 (Phase 11 新增)
│   ├── version_history.py          ← A 独占 (Phase 11 新增)
│   ├── writing_template_service.py ← A 独占 (Phase 11 新增)
│   ├── monitoring_service.py       ← A 独占 (Phase 11 新增)
│   └── ... (其余服务)
├── config.py / database.py / main.py  ← A 独占
├── style_guides/                   ← A 独占 (Phase 10)
│   ├── nature_plot_style.md
│   ├── nature_diagram_style.md
│   ├── elsevier_plot_style.md
│   └── ieee_plot_style.md
```

### 4.2 前端文件归属

```
frontend/src/
├── services/
│   └── api.ts                      ← A 独占（接口定义层）
├── types/                          ← A 独占（类型定义层）
│
├── components/                     ← B 独占（全部组件）
│   ├── Figure/                     ← B 独占 (Phase 10)
│   │   ├── FigureGenerationPanel.tsx
│   │   └── SvgEditorPanel.tsx
│   ├── Settings/                   ← B 独占
│   │   ├── SettingsModal.tsx
│   │   ├── PluginPanel.tsx         ← B 独占 (Phase 10)
│   │   └── ArchPanel.tsx           ← B 独占 (Phase 10)
│   ├── Writing/                    ← B 独占
│   │   ├── WritingWorkspace.tsx
│   │   ├── WritingPanel.tsx
│   │   ├── OutlineEditor.tsx
│   │   ├── WritingInterruptDialog.tsx
│   │   ├── VersionHistoryPanel.tsx ← B 独占 (Phase 11 新增)
│   │   └── TemplateGallery.tsx     ← B 独占 (Phase 11 新增)
├── contexts/                       ← B 独占
├── hooks/                          ← B 独占
│   ├── useVirtualScroll.ts         ← B 独占 (Phase 11 新增)
│   ├── useAutoSave.ts              ← B 独占 (Phase 11 新增)
│   ├── useLazyImage.ts             ← B 独占 (Phase 11 新增)
│   └── useErrorTracker.ts          ← B 独占 (Phase 11 新增)
├── store/                          ← B 独占
├── lib/                            ← B 独占
├── App.tsx                         ← B 独占
├── index.css                       ← B 独占
└── main.tsx                        ← 共享
```

### 4.3 共享文件规则

| 文件 | 归属 | 修改规则 |
|------|------|----------|
| `main.tsx` | 共享 | A 仅可改 `pdfjs.GlobalWorkerOptions` 行；B 改其他 |
| `api.ts` | A 独占 | B 需要新接口时，在日志中提交请求，A 添加后 B 使用 |
| `types/` | A 独占 | B 需要新类型时，在日志中提交请求，A 定义后 B 使用 |

---

## 五、API 契约先行规范

### 5.1 核心原则

1. A 先定义接口 → 写入 `api.ts` + 日志 → B 再开发前端
2. 接口变更必须先更新 `api.ts` → 日志通知 B → B 再适配
3. B 发现接口不满足需求 → 日志提交变更请求 → A 修改 → B 适配
4. 任何一方不得直接修改对方的文件
5. **前后端协议必须对齐**：A 定义后端端点时，必须同步更新 `api.ts` 中的请求参数/路径/返回类型
6. **禁止裸 fetch 调用**：前端组件中所有 HTTP 请求必须通过 `api.ts` 定义的接口方法
7. **禁止 e: any 类型**：catch 块中必须使用 `e: unknown` + `instanceof Error` 类型缩窄

### 5.2 前后端协议对齐检查清单

A 每次新增或修改后端端点时，必须逐项确认：

- [ ] 后端路由路径与 `api.ts` 中的 URL 路径完全一致
- [ ] 后端请求体字段与 `api.ts` 中的 `body: JSON.stringify()` 参数一致
- [ ] 后端路径参数与 `api.ts` 中的 URL 模板变量一致
- [ ] 后端返回值结构与 `api.ts` 中的 TypeScript 类型定义一致
- [ ] 后端 Pydantic 模型无冗余必填字段
- [ ] 已在 DEVLOG 中记录接口变更（IFACE-CHANGE）

### 5.3 代码质量检查清单

每轮开发完成后，双方必须检查：

- [ ] 前端组件中无裸 `fetch()` 调用
- [ ] 无 `e: any` / `err: any` / `error: any` 类型
- [ ] 无可避免的隐式 any 类型
- [ ] useCallback/useEffect 依赖数组完整且无冗余
- [ ] 闭包中引用的状态变量使用 Ref 避免过期值
- [ ] `npm run build` 零错误通过
- [ ] 新增 api.ts 接口返回值类型精确（非 `any`）

### 5.4 API 定义模板

A 在 `api.ts` 中新增接口时，必须同时满足以下格式：

```typescript
// === [模块名] API (契约版本: v1.0, DEVLOG-xxx) ===

export interface XxxResponse {
  // 返回值类型定义（禁止 any）
}

export const xxxApi = {
  actionName: (params: { field1: string; field2?: number }) =>
    request<XxxResponse>('/api/xxx/action', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};
```

### 5.5 接口变更请求模板（B → A）

B 需要新接口或接口变更时，在开发日志中提交：

```
[IFACE-REQ] 编号 | 日期 | 请求者:B
  模块: xxx
  类型: 新增 / 变更 / 删除
  描述: 需要xxx接口，因为xxx
  期望参数: { ... }
  期望返回: { ... }
  紧急度: P0/P1/P2
```

---

## 六、开发日志规范

### 6.1 日志文件位置

```
c:\Users\Administrator\.qclaw\workspace\AcaSight\DEVLOG.md
```

### 6.2 日志结构

```
DEVLOG.md
├── 活跃任务表 (按编号倒序，最新在前)
├── 阻塞任务表
├── 接口变更记录表 (IFACE-CHANGE)
├── 接口请求区 (IFACE-REQ)
└── 日志详情区 (按时间倒序排列)
```

### 6.3 日志条目格式

每条日志必须包含以下字段：

```markdown
### DEVLOG-xxx | 2026-05-31 HH:MM | A/B

- **模块**: 模块名称
- **方向**: 方向R/S/T/U/V
- **阶段**: 对应规划阶段编号
- **类型**: 开发 / 接口定义 / 接口变更 / Bug修复 / 重构 / 交叉审查
- **状态**: 🟡进行中 / ✅完成 / 🔴阻塞 / ⏸暂停
- **修改文件**:
  - [新增/修改] 文件路径 (+N行: 变更说明)
- **接口变更**:
  - 新增/变更: METHOD /api/path → 说明
  - 或: IFACE-CHANGE-xxx: 说明
- **依赖阻塞**: 无 / 阻塞原因
- **备注**: 补充说明
```

### 6.4 日志写入规则

1. 每次开始新任务前，先写一条 🟡进行中 日志
2. 每次完成任务后，立即更新为 ✅完成 日志
3. 遇到阻塞时，写 🔴阻塞 日志 + 阻塞原因 + 期望对方完成什么
4. 修改 `api.ts` 时，必须写 接口定义/接口变更 日志 + 更新接口变更记录表
5. 日志编号递增，不回收，不跳号
6. 每条日志只属于一个开发者(A或B)
7. 对方日志中有 🔴阻塞 且阻塞在自己时，优先处理并回复日志
8. **不得删除或修改对方已填写的日志内容**
9. 活跃任务表按编号倒序排列（最新在前）
10. 日志详情按时间倒序排列（最新在最上面）
11. **交叉审查时，审查方须在日志中记录发现的问题和修复内容**
12. **每条日志必须包含修改文件清单（含行数变更）**

### 6.5 接口变更记录规范

每次涉及 API 接口变更时，必须在接口变更记录表中追加一行：

| 字段 | 说明 |
|------|------|
| 编号 | IFACE-CHANGE-xxx，递增 |
| 日期 | 变更日期 |
| 操作者 | A 或 B |
| 接口 | METHOD /api/path |
| 变更类型 | 新增/参数变更/返回值变更/删除 |
| 契约版本 | v1.0 |

---

## 七、冲突预防清单

### 7.1 绝对禁止

1. A 不得修改 `frontend/src/components/` 下的任何文件（交叉审查修复除外）
2. B 不得修改 `backend/app/` 下的任何文件
3. B 不得修改 `frontend/src/services/api.ts`
4. B 不得修改 `frontend/src/types/` 下的任何文件
5. 双方不得同时修改 `main.tsx`
6. 双方不得在未写日志的情况下修改共享文件
7. A 不得在未写接口变更日志的情况下变更 API 行为
8. **双方不得删除或修改对方已填写的开发日志内容**
9. **前端组件中禁止使用裸 `fetch()` 调用**
10. **catch 块中禁止使用 `e: any`**

### 7.2 交叉审查规则

1. 每轮 Phase 完成后，双方交叉审查对方代码
2. 审查方可临时修改对方文件修复问题，但必须在日志中详细记录
3. 审查重点：裸fetch、any类型、闭包过期、协议不对齐、构建错误
4. 审查完成后，被审查方须确认修复内容
5. **交叉审查必须覆盖全部组件文件，不得遗漏**

### 7.3 需要协商

1. `main.tsx` 的非 pdfjs 配置部分
2. 新增共享依赖 (npm包 / pip包)
3. 数据库模型变更
4. 全局 CSS 变量变更
5. AppContext 新增全局状态字段
6. 测试框架选型与配置
7. **Phase 11 新增依赖**：react-window(虚拟滚动)、zustand-persist(状态持久化)、diff-match-patch(版本对比)

### 7.4 自由修改

**A 自由修改**:
- `backend/app/` 下所有文件
- `frontend/src/services/api.ts`
- `frontend/src/types/`
- `backend/tests/` 下测试文件
- `backend/style_guides/` 下风格指南文件

**B 自由修改**:
- `frontend/src/components/` 下所有文件
- `frontend/src/contexts/`
- `frontend/src/hooks/`
- `frontend/src/store/`
- `frontend/src/lib/`
- `frontend/src/index.css`
- `frontend/src/App.tsx`
- `frontend/src/__tests__/` 下测试文件
- `frontend/e2e/` 下测试文件

---

## 八、验收与集成流程

```
Step 1: A 完成后端模块 → 写 ✅完成 日志 + 接口变更记录
Step 2: B 看到日志 → 将 mock 替换为真实接口调用
Step 3: B 本地测试 → 通过 → 写 ✅完成 日志
Step 4: B 本地测试 → 失败 → 写 🔴阻塞 日志 + 错误信息
Step 5: A 看到 🔴阻塞 → 修复 → 写 ✅完成 日志 + 接口变更记录
Step 6: 回到 Step 2，直到全部通过
Step 7: 双方 Phase 全部 ✅ → 交叉审查 → npm run build → 集成验收
```

### 8.1 集成验收检查项

- [ ] `npm run build` 通过，无 TypeScript 错误
- [ ] 后端启动无报错，所有端点可访问
- [ ] 前端所有页面可正常加载，无白屏
- [ ] SSE 流式接口可正常推送数据
- [ ] 中断→确认→恢复流程端到端走通
- [ ] 格式导出 (DOCX/LaTeX/PDF/HTML) 可正常下载
- [ ] `api.ts` 中所有接口与后端实际行为一致
- [ ] 前端组件中无裸 `fetch()` 调用
- [ ] 无 `e: any` 类型残留
- [ ] 后端 API 测试覆盖率 > 50%
- [ ] PaperBanana插图Pipeline端到端可用
- [ ] SVG编辑器可正常打开/编辑/导出矢量图
- [ ] 新增检索器(PubMed/SearX)返回有效结果
- [ ] **前端单元测试覆盖核心组件(SearchPage/WritingWorkspace/GraphView/AgentPanel)**
- [ ] **E2E测试覆盖关键路径(搜索→阅读→写作→导出→插图→Deep Research)**
- [ ] **Bundle首屏JS<500KB(gzip)、交互响应<100ms**
- [ ] **工作区状态刷新后可恢复、自动保存间隔≤30s**
- [ ] **版本历史可查看Diff、可一键恢复**
- [ ] **写作模板可浏览、应用、自定义**

---

## 九、紧急情况处理

| 情况 | 处理方式 |
|------|----------|
| A 的接口返回格式与 B 的 mock 不一致 | A 写接口变更日志，B 适配 |
| B 发现需要新接口但 A 还没开发 | B 写 IFACE-REQ 日志，A 评估优先级 |
| 双方都需要修改 main.tsx | 协商时间差，A 先改 pdfjs 行，B 再改其他 |
| 数据库模型需要变更 | A 发起，写日志通知 B，B 更新前端类型 |
| 构建失败 | 最后修改者负责修复，写 Bug修复 日志 |
| B 越权修改了 api.ts | B 在日志中记录越权行为，A 审核后决定是否回退 |
| 前后端协议不对齐 | A 优先修复后端，写 IFACE-CHANGE 日志，B 适配 |
| 交叉审查发现类型安全问题 | 审查方直接修复并在日志中记录 |
| SAM3/RMBG2安装失败 | Docker镜像方案，可选安装 |
| PaperBanana Gemini依赖 | 增加OpenAI/OpenRouter provider路由 |
| 外部依赖版本冲突 | 隔离为可选依赖，降级不影响核心功能 |
| zustand-persist与现有store冲突 | 渐进式迁移，先持久化非关键状态 |
| react-window与现有列表样式冲突 | CSS变量适配+降级为普通列表 |
| 版本历史diff存储空间过大 | 增量diff+定期压缩+上限策略 |

---

## 十、v6.0 → v7.0 变更记录

| 变更项 | v6.0 | v7.0 | 原因 |
|--------|------|------|------|
| 项目阶段 | Phase 10 能力跃升 | Phase 11 质量深化与智能进化 | Phase 10 全部完成(插图Pipeline+SVG编辑+Deep Research+架构优化+插件系统) |
| 开发方向 | M~Q(插图/SVG/检索/架构/收尾) | R~V(测试/性能/持久化/写作升级/安全监控) | 功能趋完整，转向质量+体验+安全 |
| 已完成模块 | 45项 | 50项(+PaperBanana Pipeline+SVG编辑+Deep Research+架构优化+插件系统) | Phase 10 完成 |
| 新增后端文件 | figure_edit_service等7个 | workspace_state/version_history/writing_template_service/monitoring_service | Phase 11 新增 |
| 新增前端组件 | FigureGenerationPanel等3个 | VersionHistoryPanel/TemplateGallery + 4个hooks | Phase 11 新增 |
| 紧急处理 | 11项 | 14项(+zustand-persist冲突/react-window样式/diff存储空间) | 新增Phase 11风险 |
| 验收标准 | 插图Pipeline+SVG+检索器 | +测试覆盖+Bundle性能+状态持久化+版本历史+模板系统 | Phase 11 质量门槛 |
| 代码质量指标 | 7项 | 12项(+组件文件数+i18n键+路由数+服务数+单元测试+E2E测试) | 可度量性增强 |
| B自由修改范围 | __tests__/ | +e2e/ | E2E测试归属B方 |

---

> **文档版本**: v7.0
> **核心原则**: 文件归属清晰、接口契约先行、日志实时同步、前后端协议对齐、裸fetch零容忍、e:any零容忍、代码质量可度量、测试覆盖可验证、性能指标可量化、状态持久可恢复
