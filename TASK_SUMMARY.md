# AcaSight 学术视界 - 开发方案与材料准备

## 已完成工作

### 1. 项目规划文档
- ✅ `AcaSight_Project_Overview.md` - 项目概述与架构设计
- ✅ `DEVELOPMENT_PLAN.md` - 详细开发方案（16周计划）
- ✅ `README.md` - 项目说明文档

### 2. 前端准备
- ✅ `frontend/package.json` - 依赖配置
  - Electron 28 + React 18 + TypeScript 5
  - Tailwind CSS + shadcn/ui
  - Monaco Editor + PDF.js + ECharts
  - Zustand + React Query + React Router

### 3. 后端准备
- ✅ `backend/requirements.txt` - Python 依赖
  - FastAPI + SQLAlchemy + Alembic
  - Qdrant + Redis
  - LangChain + OpenAI
  - PyPDF2 + pdfplumber
  - pandas + numpy

- ✅ `backend/app/main.py` - FastAPI 主应用
  - 生命周期管理
  - 中间件配置
  - 路由注册
  - 全局异常处理

- ✅ `backend/app/config.py` - 配置管理
  - 环境变量支持
  - 多模型配置
  - 数据库配置

- ✅ `backend/app/database.py` - 数据库管理
  - SQLAlchemy 异步引擎
  - 会话管理
  - 表创建

### 4. 核心服务
- ✅ `backend/app/services/search_service.py` - 文献搜索服务
  - OpenAlex 客户端
  - Semantic Scholar 客户端
  - Crossref 客户端
  - Europe PMC 客户端
  - arXiv 客户端
  - 并行搜索聚合

- ✅ `backend/app/services/ai_service.py` - AI 服务
  - OpenAI 提供商
  - DeepSeek 提供商
  - Claude 提供商
  - Ollama 本地模型
  - 流式输出支持

### 5. API 路由
- ✅ `backend/app/routers/search.py` - 搜索路由
- ✅ `backend/app/routers/chat.py` - AI 对话路由

### 6. 数据模型
- ✅ `backend/app/models/paper.py` - 文献模型
- ✅ `backend/app/models/__init__.py` - 模型导出

## 技术架构

```
AcaSight/
├── frontend/          # Electron + React + TypeScript
│   ├── package.json
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── stores/
│       └── utils/
│
├── backend/           # FastAPI + Python
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       ├── routers/
│       ├── services/
│       └── utils/
│
└── docs/
    ├── PROJECT_OVERVIEW.md
    ├── DEVELOPMENT_PLAN.md
    └── README.md
```

## 核心功能模块

### 已实现
1. **多源文献搜索** - 聚合 OpenAlex, Semantic Scholar, Crossref, Europe PMC, arXiv
2. **AI 对话系统** - 支持 OpenAI, DeepSeek, Claude, Ollama
3. **数据库架构** - SQLite + SQLAlchemy + Alembic

### 待实现
1. Zotero 集成
2. PDF 阅读器
3. 笔记系统
4. 学术写作助手
5. 文献综述生成
6. PPT 生成
7. OCR 识别
8. 手绘白板

## 开发计划

| 阶段 | 时间 | 内容 |
|------|------|------|
| 阶段一 | 第1-2周 | 基础架构搭建 |
| 阶段二 | 第3-6周 | 核心功能开发 |
| 阶段三 | 第7-9周 | 学术写作功能 |
| 阶段四 | 第10-13周 | 高级功能 |
| 阶段五 | 第14-16周 | 扩展功能 |

## 下一步行动

1. **初始化项目**
   ```bash
   cd AcaSight/frontend && npm install
   cd ../backend && python -m venv venv && pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp backend/.env.example backend/.env
   # 编辑 .env 文件，添加 API 密钥
   ```

3. **启动开发服务器**
   ```bash
   # 终端1：后端
   cd backend && uvicorn app.main:app --reload
   
   # 终端2：前端
   cd frontend && npm run dev
   ```

4. **开始编码**
   - 实现前端页面组件
   - 完善后端 API
   - 集成 Zotero
   - 开发 PDF 阅读器

---

*文档版本：v1.0*
*最后更新：2026-05-18*
*状态：开发准备完成，等待开始编码*
