---
name: paper-assistant
description: AI 学术论文辅助系统。整合本地文献库(Zotero)、开放学术数据库(Semantic Scholar, CrossRef, arXiv)、多模型辅助撰写功能。支持：文献检索、论文摘要生成、参考文献管理、学术翻译、论文润色、查重检测。触发词：论文、学术、文献、查重、润色、翻译、参考文献、撰写论文。
---

# Paper Assistant - AI 学术论文辅助系统

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Paper Assistant                          │
├─────────────────────────────────────────────────────────────┤
│  📚 文献检索        │  🔍 学术搜索      │  ✍️ 论文撰写    │
│  ├─ Zotero 本地     │  ├─ Semantic     │  ├─ 摘要生成     │
│  ├─ Semantic Scholar │  ├─ CrossRef     │  ├─ 润色改写     │
│  ├─ arXiv           │  ├─ arXiv        │  ├─ 翻译         │
│  └─ CrossRef        │  └─ 百度学术     │  └─ 大纲生成    │
├─────────────────────────────────────────────────────────────┤
│                    🤖 多模型支持                             │
│  OpenAI GPT-4 / Claude 3 / Groq / Ollama 本地模型          │
└─────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. 文献检索

#### 1.1 Semantic Scholar API (推荐)

```bash
# 搜索学术论文
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=flotation+copper+sulfide&limit=10&fields=title,authors,abstract,year,citationCount"

# 获取论文详情
curl -s "https://api.semanticscholar.org/graph/v1/paper/PAPER_ID?fields=title,authors,abstract,year,citations,references"
```

#### 1.2 arXiv API

```bash
# 搜索预印本
curl -s "http://export.arxiv.org/api/query?search_query=all:flotation+copper&max_results=10"
```

#### 1.3 本地文献库

```bash
# 使用 Zotero 技能
python -X utf8 query_zotero.py search "关键词"
```

### 2. 论文分析

#### 2.1 提取 PDF 内容

使用 PDF 技能提取本地论文内容，参考 `references/pdf-extraction.md`

#### 2.2 生成摘要

```python
# scripts/summarize.py
def summarize_paper(text, model="gpt-4"):
    """生成论文摘要"""
    # 调用 LLM 生成简洁摘要
```

### 3. 写作辅助

#### 3.1 论文润色

```
输入: 原始文本
模型: GPT-4 / Claude
输出: 学术化润色后的文本
```

#### 3.2 翻译

```
中译英 / 英译中
保持学术术语准确性
```

#### 3.3 大纲生成

```
输入: 研究主题
输出: 完整论文大纲（摘要、引言、方法、结果、讨论、结论）
```

### 4. 参考文献管理

#### 4.1 生成引用

```python
# 支持格式: APA, MLA, Chicago, GB/T
def generate_citation(paper_info, style="apa"):
    """生成指定格式的引用"""
```

#### 4.2 检查重复

```
比对论文片段与已有文献的相似度
```

## 使用流程

### Step 1: 确定需求

- 📖 **文献调研** → 使用学术搜索 API
- 📝 **撰写论文** → 使用写作辅助功能
- 📚 **管理文献** → 整合 Zotero 本地库

### Step 2: 调用相应模块

```bash
# 文献检索
python scripts/search_papers.py --query "copper flotation" --source semantic

# 生成摘要
python scripts/summarize.py --file "paper.pdf"

# 论文润色
python scripts/polish.py --text "原始文本" --style academic
```

### Step 3: 结果输出

- 文献列表 → 可导出 BibTeX
- 摘要/翻译 → Markdown 格式
- 润色结果 → 直接复制使用

## 工作目录

- 技能位置: `skills/paper-assistant/`
- 工作空间: `papers/`
- 配置文件: `papers/config.json`

## 模型配置

系统支持多种语言模型，可在 `config.json` 中配置：

```json
{
  "models": {
    "primary": "openai/gpt-4",
    "fallback": "anthropic/claude-3-opus",
    "local": "ollama/llama3"
  }
}
```

## 参考文档

- `references/api-reference.md` - 各 API 详细文档
- `references/pdf-extraction.md` - PDF 提取方法
- `references/prompt-templates.md` - 提示词模板

## 注意事项

1. **API 限制**: Semantic Scholar 有频率限制，每分钟 100 次请求
2. **学术诚信**: AI 辅助仅限润色和参考，不可代写核心研究内容
3. **引用核实**: AI 生成的引用需人工核实准确性
