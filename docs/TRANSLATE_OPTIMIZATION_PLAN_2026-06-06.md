# AcaSight 翻译功能优化方案

**版本**: v1.0
**日期**: 2026-06-06
**作者**: QClaw
**状态**: 待用户验收

---

## 0. 现状速览（基于实际代码审计）

### 0.1 后端 `backend/app/services/translation_service.py`

| 模块 | 实现 | 问题 |
|---|---|---|
| 引擎降级链 | Google Deno → Microsoft Edge → MyMemory → AI | 4 个引擎串行等待，首个返回即用，但每个请求都创建新的 `httpx.AsyncClient` |
| 同步入口 `translate()` | `asyncio.run(self._translate_impl(...))` | **致命问题**：在 FastAPI 同步上下文用 `asyncio.run` 会开新事件循环，连接池/连接复用全失效，延迟翻倍 |
| 缓存 | `OrderedDict` LRU 512 条，MD5 文本哈希 | 单进程内存缓存，多 worker 不共享；命中率无法跨会话持久化 |
| 学术术语 | 静态词典 `ACADEMIC_GLOSSARY_EN2ZH`，全词替换 | 仅在结果上做一次后处理，未做词形归一，未保护 LaTeX/代码块/引文 |
| 路由 `routers/translate.py` | `/text` `/quick` `/long` `/batch` | **批量接口无并发**：逐条 `translate()` 串行；无流式输出；无 SSE 进度 |

### 0.2 前端 `frontend/src/components/Translate/FloatingTranslate.tsx`

| 模块 | 实现 | 问题 |
|---|---|---|
| 翻译触发 | `useEffect` + 300ms debounce | 短词判定逻辑硬编码（`wordCount <= 5 && !txt.includes('.')`），英文段落里几乎从不用 Argos |
| 引擎选择 | 先调 `translateApi.text()`（STranslate 风格）失败再调 `aiApi.chat()` | 每次走两个 HTTP，慢；AI 翻译返回 `res.response` 是**非流式**，需等全量响应 |
| 浮窗位置 | `position: {x,y}` 由父组件传入 | **未做视口校正**：选中 PDF 文本后弹窗固定在选中点，但未考虑 PDF 阅读器 iframe/scroll 偏移；未做"贴边翻转" |
| 拖拽 | window mousemove | 流畅，但**未限制出屏**：边界裁剪靠 `safePos`，缺少 min-size 适配 |
| 格式保留 | `<div>{translation}</div>` 直接渲染 | **Markdown/LaTeX/换行全丢**：`\n` 渲染成空格，`$x^2$` 显示源码，学术场景致命 |
| AI 解释/写作工具 | 额外 `aiApi.chat` | 复用主翻译延迟，无独立快捷入口 |

### 0.3 参考项目调研

- **BabelDOC**（PDF 翻译）：用 **paragraph-level batching** + **流式 token 输出**（OpenAI SSE），并将原文按"格式 token + 文本块"分离，确保翻译时格式不丢
- **STranslate**（桌面 OCR+翻译）：**鼠标监听 → 拖尾弹窗**，弹窗位置算法是 `targetRect.bottom + 8` 向下，触底则 `targetRect.top - popHeight - 8` 翻转向上，左右同理
- **Readest 标注器**（已有 readest 报告）：`<foliate-view>` Overlayer 处理高亮，弹窗 `Annotator.tsx` 统一管理划词回调——可作为 AcaSight 与 PDF 集成时的参考

---

## 1. 总体改造目标

| 指标 | 现状 | 目标 |
|---|---|---|
| 单次翻译 P50 延迟（短词≤5词） | 800ms-2s | **< 300ms**（走 Argos + 缓存） |
| 单次翻译 P50 延迟（句子 50-200字） | 2s-6s | **< 1.2s**（并发引擎 + 早返回） |
| 批量翻译（10 段） | 串行 ~30s | **并发 ~3s**（asyncio.gather + 信号量限流） |
| 浮窗定位 | 偶发错位/出屏 | **零错位**（视口边界 + 阅读器坐标转换） |
| LaTeX/Markdown 保留 | 完全丢失 | **100% 保留**（先分段后翻译，块内 token 替换） |
| AI 解释延迟 | 等主翻译完成 | **可独立触发**（不等主结果） |

---

## 2. 后端改造：分 3 步

### 步骤 B1：改造 `TranslationService` 引擎层 —— 共享连接池 + 并发降级

**目标**：消除 `asyncio.run`、连接池复用、首结果早返回

