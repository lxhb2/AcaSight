# AcaSight — 学术研究智能助手平台

## 一、产品概述

**AcaSight** 是一款面向科研工作者的全流程学术研究智能助手平台，集文献管理、AI深度解析、论文撰写、知识可视化于一体。平台以 **AI 11维度结构化拆分**为核心底层逻辑，将学术论文从"黑盒全文"转化为"结构化数据"，驱动文献综述、对比分析、选题头脑风暴等高阶学术场景。

### 核心理念

> **先看后存，显示器与存储器分离** — AI拆分结果先在"显示器"预览，用户确认后存入"存储器"（数据库+向量库），所有功能共享同一份结构化数据。

### 设计原则

1. **AI 11维度拆分是全系统默认底层逻辑** — 所有文献入库时自动执行拆分，不可跳过
2. **文献双存储规范** — 源文件（PDF原文）+ 结构化数据（11维度表）+ 向量索引，三介质持久化
3. **文献唯一编号** — 每篇文献自动生成 `FLT-ZH-2024-01` 格式编号，全系统共享
4. **模块化工作台** — 功能模块按需组合，不跳转页面，覆盖层交互

---

## 二、技术架构

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React 18 | 18.x | UI框架，并发模式 |
| TypeScript | 5.x | 类型安全 |
| Vite | 5.x | 构建工具，HMR |
| Excalidraw | 0.18.x | AI白板/头脑风暴画布 |
| react-pdf | 9.x | PDF阅读与标注 |
| Recharts | 2.x | 数据可视化图表 |
| i18next | 23.x | 中英文国际化 |
| Lucide React | — | 图标库 |

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.115+ | 异步Web框架 |
| SQLAlchemy 2.0 | — | ORM（异步模式） |
| SQLite / PostgreSQL | — | 关系型数据库 |
| Qdrant | — | 向量数据库（语义检索） |
| httpx | — | 异步HTTP客户端 |
| pypdf | — | PDF文本提取 |
| cryptography | — | API密钥AES-256-GCM加密存储 |
| uvicorn | — | ASGI服务器 |

### AI 服务集成

| 提供商 | 模型 | 用途 |
|--------|------|------|
| SiliconFlow | DeepSeek-V4-Flash | 默认快速推理 |
| SiliconFlow | DeepSeek-V3 Pro | 标准推理 |
| OpenAI | GPT-4o | 可选 |
| DeepSeek | DeepSeek-Chat | 可选 |
| 智谱AI | GLM-4-Plus | 可选 |
| Ollama | Qwen3.5 | 本地部署 |
| Claude | Claude-3.5-Sonnet | 可选 |

---

## 三、功能模块详解

### 3.1 文献管理（核心基础）

#### 文献三入口入库

| 入口 | 说明 |
|------|------|
| 本地上传 | 直接上传PDF/Word文件 |
| 文献检索导入 | 通过DBLP、Semantic Scholar等API检索并导入 |
| 在线抓取 | 通过DOI/URL在线获取文献元数据 |

#### 强制11维度自动拆分

所有文献入库时自动执行AI 11维度结构化拆分，生成统一结构化数据：

| 维度 | 中文名 | 说明 |
|------|--------|------|
| abstract | 摘要 | 论文核心摘要 |
| research_background | 研究背景 | 研究领域现状与背景 |
| research_purpose | 研究目的与意义 | 研究目标与价值 |
| research_status | 研究现状 | 当前领域研究进展 |
| research_questions | 研究问题 | 核心研究问题 |
| basic_theory | 基本理论 | 理论基础与框架 |
| research_methods | 研究方法 | 实验模型、测试手段、参数范围 |
| results_and_evaluation | 结果与评价 | 实验结果与评估 |
| innovation_points | 创新点 | 核心创新与贡献 |
| limitations_and_suggestions | 局限与建议 | 不足之处与未来方向 |
| conclusions | 结论 | 研究结论与展望 |

#### 文献唯一编号

格式：`{方向缩写}-{作者首字母}-{年份}-{序号}`

示例：
- `NLP-WA-2024-01` — 自然语言处理方向，王某某，2024年，第1篇
- `KG-LI-2023-02` — 知识图谱方向，李某某，2023年，第2篇

内置30个研究方向缩写映射（ML/DL/NLP/CV/KG/GNN/LLM/MM等）。

#### 双介质存储

