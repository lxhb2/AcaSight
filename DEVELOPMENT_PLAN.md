# AcaSight 学术视界 - 详细开发方案

## 一、开发阶段规划

### 阶段一：基础架构搭建（第1-2周）

#### 1.1 项目初始化
- [ ] 创建 Monorepo 结构
- [ ] 配置 TypeScript + Python 开发环境
- [ ] 设置 ESLint + Prettier + Black 代码规范
- [ ] 配置 Git 工作流

#### 1.2 前端架构
- [ ] Electron 主进程 + 渲染进程架构
- [ ] React 18 + TypeScript 配置
- [ ] 状态管理（Zustand）
- [ ] 路由系统（React Router）
- [ ] UI 组件库搭建（基于 Uiverse）
- [ ] 主题系统（浅色/深色/跟随系统）

#### 1.3 后端架构
- [ ] FastAPI 项目结构
- [ ] 数据库模型设计（SQLAlchemy）
- [ ] 配置管理系统
- [ ] 日志系统
- [ ] 错误处理中间件

#### 1.4 数据库设计
```sql
-- 核心表结构
- users (用户表)
- papers (文献表)
- collections (收藏夹表)
- tags (标签表)
- notes (笔记表)
- annotations (批注表)
- search_history (搜索历史表)
- ai_conversations (AI对话表)
```

### 阶段二：核心功能开发（第3-6周）

#### 2.1 文献管理模块
- [ ] Zotero 数据库读取集成
- [ ] 本地文献扫描与导入
- [ ] 文献元数据解析（DOI/标题/作者/摘要）
- [ ] 文献分类与标签系统
- [ ] 全文检索（SQLite FTS + Qdrant）

#### 2.2 PDF 阅读器
- [ ] PDF.js 集成与优化
- [ ] 页面渲染与缓存
- [ ] 文本选择与高亮
- [ ] 批注功能（高亮/下划线/笔记）
- [ ] 目录导航
- [ ] 缩放与滚动优化

#### 2.3 AI 对话系统
- [ ] 多模型支持（OpenAI/DeepSeek/Claude/Ollama）
- [ ] 上下文管理
- [ ] 文献上下文注入
- [ ] 流式响应
- [ ] 对话历史保存

#### 2.4 笔记系统
- [ ] Markdown 编辑器
- [ ] 双链笔记功能
- [ ] 文献关联笔记
- [ ] 笔记搜索
- [ ] 导出功能

### 阶段三：学术写作功能（第7-9周）

#### 3.1 六步写作法
- [ ] 题目输入与验证
- [ ] 资料上传与管理
- [ ] 文献选择与引用
- [ ] AI 摘要生成
- [ ] 大纲编辑器（可视化拖拽）
- [ ] 模块化撰写

#### 3.2 写作辅助
- [ ] 实时语法检查
- [ ] 学术用语建议
- [ ] 引用格式自动转换（APA/MLA/GB/T 7714）
- [ ] 查重提示
- [ ] 版本历史

### 阶段四：高级功能（第10-13周）

#### 4.1 文献综述
- [ ] 智能综述生成
- [ ] 研究脉络梳理
- [ ] 对比分析矩阵
- [ ] 趋势分析图表

#### 4.2 数据分析
- [ ] 数据导入（Excel/CSV）
- [ ] 描述统计
- [ ] 可视化图表（ECharts）
- [ ] AI 数据解读

#### 4.3 实验设计
- [ ] 实验方案模板
- [ ] 变量设计工具
- [ ] 样本量计算
- [ ] 随机化工具

### 阶段五：扩展功能（第14-16周）

#### 5.1 PPT 生成
- [ ] Markdown 转 PPT
- [ ] 学术模板库
- [ ] AI 内容生成
- [ ] 图表自动插入

#### 5.2 OCR 识别
- [ ] PDF 文字识别
- [ ] 图片文字提取
- [ ] 公式识别（LaTeX）
- [ ] 表格识别

#### 5.3 手绘白板
- [ ] 自由绘制
- [ ] 图形工具
- [ ] 协作功能
- [ ] 导出功能

---

## 二、技术实现细节

### 2.1 前端技术栈

