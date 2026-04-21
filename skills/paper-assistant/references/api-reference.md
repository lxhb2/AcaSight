# 学术数据库 API 参考

## 1. Semantic Scholar

**API 文档**: https://api.semanticscholar.org/

**特点**:
- 免费，无需 API key
- 包含 2 亿+ 学术论文
- 提供论文摘要、引用、作者信息

### 基础调用

```bash
# 搜索论文
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=flotation&limit=10"

# 获取论文详情
curl "https://api.semanticscholar.org/graph/v1/paper/{paperId}?fields=title,authors,abstract,year"

# 获取论文引用
curl "https://api.semanticscholar.org/graph/v1/paper/{paperId}/citations?limit=10"

# 获取论文参考文献
curl "https://api.semanticscholar.org/graph/v1/paper/{paperId}/references?limit=10"
```

### Python 调用示例

```python
import requests

def search_semantic(query, limit=10):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "paperId,title,authors,abstract,year,citationCount"
    }
    response = requests.get(url, params=params)
    return response.json()
```

---

## 2. arXiv

**API 文档**: https://arxiv.org/help/api

**特点**:
- 免费，无需注册
- 预印本为主（物理、数学、计算机科学）
- 支持 Atom XML 格式

### 基础调用

```bash
# 按标题搜索
curl "http://export.arxiv.org/api/query?search_query=ti:flotation+copper&max_results=10"

# 全文搜索
curl "http://export.arxiv.org/api/query?search_query=all:flotation&max_results=10"

# 按作者搜索
curl "http://export.arxiv.org/api/query?search_query=au:Smith&max_results=10"
```

### 搜索运算符

| 字段 | 说明 | 示例 |
|------|------|------|
| `ti` | 标题 | `ti:neural network` |
| `au` | 作者 | `au:Smith` |
| `abs` | 摘要 | `abs:machine learning` |
| `all` | 全部 | `all:deep learning` |
| `cat` | 分类 | `cat:cs.LG` |

---

## 3. CrossRef

**API 文档**: https://www.crossref.org/documentation/retrieve-links/

**特点**:
- 免费，需要注册 email
- 学术期刊论文元数据
- 支持 DOI 解析

### 基础调用

```bash
curl -H "User-Agent: PaperAssistant/1.0 (mailto:your@email.com)" \
     "https://api.crossref.org/works?query=flotation+copper&rows=10"
```

### DOI 解析

```bash
curl "https://api.crossref.org/works/10.1038/nature12373"
```

---

## 4. PubMed (生命科学)

**API 文档**: https://eutils.ncbi.nlm.nih.gov/home/api.html

**特点**:
- 生物医学文献
- 免费，需申请 API key（可选）

### 基础调用

```bash
# 搜索
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=flotation&retmax=10&retmode=json"

# 获取详情
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345678&retmode=json"
```

---

## 5. 中国知网 (CNKI)

**说明**: CNKI 不提供公共 API，学术研究可通过以下方式访问：

1. **机构授权**: 通过高校/研究机构 IP 访问
2. **第三方工具**: 如 NoteExpress、Mendeley
3. **手动导出**: CNKI 支持 BibTeX/EndNote 格式导出

---

## 6. 万方数据

**说明**: 万方数据提供机构授权访问，无公共 API。

**访问方式**:
1. 高校/研究机构图书馆入口
2. 个人付费订阅
3. 与 Zotero/BibMeh 配合使用

---

## 7. 百度学术

**说明**: 百度学术不提供 API，建议：

1. **手动搜索 + 复制**: 适合少量文献
2. **与 Zotero 配合**: 百度学术支持 BibTeX 导出
3. **Selenium 抓取**（不推荐，可能违反服务条款）

---

## 使用建议

| 场景 | 推荐数据源 |
|------|-----------|
| 英文论文搜索 | Semantic Scholar, arXiv, CrossRef |
| 中文论文搜索 | Zotero + 手动导入 |
| 预印本 | arXiv, bioRxiv |
| 引用分析 | Semantic Scholar, Google Scholar |
| DOI 解析 | CrossRef |
