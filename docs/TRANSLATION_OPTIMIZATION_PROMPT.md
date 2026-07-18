# AcaSight 翻译功能优化 - 开发提示词

## 角色设定

你是一位资深全栈工程师，专注于：
- Python FastAPI 后端开发
- React + TypeScript 前端开发
- PDF 阅读器交互优化
- 翻译服务架构设计

你的任务是按照以下详细规范，实现 AcaSight 项目的翻译功能优化。

---

## 项目背景

AcaSight 是一个学术 PDF 阅读与分析工具，当前翻译功能存在以下问题：
1. 翻译响应慢（串行引擎降级，无流式输出）
2. 划词弹窗位置错乱（定位算法简陋，无视口边界检测）
3. 翻译结果格式丢失（段落结构、公式、代码等）

---

## 优化目标

参考以下开源项目的优点：
1. **BabelDOC** - 批量翻译、流式输出、速率限制、SQLite 持久化缓存
2. **STranslate** - 多引擎并发、智能降级、弹窗定位
3. **pdf-reader-js** - 文本选择监听、弹窗边界检测

---

## 文件路径规范

### 后端文件（Python FastAPI）
```
backend/
├── app/
│   ├── services/
│   │   ├── translation_service.py          # 主翻译服务（需修改）
│   │   ├── translation_cache.py            # 新增：SQLite 缓存
│   │   ├── translation_engine.py           # 新增：并发引擎
│   │   ├── format_preserving_translator.py # 新增：格式保留翻译
│   │   └── rate_limiter.py                 # 新增：速率限制器
│   └── routers/
│       └── translate.py                    # 路由（需添加流式/批量接口）
```

### 前端文件（React + TypeScript）
```
frontend/
├── src/
│   ├── hooks/
│   │   └── useTextSelection.ts             # 新增：文本选择 Hook
│   ├── utils/
│   │   └── positionCalculator.ts           # 新增：弹窗定位计算
│   ├── services/
│   │   └── api.ts                          # 需添加流式 API 调用
│   └── components/
│       ├── PDFReader/
│       │   └── FloatingTranslate.tsx       # 需重构
│       └── Common/
│           └── FloatingTranslate.tsx       # 需重构
```

---

## 第一阶段：后端翻译服务优化

### 任务 1.1：实现 SQLite 持久化缓存

创建 `backend/app/services/translation_cache.py`：

**要求：**
1. 使用 `peewee` + SQLite
2. WAL 模式 (`journal_mode='wal'`)
3. 自动清理旧记录（保留最近 50000 条）
4. 冲突时自动替换（`ON CONFLICT REPLACE`）
5. 线程安全

**参考实现（BabelDOC）：**
```python
import json
import random
import threading
from pathlib import Path
import peewee
from peewee import SQL, AutoField, CharField, Model, SqliteDatabase, TextField, fn

db = SqliteDatabase(None)
CLEAN_PROBABILITY = 0.001  # 0.1% 概率触发清理
MAX_CACHE_ROWS = 50_000
_cleanup_lock = threading.Lock()

class _TranslationCache(Model):
    id = AutoField()
    translate_engine = CharField(max_length=20)
    translate_engine_params = TextField()
    original_text = TextField()
    translation = TextField()

    class Meta:
        database = db
        constraints = [SQL("""
            UNIQUE (translate_engine, translate_engine_params, original_text)
            ON CONFLICT REPLACE
        "")]

class TranslationCache:
    def __init__(self, translate_engine: str, params: dict = None):
        self.translate_engine = translate_engine
        self.params = params or {}
        self._init_db()
    
    def _init_db(self):
        cache_path = Path("./cache/translation_cache.v1.db")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        db.init(str(cache_path), pragmas={"journal_mode": "wal", "busy_timeout": 1000})
        db.create_tables([_TranslationCache], safe=True)
    
    def get(self, text: str) -> str | None:
        try:
            result = _TranslationCache.get_or_none(
                translate_engine=self.translate_engine,
                translate_engine_params=json.dumps(self.params, sort_keys=True),
                original_text=text
            )
            if result and random.random() < CLEAN_PROBABILITY:
                self._cleanup()
            return result.translation if result else None
        except peewee.OperationalError:
            return None
    
    def set(self, text: str, translation: str):
        try:
            _TranslationCache.create(
                translate_engine=self.translate_engine,
                translate_engine_params=json.dumps(self.params, sort_keys=True),
                original_text=text,
                translation=translation
            )
            if random.random() < CLEAN_PROBABILITY:
                self._cleanup()
        except peewee.OperationalError:
            pass
    
    def _cleanup(self):
        if not _cleanup_lock.acquire(blocking=False):
            return
        try:
            max_id = _TranslationCache.select(fn.MAX(_TranslationCache.id)).scalar()
            if max_id and max_id > MAX_CACHE_ROWS:
                threshold = max_id - MAX_CACHE_ROWS
                _TranslationCache.delete().where(_TranslationCache.id <= threshold).execute()
        finally:
            _cleanup_lock.release()
```

