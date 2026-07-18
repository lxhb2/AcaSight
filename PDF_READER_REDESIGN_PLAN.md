# AcaSight PDF 阅读器重做方案

> 参考项目：Readest (EPUB/PDF reader) + BabelDOC (PDF 翻译)
> 日期：2026-06-05

---

## 一、现状分析

### 1.1 现有 PDF 阅读器组件

| 组件 | 文件 | 功能 | 状态 |
|------|------|------|------|
| Annotator | `PDFReader/Annotator.tsx` | 文字选择生命周期管理 | ✅ 已有 |
| AnnotationToolbar | `PDFReader/AnnotationToolbar.tsx` | 选中后操作按钮栏 | ✅ 已有 |
| TranslatorPopup | `PDFReader/TranslatorPopup.tsx` | 紧凑翻译弹窗 | ✅ 已有 |
| FloatingTranslate | `PDFReader/FloatingTranslate.tsx` | 可拖拽浮动翻译面板 | ✅ 已有 |
| AISidePanel | `PDFReader/AISidePanel.tsx` | 右侧 AI 对话面板 | ✅ 已有 |
| BilingualPDFViewer | `Translate/BilingualPDFViewer.tsx` | 双语对照阅读 | ✅ 已有 |
| FullPageTranslate | `Translate/FullPageTranslate.tsx` | 全页文本翻译 | ✅ 已有 |
| sel.ts | `utils/sel.ts` | 选区工具函数 | ✅ 已有 |
| usePDFTextSelector | `hooks/usePDFTextSelector.ts` | 选择器 Hook | ✅ 已有 |

### 1.2 现有翻译引擎

| 引擎 | 方式 | 问题 |
|------|------|------|
| Argos Translate | 离线，需下载语言包 | 质量一般，需手动下载 |
| translate 库 (MyMemory) | 在线 | 依赖外部 API |
| Google Translate | 在线 | 国内可能被墙 |
| deep-translator (MyMemory) | 在线 | 依赖外部 API |
| AI (LLM) | 兜底 | 消耗 token |

### 1.3 缺少的功能

- ❌ PDF 页面缩略图导航
- ❌ TOC/大纲侧边栏
- ❌ 标注侧边栏（分类、搜索、跳转）
- ❌ 标注持久化（IndexedDB/后端）
- ❌ 标注颜色系统（4色法则）
- ❌ 下划线/图形标注
- ❌ 键盘快捷键
- ❌ 阅读进度记录
- ❌ 标注导出

---

## 二、Readest 借鉴要点

Readest 是一个开源 EPUB/PDF 阅读器，其 Annotator 架构非常成熟：

### 2.1 Annotator 生命周期
```
pointerDown → 清除旧选区
pointerMove → 跟踪拖拽
pointerUp   → 延迟处理选区 → snapRangeToWords
           → 计算锚点位置 (getPopupAnchor)
           → 显示 AnnotationPopup (工具栏 + 翻译/词典)
           → 点击外部/ESC → dismiss
```

### 2.2 弹窗定位策略
- `getPopupPosition`: 计算弹窗在 viewport 中的最佳位置
- 三角指示器指向选中区域
- 自动约束在可视区域内

### 2.3 标注类型系统
- 高亮 (4色: yellow/green/blue/pink) 对应 Readest 的 10色系统
- 下划线
- 笔记注释
- 标注范围编辑 (RangeEditor)

### 2.4 特色功能
- 字典弹窗 (DictionaryPopup) — 查词
- 校对弹窗 (ProofreadPopup) — AI 校对
- 批注导出 (Mrexpt 格式)
- 标注导入/合并
- 全局标注展开

---

## 三、翻译引擎替换方案

### 3.1 旧引擎问题
- Argos Translate: 需手动下载语言包，en→zh 质量一般
- translate/deep-translator: 依赖外部 API，不稳定
- 引擎降级链过长，首引擎成功率低

### 3.2 推荐新引擎: Helsinki-NLP/opus-mt-en-zh

**选择理由：**
- 🎓 **学术级翻译质量**: 训练于 OPUS 语料库（含科研论文平行语料）
- 📦 **轻量**: 模型仅 ~300MB，pip install transformers 即可
- 🔓 **100% 开源**: MIT 协议，Helsinki NLP 维护
- 🚀 **本地运行**: 无需网络，无需 API Key
- 🧩 **易集成**: 标准 HuggingFace transformers 接口
- 🌐 **多语言支持**: 可扩展其他语言对 (ja↔zh, de↔en 等)

