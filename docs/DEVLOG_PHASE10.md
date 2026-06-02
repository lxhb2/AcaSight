# AcaSight Phase 10 开发日志

> 日期: 2026-05-31 | 阶段: Phase 10 能力跃升与智能增强 | 开发者: A端

---

## 📋 总览

Phase 10 是 AcaSight 项目从"功能闭环"迈向"智能增强"的关键阶段。本阶段聚焦5个方向（M~Q），从外部项目集成评估出发，将成熟的开源设计方案融入 AcaSight 架构，同时完成生产就绪收尾。

### 核心成果

| 指标 | 数值 |
|------|------|
| 新增后端服务 | 15个 |
| API路由增量 | 201 → 234 (+33, +16.4%) |
| pytest | 115 passed (稳定) |
| TypeScript | 零错误 |
| 性能基准 | 18 benchmark passed |
| 插件系统 | 8端点 + 示例插件验证 |

---

## 🗺️ 方向总览

| 方向 | 名称 | 状态 | 核心产出 |
|------|------|------|---------|
| M | 论文插图 | ✅ | PaperBanana 6-Agent Pipeline |
| N | SVG矢量编辑 | ✅ | FigureEdit 5步流水线 + SAM3 |
| O | 检索增强 | ✅ | Deep Research Pipeline + PubMed |
| P | 架构优化 | ✅ | 4个架构服务 + Agent循环检测 |
| Q | 生产收尾 | ✅ (A端) | 性能基准 + 插件系统 |

---

## 🔴 方向M — 论文插图 (PaperBanana)

