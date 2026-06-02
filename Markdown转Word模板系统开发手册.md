# Markdown 转 Word 模板系统开发手册

> **内置模板库 + 用户自定义格式 + 一键转换**
> 
> 涵盖：字体、行距、段落、题注图注、交叉引用、三线表、参考文献
> 
> 版本：v1.0 ｜ 日期：2025年5月

---

## 目录

- [第1章 项目概述与系统架构](#第1章-项目概述与系统架构)
  - [1.1 项目目标](#11-项目目标)
  - [1.2 系统架构设计](#12-系统架构设计)
  - [1.3 技术栈](#13-技术栈)
- [第2章 核心转换引擎：Pandoc](#第2章-核心转换引擎pandoc)
  - [2.1 Pandoc 基础](#21-pandoc-基础)
  - [2.2 reference-doc 模板机制](#22-reference-doc-模板机制)
  - [2.3 完整转换命令](#23-完整转换命令)
- [第3章 内置模板库](#第3章-内置模板库)
  - [3.1 国标 GB/T 7714 学术模板](#31-国标-gbt-7714-学术模板)
  - [3.2 APA 学术模板](#32-apa-学术模板)
  - [3.3 IEEE 工程模板](#33-ieee-工程模板)
  - [3.4 模板存储结构](#34-模板存储结构)
- [第4章 用户自定义格式系统](#第4章-用户自定义格式系统)
  - [4.1 格式配置项设计](#41-格式配置项设计)
  - [4.2 字体配置](#42-字体配置)
  - [4.3 段落与行距配置](#43-段落与行距配置)
  - [4.4 页边距与页眉页脚](#44-页边距与页眉页脚)
  - [4.5 题注图注配置](#45-题注图注配置)
  - [4.6 三线表配置](#46-三线表配置)
  - [4.7 模板预览与保存](#47-模板预览与保存)
- [第5章 交叉引用与参考文献](#第5章-交叉引用与参考文献)
  - [5.1 pandoc-crossref 交叉引用](#51-pandoc-crossref-交叉引用)
  - [5.2 citeproc 参考文献](#52-citeproc-参考文献)
  - [5.3 Zotero 集成](#53-zotero-集成)
- [第6章 核心代码实现](#第6章-核心代码实现)
  - [6.1 模板配置数据结构](#61-模板配置数据结构)
  - [6.2 模板生成器](#62-模板生成器)
  - [6.3 格式设置 UI 组件](#63-格式设置-ui-组件)
  - [6.4 一键转换流程](#64-一键转换流程)
- [第7章 部署与使用](#第7章-部署与使用)
  - [7.1 环境安装](#71-环境安装)
  - [7.2 快速开始](#72-快速开始)
  - [7.3 常见问题](#73-常见问题)

---

## 第1章 项目概述与系统架构

### 1.1 项目目标

本项目旨在构建一套 Markdown 转 Word 的模板系统，解决学术写作中的格式调整痛点。核心目标包括：

- **① 内置模板库**：预置国标 GB/T 7714、APA、IEEE 等常用学术模板，开箱即用。
- **② 用户自定义**：允许用户对字体、行距、段落、题注图注、页边距、页眉页脚等进行精细配置。
- **③ 一键转换**：一条命令完成 Markdown 到 Word 的转换，自动套用所有格式。
- **④ 学术功能**：支持交叉引用（图/表/公式/章节）、三线表、参考文献自动编号。

### 1.2 系统架构设计

系统采用四层架构设计，从上到下依次为用户层、核心转换层、模板管理层和输出层。用户在 Markdown 编辑器中编写内容，通过模板配置界面选择或自定义格式，核心转换层调用 Pandoc 引擎完成文档生成。

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户层                                      │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐ │
│  │  Markdown 编辑器  │  │  模板配置界面（格式设置面板）              │ │
│  └────────┬─────────┘  └──────────────┬───────────────────────┘ │
├───────────┼───────────────────────────┼───────────────────────────┤
│           ▼                           ▼                           │
│                     核心转换层                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Pandoc 引擎  ←→  pandoc-crossref  ←→  citeproc           │  │
│  │  （文档转换）      （交叉引用）        （文献引用）            │  │
│  └────────────────────────┬───────────────────────────────────┘  │
├───────────────────────────┼──────────────────────────────────────┤
│                           ▼                                      │
│                     模板管理层                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  内置模板库                    用户自定义模板                  │  │
│  │  ├─ GB/T 7714                  ├─ 模板 A                    │  │
│  │  ├─ APA 7th                    ├─ 模板 B                    │  │
│  │  └─ IEEE                       └─ ...                       │  │
│  │                                                            │  │
│  │  模板格式定义  ←→  模板存储管理  ←→  模板预览引擎            │  │
│  └────────────────────────┬───────────────────────────────────┘  │
├───────────────────────────┼──────────────────────────────────────┤
│                           ▼                                      │
│                     输出层                                        │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Word 文档（自动套用格式）  ←→  格式验证                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 技术栈

| 技术 | 用途 | 说明 |
|------|------|------|
| Pandoc | 文档转换引擎 | 支持 Markdown 到 Word 的高质量转换 |
| pandoc-crossref | 交叉引用过滤器 | 图/表/公式/章节自动编号与引用 |
| citeproc | 参考文献处理 | 支持 CSL 样式，自动生成参考文献列表 |
| Zotero + Better BibTeX | 文献管理 | 导出 .bib 文件，VSCode 插件快速插入引文 |
| Python / Node.js | 模板生成与自动化 | 动态生成 reference-doc 模板文件 |
| python-docx | Word 模板操作 | 通过 Python 代码修改 Word 样式定义 |

---

## 第2章 核心转换引擎：Pandoc

### 2.1 Pandoc 基础

Pandoc 是由 John MacFarlane 开发的开源通用文档转换器，被誉为"文档转换瑞士军刀"。它能够在数十种标记语言与页面格式之间进行高质量转换。对于本项目，我们主要使用其 Markdown 到 DOCX 的转换能力。

**安装方式：**

```bash
# macOS
brew install pandoc pandoc-crossref

# Windows
scoop install pandoc pandoc-crossref

# Linux
sudo apt install pandoc pandoc-crossref
```

> **【注意】** pandoc-crossref 的版本必须与 Pandoc 版本一致，否则会报错。使用 `pandoc --version` 和 `pandoc-crossref --version` 检查。

### 2.2 reference-doc 模板机制

Pandoc 的 `--reference-doc` 参数是实现"一键套用模板"的核心机制。其原理是：Pandoc 在转换时会读取指定的 Word 文件中的样式定义，然后将 Markdown 元素映射到对应的 Word 样式上。这意味着只要在模板文件中定义好格式，每次转换都会自动套用。

**导出默认模板的命令：**

```bash
pandoc -o custom-reference.docx --print-default-data-file reference.docx
```

打开导出的 `custom-reference.docx`，按 **F6** 打开样式面板，就可以看到 Pandoc 预定义的所有样式。右键任意样式选择"修改"即可调整字体、字号、段落等格式。

### 2.3 完整转换命令

以下是完整的一键转换命令，整合了模板套用、交叉引用和参考文献处理：

```bash
pandoc -F pandoc-crossref \
  --citeproc \
  --bibliography=ref.bib \
  --csl=china-national-standard-gb-t-7714-2015-numeric.csl \
  --reference-doc=my-template.docx \
  -M reference-section-title="参考文献" \
  -M link-citations=true \
  input.md -o output.docx
```

| 参数 | 作用 | 说明 |
|------|------|------|
| `-F pandoc-crossref` | 交叉引用 | 图/表/公式/章节自动编号 |
| `--citeproc` | 参考文献 | 处理文中引用并生成参考文献列表 |
| `--bibliography=ref.bib` | 文献库 | 指定 BibTeX 文献数据库文件 |
| `--csl=xxx.csl` | 引用样式 | 指定参考文献格式（GB/T、APA、IEEE等） |
| `--reference-doc=xxx.docx` | 套用模板 | **核心参数**，指定格式模板文件 |
| `-M link-citations=true` | 可点击引用 | 文中引用可点击跳转到参考文献 |

---

## 第3章 内置模板库

### 3.1 国标 GB/T 7714 学术模板

这是最常用的中文学术论文模板，符合国家标准 GB/T 7714-2015 要求。典型配置如下：

| 样式元素 | 中文字体 | 英文字体 | 字号 | 段落格式 |
|----------|----------|----------|------|----------|
| 一级标题 | 黑体 | Arial | 小三/加粗 | 居中，段前段后 0.5 行 |
| 二级标题 | 黑体 | Arial | 四号/加粗 | 左对齐，段前 0.3 行 |
| 三级标题 | 宋体 | Arial | 小四/加粗 | 左对齐，段前 0.2 行 |
| 正文 | 宋体 | Times New Roman | 五号 | 首行缩进 2 字符，行距 1.5 倍 |
| 图注 | 楷体 | Cambria | 小五 | 居中，图片下方 |
| 表注 | 楷体 | Cambria | 小五 | 居中，表格上方 |
| 脚注 | 宋体 | Times New Roman | 小五 | 默认 |
| 参考文献 | 宋体 | Times New Roman | 五号 | 悬挂缩进 |

### 3.2 APA 学术模板

APA 格式是社会科学领域最广泛使用的引用格式之一。与国标模板的主要区别在于：标题层级采用五级制、行距为双倍行距、段落首行缩进 0.5 英寸、参考文献采用悬挂缩进。

### 3.3 IEEE 工程模板

IEEE 格式主要用于工程技术领域。特点是双栏版面（左栏放置双栏标题）、标题采用罗马数字编号、参考文献采用方括号引用。

### 3.4 模板存储结构

模板文件按照以下目录结构组织：

```
templates/
├── builtin/              # 内置模板
│   ├── gbt-7714.docx       # 国标 GB/T 7714
│   ├── apa-7th.docx        # APA 第七版
│   ├── ieee.docx           # IEEE
│   └── thesis-sdufe.docx   # 学校论文模板
├── custom/              # 用户自定义模板
│   └── my-template.docx
├── csl/                 # CSL 引用样式文件
│   ├── china-national-standard-gb-t-7714-2015-numeric.csl
│   ├── apa-7th-edition.csl
│   └── ieee.csl
└── config/              # 模板配置 JSON
    ├── gbt-7714.json
    └── apa-7th.json
```

---

## 第4章 用户自定义格式系统

这是本系统的核心创新点。用户可以通过可视化界面或配置文件，对模板的所有格式参数进行精细控制，无需手动操作 Word 样式面板。

### 4.1 格式配置项设计

模板配置采用 JSON 格式存储，涵盖以下七大类配置项：

| 配置类别 | 具体参数 | 说明 |
|----------|----------|------|
| 字体配置 | 中文字体、英文字体、字号 | 每种样式元素可独立设置 |
| 行距配置 | 固定行距、多倍行距、段前段后距离 | 支持固定值和倍数两种模式 |
| 段落配置 | 对齐方式、首行缩进、左右缩进 | 支持居中/左对齐/右对齐/两端对齐 |
| 页边距 | 上下左右边距、装订线方向 | 支持纵横两种装订方向 |
| 页眉页脚 | 页眉文字、页脚页码、奇偶页区分 | 支持自定义页眉页脚内容 |
| 题注图注 | 字体、字号、位置、编号格式 | 图注在下/表注在上 |
| 三线表 | 线宽、线型、表头样式 | 顶线/表头线/底线独立配置 |

### 4.2 字体配置

用户可以为每种样式元素独立设置中英文字体和字号。配置示例：

```json
{
  "fonts": {
    "title":        { "cjk": "华文新魏", "ascii": "Arial",    "size": 18 },
    "heading1":     { "cjk": "黑体",     "ascii": "Arial",    "size": 15, "bold": true },
    "heading2":     { "cjk": "黑体",     "ascii": "Arial",    "size": 14, "bold": true },
    "heading3":     { "cjk": "宋体",     "ascii": "Arial",    "size": 12, "bold": true },
    "bodyText":     { "cjk": "宋体",     "ascii": "Times New Roman", "size": 10.5 },
    "figureCaption":{ "cjk": "楷体",     "ascii": "Cambria",  "size": 9 },
    "tableCaption": { "cjk": "楷体",     "ascii": "Cambria",  "size": 9 },
    "footnote":     { "cjk": "宋体",     "ascii": "Times New Roman", "size": 9 }
  }
}
```

> **【提示】** 字号单位为磅（pt），Word 中五号字对应 10.5pt，小四对应 12pt，小三对应 15pt。

### 4.3 段落与行距配置

```json
{
  "paragraph": {
    "bodyText": {
      "alignment": "justify",
      "firstLineIndent": 2,
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 0,
      "spaceAfter": 0
    },
    "heading1": {
      "alignment": "center",
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 12,
      "spaceAfter": 12
    },
    "heading2": {
      "alignment": "left",
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 6,
      "spaceAfter": 3
    }
  }
}
```

行距支持两种模式：`fixed`（固定值，单位磅）和 `multiple`（倍数，如 1.5 倍、2.0 倍）。首行缩进单位为字符数，学术论文通常设为 2。

### 4.4 页边距与页眉页脚

```json
{
  "page": {
    "size": "A4",
    "margin": { "top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17 },
    "header": {
      "text": "基于深度学习的图像分类研究",
      "font": { "cjk": "宋体", "ascii": "Times New Roman", "size": 9 },
      "alignment": "center",
      "borderBottom": true
    },
    "footer": {
      "showPageNumber": true,
      "format": "- %d -",
      "alignment": "center"
    }
  }
}
```

页边距单位为厘米（cm）。常见配置：学术论文上下 2.54cm、左右 3.17cm；学位论文上下 2.54cm、左 3cm、右 2cm。

### 4.5 题注图注配置

```json
{
  "captions": {
    "figure": {
      "position": "below",
      "prefix": "图",
      "numbering": "chapter",
      "template": "$$i$$ $t$",
      "font": { "cjk": "楷体", "ascii": "Cambria", "size": 9 },
      "alignment": "center",
      "spaceBefore": 6,
      "spaceAfter": 12
    },
    "table": {
      "position": "above",
      "prefix": "表",
      "numbering": "chapter",
      "template": "$$i$$ $t$",
      "font": { "cjk": "楷体", "ascii": "Cambria", "size": 9 },
      "alignment": "center",
      "spaceBefore": 12,
      "spaceAfter": 6
    }
  }
}
```

`position` 控制题注出现在图表的上方还是下方。`numbering` 模式支持 `chapter`（按章编号，如图 3-1）和 `continuous`（连续编号，如图 1）。

### 4.6 三线表配置

```json
{
  "tableStyle": {
    "type": "threeLine",
    "topBorder":    { "width": 1.5, "style": "single", "color": "000000" },
    "headerBorder": { "width": 0.5, "style": "single", "color": "000000" },
    "bottomBorder": { "width": 1.5, "style": "single", "color": "000000" },
    "innerBorder":  "none",
    "headerShading": { "fill": "FFFFFF" },
    "cellPadding":   { "top": 40, "bottom": 40, "left": 80, "right": 80 }
  }
}
```

三线表是学术论文中最常用的表格样式，由顶线、表头分隔线和底线三条横线组成，其他线条均不显示。顶线和底线通常为 1.5 磅，表头分隔线为 0.5 磅。

### 4.7 模板预览与保存

用户配置完格式后，系统会生成一个预览文档，让用户确认效果。确认后保存为自定义模板，可供后续复用。模板保存时会同时存储两份：JSON 配置文件（可编辑）和 .docx 模板文件（给 Pandoc 使用）。

> **【提示】** 建议将自定义模板纳入版本管理（Git），方便团队协作和格式回溯。

---

## 第5章 交叉引用与参考文献

### 5.1 pandoc-crossref 交叉引用

pandoc-crossref 是 Pandoc 的过滤器，用于对图片、表格、公式、章节等进行自动编号和交叉引用。Markdown 中的语法如下：

| 引用类型 | Markdown 语法 | 示例 |
|----------|---------------|------|
| 章节引用 | `章节标题 {#sec:label}` | `## 引言 {#sec:intro}` |
| 图片引用 | `![题注](路径){#fig:label}` | `![架构图](fig.png){#fig:arch}` |
| 表格引用 | `: 题注 {#tbl:label}` | `: 实验结果 {#tbl:result}` |
| 公式引用 | `$$ 公式 $$ {#eq:label}` | `$$ E=mc^2 $$ {#eq:einstein}` |
| 引用处 | `@前缀:label` 或 `[@前缀:label]` | `如 @fig:arch 所示...` |

在 YAML 头部可配置编号样式：

```yaml
---
figureTitle: "图"
tableTitle: "表"
equationTitle: "公式"
figureTitleTemplate: "$$i$$ $t$"   # 输出：图 3-1 模型架构
tableTitleTemplate: "$$i$$ $t$"    # 输出：表 3-1 实验结果
---
```

**Markdown 写法示例：**

```markdown
## 引言 {#sec:introduction}

如第 @sec:methods 节所述...

## 方法 {#sec:methods}

### 数据集

实验结果如 @tbl:result 所示。

| 模型 | 准确率 | F1值 |
|:-----|-------:|-----:|
| ResNet | 95.2% | 0.94 |
| VGG | 93.1% | 0.91 |
| Ours | 97.8% | 0.97 |

: 模型性能对比 {#tbl:result}

### 模型架构

模型结构如 @fig:architecture 所示。

![模型整体架构图](./figures/architecture.png){#fig:architecture}

### 公式

损失函数定义如 @eq:loss：

$$L = -\frac{1}{N}\sum_{i=1}^{N}[y_i \log(\hat{y}_i) + (1-y_i)\log(1-\hat{y}_i)]$$ {#eq:loss}
```

### 5.2 citeproc 参考文献

Pandoc 内置的 citeproc 引擎可以自动处理文中引用并生成参考文献列表。Markdown 中的引用语法为 `[@CitationKey]`。不同的 CSL 样式文件决定了参考文献的呈现格式。

**CSL 样式文件下载地址：** https://www.zotero.org/styles

**Markdown 中的引用写法：**

```markdown
根据已有研究 [@zhang2020deep; @li2021transformer]，深度学习在图像分类领域取得了显著进展。
Zhang 等 [@zhang2020deep] 提出了...
```

**控制参考文献出现位置：**

```markdown
## 参考文献
::: {#refs}
:::
```

### 5.3 Zotero 集成

推荐使用 Zotero + Better BibTeX 插件进行文献管理。工作流程如下：

1. **安装 Zotero** 主程序 + Better BibTeX 插件 + 浏览器插件 Zotero Connector
2. **VSCode 安装插件**：`Citation Picker for Zotero`，按 `Alt+Shift+Z` 快速插入引文
3. **导出文献库**：从 Zotero 导出所有文献为 `.bib` 文件
4. **Pandoc 转换**：通过 `--bibliography` 参数指定 `.bib` 文件

```
Zotero 文献库 → Better BibTeX 导出 .bib → Pandoc 自动引用
```

---

## 第6章 核心代码实现

### 6.1 模板配置数据结构

以下是完整的模板配置 TypeScript 类型定义：

```typescript
interface TemplateConfig {
  name: string;
  description: string;
  fonts: {
    title?:         FontConfig;
    heading1?:      FontConfig;
    heading2?:      FontConfig;
    heading3?:      FontConfig;
    bodyText?:      FontConfig;
    figureCaption?: FontConfig;
    tableCaption?:  FontConfig;
    footnote?:      FontConfig;
  };
  paragraph: {
    bodyText?:  ParagraphConfig;
    heading1?:  ParagraphConfig;
    heading2?:  ParagraphConfig;
    heading3?:  ParagraphConfig;
  };
  page: {
    size?: "A4" | "Letter";
    orientation?: "portrait" | "landscape";
    margin?: { top: number; bottom: number; left: number; right: number };
    header?: HeaderFooterConfig;
    footer?: HeaderFooterConfig;
  };
  captions: {
    figure?: CaptionConfig;
    table?:  CaptionConfig;
  };
  tableStyle?: TableStyleConfig;
  bibliography?: {
    cslFile: string;
    style: string;
  };
}

interface FontConfig {
  cjk: string;       // 中文字体
  ascii: string;     // 英文字体
  size: number;      // 字号（磅）
  bold?: boolean;
  italic?: boolean;
  color?: string;
}

interface ParagraphConfig {
  alignment?: "left" | "center" | "right" | "justify";
  firstLineIndent?: number;   // 首行缩进（字符数）
  lineSpacing?: {
    type: "fixed" | "multiple";  // 固定值 or 倍数
    value: number;
  };
  spaceBefore?: number;  // 段前间距（磅）
  spaceAfter?: number;   // 段后间距（磅）
}

interface CaptionConfig {
  position: "above" | "below";
  prefix: string;
  numbering: "chapter" | "continuous";
  template: string;
  font: FontConfig;
  alignment: string;
}

interface TableStyleConfig {
  type: "threeLine" | "fullBorder" | "custom";
  topBorder?:    BorderConfig;
  headerBorder?: BorderConfig;
  bottomBorder?: BorderConfig;
}

interface BorderConfig {
  width: number;
  style: "single" | "double" | "dotted";
  color: string;
}
```

### 6.2 模板生成器

模板生成器负责将 JSON 配置转换为 Pandoc 可用的 .docx 模板文件。它通过 python-docx 库操作 Word 的样式定义，实现配置到模板的自动化转换：

```python
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
import json

class TemplateGenerator:
    """根据 JSON 配置生成 Pandoc reference-doc 模板"""

    def __init__(self, config: dict):
        self.config = config
        self.doc = Document()

    def generate(self, output_path: str):
        # 设置页边距
        page = self.config.get("page", {})
        margin = page.get("margin", {})
        for section in self.doc.sections:
            section.top_margin = Cm(margin.get("top", 2.54))
            section.bottom_margin = Cm(margin.get("bottom", 2.54))
            section.left_margin = Cm(margin.get("left", 3.17))
            section.right_margin = Cm(margin.get("right", 3.17))

        # 设置样式
        self._setup_styles()
        # 设置页眉页脚
        self._setup_header_footer()
        # 添加示例内容
        self._add_sample_content()
        # 保存
        self.doc.save(output_path)
        print(f"✅ 模板已生成: {output_path}")

    def _setup_styles(self):
        fonts = self.config.get("fonts", {})
        para = self.config.get("paragraph", {})

        # === 正文样式 ===
        body_font = fonts.get("bodyText", {})
        body_para = para.get("bodyText", {})
        style = self.doc.styles['Normal']
        style.font.name = body_font.get("ascii", "Times New Roman")
        style.font.size = Pt(body_font.get("size", 10.5))
        # 设置中文字体
        style.element.rPr.rFonts.set(
            qn('w:eastAsia'),
            body_font.get("cjk", "宋体")
        )
        # 段落格式
        pf = style.paragraph_format
        alignment_map = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        pf.alignment = alignment_map.get(
            body_para.get("alignment", "justify"),
            WD_ALIGN_PARAGRAPH.JUSTIFY
        )
        # 首行缩进
        indent = body_para.get("firstLineIndent", 2)
        pf.first_line_indent = Pt(body_font.get("size", 10.5) * indent)
        # 行距
        ls = body_para.get("lineSpacing", {})
        if ls.get("type") == "multiple":
            pf.line_spacing = ls.get("value", 1.5)

        # === 一级标题样式 ===
        h1_font = fonts.get("heading1", {})
        h1_para = para.get("heading1", {})
        h1_style = self.doc.styles['Heading 1']
        h1_style.font.name = h1_font.get("ascii", "Arial")
        h1_style.font.size = Pt(h1_font.get("size", 15))
        h1_style.font.bold = h1_font.get("bold", True)
        h1_style.element.rPr.rFonts.set(
            qn('w:eastAsia'),
            h1_font.get("cjk", "黑体")
        )
        h1_pf = h1_style.paragraph_format
        h1_pf.alignment = alignment_map.get(
            h1_para.get("alignment", "center"),
            WD_ALIGN_PARAGRAPH.CENTER
        )
        h1_pf.space_before = Pt(h1_para.get("spaceBefore", 12))
        h1_pf.space_after = Pt(h1_para.get("spaceAfter", 12))

        # === 二级标题样式 ===
        h2_font = fonts.get("heading2", {})
        h2_para = para.get("heading2", {})
        h2_style = self.doc.styles['Heading 2']
        h2_style.font.name = h2_font.get("ascii", "Arial")
        h2_style.font.size = Pt(h2_font.get("size", 14))
        h2_style.font.bold = h2_font.get("bold", True)
        h2_style.element.rPr.rFonts.set(
            qn('w:eastAsia'),
            h2_font.get("cjk", "黑体")
        )
        h2_pf = h2_style.paragraph_format
        h2_pf.alignment = alignment_map.get(
            h2_para.get("alignment", "left"),
            WD_ALIGN_PARAGRAPH.LEFT
        )

        # === 新建图注样式 ===
        fig_font = fonts.get("figureCaption", {})
        fig_para = self.config.get("captions", {}).get("figure", {})
        fig_style = self.doc.styles.add_style(
            'Figure Caption',
            self.doc.styles['Normal']
        )
        fig_style.font.name = fig_font.get("ascii", "Cambria")
        fig_style.font.size = Pt(fig_font.get("size", 9))
        fig_style.element.rPr.rFonts.set(
            qn('w:eastAsia'),
            fig_font.get("cjk", "楷体")
        )
        fig_style.paragraph_format.alignment = alignment_map.get(
            fig_para.get("alignment", "center"),
            WD_ALIGN_PARAGRAPH.CENTER
        )

        # === 新建表注样式 ===
        tbl_font = fonts.get("tableCaption", {})
        tbl_para = self.config.get("captions", {}).get("table", {})
        tbl_style = self.doc.styles.add_style(
            'Table Caption',
            self.doc.styles['Normal']
        )
        tbl_style.font.name = tbl_font.get("ascii", "Cambria")
        tbl_style.font.size = Pt(tbl_font.get("size", 9))
        tbl_style.element.rPr.rFonts.set(
            qn('w:eastAsia'),
            tbl_font.get("cjk", "楷体")
        )
        tbl_style.paragraph_format.alignment = alignment_map.get(
            tbl_para.get("alignment", "center"),
            WD_ALIGN_PARAGRAPH.CENTER
        )

    def _setup_header_footer(self):
        page = self.config.get("page", {})
        header_cfg = page.get("header", {})
        if header_cfg.get("text"):
            header = self.doc.sections[0].header
            header_para = header.paragraphs[0]
            header_para.text = header_cfg["text"]
            header_para.alignment = alignment_map.get(
                header_cfg.get("alignment", "center"),
                WD_ALIGN_PARAGRAPH.CENTER
            )
            # 页眉底部边框线
            from docx.oxml import OxmlElement
            pPr = header_para._p.get_or_add_pPr()
            pBdr = OxmlElement('w:pBdr')
            bottom = OxmlElement('w:bottom')
            bottom.set(qn('w:val'), 'single')
            bottom.set(qn('w:sz'), '4')
            bottom.set(qn('w:space'), '1')
            bottom.set(qn('w:color'), '000000')
            pBdr.append(bottom)
            pPr.append(pBdr)

        footer_cfg = page.get("footer", {})
        if footer_cfg.get("showPageNumber"):
            from docx.oxml.ns import qn
            from docx.oxml import OxmlElement
            footer = self.doc.sections[0].footer
            footer_para = footer.paragraphs[0]
            footer_para.alignment = alignment_map.get(
                footer_cfg.get("alignment", "center"),
                WD_ALIGN_PARAGRAPH.CENTER
            )
            # 添加页码字段
            run = footer_para.add_run()
            fldChar1 = OxmlElement('w:fldChar')
            fldChar1.set(qn('w:fldCharType'), 'begin')
            run._r.append(fldChar1)

            instrText = OxmlElement('w:instrText')
            instrText.set(qn('xml:space'), 'preserve')
            instrText.text = ' PAGE '
            run._r.append(instrText)

            fldChar2 = OxmlElement('w:fldChar')
            fldChar2.set(qn('w:fldCharType'), 'end')
            run._r.append(fldChar2)

    def _add_sample_content(self):
        """添加示例内容用于预览"""
        self.doc.add_heading('一级标题示例', level=1)
        self.doc.add_paragraph('这是正文内容示例。正文采用宋体五号字，首行缩进两个字符，1.5倍行距。')
        self.doc.add_heading('二级标题示例', level=2)
        self.doc.add_paragraph('这是二级标题下的正文内容。')
        self.doc.add_heading('三级标题示例', level=3)
        self.doc.add_paragraph('这是三级标题下的正文内容。')


# 使用示例
if __name__ == "__main__":
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    generator = TemplateGenerator(config)
    generator.generate("my-template.docx")
```

### 6.3 格式设置 UI 组件

前端格式设置界面提供可视化的模板配置体验。用户可以通过表单、下拉框、颜色选择器等控件调整所有格式参数，实时预览效果。以下是 React 组件的核心结构：

```tsx
import React, { useState } from 'react';

interface TemplateEditorProps {
  config: TemplateConfig;
  onChange: (config: TemplateConfig) => void;
}

function TemplateEditor({ config, onChange }: TemplateEditorProps) {
  const [activeTab, setActiveTab] = useState("字体");

  return (
    <div className="template-editor">
      {/* 标签页导航 */}
      <TabBar
        tabs={["字体", "段落", "页面", "题注", "表格"]}
        active={activeTab}
        onChange={setActiveTab}
      />

      {/* 各配置面板 */}
      {activeTab === "字体" && (
        <FontPanel config={config} onChange={onChange} />
      )}
      {activeTab === "段落" && (
        <ParagraphPanel config={config} onChange={onChange} />
      )}
      {activeTab === "页面" && (
        <PagePanel config={config} onChange={onChange} />
      )}
      {activeTab === "题注" && (
        <CaptionPanel config={config} onChange={onChange} />
      )}
      {activeTab === "表格" && (
        <TablePanel config={config} onChange={onChange} />
      )}

      {/* 操作按钮 */}
      <div className="actions">
        <button onClick={handlePreview}>预览效果</button>
        <button onClick={handleSave}>保存模板</button>
        <button onClick={handleExport}>导出配置</button>
      </div>
    </div>
  );
}

// 字体配置面板
function FontPanel({ config, onChange }) {
  const updateFont = (key: string, field: string, value: any) => {
    onChange({
      ...config,
      fonts: {
        ...config.fonts,
        [key]: { ...config.fonts[key], [field]: value },
      },
    });
  };

  return (
    <div className="font-panel">
      {Object.entries(config.fonts).map(([key, font]) => (
        <div key={key} className="font-item">
          <h4>{key}</h4>
          <label>
            中文字体：
            <select
              value={font.cjk}
              onChange={(e) => updateFont(key, 'cjk', e.target.value)}
            >
              <option value="宋体">宋体</option>
              <option value="黑体">黑体</option>
              <option value="楷体">楷体</option>
              <option value="仿宋">仿宋</option>
              <option value="华文新魏">华文新魏</option>
            </select>
          </label>
          <label>
            英文字体：
            <select
              value={font.ascii}
              onChange={(e) => updateFont(key, 'ascii', e.target.value)}
            >
              <option value="Times New Roman">Times New Roman</option>
              <option value="Arial">Arial</option>
              <option value="Cambria">Cambria</option>
              <option value="Calibri">Calibri</option>
            </select>
          </label>
          <label>
            字号：
            <input
              type="number"
              value={font.size}
              onChange={(e) => updateFont(key, 'size', Number(e.target.value))}
              step="0.5"
              min="8"
              max="72"
            />
          </label>
          <label>
            加粗：
            <input
              type="checkbox"
              checked={font.bold || false}
              onChange={(e) => updateFont(key, 'bold', e.target.checked)}
            />
          </label>
        </div>
      ))}
    </div>
  );
}
```

### 6.4 一键转换流程

```typescript
import { execSync } from "child_process";
import path from "path";

interface ConvertOptions {
  inputFile: string;
  outputFile: string;
  templatePath: string;
  bibFile?: string;
  cslFile?: string;
  refTitle?: string;
}

function convertMarkdownToWord(options: ConvertOptions) {
  const {
    inputFile,
    outputFile,
    templatePath,
    bibFile,
    cslFile,
    refTitle = "参考文献",
  } = options;

  // 构建 Pandoc 命令
  const args = [
    "pandoc",
    "-F", "pandoc-crossref",
    "--reference-doc", templatePath,
    "-M", `reference-section-title=${refTitle}`,
    "-M", "link-citations=true",
  ];

  // 可选：参考文献
  if (bibFile) {
    args.push("--citeproc");
    args.push("--bibliography", bibFile);
  }
  if (cslFile) {
    args.push("--csl", cslFile);
  }

  args.push(inputFile, "-o", outputFile);

  // 执行转换
  execSync(args.join(" "), { stdio: "inherit" });
  console.log("✔ 已生成: " + outputFile);
}

// 使用示例
convertMarkdownToWord({
  inputFile: "paper.md",
  outputFile: "paper.docx",
  templatePath: "templates/custom/my-template.docx",
  bibFile: "ref.bib",
  cslFile: "templates/csl/china-national-standard-gb-t-7714-2015-numeric.csl",
});
```

**封装为 shell 脚本（真正的一键转换）：**

```bash
#!/bin/bash
# convert.sh - 一键 Markdown 转 Word

INPUT=${1:-"input.md"}
OUTPUT="${INPUT%.md}.docx"
TEMPLATE="templates/custom/my-template.docx"
BIB="ref.bib"
CSL="templates/csl/china-national-standard-gb-t-7714-2015-numeric.csl"

pandoc -F pandoc-crossref \
  --citeproc \
  --bibliography="$BIB" \
  --csl="$CSL" \
  --reference-doc="$TEMPLATE" \
  -M reference-section-title="参考文献" \
  -M link-citations=true \
  "$INPUT" -o "$OUTPUT"

echo "✅ 已生成: $OUTPUT"
```

使用方式：

```bash
chmod +x convert.sh
./convert.sh my-paper.md
```

---

## 第7章 部署与使用

### 7.1 环境安装

```bash
# 1. 安装 Pandoc 和 pandoc-crossref
brew install pandoc pandoc-crossref    # macOS
scoop install pandoc pandoc-crossref   # Windows

# 2. 安装 Python 依赖
pip install python-docx

# 3. 克隆项目
git clone https://github.com/your-repo/md2word-template.git
cd md2word-template
npm install
```

### 7.2 快速开始

| 步骤 | 操作 | 说明 |
|------|------|------|
| **步骤 1** | 选择内置模板或创建自定义模板 | 从模板库中选择，或从空白开始 |
| **步骤 2** | 在配置界面调整格式参数 | 字体、行距、段落、页边距等 |
| **步骤 3** | 预览确认后保存模板 | 生成 .docx 模板文件 + JSON 配置文件 |
| **步骤 4** | 编写 Markdown 文档 | 使用交叉引用语法标注图表 |
| **步骤 5** | 执行一键转换命令 | 生成最终 Word 文档 |

### 7.3 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 转换后样式未生效 | `--reference-doc` 路径错误 | 检查模板文件路径是否正确 |
| 图注表注不显示 | 模板中缺少对应样式 | 在模板中新建 Figure/Table Caption 样式 |
| 交叉引用显示原始标记 | 未安装 pandoc-crossref | 确认安装且版本与 Pandoc 一致 |
| 参考文献未生成 | `--citeproc` 位置错误 | 必须放在 `-F pandoc-crossref` 之后 |
| 中文乱码 | 模板字体缺少中文字体 | 确保每个样式都设置了 eastAsia 字体 |
| 三线表需要手动调整 | Pandoc 表格支持有限 | 转换后在 Word 中手动应用表格样式 |
| 行距不符合预期 | 模板样式行距未正确设置 | 检查样式的段落格式 > 行距设置 |
| 公式渲染异常 | LaTeX 语法错误 | 确认使用 `$...$` 行内和 `$$...$$` 行间公式语法 |

> **【提示】** 建议将常用的转换命令封装为 shell 脚本或 npm scripts，实现真正的一键转换。例如在 `package.json` 中添加：
> ```json
> "scripts": {
>   "convert": "pandoc -F pandoc-crossref --reference-doc=templates/my-template.docx input.md -o output.docx"
> }
> ```

---

## 附录 A：完整配置文件示例

以下是一个完整的国标 GB/T 7714 模板配置文件 `gbt-7714.json`：

```json
{
  "name": "国标 GB/T 7714 学术模板",
  "description": "符合 GB/T 7714-2015 标准的中文学术论文格式",
  "fonts": {
    "title":         { "cjk": "华文新魏", "ascii": "Arial",    "size": 18 },
    "heading1":      { "cjk": "黑体",     "ascii": "Arial",    "size": 15, "bold": true },
    "heading2":      { "cjk": "黑体",     "ascii": "Arial",    "size": 14, "bold": true },
    "heading3":      { "cjk": "宋体",     "ascii": "Arial",    "size": 12, "bold": true },
    "bodyText":      { "cjk": "宋体",     "ascii": "Times New Roman", "size": 10.5 },
    "figureCaption": { "cjk": "楷体",     "ascii": "Cambria",  "size": 9 },
    "tableCaption":  { "cjk": "楷体",     "ascii": "Cambria",  "size": 9 },
    "footnote":      { "cjk": "宋体",     "ascii": "Times New Roman", "size": 9 }
  },
  "paragraph": {
    "bodyText": {
      "alignment": "justify",
      "firstLineIndent": 2,
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 0,
      "spaceAfter": 0
    },
    "heading1": {
      "alignment": "center",
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 12,
      "spaceAfter": 12
    },
    "heading2": {
      "alignment": "left",
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 6,
      "spaceAfter": 3
    },
    "heading3": {
      "alignment": "left",
      "lineSpacing": { "type": "multiple", "value": 1.5 },
      "spaceBefore": 3,
      "spaceAfter": 1.5
    }
  },
  "page": {
    "size": "A4",
    "margin": { "top": 2.54, "bottom": 2.54, "left": 3.17, "right": 3.17 },
    "header": {
      "text": "",
      "font": { "cjk": "宋体", "ascii": "Times New Roman", "size": 9 },
      "alignment": "center",
      "borderBottom": false
    },
    "footer": {
      "showPageNumber": true,
      "format": "- %d -",
      "alignment": "center"
    }
  },
  "captions": {
    "figure": {
      "position": "below",
      "prefix": "图",
      "numbering": "chapter",
      "template": "$$i$$ $t$",
      "font": { "cjk": "楷体", "ascii": "Cambria", "size": 9 },
      "alignment": "center",
      "spaceBefore": 6,
      "spaceAfter": 12
    },
    "table": {
      "position": "above",
      "prefix": "表",
      "numbering": "chapter",
      "template": "$$i$$ $t$",
      "font": { "cjk": "楷体", "ascii": "Cambria", "size": 9 },
      "alignment": "center",
      "spaceBefore": 12,
      "spaceAfter": 6
    }
  },
  "tableStyle": {
    "type": "threeLine",
    "topBorder":    { "width": 1.5, "style": "single", "color": "000000" },
    "headerBorder": { "width": 0.5, "style": "single", "color": "000000" },
    "bottomBorder": { "width": 1.5, "style": "single", "color": "000000" },
    "innerBorder":  "none",
    "headerShading": { "fill": "FFFFFF" },
    "cellPadding":   { "top": 40, "bottom": 40, "left": 80, "right": 80 }
  },
  "bibliography": {
    "cslFile": "china-national-standard-gb-t-7714-2015-numeric.csl",
    "style": "numeric"
  }
}
```

## 附录 B：CSL 样式文件常用下载

| 样式名称 | 下载文件名 | 适用领域 |
|----------|------------|----------|
| 国标 GB/T 7714 | `china-national-standard-gb-t-7714-2015-numeric.csl` | 中文学术论文 |
| APA 第七版 | `apa-7th-edition.csl` | 社会科学 |
| IEEE | `ieee.csl` | 工程技术 |
| Chicago | `chicago-author-date.csl` | 人文学科 |
| MLA | `modern-language-association.csl` | 语言文学 |
| Vancouver | `vancouver.csl` | 医学卫生 |

下载地址：https://www.zotero.org/styles

## 附录 C：Markdown 写作完整示例

```markdown
---
title: "基于深度学习的图像分类研究"
author: "张三"
date: "2025年5月"
bibliography: [./ref.bib]
csl: china-national-standard-gb-t-7714-2015-numeric.csl
link-citations: true
reference-section-title: "参考文献"
tables:
  position: top
figureTitle: "图"
tableTitle: "表"
figureTitleTemplate: "$$i$$ $t$"
tableTitleTemplate: "$$i$$ $t$"
---

## 引言 {#sec:intro}

深度学习在计算机视觉领域取得了突破性进展 [@zhang2020deep; @li2021transformer]。
如第 @sec:method 节所述，本文提出了一种新的图像分类方法。

## 方法 {#sec:method}

### 数据集

实验使用 ImageNet 数据集，包含 1000 个类别、120 万张训练图像。
实验结果如 @tbl:result 所示。

| 模型 | 准确率 | F1值 | 参数量 |
|:-----|-------:|-----:|-------:|
| ResNet-50 | 95.2% | 0.94 | 25.6M |
| VGG-16 | 93.1% | 0.91 | 138.4M |
| Ours | 97.8% | 0.97 | 18.2M |

: 不同模型在 ImageNet 上的性能对比 {#tbl:result}

### 模型架构

模型整体结构如图 @fig:arch 所示。该模型采用轻量级设计，
在保持高精度的同时显著降低了计算开销。

![模型整体架构图](./figures/architecture.png){#fig:arch}

### 损失函数

损失函数定义如 @eq:loss 所示：

$$L = -\frac{1}{N}\sum_{i=1}^{N}[y_i \log(\hat{y}_i) + (1-y_i)\log(1-\hat{y}_i)]$$ {#eq:loss}

## 结论 {#sec:conclusion}

本文提出的模型在 ImageNet 数据集上达到了 97.8% 的准确率，
超越了现有方法。

## 参考文献
::: {#refs}
:::
```
```
