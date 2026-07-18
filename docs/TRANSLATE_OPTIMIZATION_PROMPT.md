# AcaSight 翻译功能优化提示词

## 角色设定
你是一位精通 FastAPI + React/TypeScript 的全栈工程师，熟悉 BabelDOC（PDF 翻译）和 STranslate（桌面 OCR 翻译）的架构设计。

## 任务目标
优化 AcaSight 项目的翻译功能，解决以下 3 个核心问题：
1. **翻译响应慢** → 参考 BabelDOC 的批量/流式方式
2. **划词弹窗位置错乱** → 参考 STranslate 的监听机制和弹窗定位算法
3. **翻译结果格式丢失** → 参考 BabelDOC 的格式保留逻辑

## 项目背景

### 现有代码位置
- 后端翻译服务：`backend/app/services/translation_service.py`
- 后端路由：`backend/app/routers/translate.py`
- 前端浮窗组件：`frontend/src/components/Translate/FloatingTranslate.tsx`

### 现有架构
- **后端**：STranslate 风格多引擎降级（Google Deno → Microsoft Edge → MyMemory → AI）
- **前端**：React 浮窗组件，支持拖拽、语言切换、AI 解释、写作工具

### 技术栈
- 后端：Python 3.11 + FastAPI + httpx + asyncio
- 前端：React 18 + TypeScript + Vite
- 已有依赖：react-markdown, remark-gfm, rehype-katex（前端）

---

## 具体需求

### 需求 1：后端翻译引擎优化（参考 BabelDOC）

**目标**：消除 `asyncio.run` 阻塞、连接池复用、并发降级、首结果早返回

**必须实现**：
1. **共享 httpx.AsyncClient**：三个引擎（google/microsoft/mymemory）共用单例 client，配置连接池（max_connections=20, max_keepalive=10）
2. **并发降级调度**：使用 `asyncio.wait(..., return_when=FIRST_COMPLETED)`，首个有效结果立即取消其他任务
3. **删除同步入口的 `asyncio.run`**：同步 `translate()` 仅做缓存快路径，真正的请求必须走 async handler
4. **新增 SSE 流式端点 `/translate/stream`**：返回 `StreamingResponse`，支持逐 token 输出
5. **批量翻译并发化**：`/translate/batch` 使用 `asyncio.gather` + `asyncio.Semaphore(5)` 限流
6. **格式保护机制**：翻译前用正则提取 LaTeX `$...$` `$$...$$`、代码块、Markdown 格式，替换为占位符 `⟦KIND_INDEX⟧`，翻译后还原

**代码规范**：
- 引擎类抽离到 `backend/app/services/translate/engines.py`
- 所有异步函数使用 `async/await`，禁止在 async 上下文使用 `asyncio.run`
- 添加类型注解和 docstring

---

### 需求 2：前端浮窗定位优化（参考 STranslate）

**目标**：弹窗在视口内不溢出，贴边自动翻转

**必须实现**：
1. **新建 Hook `usePopoverPosition`**：
   - 输入：`anchor: DOMRect`（选中文本的边界矩形）、`popoverSize: {width, height}`
   - 输出：`{x, y, placement}`（placement: 'bottom' | 'top' | 'left' | 'right'）
   - 算法：优先显示在锚点下方（`anchor.bottom + 8`），空间不足则翻转上方，再不足则左右贴边
   - 边界校正：确保 `x >= scrollX + 8`，`x + width <= scrollX + viewportWidth - 8`

2. **修改 `FloatingTranslate` 组件**：
   - 将 `position: {x, y}` prop 改为 `anchor: DOMRect`
   - 使用 `usePopoverPosition` 计算实际位置
   - 监听 `resize` 和 `scroll` 事件，位置变化时重新计算

3. **PDF 阅读器集成**：
   - 划词时使用 `window.getSelection().getRangeAt(0).getBoundingClientRect()` 获取真实视口坐标
   - 如果 PDF 在 iframe 内，需加上 `iframe.getBoundingClientRect()` 的 offset

---

### 需求 3：翻译结果格式保留（参考 BabelDOC）

**目标**：LaTeX、Markdown、代码块在翻译结果中正确显示

