# AcaSight 翻译功能优化方案

## 现状分析

### 当前问题

1. **翻译响应慢/无响应**
   - 当前使用多引擎降级链：Google → Microsoft → MyMemory → AI
   - 每个引擎串行调用，失败后才切换，导致延迟累积
   - 没有流式输出，用户需要等待完整响应
   - 缓存机制简单（内存LRU），没有持久化

2. **划词弹窗位置错乱**
   - 当前使用固定偏移量计算位置（`position: { x, y }`）
   - 没有考虑视口边界检测
   - 没有处理PDF缩放(scale)的影响
   - 弹窗可能超出屏幕边界

3. **翻译结果格式丢失**
   - 纯文本翻译，丢失原文的段落结构
   - 没有保留换行、缩进等格式信息
   - 学术术语替换简单粗暴（正则替换）

---

## 改进方案

### 一、翻译 API 优化（参考 BabelDOC）

#### 1.1 批量翻译 + 并发请求

**BabelDOC 的优势：**
- 使用 `AsyncCallback` + `asyncio.Queue` 实现流式进度
- `RateLimiter` 漏桶算法控制请求速率
- 批量处理减少API调用次数

**改进措施：**

```python
# 1. 添加流式翻译接口
async def translate_stream(self, text: str, from_lang: str = "auto", to_lang: str = "zh"):
    """流式翻译，实时返回结果"""
    # 先检查缓存
    cached = self._cache.get(text, from_lang, to_lang)
    if cached:
        yield {"type": "complete", "translation": cached, "engine": "cache"}
        return
    
    # 并发调用多个引擎，取最快结果
    tasks = [
        self._try_engine_async("google", text, from_lang, to_lang),
        self._try_engine_async("microsoft", text, from_lang, to_lang),
        self._try_engine_async("mymemory", text, from_lang, to_lang),
    ]
    
    # 使用 asyncio.wait_for_first 取最快结果
    for coro in asyncio.as_completed(tasks):
        result = await coro
        if result:
            yield {"type": "chunk", "translation": result}
            yield {"type": "complete", "translation": result, "engine": result.engine}
            self._cache.set(text, from_lang, to_lang, result.translation)
            return
    
    # 全部失败，使用AI兜底
    async for chunk in self._ai_translate_stream(text, from_lang, to_lang):
        yield chunk

# 2. 添加批量翻译接口
async def translate_batch(self, texts: List[str], from_lang: str = "auto", to_lang: str = "zh"):
    """批量翻译，使用连接池并发"""
    # 合并短文本，减少API调用
    batches = self._merge_short_texts(texts, max_length=5000)
    
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=10)) as client:
        tasks = [self._translate_batch_async(client, batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        
    return self._split_batch_results(results, texts)
```

#### 1.2 持久化缓存（SQLite）

参考 BabelDOC 的 `TranslationCache`：

```python
# 使用 peewee + SQLite 实现持久化缓存
# - WAL模式支持高并发
# - 自动清理旧记录（保留最近50000条）
# - 冲突时自动替换（ON CONFLICT REPLACE）
```

**改进措施：**

1. 添加 SQLite 缓存层，缓存不随服务重启丢失
2. 添加缓存预热机制，预加载常用学术术语
3. 添加缓存统计接口，监控命中率

#### 1.3 速率限制与重试

参考 BabelDOC 的 `RateLimiter`：

```python
class RateLimiter:
    """漏桶算法速率限制器"""
    def __init__(self, max_qps: int):
        self.max_qps = max_qps
        self.min_interval = 1.0 / max_qps
        self.lock = threading.Lock()
        self.next_request_time = time.monotonic()
    
    def wait(self):
        with self.lock:
            now = time.monotonic()
            wait_duration = self.next_request_time - now
            if wait_duration > 0:
                time.sleep(wait_duration)
            self.next_request_time = max(self.next_request_time, now) + self.min_interval
```

---

### 二、划词交互优化（参考 STranslate + pdf-reader-js）

#### 2.1 智能弹窗定位算法

**当前问题：**
- 使用鼠标位置直接定位，没有考虑选区矩形
- 没有视口边界检测

**改进措施（参考 pdf-reader-js SelectionToolbar）：**