---

### 任务 1.2：实现速率限制器

创建 `backend/app/services/rate_limiter.py`：

**要求：**
1. 漏桶算法实现
2. 线程安全（使用 `threading.Lock`）
3. 支持动态调整 QPS
4. 使用 `time.monotonic()` 防止系统时间变化影响

**参考实现（BabelDOC）：**
```python
import threading
import time

class RateLimiter:
    def __init__(self, max_qps: int):
        if max_qps <= 0:
            raise ValueError("max_qps must be positive")
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
            now = time.monotonic()
            self.next_request_time = max(self.next_request_time, now) + self.min_interval
    
    def set_max_qps(self, max_qps: int):
        if max_qps <= 0:
            raise ValueError("max_qps must be positive")
        with self.lock:
            self.max_qps = max_qps
            self.min_interval = 1.0 / max_qps
```

---

### 任务 1.3：实现并发翻译引擎

创建 `backend/app/services/translation_engine.py`：

**要求：**
1. 抽象基类 `BaseTranslationEngine`
2. 并发调用多个引擎（Google/Microsoft/MyMemory）
3. 使用 `asyncio.as_completed` 取最快结果
4. 集成速率限制器
5. 集成 SQLite 缓存

**接口定义：**
```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
import asyncio
import httpx

class TranslationResult:
    def __init__(self, text: str, engine: str, from_lang: str, to_lang: str):
        self.text = text
        self.engine = engine
        self.from_lang = from_lang
        self.to_lang = to_lang

class BaseTranslationEngine(ABC):
    name: str = "base"
    
    def __init__(self, rate_limiter: RateLimiter, cache: TranslationCache):
        self.rate_limiter = rate_limiter
        self.cache = cache
    
    async def translate(self, text: str, from_lang: str, to_lang: str) -> Optional[TranslationResult]:
        # 检查缓存
        cached = self.cache.get(text)
        if cached:
            return TranslationResult(cached, "cache", from_lang, to_lang)
        
        # 速率限制
        self.rate_limiter.wait()
        
        # 执行翻译
        result = await self._do_translate(text, from_lang, to_lang)
        if result:
            self.cache.set(text, result)
        return TranslationResult(result, self.name, from_lang, to_lang) if result else None
    
    @abstractmethod
    async def _do_translate(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        pass

class GoogleEngine(BaseTranslationEngine):
    name = "google"
    
    async def _do_translate(self, text: str, from_lang: str, to_lang: str) -> Optional[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://googlet.deno.dev/translate",
                json={
                    "text": text,
                    "source_lang": self._normalize_lang(from_lang),
                    "target_lang": self._normalize_lang(to_lang)
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", "")
        return None
    
    def _normalize_lang(self, code: str) -> str:
        mapping = {"zh": "zh-CN", "en": "en", "auto": "auto"}
        return mapping.get(code, code)

class MicrosoftEngine(BaseTranslationEngine):
    name = "microsoft"
    # 类似实现...

class MyMemoryEngine(BaseTranslationEngine):
    name = "mymemory"
    # 类似实现...

class ConcurrentTranslationService:
    """并发翻译服务 - 多引擎竞争，取最快结果"""
    
    def __init__(self):
        self.engines = [
            GoogleEngine(RateLimiter(5), TranslationCache("google")),
            MicrosoftEngine(RateLimiter(5), TranslationCache("microsoft")),
            MyMemoryEngine(RateLimiter(10), TranslationCache("mymemory")),
        ]
    
    async def translate(self, text: str, from_lang: str = "auto", to_lang: str = "zh") -> TranslationResult:
        """并发翻译，返回最快结果"""
        if from_lang == "auto":
            from_lang = self._detect_language(text)
        
        # 创建并发任务
        tasks = [engine.translate(text, from_lang, to_lang) for engine in self.engines]
        
        # 取第一个成功结果
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result and result.text:
                return result
        
        # 全部失败，返回原文
        return TranslationResult(text, "none", from_lang, to_lang)
    
    async def translate_stream(self, text: str, from_lang: str = "auto", to_lang: str = "zh") -> AsyncGenerator[dict, None]:
        """流式翻译 - 实时返回结果"""
        # 先检查缓存
        for engine in self.engines:
            cached = engine.cache.get(text)
            if cached:
                yield {"type": "chunk", "text": cached}
                yield {"type": "complete", "text": cached, "engine": "cache"}
                return
        
        # 并发请求，谁先返回就推送
        tasks = {asyncio.create_task(engine.translate(text, from_lang, to_lang)): engine 
                 for engine in self.engines}
        
        done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)
        
        for task in done:
            result = await task
            if result and result.text:
                # 取消其他任务
                for t in pending:
                    t.cancel()
                yield {"type": "complete", "text": result.text, "engine": result.engine}
                return
        
        yield {"type": "error", "error": "All engines failed"}
    
    def _detect_language(self, text: str) -> str:
        import re
        cjk = len(re.findall(r'[\u4e00-\u9fff]', text))
        return "zh" if (cjk / max(len(text.strip()), 1)) > 0.1 else "en"
```

