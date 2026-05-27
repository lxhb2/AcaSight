# PDF 论文阅读器开发手册

> **类 Zotero / UPDF 功能实现指南**
>
> 涵盖：PDF 渲染、文字选中、高亮标注、下划线、图形插入、标注侧边栏跳转、文献关联图谱等核心功能
>
> 版本：v1.0 ｜ 日期：2025年5月

---

## 目录

- [第1章 项目概述与架构设计](#第1章-项目概述与架构设计)
  - [1.1 项目目标](#11-项目目标)
  - [1.2 技术栈选型](#12-技术栈选型)
  - [1.3 系统架构设计](#13-系统架构设计)
  - [1.4 推荐目录结构](#14-推荐目录结构)
- [第2章 PDF 渲染与文字选中](#第2章-pdf-渲染与文字选中)
  - [2.1 PDF.js 基础渲染](#21-pdfjs-基础渲染)
  - [2.2 文本层与文字选中](#22-文本层与文字选中)
  - [2.3 多页渲染与虚拟滚动](#23-多页渲染与虚拟滚动)
- [第3章 标注系统实现](#第3章-标注系统实现)
  - [3.1 高亮标注](#31-高亮标注)
  - [3.2 下划线标注](#32-下划线标注)
  - [3.3 图形标注（矩形、圆形、箭头）](#33-图形标注矩形圆形箭头)
  - [3.4 文本注释与手绘批注](#34-文本注释与手绘批注)
  - [3.5 标注数据结构设计](#35-标注数据结构设计)
- [第4章 标注侧边栏与快速跳转](#第4章-标注侧边栏与快速跳转)
  - [4.1 侧边栏 UI 设计](#41-侧边栏-ui-设计)
  - [4.2 标注分类与颜色法则](#42-标注分类与颜色法则)
  - [4.3 点击跳转定位实现](#43-点击跳转定位实现)
  - [4.4 标注持久化存储](#44-标注持久化存储)
- [第5章 文献关联图谱](#第5章-文献关联图谱)
  - [5.1 学术 API 对接](#51-学术-api-对接)
  - [5.2 图谱数据构建](#52-图谱数据构建)
  - [5.3 D3.js 力导向图可视化](#53-d3js-力导向图可视化)
  - [5.4 节点交互与展开](#54-节点交互与展开)
- [第6章 开源项目参考](#第6章-开源项目参考)
  - [6.1 pdfjs-reader-core（强烈推荐）](#61-pdfjs-reader-core强烈推荐)
  - [6.2 PDFJsAnnotations](#62-pdfjsannotations)
  - [6.3 Zotero](#63-zotero)
  - [6.4 其他参考项目](#64-其他参考项目)
- [第7章 部署与进阶指南](#第7章-部署与进阶指南)
  - [7.1 项目初始化与构建](#71-项目初始化与构建)
  - [7.2 性能优化建议](#72-性能优化建议)
  - [7.3 功能扩展方向](#73-功能扩展方向)
- [附录 A PyMuPDF 桌面端方案](#附录-a-pymupdf-桌面端方案)
- [附录 B API 速率限制参考](#附录-b-api-速率限制参考)

---

## 第1章 项目概述与架构设计

### 1.1 项目目标

本手册旨在指导开发者构建一个类似 Zotero / UPDF 的 PDF 论文阅读器，核心功能包括：

- **PDF 渲染与文字选中**：使用 PDF.js 在浏览器中渲染 PDF，支持文字选择
- **高亮标注（多颜色）**：支持黄色、绿色、蓝色、粉色等多种颜色
- **下划线标注**：在选中文字下方绘制线条
- **图形插入**：支持矩形、圆形、箭头等图形标注
- **文本注释**：在 PDF 任意位置添加便签式注释
- **标注侧边栏**：分类列表展示，点击跳转定位
- **文献关联图谱**：基于学术 API 的可视化引用关系图

目标用户为科研人员和学术研究者，帮助其高效阅读、标注和管理 PDF 文献。

### 1.2 技术栈选型

前端技术栈推荐如下：

| 技术 | 版本 | 用途 | 说明 |
|------|------|------|------|
| PDF.js | 3.x / 4.x | PDF 渲染 | Mozilla 开源，浏览器端渲染 PDF |
| React | 18.x | UI 框架 | 组件化开发，生态丰富 |
| TypeScript | 5.x | 类型安全 | 提升代码可维护性 |
| D3.js | 7.x | 图谱可视化 | 力导向图，节点交互 |
| IndexedDB | - | 本地存储 | 浏览器端持久化标注数据 |
| Tailwind CSS | 3.x | 样式方案 | 快速构建 UI |

后端技术栈（可选）：

| 技术 | 用途 | 说明 |
|------|------|------|
| Node.js + Express | API 服务 | 处理用户认证、标注同步 |
| PostgreSQL / MongoDB | 数据库 | 存储用户标注、文献元数据 |
| Semantic Scholar API | 学术数据 | 获取论文引用关系、元数据 |
| OpenAlex API | 学术数据 | 开源免费，2.5亿+ 论文 |

### 1.3 系统架构设计

系统采用三层架构设计，展示层负责 PDF 渲染和用户交互，业务逻辑层管理标注数据和文献图谱，数据层提供持久化存储和外部 API 接入。

```
┌─────────────────────────────────────────────────────────────────────┐
│                         展示层                                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │ PDF.js Canvas │  │  文本选择层    │  │    标注交互层         │  │
│  │   渲染层      │  │  (TextLayer)  │  │ (AnnotationLayer)     │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                       业务逻辑层                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │  标注管理器    │  │  标注侧边栏    │  │   文献图谱引擎         │  │
│  │ AnnotationMgr │  │ Sidebar List  │  │  Citation Graph       │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                         数据层                                        │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐  │
│  │   IndexedDB   │  │  Semantic      │  │     OpenAlex API      │  │
│  │  (本地存储)    │  │  Scholar API   │  │   (学术数据)          │  │
│  └───────────────┘  └───────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 推荐目录结构

```
pdf-reader/
├── public/
│   └── index.html
├── src/
│   ├── components/
│   │   ├── PDFViewer/           # PDF 渲染组件
│   │   │   ├── PDFPage.tsx      # 单页渲染
│   │   │   ├── TextLayer.tsx    # 文本选择层
│   │   │   └── AnnotationLayer.tsx  # 标注交互层
│   │   ├── Toolbar/             # 工具栏
│   │   ├── Sidebar/             # 标注侧边栏
│   │   │   ├── AnnotationList.tsx
│   │   │   └── AnnotationItem.tsx
│   │   └── CitationGraph/       # 文献关联图谱
│   │       ├── GraphView.tsx
│   │       └── NodeTooltip.tsx
│   ├── core/
│   │   ├── annotationManager.ts # 标注管理器
│   │   ├── annotationStore.ts   # 标注数据存储
│   │   └── pdfService.ts       # PDF 服务
│   ├── api/
│   │   ├── semanticScholar.ts  # Semantic Scholar API
│   │   └── openalex.ts         # OpenAlex API
│   ├── types/
│   │   └── annotation.ts       # TypeScript 类型定义
│   ├── utils/
│   │   ├── colorUtils.ts      # 颜色工具
│   │   └── positionUtils.ts    # 位置计算工具
│   ├── App.tsx
│   └── main.tsx
├── package.json
└── tsconfig.json
```

---

## 第2章 PDF 渲染与文字选中

### 2.1 PDF.js 基础渲染

PDF.js 是 Mozilla 开发的开源 JavaScript 库，可在浏览器中渲染 PDF 文件，无需任何插件。其核心工作流程为：加载 PDF 文档 → 获取页面 → 创建 Canvas → 渲染。

**安装依赖：**

```bash
npm install pdfjs-dist@3.11.174
```

**基础渲染代码：**

```typescript
import * as pdfjsLib from 'pdfjs-dist';
import 'pdfjs-dist/build/pdf.worker.entry';

// 设置 Worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 
  'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

async function renderPDF(url: string, container: HTMLElement) {
  const pdf = await pdfjsLib.getDocument(url).promise;
  
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const scale = 1.5;
    const viewport = page.getViewport({ scale });
    
    // 创建 Canvas
    const canvas = document.createElement('canvas');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    container.appendChild(canvas);
    
    // 渲染
    await page.render({
      canvasContext: canvas.getContext('2d'),
      viewport
    }).promise;
  }
}
```

### 2.2 文本层与文字选中

PDF.js 的文本层（TextLayer）是一个覆盖在 Canvas 上方的透明 HTML 层，由 span 元素组成，每个 span 对应 PDF 中的一个文本片段。文本层使用户能够用鼠标选中 PDF 中的文字，这是实现高亮和下划线标注的前提。

**文本层渲染代码：**

```typescript
async function renderTextLayer(
  page: any, 
  container: HTMLElement, 
  viewport: any
) {
  const textContent = await page.getTextContent();
  
  const textLayer = document.createElement('div');
  textLayer.className = 'text-layer';
  textLayer.style.width = viewport.width + 'px';
  textLayer.style.height = viewport.height + 'px';
  container.appendChild(textLayer);
  
  // 渲染文本层
  await pdfjsLib.renderTextLayer({
    textContentSource: textContent,
    container: textLayer,
    viewport: viewport,
  }).promise;
}
```

**CSS 样式配置：**

```css
.text-layer {
  position: absolute;
  left: 0;
  top: 0;
  /* 文本层需要透明但可选中 */
  opacity: 0.2;
  color: transparent;
}

.text-layer ::selection {
  background: rgba(33, 150, 243, 0.3);
}

.text-layer span {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
}
```

> **【提示】** 文本层 opacity 设为 0.2 是为了让用户能感知到可选区域，同时保持 PDF 原始视觉不受影响。颜色设为 transparent 确保文字不会重复显示。

### 2.3 多页渲染与虚拟滚动

对于大型 PDF 文档，一次性渲染所有页面会导致严重的性能问题。推荐使用虚拟滚动（Virtual Scrolling）技术，只渲染可视区域内的页面。

```typescript
// 使用 IntersectionObserver 实现懒加载
function setupLazyLoading(container: HTMLElement) {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const pageNum = entry.target.getAttribute('data-page');
        renderPage(parseInt(pageNum));
        observer.unobserve(entry.target);
      }
    });
  }, { rootMargin: '200px' });
  
  // 为每个页面占位符设置观察
  document.querySelectorAll('.page-placeholder').forEach(el => {
    observer.observe(el);
  });
}
```

---

## 第3章 标注系统实现

### 3.1 高亮标注

高亮标注是 PDF 阅读器最核心的功能。实现原理是：用户在文本层选中文字后，通过 `window.getSelection()` 获取选区信息，然后使用 `range.getClientRects()` 获取选区的矩形坐标，最后在标注层上创建对应位置的半透明色块。

**高亮标注实现代码：**

```typescript
interface HighlightData {
  id: string;
  type: 'highlight';
  subType: 'yellow' | 'green' | 'blue' | 'pink';
  pageNum: number;
  text: string;
  color: string;
  rects: { x: number; y: number; width: number; height: number }[];
  comment: string;
  timestamp: string;
}

const COLOR_MAP = {
  yellow: { name: '核心观点', bg: 'rgba(255, 215, 0, 0.3)' },
  green:  { name: '方法论',   bg: 'rgba(76, 175, 80, 0.3)' },
  blue:   { name: '存疑',     bg: 'rgba(33, 150, 243, 0.3)' },
  pink:   { name: '重要',     bg: 'rgba(233, 30, 99, 0.3)' },
};

function addHighlightAnnotation(
  selection: Selection,
  pageNum: number,
  annotationLayer: HTMLElement,
  color: string = 'yellow'
): HighlightData {
  const range = selection.getRangeAt(0);
  const rects = range.getClientRects();
  const text = selection.toString();
  const layerRect = annotationLayer.getBoundingClientRect();

  const highlightData: HighlightData = {
    id: Date.now().toString(),
    type: 'highlight',
    subType: color,
    pageNum,
    text,
    color,
    rects: [],
    comment: '',
    timestamp: new Date().toISOString(),
  };

  for (const rect of rects) {
    const overlay = document.createElement('div');
    overlay.className = 'highlight-overlay';
    overlay.style.position = 'absolute';
    overlay.style.left = (rect.left - layerRect.left) + 'px';
    overlay.style.top = (rect.top - layerRect.top) + 'px';
    overlay.style.width = rect.width + 'px';
    overlay.style.height = rect.height + 'px';
    overlay.style.background = COLOR_MAP[color].bg;
    overlay.style.cursor = 'pointer';
    overlay.dataset.id = highlightData.id;
    annotationLayer.appendChild(overlay);

    highlightData.rects.push({
      x: rect.left - layerRect.left,
      y: rect.top - layerRect.top,
      width: rect.width,
      height: rect.height,
    });
  }

  return highlightData;
}
```

### 3.2 下划线标注

下划线标注的实现与高亮类似，区别在于渲染方式：高亮是在选区矩形上覆盖半透明色块，而下划线是在选区底部绘制一条线。

```typescript
function addUnderlineAnnotation(
  selection: Selection,
  pageNum: number,
  annotationLayer: HTMLElement
) {
  const range = selection.getRangeAt(0);
  const rects = range.getClientRects();
  const layerRect = annotationLayer.getBoundingClientRect();

  for (const rect of rects) {
    const underline = document.createElement('div');
    underline.style.position = 'absolute';
    underline.style.left = (rect.left - layerRect.left) + 'px';
    underline.style.top = (rect.bottom - layerRect.top - 2) + 'px';
    underline.style.width = rect.width + 'px';
    underline.style.height = '2px';
    underline.style.background = '#FF5722';
    annotationLayer.appendChild(underline);
  }
}
```

### 3.3 图形标注（矩形、圆形、箭头）

图形标注包括矩形、圆形和箭头。实现原理是在标注层上监听鼠标事件，用户按下鼠标记录起点，拖动过程中实时绘制图形，松开鼠标完成绘制。

**图形标注实现代码：**

```typescript
function setupShapeDrawing(
  annotationLayer: HTMLElement,
  tool: 'rect' | 'circle' | 'arrow',
  color: string
) {
  let isDrawing = false;
  let startX: number, startY: number;
  let currentShape: HTMLElement | null = null;

  annotationLayer.addEventListener('mousedown', (e) => {
    isDrawing = true;
    const rect = annotationLayer.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;

    currentShape = document.createElement('div');
    currentShape.style.position = 'absolute';
    currentShape.style.left = startX + 'px';
    currentShape.style.top = startY + 'px';
    annotationLayer.appendChild(currentShape);
  });

  annotationLayer.addEventListener('mousemove', (e) => {
    if (!isDrawing || !currentShape) return;
    const rect = annotationLayer.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    const width = currentX - startX;
    const height = currentY - startY;

    currentShape.style.width = Math.abs(width) + 'px';
    currentShape.style.height = Math.abs(height) + 'px';
    currentShape.style.left = (width > 0 ? startX : currentX) + 'px';
    currentShape.style.top = (height > 0 ? startY : currentY) + 'px';

    if (tool === 'rect') {
      currentShape.style.border = '2px solid ' + color;
      currentShape.style.background = color.replace(')', ', 0.1)').replace('rgb', 'rgba');
    } else if (tool === 'circle') {
      currentShape.style.border = '2px solid ' + color;
      currentShape.style.borderRadius = '50%';
    } else if (tool === 'arrow') {
      currentShape.style.height = '2px';
      currentShape.style.background = color;
    }
  });

  annotationLayer.addEventListener('mouseup', () => {
    isDrawing = false;
    currentShape = null;
  });
}
```

### 3.4 文本注释与手绘批注

文本注释允许用户在 PDF 任意位置添加笔记。手绘批注则允许用户自由绘制线条，适用于签名、圈画等场景。

```typescript
// 添加文本注释
function addNoteAnnotation(
  pageNum: number,
  x: number,
  y: number,
  content: string,
  annotationLayer: HTMLElement
) {
  const noteIcon = document.createElement('div');
  noteIcon.style.position = 'absolute';
  noteIcon.style.left = x + 'px';
  noteIcon.style.top = y + 'px';
  noteIcon.style.width = '24px';
  noteIcon.style.height = '24px';
  noteIcon.style.background = '#FFD700';
  noteIcon.style.borderRadius = '50%';
  noteIcon.style.cursor = 'pointer';
  noteIcon.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
  noteIcon.textContent = '📝';
  annotationLayer.appendChild(noteIcon);
}

// 手绘批注（使用 Canvas 或 SVG）
function setupFreeDrawing(canvas: HTMLCanvasElement) {
  const ctx = canvas.getContext('2d')!;
  let isDrawing = false;
  let lastX = 0, lastY = 0;

  canvas.addEventListener('mousedown', (e) => {
    isDrawing = true;
    [lastX, lastY] = [e.offsetX, e.offsetY];
  });

  canvas.addEventListener('mousemove', (e) => {
    if (!isDrawing) return;
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.strokeStyle = '#FF0000';
    ctx.lineWidth = 2;
    ctx.stroke();
    [lastX, lastY] = [e.offsetX, e.offsetY];
  });

  canvas.addEventListener('mouseup', () => { isDrawing = false; });
}
```

### 3.5 标注数据结构设计

统一的标注数据结构是系统可扩展性的基础。所有类型的标注共享基础字段，同时通过 type 字段区分不同类型，各类型拥有各自的扩展字段。

```typescript
// 统一标注类型定义
interface BaseAnnotation {
  id: string;            // 唯一标识
  type: AnnotationType;  // 标注类型
  pageNum: number;       // 所在页码
  timestamp: string;     // 创建时间
  author?: string;       // 作者
}

interface HighlightAnnotation extends BaseAnnotation {
  type: 'highlight';
  text: string;          // 选中的文字
  color: string;         // 颜色
  rects: Rect[];        // 位置矩形数组
  comment?: string;      // 备注
}

interface UnderlineAnnotation extends BaseAnnotation {
  type: 'underline';
  text: string;
  rects: Rect[];
}

interface ShapeAnnotation extends BaseAnnotation {
  type: 'shape';
  shapeType: 'rect' | 'circle' | 'arrow' | 'line';
  rect: Rect;            // 图形边界
  color: string;
  strokeWidth?: number;
}

interface NoteAnnotation extends BaseAnnotation {
  type: 'note';
  x: number;
  y: number;
  content: string;
  color?: string;
}

interface InkAnnotation extends BaseAnnotation {
  type: 'ink';
  points: { x: number; y: number }[][];
  color: string;
  strokeWidth: number;
}

type AnnotationType = 'highlight' | 'underline' | 'shape' | 'note' | 'ink';
type Annotation = HighlightAnnotation | UnderlineAnnotation 
  | ShapeAnnotation | NoteAnnotation | InkAnnotation;

interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}
```

---

## 第4章 标注侧边栏与快速跳转

### 4.1 侧边栏 UI 设计

标注侧边栏是类似 Zotero / UPDF 的核心交互组件，位于 PDF 阅读区左侧。它将所有标注按类型和颜色分组展示，每个标注项显示摘要文字和页码信息，点击即可跳转到 PDF 对应位置。

**侧边栏组件结构：**

```tsx
function AnnotationSidebar({ annotations, onJump }: Props) {
  // 按颜色分组高亮
  const highlightsByColor = useMemo(() => {
    const groups: Record<string, HighlightAnnotation[]> = {};
    Object.keys(COLOR_MAP).forEach(color => {
      groups[color] = annotations
        .filter(a => a.type === 'highlight' && a.color === color);
    });
    return groups;
  }, [annotations]);

  return (
    <div className="annotation-sidebar">
      <div className="sidebar-header">
        <h2>📚 标注列表</h2>
      </div>
      <div className="sidebar-content">
        {/* 高亮分组 */}
        {Object.entries(highlightsByColor).map(([color, items]) => (
          items.length > 0 && (
            <AnnotationGroup
              key={color}
              color={color}
              label={COLOR_MAP[color].name}
              items={items}
              onJump={onJump}
            />
          )
        ))}
        {/* 下划线分组 */}
        {/* 图形分组 */}
        {/* 注释分组 */}
      </div>
    </div>
  );
}
```

### 4.2 标注分类与颜色法则

参考 UPDF 视频中的做法，建立颜色法则可以大幅提升文献阅读效率。推荐的颜色分类方案如下：

| 颜色 | 分类名 | 用途 | RGB 值 |
|------|--------|------|--------|
| 🟡 黄色 | 核心观点 | 标注论文核心论点和结论 | rgba(255, 215, 0, 0.3) |
| 🟢 绿色 | 方法论 | 标注研究方法和实验设计 | rgba(76, 175, 80, 0.3) |
| 🔵 蓝色 | 存疑 | 标注有疑问或需要验证的内容 | rgba(33, 150, 243, 0.3) |
| 🩷 粉色 | 重要 | 标注重要数据和关键发现 | rgba(233, 30, 99, 0.3) |

> **【提示】** 颜色法则可以根据个人习惯自定义。建议在首次使用时提供引导设置，允许用户修改颜色分类名称和对应颜色。

### 4.3 点击跳转定位实现

点击侧边栏标注项跳转到 PDF 对应位置是提升阅读效率的关键功能。实现原理分为两步：滚动到目标页面，然后高亮闪烁目标标注。

```typescript
function jumpToAnnotation(annotation: Annotation) {
  const pageNum = annotation.pageNum;
  const pageContainer = document.getElementById('page-' + pageNum);

  if (!pageContainer) return;

  // 第一步：平滑滚动到目标页面
  pageContainer.scrollIntoView({
    behavior: 'smooth',
    block: 'center'
  });

  // 第二步：高亮闪烁目标标注
  setTimeout(() => {
    const overlays = document.querySelectorAll(
      '[data-id="' + annotation.id + '"]'
    );
    overlays.forEach(overlay => {
      overlay.classList.add('selected');
      // 2秒后移除高亮
      setTimeout(() => {
        overlay.classList.remove('selected');
      }, 2000);
    });
  }, 500); // 等待滚动完成
}
```

**CSS 高亮动画：**

```css
.highlight-overlay.selected {
  box-shadow: 0 0 0 3px #1976D2;
  animation: pulse 0.5s ease-in-out 3;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### 4.4 标注持久化存储

标注数据需要持久化存储，以保证用户关闭浏览器后标注不丢失。推荐使用 IndexedDB（适合大量结构化数据）或 localStorage（简单场景）。

```typescript
// 使用 IndexedDB 存储标注
class AnnotationDB {
  private dbName = 'pdf-reader-db';
  private storeName = 'annotations';

  async open(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: 'id' });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async save(annotation: Annotation) {
    const db = await this.open();
    const tx = db.transaction(this.storeName, 'readwrite');
    tx.objectStore(this.storeName).put(annotation);
  }

  async getAll(docId: string): Promise<Annotation[]> {
    const db = await this.open();
    const tx = db.transaction(this.storeName, 'readonly');
    return new Promise((resolve) => {
      const request = tx.objectStore(this.storeName).getAll();
      request.onsuccess = () => {
        resolve(request.result.filter(
          (a: Annotation) => a.docId === docId
        ));
      };
    });
  }

  async delete(id: string) {
    const db = await this.open();
    const tx = db.transaction(this.storeName, 'readwrite');
    tx.objectStore(this.storeName).delete(id);
  }
}
```

---

## 第5章 文献关联图谱

### 5.1 学术 API 对接

文献关联图谱的数据来源于学术 API。推荐使用 Semantic Scholar Academic Graph API，它提供免费的论文查询、引用关系获取服务，覆盖超过 2 亿篇学术论文。

**API 对比：**

| API | 免费额度 | 数据量 | 引用关系 | 推荐场景 |
|-----|---------|--------|---------|---------|
| Semantic Scholar | 5000次/月（无Key） | 2亿+ | 完整引用链 | 首选 |
| OpenAlex | 无限制 | 2.5亿+ | 完整引用链 | 大量请求 |
| CrossRef | 无限制 | 1.3亿+ | 基础引用 | DOI 查询 |
| PubMed E-utilities | 3次/秒 | 3500万+ | 有限 | 医学文献 |

**Semantic Scholar API 封装：**

```typescript
const API_BASE = 'https://api.semanticscholar.org/graph/v1';

// 通过 DOI 查询论文
async function getPaperByDOI(doi: string) {
  const fields = 'title,authors,year,citationCount,abstract,' +
    'references.title,references.year,references.citationCount,' +
    'citations.title,references.year,references.citationCount';
  const url = `${API_BASE}/paper/DOI:${encodeURIComponent(doi)}?fields=${fields}`;
  const response = await fetch(url);
  return response.json();
}

// 通过关键词搜索
async function searchPapers(query: string, limit = 10) {
  const fields = 'title,authors,year,citationCount,abstract';
  const url = `${API_BASE}/paper/search?query=${encodeURIComponent(query)}` +
    `&fields=${fields}&limit=${limit}`;
  const response = await fetch(url);
  return response.json();
}

// 获取论文的引用和参考文献
async function getCitationNetwork(paperId: string) {
  const fields = 'title,authors,year,citationCount,abstract';
  const url = `${API_BASE}/paper/${paperId}?fields=${fields}` +
    `&fields=${fields},citations(${fields}),references(${fields})`;
  const response = await fetch(url);
  return response.json();
}
```

### 5.2 图谱数据构建

从 API 获取论文数据后，需要将其转换为图谱数据结构（nodes + links），供 D3.js 力导向图使用。节点代表论文，边代表引用关系。

```typescript
interface GraphNode {
  id: string;
  title: string;
  authors: string;
  year: number;
  citationCount: number;
  abstract?: string;
  isSeed?: boolean;
}

interface GraphLink {
  source: string;
  target: string;
  type: 'references' | 'citedBy';
}

function buildGraphData(seedPaper: any): 
  { nodes: GraphNode[]; links: GraphLink[] } 
{
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const visited = new Set<string>();

  // 添加种子节点
  nodes.push({
    id: seedPaper.paperId,
    title: seedPaper.title,
    authors: seedPaper.authors?.map((a: any) => a.name).join(', '),
    year: seedPaper.year || 2020,
    citationCount: seedPaper.citationCount || 0,
    abstract: seedPaper.abstract,
    isSeed: true,
  });
  visited.add(seedPaper.paperId);

  // 添加参考文献
  seedPaper.references?.forEach((ref: any) => {
    if (ref.paperId && !visited.has(ref.paperId)) {
      nodes.push({
        id: ref.paperId,
        title: ref.title || 'Unknown',
        authors: ref.authors?.map((a: any) => a.name).join(', '),
        year: ref.year || 2020,
        citationCount: ref.citationCount || 0,
      });
      visited.add(ref.paperId);
    }
    if (ref.paperId) {
      links.push({ source: seedPaper.paperId, target: ref.paperId, 
                    type: 'references' });
    }
  });

  // 添加被引文献
  seedPaper.citations?.slice(0, 20).forEach((cit: any) => {
    if (cit.paperId && !visited.has(cit.paperId)) {
      nodes.push({
        id: cit.paperId,
        title: cit.title || 'Unknown',
        authors: cit.authors?.map((a: any) => a.name).join(', '),
        year: cit.year || 2020,
        citationCount: cit.citationCount || 0,
      });
      visited.add(cit.paperId);
    }
    if (cit.paperId) {
      links.push({ source: cit.paperId, target: seedPaper.paperId, 
                    type: 'citedBy' });
    }
  });

  return { nodes, links };
}
```

### 5.3 D3.js 力导向图可视化

D3.js 的力导向图（Force-Directed Graph）是展示文献关联关系的最佳方式。节点大小映射引用次数，颜色映射发表年份，箭头表示引用方向。

**D3.js 力导向图核心代码：**

```typescript
import * as d3 from 'd3';

function renderForceGraph(
  container: HTMLElement,
  data: { nodes: GraphNode[]; links: GraphLink[] }
) {
  const width = container.clientWidth;
  const height = container.clientHeight;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height);

  // 定义箭头标记
  svg.append('defs').append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M 0,-5 L 10,0 L 0,5')
    .attr('fill', '#45b7d1');

  // 创建力模拟
  const simulation = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(data.links).id(d => d.id).distance(150))
    .force('charge', d3.forceManyBody().strength(-500))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide()
      .radius(d => Math.sqrt(d.citationCount || 10) + 20));

  // 绘制连线
  const link = svg.append('g')
    .selectAll('line')
    .data(data.links)
    .enter().append('line')
    .attr('stroke', '#45b7d1')
    .attr('stroke-opacity', 0.6)
    .attr('marker-end', 'url(#arrowhead)');

  // 绘制节点
  const node = svg.append('g')
    .selectAll('g')
    .data(data.nodes)
    .enter().append('g')
    .call(d3.drag()
      .on('start', (e, d) => { 
        if (!e.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x; d.fy = d.y; 
      })
      .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
      .on('end', (e, d) => { 
        if (!e.active) simulation.alphaTarget(0);
        d.fx = null; d.fy = null; 
      })
    );

  // 节点圆形：大小 = 引用次数，颜色 = 年份
  node.append('circle')
    .attr('r', d => Math.sqrt(d.citationCount || 10) + 10)
    .attr('fill', d => yearToColor(d.year))
    .attr('stroke', d => d.isSeed ? '#E94560' : '#fff')
    .attr('stroke-width', d => d.isSeed ? 3 : 1);

  // 年份到颜色的映射函数
  function yearToColor(year: number): string {
    const age = new Date().getFullYear() - year;
    const hue = 180 - Math.min(age * 5, 120);
    return 'hsl(' + hue + ', 70%, 50%)';
  }

  // 更新位置
  simulation.on('tick', () => {
    link.attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
    node.attr('transform', d => 'translate(' + d.x + ',' + d.y + ')');
  });
}
```

### 5.4 节点交互与展开

图谱中的节点支持悬停显示详情、点击展开更多关联文献。点击某个节点时，会调用 API 获取该论文的引用关系，并将新节点和边动态添加到现有图谱中。

**节点交互代码：**

```typescript
// 悬停提示
node.on('mouseover', function(event, d) {
  tooltip.innerHTML = 
    '<div class="title">' + d.title + '</div>' +
    '<div class="meta">' +
    '  <span>👥 ' + d.authors + '</span>' +
    '  <span>📅 ' + d.year + '</span>' +
    '  <span>📊 ' + d.citationCount + ' 次引用</span>' +
    '</div>' +
    (d.abstract ? '<div class="abstract">' + 
      d.abstract.slice(0, 200) + '...</div>' : '');
  tooltip.style.opacity = '1';
  tooltip.style.left = (event.pageX + 15) + 'px';
  tooltip.style.top = (event.pageY - 10) + 'px';
});

// 点击展开
node.on('click', async function(event, d) {
  const paperData = await getCitationNetwork(d.id);
  const newData = buildGraphData(paperData);
  
  // 合并新数据到现有图谱
  newData.nodes.forEach(n => {
    if (!existingIds.has(n.id)) {
      data.nodes.push(n);
      existingIds.add(n.id);
    }
  });
  newData.links.forEach(l => {
    data.links.push(l);
  });
  
  // 重新渲染
  updateGraph(data);
});
```

---

## 第6章 开源项目参考

以下是实现 PDF 阅读器时可参考的开源项目，按推荐程度排序。

### 6.1 pdfjs-reader-core（强烈推荐）

pdfjs-reader-core 是一个 React 组件库，内置 PDF 渲染、搜索、高亮、标注等完整功能，是目前最接近本手册目标的开源方案。

| 属性 | 详情 |
|------|------|
| NPM 地址 | https://www.npmjs.com/package/pdfjs-reader-core |
| 最新版本 | 0.5.12 |
| 许可证 | MIT |
| 技术栈 | React + PDF.js + TypeScript |

**核心功能：**

| 功能 | API / Hook | 说明 |
|------|-----------|------|
| 页面导航 | `goToPage()`, `nextPage()`, `previousPage()` | 跳转到指定页 |
| 搜索 | `search()`, `searchResults`, `nextSearchResult()` | 全文搜索+高亮 |
| 高亮标注 | `addHighlight()`, `removeHighlight()` | 多颜色高亮 |
| 图形标注 | `addShape()` - rect/circle/arrow/line | 形状绘制 |
| 手绘批注 | `startDrawing()`, `addDrawingPoint()` | 自由绘画 |
| 文本注释 | `addNote()` | 便签式注释 |
| 侧边栏 | `<Sidebar />` 组件 | 内置标注列表 |
| 持久化 | `saveHighlights()`, `loadHighlights()` | localStorage |

### 6.2 PDFJsAnnotations

PDFJsAnnotations 基于 PDF.js + Fabric.js 实现，支持自由绘画、文字、箭头、矩形、图片等功能，每个对象都可以调整大小，并支持导出带标注的 PDF。

| 属性 | 详情 |
|------|------|
| GitHub | https://github.com/RavishaHesh/PDFJsAnnotations |
| 技术栈 | PDF.js + Fabric.js + jsPDF |
| 核心特点 | Fabric.js 画布层实现标注 |
| 导出功能 | 支持导出带标注的 PDF |

**快速启动：**

```bash
git clone https://github.com/RavishaHesh/PDFJsAnnotations.git
cd PDFJsAnnotations
npm install
npm start
# 浏览器打开 http://localhost:3000
```

### 6.3 Zotero

Zotero 是最知名的开源文献管理工具，其 PDF 阅读器标注系统非常成熟，是学习标注系统架构的最佳参考。

| 属性 | 详情 |
|------|------|
| GitHub | https://github.com/zotero/zotero |
| 技术栈 | XUL/HTML + JavaScript + SQLite |
| 核心特点 | 完整的文献管理 + PDF 阅读 + 标注系统 |
| 标注类型 | 高亮、下划线、文本注释、矩形、椭圆 |
| 值得参考 | 标注数据模型、侧边栏交互、标注导出 |

### 6.4 其他参考项目

| 项目 | 地址 | 特点 | 适用场景 |
|------|------|------|---------|
| pdfjs-viewer-pyside6 | pypi.org/project/pdfjs-viewer-pyside6 | Python + Qt 桌面应用 | 桌面端开发 |
| React-PDF | github.com/wojtekmaj/react-pdf | React PDF 渲染组件 | React 项目基础 |
| PDF.js Express | pdfjs.express | 商业 PDF SDK | 功能参考 |
| VOSviewer | vosviewer.com | 文献可视化工具 | 图谱可视化参考 |
| Connected Papers | connectedpapers.com | 文献关联图谱 | 产品形态参考 |
| opencite | pypi.org/project/opencite | 多源文献搜索 CLI | 后端数据获取 |

---

## 第7章 部署与进阶指南

### 7.1 项目初始化与构建

使用 Vite + React + TypeScript 初始化项目：

```bash
# 创建项目
npm create vite@latest pdf-reader -- --template react-ts
cd pdf-reader

# 安装核心依赖
npm install pdfjs-dist d3
npm install -D @types/d3

# 安装样式方案
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 安装状态管理（可选）
npm install zustand

# 启动开发
npm run dev
```

### 7.2 性能优化建议

| 优化点 | 方案 | 效果 |
|--------|------|------|
| 大文件渲染 | 虚拟滚动 + 按需渲染 | 内存占用降低 80%+ |
| 标注层性能 | 使用 Canvas 替代 DOM 元素 | 渲染速度提升 3-5x |
| 文本选择 | 合并相邻 span，减少 DOM 节点 | 选择响应速度提升 |
| 图谱渲染 | 限制节点数量（<200），使用 WebGL | 流畅交互 |
| API 缓存 | IndexedDB 缓存 API 响应 | 减少网络请求 |
| 图片懒加载 | IntersectionObserver | 首屏加载速度提升 |

### 7.3 功能扩展方向

| 功能 | 描述 | 技术方案 |
|------|------|---------|
| AI 对话 | 与 PDF 对话，自动提取摘要 | LLM API + PDF 文本提取 |
| 多人协作 | 实时同步标注 | WebSocket + CRDT |
| PDF 导出 | 将标注写入 PDF 文件 | PyMuPDF / jsPDF |
| 笔记导出 | 导出标注为 Markdown | 标注数据 → MD 转换 |
| OCR 支持 | 扫描版 PDF 文字识别 | Tesseract.js |
| 暗色模式 | 深色主题 | CSS 变量 + Tailwind |
| 快捷键 | 键盘操作标注 | 全局快捷键监听 |
| 标签管理 | 为标注添加自定义标签 | 标签系统 + 过滤器 |

> **【提示】** 推荐使用 Zustand 进行状态管理，它比 Redux 更轻量，API 更简洁，非常适合中等规模的 PDF 阅读器项目。

---

## 附录 A PyMuPDF 桌面端方案

如果需要桌面端应用或后端处理，可以使用 Python 的 PyMuPDF 库。它提供了完整的 PDF 标注 API，支持高亮、下划线、矩形、圆形、箭头、文本注释、手绘批注等所有标注类型，且标注直接写入 PDF 文件。

```python
import pymupdf

# 打开 PDF
doc = pymupdf.open("input.pdf")
page = doc[0]

# 高亮文字
areas = page.search_for("important text", quads=True)
annot = page.add_highlight_annot(areas[0])
annot.set_colors(stroke=(1, 1, 0))  # 黄色
annot.update()

# 下划线
annot = page.add_underline_annot(areas[0])
annot.set_colors(stroke=(0, 1, 0))  # 绿色
annot.update()

# 矩形标注
rect = pymupdf.Rect(100, 100, 200, 200)
annot = page.add_rect_annot(rect)
annot.set_colors(stroke=(1, 0, 0), fill=(1, 1, 0))
annot.update(opacity=0.5)

# 文本注释
annot = page.add_text_annot((300, 300), "This is a note")

# 手绘批注
points = [(100, 200), (110, 210), (120, 205)]
annot = page.add_ink_annot((points,))
annot.set_colors(stroke=(0, 0, 1))
annot.update()

# 保存
doc.save("output.pdf", deflate=True)
doc.close()
```

---

## 附录 B API 速率限制参考

| API | 无 Key 限制 | 有 Key 限制 | Key 申请 |
|-----|-------------|-------------|----------|
| Semantic Scholar | 100次/5分钟 | 5000次/月 | 官网免费申请 |
| OpenAlex | 10次/秒 | 无限制 | 邮箱注册即可 |
| CrossRef | 无限制 | 无限制 | 无需 Key |
| PubMed | 3次/秒 | 10次/秒 | 免费注册 |

---

## 附录 C 完整页面示例代码

以下是完整的单页 HTML 实现，包含了 PDF 渲染、文本选择、多种标注工具、侧边栏和快速跳转功能，可作为入门参考：

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>PDF 论文阅读器</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, sans-serif; display: flex; height: 100vh; }
        .sidebar { width: 320px; background: #fff; border-right: 1px solid #e0e0e0; overflow-y: auto; padding: 16px; }
        .main { flex: 1; display: flex; flex-direction: column; }
        .toolbar { padding: 10px 16px; background: #fff; border-bottom: 1px solid #e0e0e0; display: flex; gap: 8px; }
        .toolbar-btn { padding: 8px 12px; border: none; background: #f5f5f5; border-radius: 6px; cursor: pointer; }
        .toolbar-btn.active { background: #1976d2; color: white; }
        .pdf-container { flex: 1; overflow: auto; padding: 20px; background: #e0e0e0; }
        .page-container { position: relative; margin: 0 auto 20px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .text-layer { position: absolute; left: 0; top: 0; opacity: 0.2; }
        .annotation-layer { position: absolute; left: 0; top: 0; pointer-events: none; }
        .annotation-layer.active { pointer-events: auto; }
        .highlight-overlay { position: absolute; pointer-events: auto; cursor: pointer; }
        .annotation-group { margin-bottom: 16px; }
        .group-header { display: flex; align-items: center; padding: 8px 12px; background: #f8f9fa; border-radius: 6px; cursor: pointer; margin-bottom: 8px; }
        .group-color { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; }
        .group-title { flex: 1; font-size: 14px; font-weight: 500; }
        .group-count { font-size: 12px; color: #666; background: #e0e0e0; padding: 2px 8px; border-radius: 10px; }
        .annotation-item { padding: 10px 12px; margin-left: 20px; border-left: 3px solid; background: #fafafa; border-radius: 0 6px 6px 0; cursor: pointer; margin-bottom: 6px; }
        .annotation-item:hover { background: #f0f0f0; transform: translateX(2px); }
        .annotation-text { font-size: 13px; color: #333; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
        .annotation-meta { font-size: 11px; color: #999; margin-top: 6px; }
    </style>
</head>
<body>
    <!-- 左侧标注栏 -->
    <div class="sidebar">
        <div class="sidebar-header"><h2>📚 标注列表</h2></div>
        <div class="sidebar-content" id="annotationList"></div>
    </div>
    
    <!-- 主内容区 -->
    <div class="main">
        <div class="toolbar">
            <button class="toolbar-btn active" onclick="setTool('select')">↖ 选择</button>
            <button class="toolbar-btn" onclick="setTool('highlight', 'yellow')">🟡 高亮</button>
            <button class="toolbar-btn" onclick="setTool('underline')"><u>U</u> 下划线</button>
            <button class="toolbar-btn" onclick="setTool('rect')">▢ 矩形</button>
            <button class="toolbar-btn" onclick="setTool('note')">📝 注释</button>
        </div>
        <div class="pdf-container" id="pdfContainer"></div>
    </div>

    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        let annotations = { highlights: [], underlines: [], shapes: [], notes: [] };
        let currentTool = 'select';
        let currentColor = 'yellow';
        let pdfDoc = null;
        
        const COLOR_MAP = {
            yellow: { name: '核心观点', bg: 'rgba(255, 215, 0, 0.3)' },
            green: { name: '方法论', bg: 'rgba(76, 175, 80, 0.3)' },
            blue: { name: '存疑', bg: 'rgba(33, 150, 243, 0.3)' },
        };
        
        function setTool(tool, color) {
            currentTool = tool;
            currentColor = color || 'yellow';
            document.querySelectorAll('.toolbar-btn').forEach(b => b.classList.remove('active'));
            event.target.closest('.toolbar-btn')?.classList.add('active');
            document.querySelectorAll('.annotation-layer').forEach(l => 
                l.classList.toggle('active', tool !== 'select'));
        }
        
        async function loadPDF(url) {
            pdfDoc = await pdfjsLib.getDocument(url).promise;
            const container = document.getElementById('pdfContainer');
            for (let i = 1; i <= pdfDoc.numPages; i++) {
                await renderPage(i);
            }
            updateAnnotationList();
        }
        
        async function renderPage(pageNum) {
            const page = await pdfDoc.getPage(pageNum);
            const scale = 1.5;
            const viewport = page.getViewport({ scale });
            
            const pageContainer = document.createElement('div');
            pageContainer.className = 'page-container';
            pageContainer.id = 'page-' + pageNum;
            pageContainer.style.width = viewport.width + 'px';
            pageContainer.style.height = viewport.height + 'px';
            
            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            pageContainer.appendChild(canvas);
            
            const textLayer = document.createElement('div');
            textLayer.className = 'text-layer';
            textLayer.style.width = viewport.width + 'px';
            textLayer.style.height = viewport.height + 'px';
            pageContainer.appendChild(textLayer);
            
            const annotationLayer = document.createElement('div');
            annotationLayer.className = 'annotation-layer';
            annotationLayer.id = 'annotation-layer-' + pageNum;
            annotationLayer.style.width = viewport.width + 'px';
            annotationLayer.style.height = viewport.height + 'px';
            pageContainer.appendChild(annotationLayer);
            
            document.getElementById('pdfContainer').appendChild(pageContainer);
            
            await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise;
            
            const textContent = await page.getTextContent();
            await pdfjsLib.renderTextLayer({
                textContentSource: textContent,
                container: textLayer,
                viewport: viewport
            }).promise;
            
            // 绑定事件
            textLayer.addEventListener('mouseup', () => {
                const selection = window.getSelection();
                if (selection.rangeCount > 0 && selection.toString().trim()) {
                    if (currentTool === 'highlight') {
                        addHighlightAnnotation(selection, pageNum, annotationLayer);
                    } else if (currentTool === 'underline') {
                        addUnderlineAnnotation(selection, pageNum, annotationLayer);
                    }
                }
            });
            
            // ... 更多事件绑定
        }
        
        function addHighlightAnnotation(selection, pageNum, annotationLayer) {
            const range = selection.getRangeAt(0);
            const rects = range.getClientRects();
            const text = selection.toString();
            const layerRect = annotationLayer.getBoundingClientRect();
            
            const data = {
                id: Date.now().toString(),
                type: 'highlight', pageNum, text,
                color: currentColor,
                rects: [], timestamp: new Date().toISOString()
            };
            
            for (let rect of rects) {
                const overlay = document.createElement('div');
                overlay.className = 'highlight-overlay';
                overlay.style.left = (rect.left - layerRect.left) + 'px';
                overlay.style.top = (rect.top - layerRect.top) + 'px';
                overlay.style.width = rect.width + 'px';
                overlay.style.height = rect.height + 'px';
                overlay.style.background = COLOR_MAP[currentColor].bg;
                overlay.dataset.id = data.id;
                annotationLayer.appendChild(overlay);
                data.rects.push({ x: rect.left - layerRect.left, y: rect.top - layerRect.top, width: rect.width, height: rect.height });
            }
            
            annotations.highlights.push(data);
            updateAnnotationList();
            selection.removeAllRanges();
        }
        
        function updateAnnotationList() {
            const container = document.getElementById('annotationList');
            container.innerHTML = '';
            
            Object.entries(COLOR_MAP).forEach(([color, info]) => {
                const items = annotations.highlights.filter(h => h.color === color);
                if (items.length === 0) return;
                
                const group = document.createElement('div');
                group.className = 'annotation-group';
                group.innerHTML = `
                    <div class="group-header">
                        <span class="group-color" style="background:${color === 'yellow' ? '#ffd700' : color === 'green' ? '#4caf50' : '#2196f3'}"></span>
                        <span class="group-title">${info.name}</span>
                        <span class="group-count">${items.length}</span>
                    </div>`;
                
                items.forEach(item => {
                    const el = document.createElement('div');
                    el.className = 'annotation-item';
                    el.style.borderLeftColor = color === 'yellow' ? '#ffd700' : color === 'green' ? '#4caf50' : '#2196f3';
                    el.innerHTML = `<div class="annotation-text">"${item.text}"</div><div class="annotation-meta">第 ${item.pageNum} 页</div>`;
                    el.onclick = () => jumpToAnnotation(item);
                    group.appendChild(el);
                });
                
                container.appendChild(group);
            });
        }
        
        function jumpToAnnotation(annotation) {
            const pageContainer = document.getElementById('page-' + annotation.pageNum);
            if (pageContainer) {
                pageContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
        
        // 加载示例 PDF
        // loadPDF('your-document.pdf');
    </script>
</body>
</html>
```
