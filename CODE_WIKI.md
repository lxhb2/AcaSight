# AcaSight Code Wiki

> **AcaSight（学术视界）** — 全能型学术智能体应用，为科研人员提供一站式学术工作平台

---

## 目录

1. [项目概览](#1-项目概览)
2. [整体架构](#2-整体架构)
3. [项目目录结构](#3-项目目录结构)
4. [后端架构详解](#4-后端架构详解)
   - 4.1 [应用入口与生命周期](#41-应用入口与生命周期)
   - 4.2 [配置管理](#42-配置管理)
   - 4.3 [数据库层](#43-数据库层)
   - 4.4 [数据模型](#44-数据模型)
   - 4.5 [Agent 智能体系统](#45-agent-智能体系统)
   - 4.6 [AI 服务层](#46-ai-服务层)
   - 4.7 [业务服务层](#47-业务服务层)
   - 4.8 [绘图引擎](#48-绘图引擎)
   - 4.9 [路由层（API 端点）](#49-路由层api-端点)
   - 4.10 [中间件与安全](#410-中间件与安全)
   - 4.11 [插件系统](#411-插件系统)
5. [前端架构详解](#5-前端架构详解)
   - 5.1 [技术栈与入口](#51-技术栈与入口)
   - 5.2 [布局与路由](#52-布局与路由)
   - 5.3 [状态管理](#53-状态管理)
   - 5.4 [API 客户端](#54-api-客户端)
   - 5.5 [核心组件](#55-核心组件)
   - 5.6 [Tauri 适配层](#56-tauri-适配层)
   - 5.7 [国际化](#57-国际化)
6. [Tauri 桌面端](#6-tauri-桌面端)
7. [依赖关系](#7-依赖关系)
8. [项目运行方式](#8-项目运行方式)
9. [测试体系](#9-测试体系)
10. [CI/CD](#10-cicd)

---

## 1. 项目概览

AcaSight 是一款面向科研人员的全能型学术智能体应用，整合以下核心能力：

| 能力域 | 功能 |
|--------|------|
| **文献管理** | Zotero 集成、多源智能搜索（OpenAlex/Semantic Scholar/Crossref/CORE/arXiv）、标签分类、全文检索 |
| **AI 辅助阅读** | AI 对话式阅读、智能摘要、多语言翻译、研究空白发现 |
| **学术写作** | 六步写作法、大纲编辑、分章节 AI 写作、引用管理（APA/MLA/GB/T 7714） |
| **数据分析** | 统计分析可视化、XRD/FTIR/Raman/UV-Vis/XPS 等光谱处理、DOE 实验设计 |
| **高级功能** | 文献综述生成、PPT 生成、OCR 识别、手绘白板、论文查重、知识图谱 |

---

## 2. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Tauri / Electron 桌面壳                   │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              React 18 + TypeScript 前端                 │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ PDF阅读器 │ │ 写作面板  │ │ 绘图工作台│ │ Agent面板 │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │  │
│  │       │             │            │             │         │  │
│  │  ┌────┴─────────────┴────────────┴─────────────┴─────┐  │  │
│  │  │              API Client (api.ts)                    │  │  │
│  │  └────────────────────┬───────────────────────────────┘  │  │
│  └───────────────────────┼──────────────────────────────────┘  │
│                          │ HTTP / SSE                          │
│  ┌───────────────────────┼──────────────────────────────────┐  │
│  │              FastAPI 后端 (Python)                        │  │
│  │  ┌────────────────────┴───────────────────────────────┐  │  │
│  │  │              路由层 (40+ Routers)                    │  │  │
│  │  └──────┬──────────┬──────────┬──────────┬────────────┘  │  │
│  │  ┌──────┴───┐ ┌────┴────┐ ┌───┴────┐ ┌───┴──────────┐  │  │
│  │  │ Agent 系统│ │ 业务服务 │ │绘图引擎│ │ AI 服务(多模型)│  │  │
│  │  └──────┬───┘ └────┬────┘ └───┬────┘ └───┬──────────┘  │  │
│  │  ┌──────┴──────────┴──────────┴──────────┴────────────┐  │  │
│  │  │     数据层: SQLite/PostgreSQL + ChromaDB + Redis    │  │  │
│  │  └────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**架构特点：**

- **前后端分离**：前端 React SPA + 后端 FastAPI REST API，通过 HTTP/SSE 通信
- **多桌面框架**：同时支持 Tauri（Rust 壳）和 Electron 双打包路径
- **Agent 驱动**：核心交互通过 ReAct 模式 Agent + Function Calling 实现
- **多模型路由**：AI 服务支持 7+ Provider（OpenAI/DeepSeek/Claude/Ollama/SiliconFlow/MiniMax/GLM），按任务复杂度智能路由

---

## 3. 项目目录结构

```
AcaSight/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── main.py             # FastAPI 应用入口
│   │   ├── config.py           # 配置管理（Pydantic Settings）
│   │   ├── database.py         # 数据库连接与会话管理
│   │   ├── agent/              # Agent 智能体系统
│   │   │   ├── core.py         # Agent 推理引擎（ReAct 循环）
│   │   │   ├── router.py       # Agent API 路由
│   │   │   ├── base_module.py  # 模块 Agent 抽象基类
│   │   │   ├── skill_registry.py # 技能注册表
│   │   │   ├── modules/        # 六大模块 Agent
│   │   │   │   ├── chart_agent.py
│   │   │   │   ├── knowledge_agent.py
│   │   │   │   ├── output_agent.py
│   │   │   │   ├── storage_agent.py
│   │   │   │   └── writing_agent.py
│   │   │   ├── skills/         # 技能定义
│   │   │   │   └── nature_skills.py
│   │   │   ├── context_compressor.py
│   │   │   ├── loop_detector.py
│   │   │   ├── message_sanitization.py
│   │   │   └── retry_utils.py
│   │   ├── models/             # SQLAlchemy 数据模型
│   │   │   ├── paper.py
│   │   │   ├── annotation.py
│   │   │   ├── document.py
│   │   │   ├── experiment.py
│   │   │   └── paper_dimensions.py
│   │   ├── routers/            # API 路由（40+ 个）
│   │   ├── services/           # 业务服务层
│   │   │   ├── ai_service.py   # AI 多模型服务
│   │   │   ├── pdf_service.py  # PDF 处理
│   │   │   ├── search_service.py # 文献搜索
│   │   │   ├── rag_service.py  # RAG 问答
│   │   │   ├── vector_service.py # 向量存储
│   │   │   ├── translation_service.py
│   │   │   ├── format_service.py
│   │   │   ├── workflow_engine.py
│   │   │   ├── plugin_system.py
│   │   │   ├── deep_research_service.py
│   │   │   ├── literature_service.py
│   │   │   ├── writing_template_service.py
│   │   │   ├── storage_service.py
│   │   │   └── plot/           # 绘图引擎
│   │   │       ├── theme_engine.py
│   │   │       ├── compute_pool.py
│   │   │       ├── spectrum_engine.py
│   │   │       ├── xrd_plot.py
│   │   │       ├── stats_plot.py
│   │   │       └── ... (10+ 绘图模块)
│   │   └── middleware/
│   │       └── security.py     # 安全中间件
│   ├── alembic/                # 数据库迁移
│   ├── plugins/                # 插件目录（11 个内置插件）
│   ├── tests/                  # 测试
│   ├── themes/                 # 期刊绘图主题（Nature/ACS/Elsevier/RSC/Science）
│   └── requirements.txt
│
├── frontend/                   # React + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx             # 应用根组件
│   │   ├── main.tsx            # 入口文件
│   │   ├── components/         # UI 组件
│   │   │   ├── Layout/         # 布局（ObsidianLayout）
│   │   │   ├── PDFReader/      # PDF 阅读器
│   │   │   ├── Writing/        # 写作面板
│   │   │   ├── Charts/         # 图表编辑器
│   │   │   ├── Agent/          # Agent 面板
│   │   │   ├── Search/         # 搜索页面
│   │   │   ├── Translate/      # 翻译组件
│   │   │   ├── KnowledgeGraph/ # 知识图谱
│   │   │   ├── Literature*/    # 文献相关组件
│   │   │   ├── Zotero/         # Zotero 面板
│   │   │   ├── Whiteboard/     # 白板
│   │   │   └── ... (20+ 组件目录)
│   │   ├── contexts/           # React Context
│   │   ├── hooks/              # 自定义 Hooks
│   │   ├── services/           # API 客户端
│   │   ├── store/              # Zustand 状态管理
│   │   ├── i18n/               # 国际化
│   │   ├── lib/                # 工具库
│   │   ├── types/              # TypeScript 类型
│   │   └── utils/              # 工具函数
│   ├── e2e/                    # E2E 测试
│   └── package.json
│
├── src-tauri/                  # Tauri 桌面端（Rust）
│   ├── src/
│   │   ├── lib.rs              # Tauri 应用入口
│   │   ├── main.rs             # Rust main
│   │   └── commands/mod.rs     # Tauri 命令
│   ├── Cargo.toml
│   └── tauri.conf.json
│
├── docs/                       # 项目文档
├── start.bat                   # Windows 快速启动脚本
└── .env.example                # 环境变量模板
```

---

## 4. 后端架构详解

### 4.1 应用入口与生命周期

**文件**: `backend/app/main.py`

FastAPI 应用通过 `lifespan` 异步上下文管理器管理生命周期：

| 阶段 | 操作 |
|------|------|
| **启动** | 安全检查（JWT_SECRET）→ 创建数据目录 → 初始化数据库 → 初始化 AI 服务 → 初始化搜索服务 → 启动 APScheduler 定时缓存清理 |
| **运行** | 注册 40+ 路由 → 挂载前端静态文件（SPA fallback）→ 请求日志中间件 → 全局异常处理 |
| **关闭** | 停止调度器 → 关闭 AI 连接池 → 关闭数据库连接 |

关键全局对象：
- `app.state.db_ready` — 数据库是否就绪
- `app.state.ai_service` — AI 服务单例
- `app.state.search_service` — 搜索服务实例
- `app.state.scheduler` — APScheduler 调度器

### 4.2 配置管理

**文件**: `backend/app/config.py`

使用 `pydantic-settings` 的 `BaseSettings` 管理配置，支持环境变量和 `.env` 文件：

```python
class Settings(BaseSettings):
    # 应用
    APP_NAME / APP_VERSION / DEBUG
    # 服务器
    HOST / PORT
    # 数据库
    DATABASE_URL / TEST_DATABASE_URL
    # Redis / Qdrant
    REDIS_URL / QDRANT_HOST / QDRANT_PORT
    # CORS
    CORS_ORIGINS
    # AI 模型（7+ Provider）
    OPENAI_API_KEY / OPENAI_BASE_URL
    DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL
    CLAUDE_API_KEY / OLLAMA_BASE_URL
    DEFAULT_AI_PROVIDER / DEFAULT_AI_MODEL
    # 搜索 API
    SEMANTIC_SCHOLAR_API_KEY / CORE_API_KEY
    # 文件存储
    UPLOAD_DIR / MAX_FILE_SIZE
    # Zotero
    ZOTERO_DB_PATH
    # 安全
    JWT_SECRET / JWT_ALGORITHM / JWT_EXPIRE_DAYS
    # 日志
    LOG_LEVEL
```

AI 模型配置还支持通过 `data/ai_config.json` 动态加载（含加密 API Key），`AIService` 每 30 秒自动重载。

### 4.3 数据库层

**文件**: `backend/app/database.py`

| 组件 | 说明 |
|------|------|
| `engine` | SQLAlchemy 异步引擎（SQLite 默认，支持 PostgreSQL） |
| `AsyncSessionLocal` | 异步会话工厂（`async_sessionmaker`） |
| `Base` | ORM 声明基类 |
| `init_db()` | 创建所有表 |
| `get_db()` | FastAPI 依赖注入，获取数据库会话 |
| `get_session()` | async context manager 形式，用于非 DI 场景 |

数据库迁移使用 Alembic，配置文件 `backend/alembic.ini`。

### 4.4 数据模型

#### Paper（论文模型）

**文件**: `backend/app/models/paper.py`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| title | String | 论文标题 |
| authors | Text (JSON) | 作者列表 |
| abstract | Text | 摘要 |
| year | Integer | 发表年份 |
| doi | String | DOI 标识 |
| arxiv_id | String | arXiv ID |
| pdf_hash | String | PDF 文件哈希（去重） |
| pdf_path | String | 本地 PDF 路径 |
| source | String | 来源（openalex/semantic_scholar/crossref 等） |
| venue | String | 发表期刊/会议 |
| keywords | Text (JSON) | 关键词列表 |
| citation_count | Integer | 被引次数 |
| embedding_id | String | 向量索引 ID |
| is_read | Boolean | 是否已读 |
| tags | Text (JSON) | 用户标签 |
| notes | Text | 用户笔记 |
| collection | String | 收藏夹 |

#### Annotation（批注模型）

**文件**: `backend/app/models/annotation.py`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer (PK) | 自增主键 |
| paper_id | Integer (FK) | 关联论文 |
| page_number | Integer | 页码 |
| annotation_type | String | 类型（highlight/underline/note） |
| position_data | Text (JSON) | 位置信息（坐标、范围） |
| content | Text | 批注内容 |
| color | String | 高亮颜色 |

#### Document / DocumentVersion（文档管理模型）

**文件**: `backend/app/models/document.py`

- `Document` — 文档主表（标题、内容、类型、标签）
- `DocumentVersion` — 文档版本表（版本号、内容快照、变更描述）

#### Experiment / ExperimentEntry / ExperimentLink（实验笔记本模型）

**文件**: `backend/app/models/experiment.py`

- `Experiment` — 实验主表（名称、描述、状态、标签）
- `ExperimentEntry` — 实验条目（参数、结果、观察记录）
- `ExperimentLink` — 实验关联（链接实验与论文/文档）

#### PaperDimensions（论文维度模型）

**文件**: `backend/app/models/paper_dimensions.py`

将论文按 11 个固定维度拆分：`research_problem / methodology / key_findings / innovation / limitations / future_work / dataset / evaluation_metrics / theoretical_basis / related_work / conclusion`

### 4.5 Agent 智能体系统

Agent 系统是 AcaSight 的核心创新，采用 **ReAct（Reasoning + Acting）模式** + **Function Calling** 架构。

#### 架构总览

```
用户任务
    │
    ▼
AgentCore.run()  ←── ReAct 推理循环
    │
    ├── 构建系统提示词（含工具列表 + 上下文）
    ├── 消息序列修复（role alternation + surrogate fix）
    ├── LLM 调用（带分类重试 + 多 Provider 回退）
    │
    ├── 有 tool_calls → 并行执行工具 → 结果返回 LLM → 继续循环
    │                  └── SkillRegistry.execute()
    │
    └── 无 tool_calls → 流式返回最终回答
```

#### AgentCore（推理引擎）

**文件**: `backend/app/agent/core.py`

```python
class AgentCore:
    max_turns: int = 15              # 最大推理轮次
    max_retries: int = 3             # Provider 失败重试
    max_context_compressions: int = 3 # 最大压缩轮次

    async def run(task, context, conversation_history) -> AsyncGenerator[Dict, None]
    # 流式返回事件类型：
    #   thinking / tool_call / tool_result / answer / heartbeat / error / interrupted
```

**关键机制：**

| 机制 | 文件 | 说明 |
|------|------|------|
| 消息序列修复 | `message_sanitization.py` | 修复 role alternation、surrogate 字符、tool_call JSON |
| 分类重试 | `retry_utils.py` | 区分 rate_limit/context_overflow/auth_error/timeout，不同策略 |
| 循环检测 | `loop_detector.py` | 检测重复工具调用、输出相似度、状态回环，3 次后自动中断 |
| 上下文压缩 | `context_compressor.py` | 消息超限时压缩历史，移除非关键工具结果 |
| 中断机制 | `core.py` | 用户可随时中断跑偏的 Agent |

#### SkillRegistry（技能注册表）

**文件**: `backend/app/agent/skill_registry.py`

```python
class SkillRegistry:
    _skills: Dict[str, SkillDefinition]    # 技能名 → 定义
    _bundles: Dict[str, SkillBundle]        # 技能包名 → 包

    def register(skill: SkillDefinition)    # 注册技能
    def get_tool_schemas(bundle_name)       # 生成 OpenAI function calling 格式
    async def execute(tool_name, arguments) # 执行技能
    def list_skills(category)               # 列出技能
    def list_bundles()                      # 列出技能包
```

**技能分类（SkillCategory）：**
literature / reading / writing / analysis / formatting / translation / search / figure / citation / data / response / paper2ppt / data_process / auto_chart / knowledge_graph / document_parse / framework / visio / polishing / pipeline

**内置技能包（15 个）：**

| 技能包 | 包含技能 |
|--------|----------|
| reading | paper_qa, paper_summarize, translate_text |
| writing | draft_section, generate_outline, polish_text, format_citation |
| search | search_literature, search_zotero, find_similar_zotero |
| review | draft_response, check_data_availability |
| presentation | paper_to_ppt, generate_figure |
| paper_framework | generate_framework_diagram, generate_method_flowchart, generate_experiment_architecture |
| visiomaster | convert_to_visio, export_vsdx |
| nature_figure | generate_nature_figure, validate_figure_standards, generate_plot_code |
| cs_writing | check_paper_logic, check_conclusion_support, check_experiment_design |
| nature_writing | write_nature_abstract, write_nature_introduction, write_nature_methods, write_nature_results |
| nature_polishing | polish_nature_style, check_language_quality, suggest_improvements |
| nature_citation | check_citation_format, check_citation_completeness, check_self_citation_ratio |
| nature_review | generate_review_reply, structure_point_by_point, suggest_revisions |
| nature_ppt | convert_paper_to_ppt, extract_key_slides, generate_slide_notes |
| academic_pipeline | deep_research_pipeline, literature_review_pipeline, paper_writing_pipeline, paper_review_pipeline, format_export_pipeline |

#### Nature Skills（学术技能实现）

**文件**: `backend/app/agent/skills/nature_skills.py`

注册 9 大学术能力，深度嵌入 Nature 期刊标准：
- 论文阅读（paper_qa / paper_summarize）
- 论文写作（draft_section / generate_outline / polish_text / format_citation）
- 文献检索（search_literature / search_zotero / find_similar_zotero）
- 翻译（translate_text）
- 图表生成（generate_figure / paper_to_ppt）
- 引用检查（check_citation_format / check_citation_completeness / check_self_citation_ratio）
- 审稿回复（draft_response / check_data_availability）
- 润色（polish_nature_style / check_language_quality / suggest_improvements）
- 框架图（generate_framework_diagram / generate_method_flowchart / generate_experiment_architecture）

#### 六大模块 Agent

**文件**: `backend/app/agent/modules/`

所有模块 Agent 继承 `BaseModule` 抽象基类，实现统一接口：

```python
class BaseModule(ABC):
    async def execute(task, context) -> ModuleResult  # 执行任务
    async def interrupt(reason, ...)                   # 中断执行
    async def resume(user_choice) -> ModuleResult      # 恢复执行
    def get_status() -> Dict                           # 获取状态
```

| 模块 Agent | 文件 | 职责 |
|------------|------|------|
| ChartAgent | `chart_agent.py` | 自动绘图、AI 推荐、模板生成、数据解析、图表保存 |
| KnowledgeAgent | `knowledge_agent.py` | 论文搜索、文档上传、RAG 拆分、图谱关联、精准引用 |
| OutputAgent | `output_agent.py` | Markdown 编辑、Word 导出、格式转换、润色、BibTeX 生成 |
| StorageAgent | `storage_agent.py` | 素材归档、缓存管理、维度拆分入库、文件操作 |
| WritingAgent | `writing_agent.py` | AI 写作、研究方向生成、试验方案设计、降重润色、自动写入章节 |

**模块注册表**（`modules/__init__.py`）管理所有 Agent 实例，供主控 Agent 和工作流引擎调度。

#### Agent Router（API 端点）

**文件**: `backend/app/agent/router.py`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/task` | 执行 Agent 任务（SSE 流式返回） |
| POST | `/api/agent/interrupt` | 中断正在运行的 Agent |
| GET | `/api/agent/status` | 获取 Agent 运行状态 |
| GET | `/api/agent/skills` | 列出可用技能 |
| GET | `/api/agent/bundles` | 列出技能包 |
| POST | `/api/agent/direct` | 直接调用指定技能（跳过推理） |
| POST | `/api/agent/memory` | 搜索 Agent 记忆（向量检索） |
| GET | `/api/agent/sessions` | 列出所有会话 |
| GET | `/api/agent/sessions/{id}` | 获取会话详情 |
| DELETE | `/api/agent/sessions/{id}` | 删除会话 |

### 4.6 AI 服务层

**文件**: `backend/app/services/ai_service.py`

`AIService` 是全局单例，核心特性：

| 特性 | 说明 |
|------|------|
| **多 Provider 支持** | OpenAI / DeepSeek / Claude / Ollama / SiliconFlow / MiniMax / GLM / Custom |
| **智能模型路由** | 按任务复杂度自动选择快/标准/强模型（`get_optimal_model()`） |
| **全局连接池** | 单例 `httpx.AsyncClient`，TCP 连接复用 |
| **响应缓存** | LRU 缓存（128 条，TTL=300s），幂等请求零延迟 |
| **动态配置** | 从 `ai_config.json` 加载，30 秒自动重载，API Key 加密存储 |

**任务复杂度映射：**

| 复杂度 | 任务类型 | 模型偏好 |
|--------|----------|----------|
| fast（快速） | translate, summarize, polish, shorten, abstract | DeepSeek-V4-Flash / gpt-4o-mini |
| standard（标准） | outline, section, literature_review, deep_read | DeepSeek-V3 / gpt-4o |
| strong（强力） | agent_reasoning, experiment_design, critic | deepseek-reasoner / gpt-4o |

**核心方法：**

```python
class AIService:
    async def chat(messages, provider, model, stream, temperature, max_tokens, task_type, use_cache) -> AsyncGenerator[str, None]
    async def chat_with_tools(messages, tools, provider, model, temperature, max_tokens) -> Dict
    async def generate_summary(text, max_length) -> str
    async def translate(text, target_language) -> str
    async def deep_read_paper(text, title) -> str
    async def generate_literature_review(papers, topic) -> str
    async def find_research_gaps(papers) -> str
    async def get_available_providers_with_tools() -> List[str]
```

### 4.7 业务服务层

| 服务 | 文件 | 职责 |
|------|------|------|
| **LiteratureSearchService** | `search_service.py` | 聚合 6 个数据源（CORE/OpenAlex/Semantic Scholar/Crossref/Europe PMC/arXiv），并行搜索 |
| **PDFService** | `pdf_service.py` | 文本提取、合并/拆分、旋转、水印、图片提取、结构化解析、渲染预览、AI 精读 |
| **RAGService** | `rag_service.py` | 与 RAGFlow 服务交互，支持查询和列表数据集 |
| **VectorService** | `vector_service.py` | ChromaDB 向量存储，论文索引、语义检索、HNSW 优化 |
| **TranslationService** | `translation_service.py` | 并发调用 Google/Microsoft/MyMemory + AI 兜底，支持流式翻译和格式保留 |
| **FormatService** | `format_service.py` | pypandoc 实现 Markdown → DOCX/LaTeX/PDF/HTML，支持 CSL 引用样式 |
| **WorkflowEngine** | `workflow_engine.py` | 多步骤工作流编排，步骤间数据流转、条件执行、超时处理 |
| **WritingTemplateService** | `writing_template_service.py` | 写作模板 CRUD，内置模板 + 用户自定义，分类标签 |
| **LiteratureService** | `literature_service.py` | 文献结构化分解，11 维度拆分，RAG 拆分支持 |
| **StorageService** | `storage_service.py` | PDF 本地仓库管理，文件去重、路径组织 |
| **DeepResearchService** | `deep_research_service.py` | 深度研究服务，子问题分解、多检索器并行聚合，快速/深度/综合三种模式 |
| **PluginSystem** | `plugin_system.py` | 插件注册/发现、生命周期管理、钩子系统、沙箱隔离、热插拔 |
| **CacheManager** | `cache_manager.py` | 缓存管理，过期清理 |
| **CitationMatcher** | `citation_matcher.py` | 引用匹配 |
| **CitationNetwork** | `citation_network.py` | 引用网络分析 |
| **DimensionService** | `dimension_service.py` | 论文维度分析 |
| **KnowledgeGraphService** | `knowledge_graph_service.py` | 知识图谱构建与查询 |
| **PlagiarismService** | `plagiarism_service.py` | 论文查重 |
| **PaperBananaService** | `paper_banana_service.py` | 图表生成 Pipeline |
| **FigureEditService** | `figure_edit_service.py` | SVG 矢量图编辑 |
| **MonitoringService** | `monitoring_service.py` | 运行监控 |
| **BabelDocService** | `babeldoc_service.py` | PDF 全文翻译与双语对照 |
| **DBLPService** | `dblp_service.py` | DBLP 检索 |
| **ZoteroSync** | `zotero_sync.py` | Zotero 同步 |
| **VersionHistory** | `version_history.py` | 版本历史管理 |

### 4.8 绘图引擎

**文件**: `backend/app/services/plot/`

AcaSight 内置专业级学术绘图引擎，支持多种材料表征图表：

| 模块 | 文件 | 功能 |
|------|------|------|
| **ThemeEngine** | `theme_engine.py` | 期刊风格主题（Nature/ACS/Elsevier/RSC/Science），加载/应用/列出主题 |
| **ComputePool** | `compute_pool.py` | 进程池计算接口，CPU 密集型任务异步并行 |
| **SpectrumEngine** | `spectrum_engine.py` | 光谱处理引擎：基线校正、平滑、峰识别、多峰拟合 |
| **XRDPlot** | `xrd_plot.py` | XRD 图表：堆叠图、Jade 文件解析、PDF 卡片绘制 |
| **FTIRPlot** | `ftir_plot.py` | FTIR 红外光谱图 |
| **RamanPlot** | `raman_plot.py` | Raman 拉曼光谱图 |
| **UVVisPlot** | `uvvis_plot.py` | UV-Vis 紫外可见光谱图 |
| **XPSPlot** | `xps_plot.py` | XPS 光电子能谱图 |
| **StatsPlot** | `stats_plot.py` | 统计图表：ANOVA 条形图、相关性热力图、PCA 双向图 |
| **DOEPlot** | `doe_plot.py` | DOE 实验设计图 |
| **BETPlot** | `bet_plot.py` | BET 比表面积图 |
| **ThermalPlot** | `thermal_plot.py` | 热分析图（TGA/DSC） |
| **RSMPlot** | `rsm_plot.py` | 响应面方法图 |
| **SchemaRenderer** | `schema_renderer.py` | 图表模板渲染 |
| **CIFParser** | `cif_parser.py` | CIF 晶体结构文件解析 |

**绘图路由**（`routers/plot.py`）：提供 20+ 个图表生成 API 端点。

### 4.9 路由层（API 端点）

所有路由在 `main.py` 中以 try/except 方式注册，单个路由加载失败不影响整体运行：

| 路由模块 | 前缀 | 核心端点 |
|----------|------|----------|
| pdf | `/api/pdf` | 上传、文本提取、页面渲染、搜索、AI 精读 |
| chat | `/api/chat` | AI 对话、流式输出、摘要、翻译、研究空白 |
| search | `/api/search` | 文献搜索、DOI 查找、来源列表、导入 |
| notes | `/api/notes` | 笔记 CRUD |
| zotero | `/api/zotero` | Zotero 库读取 |
| storage | `/api/storage` | PDF 存储管理 |
| sync | `/api/sync` | Zotero 同步 |
| chart_auto | `/api/chart/auto` | 智能绘图 |
| agent_orchestration | `/api/agent` | Agent 编排 |
| agent_tools_api | `/api/agent` | Agent 工具对话 |
| workflow_api | `/api/system` | 工作流与状态 |
| writing | `/api/writing` | 智能写作 |
| literature | `/api/literature` | 文献结构化 |
| ai_config | `/api/ai` | AI 配置管理 |
| papers | `/api/papers` | 论文数据库 CRUD |
| annotations | `/api/annotations` | 批注管理 |
| knowledge_graph | `/api/knowledge-graph` | 知识图谱可视化 |
| rag | `/api/rag` | RAG 问答 |
| format_export | `/api/format` | 格式导出 |
| template | `/api/templates` | 模板管理 |
| paper_banana | `/api` | 图表生成 Pipeline |
| deep_research | `/api` | 深度研究 Pipeline |
| figure_edit | `/api` | SVG 矢量图编辑 |
| arch | `/api` | 架构优化 |
| plugins | `/api` | 插件系统 |
| workspace_state | `/api` | 工作区状态 |
| version_and_templates | `/api` | 版本历史 + 写作模板 |
| monitoring | — | 运行监控 |
| data_preprocess | `/api/data-preprocess` | 数据预处理 |
| dblp | `/api/dblp` | DBLP 检索 |
| citations | `/api` | AI 参考文献提取 |
| literature_table | `/api` | AI 文献表格 |
| documents | `/api/documents` | 文档管理（OnlyOffice） |
| convert | `/api/convert` | 格式转换 |
| literature_review | `/api` | 文献综述 |
| brainstorm | `/api` | AI 白板头脑风暴 |
| plot | `/api` | 绘图 |
| latex | `/api/latex` | LaTeX 编辑器 |
| experiment | `/api/experiments` | 实验笔记本 |
| literature_batch | `/api/literature-batch` | 批量文献处理 |
| plagiarism | `/api/plagiarism` | 论文查重 |
| translate | `/api/translate` | 翻译引擎 |

### 4.10 中间件与安全

**文件**: `backend/app/middleware/security.py`

| 中间件 | 功能 |
|--------|------|
| IP 限流 | 每分钟最多 60 次请求 |
| 请求大小限制 | 最大 50MB |
| CORS 加固 | 限制允许的源、方法、头部 |
| 安全头 | X-Content-Type-Options / X-Frame-Options / X-XSS-Protection / Content-Security-Policy |
| GZip 压缩 | 最小 1000 字节 |
| 请求日志 | 记录方法、路径、状态码、耗时 |

### 4.11 插件系统

**文件**: `backend/app/services/plugin_system.py` + `backend/plugins/`

插件系统支持注册/发现、生命周期管理（加载/启用/禁用/卸载）、钩子系统、沙箱隔离和热插拔。

**内置插件（11 个）：**

| 插件 | 目录 | 功能 |
|------|------|------|
| academic-research-skills | `plugins/academic-research-skills/` | 学术研究技能 |
| example-search-enhancer | `plugins/example-search-enhancer/` | 搜索增强示例 |
| nature-citation-check | `plugins/nature-citation-check/` | Nature 引用检查 |
| nature-figure | `plugins/nature-figure/` | Nature 图表生成 |
| nature-paper2ppt | `plugins/nature-paper2ppt/` | Nature 论文转 PPT |
| nature-polishing | `plugins/nature-polishing/` | Nature 论文润色 |
| nature-review-reply | `plugins/nature-review-reply/` | Nature 审稿回复 |
| nature-writing | `plugins/nature-writing/` | Nature 论文写作 |
| paper-framework | `plugins/paper-framework/` | 论文框架图 |
| research-paper-writing-skills | `plugins/research-paper-writing-skills/` | 研究论文写作技能 |
| visiomaster | `plugins/visiomaster/` | Visio 图纸重建 |

每个插件包含 `plugin.py`（逻辑）和 `plugin.yaml`（元数据）。

---

## 5. 前端架构详解

### 5.1 技术栈与入口

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.2 | UI 框架 |
| TypeScript | 5.2 | 类型安全 |
| Vite | 5.0 | 构建工具 |
| Tailwind CSS | 3.3 | 样式系统 |
| Zustand | 4.4 | 状态管理 |
| React Router | 6.20 | 路由 |
| react-pdf | 7.5 | PDF 渲染 |
| Plotly.js | 3.5 | 数据可视化 |
| Monaco Editor | 4.6 | 代码/文本编辑 |
| Excalidraw | 0.18 | 手绘白板 |
| Milkdown | 7.21 | Markdown 编辑器（支持数学公式/代码高亮） |
| i18next | 26.3 | 国际化 |
| react-query | 5.8 | 数据请求缓存 |

**入口文件**: `frontend/src/main.tsx`

```tsx
// 初始化 PDF.js Worker → i18n → KaTeX CSS → 渲染 App
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><App /></React.StrictMode>
);
```

**App 组件**: `frontend/src/App.tsx`

```tsx
<ErrorBoundary>
  <ThemeProvider>
    <AppProvider>
      <ObsidianLayout />
    </AppProvider>
  </ThemeProvider>
</ErrorBoundary>
```

### 5.2 布局与路由

**ObsidianLayout**（`components/Layout/ObsidianLayout.tsx`）是整个应用的核心布局组件：

- **看板模式（Dashboard）**：展示最近文件、快捷操作、统计信息
- **工作区模式（Workspace）**：左侧边栏 + 主内容区 + 右侧面板
- 管理面板显示/隐藏、工作区切换、拖拽交互
- 调度 20+ 个面板组件

### 5.3 状态管理

前端使用 **三层状态管理**：

| 层级 | 方案 | 文件 | 用途 |
|------|------|------|------|
| 全局 Context | React Context | `contexts/AppContext.tsx` | PDF 状态、AI 面板、笔记、注释、Zotero、编辑器标签页 |
| 独立 Store | Zustand | `store/workspaceStore.ts` | 面板状态、写作草稿、搜索历史、最近文件 |
| Agent Store | Zustand | `store/agentStore.ts` | Agent 消息、会话历史、运行状态、多会话管理 |
| Plot Store | Zustand | `store/plotStore.ts` | 图表编辑器状态、图层、XRD 数据集 |
| 面板切换 | Zustand | `store/panelSwitchStore.ts` | 面板切换状态 |
| 文档桥接 | Zustand | `store/documentBridgeStore.ts` | 文档与编辑器桥接 |

**AppContext** 提供的核心状态：

```typescript
interface AppState {
  // PDF
  pdfFile: File | null;
  pdfId: string;
  pdfText: string;
  // AI
  aiPanelOpen: boolean;
  aiMessages: Message[];
  // 笔记
  notes: Note[];
  // 注释
  annotations: Annotation[];
  // Zotero
  zoteroConnected: boolean;
  // 编辑器标签页
  openTabs: Tab[];
  activeTabId: string;
}
```

### 5.4 API 客户端

**文件**: `frontend/src/services/api.ts`

统一的 API 客户端封装（2435 行），按功能域组织：

| 模块 | 核心方法 |
|------|----------|
| PDF | uploadPdf, extractText, renderPage, searchInPdf |
| AI | chat, streamChat, generateSummary, translate, deepRead |
| 搜索 | searchLiterature, searchByDoi, getSources |
| 文献 | structureLiterature, batchProcess |
| 图表 | generateChart, getXrdPlot, getSpectrum |
| Zotero | getLibrary, syncLibrary |
| Agent | runTask, listSkills, directCall |
| 写作 | generateOutline, draftSection, polishText |
| 格式 | exportToDocx, exportToLatex, exportToPdf |

### 5.5 核心组件

| 组件目录 | 核心组件 | 功能 |
|----------|----------|------|
| PDFReader/ | PDFViewer, Annotator, AISidePanel, TOCSidebar, PageThumbnails, AnnotationToolbar, FloatingTranslate, TranslatorPopup | PDF 阅读、批注、AI 侧边栏、目录、翻译 |
| Writing/ | WritingPanel, OutlineEditor, TemplateGallery, VersionHistoryPanel, WritingInterruptDialog | 学术写作、大纲编辑、模板、版本历史 |
| WritingWorkbench/ | PaperWritingWorkbench | 论文写作工作台 |
| Charts/ | ChartPanel, PlotStudio, ChartEditor, LayerManager, XRDStackedChart, RamanSpectrumChart, XPSSpectrumChart, StatisticsPanel, ResponseSurface3D | 图表编辑、XRD/Raman/XPS 光谱、统计图表 |
| Agent/ | AgentPanel, ContextualAgentBar | Agent 交互面板 |
| Search/ | SearchPage, DeepResearchPanel | 文献搜索、深度研究 |
| Translate/ | BilingualPDFViewer, BilingualReader, FloatingTranslate, FullPageTranslate | 双语对照、浮动翻译、全页翻译 |
| KnowledgeGraph/ | KnowledgeGraphPanel | 知识图谱可视化 |
| LiteratureReview/ | LiteratureReviewView | 文献综述 |
| LiteratureTable/ | LiteratureTableView | 文献表格 |
| Zotero/ | ZoteroPanel | Zotero 管理 |
| Whiteboard/ | ExcalidrawBoard | 手绘白板 |
| Plagiarism/ | PlagiarismCheckPanel | 论文查重 |
| Experiment/ | LabNotebookPanel | 实验笔记本 |
| Latex/ | LatexEditorPanel | LaTeX 编辑器 |
| Brainstorm/ | BrainstormView | 头脑风暴 |
| Monitor/ | MonitoringDashboard | 运行监控 |
| Settings/ | SettingsModal, ArchPanel, PluginPanel, DataExportImportPanel | 设置、架构、插件、数据导入导出 |
| Common/ | ErrorBoundary, FloatingBubble, FloatingTranslate, ImageViewer, LazyImage, MarkdownRenderer, TauriDragDrop | 通用组件 |
| Views/ | FileExplorerView, OutlineView, GraphView, BookmarksView, TagsView, MaterialPanel, EditorView | 文件浏览、大纲、图谱、书签、标签 |

### 5.6 Tauri 适配层

**文件**: `frontend/src/lib/tauri-adapter.ts`

提供统一的 Tauri 环境适配器，兼容浏览器和 Tauri 两种运行环境：

```typescript
// 文件操作
readFile(path) / writeFile(path, content) / readBinaryFile(path)
// 系统信息
isTauri() / getPlatform() / getAppVersion()
// 窗口操作
minimize() / maximize() / close()
// 对话框
openFileDialog() / saveFileDialog()
// 拖拽
onFileDrop(callback)
```

### 5.7 国际化

**文件**: `frontend/src/i18n/index.ts`

使用 i18next + react-i18next，支持中英文切换：
- 语言文件：`locales/en.json` / `locales/zh.json`
- 自动检测浏览器语言
- 本地存储记住用户偏好

---

## 6. Tauri 桌面端

**文件**: `src-tauri/`

### Rust 入口

**文件**: `src-tauri/src/lib.rs`

Tauri 应用入口，配置：
- 菜单栏（文件/编辑/视图/帮助）
- 全局快捷键（Ctrl+Q 退出、Ctrl+N 新建、Ctrl+O 打开）
- 系统托盘
- 窗口行为（关闭到托盘、单实例）

### Tauri 命令

**文件**: `src-tauri/src/commands/mod.rs`

| 命令 | 功能 |
|------|------|
| `read_text_file` | 读取文本文件 |
| `write_text_file` | 写入文本文件 |
| `read_binary_file` | 读取二进制文件 |
| `get_file_info` | 获取文件元信息 |
| `get_system_info` | 获取系统信息 |

### Tauri 配置

**文件**: `src-tauri/tauri.conf.json`

| 配置项 | 值 |
|--------|-----|
| 产品名 | AcaSight |
| 版本 | 3.0.0 |
| 标识符 | com.acasight.app |
| 窗口尺寸 | 1400x900（最小 1024x680） |
| 打包目标 | NSIS / MSI |
| Tauri 插件 | fs, dialog, shell, updater, process, autostart, global-shortcut, window-state |

### Cargo 依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| tauri | 2 | 桌面框架 |
| tauri-plugin-* | 2 | 文件/对话框/Shell/更新/快捷键等 |
| serde / serde_json | 1 | 序列化 |
| base64 | 0.22 | 编码 |
| open | 5 | 打开外部链接 |

---

## 7. 依赖关系

### 后端 Python 依赖

| 类别 | 依赖 | 版本 |
|------|------|------|
| Web 框架 | fastapi, uvicorn, python-multipart, httpx | ≥0.104 |
| 数据库 | sqlalchemy, alembic, aiosqlite | ≥2.0 |
| 向量数据库 | qdrant-client, chromadb | ≥1.6 |
| AI/LLM | openai, langsmith | ≥1.3 |
| PDF 处理 | pymupdf, pypdf | ≥1.23 |
| PDF 翻译 | babeldoc | ≥0.6.3 |
| 数据处理 | pandas, numpy, openpyxl | ≥2.1 |
| 文档转换 | pypandoc | ≥1.11 |
| 异步 HTTP | aiohttp | ≥3.9 |
| PPT 生成 | python-pptx | ≥0.6 |
| 认证 | python-jose | ≥3.3 |
| 配置 | pydantic, pydantic-settings | ≥2.5 |
| 日志 | structlog | ≥23.2 |
| 定时任务 | apscheduler | ≥3.10 |
| 测试 | pytest, pytest-asyncio | ≥7.4 |
| 翻译缓存 | peewee | ≥3.17 |

### 前端 npm 依赖

| 类别 | 依赖 | 版本 |
|------|------|------|
| UI 框架 | react, react-dom | 18.2 |
| 状态管理 | zustand | 4.4 |
| 路由 | react-router-dom | 6.20 |
| PDF | react-pdf, pdf-lib | 7.5 / 1.17 |
| 图表 | plotly.js, react-plotly.js, recharts | 3.5 / 2.6 / 2.10 |
| 编辑器 | @monaco-editor/react, @milkdown/* | 4.6 / 7.21 |
| 白板 | @excalidraw/excalidraw | 0.18 |
| Markdown | react-markdown, remark-gfm, remark-math, rehype-katex | 9.0 |
| UI 组件 | @radix-ui/*, lucide-react | — |
| HTTP | axios | 1.6 |
| 国际化 | i18next, react-i18next | 26.3 / 17.0 |
| Tauri | @tauri-apps/api, @tauri-apps/plugin-* | 2.x |
| 图形 | fabric, html2canvas, jspdf, jszip | — |
| 数据 | exceljs, date-fns | — |
| 测试 | vitest, @testing-library/react, @playwright/test | — |

### 外部服务依赖

| 服务 | 用途 | 必需 |
|------|------|------|
| AI Provider（至少一个） | OpenAI/DeepSeek/Claude/Ollama 等 | 是 |
| SQLite | 本地数据库 | 是 |
| ChromaDB | 向量存储 | 否（可选） |
| Qdrant | 向量存储（RAGFlow） | 否（可选） |
| Redis | 缓存 | 否（可选） |
| Zotero | 文献管理集成 | 否（可选） |
| Pandoc | 文档格式转换 | 否（可选） |
| Semantic Scholar API | 文献搜索 | 否（可选） |
| CORE API | 文献搜索 | 否（可选） |

---

## 8. 项目运行方式

### 环境要求

- Node.js 18+
- Python 3.10+
- Rust（仅 Tauri 构建时）

### 快速启动（Windows）

```bash
# 双击运行
start.bat
```

或手动启动：

### 开发模式

**终端 1 — 后端：**
```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
alembic upgrade head        # 初始化数据库
uvicorn app.main:app --reload --port 8000
```

**终端 2 — 前端：**
```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

**Tauri 桌面模式：**
```bash
cd frontend
npm run tauri:dev
```

### 构建发布

**Web 版本：**
```bash
cd frontend
npm run build               # 输出到 frontend/dist/
# 后端自动服务 frontend/dist/ 静态文件
```

**Tauri 桌面应用：**
```bash
cd frontend
npm run tauri:build         # 输出到 src-tauri/target/release/
npm run tauri:build:win     # Windows NSIS/MSI 安装包
```

**Electron 桌面应用：**
```bash
cd frontend
npm run electron:build      # 输出到 dist-electron/
npm run electron:build:win  # Windows 安装包
```

### 环境变量配置

复制 `.env.example` 为 `.env`，至少配置一个 AI Provider：

```env
# 最小配置（使用 Ollama 本地模型）
DEFAULT_AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434

# 或使用云端模型
DEFAULT_AI_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
```

### 关键端口

| 服务 | 端口 |
|------|------|
| 前端开发服务器 | 5173 |
| 后端 API | 8000 |
| API 文档 | 8000/api/docs |
| ReDoc | 8000/api/redoc |
| Ollama | 11434 |
| Qdrant | 6333 |
| Redis | 6379 |

---

## 9. 测试体系

### 后端测试

**框架**: pytest + pytest-asyncio

```bash
cd backend
pytest                          # 运行所有测试
pytest tests/routers/           # 路由测试
pytest tests/test_api_contract.py  # API 契约测试
pytest tests/bench/             # 性能基准测试
```

测试覆盖的路由模块（`tests/routers/`）：
agent, agent_tools_api, ai_config, annotations, arch, chart, chat, deep_research, figure_edit, format, knowledge, literature, notes, paper_banana, papers, pdf, plugins, rag, search, storage, sync, template, workflow, writing, zotero

### 前端测试

**单元测试**: Vitest + Testing Library

```bash
cd frontend
npm run test              # 运行单元测试
npm run test:watch        # 监听模式
npm run test:coverage     # 覆盖率报告
```

**E2E 测试**: Playwright

```bash
npm run test:e2e          # 运行 E2E 测试
npm run test:e2e:ui       # Playwright UI 模式
```

---

## 10. CI/CD

**文件**: `.github/workflows/ci.yml`

CI 流水线包含：
- 后端 Python 代码检查与测试
- 前端 TypeScript 类型检查、ESLint、Vitest 单元测试
- E2E 测试（Playwright）
- Tauri 构建验证

---

## 附录：关键设计决策

| 决策 | 原因 |
|------|------|
| 路由 try/except 注册 | 单个模块加载失败不影响整体运行，提升容错性 |
| Agent ReAct + Function Calling | 兼顾推理能力和工具调用灵活性 |
| 多 Provider 智能路由 | 按任务复杂度选择模型，平衡成本与质量 |
| 全局 httpx 连接池 | TCP 连接复用，减少 AI API 延迟 |
| LRU 响应缓存 | 幂等请求零延迟，减少 API 调用 |
| 消息序列修复 | 防止 LLM API 400 错误（role alternation / surrogate） |
| 循环检测 | 防止 Agent 无限循环，3 次检测后自动中断 |
| 上下文压缩 | 长对话自动压缩，避免 token 溢出 |
| Tauri + Electron 双路径 | Tauri 轻量高性能，Electron 兼容性好 |
| 插件系统 | 可扩展架构，支持第三方技能包 |