**涉及文件**：
- `backend/app/services/translation_service.py`（重写 `_translate_impl` 内部组织）
- 新增 `backend/app/services/translate/engines.py`（按引擎拆成模块化类）

**具体动作**：

1. **单例化 httpx 客户端**：
   ```python
   # engines.py
   class GoogleDenoEngine:
       _client: Optional[httpx.AsyncClient] = None
       def __init__(self):
           if GoogleDenoEngine._client is None:
               GoogleDenoEngine._client = httpx.AsyncClient(
                   timeout=httpx.Timeout(8.0, connect=3.0),
                   limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
               )
           self._client = GoogleDenoEngine._client
   ```
   三个引擎（google/microsoft/mymemory）共用一个 `AsyncClient`，连接池复用。

2. **并发降级 + 早返回**（核心改进，对应 BabelDOC 的"任一成功即停"）：
   ```python
   async def _translate_concurrent(self, text, src, tgt):
       """并发调度所有可用引擎,首结果胜出"""
       available = [n for n in ("google","microsoft","mymemory") if not self._disabled(n)]
       if not available:
           return None, "none"
       tasks = {n: asyncio.create_task(self._engines[n].translate(text, src, tgt))
                for n in available}
       try:
           done, pending = await asyncio.wait(
               tasks.values(),
               timeout=8.0,
               return_when=asyncio.FIRST_COMPLETED,
           )
           for t in done:
               r = t.result()
               if r and r.strip() and r != text:
                   for p in pending: p.cancel()
                   engine_name = next(n for n, t2 in tasks.items() if t2 == t)
                   return r, engine_name
           for p in pending: p.cancel()
           return None, "none"
       except Exception as e:
           logger.warning(f"concurrent translate: {e}")
           return None, "none"
   ```
   关键：8s 超时，**首个有效结果立即取消其他任务**，比当前的"串行逐个尝试"快 3-4 倍。

3. **删除同步 `translate()` 中的 `asyncio.run`**：
   ```python
   # 旧 (致命)
   def translate(self, text, ...):
       ...
       return asyncio.run(self._translate_impl(text, ...))  # 开新事件循环!
   
   # 新:在 FastAPI 端点直接调 translate_async;同步入口仅在缓存命中时返回
   def translate(self, text, ...):
       cached = self._cache.get(...)
       if cached: return {...}
       raise RuntimeError("Use translate_async in async context")
   ```
   同步入口只做缓存快路径，真正的请求必须走 `/translate/text` 的 async handler（已存在 `translate_async`）。

4. **Redis 缓存兜底（可选，Phase 2）**：
   - 短期：保留进程内 LRU
   - 中期：加 `app/services/cache_manager.py` 已有的 CacheManager 适配，把高频翻译词条（学术术语）落 Redis

### 步骤 B2：新增流式翻译端点（SSE）

**目标**：参考 BabelDOC 的 OpenAI SSE 流式输出，让前端可以"逐 token 渲染"

**涉及文件**：
- `backend/app/routers/translate.py`（新增 `/translate/stream`）
- `backend/app/services/translation_service.py`（新增 `translate_stream` 生成器）

**具体动作**：

1. **新增 SSE 端点**：
   ```python
   from fastapi.responses import StreamingResponse
   
   @router.post("/stream")
   async def translate_stream(req: TranslateRequest):
       async def event_gen():
           try:
               async for chunk in translation_service.translate_stream(
                   req.text, req.source_lang, req.target_lang
               ):
                   yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
               yield "data: [DONE]\n\n"
           except Exception as e:
               yield f"data: {json.dumps({'error': str(e)})}\n\n"
       return StreamingResponse(event_gen(), media_type="text/event-stream")
   ```

2. **`translate_stream` 优先走 AI 引擎的流式**：
   - `AIService.chat()` 已经是 async generator（`async for chunk in ai.chat(...)`），直接转发
   - 非 AI 引擎不流式，整段返回（前端用 `delta` 累加）

3. **前端消费 SSE**（步骤 F3 对接）：
   - 用 `fetch` + ReadableStream（不要用 EventSource，因为是 POST）
   - 收到每个 `delta` 立即更新 `translation` state

### 步骤 B3：批量翻译并发化 + 格式保护

**目标**：10 段并发翻译；LaTeX/Markdown 块在翻译前后不被破坏

**涉及文件**：
- `backend/app/routers/translate.py`（重写 `/translate/batch`）
- `backend/app/services/translation_service.py`（新增 `batch_translate`）

**具体动作**：