**安装方式：**
```bash
pip install transformers sentencepiece torch
# 模型首次使用时自动从 HuggingFace 下载
```

**备用方案: NLLB-200-distilled-600M + CTranslate2**
- 更大模型 (~1.2GB)，质量更高
- 支持 200 种语言
- CTranslate2 推理速度 2-4x 于 transformers

### 3.3 新架构

```
选中文本
  ↓
翻译请求 → /api/translate/text
  ↓
TranslationService (新)
  ├─ 1. LRU 缓存检查
  ├─ 2. Helsinki-NLP/opus-mt-en-zh (主力)
  ├─ 3. AI (LLM) 兜底
  └─ 学术术语词典后处理
  ↓
返回译文 + 引擎标识
```

### 3.4 保留逻辑
- ✅ API 接口不变 (`/translate/text`, `/translate/quick`)
- ✅ 前端调用方式不变 (`translateApi.text()`, `translateApi.quick()`)
- ✅ 缓存策略不变 (LRU)
- ✅ 学术术语词典后处理不变
- ✅ 语言检测逻辑不变
- ❌ 移除 Argos Translate 依赖
- ❌ 移除 translate 库依赖
- ❌ 移除 deep-translator 依赖
- ❌ 移除 Google/MyMemory 在线引擎
- ❌ 简化降级链: opus-mt → AI

---

## 四、PDF 阅读器重做计划

### Phase 1: 核心渲染增强
1. **PDFViewer 组件重构**
   - 虚拟滚动（react-window 已有）
   - 页面缩略图侧边栏
   - TOC/大纲导航
   - 缩放控制（ZoomIn/ZoomOut/Rotate）
   - 页面跳转输入框

2. **文本选择增强**
   - 跨页选择支持
   - 双击选词、三击选段
   - 选择高亮反馈

### Phase 2: 标注系统完善
3. **标注类型扩展**
   - 多色高亮（4色 → 6色：黄/绿/蓝/粉/橙/紫）
   - 下划线标注
   - 文本附注（便签）
   - 矩形区域标注

4. **标注侧边栏**
   - 按颜色/类型分类
   - 搜索过滤
   - 点击跳转到对应页面位置
   - 删除/编辑标注

5. **标注持久化**
   - IndexedDB 本地存储
   - 后端 API 同步（已有 annotations.py）
   - 导出 Markdown/JSON

### Phase 3: 翻译引擎替换
6. **后端翻译引擎替换**
   - 新增 `opus_mt_service.py`
   - 重写 `translation_service.py`
   - 移除旧依赖
   - 保持 API 兼容

### Phase 4: 用户体验增强
7. **键盘快捷键**
   - 空格翻页
   - Ctrl+C 复制
   - Ctrl+H 高亮
   - Esc 关闭弹窗
   - T 翻译选中文字

8. **阅读进度**
   - 进度条
   - 断点续读
   - 阅读时间统计

---

## 五、目录结构变更

```
frontend/src/components/PDFReader/
├── PDFViewer.tsx          # [重做] 主阅读器组件
├── PageThumbnails.tsx     # [新增] 页面缩略图侧边栏
├── TOCSidebar.tsx         # [新增] 大纲导航
├── Annotator.tsx          # [重构] 文字选择编排
├── AnnotationToolbar.tsx  # [增强] 操作工具栏
├── AnnotationSidebar.tsx  # [新增] 标注侧边栏
├── AnnotationItem.tsx     # [新增] 标注列表项
├── TranslatorPopup.tsx    # [保持] 翻译弹窗
├── FloatingTranslate.tsx  # [保持] 浮动翻译面板
├── AISidePanel.tsx        # [保持] AI 对话面板
└── ReaderToolbar.tsx      # [新增] 顶部工具栏(缩放/搜索/导出)

backend/app/services/
├── opus_mt_service.py     # [新增] Helsinki-NLP opus-mt 翻译引擎
├── translation_service.py # [重写] 统一翻译服务
└── quick_translate_service.py  # [删除] 合并到 translation_service.py
```

---

## 六、实施步骤

1. ✅ 分析现状 + 参考项目 (done)
2. 🔲 重写后端翻译引擎 (opus-mt)
3. 🔲 重构 PDFViewer 核心组件
4. 🔲 添加页面缩略图 + TOC 导航
5. 🔲 完善标注系统（类型/侧边栏/持久化）
6. 🔲 添加快捷键支持
7. 🔲 移除旧依赖，清理代码
