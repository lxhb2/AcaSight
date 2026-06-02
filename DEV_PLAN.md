# AcaSight 开发计划

> 更新时间: 2026-05-20 12:59
> 当前阶段: Phase 1 (P0) - AI 论文检索增强

---

## 🎯 Phase 1: AI 论文检索增强 (当前)

**目标**: 将 SearchPage 从 mock 数据改造为真实 API 调用，实现完整检索流程。

### 任务清单

- [x] 后端 6 数据源已就绪 (CORE/OpenAlex/Semantic Scholar/Crossref/Europe PMC/arXiv)
- [x] 后端搜索路由已就绪 (`/api/search/`)
- [ ] **前端 SearchPage 改造** (进行中)
  - [ ] 移除 mock 数据，调用真实 searchApi
  - [ ] 添加数据源选择器（6 个 checkbox）
  - [ ] 多源结果合并与去重
  - [ ] 统一结果展示格式
  - [ ] 添加「保存到 Zotero」按钮
  - [ ] 高级筛选（年份、排序、开放获取）
  - [ ] 加载状态与错误处理
  - [ ] 分页支持

### API 响应格式

```json
{
  "query": "transformer",
  "sources": ["core", "openalex"],
  "results": {
    "core": { "source": "core", "results": [...], "count": 20 },
    "openalex": { "source": "openalex", "results": [...], "count": 20 }
  }
}
```

### 前端统一格式

```typescript
interface UnifiedPaper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  doi?: string;
  journal?: string;
  cited_by_count?: number;
  is_open_access: boolean;
  pdf_url?: string;
  source: string;
  source_id?: string; // arXiv ID, PMID, etc.
}
```

---

## 📊 Phase 2: 数据处理 + 绘图模块

**三种模式**:
1. **纯手动** - Plotly.js 交互式图表编辑器
2. **全自动** - 上传数据 → Skill → 自动生成图表
3. **半自动** - AI 对话引导逐步生成

**依赖**: 等待用户提供绘图 Skill

---

## 🤖 Phase 3: 最小化 Agent Core

- 系统提示词管理
- 任务规划引擎
- Skill 路由

---

## 🔮 未来功能 (P2+)

| 功能 | 技术方案 | 优先级 |
|------|----------|--------|
| PPT 生成 Skill | python-pptx | P2 |
| OnlyOffice 嵌入 | iframe + Document Server | P2 |
| Tauri 桌面应用 | Rust + WebView | 未来 |
| 内置浏览器 | Tauri webview | 未来 |
| SciDAVis 外部调用 | 导出数据 → 命令行调用 | 未来 |

---

## 📁 项目结构

```
AcaSight/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── search.py      ✅ 6源搜索就绪
│   │   │   ├── zotero.py      ✅ MCP代理就绪
│   │   │   └── ...
│   │   └── services/
│   │       └── search_service.py  ✅ 完整实现
├── frontend/
│   └── src/
│       ├── components/
│       │   └── Search/
│       │       └── SearchPage.tsx  🔄 改造中
│       └── services/
│           └── api.ts        ✅ searchApi 已定义
└── DEV_PLAN.md              本文件
```

---

## 🏃 当前进度

```
Phase 1 ████████████░░░░  60%
Phase 2 ░░░░░░░░░░░░░░░░   0%
Phase 3 ░░░░░░░░░░░░░░░░   0%
```
