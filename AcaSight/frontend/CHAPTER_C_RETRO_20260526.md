# Chapter C 技术复盘 — 论文数据库 CRUD

**时间**: 2026-05-26 22:56–23:29 GMT+8 | **版本**: v8.0

## 执行摘要

Chapter C 的**全部四层均已完整实现**：后端模型、CRUD 路由、前端 API 服务层、两个前端组件都已经在生产级代码状态运转。

**实际工作量**: 33 分钟（验证+构建+API 测试）= 预估 6h 的 9.2%

---

## 现状清单

### 后端（Python/FastAPI）

| 组件 | 文件 | 状态 | 说明 |
|------|------|------|------|
| 数据模型 | `models/paper.py` | ✅ | Paper 模型，27字段，to_dict() |
| CRUD 路由 | `routers/papers.py` | ✅ | 15个端点，分页/筛选/排序/搜索 |
| 路由注册 | `main.py` Line 182-183 | ✅ | `/api/papers` |
| 数据库 | SQLite (已存) | ✅ | 1条测试文献 |

#### 15 个 API 端点：
```
GET    /api/papers                  列表（分页/筛选/排序/搜索）
POST   /api/papers                  创建文献
POST   /api/papers/batch            批量导入
GET    /api/papers/tags             标签统计
GET    /api/papers/stats            数据库统计
GET    /api/papers/search           全文搜索
GET    /api/papers/{id}             详情
PUT    /api/papers/{id}             更新元数据
DELETE /api/papers/{id}             删除
PUT    /api/papers/{id}/tags        替换标签
POST   /api/papers/{id}/tags/{tag}  添加标签
DELETE /api/papers/{id}/tags/{tag}  移除标签
PUT    /api/papers/{id}/read-status 阅读状态
PUT    /api/papers/{id}/rating      评分
PUT    /api/papers/{id}/favorite    切换收藏
```

### 前端（React/TypeScript）

| 组件 | 文件 | 状态 | 说明 |
|------|------|------|------|
| API 服务 | `services/api.ts` | ✅ | `papersApi` 14方法 + `PaperItem`/`TagInfo`/`PaperListResponse` 接口 |
| 文献管理 | `components/Views/FileExplorerView.tsx` | ✅ | 搜索/标签筛选/状态筛选/排序/收藏/右键菜单/Zotero导入 |
| 标签面板 | `components/Views/TagsView.tsx` | ✅ | 标签云（大小按频率）+ 点击筛选文献列表 |

#### FileExplorerView 功能矩阵：
- 工具栏：导入PDF / 新建文件夹 / 新建笔记 / 仅收藏
- 搜索框：防抖 300ms
- 标签筛选：横向标签云 (最多15个)
- 状态筛选：未读/在读/已读 三按钮
- 排序：时间/标题/年份/引用数
- 列表项：状态点、PDF图标、标题、首标签、年份、收藏星、更多按钮
- 右键菜单：阅读状态 + 评分1-5 + 标签管理 + 删除
- 底部详情预览：标题/作者/期刊/DOI/阅读状态/评分/标签/摘要
- Zotero 集成：连接状态 + 一键导入
- 分页：>50篇时显示翻页

#### TagsView 功能矩阵：
- 搜索标签
- 标签云（10色调色板，按频率计算字号）
- 点击标签显示该标签下文献列表
- 文献可点击打开阅读器
- 底部统计：标签数 × 文献总数

---

## 验收结果

| 标准 | 结果 |
|------|------|
| `npx tsc --noEmit` | ✅ 零错误 |
| `npx vite build` | ✅ 成功（1m 12s, 4266 modules）|
| 后端模型导入 | ✅ Paper + 15 routes |
| 后端路由注册 | ✅ Papers router loaded |
| API 端点测试 | ✅ `/api/papers` 返回分页数据 |
| Swagger 文档 | ✅ FastAPI 自动生成 |

---

## 发现的问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| authors 字段存为字符串 | P2 | 数据库旧记录 authors="Xuezhong Cai Curt H. Hagedorn..." 应为 JSON 数组 ["Xuezhong Cai", ...]。代码 `to_dict()` 返回 `self.authors or []` 正确但遇到字符串时前端 may crash。建议加后端兼容处理。 |

---

## Phase 1 进度

```
Phase 1 (当前):
  ├─ Chapter B: 玻璃浮雕 UI ✅ (10min)
  ├─ Chapter C: 论文数据库 CRUD ✅ (33min — 已存在，仅验证)
  └─ Chapter D: Markdown 增强 (4h) ← 下一步
```

---

## 下一步：Chapter D

根据 TECHNICAL_MANUAL.md v8.0：

```
Chapter D: Markdown 增强（P2，预估 4h）

| # | 任务 | 文件 | 预估 |
|---|------|------|------|
| D.1 | Milkdown 编辑器集成 | MarkdownEditor.tsx | 2h |
| D.2 | KaTeX 公式支持 | MarkdownEditor.tsx | 1h |
| D.3 | 实时预览面板 | MarkdownEditor.tsx | 30min |
| D.4 | 导出格式 (Docx/MD) | MarkdownEditor.tsx + format_export.py | 30min |
```

**当前状态**: Markdown 编辑器已标注 `⚠️ 基础可用 — 无实时预览/KaTeX`，Milkdown 替代方案已确定但未落地。