---

### 任务 1.4：实现格式保留翻译

创建 `backend/app/services/format_preserving_translator.py`：

**要求：**
1. 使用占位符保护公式、代码等特殊内容
2. 翻译后还原占位符
3. 保留段落结构和缩进
4. 智能学术术语替换（避免在代码/公式中替换）

**接口定义：**
```python
import re
from typing import List, Tuple, Dict

class FormatPreservingTranslator:
    """格式保留翻译器"""
    
    PLACEHOLDER_TEMPLATE = "<<<{id}>>>"
    
    def __init__(self, inner_translator):
        self.inner = inner_translator
        self.placeholders: Dict[str, dict] = {}
        self.placeholder_id = 0
        self.academic_glossary = {...}  # 学术术语词典
    
    async def translate(self, text: str, from_lang: str, to_lang: str) -> str:
        """格式保留翻译"""
        self.placeholders = {}
        self.placeholder_id = 0
        
        # 1. 提取并保护特殊内容
        protected_text = self._extract_special_content(text)
        
        # 2. 翻译
        translated = await self.inner.translate(protected_text, from_lang, to_lang)
        
        # 3. 还原占位符
        result = self._restore_placeholders(translated.text if hasattr(translated, 'text') else translated)
        
        # 4. 应用学术术语（避开保护区域）
        result = self._apply_glossary_smart(result)
        
        return result
    
    def _extract_special_content(self, text: str) -> str:
        """提取并保护特殊内容"""
        result = text
        
        # 保护 LaTeX 公式 $$...$$
        result = re.sub(
            r'\$\$(.*?)\$\$',
            lambda m: self._create_placeholder(m.group(0), "formula_display"),
            result,
            flags=re.DOTALL
        )
        
        # 保护行内公式 $...$
        result = re.sub(
            r'(?<!\$)\$(?!\$)(.*?)\$',
            lambda m: self._create_placeholder(m.group(0), "formula_inline"),
            result
        )
        
        # 保护代码块
        result = re.sub(
            r'```[\s\S]*?```',
            lambda m: self._create_placeholder(m.group(0), "code_block"),
            result
        )
        
        # 保护行内代码
        result = re.sub(
            r'`([^`]+)`',
            lambda m: self._create_placeholder(m.group(0), "code_inline"),
            result
        )
        
        # 保护 URL
        result = re.sub(
            r'https?://[^\s<>"\']+',
            lambda m: self._create_placeholder(m.group(0), "url"),
            result
        )
        
        return result
    
    def _create_placeholder(self, content: str, content_type: str) -> str:
        self.placeholder_id += 1
        placeholder = self.PLACEHOLDER_TEMPLATE.format(id=self.placeholder_id)
        self.placeholders[placeholder] = {"content": content, "type": content_type}
        return placeholder
    
    def _restore_placeholders(self, text: str) -> str:
        result = text
        for placeholder, info in self.placeholders.items():
            result = result.replace(placeholder, info["content"])
        return result
    
    def _apply_glossary_smart(self, text: str) -> str:
        """智能应用术语词典，避开保护区域"""
        # 识别保护区域（已还原的内容）
        protected_ranges = []
        for match in re.finditer(r'(\$\$.*?\$\$|\$.*?\$|`[^`]+`|```[\s\S]*?```)', text):
            protected_ranges.append((match.start(), match.end()))
        
        # 按长度排序术语，先替换长的
        sorted_terms = sorted(self.academic_glossary.keys(), key=len, reverse=True)
        
        result = text
        for term in sorted_terms:
            pattern = re.compile(
                r'(?<![a-zA-Z])' + re.escape(term) + r'(?![a-zA-Z])',
                re.IGNORECASE
            )
            
            def replace_if_safe(match):
                start, end = match.span()
                # 检查是否在保护区域内
                for p_start, p_end in protected_ranges:
                    if start >= p_start and end <= p_end:
                        return match.group(0)  # 不替换
                return self.academic_glossary[term]
            
            result = pattern.sub(replace_if_safe, result)
        
        return result
```

---

### 任务 1.5：修改路由添加新接口

修改 `backend/app/routers/translate.py`：

**要求：**
1. 保留原有接口（向后兼容）
2. 添加 `/translate/stream` SSE 流式接口
3. 添加 `/translate/batch` 批量翻译接口
4. 添加 `/translate/status` 服务状态接口

**新增接口：**
```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import json
import asyncio

router = APIRouter()

class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "zh"

class BatchTranslateRequest(BaseModel):
    texts: List[str]
    source_lang: str = "auto"
    target_lang: str = "zh"

# 原有接口保持不变...

@router.post("/stream")
async def translate_stream(req: TranslateRequest):
    """流式翻译 - SSE"""
    async def event_generator():
        service = ConcurrentTranslationService()
        async for event in service.translate_stream(req.text, req.source_lang, req.target_lang):
            yield f"data: {json.dumps(event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/batch")