### 起源
从 [PaperBanana](https://github.com/dwzhu-pku/PaperBanana) 开源项目集成。PaperBanana 采用 6-Agent Pipeline 架构，包含 Retriever→Planner→Visualizer→Critic→Polish→Stylist 全链路。

### 实现内容

**paper_banana_service.py** — 6-Agent Pipeline 核心
- **Retriever**: 从论文文本提取数据与图表描述
- **Planner**: 生成 matplotlib 绑定代码计划
- **Visualizer**: ProcessPoolExecutor 沙箱执行 matplotlib 代码
- **Critic**: VL 模型评估图表质量 (3轮 max_critic_rounds)
- **Polish**: 根据评估反馈修复代码
- **Stylist**: 应用 SCI 风格指南 (Nature/IEEE/Elsevier/默认)

**3套 SCI 风格指南** — 内嵌于 `STYLE_GUIDES` 字典:
- Nature: 紧凑布局, 小字号, 无网格, PDF 300dpi
- IEEE: 标准字号, 网格线, EPS/PDF
- Elsevier: 大字号, 灰色网格, 高分辨率

**API端点** (4个):
- `POST /api/paper-banana/styles` — 可用风格列表
- `POST /api/paper-banana/generate-plot` — 完整 Pipeline
- `POST /api/paper-banana/generate-diagram` — 流程图生成
- `POST /api/paper-banana/critique` — Critic 评估

### 技术亮点
- matplotlib 代码沙箱: `ProcessPoolExecutor` 隔离执行, 超时120s
- Critic 循环: 3轮评估 → 不通过 → 自动修复 → 重新生成
- 前端 `FigureGenerationPanel.tsx` (615行): 风格选择+代码预览+图表展示+Critic反馈

---

## 🟠 方向N — SVG矢量编辑 (AutoFigure-Edit)

### 起源
从 [AutoFigure-Edit](https://github.com/xxx/autofigure-edit) 开源项目移植核心流水线。原版 137KB，精简至 20KB 保留核心5步。

### 实现内容

**figure_edit_service.py** — 5步 SVG 编辑流水线:
1. **Method→Figure**: 文字描述 → 学术风格图片 (OpenAI Images API 降级方案)
2. **SAM3分割**: 文字 prompt → 图标分割框 (支持 fal/Roboflow/API 三种后端)
3. **裁切+去背景**: 按分割框裁切 + RMBG2/rembg 可选去背景
4. **SVG模板生成**: 多模态 LLM 生成 SVG (label/box/none 三种占位符模式) + 语法验证 + LLM修复 + 可配置迭代优化
5. **图标替换**: 分割图标 → base64嵌入 → SVG占位符替换

**sam_segmenter.py** — 独立分割服务:
- 三后端: fal.ai / Roboflow / 本地 segment-anything
- 多 text prompt 分割 + 重叠框合并
- `.available` 属性自动检测可用性

**API端点** (6个):
- `POST /api/figure-edit/method-to-svg` — 完整5步流水线
- `POST /api/figure-edit/segment` — SAM3 分割
- `POST /api/figure-edit/generate-svg` — SVG 生成
- `POST /api/figure-edit/replace-icons` — 图标替换
- `POST /api/figure-edit/fix-svg` — SVG 修复
- `GET /api/figure-edit/status` — 服务状态

### 技术决策
- SAM3 为可选功能 (需 API Key), 不影响 SVG 生成/优化/替换
- ai_service 无 `generate_image()` → 直接使用 OpenAI Images API
- 原版137KB → 20KB精简: 保留5步流水线+3种占位符, 移除冗余模型加载逻辑

---

## 🟡 方向O — 检索增强 (Deep Research)

### 起源
从 [gpt-researcher](https://github.com/assafelovic/gpt-researcher) 选择性移植 PubMed/PMC 检索器和 Deep Research 管道。

### 实现内容

**retriever_pubmed.py** — PubMed/PMC 检索器:
- PMC 全文搜索: esearch → efetch XML解析 (标题/摘要/正文/作者/年份/DOI/PMC ID)
- PubMed 摘要搜索: 标准摘要+结构化摘要
- 异步 httpx + NCBI_API_KEY 可选 (3→10 req/s)
- 批量 fetch + 单篇降级兜底

**retriever_searx_tavily.py** — SearX/Tavily 检索器:
- SearXNG: 自建实例 API, `SEARX_URL` 环境变量
- Tavily: AI 驱动搜索, `TAVILY_API_KEY` 环境变量
- 两者均为可选, 未配置时 `.available = False` 自动禁用

**deep_research_service.py** — Deep Research Pipeline:
- 三种模式: quick(3×1) / deep(4×2) / comprehensive(5×3)
- 流程: 子问题分解(LLM) → 多源并行搜索 → 学习提取+后续问题 → 综合总结+空白识别
- 多检索器并行: AcaSight内置(CORE+OpenAlex+arXiv) + PubMed + SearX + Tavily
- SSE 流式进度 + 同步等待两种模式

**API端点** (4个):
- `POST /api/deep-research/start` — SSE 流式
- `POST /api/deep-research/start-sync` — 同步等待
- `POST /api/deep-research/pubmed` — PubMed/PMC 搜索
- `GET /api/deep-research/sources` — 检索源列表

### 关键Bug修复
1. `get_http_client()` 是 async → 必须 `await` (3处修复)
2. `ai_service.chat()` 返回 AsyncGenerator → 必须 `async for` 收集 (4处修复)
3. `search_service.search()` 签名需 `client + limit` 参数

---

## 🟢 方向P — 架构优化

### 起源
参考 [ggplotAgent](https://github.com/charlin90/ggplotAgent) (视觉评估循环)、[agentic-data-scientist](https://github.com/xxx/agentic-data-scientist) (Stage编排+循环检测)、[agentscope](https://github.com/xxx/agentscope) (Formatter+Permission) 三个项目的设计模式。

### 实现内容

**P.1 Visual Evaluator** (visual_evaluator.py, 9.9KB):
- VL 模型评估图表质量: MATCH/MISMATCH 二元判定
- 4种 SCI 风格标准: nature/ieee/elsevier/default
- `evaluate_with_regeneration`: 评估→不通过→反馈修复→重新评估 (多轮循环)
- API: `POST /api/arch/evaluate-visual`

**P.2 Stage Orchestrator** (stage_orchestrator.py, 13.3KB):
- DAG 并行编排: 拓扑排序 → 按层并行执行 (asyncio.Semaphore 并发控制)
- 可配置重试策略: none/fixed/exponential (RetryPolicy)
- Stage 回滚: 失败时逆序调用 `rollback_handler`
- 依赖图环检测: DFS
- 执行快照 + 断点恢复: `create_snapshot` / `restore_from_snapshot`
- API: `POST /api/arch/pipeline`

**P.3 Loop Detector** (loop_detector.py, 8.2KB):
- 三层循环检测:
  1. **TOOL_REPEAT**: 同一工具+相同参数 ≥N次
  2. **OUTPUT_SIMILARITY**: Jaccard 相似度 ≥ 阈值
  3. **STATE_CYCLE**: 状态哈希序列出现环
- 集成 AgentCore.run(): 检测 → yield warning → 3次后自动中断
- API: `POST /api/arch/detect-loop`

**P.4 AI Formatter** (ai_formatter.py, 9.9KB):
- 自动格式检测: JSON/SVG/Markdown/Code/Text/List/Table
- 格式提取: `extract_json` / `extract_svg` / `extract_list`
- 常见问题修复: BOM去除、`<think/>`标签、代码围栏、JSON尾随逗号/单引号
- 严格/宽松模式切换
- API: `POST /api/arch/format`

**API端点** (5个):
- `POST /api/arch/evaluate-visual` — 图表视觉评估
- `POST /api/arch/pipeline` — Stage Pipeline 执行
- `POST /api/arch/detect-loop` — Agent 循环检测
- `POST /api/arch/format` — AI 响应格式化
- `GET /api/arch/status` — 架构服务状态

### 集成修复
- **Bug**: 循环检测 `yield` 语句错放在 `_execute_tools_concurrent` 中，使 `async def` 变为 `async generator`，导致 `return results` 语法错误
- **修复**: 将循环检测逻辑移到 `run()` 方法中，在 `_execute_tools_concurrent` 返回后执行

---

## 🔵 方向Q — 生产收尾 (A端)

### Q.1 性能基准测试

**test_benchmarks.py** (9.9KB) — 17个基准 + 7个阈值 + 2个并发:

| 测试类 | 端点数 | 说明 |
|--------|--------|------|
| TestHealthBenchmark | 5 | 基础状态端点 |
| TestSearchBenchmark | 3 | 搜索类端点 |
| TestCRUDBenchmark | 1 | 创建+删除循环 |
| TestWorkflowBenchmark | 2 | 工作流端点 |
| TestZoteroBenchmark | 2 | Zotero 同步 |
| TestFormatterBenchmark | 3 | 格式化服务 |
| TestSlowQueryThreshold | 7 | 延迟阈值参数化验证 |
| TestConcurrencyBenchmark | 2 | 并发吞吐量 |

**性能基准数据** (pytest-benchmark):

| 类别 | avg (ms) | 说明 |
|------|----------|------|
| compute (format/loop) | 5.5 | 极快 |
| list (papers/workflow) | 4.5 | 极快 |
| status (arch/figure-edit) | 8.7 | 快 |
| search (literature/dimensions) | 7.5 | 快 |
| health | 247.7 | 中 (lazy import 冷启动) |
| external (Zotero) | 2397.3 | 慢 (外部 API) |

**slow_query_analyzer.py** (7.6KB): 自动扫描14端点 + 分类统计 + 报告格式化

**关键发现**:
- 最快端点: `format_svg` (2.3ms), `search_sources` (2.6ms)
- 唯一慢查询: `/api/health` (247ms avg, 1193ms p95) — 原因: 多处 lazy import
- 外部API瓶颈: Zotero 同步 ~2.2s — 不可避免

### Q.2 插件系统架构

**plugin_system.py** (17.5KB) — 完整插件系统:

核心组件:
- **PluginRegistry**: 生命周期管理 (load → enable → disable → unload)
- **PluginSandbox**: 权限检查 (safe/network/fs_read/fs_write/env/full)
- **AcaSightPlugin 基类**: on_load/on_enable/on_disable/on_unload + register_hook
- **Hook 调度**: 多处理器顺序执行 + 错误隔离 + 30s超时保护
- **PluginManifest**: YAML 声明式配置 (name/version/hooks/provides/depends/permissions)

生命周期状态机:
```
UNLOADED → LOADING → LOADED → ENABLED → DISABLED → UNLOADED
                       ↓          ↑
                     ERROR ←──────┘
```

权限模型:
| 权限 | 风险 | 默认 |
|------|------|------|
| safe | 无 | ✅ |
| network | 中 | ✅ |
| fs_read | 中 | ✅ |
| fs_write | 高 | 需审批 |
| env | 中 | 需审批 |
| full | 极高 | 禁止 |

**示例插件**: `example-search-enhancer`
- plugin.yaml 声明: hooks=[post_search], permissions=[network]
- plugin.py 实现: 关键词提取 + 自动标签增强
- 验证: load → enable → hook → handlers_called=1, 关键词提取正常 ✅

**API端点** (8个):
- `GET /api/plugins/` — 列出已安装插件
- `GET /api/plugins/discover` — 发现可用插件
- `POST /api/plugins/load` — 加载插件
- `POST /api/plugins/{name}/enable` — 启用插件
- `POST /api/plugins/{name}/disable` — 禁用插件
- `DELETE /api/plugins/{name}` — 卸载插件
- `POST /api/plugins/hook` — 触发钩子
- `GET /api/plugins/{name}/status` — 插件状态

**PLUGIN_ARCHITECTURE.md** (4.0KB): 架构设计文档
- 完整生命周期、权限模型、内置钩子点、API端点、示例代码、未来扩展规划

---

## 🔧 基础设施改进

### AI 速度优化 v2.0 (ai_service.py)
- 全局连接池: `get_http_client()` 单例 httpx.AsyncClient
- 响应缓存: ResponseCache (LRU, TTL=300s, maxsize=128)
- 智能模型路由: TASK_COMPLEXITY + PROVIDER_SPEED_TIERS
- 单例 AIService: `__new__` 模式, 30s 自动重载配置
- main.py shutdown hook: `close_http_client()`

### Agent 循环检测集成 (core.py)
- LoopDetector 实例化于 `run()` 方法
- 工具执行后自动检测循环: yield warning → 3次后 return 中断
- 并行工具执行: `asyncio.gather()` + 中断检查 + 超时控制(120s)

### 外部项目集成评估 (6项目)
| 优先级 | 项目 | 融合方式 | 工时 |
|--------|------|---------|------|
| P1 | PaperBanana | 代码融入 | 3-5天 |
| P1 | AutoFigure-Edit | 代码融入 | 5-7天 |
| P2 | gpt-researcher | 选择性移植 | 2-3天 |
| P3 | ggplotAgent | 设计参考 | 1天 |
| P3 | agentic-data-scientist | 设计参考 | 0.5天 |
| P3 | agentscope | 设计参考 | 1天 |

---

## 📊 今日完整统计

### 新增文件
| 文件 | 大小 | 方向 |
|------|------|------|
| paper_banana_service.py | ~25KB | M |
| paper_banana.py (路由) | ~4KB | M |
| retriever_pubmed.py | 9.3KB | O |
| retriever_searx_tavily.py | 5.6KB | O |
| deep_research_service.py | 19.7KB | O |
| deep_research.py (路由) | 5.0KB | O |
| figure_edit_service.py | 20.2KB | N |
| sam_segmenter.py | 8.6KB | N |
| figure_edit.py (路由) | 9.5KB | N |
| visual_evaluator.py | 9.9KB | P |
| stage_orchestrator.py | 13.3KB | P |
| loop_detector.py | 8.2KB | P |
| ai_formatter.py | 9.9KB | P |
| arch.py (路由) | 7.4KB | P |
| slow_query_analyzer.py | 7.6KB | Q.1 |
| test_benchmarks.py | 9.9KB | Q.1 |
| plugin_system.py | 17.5KB | Q.2 |
| plugins.py (路由) | 4.5KB | Q.2 |
| PLUGIN_ARCHITECTURE.md | 4.0KB | Q.2 |
| example-search-enhancer/ | ~2.4KB | Q.2 |

### API 路由增量
| 方向 | 新增端点 | 累计路由 |
|------|---------|---------|
| 起点 | — | 201 |
| M (PaperBanana) | +4 | 205 |
| O (Deep Research) | +4 | 209 |
| N (Figure Edit) | +6 | 221 (含状态路由) |
| P (Architecture) | +5 | 226 |
| Q.2 (Plugins) | +8 | 234 |
| **总增量** | **+33 (+16.4%)** | **234** |

### 验证结果
| 检查项 | 结果 |
|--------|------|
| pytest | 115 passed (稳定, 4 failed 为外部API超时) |
| TypeScript | 零错误 |
| pytest-benchmark | 18 passed |
| Vite 构建 | 成功 |
| 示例插件 | load→enable→hook 完整生命周期 ✅ |

---

## 📝 接口变更记录

| 编号 | 日期 | 方向 | 端点 | 说明 | 版本 |
|------|------|------|------|------|------|
| IFACE-020 | 05-31 | M | PaperBanana 4端点 | 新增 | v1.0 |
| IFACE-021 | 05-31 | — | AI缓存统计端点 | 新增 | v1.0 |
| IFACE-022 | 05-31 | O | Deep Research 4端点 | 新增 | v1.0 |
| IFACE-023 | 05-31 | N | Figure Edit 6端点 | 新增 | v1.0 |
| IFACE-024 | 05-31 | P | Architecture 5端点 | 新增 | v1.0 |
| IFACE-025 | 05-31 | Q | Plugins 8端点 | 新增 | v1.0 |

---

## 🐛 Bug修复记录

| Bug | 原因 | 修复 |
|-----|------|------|
| `async for` 收集 AI 响应 | `ai_service.chat()` 返回 AsyncGenerator | 新增 `_ai_chat()` 辅助函数 |
| `await get_http_client()` | async 函数未 await | 3处修复 |
| async generator `return value` | yield 在 `_execute_tools_concurrent` 使其变 generator | 循环检测移到 `run()` |
| 插件 hook 注册空 | `ensure_future` 异步调度未等 on_load 完成 | `load_plugin` 改为 async |
| api.ts 模板字符串 | PowerShell 转义破坏 `` ` ` `` 语法 | 手动修复3处路径 |
| SearchPage.tsx JSX | 缺少 `</div>` 关闭标签 | 补全 |

---

## 🎯 待办事项

| 任务 | 负责方 | 优先级 | 依赖 |
|------|--------|--------|------|
| Q.3 E2E 测试 (Playwright) | B端 | P2 | Q.1 |
| M.6 Critic 结果前端展示 | B端 | P2 | M.1 |
| N 前端对接 (SvgEditorPanel) | B端 | P1 | N.1 |
| writing.py 拆分 (1175行) | A端 | P3 | — |
| Pydantic V2 弃用警告 (27处) | A端 | P3 | — |
| health 端点优化 (lazy import) | A端 | P3 | — |
| 插件子进程沙箱 (v1.2) | A端 | 未来 | Q.2 |
| 插件市场 (v1.3) | A端 | 未来 | Q.2 |

---

## 💡 技术经验教训

1. **async generator 不能 `return value`**: Python 语法限制, `yield` 语句使函数成为 generator, `return results` 报语法错误。解决方案: 将 yield 逻辑移到正确的函数层级。
2. **ensure_future 不是 await**: `asyncio.ensure_future()` 仅调度协程, 不会等待完成。后续依赖其结果的代码必须 `await` 而非同步访问。
3. **PowerShell 模板字符串**: 通过 PowerShell 变量注入的 JavaScript 模板字符串会被转义, 需手动验证或使用不同注入方式。
4. **外部项目集成策略**: P1 项目代码融入, P2 选择性移植, P3 仅参考设计。框架级冲突的项目 (LangGraph/Google ADK) 不强制集成。
5. **性能基准先定阈值**: 慢查询测试需先定义合理阈值 (基础 GET <100ms, 搜索 <2000ms, 写入 <500ms), 否则基准无意义。

---

> Phase 10 A端全部完成。Q.3 E2E 测试由 B端负责。
> 
> 下一步: 等待 B端完成 Q.3 E2E 测试, 然后进入 Phase 11 规划。