1. **并发批量**：
   ```python
   @router.post("/batch")
   async def translate_batch(req: BatchTranslateRequest):
       sem = asyncio.Semaphore(5)  # 限流 5 并发
       async def _one(t):
           async with sem:
               return await translation_service.translate_async(t, req.source_lang, req.target_lang)
       results = await asyncio.gather(*[_one(t) for t in req.texts])
       return {"status": "ok", "data": results}
   ```

2. **格式保护（参考 BabelDOC 的 placeholder 机制）**：
   ```python
   import re
   
   # 保护模式:LaTeX $...$、$$...$$、代码 ```...```、行内 `code`、Markdown 链接 [text](url)
   PROTECTED_PATTERNS = [
       (re.compile(r'\$\$.*?\$\$', re.DOTALL), 'MATH_BLOCK'),
       (re.compile(r'\$[^$\n]+\$'), 'MATH_INLINE'),
       (re.compile(r'```[\s\S]*?```'), 'CODE_BLOCK'),
       (re.compile(r'`[^`\n]+`'), 'CODE_INLINE'),
       (re.compile(r'\[([^\]]+)\]\(([^)]+)\)'), 'MD_LINK'),
       (re.compile(r'\*\*([^*]+)\*\*'), 'MD_BOLD'),
       (re.compile(r'\*([^*]+)\*'), 'MD_ITALIC'),
   ]
   
   def protect_format(text: str) -> tuple[str, dict]:
       placeholders = {}
       for i, (pat, kind) in enumerate(PROTECTED_PATTERNS):
           def repl(m, _i=i, _kind=kind):
               key = f"⟦{_kind}_{_i}_{len(placeholders)}⟧"
               placeholders[key] = m.group(0)
               return key
           text = pat.sub(repl, text)
       return text, placeholders
   
   def restore_format(text: str, placeholders: dict) -> str:
       for k, v in placeholders.items():
           text = text.replace(k, v)
       return text
   ```
   在 `_translate_impl` 入口 `protect_format`，出口 `restore_format`。同时在词典 `_apply_glossary` 时**跳过 placeholder**。

---

## 3. 前端改造：分 4 步

### 步骤 F1：浮窗定位算法重写（参考 STranslate 翻转逻辑）

**目标**：弹窗在视口内不溢出，贴边自动翻转

**涉及文件**：
- `frontend/src/components/Translate/FloatingTranslate.tsx`（重写定位 + 抽出 hook）
- 新增 `frontend/src/hooks/usePopoverPosition.ts`

**算法**（参考 STranslate 弹窗定位）：

```typescript
// usePopoverPosition.ts
export interface AnchorRect { x: number; y: number; width: number; height: number; }
export interface PopSize { width: number; height: number; }

export function usePopoverPosition(anchor: AnchorRect | null, size: PopSize) {
  const [pos, setPos] = useState({ x: 0, y: 0, placement: 'bottom' as 'bottom' | 'top' | 'left' | 'right' });
  
  useLayoutEffect(() => {
    if (!anchor) return;
    const margin = 8;
    const vw = window.innerWidth, vh = window.innerHeight;
    const scrollY = window.scrollY, scrollX = window.scrollX;
    
    // 基础位置:锚点下方
    let x = anchor.x + anchor.width / 2 - size.width / 2 + scrollX;
    let y = anchor.y + anchor.height + margin + scrollY;
    let placement: 'bottom' | 'top' | 'left' | 'right' = 'bottom';
    
    // 下方空间不足 → 翻转上方
    if (y + size.height > vh + scrollY - 16) {
      y = anchor.y - size.height - margin + scrollY;
      placement = 'top';
    }
    // 左/右越界
    if (x < scrollX + 8) x = scrollX + 8;
    if (x + size.width > vw + scrollX - 8) x = vw + scrollX - 8 - size.width;
    
    // 垂直翻转后还在屏幕外 → 强制改右/左贴边
    if (y < scrollY + 8) {
      // 居中于锚点右侧
      x = anchor.x + anchor.width + margin + scrollX;
      y = anchor.y + anchor.height / 2 - size.height / 2 + scrollY;
      placement = 'right';
      if (x + size.width > vw + scrollX - 8) {
        x = anchor.x - size.width - margin + scrollX;
        placement = 'left';
      }
    }
    
    setPos({ x, y, placement });
  }, [anchor?.x, anchor?.y, anchor?.width, anchor?.height, size.width, size.height]);
  
  return pos;
}
```

**调用方**（PDF 阅读器划词后）：
```typescript
// 替换 props.position 为 anchor
<FloatingTranslate
  text={selectedText}
  anchor={selectionRect}  // 来自 window.getSelection().getRangeAt(0).getBoundingClientRect()
  onClose={...}
