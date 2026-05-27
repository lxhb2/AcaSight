# AcaSight 2.0 一站式科研学术综合平台 — 重构计划

> 日期: 2026-05-25
> 目标: 融合 Obsidian/UPDF/Origin/Zotero 核心体验的一站式科研桌面应用

---

## 五大模块开发计划

### 模块一: 全局 UI 玻璃浮雕 + 圆角统一 (GLASS)

**文件变更:**
- `frontend/src/index.css` — 新增 glass morphism CSS 变量和类
- `frontend/src/components/Layout/ObsidianLayout.tsx` — 容器样式替换
- 所有子组件 — 方框→圆角矩形

**CSS 新增:**
```css
/* 玻璃浮雕系统 */
:root {
  --glass-bg: rgba(30, 30, 46, 0.72);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: 16px;
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.28);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
}
.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  border-radius: var(--radius-lg);
}
```

**规则:** 科研绘图(ChartPanel)保留方框，其余全部圆角。

---

### 模块二: 本地论文数据库 CRUD (DB)

**后端新增/修改:**
- `backend/app/routers/storage.py` — 新增 DELETE/PUT/手动入库端点
- `backend/app/routers/papers.py` — 新建，完整的论文 CRUD API
- `backend/app/models/paper.py` — 已有，补充 tag/outline 查询方法

**前端新增:**
- `frontend/src/components/Library/PaperDatabase.tsx` — 论文数据库管理面板
- `frontend/src/components/Library/TagManager.tsx` — 标签管理组件
- `frontend/src/components/Library/OutlinePanel.tsx` — 大纲目录组件

**API 设计:**
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

---

### 模块三: PDF 阅读器升级 (PDF)

**前端修改:**
- `ObsidianLayout.tsx` 中的 PDF 渲染区 — 新增文本选择层
- `frontend/src/hooks/useTextSelection.ts` — 已有，增强单击选词

**核心改进:**
1. 单击选中文本 → TextLayer 点击事件优化
2. 批注功能完善 → 高亮/下划线/文本批注/图形标注
3. 批注持久化 → 后端存储 + 前端渲染

**后端新增:**
- `backend/app/routers/pdf.py` — 新增批注 CRUD 端点
- `backend/app/models/paper.py` — Annotation 模型已有

---

### 模块四: AI Agent 多会话重构 (AGENT)

**前端全新:**
- `frontend/src/components/Agent/MultiSessionAgent.tsx` — 多会话界面
- `frontend/src/components/Agent/SessionList.tsx` — 会话列表侧栏
- `frontend/src/components/Agent/SessionChat.tsx` — 单会话聊天区
- `frontend/src/store/agentStore.ts` — 重构为多会话 store

**后端增强:**
- `backend/app/agent/router.py` — 新增会话管理端点
- `backend/app/agent/core.py` — 文档读取修复 + 全局文献库检索权限

**新 API:**
```
GET    /api/agent/sessions           — 列出所有会话
POST   /api/agent/sessions           — 创建新会话
DELETE /api/agent/sessions/:id       — 删除会话
GET    /api/agent/sessions/:id       — 获取会话详情+消息
POST   /api/agent/sessions/:id/chat  — 在指定会话中发送消息
POST   /api/agent/upload             — 上传文档供 Agent 读取
```

---

### 模块五: 独立知识图谱界面 (GRAPH)

**前端全新:**
- `frontend/src/components/KnowledgeGraph/KnowledgeGraphPage.tsx` — 图谱主页面
- `frontend/src/components/KnowledgeGraph/GraphCanvas.tsx` — 力导向图渲染(react-force-graph)
- `frontend/src/components/KnowledgeGraph/GraphNode.tsx` — 节点组件
- `frontend/src/components/KnowledgeGraph/GraphSidebar.tsx` — 图谱控制面板

**依赖新增:** `react-force-graph-2d` 或 `@antv/g6`

**后端新增:**
- `backend/app/routers/knowledge_graph.py` — 图谱生成 API
- `backend/app/services/knowledge_graph_service.py` — 图谱构建逻辑

**工作流:**
1. PDF 上传 → 数据清洗本地存储
2. AI Agent 分析内容并关联已有文献
3. 生成同研究方向双链关联图谱
4. 支持拖拽/缩放/点击跳转原文

---

## 开发顺序 (按依赖关系)

1. **Phase 1: UI 玻璃特效** — 纯前端，无后端依赖，最快见效
2. **Phase 2: 数据库 CRUD** — 后端先建 API，前端对接
3. **Phase 3: PDF 阅读器升级** — 依赖 Phase 1 的 UI 风格
4. **Phase 4: Agent 多会话** — 依赖 Phase 2 的数据库
5. **Phase 5: 知识图谱** — 依赖 Phase 2 + Phase 4

每阶段完成后验证构建 + 功能测试。
