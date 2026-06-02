# 外部项目集成评估报告

> 日期: 2026-05-31 | 评估者: A方 | 针对AcaSight学术智能体应用

## 1. 项目概览

| 项目 | 定位 | 技术栈 | 核心文件 | 代码量 |
|------|------|--------|---------|--------|
| **agentic-data-scientist** | 数据科学多Agent编排 | Google ADK + Gemini | agent.py, stage_orchestrator.py | ~3,700行 |
| **agentscope** | 通用Agent框架 | Python (多LLM适配器) | _agent.py, _toolkit.py, 多formatter | ~15,000行 |
| **AutoFigure-Edit** | 论文方法图→SVG编辑替换 | Python + SVG-Edit + SAM3 + RMBG2 | autofigure2.py, server.py | ~5,100行 |
| **ggplotAgent** | 数据可视化Agent | LangGraph + 豆包VL + Streamlit | agent_logic.py | ~900行 |
| **gpt-researcher** | 自动研究+报告生成 | Python (多retriever) | agent.py, researcher.py | ~8,000行 |
| **PaperBanana** | 论文插图生成 | Google Gemini + matplotlib | 7个Agent + generation_utils | ~3,500行 |

---

## 2. 逐项评估

### 2.1 🟢 PaperBanana — ★★★★ (高价值，可融合)

**定位**：论文插图自动生成（plot + diagram）

**核心架构**：6-Agent Pipeline
```
RetrieverAgent → PlannerAgent → VisualizerAgent → CriticAgent → PolishAgent → StylistAgent
```

**关键能力**：
- 📊 **Plot生成**：LLM生成matplotlib代码 → ProcessPoolExecutor沙箱执行 → 300dpi JPEG
- 🎨 **Diagram生成**：LLM直接生成图像（Gemini/GPT-Image/OpenRouter多provider）
- 🔄 **Critic循环**：最多3轮critic-refinement，自动判断"No changes needed"时停止
- 📐 **风格指南**：NeurIPS 2025 plot/diagram style guide（论文级标准）
- 🔍 **参考检索**：基于PaperBananaBench的top-10检索，少样本学习生成

**与AcaSight映射**：
| PaperBanana组件 | AcaSight对应 | 融合方式 |
|----------------|-------------|---------|
| VisualizerAgent | ChartAgent + `generate_figure` skill | **替换**chart_agent.py的绘图逻辑 |
| PlannerAgent | `generate_figure` skill | **增强**，加参考图检索+描述生成 |
| CriticAgent | 无 | **新增**，图表质量评估循环 |
| PolishAgent | 无 | **新增**，细节润色 |
| StylistAgent | 无 | **新增**，风格对齐（SCI期刊风格） |
| style_guides/ | 无 | **新增**，SCI级风格模板 |
| generation_utils.py | ai_service.py | **参考**，多provider图像生成路由 |

**融合方案**：
1. **后端新增**：`backend/app/agent/skills/paper_banana_skills.py`
   - `generate_plot` skill：替换当前generate_figure（仅描述→直接生成代码+执行）
   - `critique_figure` skill：新增critic评估循环
   - `polish_figure` skill：新增润色
2. **后端修改**：`chart_agent.py` 引入PaperBanana的6-Agent pipeline
3. **风格指南**：复制NeurIPS style guide，扩展为SCI/Nature/Esevier等期刊模板
4. **工具沙箱**：参考`_execute_plot_code_worker`的ProcessPoolExecutor隔离执行

**工作量**：3-5天

---

### 2.2 🟢 AutoFigure-Edit — ★★★★ (高价值，可融合)

**定位**：论文方法图(method figure)的AI重绘+SVG编辑替换

**核心流程**：
```
Method文本 → 图像生成 → SAM3分割 → RMBG2去背景 → LLM生成SVG → 图标替换 → final.svg
```

**关键能力**：
- 🖼️ **SVG生成**：多模态LLM生成矢量图模板（可编辑、可缩放、期刊投稿级）
- ✂️ **SAM3分割**：自动检测图中icon/箭头/框图区域，带多prompt+box合并
- 🎯 **占位符模式**：label模式（灰色+序号标签）精确匹配替换
- 🔧 **SVG优化**：lxml验证 + LLM修复 + 坐标系对齐 + 多轮优化
- 🌐 **Web编辑器**：内置SVG-Edit在线编辑器（canvas.html）