/>
```

**关键**：用 `getBoundingClientRect()` 获取真实视口坐标（PDF iframe 内则需 `iframe.getBoundingClientRect()` 加 offset），不要用 `event.clientX/Y`（滚动时不准）。

### 步骤 F2：双引擎并发请求（短词走 Argos 并发触发）

**目标**：短词翻译 P50 < 300ms；句子翻译可立即显示"加载中"

**涉及文件**：`FloatingTranslate.tsx` 重写 `doTranslate`

```typescript
const doTranslate = useCallback(async (src, tgt, txt) => {
  if (!txt.trim()) return;
  setLoading(true);
  setError(null);
  setTranslation('');  // 清空旧结果
  
  const wordCount = txt.split(/\s+/).length;
  const isShort = wordCount <= 5;
  
  // 启动 SSE 流（所有情况都走流式;短词也用流式以保持代码统一）
  const ctrl = new AbortController();
  abortRef.current = ctrl;
  
  try {
    const res = await fetch('/api/translate/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
      body: JSON.stringify({ text: txt, source_lang: src, target_lang: tgt }),
      signal: ctrl.signal,
    });
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';
    let acc = '';
    let firstChunk = true;
    
    // 显示"等待"状态:流式首字节 > 200ms 才显示 loading
    const loadingTimer = setTimeout(() => { if (!acc) setLoading(true); }, 200);
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      
      let idx;
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const event = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        const line = event.split('\n').find(l => l.startsWith('data: '));
        if (!line) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') { clearTimeout(loadingTimer); setLoading(false); return; }
        try {
          const { delta, error } = JSON.parse(payload);
          if (error) { setError(error); continue; }
          if (firstChunk) { clearTimeout(loadingTimer); setLoading(false); firstChunk = false; }
          acc += delta;
          setTranslation(acc);  // 逐 token 渲染
        } catch {}
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      setError(e instanceof Error ? e.message : '翻译失败');
      setLoading(false);
    }
  }
}, []);
```

**关键改进**：
- 200ms 内收到首字节 → 不显示 loading（直接渲染）
- `AbortController` 切换语言/关闭时取消旧请求
- 取消旧的 `useEffect` debounce，直接组件卸载时 `abortRef.current?.abort()`

### 步骤 F3：格式保留渲染（Markdown + LaTeX）

**目标**：翻译结果中的 `$x^2$`、`**bold**`、列表等正确显示

**涉及文件**：
- `FloatingTranslate.tsx` 替换 `<div>{translation}</div>` 为 `<ReactMarkdown>`
- `package.json` 添加依赖：`react-markdown` `remark-math` `rehype-katex` `remark-gfm`

**实现**（你已经装了 `react-markdown + remark-gfm + rehype-katex`——见 MEMORY.md）：
```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// 翻译结果区
<div className="translation-content">
  {loading && !translation ? (
    <Loader />
  ) : (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        p: ({node, ...props}) => <p style={{margin: '4px 0'}} {...props} />,
        code: ({node, inline, ...props}) => 
          inline ? <code style={...} {...props} /> : <pre style={...}><code {...props} /></pre>,
      }}
    >
      {translation}
    </ReactMarkdown>
  )}