```
文献入库 → AI 11维度拆分 → 三介质持久化
  ├── 文件库：原始PDF/Word完整文献
  ├── 结构化数据库：单文献单行·11维度数据表 + 唯一编号
  └── 向量存储器：原文向量 + 11维结构化向量，绑定同编号
```

---

### 3.2 11维度数据显示器

**合并模块**：原"文献维度拆分" + "文献对比表格" → 统一可视化入口

#### 单篇详情模式

- 选择一篇论文 → 展示11维度展开/折叠视图
- 预览/确认流程：AI拆分先预览，用户确认后存库
- 维度填充进度条（已填充/11）
- 每个维度支持一键复制
- 来源标识：🟢 已存储（数据库） / 🟡 预览中（未存库）

#### 多篇对比模式

- 勾选多篇论文 → 生成横向对比表格
- 默认8列：标题/作者/年份 + 4个关键维度
- 支持自定义AI列（如"方法论评分"、"与自身研究关联度"）
- 11维度字段零LLM调用直接填充，AI列按需调用
- 支持导出CSV/Excel

---

### 3.3 论文全流程撰写工作台

**合并模块**：原"AI写作工作台" + "文献综述工作台" → 统一写作入口

#### 文献综述模式（4步工作流）

1. **选择文献** — 从库中勾选论文 + 输入综述主题
2. **生成大纲** — AI基于11维度数据生成结构化大纲（可编辑JSON）
3. **流式写作** — SSE实时生成各章节内容，按维度精准引用
4. **完成导出** — 预览全文，导出Markdown

**维度精准引用**：
- 引言 → 调取研究背景/目的/现状
- 方法 → 调取研究方法/基本理论
- 结果 → 调取结果评价/创新点
- 讨论 → 调取局限建议/结论

#### AI写作模式

- 学术润色（polish_text）
- 学术改写（rewrite_text）
- 文本扩写（expand_text）
- 文本缩写（shrink_text）
- 学术翻译（translate_text）
- 格式化引用（format_citation）

---

### 3.4 AI白板头脑风暴（Excalidraw深度融合）

**深度融合**：AI头脑风暴功能直接嵌入Excalidraw白板，而非独立组件

#### 白板功能

- 完整Excalidraw编辑能力：手绘、文本、形状、箭头、图片
- 桌面端顶部横向工具栏
- 支持导出/导入 `.excalidraw` 文件
- 深色/浅色主题自动切换
- 中文界面

#### 文献导入白板

- 左侧侧边栏选择论文 → 点击「导入到白板」
- 自动在画布上生成文献卡片（紫色边框矩形）
- 卡片内容：标题、作者/年份/期刊、摘要、文献编号
- 自动定位到新内容（scrollToContent）

#### AI头脑风暴

- 选择2+篇论文 + 可选聚焦方向
- SSE流式生成选题思路
- 点击「渲染到白板」→ 自动在画布上生成结构化思维导图
- 标题用橙色矩形高亮，条目用缩进文本
- 支持导出Markdown

---

### 3.5 DBLP会议论文检索

- 三种搜索模式：关键词/作者/会议
- 热门CS会议分类标签（AI/ML/NLP/CV/SE等）
- 年份范围筛选
- 一键导入到文献库（自动触发11维度拆分）
- 批量导入支持

---

### 3.6 PDF阅读与标注

- PDF在线阅读，支持缩放/翻页
- 文本选择 → AI划线辅助4动作：
  - 💡 **AI解释**（橙色）— 解释选中文本含义
  - 🌐 **翻译**（蓝色）— 翻译为中文
  - ✏️ **改写**（紫色）— 学术改写
  - 📋 **总结**（绿色）— 核心要点总结
- PDF全文提取与AI分析
- 标注工具（高亮/下划线/矩形）
- Zotero文献库集成

---

### 3.7 学术Agent

- 上下文感知AI助手
- 自动获取当前面板的论文信息
- 多轮对话，支持追问
- 技能面板：论文问答、摘要生成、关键词提取、方法论分析
- 模块化执行：RAG检索增强生成

---

### 3.8 AI参考文献提取

- 从PDF全文自动定位参考文献部分
- AI解析为结构化数据（authors/title/year/journal/doi/type）
- 支持四种格式输出：
  - **GB/T 7714** — 中国国标格式
  - **APA** — 美国心理学会格式
  - **IEEE** — 电气电子工程师格式
  - **Raw** — 原始结构化数据