**与AcaSight映射**：
| AutoFigure组件 | AcaSight对应 | 融合方式 |
|---------------|-------------|---------|
| SVG生成pipeline | 无 | **新增**，论文方法图重绘能力 |
| SAM3分割 | 无 | **新增**，图表元素检测 |
| SVG-Edit Web UI | 无 | **新增**，矢量图在线编辑 |
| server.py (Gradio) | FastAPI | **适配**，改写为FastAPI端点 |

**融合方案**：
1. **后端新增**：`backend/app/services/figure_edit_service.py`
   - 封装autofigure2.py核心逻辑为service
   - 新增API端点：`/api/figure/edit-svg`, `/api/figure/sam-segment`, `/api/figure/replace-icons`
2. **前端新增**：SVG-Edit集成到EditorView的图表标签页
3. **Agent技能**：新增`edit_figure_svg` skill → 调用figure_edit_service
4. **依赖**：需安装segment-anything、rembg、lxml

**工作量**：5-7天

---

### 2.3 🟡 gpt-researcher — ★★★ (中高价值，选择性融合)

**定位**：自动研究+报告生成（网页搜索→内容抓取→报告撰写）

**核心能力**：
- 🔍 **多源检索**：13个retriever（Bing/Google/Tavily/SearX/OpenAlex/PubMed等）
- 📝 **报告生成**：ResearchReport/ResourceReport/CustomReport等多种类型
- 🧠 **Deep Research**：多轮子问题分解+并行搜索+质量评估
- 🤖 **Multi-Agent**：Chief/Researcher/Reviewer/Revisor/Human角色协作
- 📚 **向量记忆**：Mem0集成，跨会话长期记忆
- 🔧 **MCP集成**：支持MCP工具调用
- 🎨 **图片生成**：内置image_generator skill

**与AcaSight映射**：
| gpt-researcher组件 | AcaSight对应 | 融合方式 |
|-------------------|-------------|---------|
| OpenAlex retriever | search_service (已有OpenAlex) | **参考**，补充更多检索源 |
| PubMed retriever | 无 | **新增**，医学文献检索 |
| Deep Research skill | search_literature skill | **增强**，多轮子问题分解 |
| context/compression.py | context_compressor.py | **参考**，已有类似实现 |
| Multi-Agent协作 | 无 | **参考设计**，不直接引入（太重） |
| vector_store/ | ChromaDB (已有) | 不需要 |
| prompts.py | nature_skills.py (已有) | 不需要 |

**融合方案**：
1. **新增检索器**：从gpt-researcher移植PubMed Central、SearX、Tavily retriever到search_service
2. **Deep Research增强**：将`deep_research.py`的子问题分解逻辑整合到`search_literature` skill
3. **不引入**：multi_agents框架（太重，与AcaSight自写Agent冲突）、vector_store（已有ChromaDB）

**工作量**：2-3天

---

### 2.4 🟡 ggplotAgent — ★★★ (中等价值，参考设计)

**定位**：数据可视化Agent（LangGraph + 多LLM）

**核心架构**：LangGraph StateGraph
```
数据分析 → 图表类型选择 → ggplot代码生成 → 执行 → 视觉评估 → 修正循环
```

**关键能力**：
- 📊 **ggplot代码生成**：基于LangGraph的多步编排
- 👁️ **视觉评估**：豆包VL模型评估图表质量
- 🔄 **修正循环**：评估不合格时自动修正代码

**与AcaSight映射**：
| ggplotAgent组件 | AcaSight对应 | 融合方式 |
|----------------|-------------|---------|
| LangGraph StateGraph | workflow_engine.py | **参考设计**，不引入LangGraph |
| 视觉评估循环 | 无 | **参考思路**，用VL模型评估图表质量 |
| ggplot代码生成 | ChartAgent (matplotlib) | **不融合**，AcaSight用matplotlib非ggplot |

**融合方案**：
1. **设计参考**：将"生成→视觉评估→修正"循环思路应用到ChartAgent
2. **不直接引入**：ggplotAgent依赖LangGraph+豆包VL，与AcaSight技术栈冲突
3. **可选增强**：如果未来AcaSight需要R语言ggplot2支持，可作为参考

**工作量**：1天（设计参考）

---

### 2.5 🟠 agentic-data-scientist — ★★ (低价值，设计参考)

**定位**：数据科学多Agent编排（Google ADK框架）

**核心架构**：Google ADK (Agent Development Kit)
```
Plan生成 → StageOrchestrator → ImplementationLoop → ReviewConfirmation → LoopDetection
```