```typescript
// 核心技术
- Electron 28+
- React 18 + TypeScript 5
- Vite (构建工具)
- Tailwind CSS (样式)
- shadcn/ui (组件库)
- Zustand (状态管理)
- React Query (数据获取)
- React Router (路由)

// 编辑器
- Monaco Editor (代码/文本编辑)
- Milkdown (Markdown 编辑)
- Tiptap (富文本编辑)

// 可视化
- ECharts (图表)
- Fabric.js (白板)
- React Flow (流程图)

// PDF
- PDF.js (PDF 渲染)
- react-pdf (React 封装)
```

### 2.2 后端技术栈

```python
# 核心框架
- FastAPI 0.100+
- Uvicorn (ASGI 服务器)
- SQLAlchemy 2.0 (ORM)
- Alembic (数据库迁移)

# 数据库
- SQLite (本地开发)
- PostgreSQL (生产环境)
- Qdrant (向量数据库)
- Redis (缓存)

# AI 服务
- LangChain (LLM 编排)
- OpenAI API
- DeepSeek API
- Ollama (本地模型)

# 工具库
- PyPDF2 / pdfplumber (PDF 处理)
- Pandas (数据分析)
- OpenPyXL (Excel 处理)
- python-pptx (PPT 生成)
```

### 2.3 API 设计

```yaml
# 核心 API 端点

# 文献管理
GET    /api/papers              # 获取文献列表
POST   /api/papers              # 导入文献
GET    /api/papers/{id}         # 获取文献详情
PUT    /api/papers/{id}         # 更新文献
DELETE /api/papers/{id}         # 删除文献
POST   /api/papers/search       # 搜索文献

# AI 对话
POST   /api/chat                # 发送消息
GET    /api/chat/{id}           # 获取对话历史
DELETE /api/chat/{id}           # 删除对话

# 笔记
GET    /api/notes               # 获取笔记列表
POST   /api/notes               # 创建笔记
PUT    /api/notes/{id}          # 更新笔记
DELETE /api/notes/{id}          # 删除笔记

# 写作
POST   /api/writing/outline     # 生成大纲
POST   /api/writing/draft       # 生成草稿
POST   /api/writing/polish      # 润色文本

# 文件
POST   /api/files/upload        # 上传文件
GET    /api/files/{id}          # 下载文件
```

---

## 三、数据库设计

### 3.1 ER 图

```
[User] 1--* [Paper]
[User] 1--* [Collection]
[User] 1--* [Note]
[User] 1--* [AIConversation]

[Paper] 1--* [Annotation]
[Paper] 1--* [Note]
[Paper] *--* [Tag]
[Paper] *--* [Collection]

[Collection] 1--* [Collection] (自关联，子收藏夹)

[Note] *--* [Note] (双链关联)
[Note] *--* [Paper]

[AIConversation] 1--* [AIMessage]
```

### 3.2 核心表结构

```sql
-- 用户表
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    password_hash VARCHAR(255),
    avatar_url VARCHAR(255),
    preferences JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文献表
CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(500) NOT NULL,
    authors JSON,
    abstract TEXT,
    doi VARCHAR(100),
    pmid VARCHAR(20),
    arxiv_id VARCHAR(50),
    journal VARCHAR(200),
    year INTEGER,
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    pdf_path VARCHAR(500),
    file_size INTEGER,
    page_count INTEGER,
    metadata JSON,
    vector_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 收藏夹表
CREATE TABLE collections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES collections(id),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文献-收藏夹关联表
CREATE TABLE paper_collections (
    paper_id INTEGER REFERENCES papers(id),
    collection_id INTEGER REFERENCES collections(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (paper_id, collection_id)
);

-- 标签表
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    color VARCHAR(7) DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文献-标签关联表
CREATE TABLE paper_tags (
    paper_id INTEGER REFERENCES papers(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (paper_id, tag_id)
);

-- 笔记表
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    paper_id INTEGER REFERENCES papers(id),
    title VARCHAR(200),
    content TEXT,
    content_type VARCHAR(20) DEFAULT 'markdown',
    backlinks JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 批注表
CREATE TABLE annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER REFERENCES papers(id),
    user_id INTEGER REFERENCES users(id),
    page INTEGER NOT NULL,
    type VARCHAR(20) NOT NULL, -- highlight, underline, note, strike
    rect JSON, -- 位置信息 {x, y, width, height}
    color VARCHAR(7) DEFAULT '#fbbf24',
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI 对话表
CREATE TABLE ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    paper_id INTEGER REFERENCES papers(id),
    title VARCHAR(200),
    model VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI 消息表
CREATE TABLE ai_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES ai_conversations(id),
    role VARCHAR(20) NOT NULL, -- user, assistant, system
    content TEXT NOT NULL,
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 搜索历史表
CREATE TABLE search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    query VARCHAR(500) NOT NULL,
    source VARCHAR(50), -- local, zotero, semanticscholar, openalex
    result_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 四、关键功能实现

### 4.1 Zotero 集成

```python
# zotero_service.py
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