async def translate_batch(req: BatchTranslateRequest):
    """批量翻译"""
    service = ConcurrentTranslationService()
    
    # 并发处理所有文本
    tasks = [service.translate(text, req.source_lang, req.target_lang) 
             for text in req.texts]
    results = await asyncio.gather(*tasks)
    
    return {
        "status": "ok",
        "data": [
            {
                "translation": r.text,
                "engine": r.engine,
                "from_lang": r.from_lang,
                "to_lang": r.to_lang
            }
            for r in results
        ]
    }

@router.get("/status")
async def get_status():
    """获取翻译服务状态"""
    service = ConcurrentTranslationService()
    return {
        "status": "ok",
        "engines": [e.name for e in service.engines],
        "cache_stats": {...}  # 各引擎缓存统计
    }
```

---

## 第二阶段：前端交互优化

### 任务 2.1：创建文本选择 Hook

创建 `frontend/src/hooks/useTextSelection.ts`：

**要求：**
1. 监听 `selectionchange` 事件
2. 获取选区的所有矩形（`getClientRects`）
3. 识别选区所在的 PDF 页码
4. 提供防抖处理

**接口定义：**
```typescript
import { useCallback, useEffect, useState, useRef } from 'react';

export interface TextSelection {
  text: string;
  pageNumber: number;
  rects: DOMRect[];
  range: Range | null;
}

