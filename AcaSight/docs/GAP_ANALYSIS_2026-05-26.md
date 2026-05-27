# AcaSight 对标分析报告

> 对照《PDF阅读器开发手册》和《Markdown转Word模板系统开发手册》，逐项对比 AcaSight 现有实现，标识差距和优先级

日期：2026-05-26

---

## 一、PDF 阅读器模块

### 1.1 PDF 渲染与文字选中

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| PDF.js 渲染 | PDF.js 3.x/4.x | react-pdf（封装 PDF.js）✅ | 无 | - |
| 文本层与选中 | TextLayer + user-select | ✅ 已修复（pointer-events穿透） | 无 | - |
| 多页渲染 | 连续页渲染 | ✅ Array.from 渲染所有页 | 无 | - |
| 虚拟滚动 | IntersectionObserver 懒加载 | ❌ 全量渲染，大文件卡 | **缺失** | P1 |

### 1.2 标注系统

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| 高亮标注 | 4色（黄/绿/蓝/粉） | 6色（黄/绿/蓝/粉/橙/紫）✅ | 更好 | - |
| 颜色分类法则 | 黄=核心观点/绿=方法论/蓝=存疑/粉=重要 | 仅有颜色无语义标签 | **缺失标签** | P2 |
| 下划线标注 | 选区底部绘制线条 | ✅ 已实现 | 无 | - |
| 删除线标注 | - | ✅ 已实现（手册未提及，额外功能） | - | - |
| 文本选择浮动工具栏 | 选中文字弹出工具条 | ✅ 已实现 v2.0 | 无 | - |
| 图形标注-矩形 | 矩形拖拽绘制 | ✅ 标注模式下可拖拽 | 无 | - |
| 图形标注-圆形 | 圆形绘制 | ❌ 无 | **缺失** | P3 |
| 图形标注-箭头 | 箭头绘制 | ❌ 无 | **缺失** | P3 |
| 文本注释 | 便签式注释 | ✅ note 类型已实现 | 无 | - |
| 手绘批注 | Canvas/SVG 自由绘画 | ❌ 无 | **缺失** | P3 |
| 标注数据结构 | 统一类型（highlight/underline/shape/note/ink） | 仅 highlight/underline/note/strikethrough | **缺 shape/ink** | P2 |

### 1.3 标注侧边栏与跳转

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| 标注列表侧边栏 | 按颜色/类型分组展示 | ❌ 无独立标注侧边栏 | **缺失** | **P0** |
| 点击跳转定位 | 点击标注→滚动+高亮闪烁 | ❌ 无 | **缺失** | **P0** |
| 颜色分组 | 按颜色分组高亮 | ❌ 无分组 | **缺失** | P1 |
| 标注搜索/过滤 | 搜索标注内容 | ❌ 无 | **缺失** | P2 |
| 标注持久化 | IndexedDB / 后端存储 | ✅ annotationsApi 后端存储 | 无 | - |

### 1.4 文献关联图谱

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| 学术API对接 | Semantic Scholar / OpenAlex | ✅ 后端 search_service + GraphView | 无 | - |
| 力导向图 | D3.js / react-force-graph | ✅ react-force-graph-2d | 无 | - |
| 节点交互 | 悬停详情+点击展开 | ✅ 已有悬停+点击展开 | 无 | - |
| 搜索结果联动 | 搜索↔图谱联动 | ✅ Phase 2.8 已完成 | 无 | - |
| 引用方向箭头 | 箭头标记引用方向 | ⚠️ 需验证 | 检查 | P2 |

---

## 二、Markdown 转 Word 模块

### 2.1 核心转换引擎

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| Pandoc 集成 | pypandoc | ✅ format_service.py | 无 | - |
| DOCX 导出 | --reference-doc 模板 | ✅ markdown_to_docx | 无 | - |
| LaTeX 导出 | markdown→LaTeX | ✅ markdown_to_latex | 无 | - |
| PDF 导出 | XeLaTeX | ✅ markdown_to_pdf | 无 | - |
| citeproc 参考文献 | --citeproc | ✅ 已支持 | 无 | - |
| CSL 样式 | APA/IEEE/Nature等 | ✅ 6种内置样式 | 缺GB/T 7714 CSL | P1 |

### 2.2 模板系统

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| 内置模板库 | GB/T 7714/APA/IEEE | ✅ template_service.py 3种内置 | 无 | - |
| python-docx 模板生成 | JSON→.docx | ✅ generate_template | 无 | - |
| 用户自定义格式配置 | JSON 7大类参数 | ⚠️ 后端支持，前端无UI | **缺前端UI** | P2 |
| 交叉引用 | pandoc-crossref | ❌ 未集成 | **缺失** | P1 |
| 三线表 | 三线表样式 | ❌ 无 | **缺失** | P2 |
| 题注图注 | 图/表标题格式 | ❌ 无特殊处理 | **缺失** | P2 |
| 模板预览 | 预览模板效果 | ❌ 无 | **缺失** | P3 |

### 2.3 Zotero 集成

| 功能 | 手册要求 | AcaSight 现状 | 差距 | 优先级 |
|------|---------|-------------|------|--------|
| Better BibTeX 导出 | .bib 文件引用 | ✅ zoteroApi + zotero_sync.py | 无 | - |
| 参考文献自动编号 | citeproc | ✅ 已支持 | 无 | - |

---

## 三、优先级排序

### P0 — 核心缺失，立即实现
1. **标注侧边栏**（AnnotationSidebar）：按颜色/类型分组、点击跳转
2. **标注跳转定位**（jumpToAnnotation）：滚动到页面 + 高亮闪烁动画

### P1 — 重要功能，尽快补齐
3. **虚拟滚动**（大PDF性能优化）
4. **GB/T 7714 CSL 样式**（中国国标引用格式）
5. **pandoc-crossref 交叉引用**集成（图表公式编号引用）
6. **颜色语义标签**（黄=核心观点/绿=方法论/蓝=存疑/粉=重要）
7. **标注类型扩展**：shape（矩形/圆形/箭头）、ink（手绘）

### P2 — 增强体验
8. **前端格式配置 UI**（WritingPanel 模板选择+自定义）
9. **标注搜索/过滤**
10. **三线表样式**支持
11. **题注图注**格式处理
12. **引用方向箭头**验证

### P3 — 锦上添花
13. **图形标注-圆形/箭头**绘制工具
14. **手绘批注**（Canvas/SVG）
15. **模板预览**功能

---

## 四、实施计划

### Phase A：标注侧边栏 + 跳转（P0）
- 新建 `AnnotationSidebar.tsx` 组件
- 按颜色分组展示，每组可折叠
- 点击标注项→scrollToPage + 高亮闪烁
- 集成到 EditorView 右侧面板

### Phase B：虚拟滚动 + 交叉引用 + CSL（P1）
- PDF 页面懒加载（IntersectionObserver）
- pandoc-crossref 安装 + format_service 集成
- gbt7714-numeric.csl 下载到 csl_styles/

### Phase C：标注系统增强（P1-P2）
- 颜色语义标签配置
- AnnotationItem 类型扩展（shape/ink）
- 圆形/箭头绘制工具
- 标注搜索过滤

### Phase D：模板系统增强（P2）
- WritingPanel 格式设置 UI
- 三线表 python-docx 实现
- 题注图注样式