class ZoteroService:
    def __init__(self, zotero_db_path: str):
        self.db_path = zotero_db_path
    
    def get_all_items(self) -> List[Dict]:
        """获取所有文献条目"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT items.itemID, items.key, itemTypes.typeName,
                   itemDataValues.value
            FROM items
            JOIN itemTypes ON items.itemTypeID = itemTypes.itemTypeID
            LEFT JOIN itemData ON items.itemID = itemData.itemID
            LEFT JOIN fields ON itemData.fieldID = fields.fieldID
            LEFT JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
            WHERE items.itemID NOT IN (SELECT itemID FROM deletedItems)
        """)
        
        items = {}
        for row in cursor.fetchall():
            item_id, key, item_type, value = row
            if item_id not in items:
                items[item_id] = {
                    'itemID': item_id,
                    'key': key,
                    'itemType': item_type,
                    'fields': {}
                }
            # 解析字段...
        
        conn.close()
        return list(items.values())
    
    def get_attachments(self, item_id: int) -> List[Dict]:
        """获取文献附件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT itemAttachments.path, itemAttachments.contentType
            FROM itemAttachments
            WHERE itemAttachments.parentItemID = ?
        """, (item_id,))
        
        attachments = []
        for row in cursor.fetchall():
            path, content_type = row
            attachments.append({
                'path': path,
                'contentType': content_type
            })
        
        conn.close()
        return attachments
```

### 4.2 文献搜索 API 集成

```python
# search_service.py
import httpx
from typing import List, Dict, Optional

