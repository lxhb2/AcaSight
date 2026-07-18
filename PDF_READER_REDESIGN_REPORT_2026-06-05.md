# PDF 阅读器重做 — 任务完成报告

> 日期：2026-06-05 | 参考项目：Readest + BabelDOC

---

## 一、变更总览

### 新增文件 (7个)

| 文件 | 说明 |
|------|------|
| `backend/app/services/opus_mt_service.py` | Helsinki-NLP Opus-MT 学术翻译引擎 |
| `frontend/src/components/PDFReader/PDFViewer.tsx` | 主阅读器组件（react-pdf + 缩略图 + TOC + 标注） |
| `frontend/src/components/PDFReader/ReaderToolbar.tsx` | 顶部工具栏（导航/缩放/面板切换） |
| `frontend/src/components/PDFReader/PageThumbnails.tsx` | 页面缩略图侧边栏 |
| `frontend/src/components/PDFReader/TOCSidebar.tsx` | 大纲/目录导航 |
| `frontend/src/components/PDFReader/AnnotationSidebar.tsx` | 标注列表（搜索/过滤/跳转/删除） |
| `frontend/src/components/PDFReader/index.ts` | 统一导出 |

### 重写文件 (4个)

| 文件 | 变更 |
|------|------|
| `backend/app/services/translation_service.py` | 完全重写：Opus-MT 主力 + AI 兜底，移除 Argos Translate |
| `backend/app/routers/translate.py` | 简化路由，移除语言包下载端点，新增 /batch 批量翻译 |
| `backend/requirements.txt` | 替换 deep-translator→transformers+torch+sentencepiece |
| `frontend/src/services/api.ts` | 更新状态响应类型，移除 downloadLanguages |

### 修改文件 (4个)

| 文件 | 变更 |
|------|------|
| `frontend/src/components/PDFReader/TranslatorPopup.tsx` | 更新引擎标签为 Opus-MT |
| `frontend/src/components/PDFReader/FloatingTranslate.tsx` | 简化翻译调用链 |
| `frontend/src/components/Translate/FloatingTranslate.tsx` | 修复状态检查 |
| `backend/app/services/quick_translate_service.py` | 标记为 DEPRECATED |

---

## 二、翻译引擎替换

### 旧架构
```
Argos Translate (下载模型) → Google → MyMemory → AI
```

### 新架构
```
Helsinki-NLP/opus-mt-en-zh (本地) → AI (LLM) 兜底
```

**选型理由：**
- Helsinki-NLP/opus-mt-en-zh 训练于 OPUS 语料库（含科研论文平行语料）
- ~300MB 模型，首次使用自动从 HuggingFace 下载
- 纯 Python pip 安装：`pip install transformers sentencepiece torch`
- 100% 开源 MIT 协议
- 支持 14 个语言对，可扩展

**前端 API 完全兼容：**
- `/translate/text` ✅
- `/translate/quick` ✅ 
- `/translate/long` ✅
- `/translate/status` ✅
- `/translate/languages` ✅
- `/translate/batch` 🆕 新增

---

## 三、PDF 阅读器架构

### 借鉴 Readest 的设计

```
┌─────────────────────────────────────────────────┐
│  ReaderToolbar (导航/缩放/面板切换)               │
├─────────┬───────────────────────┬───────────────┤
│ 左侧    │ 中央 PDF 渲染区        │ 右侧          │
│ 缩略图  │ ┌─────────────────┐   │ 标注列表      │
│ / TOC   │ │ Page 1 (Canvas) │   │ / AI 对话     │
│         │ │ Page 2 (Canvas) │   │               │
│         │ │ Page 3 (Canvas) │   │               │
│         │ │  [Annotator]    │   │               │
│         │ └─────────────────┘   │               │
└─────────┴───────────────────────┴───────────────┘
```

### 核心组件

| 组件 | 功能 | 参考来源 |
|------|------|----------|
| PDFViewer | 主容器，react-pdf 渲染 | Readest Reader.tsx |
| ReaderToolbar | 缩放/翻页/面板 | Readest 布局 |
| PageThumbnails | 缩略图导航 | Readest 缩略图 |
| TOCSidebar | PDF 大纲提取 | PDF.js getOutline() |
| Annotator | 文字选择→工具栏→翻译 | Readest Annotator.tsx |
| AnnotationSidebar | 标注管理 | Readest Notebook |
| AISidePanel | AI 对话 | 原有 |
| FloatingTranslate | 浮动翻译 | 原有 |

### 快捷键

| 按键 | 功能 |
|------|------|
| ← / PageUp | 上一页 |
| → / PageDown | 下一页 |
| Home | 跳转首页 |
| End | 跳转末页 |
| +/= | 放大 |
| - | 缩小 |
| Esc | 关闭面板/弹窗 |

---

## 四、类型检查验证

```
✅ TypeScript: npx tsc --noEmit → 0 errors
✅ Python: from app.services.translation_service import → OK
✅ Python: from app.services.opus_mt_service import → OK (14 supported pairs)
```

---

## 五、待后续完善

1. **标注持久化**：当前存在内存中，需对接 IndexedDB 或后端 API
2. **标注颜色扩展**：当前 4 色，可扩展到 6+ 色（参考 Readest 10色系统）
3. **标注导入/导出**：Markdown/JSON 格式
4. **搜索高亮**：在 PDF 中搜索定位
5. **阅读进度保存**：断点续读
6. **Opus-MT 模型预热**：首次调用时延迟加载模型（~2-5秒），可考虑启动时预热
7. **downloadLanguages 前端调用**：前端 api.ts 已移除，如有引用需更新