**问题**：
- 🔴 **强依赖Google ADK**：基于`google.adk.agents`、`google.genai`，与AcaSight无关
- 🔴 **仅支持Gemini**：LLM调用全部走Google Gemini API
- 🔴 **通用数据科学**：非学术场景定制

**可借鉴**：
- ✅ **StageOrchestrator**：阶段式编排+成功标准检查 → 可参考优化workflow_engine.py
- ✅ **LoopDetection**：Agent循环检测（防死循环） → 可加入AgentCore
- ✅ **ReviewConfirmation**：人工审核确认节点 → 可加入写作工作流

**融合方案**：仅参考设计理念，不引入代码

**工作量**：0.5天（设计参考）

---

### 2.6 🟠 agentscope — ★★ (低价值，框架不兼容)

**定位**：通用Agent开发框架（阿里达摩院）

**核心能力**：
- 🤖 完整Agent框架（Agent基类、消息、事件、中间件）
- 🔧 10+ LLM格式化器（OpenAI/Anthropic/Gemini/DeepSeek/Ollama等）
- 🛠️ 内置工具集（Bash/Edit/Read/Write/Glob/Grep/Skill）
- 🐳 Docker/E2B工作空间管理
- 🔐 权限引擎
- 📊 Web UI + AGUI协议
- 🔗 MCP客户端

**问题**：
- 🔴 **完整框架**：与AcaSight自写Agent架构冲突，引入成本极高
- 🔴 **依赖链重**：Redis/Gradio/Docker等

**可借鉴**：
- ✅ **Formatter层**：10+ LLM provider的message格式化 → 可参考增强ai_service.py
- ✅ **Permission Engine**：工具执行权限控制 → K.4插件系统可参考
- ✅ **AGUI协议**：Agent-UI通信协议 → 前端交互设计参考
- ✅ **Tool Toolkit**：工具注册/分组/适配器模式 → 可参考skill_registry.py增强

**融合方案**：仅参考设计，提取formatter逻辑

**工作量**：1天（设计参考+formatter参考）

---

## 3. 融合优先级总表

| 优先级 | 项目 | 融合方式 | 预估工时 | 收益 |
|--------|------|---------|---------|------|
| **P1** | PaperBanana | 代码融入（6-Agent pipeline + plot代码生成 + critic循环） | 3-5天 | 🔥🔥🔥 论文插图质变 |
| **P1** | AutoFigure-Edit | 代码融入（SVG生成+编辑+SAM3分割） | 5-7天 | 🔥🔥🔥 方法图重绘能力 |
| **P2** | gpt-researcher | 选择性移植（PubMed retriever + Deep Research） | 2-3天 | 🔥🔥 检索增强 |
| **P3** | ggplotAgent | 设计参考（视觉评估循环思路） | 1天 | 🔥 ChartAgent增强 |
| **P3** | agentic-data-scientist | 设计参考（Stage编排+循环检测） | 0.5天 | 🔥 workflow优化 |
| **P3** | agentscope | 设计参考（Formatter+Permission+Toolkit） | 1天 | 🔥 架构优化 |

---

## 4. 推荐路线

### 第一阶段（P1，8-12天）：图表能力跃升
1. **融合PaperBanana** → 替换现有ChartAgent的绘图逻辑
2. **融合AutoFigure-Edit** → 新增SVG矢量图编辑能力
3. 效果：AcaSight从"简单绘图"→"论文级插图生成+编辑+质量评估"

### 第二阶段（P2，2-3天）：检索增强
4. 移植gpt-researcher的PubMed/SearX/Tavily检索器
5. 整合Deep Research子问题分解逻辑

### 第三阶段（P3，2.5天）：架构优化
6. 参考agentic-data-scientist的Stage编排优化workflow_engine
7. 参考ggplotAgent加入图表视觉评估循环
8. 参考agentscope的Formatter/Permission增强底层架构

---

## 5. 技术风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| PaperBanana依赖Gemini API | 只能用Gemini生成图 | 增加OpenAI/OpenRouter provider路由 |
| AutoFigure-Edit依赖SAM3+RMBG2 | 需要额外安装GPU依赖 | Docker镜像/可选安装 |
| gpt-researcher代码量巨大 | 难以完整移植 | 只移植retriever子模块 |
| 多项目代码风格不一 | 维护成本 | 统一适配AcaSight代码规范 |