class LiteratureSearchService:
    def __init__(self):
        self.clients = {
            'openalex': OpenAlexClient(),
            'semanticscholar': SemanticScholarClient(),
            'crossref': CrossrefClient(),
            'europepmc': EuropePMCClient(),
            'arxiv': ArxivClient()
        }
    
    async def search_all(self, query: str, limit: int = 20) -> Dict[str, List]:
        """并行搜索多个数据源"""
        results = {}
        
        async with httpx.AsyncClient() as client:
            tasks = [
                self.clients['openalex'].search(client, query, limit),
                self.clients['semanticscholar'].search(client, query, limit),
                self.clients['crossref'].search(client, query, limit),
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for source, response in zip(['openalex', 'semanticscholar', 'crossref'], responses):
                if isinstance(response, Exception):
                    results[source] = {'error': str(response)}
                else:
                    results[source] = response
        
        return results

class OpenAlexClient:
    BASE_URL = "https://api.openalex.org"
    
    async def search(self, client: httpx.AsyncClient, query: str, limit: int = 20) -> List[Dict]:
        response = await client.get(
            f"{self.BASE_URL}/works",
            params={"search": query, "per-page": limit}
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_work(w) for w in data.get('results', [])]
    
    def _format_work(self, work: Dict) -> Dict:
        return {
            'id': work.get('id'),
            'title': work.get('display_name'),
            'authors': [a['author']['display_name'] for a in work.get('authorships', [])],
            'year': work.get('publication_year'),
            'doi': work.get('doi'),
            'abstract': work.get('abstract'),
            'cited_by_count': work.get('cited_by_count'),
            'open_access': work.get('open_access', {}).get('is_oa', False),
            'pdf_url': work.get('open_access', {}).get('oa_url')
        }

class SemanticScholarClient:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    
    async def search(self, client: httpx.AsyncClient, query: str, limit: int = 20) -> List[Dict]:
        response = await client.get(
            f"{self.BASE_URL}/paper/search",
            params={
                "query": query,
                "fields": "title,authors,year,citationCount,abstract,openAccessPdf",
                "limit": limit
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return [self._format_paper(p) for p in data.get('data', [])]
    
    def _format_paper(self, paper: Dict) -> Dict:
        return {
            'id': paper.get('paperId'),
            'title': paper.get('title'),
            'authors': [a['name'] for a in paper.get('authors', [])],
            'year': paper.get('year'),
            'doi': paper.get('externalIds', {}).get('DOI'),
            'abstract': paper.get('abstract'),
            'cited_by_count': paper.get('citationCount'),
            'pdf_url': paper.get('openAccessPdf', {}).get('url')
        }
```

### 4.3 RAG 系统实现

```python
# rag_service.py
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Qdrant
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI
import qdrant_client

class RAGService:
    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        self.client = qdrant_client.QdrantClient(host=qdrant_host, port=qdrant_port)
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    async def index_paper(self, paper_id: str, text: str):
        """索引文献到向量数据库"""
        chunks = self.text_splitter.split_text(text)
        
        # 创建或获取集合
        collection_name = f"paper_{paper_id}"
        
        # 存储向量
        self.client.upsert(
            collection_name=collection_name,
            points=[
                {
                    'id': i,
                    'vector': self.embeddings.embed_query(chunk),
                    'payload': {'text': chunk, 'index': i}
                }
                for i, chunk in enumerate(chunks)
            ]
        )
    
    async def query(self, paper_id: str, question: str, k: int = 5) -> str:
        """基于文献内容回答问题"""
        collection_name = f"paper_{paper_id}"
        
        # 检索相关片段
        query_vector = self.embeddings.embed_query(question)
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=k
        )
        
        context = "\n".join([r.payload['text'] for r in results])
        
        # 构建提示
        prompt = f"""基于以下文献内容回答问题：

文献内容：
{context}

问题：{question}

请用中文回答，并引用相关段落。"""
        
        # 调用 LLM
        llm = OpenAI(temperature=0.3)
        return llm.predict(prompt)
```

### 4.4 AI 对话系统

```python
# ai_service.py
from typing import AsyncGenerator, List, Dict
import openai
import httpx

class AIService:
    def __init__(self):
        self.providers = {
            'openai': OpenAIProvider(),
            'deepseek': DeepSeekProvider(),
            'claude': ClaudeProvider(),
            'ollama': OllamaProvider()
        }
    
    async def chat(
        self,
        provider: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False
    ) -> AsyncGenerator[str, None]:
        """AI 对话，支持流式输出"""
        provider_impl = self.providers.get(provider)
        if not provider_impl:
            raise ValueError(f"Unknown provider: {provider}")
        
        if stream:
            async for chunk in provider_impl.chat_stream(messages, model):
                yield chunk
        else:
            response = await provider_impl.chat(messages, model)
            yield response

class OpenAIProvider:
    def __init__(self):
        self.client = openai.AsyncOpenAI()
    
    async def chat(self, messages: List[Dict], model: str = "gpt-4") -> str:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        return response.choices[0].message.content
    
    async def chat_stream(self, messages: List[Dict], model: str = "gpt-4") -> AsyncGenerator[str, None]:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    async def chat(self, messages: List[Dict], model: str = "llama2") -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False}
            )
            return response.json()['message']['content']
    
    async def chat_stream(self, messages: List[Dict], model: str = "llama2") -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if 'message' in data and 'content' in data['message']:
                            yield data['message']['content']
```

---

## 五、开发环境配置

### 5.1 前端环境

```bash
# 创建前端项目
cd AcaSight/frontend
npm init -y

# 安装核心依赖
npm install react react-dom typescript @types/react @types/react-dom
npm install vite @vitejs/plugin-react
npm install electron electron-builder
npm install tailwindcss postcss autoprefixer
npm install zustand react-router-dom @tanstack/react-query
npm install @monaco-editor/react milkdown @tiptap/react
npm install recharts fabric react-flow-renderer