export interface UseTextSelectionOptions {
  onSelect?: (selection: TextSelection) => void;
  debounceMs?: number;
}

export function useTextSelection(options: UseTextSelectionOptions = {}) {
  const { onSelect, debounceMs = 100 } = options;
  const [selection, setSelection] = useState<TextSelection | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

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

    // 获取页码
    const anchorNode = windowSelection.anchorNode;
    let pageElement = anchorNode?.parentElement;
    while (pageElement && !pageElement.dataset.pageNumber) {
      pageElement = pageElement.parentElement;
    }
    const pageNumber = pageElement 
      ? parseInt(pageElement.dataset.pageNumber || '1', 10) 
      : 1;

    // 获取所有矩形
    const range = windowSelection.getRangeAt(0);
    const rects = Array.from(range.getClientRects());

    const newSelection: TextSelection = {
      text,
      pageNumber,
      rects,
      range,
    };

    // 防抖
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(() => {
      setSelection(newSelection);
      onSelect?.(newSelection);
    }, debounceMs);
  }, [onSelect, debounceMs]);

  const clearSelection = useCallback(() => {
    window.getSelection()?.removeAllRanges();
    setSelection(null);
  }, []);

  useEffect(() => {
    const handleMouseUp = () => {
      setIsSelecting(false);
      handleSelectionChange();
    };
    const handleMouseDown = () => setIsSelecting(true);

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('selectionchange', handleSelectionChange);

    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('selectionchange', handleSelectionChange);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [handleSelectionChange]);

  return {
    selection,
    isSelecting,
    clearSelection,
    hasSelection: selection !== null && selection.text.length > 0,
  };
}
```

---

### 任务 2.2：创建弹窗定位计算器

创建 `frontend/src/utils/positionCalculator.ts`：

**要求：**
1. 基于选区矩形计算弹窗位置
2. 默认在选区上方显示
3. 视口边界检测与调整
4. 支持 PDF 缩放因子

**接口定义：**
```typescript
export interface Position {
  top: number;
  left: number;
  visible: boolean;
}

export interface PositionOptions {
  popoverWidth?: number;
  popoverHeight?: number;
  gap?: number;
  scale?: number;
}

export function calculatePopoverPosition(
  rects: DOMRect[],
  options: PositionOptions = {}
): Position {
  const {
    popoverWidth = 380,
    popoverHeight = 200,
    gap = 8,
    scale = 1,
  } = options;

  if (!rects || rects.length === 0) {
    return { top: 0, left: 0, visible: false };
  }

  // 找到最上方的矩形
  const firstRect = rects.reduce((min, rect) => {
    if (rect.top < min.top || (rect.top === min.top && rect.left < min.left)) {
      return rect;
    }
    return min;
  }, rects[0]);

  // 默认在选区上方
  let top = firstRect.top - popoverHeight - gap;
  let left = firstRect.left + (firstRect.width * scale) / 2;

  // 视口边界检测
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  // 水平边界
  let adjustedLeft = left - popoverWidth / 2;
  if (adjustedLeft < gap) {
    adjustedLeft = gap;
  } else if (adjustedLeft + popoverWidth > viewportWidth - gap) {
    adjustedLeft = viewportWidth - popoverWidth - gap;
  }

  // 垂直边界：上方空间不足时改在下方
  let adjustedTop = top;
  if (adjustedTop < gap) {
    const lastRect = rects[rects.length - 1];
    adjustedTop = lastRect.bottom + gap;
  }

  // 确保不超出底部
  if (adjustedTop + popoverHeight > viewportHeight - gap) {
    adjustedTop = viewportHeight - popoverHeight - gap;
  }

  return {
    top: adjustedTop,
    left: adjustedLeft + popoverWidth / 2,
    visible: true,
  };
}