```typescript
interface TextSelection {
  text: string;
  pageNumber: number;
  rects: DOMRect[];  // 选区的所有矩形区域
}

function calculatePosition(selection: TextSelection): Position {
  if (!selection || selection.rects.length === 0) {
    return { top: 0, left: 0, visible: false };
  }

  // 1. 找到最上方的矩形（选区起始位置）
  const firstRect = selection.rects.reduce((min, rect) => {
    if (rect.top < min.top || (rect.top === min.top && rect.left < min.left)) {
      return rect;
    }
    return min;
  }, selection.rects[0]);

  // 2. 默认在选区上方显示（留出48px间距）
  let top = firstRect.top - 48;
  let left = firstRect.left + firstRect.width / 2;

  // 3. 视口边界检测与调整
  const toolbarWidth = 200;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  // 水平边界：确保不超出左右边界
  let adjustedLeft = left - toolbarWidth / 2;
  if (adjustedLeft < 8) adjustedLeft = 8;
  if (adjustedLeft + toolbarWidth > viewportWidth - 8) {
    adjustedLeft = viewportWidth - toolbarWidth - 8;
  }

  // 垂直边界：如果上方空间不足，改在下方显示
  let adjustedTop = top;
  if (adjustedTop < 8) {
    const lastRect = selection.rects[selection.rects.length - 1];
    adjustedTop = lastRect.bottom + 8;
  }

  return {
    top: adjustedTop,
    left: adjustedLeft + toolbarWidth / 2,
    visible: true
  };
}
```

#### 2.2 文本选择监听优化

**改进措施（参考 pdf-reader-js useTextSelection）：**

```typescript
export function useTextSelection(options: UseTextSelectionOptions = {}) {
  const { onSelect, onCopy } = options;
  const [selection, setSelection] = useState<TextSelection | null>(null);

  const handleSelectionChange = useCallback(() => {
    const windowSelection = window.getSelection();
    if (!windowSelection || windowSelection.isCollapsed) {
      setSelection(null);
      return;
    }

    const text = windowSelection.toString().trim();
    if (!text) {
      setSelection(null);
      return;
    }

    // 获取选区所在的页码（从PDF元素的数据属性中读取）
    const anchorNode = windowSelection.anchorNode;
    let pageElement = anchorNode?.parentElement;
    while (pageElement && !pageElement.dataset.pageNumber) {
      pageElement = pageElement.parentElement;
    }
    const pageNumber = pageElement ? parseInt(pageElement.dataset.pageNumber || '1', 10) : 1;

    // 获取选区的所有矩形（支持多行选择）
    const range = windowSelection.getRangeAt(0);
    const rects = Array.from(range.getClientRects());

    const newSelection: TextSelection = { text, pageNumber, rects };
    setSelection(newSelection);
    onSelect?.(newSelection);
  }, [onSelect]);

  // 监听选择变化
  useEffect(() => {
    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, [handleSelectionChange]);

  return { selection, hasSelection: selection !== null };
}
```

#### 2.3 弹窗显示/隐藏优化

**改进措施：**

1. **防抖处理**：划词结束后延迟100ms显示弹窗，避免快速选择时的闪烁
2. **点击外部关闭**：监听 mousedown 事件，点击弹窗外区域自动关闭
3. **Esc键关闭**：支持键盘快捷键关闭弹窗
4. **滚动时隐藏**：PDF滚动时自动隐藏弹窗，停止滚动后重新计算位置

```typescript
// 防抖显示
const debouncedShow = useMemo(
  () => debounce((sel: TextSelection) => {
    setPosition(calculatePosition(sel));
    setVisible(true);
  }, 100),
  []
);

// 点击外部关闭
useEffect(() => {
  const handleClickOutside = (e: MouseEvent) => {
    if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
      onClose();
    }
  };
  document.addEventListener('mousedown', handleClickOutside);
  return () => document.removeEventListener('mousedown', handleClickOutside);
}, [onClose]);

// 滚动时隐藏
useEffect(() => {
  const handleScroll = () => {
    setVisible(false);
    // 滚动停止后重新显示
    clearTimeout(scrollTimeoutRef.current);
    scrollTimeoutRef.current = setTimeout(() => {
      if (selection) {
        setPosition(calculatePosition(selection));
        setVisible(true);
      }
    }, 150);
  };
  window.addEventListener('scroll', handleScroll, true);
  return () => window.removeEventListener('scroll', handleScroll, true);
}, [selection]);
```

---

### 三、翻译结果格式保留（参考 BabelDOC）

#### 3.1 段落结构保留

**BabelDOC 的优势：**
- 使用占位符标记公式、样式等特殊内容
- 翻译后再还原占位符，保持格式一致

**改进措施：**