# 安装开发依赖
npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install -D prettier eslint-config-prettier
npm install -D @types/node
```

### 5.2 后端环境

```bash
# 创建后端项目
cd AcaSight/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install fastapi uvicorn[standard]
pip install sqlalchemy alembic sqlite3
pip install qdrant-client redis
pip install langchain openai httpx
pip install pypdf2 pdfplumber python-pptx openpyxl
pip install pandas numpy matplotlib
pip install pytest pytest-asyncio black isort mypy

# 保存依赖
pip freeze > requirements.txt
```

### 5.3 数据库初始化

```bash
# 初始化 Alembic
cd backend
alembic init alembic

# 创建初始迁移
alembic revision --autogenerate -m "Initial migration"

# 执行迁移
alembic upgrade head
```

---

## 六、测试策略

### 6.1 单元测试

```python
# test_paper_service.py
import pytest
from app.services.paper_service import PaperService

@pytest.fixture
def paper_service():
    return PaperService()

async def test_create_paper(paper_service):
    paper = await paper_service.create_paper({
        'title': 'Test Paper',
        'authors': ['John Doe'],
        'year': 2024
    })
    assert paper.title == 'Test Paper'
    assert paper.id is not None

async def test_search_papers(paper_service):
    results = await paper_service.search_papers('machine learning')
    assert len(results) > 0
```

### 6.2 集成测试

```python
# test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

async def test_create_paper_api(client):
    response = await client.post("/api/papers", json={
        'title': 'Test Paper',
        'authors': ['John Doe'],
        'year': 2024
    })
    assert response.status_code == 201
    assert response.json()['title'] == 'Test Paper'
```

### 6.3 E2E 测试

```typescript
// e2e/paper.spec.ts
import { test, expect } from '@playwright/test';

test('create paper', async ({ page }) => {
  await page.goto('http://localhost:5173');
  
  await page.click('[data-testid="add-paper-btn"]');
  await page.fill('[data-testid="title-input"]', 'Test Paper');
  await page.click('[data-testid="save-btn"]');
  
  await expect(page.locator('[data-testid="paper-title"]')).toHaveText('Test Paper');
});
```

---

## 七、部署方案

### 7.1 桌面应用打包

```json
// package.json
{
  "name": "acasight",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "electron:dev": "npm run build && electron .",
    "electron:build": "npm run build && electron-builder",
    "electron:build:win": "npm run build && electron-builder --win",
    "electron:build:mac": "npm run build && electron-builder --mac",
    "electron:build:linux": "npm run build && electron-builder --linux"
  },
  "build": {
    "appId": "com.acasight.app",
    "productName": "AcaSight",
    "directories": {
      "output": "dist-electron"
    },
    "files": [
      "dist/**/*",
      "electron/**/*"
    ],
    "mac": {
      "target": ["dmg", "zip"]
    },
    "win": {
      "target": ["nsis", "portable"]
    },
    "linux": {
      "target": ["AppImage", "deb"]
    }
  }
}
```

### 7.2 Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:///data/acasight.db
      - QDRANT_HOST=qdrant
      - REDIS_URL=redis://redis:6379
    depends_on:
      - qdrant
      - redis

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  qdrant_storage:
```

---

## 八、项目里程碑

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1 - 架构完成 | 第2周末 | 可运行的基础框架 |
| M2 - 核心功能 | 第6周末 | PDF阅读 + AI对话 + 文献管理 |
| M3 - 写作功能 | 第9周末 | 六步写作法 + 大纲编辑 |
| M4 - 高级功能 | 第13周末 | 综述生成 + 数据分析 |
| M5 - 扩展功能 | 第16周末 | PPT + OCR + 白板 |
| M6 - 发布 | 第18周末 | v1.0 正式版 |

---

## 九、风险应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| Electron 性能问题 | 中 | 高 | 使用 Web Worker，优化渲染 |
| AI 模型不稳定 | 高 | 中 | 多模型备份，本地模型兜底 |
| 开发进度延迟 | 中 | 中 | 分阶段交付，MVP 优先 |
| 第三方 API 限制 | 中 | 中 | 缓存策略，多源聚合 |

---

*文档版本：v1.0*
*最后更新：2026-05-18*
*状态：开发中*
