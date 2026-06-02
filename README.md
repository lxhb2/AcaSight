# AcaSight 学术视界

> 全能型学术智能体应用 - 为科研人员提供一站式学术工作平台

## 项目简介

AcaSight（学术视界）是一款面向科研人员的全能型学术智能体应用，整合文献管理、AI 辅助阅读、学术写作、数据分析、可视化笔记等功能，帮助研究者高效完成学术工作。

## 核心功能

### 文献管理
- 📚 **Zotero 集成** - 直接读取 Zotero 文献库
- 🔍 **智能搜索** - 聚合 OpenAlex、Semantic Scholar、Crossref 等权威数据源
- 🏷️ **智能分类** - 标签、文件夹、自动分类
- 📎 **全文检索** - 基于内容的深度搜索

### AI 辅助阅读
- 🤖 **AI 对话** - 与文献进行对话式阅读
- 📝 **智能摘要** - 自动提炼核心论点
- 🌐 **多语言翻译** - 实时翻译 + 术语表
- 💡 **研究空白发现** - AI 识别研究空白

### 学术写作
- ✍️ **六步写作法** - 题目 → 资料 → 文献 → 摘要 → 大纲 → 全文
- 📋 **大纲编辑** - 可视化拖拽编辑
- 🔄 **模块化撰写** - 分章节 AI 辅助写作
- 📖 **引用管理** - APA/MLA/GB/T 7714 自动转换

### 高级功能
- 📊 **数据分析** - 统计分析与可视化
- 🔬 **实验设计** - AI 辅助设计实验
- 📑 **文献综述** - 智能综述生成
- 🎯 **PPT 生成** - Markdown 转 PPT
- 🔍 **OCR 识别** - 扫描版 PDF 文字识别
- 🎨 **手绘白板** - 自由绘制与协作

## 技术架构

### 前端
- **Electron** - 桌面应用框架
- **React 18 + TypeScript** - UI 框架
- **Tailwind CSS + shadcn/ui** - 样式系统
- **Monaco Editor** - 代码/文本编辑
- **PDF.js** - PDF 渲染
- **ECharts** - 数据可视化

### 后端
- **FastAPI** - Python Web 框架
- **SQLAlchemy** - ORM
- **SQLite/PostgreSQL** - 关系数据库
- **Qdrant** - 向量数据库
- **Redis** - 缓存

### AI 服务
- **LangChain** - LLM 编排
- **OpenAI / DeepSeek / Claude** - 云端模型
- **Ollama** - 本地模型
- **SPECTER2** - 文献嵌入向量

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.11+
- Git

### 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/acasight.git
cd acasight

# 安装前端依赖
cd frontend
npm install

# 安装后端依赖
cd ../backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 初始化数据库
alembic upgrade head
```

### 运行

```bash
# 开发模式
# 终端 1：启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 终端 2：启动前端
cd frontend
npm run dev

# 启动 Electron
cd frontend
npm run electron:dev
```

### 构建

```bash
# 构建桌面应用
cd frontend
npm run electron:build

# 构建结果在 dist-electron/ 目录
```

## 项目结构

```
AcaSight/
├── frontend/          # Electron + React 前端
│   ├── src/
│   │   ├── components/  # UI 组件
│   │   ├── pages/       # 页面
│   │   ├── hooks/       # 自定义 Hooks
│   │   ├── stores/      # 状态管理
│   │   └── utils/       # 工具函数
│   └── electron/        # Electron 主进程
│
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── models/      # 数据模型
│   │   ├── routers/     # API 路由
│   │   ├── services/    # 业务逻辑
│   │   └── utils/       # 工具函数
│   └── alembic/         # 数据库迁移
│
├── ai/                # AI 服务
│   ├── llm/             # 大模型接口
│   ├── rag/             # RAG 系统
│   └── prompts/         # 提示词模板
│
└── docs/              # 文档
    ├── DEVELOPMENT_PLAN.md
    └── API_DOCUMENTATION.md
```

## 开发计划

| 阶段 | 时间 | 内容 |
|------|------|------|
| 阶段一 | 第1-2周 | 基础架构搭建 |
| 阶段二 | 第3-6周 | 核心功能开发 |
| 阶段三 | 第7-9周 | 学术写作功能 |
| 阶段四 | 第10-13周 | 高级功能 |
| 阶段五 | 第14-16周 | 扩展功能 |

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 致谢

- [Zotero](https://www.zotero.org/) - 文献管理
- [OpenAlex](https://openalex.org/) - 开放学术数据
- [Semantic Scholar](https://www.semanticscholar.org/) - 学术搜索
- [Uiverse](https://uiverse.io/) - UI 组件灵感

---

> 🌟 如果这个项目对你有帮助，请给它一个 Star！
