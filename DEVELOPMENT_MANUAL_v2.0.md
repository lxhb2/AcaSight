# AcaSight AI 论文写作系统架构开发手册 v1.0

> 版本：v1.0 | 日期：2026-05-30 | 状态：开发中
> 基于六大应用架构模块，定义 Agent 调度、多渠道文献调用、数据插图交互、统一存储四大核心规范

---

## 1. 手册总则

本手册针对系统六大应用架构模块，明确四大核心开发规范与技术方案：

| 核心能力 | 目标 |
|----------|------|
| **Agent 跨模块调度** | 各模块配置独立 Agent 调度能力，支持写作全流程自动化衔接 |
| **多渠道文献检索与调用** | 本地/数据库/网络 API 三类文献源差异化处理 |
| **数据插图人机交互** | 写作到数据/插图章节时强制中断，用户确认后继续 |
| **全类型数据统一存储** | 结构化文献数据、绘图素材、内嵌对象统一归档 |

---

## 2. 六大模块 Agent 调度开发规范

### 2.1 模块划分

| 模块 | ID | Agent 调度职责 |
|------|-----|---------------|
| 文献管理与深度阅读 | `literature` | 检索、RAG 问答、文献推荐、对比分析 |
| 学术写作与排版 | `writing` | 提纲生成、章节撰写、润色、引用管理、Word 导出 |
| 科研数据与可视化 | `charts` | 数据导入、图表生成、AI 自动绘图、统计分析 |
| AI 学术 Agent | `agent` | 中央调度器，接收用户意图，分发任务到各模块 |
| 知识管理与发现 | `knowledge` | 知识图谱、概念提取、趋势分析、个人知识库 |
| 笔记/白板/协作 | `notes` | Markdown 编辑、白板、格式转换、版本管理 |

### 2.2 开发落地原则

1. **禁止从零搭建** → 优先复用开源工具（LangChain Agent、SkillRegistry 现有框架）
2. **独立调度 + 协同联动** → 各模块 Agent 可独立运行，也可被中央 Agent 调用
3. **统一工具注册** → 所有模块通过 ToolRegistry 注册可调用工具，Agent 通过 function calling 调用

### 2.3 技术方案

