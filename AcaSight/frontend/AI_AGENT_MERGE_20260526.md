# AcaSight AI 阅读与 Agent 合并 — 任务摘要

**时间**: 2026-05-26 14:52–15:15 GMT+8

## 目标
1. 合并 AI 阅读功能与 Agent，让 Agent 成为应用统筹中心
2. 修复 Agent 无法完全阅读 PDF 文档的问题
3. 修复悬浮窗（翻译等）功能不可用

## 根本原因分析

### 问题 1：Agent 无法阅读 PDF
`agentStore.sendTask()` 只向发送 `pdf_title` + `selected_text`，**不传递 PDF 全文**。后端 Agent 只能看到标题，无法深入分析论文内容。用户反馈 "根据标题推测..." 表现正是这个原因。

### 问题 2：悬浮窗翻译功能
三套 AI 入口并存且各自为政：
- `FloatingBubble`（全局浮层）：直调 `aiApi.chat()`，不走 Agent
- `ContextualAgentBar`（面板内）：部分直调 API、部分走 Agent
- `AgentPanel`（专用面板）：走 Agent，但缺少 PDF 全文

## 修改清单

### 文件 1: `agentStore.ts`
- `PanelContext` 新增 `pdfFullText?: string` 字段
- `sendTask()` 向发送 `pdf_full_text`（截断至 20K 字符，超过标记 `pdf_text_truncated: true`）

### 文件 2: `ObsidianLayout.tsx`
- 从 `useApp()` 提取 `pdfFullText`
- **移除 `FloatingBubble` 组件**（import + 渲染代码）
- 改为渲染全局 `ContextualAgentBar`，接收 `pdfFullText` 作为上下文
- 将 `pdfFullText` 传递给 `AgentPanel`
- 移除未使用的 `clearGlobalSelection`

### 文件 3: `ContextualAgentBar.tsx`
- **所有 AI 操作统一走 Agent**（不再用直调 `aiApi.chat()`）
- 移除内联 AI 结果展示（翻译/解释结果现在显示在 Agent Panel）
- 移除 `aiApi`/`useAIModels`/`MarkdownRenderer` 等不再需要的导入
- 保留高亮/笔记等 UI 本地操作
- 保留自由输入发送到 Agent

### 文件 4: `AgentPanel.tsx`
- 新增 `pdfText?: string` prop
- 将 `pdfFullText` 写入 `PanelContext` → 发送到

## 新架构

```
用户选中文字 ──→ ContextualAgentBar（唯一悬浮入口）
                      │
                  所有 AI 操作 ──→ agentStore.sendTask()
                      │
                  发送 SSE ──→ Agent Panel（流式响应）
                      │
          发送：task + pdf_full_text + selected_text + ...
```

- ✅ `FloatingBubble` 已移除，不再冗余
- ✅ `ContextualAgentBar` 为唯一悬浮交互（全局 + 面板内）
- ✅ 所有 AI 操作（翻译/解释/润色/总结/问答）统一走 Agent SSE
- ✅ Agent 可接收 PDF 全文上下文（前 20K 字符）
- ✅ TypeScript 编译零错误

## 后续建议

1. 将 20K 字符截断策略升级为 RAG（`/api/rag/query`）后端按需检索
2. 后端 Agent 需适配 `pdf_full_text` 字段（目前只处理 `pdf_title`）
3. 可考虑在 Agent 回复中标注"已读取 PDF 全文"或"已读取前 N 页"