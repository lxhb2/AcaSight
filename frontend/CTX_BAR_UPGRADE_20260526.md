# ContextualAgentBar 样式升级 + 智能 PDF 截断

**时间**: 2026-05-26 17:32–17:50 GMT+8

## 一、ContextualAgentBar 样式升级（前端 CSS）

### 修改文件：`frontend/src/index.css`

| 元素 | 升级前 | 升级后 |
|---|---|---|
| Orb 球体 | 32px，单层光晕 | 36px，双层光晕（inset -4px + blur 7px），脉冲动画延长至 2.5s |
| Panel 面板 | 320px，blur(16px) | 340px，blur(20px) saturate(1.4)，阴影加深 |
| Header | 基础 flex 布局 | 字重 700，letter-spacing 微调，图标加大至 22px |
| Action 按钮 | 10px 字，基础 hover | 10.5px 字重 500，hover 时图标 scale(1.08)，阴影加强 |
| 选中文本预览 | 无装饰 | 左侧紫蓝渐变竖线（quote 风格），字体 10.5px |
| Input 输入框 | 基础圆角 | 圆角 11px，focus 时 2.5px accent 外框，placeholder 颜色统一 |
| Send 按钮 | 28px | 30px，hover scale(1.06) |
| 深色模式 | 基础覆盖 | 面板玻璃加深至 rgba(30,30,60,0.88)，header 微亮 |

## 二、智能 PDF 截断（前端 TypeScript）

### 修改文件：`frontend/src/store/agentStore.ts`

新增函数 `selectRelevantChunks(fullText, query, maxTotalChars=20000)`：

1. **段落切分** — 按 `\n\s*\n` 分段，每段 < 2000 字符
2. **中英文停用词过滤** — 中文 30 词 + 英文 50 词
3. **关键词评分** — 统计 query 中各词在 chunk 中的出现次数之和
4. **按评分排序** — 高分 chunk 优先发送，总字符 ≤ 20000
5. **无匹配回退** — 若无关键词命中，取前 20000 字符

`sendTask()` 调用方式变更：
```ts
// 之前：简单截断
pdf_full_text: ctx?.pdfFullText?.slice(0, 20000)

// 现在：智能截断
pdf_full_text: ctx?.pdfFullText
  ? selectRelevantChunks(ctx.pdfFullText, task, 20000)
  : undefined
```

## 三、后端配套（上一轮已完成）

`backend/app/agent/core.py` 的 `_format_context()` 已支持 `pdf_full_text`（≤18000 字符），本次无需再改。

## 验证

- ✅ `npx tsc --noEmit` — 零错误
- ✅ `npx vite build` — 构建成功（48.70s）
- ⚠️ 需在运行中的 AcaSight 前端验证 UI 效果（Vite dev server 或 build 后部署）