---

### 3.9 监控与数据看板

- 系统运行状态监控
- 文献库统计图表
- AI调用次数/耗时统计
- Zotero连接状态

---

## 四、数据安全

### API密钥加密存储

- AES-256-GCM加密算法
- PBKDF2密钥派生（600,000次迭代，符合OWASP推荐）
- Master Key自动生成并持久化
- 密钥掩码显示（`sk-y...nwve`）
- 支持密钥轮换

### 安全中间件

- CORS跨域保护
- 请求体大小限制（10MB）
- 速率限制（300次/分钟）

---

## 五、AI提示词体系

### 批量多篇文献通用提示词（系统自动调用）

```
你是科研文献解析专家，对批量传入的多篇学术论文进行标准化11维度结构化拆解：
1. 输出格式：一篇文献对应一行表格数据，11列严格匹配预设维度
2. 内容规则：提炼关键信息，精简凝练，不摘抄大段原文
3. 数据绑定：每篇附带基础信息（作者、年份、期刊）
4. 批量处理：多份文献分行输出，缺失标注【无】
```

### 单篇精细化拆解提示词（用户手动触发）

```
针对当前单篇文献深度拆解11个维度：
1. 研究缺口、创新点优先提炼作者文中提出的不足与未来方向
2. 方法维度细化：实验模型、测试手段、参数范围
3. 结论维度区分正向成果与局限性
4. 输出适配数据库入库格式
```

### 头脑风暴提示词

```
基于多篇文献的11维度结构化数据，开展科研选题头脑风暴：
1. 横向对比研究方向、方法、现存缺陷
2. 梳理研究空白、未解决问题、方法改进空间
3. 输出3~5个可行新研究选题，附选题依据（文献编号）
4. 支持分层思维导图格式
```

---

## 六、API接口一览

### 文献管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/papers` | GET | 文献列表（分页/排序/搜索） |
| `/api/papers` | POST | 创建文献（**自动拆分+自动编号**） |
| `/api/papers/{id}` | GET/PUT/DELETE | 文献CRUD |
| `/api/papers/batch` | POST | 批量导入（**自动拆分+自动编号**） |
| `/api/papers/batch-split` | POST | 批量补拆分/重新拆分 |
| `/api/papers/{id}/dimensions` | GET/POST | 获取/创建维度数据 |
| `/api/papers/{id}/dimensions/preview` | POST | 预览拆分（不存库） |
| `/api/papers/{id}/dimensions/confirm` | POST | 确认存储预览数据 |

### AI服务

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/ai/config` | GET/POST | AI配置管理 |
| `/api/ai/test` | POST | 测试AI连接 |
| `/api/ai/providers` | GET | 可用提供商列表 |
| `/api/ai/models/{provider}` | GET | 提供商模型列表 |

### 文献综述

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/literature-review/outline` | POST | 生成综述大纲 |
| `/api/literature-review/section` | POST | 按章节写作 |
| `/api/literature-review/generate` | POST | SSE流式生成完整综述 |

### 文献表格

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/literature-table/generate` | POST | 生成对比表格 |
| `/api/literature-table/export` | POST | 导出CSV |

### 参考文献提取

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/citations/extract` | POST | AI提取参考文献 |

### AI白板头脑风暴

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/brainstorm/generate` | POST | 生成头脑风暴 |
| `/api/brainstorm/generate/stream` | POST | SSE流式生成 |

### DBLP检索

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/dblp/search` | GET | 关键词搜索 |
| `/api/dblp/author/{name}` | GET | 作者搜索 |
| `/api/dblp/conferences` | GET | 会议列表 |
| `/api/dblp/conference-papers` | GET | 会议论文 |
| `/api/dblp/import` | POST | 导入到文献库 |

### PDF服务

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/pdf/proxy` | GET | PDF代理访问 |
| `/api/pdf/extract-text` | POST | PDF文本提取 |

### Zotero集成

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/zotero/status` | GET | 连接状态 |
| `/api/zotero/collections` | GET | 文献集合 |
| `/api/zotero/items` | GET | 文献条目 |
| `/api/zotero/items/{key}/pdf` | GET | PDF附件 |

---

## 七、项目结构