**必须实现**：
1. **后端格式保护**：
   - 正则模式：
     - `\$\$.*?\$\$` → MATH_BLOCK
     - `\$[^$\n]+\$` → MATH_INLINE
     - ````[\s\S]*?```` → CODE_BLOCK
     - `` `[^`\n]+` `` → CODE_INLINE
     - `\[([^\]]+)\]\(([^)]+)\)` → MD_LINK
     - `\*\*([^*]+)\*\*` → MD_BOLD
     - `\*([^*]+)\*` → MD_ITALIC
   - 占位符格式：`⟦{KIND}_{UNIQUE_ID}⟧`
   - 翻译后按字典顺序还原（避免嵌套替换问题）

2. **前端 Markdown 渲染**：
   - 使用 `ReactMarkdown` + `remarkMath` + `rehypeKatex` 渲染翻译结果
   - 自定义 components：
     - `p`: 减少 margin
     - `code` (inline): 背景色 `rgba(255,255,255,0.1)`，圆角 4px
     - `pre` (block): 背景色 `rgba(0,0,0,0.3)`，padding 8px，overflow-x: auto
     - `a`: 颜色使用主题色，hover 下划线

3. **样式适配**：
   - 确保 KaTeX 字体正确加载（已在项目依赖中）
   - 深色主题适配（使用 CSS 变量 `--body`, `--ink`, `--canvas`）

---

### 需求 4：前端流式翻译体验

**目标**：首 token < 200ms 可见，减少等待焦虑

**必须实现**：
1. **SSE 消费**：使用 `fetch` + `ReadableStream`（不要用 EventSource，因为是 POST）
2. **智能 Loading**：
   - 200ms 内收到首字节 → 不显示 loading，直接渲染
   - 超过 200ms → 显示 "翻译中..." 动画
3. **请求取消**：使用 `AbortController`，组件卸载或重新划词时取消旧请求
4. **错误处理**：网络错误显示友好提示，支持重试按钮

---

### 需求 5：AI 解释/写作工具解耦

**目标**：AI 解释与主翻译并行触发，不阻塞主结果

**必须实现**：
1. **独立请求**：AI 解释使用独立的 `fetch` 调用 `/api/ai/chat/stream`
2. **并行触发**：组件挂载时立即发起 AI 解释请求，不等翻译完成
3. **独立状态**：AI 解释有独立的 loading/error/result 状态
4. **写作工具**：点击按钮时即时调用 `/api/writing/process`，不等待其他请求

---

## 输出要求

### 文件清单
1. `backend/app/services/translate/engines.py` —— 抽离的引擎类
2. `backend/app/services/translation_service.py` —— 重写后的翻译服务
3. `backend/app/routers/translate.py` —— 新增 SSE 和批量并发
4. `frontend/src/hooks/usePopoverPosition.ts` —— 定位 Hook
5. `frontend/src/components/Translate/FloatingTranslate.tsx` —— 重写后的浮窗组件
6. `backend/tests/test_translation.py` —— 单元测试（并发、格式保护、SSE）

### 代码规范
- Python：PEP 8，类型注解，docstring
- TypeScript：严格模式，接口定义，无 `any`
- 错误处理：所有异步操作有 try/catch，用户友好的错误提示
- 性能：无内存泄漏，请求可取消，组件卸载清理

### 测试要求
- 后端单元测试覆盖：引擎并发、格式保护、SSE 流式、批量并发
- 手动验证：
  - 短词翻译 < 300ms
  - 句子翻译首 token < 200ms
  - PDF 顶部/底部/左侧/右侧划词，浮窗都在视口内
  - `$E=mc^2$`、`**bold**`、代码块正确渲染

---

## 参考实现（伪代码）

### 后端并发降级
```python
async def _translate_concurrent(self, text, src, tgt):
    available = [n for n in ("google","microsoft","mymemory") if not self._disabled(n)]
    if not available:
        return None, "none"
    tasks = {n: asyncio.create_task(self._engines[n].translate(text, src, tgt))
             for n in available}
    done, pending = await asyncio.wait(
        tasks.values(), timeout=8.0, return_when=asyncio.FIRST_COMPLETED
    )
    for t in done:
        r = t.result()
        if r and r.strip() and r != text:
            for p in pending: p.cancel()
            return r, next(n for n, t2 in tasks.items() if t2 == t)
    for p in pending: p.cancel()
    return None, "none"
```

### 前端定位 Hook
```typescript
export function usePopoverPosition(anchor: DOMRect | null, size: {w: number, h: number}) {
  const [pos, setPos] = useState({x: 0, y: 0, placement: 'bottom'});
  useLayoutEffect(() => {
    if (!anchor) return;
    const margin = 8, vw = window.innerWidth, vh = window.innerHeight;
    let x = anchor.left + anchor.width/2 - size.w/2;
    let y = anchor.bottom + margin;
    let placement: 'bottom'|'top'|'left'|'right' = 'bottom';
    if (y + size.h > vh - 16) { y = anchor.top - size.h - margin; placement = 'top'; }
    if (x < 8) x = 8; if (x + size.w > vw - 8) x = vw - 8 - size.w;
    setPos({x, y, placement});
  }, [anchor, size]);
  return pos;
}
```

### 格式保护
```python
PROTECTED_PATTERNS = [
    (re.compile(r'\$\$.*?\$\$', re.DOTALL), 'MATH_BLOCK'),
    (re.compile(r'\$[^$\n]+\$'), 'MATH_INLINE'),
    # ... 其他模式
]

def protect_format(text: str) -> tuple[str, dict]:
    placeholders = {}
    for pat, kind in PROTECTED_PATTERNS:
        def repl(m, k=kind, c=len(placeholders)):
            key = f"⟦{k}_{c}⟧"
            placeholders[key] = m.group(0)
            return key
        text = pat.sub(repl, text)
    return text, placeholders
```

---

## 验收标准

- [ ] 短词（≤5词）翻译 P50 < 300ms
- [ ] 句子（50-200字）翻译首 token < 200ms
- [ ] 批量 10 段翻译 < 4s
- [ ] PDF 任意位置划词，浮窗都在视口内不越界
- [ ] `$E=mc^2$`、`**bold**`、列表、代码块正确渲染
- [ ] 切换语言/快速划词无内存泄漏、无僵尸请求
- [ ] 引擎全挂时自动降级到 AI 兜底
- [ ] 单元测试覆盖率 > 70%

---

**开始实施前请确认**：
1. 是否理解所有需求？
2. 是否需要调整任何实现细节？
3. 是否按 M1→M5 顺序逐步实施，还是一次性完成？
