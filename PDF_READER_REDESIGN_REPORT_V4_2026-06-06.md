# PDF 阅读器重做 v4.0 — 完整报告

> 日期: 2026-06-06 | 参考: STranslate + BabelDOC | 状态: ✅ 完成

---

## 一、核心思路转变

### v3 → v4 思路对比

| 版本 | 翻译引擎 | 体积 | API Key | 离线 |
|------|----------|------|---------|------|
| v3.0 Opus-MT | 本地 ML 模型 | +1.1GB | 否 | ✅ |
| v3.1 MyMemory | 在线 API | 0 | 否 | ❌ |
| **v4.0 STranslate 风格** | **HTTP 多引擎** | **0** | **否** | **❌(可缓存)** |

最终选择 **STranslate 风格**: 4 个内嵌 HTTP 引擎 (Google/Microsoft/MyMemory/AI) 自动降级
- 零 ML 模型依赖
- 零 API Key 配置
- 零本地存储开销
- 100% 可打包进 exe

---

## 二、翻译引擎架构 (STranslate 启发)

### 引擎降级链
```
Google (googlet.deno.dev) → Microsoft Edge → MyMemory → AI (LLM)
   ↓ 失败自动切换 (5min 冷却)               ↓ 缓存命中直接返回
```

### 关键 API 端点
- `GET  /translate/status`   → 4 引擎状态
- `POST /translate/text`     → 单次翻译
- `POST /translate/quick`    → 同 /text (兼容)
- `POST /translate/long`     → 长文本异步
- `POST /translate/batch`    → 批量翻译
- BabelDOC 全文翻译端点保留

### 引擎实现 (300 行)
- `GoogleDenoEngine` — Deno 代理 Google 翻译
- `MicrosoftEdgeEngine` — Edge API 内嵌免 Key
- `MyMemoryEngine` — 免费全开
- `AIEngine` — LLM 兜底

---

## 三、双语 PDF 阅读器 (BabelDOC 启发)

### 新增 `BilingualReader.tsx`

```
┌────────────────────────────────────────────┐
│ Toolbar: [并排] [段落] [全文] [+翻译全部]  │
├────────────────────────────────────────────┤
│ 模式 A: 并排对照                            │
│  ┌──────────────┬──────────────────┐       │
│  │ 原文 PDF     │ 译文 (实时翻译)   │       │
│  │ (Page 1)     │ (左: 原文 右:译文)│       │
│  └──────────────┴──────────────────┘       │
│  同步滚动                                  │
├────────────────────────────────────────────┤
│ 模式 B: 段落对照                            │
│  ┌─ 原文段1 ─┐                              │
│  ┌─ 译文段1 ─┐                              │
│  ┌─ 原文段2 ─┐                              │
│  ┌─ 译文段2 ─┐                              │
├────────────────────────────────────────────┤
│ 模式 C: 全文翻译 (BabelDOC)                 │
│  生成 dual.pdf (交替页 原文+译文)           │
└────────────────────────────────────────────┘
```

### 与 BabelDOC 的区别
| BabelDOC | AcaSight BilingualReader |
|----------|-------------------------|
| 完整 PDF 重建 (布局保留) | 简化实时翻译 (无需重建) |
| 需 OpenAI API | 4 引擎自动降级 |
| 翻译全文 (慢) | 可逐页翻译 (快) |
| Mono/Dual/Alternating 输出 | 并排/段落/全文 三模式 |

---

## 四、PDF 阅读器增强 (上轮完成)

### 新增 7 个组件
- `PDFViewer.tsx` — 主阅读器 (react-pdf, 三栏布局)
- `ReaderToolbar.tsx` — 顶部工具栏
- `PageThumbnails.tsx` — 缩略图
- `TOCSidebar.tsx` — 大纲
- `AnnotationSidebar.tsx` — 标注管理
- `AnnotationSidebar.tsx` — 标注管理
- `index.ts` — 统一导出

### 键盘快捷键
- 方向键翻页, +/- 缩放, Esc 关闭
- Ctrl+方向键 (待加)

---

## 五、文件清单

### 新增 (1)
- `frontend/src/components/Translate/BilingualReader.tsx`

### 重写 (2)
- `backend/app/services/translation_service.py`
- `backend/app/routers/translate.py`

### 修改 (4)
- `backend/requirements.txt`
- `frontend/src/services/api.ts`
- `frontend/src/components/PDFReader/TranslatorPopup.tsx`
- `frontend/src/components/Translate/FloatingTranslate.tsx`

---

## 六、验证

- ✅ TypeScript: tsc --noEmit → 0 errors
- ✅ Python: 4 引擎全部就绪 (google/microsoft/mymemory/ai)
- ✅ 路由: 11 个端点全部加载
- ✅ API: 完全向后兼容

---

## 七、用户体验改进

1. **零配置启动**: 不需要下载任何模型或配置任何 API Key
2. **学术化**: 100+ 学术术语词典自动后处理 (deep learning → 深度学习)
3. **可降级**: 4 引擎自动切换，任意一个失败不影响使用
4. **可缓存**: LRU 缓存避免重复翻译
5. **可打包**: 翻译引擎只是 httpx HTTP 调用，~2KB 代码，可打包进 exe

---

## 八、待优化 (后续)

- [ ] 标注持久化 (IndexedDB/后端)
- [ ] 标注颜色扩展 (6+色)
- [ ] 标注导入/导出 (Markdown/JSON)
- [ ] 阅读进度保存
- [ ] 全文搜索高亮