// 计算工具栏位置（更紧凑）
export function calculateToolbarPosition(
  rects: DOMRect[],
  options: PositionOptions = {}
): Position {
  const { popoverWidth = 200, gap = 8, scale = 1 } = options;

  if (!rects || rects.length === 0) {
    return { top: 0, left: 0, visible: false };
  }

  const firstRect = rects.reduce((min, rect) => {
    if (rect.top < min.top || (rect.top === min.top && rect.left < min.left)) {
      return rect;
    }
    return min;
  }, rects[0]);

  // 工具栏在选区上方，高度约 40px
  const toolbarHeight = 40;
  let top = firstRect.top - toolbarHeight - gap;
  let left = firstRect.left + (firstRect.width * scale) / 2;

  const viewportWidth = window.innerWidth;

  let adjustedLeft = left - popoverWidth / 2;
  if (adjustedLeft < gap) adjustedLeft = gap;
  if (adjustedLeft + popoverWidth > viewportWidth - gap) {
    adjustedLeft = viewportWidth - popoverWidth - gap;
  }

  let adjustedTop = top;
  if (adjustedTop < gap) {
    const lastRect = rects[rects.length - 1];
    adjustedTop = lastRect.bottom + gap;
  }

  return {
    top: adjustedTop,
    left: adjustedLeft + popoverWidth / 2,
    visible: true,
  };
}
```

---

### 任务 2.3：重构 FloatingTranslate 组件

修改 `frontend/src/components/PDFReader/FloatingTranslate.tsx`：

**要求：**
1. 使用新的 `useTextSelection` Hook
2. 使用 `calculatePopoverPosition` 定位
3. 添加流式翻译显示
4. 添加点击外部关闭
5. 添加滚动时隐藏
6. 添加 Esc 键关闭

**关键修改点：**
```typescript
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useTextSelection } from '@/hooks/useTextSelection';
import { calculatePopoverPosition } from '@/utils/positionCalculator';
import { translateApi } from '@/services/api';

interface FloatingTranslateProps {
  onClose?: () => void;
}

