# Agent PDF 全文阅读 — 第二轮（后端适配）

**时间**: 2026-05-26 15:42–15:50 GMT+8

## 本轮目标
配合上一轮前端改造，适配后端 `/api/agent/task` 端点，使 Agent 能够接收并利用 PDF 全文进行深度分析。

## 修改内容

### 文件: `backend/app/agent/core.py`

**`_format_context()` 方法重写：**

| 新增处理 | 行为 |
|---|---|
| `pdf_full_text` | 追加「PDF 全文内容」到 Agent 系统提示词（max 18000 字符）|
| `pdf_text_truncated` | 若标记为 `true` 且文本被截断，显示警告提示 |
| `selected_text` 标签 | 优化为「用户选中文本」标记，增强区分度 |
| `pdf_text` 标签 | 改为「文献片段内容」，与 `pdf_full_text` 区分用途 |

**原有 `pdf_text` 保留**，截断策略不变（2000 字符），用于 Zotero 文献摘要等短文本场景。

## 数据流（端到端）

```
react-pdf 渲染 PDF
    ↓  提取 visible page text
  AppContext.pdfFullText (客户侧累积)
    ↓  前端 agentStore.sendTask()
context: { pdf_title, selected_text, pdf_full_text (前 20K), pdf_text_truncated }
    ↓  SSE /api/agent/task
  agent_core.run(task, context)
    ↓  _format_context()
ACADEMIC_SYSTEM_PROMPT + PDF 全文内容
    ↓  LLM 推理
  流式回答（基于 PDF 全文）
```

## Agent 现在能回答的问题

- ✅ 论文的核心研究方法和实验设计
- ✅ 具体的数据、表格内容
- ✅ 论文中发现的具体数值和统计结果（而非推测）
- ✅ 特定段落的解释
- ✅ 多篇论文的对比（如果同时打开多篇）

## 已知限制
- 超过 18000 字符的 PDF 会截断，后端显示警告
- 后续可升级为 RAG 向量检索（`/api/rag/query`）按需获取 PDF 片段