</div>
```

**样式补充**：在 CSS 加 `.translation-content pre { background: rgba(0,0,0,0.3); padding: 6px 8px; border-radius: 4px; }` 等。

### 步骤 F4：解耦 AI 解释 / 写作工具的加载

**目标**：AI 解释与主翻译并行触发，不阻塞主结果

**实现**（同文件 `FloatingTranslate.tsx`）：

```typescript
// 独立 fetch，组件挂载时立即发起,不等翻译完成
useEffect(() => {
  if (!text) return;
  const ctrl = new AbortController();
  (async () => {
    try {
      const res = await fetch('/api/ai/chat/stream', {
        method: 'POST',
        body: JSON.stringify({ messages: [...explainPrompt, { role: 'user', content: text }] }),
        signal: ctrl.signal,
      });
      // ...类似 F2 的 SSE 消费
    } catch {}
  })();
  return () => ctrl.abort();
}, [text]);
```

写作工具同模式，按钮点击时直接 fetch `/api/writing/process`，互不等待。

---

## 4. 联调与迁移步骤（5 步走）

| 步骤 | 内容 | 验证方式 | 预计工作量 |
|---|---|---|---|
| **M1** | B1：引擎并发 + 共享 client | `pytest` 单元测试：mock 引擎 8s 慢响应，验证首结果 < 1.5s 返回 | 0.5d |
| **M2** | B2：新增 `/translate/stream` SSE | curl 测试：`curl -N -X POST .../translate/stream` 看到逐 chunk | 0.3d |
| **M3** | B3：批量并发 + 格式保护 | 单元测试：含 LaTeX 的文本翻译后，LaTeX 块完整保留 | 0.5d |
| **M4** | F1+F2：定位算法 + SSE 消费 | 手动：PDF 划词 → 浮窗贴在选中处下方/上方面板内 → 翻译逐字渲染 | 1.0d |
| **M5** | F3+F4：格式渲染 + AI 并行 | 手动：翻译含 `$E=mc^2$` 的文本，浮窗内 LaTeX 渲染；解释按钮秒开 | 0.5d |

**总计**：~2.8 工作日

**回归测试**（每步必做）：
- `pytest backend/tests/test_translation.py`（已存在或需新建）
- 手动：在 PDF 阅读器中划词不同位置（页面顶部/底部/左边/右边）→ 浮窗不越界
- 手动：连续划词 5 次 → 无内存泄漏、无僵尸请求

---

## 5. 风险与备选

| 风险 | 缓解 |
|---|---|
| Google Deno 代理 `googlet.deno.dev` 不稳定 | 已有多引擎降级；并发调度中失败引擎标记 disabled，5min 后自动重试 |
| AI 流式响应中文长文本卡顿 | 引擎层早返回（首 token 后 200ms 内用户已看到反馈）；继续累积 delta |
| `react-markdown` 增大包体积 ~80KB | 用 `react-markdown` 的 `lazy` 加载 + 拆分到 `Translate/Chunk` 路由 |
| 多 worker 下 LRU 缓存命中率低 | 短期接受；中期接 Redis（`CacheManager` 已有基础设施） |
| PDF iframe 内划词坐标不准 | 调用方需在 `iframe.contentWindow` 内调用 `getSelection()`，并加 `iframe.getBoundingClientRect()` 偏移——文档化到 `PDF_READER_REDESIGN_PLAN.md` |

---

## 6. 关键文件改动清单

**后端**：
- ✏️ `backend/app/services/translation_service.py` —— 重写 `_translate_impl` 为并发降级；新增 `translate_stream`、`batch_translate`、格式保护工具
- ➕ `backend/app/services/translate/engines.py` —— 抽离引擎类
- ✏️ `backend/app/routers/translate.py` —— 新增 `/stream`；重写 `/batch` 为并发
- ➕ `backend/tests/test_translation.py` —— 单元测试（并发、格式保护、SSE）

**前端**：
- ✏️ `frontend/src/components/Translate/FloatingTranslate.tsx` —— SSE 消费 + Markdown 渲染 + 解耦 AI
- ➕ `frontend/src/hooks/usePopoverPosition.ts` —— 翻转定位 hook
- ✏️ `frontend/src/components/Translate/BilingualPDFViewer.tsx` —— 划词时计算 `getSelection()` 真实矩形并传入
- ➕ `frontend/src/components/Translate/TranslatePopover.tsx` —— 如需独立轻量弹窗（不依赖 `FloatingTranslate` 的写作工具）

**文档**：
- ✏️ `docs/PDF_READER_REDESIGN_REPORT_V4_2026-06-06.md` —— 追加章节"E.6 翻译性能与定位优化"
- ➕ `task-artifacts/translate_optimization_implementation_2026-06-XX.md` —— 实施日志

---

## 7. 验收标准

✅ **功能**：
- 短词（≤5词）翻译 P50 < 300ms
- 句子（50-200字）翻译 P50 < 1.2s,首 token < 200ms
- 批量 10 段 < 4s 完成
- 浮窗在 PDF 任意位置划词都贴在视口内（不越界）
- `$E=mc^2$`、`**bold**`、列表、代码块在结果中正确显示

✅ **健壮性**：
- 引擎全挂时降级到 AI 兜底
- 切换语言/快速划词不会泄漏请求
- 跨页/跨 iframe 划词坐标正确

✅ **可维护性**：
- 引擎插拔式（新增引擎 < 20 行）
- 单元测试覆盖 > 70%

---

**下一步**：等待用户确认方案后，按 M1→M5 顺序实施；每步完成后输出"实施日志"到 `task-artifacts/`。