```python
class FormatPreservingTranslator:
    """保留格式的翻译器"""
    
    # 占位符模板
    PLACEHOLDER_TEMPLATE = "<<<{id}>>>"
    
    def __init__(self):
        self.placeholders = {}
        self.placeholder_id = 0
    
    def _create_placeholder(self, content: str, content_type: str) -> str:
        """为特殊内容创建占位符"""
        self.placeholder_id += 1
        placeholder = self.PLACEHOLDER_TEMPLATE.format(id=self.placeholder_id)
        self.placeholders[placeholder] = {
            "content": content,
            "type": content_type
        }
        return placeholder
    
    def _extract_formulas(self, text: str) -> str:
        """提取数学公式，用占位符替换"""
        # 匹配 LaTeX 公式: $...$ 或 $$...$$
        import re
        
        # 行间公式 $$...$$
        text = re.sub(
            r'\$\$(.*?)\$\$',
            lambda m: self._create_placeholder(m.group(0), "formula_display"),
            text,
            flags=re.DOTALL
        )
        
        # 行内公式 $...$
        text = re.sub(
            r'\$(.*?)\$',
            lambda m: self._create_placeholder(m.group(0), "formula_inline"),
            text
        )
        
        return text
    
    def _extract_special_formats(self, text: str) -> str:
        """提取其他特殊格式"""
        # 代码块
        text = re.sub(
            r'```[\s\S]*?```',
            lambda m: self._create_placeholder(m.group(0), "code_block"),
            text
        )
        
        # 行内代码
        text = re.sub(
            r'`([^`]+)`',
            lambda m: self._create_placeholder(m.group(0), "code_inline"),
            text
        )
        
        # 保留换行和缩进信息
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            # 记录每行的缩进
            indent_match = re.match(r'^(\s+)', line)
            indent = indent_match.group(1) if indent_match else ""
            content = line.strip()
            if content:
                formatted_lines.append(f"{indent}{content}")
            else:
                formatted_lines.append("")  # 保留空行
        
        return '\n'.join(formatted_lines)
    
    def _restore_placeholders(self, translated: str) -> str:
        """翻译后还原占位符"""
        result = translated
        for placeholder, info in self.placeholders.items():
            result = result.replace(placeholder, info["content"])
        return result
    
    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        """格式保留翻译"""
        # 1. 提取公式
        text = self._extract_formulas(text)
        
        # 2. 提取其他特殊格式
        text = self._extract_special_formats(text)
        
        # 3. 翻译
        translated = await self._do_translate(text, from_lang, to_lang)
        
        # 4. 还原占位符
        translated = self._restore_placeholders(translated)
        
        return translated
```

#### 3.2 学术术语智能替换

**改进措施：**

```python
class AcademicTermHandler:
    """学术术语处理器 - 避免过度替换"""
    
    def __init__(self):
        self.glossary = ACADEMIC_GLOSSARY_EN2ZH
        
    def apply_glossary(self, text: str, context: dict = None) -> str:
        """
        智能应用术语词典
        - 根据上下文决定是否替换
        - 保留代码、公式中的术语
        """
        # 标记保护区域（代码、公式）
        protected_ranges = self._mark_protected_ranges(text)
        
        # 按长度排序，先替换长术语
        sorted_terms = sorted(
            self.glossary.keys(),
            key=len,
            reverse=True
        )
        
        result = text
        for term in sorted_terms:
            pattern = re.compile(
                r'(?<![a-zA-Z])' + re.escape(term) + r'(?![a-zA-Z])',
                re.IGNORECASE
            )
            
            # 只在非保护区域替换
            def replace_if_safe(match):
                start, end = match.span()
                if self._is_in_protected_range(start, end, protected_ranges):
                    return match.group(0)  # 不替换
                return self.glossary[term]
            
            result = pattern.sub(replace_if_safe, result)
        
        return result
    
    def _mark_protected_ranges(self, text: str) -> List[Tuple[int, int]]:
        """标记需要保护的区域（代码、公式等）"""
        ranges = []
        
        # 保护 LaTeX 公式
        for match in re.finditer(r'\$\$.*?\$\$', text, re.DOTALL):
            ranges.append((match.start(), match.end()))
        for match in re.finditer(r'\$.*?\$', text):
            ranges.append((match.start(), match.end()))
        
        # 保护代码块
        for match in re.finditer(r'```[\s\S]*?```', text):
            ranges.append((match.start(), match.end()))
        
        return ranges
```

---

## 四、详细修改步骤

### 阶段一：后端翻译服务优化（约 2-3 天）

#### 步骤 1.1：添加 SQLite 持久化缓存

1. 安装依赖：`pip install peewee`
2. 创建 `backend/app/services/translation_cache.py`
3. 修改 `TranslationCache` 类，使用 SQLite WAL 模式
4. 添加缓存预热和自动清理机制

#### 步骤 1.2：实现并发翻译引擎

1. 创建 `backend/app/services/translation_engine.py`
2. 实现 `AsyncTranslationEngine` 基类
3. 实现并发引擎调用（`asyncio.gather` / `asyncio.as_completed`）
4. 添加 `RateLimiter` 速率限制器

#### 步骤 1.3：添加流式翻译接口

1. 修改 `translation_service.py`，添加 `translate_stream` 方法
2. 修改 `translate.py` 路由，添加 `/translate/stream` endpoint
3. 使用 SSE (Server-Sent Events) 或 WebSocket 推送流式结果

#### 步骤 1.4：添加批量翻译接口

1. 实现 `translate_batch` 方法
2. 添加文本合并/拆分逻辑（短文本合并，长文本拆分）
3. 修改路由，添加 `/translate/batch` endpoint

#### 步骤 1.5：格式保留翻译

1. 创建 `FormatPreservingTranslator` 类
2. 实现占位符提取/还原逻辑
3. 集成到翻译服务中

---

### 阶段二：前端弹窗交互优化（约 2-3 天）

#### 步骤 2.1：重构文本选择 Hook

1. 创建 `frontend/src/hooks/useTextSelection.ts`
2. 实现 `getClientRects` 获取选区矩形
3. 添加页码识别逻辑（从 PDF 元素 data 属性读取）

#### 步骤 2.2：实现智能定位算法

1. 创建 `frontend/src/utils/positionCalculator.ts`
2. 实现 `calculatePosition` 函数
3. 添加视口边界检测逻辑
4. 处理 PDF 缩放（scale）影响

#### 步骤 2.3：优化弹窗组件

1. 修改 `FloatingTranslate.tsx`：
   - 使用新的定位算法
   - 添加防抖显示逻辑
   - 添加点击外部关闭
   - 添加滚动时隐藏
   - 添加 Esc 键关闭

#### 步骤 2.4：添加流式显示支持

1. 修改 API 调用，支持流式响应
2. 添加打字机效果显示翻译结果
3. 添加加载状态指示器

---

### 阶段三：格式保留优化（约 1-2 天）

#### 步骤 3.1：后端格式保留

1. 集成 `FormatPreservingTranslator` 到翻译服务
2. 添加公式/代码识别和占位符处理
3. 测试各种格式场景

#### 步骤 3.2：前端格式渲染

1. 修改翻译结果显示组件
2. 添加 LaTeX 公式渲染（使用 KaTeX 或 MathJax）
3. 添加代码块样式

---

### 阶段四：测试与优化（约 2 天）

#### 步骤 4.1：性能测试

1. 测试翻译响应时间（目标：< 500ms）
2. 测试并发性能
3. 测试缓存命中率

#### 步骤 4.2：交互测试

1. 测试各种选区场景（单行/多行/跨页）
2. 测试弹窗位置（边界情况）
3. 测试 PDF 缩放时的表现

#### 步骤 4.3：格式测试

1. 测试公式保留
2. 测试代码块保留
3. 测试段落结构保留

---

## 五、预期效果

| 指标 | 当前 | 目标 |
|------|------|------|
| 翻译响应时间 | 2-5s (串行降级) | < 500ms (并发+缓存) |
| 弹窗定位准确率 | ~60% | > 95% |
| 格式保留率 | ~30% | > 90% |
| 缓存命中率 | N/A (内存缓存) | > 70% (持久化缓存) |

---

## 六、参考项目关键代码片段

### BabelDOC 关键文件

1. `babeldoc/translator/translator.py` - 翻译器基类
2. `babeldoc/translator/cache.py` - SQLite 缓存实现
3. `babeldoc/asynchronize/__init__.py` - 异步回调机制

### pdf-reader-js 关键文件

1. `packages/core/src/hooks/useTextSelection.ts` - 文本选择 Hook
2. `packages/core/src/components/SelectionToolbar/SelectionToolbar.tsx` - 工具栏定位
3. `packages/core/src/components/HighlightPopover/HighlightPopover.tsx` - 弹窗定位

---

## 七、风险提示

1. **并发请求限制**：Google/Microsoft API 可能有并发限制，需要配置合理的 `max_qps`
2. **SQLite 并发**：WAL 模式支持读写并发，但大量并发写入仍可能遇到锁竞争
3. **PDF 缩放处理**：需要确保定位算法正确处理不同的 scale 值
4. **浏览器兼容性**：`getClientRects` 和 `selectionchange` 事件在旧浏览器可能需要 polyfill

---

*文档生成时间：2026-06-06*
*版本：v1.0*