```
AcaSight/
├── frontend/                    # 前端（React + TypeScript + Vite）
│   ├── src/
│   │   ├── components/
│   │   │   ├── Agent/           # AI助手（AgentPanel, ContextualAgentBar）
│   │   │   ├── Brainstorm/      # AI头脑风暴（已融入白板）
│   │   │   ├── Charts/          # 数据图表（ChartPanel）
│   │   │   ├── DimensionDisplay/# 11维度数据显示器（合并版）
│   │   │   ├── Layout/          # 主布局（ObsidianLayout）
│   │   │   ├── Monitor/         # 系统监控（MonitoringDashboard）
│   │   │   ├── Papers/          # 论文维度视图（PaperDimensionView）
│   │   │   ├── Views/           # 编辑器/文件浏览器
│   │   │   ├── Whiteboard/      # Excalidraw白板（融合AI头脑风暴）
│   │   │   ├── Writing/         # AI写作面板
│   │   │   └── WritingWorkbench/# 论文撰写工作台（合并版）
│   │   ├── contexts/            # React Context（AppContext, PanelContext）
│   │   ├── hooks/               # 自定义Hooks
│   │   ├── i18n/                # 国际化（中/英）
│   │   ├── services/            # API服务层
│   │   └── store/               # Zustand状态管理
│   └── package.json
│
├── backend/                     # 后端（FastAPI + SQLAlchemy）
│   ├── app/
│   │   ├── models/              # 数据模型
│   │   │   ├── paper.py         # 文献模型（含paper_code唯一编号）
│   │   │   └── paper_dimensions.py  # 11维度模型
│   │   ├── routers/             # API路由
│   │   │   ├── papers.py        # 文献管理（含强制拆分）
│   │   │   ├── dblp.py          # DBLP检索
│   │   │   ├── citations.py     # 参考文献提取
│   │   │   ├── literature_table.py   # 文献对比表格
│   │   │   ├── literature_review.py  # 文献综述生成
│   │   │   ├── brainstorm.py    # AI头脑风暴
│   │   │   ├── ai_config.py     # AI配置管理
│   │   │   └── ...              # PDF/Zotero/Agent等
│   │   ├── services/            # 业务逻辑
│   │   │   ├── ai_service.py    # AI服务（多提供商路由）
│   │   │   ├── dimension_service.py  # 维度拆分（批量/精细/预览）
│   │   │   ├── dblp_service.py  # DBLP检索服务
│   │   │   ├── crypto.py        # 密钥加密管理
│   │   │   └── paper_code_service.py # 文献编号生成
│   │   └── database.py          # 数据库配置
│   └── data/
│       ├── acasight.db          # SQLite数据库
│       ├── ai_config.json       # AI配置
│       └── .master_key          # 加密主密钥
│
└── COLLABORATION.md             # 协作规范
```

---

## 八、工作流全景

```
用户操作三入口
  ├── 1. 本地上传文献
  ├── 2. 文献检索导入（DBLP/Semantic Scholar）
  └── 3. 在线抓取（DOI/URL）
         │
         ▼
  强制默认：AI执行11维度自动拆分
  （支持批量多篇文献并行拆解）
         │
         ▼
  双介质持久化存储
  ├── 文件库：原始完整文献原文
  ├── 结构化数据库：单文献单行·11维度 + 唯一编号
  └── 向量存储器：原文向量 + 结构化向量，绑定同编号
         │
         ├─→ 论文撰写工作台（AI写作 + 文献综述）
         ├─→ 11维度数据显示器（单篇详情 + 多篇对比）
         ├─→ AI白板头脑风暴（Excalidraw + 文献导入）
         └─→ 文献智能检索（RAG语义检索 + 维度筛选）
```

---

## 九、部署说明

### 环境要求

- Python 3.12+
- Node.js 18+
- SQLite（默认）或 PostgreSQL

### 快速启动

```bash
# 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 前端
cd frontend
npm install
npm run dev
```

### 访问地址

- 前端：http://localhost:5173/
- 后端API：http://localhost:8000/
- API文档：http://localhost:8000/docs

### AI配置

首次使用需在设置页面配置AI提供商的API Key。推荐使用SiliconFlow（国内访问稳定，免费额度充足）。

---

## 十、版本信息

- **当前版本**：v2.0
- **核心特性**：AI 11维度强制拆分 + 文献双存储 + 模块合并 + Excalidraw深度融合
- **开发框架**：AcaSight COLLABORATION.md v7.0
