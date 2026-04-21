#!/usr/bin/env python3
"""
学术论文搜索工具
整合 Semantic Scholar、arXiv、CrossRef 等开放学术数据库
"""
import argparse
import json
import sys
from pathlib import Path
import urllib.request
import urllib.parse

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))


def search_semantic_scholar(query, limit=10, offset=0):
    """搜索 Semantic Scholar"""
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),  # 最大100
        "offset": offset,
        "fields": "paperId,title,authors,abstract,year,citationCount,venue,openAccessPdf"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            return {
                "source": "Semantic Scholar",
                "total": data.get("total", 0),
                "papers": data.get("data", [])
            }
    except Exception as e:
        return {"source": "Semantic Scholar", "error": str(e)}


def search_arxiv(query, limit=10):
    """搜索 arXiv 预印本"""
    base_url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": f"all:{query}",
        "max_results": min(limit, 50),
        "sortBy": "relevance"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/xml"})
        with urllib.request.urlopen(req, timeout=30) as response:
            import xml.etree.ElementTree as ET
            content = response.read().decode()
            root = ET.fromstring(content)
            
            papers = []
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                published = entry.find("atom:published", ns)
                authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
                link = entry.find("atom:id", ns)
                
                papers.append({
                    "title": title.text.strip().replace("\n", " ") if title is not None else "",
                    "abstract": summary.text.strip()[:500] if summary is not None else "",
                    "year": published.text[:4] if published is not None else "",
                    "authors": authors[:5],  # 只取前5个作者
                    "url": link.text if link is not None else "",
                    "source": "arXiv"
                })
            
            return {"source": "arXiv", "papers": papers}
    except Exception as e:
        return {"source": "arXiv", "error": str(e)}


def search_crossref(query, limit=10):
    """搜索 CrossRef"""
    base_url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": min(limit, 100),
        "select": "DOI,title,author,published-print,container-title,abstract"
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "PaperAssistant/1.0 (mailto:user@example.com)"
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            items = data.get("message", {}).get("items", [])
            
            papers = []
            for item in items:
                authors = []
                for author in item.get("author", []):
                    name = author.get("given", "") + " " + author.get("family", "")
                    authors.append(name.strip())
                
                papers.append({
                    "title": item.get("title", [""])[0] if item.get("title") else "",
                    "authors": authors,
                    "year": item.get("published-print", {}).get("date-parts", [[""]])[0][0],
                    "journal": item.get("container-title", [""])[0] if item.get("container-title") else "",
                    "doi": item.get("DOI", ""),
                    "source": "CrossRef"
                })
            
            return {"source": "CrossRef", "total": data.get("message", {}).get("total-results", 0), "papers": papers}
    except Exception as e:
        return {"source": "CrossRef", "error": str(e)}


def format_results(results, format="markdown"):
    """格式化搜索结果"""
    if format == "json":
        return json.dumps(results, ensure_ascii=False, indent=2)
    
    output = []
    output.append(f"# 搜索结果\n")
    output.append(f"**数据源:** {results.get('source', 'Unknown')}\n")
    
    if "total" in results:
        output.append(f"**总数:** {results['total']}\n")
    
    if "error" in results:
        output.append(f"**错误:** {results['error']}\n")
        return "".join(output)
    
    papers = results.get("papers", [])
    for i, paper in enumerate(papers, 1):
        output.append(f"## {i}. {paper.get('title', 'N/A')}\n")
        output.append(f"- **作者:** {', '.join(paper.get('authors', [])[:3])}\n")
        output.append(f"- **年份:** {paper.get('year', 'N/A')}\n")
        if paper.get("journal"):
            output.append(f"- **期刊:** {paper['journal']}\n")
        if paper.get("doi"):
            output.append(f"- **DOI:** {paper['doi']}\n")
        if paper.get("abstract"):
            abstract = paper["abstract"][:300] + "..." if len(paper["abstract"]) > 300 else paper["abstract"]
            output.append(f"- **摘要:** {abstract}\n")
        output.append("\n")
    
    return "".join(output)


def main():
    parser = argparse.ArgumentParser(description="学术论文搜索工具")
    parser.add_argument("--query", "-q", required=True, help="搜索关键词")
    parser.add_argument("--source", "-s", choices=["semantic", "arxiv", "crossref", "all"], 
                        default="all", help="数据源")
    parser.add_argument("--limit", "-l", type=int, default=10, help="返回数量")
    parser.add_argument("--format", "-f", choices=["json", "markdown"], default="markdown", help="输出格式")
    
    args = parser.parse_args()
    
    results_list = []
    
    if args.source in ["semantic", "all"]:
        results_list.append(search_semantic_scholar(args.query, args.limit))
    
    if args.source in ["arxiv", "all"]:
        results_list.append(search_arxiv(args.query, args.limit))
    
    if args.source in ["crossref", "all"]:
        results_list.append(search_crossref(args.query, args.limit))
    
    # 汇总输出
    for results in results_list:
        print(format_results(results, args.format))
        print("\n---\n")


if __name__ == "__main__":
    main()