export const FloatingTranslate: React.FC<FloatingTranslateProps> = ({ onClose }) => {
  const [translation, setTranslation] = useState('');
  const [loading, setLoading] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0, visible: false });
  const [currentText, setCurrentText] = useState('');
  
  const popoverRef = useRef<HTMLDivElement>(null);
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 文本选择处理
  const { selection, clearSelection } = useTextSelection({
    onSelect: (sel) => {
      if (sel.text.length > 0 && sel.text.length < 5000) {
        setCurrentText(sel.text);
        
        // 计算位置
        const pos = calculatePopoverPosition(sel.rects, {
          popoverWidth: 380,
          popoverHeight: 300,
        });
        setPosition(pos);
        
        // 开始翻译
        handleTranslate(sel.text);
      }
    },
    debounceMs: 150,  // 防抖 150ms
  });

  // 流式翻译
  const handleTranslate = useCallback(async (text: string) => {
    setLoading(true);
    setTranslation('');
    
    try {
      // 优先使用流式接口
      const response = await fetch('/api/translate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, source_lang: 'auto', target_lang: 'zh' }),
      });
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6));
              if (data.type === 'chunk') {
                setTranslation(prev => prev + data.text);
              } else if (data.type === 'complete') {
                setTranslation(data.text);
                setLoading(false);
              }
            }
          }
        }
      }
    } catch (error) {
      // 流式失败，回退到普通接口
      try {
        const res = await translateApi.text({ text, source_lang: 'auto', target_lang: 'zh' });
        setTranslation(res.data?.translation || '翻译失败');
      } catch {
        setTranslation('翻译请求失败');
      }
      setLoading(false);
    }
  }, []);

  // 点击外部关闭
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        clearSelection();
        onClose?.();
      }
    };
    
    if (position.visible) {
      // 延迟绑定避免触发时的点击事件立即关闭
      const timer = setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside);
      }, 100);
      return () => {
        clearTimeout(timer);
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [position.visible, clearSelection, onClose]);

  // Esc 键关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        clearSelection();
        onClose?.();
      }
    };
    
    if (position.visible) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [position.visible, clearSelection, onClose]);

  // 滚动时隐藏
  useEffect(() => {
    const handleScroll = () => {
      if (position.visible) {
        setPosition(prev => ({ ...prev, visible: false }));
        
        // 滚动停止后重新计算位置
        if (scrollTimeoutRef.current) {
          clearTimeout(scrollTimeoutRef.current);
        }
        scrollTimeoutRef.current = setTimeout(() => {
          if (selection) {
            const pos = calculatePopoverPosition(selection.rects);
            setPosition(pos);
          }
        }, 150);
      }
    };
    
    window.addEventListener('scroll', handleScroll, true);
    return () => {
      window.removeEventListener('scroll', handleScroll, true);
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [position.visible, selection]);

  if (!position.visible) return null;

  return (
    <div
      ref={popoverRef}
      className="acasight-floating-translate"
      style={{
        position: 'fixed',
        left: position.left,
        top: position.top,
        transform: 'translateX(-50%)',
        width: 380,
        maxHeight: 500,
        zIndex: 1000,
        // ... 其他样式
      }}
    >
      {/* 原文显示 */}
      <div className="original-text">
        <div className="label">原文</div>
        <div className="content">{currentText.slice(0, 500)}{currentText.length > 500 ? '...' : ''}</div>
      </div>
      
      {/* 翻译结果 */}
      <div className="translation-result">
        <div className="label">翻译</div>
        {loading && !translation ? (
          <div className="loading">翻译中...</div>
        ) : (
          <div className="content" style={{ whiteSpace: 'pre-wrap' }}>
            {translation}
          </div>
        )}
      </div>
    </div>
  );
};
```

---

## 第三阶段：测试验证

### 测试清单

#### 后端测试
- [ ] SQLite 缓存读写正常
- [ ] 并发引擎调用返回最快结果
- [ ] 速率限制器有效控制 QPS
- [ ] 流式接口 SSE 输出正常
- [ ] 批量翻译接口正常工作
- [ ] 格式保留翻译正确处理公式/代码

#### 前端测试
- [ ] 文本选择 Hook 正确获取选区矩形
- [ ] 弹窗定位在选区上方
- [ ] 视口边界检测正确调整位置
- [ ] 点击外部关闭弹窗
- [ ] Esc 键关闭弹窗
- [ ] 滚动时隐藏，停止后重新显示
- [ ] 流式翻译显示打字机效果

#### 集成测试
- [ ] 端到端翻译流程正常
- [ ] PDF 缩放时定位准确
- [ ] 多行/跨页选择定位准确
- [ ] 学术术语正确替换（避开代码/公式）

---

## 注意事项

1. **依赖安装**：
   ```bash
   # 后端
   pip install peewee httpx tenacity
   
   # 前端（如需要新依赖）
   npm install  # 通常不需要新依赖
   ```

2. **数据库迁移**：
   - SQLite 缓存会自动创建表，无需手动迁移
   - 缓存文件位置：`backend/cache/translation_cache.v1.db`

3. **性能调优**：
   - 根据实际 API 限制调整 `RateLimiter` 的 `max_qps`
   - 根据服务器内存调整 `MAX_CACHE_ROWS`

4. **错误处理**：
   - 所有引擎失败时返回原文
   - 流式接口失败时自动回退到普通接口
   - 缓存操作失败时降级到无缓存模式

---

## 参考链接

- BabelDOC: https://github.com/funstory-ai/yadt
- STranslate: https://github.com/ZGGSONG/STranslate
- pdf-reader-js: 本地参考项目

---

*提示词版本：v1.0*
*生成时间：2026-06-06*