```
                    ┌──────────────────┐
                    │   Central Agent   │
                    │  (AgentPanel)     │
                    │  ToolRegistry     │
                    └────────┬─────────┘
           ┌─────────────────┼─────────────────┐
           ↓                 ↓                  ↓
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Literature   │  │   Writing    │  │   Charts     │
    │ Tools:       │  │  Tools:      │  │  Tools:      │
    │ - search     │  │  - outline   │  │  - auto_chart│
    │ - rag_query  │  │  - section   │  │  - plot_data │
    │ - get_paper  │  │  - polish    │  │  - export_img│
    │ - cite       │  │  - export    │  │  - template  │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 3. 多渠道论文检索与 AI 调用技术方案

### 3.1 本地及数据库文献：RAG 结构化拆分

#### 拆分维度（11 字段）

每篇文献 AI 拆分为以下标准化字段，全部入库：

| # | 字段 | 用途 |
|---|------|------|
| 1 | `abstract` | 摘要 → 写作时快速判断相关性 |
| 2 | `background` | 研究背景 → 引言/绪论素材 |
| 3 | `purpose` | 研究目的与意义 → 选题论证 |
| 4 | `current_status` | 研究现状 → 文献综述素材 |
| 5 | `research_question` | 研究问题 → 方法论参考 |
| 6 | `basic_theory` | 基本理论 → 理论基础章节 |
| 7 | `method` | 研究方法 → 实验方法参考 |
| 8 | `results` | 结果与评价 → 结果讨论素材 |
| 9 | `innovation` | 创新点 → 创新点论证 |
| 10 | `limitations` | 局限与建议 → 不足与展望 |
| 11 | `conclusion` | 结论 → 结论引用 |

#### 数据库 Schema

```sql
CREATE TABLE paper_structured (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    journal TEXT,
    doi TEXT,
    source TEXT,              -- 'local' | 'database' | 'api'
    
    -- 11 结构化字段
    abstract TEXT,
    background TEXT,
    purpose TEXT,
    current_status TEXT,
    research_question TEXT,
    basic_theory TEXT,
    method TEXT,
    results TEXT,
    innovation TEXT,
    limitations TEXT,
    conclusion TEXT,
    
    -- 元数据
    full_text_path TEXT,
    structured_at TIMESTAMP,
    knowledge_graph_id TEXT,
    
    -- 索引
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_paper_field ON paper_structured(source, year);
CREATE INDEX idx_paper_kg ON paper_structured(knowledge_graph_id);
```

### 3.2 网络 API 检索文献：效率优化方案

```
传统流程（废弃）：搜索 → 全量拆分 → 全量存储 → 调用
              ↑ 慢、冗余、无效存储

优化流程（采纳）：搜索 → 即时展示 → 用户选择 → 仅确认的拆分存储
                              ↓
                    未被使用的 → 临时缓存 30min → 自动清理
```

**实现要点**：
1. 搜索结果即时返回，不做拆分
2. 用户点击"确认使用" → 触发单篇拆分 + 入库
3. 未确认结果临时 Redis/内存缓存，30 分钟过期
4. 写作时引用 → 从已入库文献匹配 → 返回对应维度内容

---

## 4. 数据与插图人机交互中断机制

### 4.1 触发条件

AI 写作检测到以下关键词/章节时自动暂停：
- "数据"、"实验"、"结果"、"图表"、"如图"、"见表"
- 章节标题包含：结果与分析、实验部分、数据、图/Figure/Fig/表/Table

### 4.2 用户可选模式

```
┌─────────────────────────────────────────────┐
│         AI 写作中断 — 素材选择               │
├─────────────────────────────────────────────┤
│                                             │
│  当前章节：第三章 结果与分析                  │
│  需要插入：数据图表 / 实验结果                │
│                                             │
│  ○ 模式一：上传本地文件                       │
│    └ 实验图片、数据文件、开题报告等            │
│                                             │
│  ○ 模式二：AI 自动生成（基于已有数据）          │
│    └ 使用科研绘图 Skill 自动生成图表           │
│                                             │
│  ○ 模式三：从已有作品选择                      │
│    └ 历史保存的图表、内嵌对象                  │
│                                             │
│  ○ 跳过（本章不插入图表）                      │
│                                             │
│  [确认]  [返回修改]                           │
└─────────────────────────────────────────────┘
```

### 4.3 交互流程

```
AI 写作 → 检测到数据/图表章节
  → 暂停写入
  → 弹出素材选择对话框
  → 用户选择模式
    ├─ 模式一：打开文件选择器 → 上传 → 插入
    ├─ 模式二：调用 ChartPanel Skill → 生成 → 预览 → 确认 → 插入
    └─ 模式三：打开已保存列表 → 选择 → 插入
  → 继续写作
```

---

## 5. 全类型数据统一存储规范

### 5.1 存储架构

```
C:\Users\...\AcaSight\backend\data\
├── literature/           # 结构化文献数据
│   ├── paper.db          # SQLite 主库 (paper_structured 表)
│   └── fulltext/         # PDF 全文存储
├── charts/               # 科研绘图相关
│   ├── uploads/          # 用户上传的图片/数据
│   ├── generated/        # 系统生成的成品图片
│   │   └── {timestamp}_{chart_id}.png
│   └── projects/         # 绘图工程文件 (数据+参数+内嵌对象)
│       └── {project_id}.json
├── temp/                 # 临时缓存 (定时清理)
│   └── cache.db
└── exports/              # 导出文件 (Word/PPT)
    └── {timestamp}_{title}.docx
```

### 5.2 数据生命周期

| 数据类型 | 持久化 | 清理策略 |
|----------|--------|----------|
| 结构化文献 | ✅ 永久 | 用户手动删除 |
| 绘图成品 | ✅ 永久 | 用户手动删除 |
| 绘图工程 | ✅ 永久 | 用户手动删除 |
| 用户上传素材 | ✅ 永久 | 用户手动删除 |
| 网络检索临时缓存 | ❌ | 30 分钟自动清理 |
| 写作临时交互数据 | ❌ | 会话结束后清理 |
| 导出文件 | ✅ 30 天 | 定时清理旧版本 |

---

## 6. 开发落地路线图

### Phase 1：基础存储 + 文献结构化（当前）

| 任务 | 优先级 | 预估 |
|------|--------|------|
| paper.db 数据库 + Schema | P0 | 1h |
| 文献 RAG 拆分服务（11 字段） | P0 | 2h |
| 文献管理 API (CRUD + 查询) | P0 | 1h |
| 网络检索"搜索即用"优化 | P1 | 1h |
| 数据统一存储目录初始化 | P1 | 0.5h |

### Phase 2：Agent 调度框架

| 任务 | 优先级 | 预估 |
|------|--------|------|
| ToolRegistry 统一注册 | P0 | 2h |
| Agent function calling 集成 | P0 | 2h |
| 各模块工具注册 | P1 | 2h |

### Phase 3：人机交互中断

| 任务 | 优先级 | 预估 |
|------|--------|------|
| WritingWorkspace 中断检测 | P0 | 1h |
| 素材选择对话框组件 | P0 | 2h |
| Skill 绘图集成 | P1 | 2h |

### Phase 4：知识管理增强

| 任务 | 优先级 | 预估 |
|------|--------|------|
| 概念提取服务 | P2 | 2h |
| 研究趋势分析 | P2 | 2h |
| 知识图谱可视化增强 | P2 | 1h |

---

*文档状态：开发中 | 下次审查：Phase 1 完成后*