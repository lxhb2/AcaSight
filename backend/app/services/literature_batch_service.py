"""
批量文献处理服务

支持 BibTeX / RIS / CSV / EndNote XML 格式的解析、分析与导出。
"""

import csv
import io
import re
import json
import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class ParsedEntry:
    """解析后的文献条目"""
    title: str = ""
    authors: str = ""
    year: str = ""
    journal: str = ""
    doi: str = ""
    abstract: str = ""
    entry_type: str = ""  # article, inproceedings, etc.
    extra: Dict = field(default_factory=dict)


class LiteratureBatchService:
    """批量文献处理服务"""

    # ── BibTeX 解析 ──

    def parse_bibtex(self, content: str) -> List[ParsedEntry]:
        """解析 BibTeX 格式文件内容

        提取 @article/@inproceedings 等条目中的 title, authors, year, journal, doi, abstract。
        """
        entries: List[ParsedEntry] = []
        # 匹配 @type{key, ... } — 使用花括号深度匹配，兼容单行和多行
        i = 0
        while i < len(content):
            # 查找下一个 @type{
            m = re.search(r'@(\w+)\s*\{', content[i:])
            if not m:
                break
            entry_type = m.group(1).lower()
            start = i + m.end()
            i = start

            if entry_type in ('comment', 'string', 'preamble'):
                continue

            # 找到匹配的闭合花括号
            depth = 1
            pos = start
            while pos < len(content) and depth > 0:
                if content[pos] == '{':
                    depth += 1
                elif content[pos] == '}':
                    depth -= 1
                pos += 1

            if depth != 0:
                continue

            body = content[start:pos - 1]
            fields = self._parse_bibtex_fields(body)
            entry = ParsedEntry(
                title=self._clean_bibtex_value(fields.get('title', '')),
                authors=self._clean_bibtex_value(fields.get('author', '')),
                year=self._clean_bibtex_value(fields.get('year', '')),
                journal=self._clean_bibtex_value(
                    fields.get('journal', '') or fields.get('booktitle', '')
                ),
                doi=self._clean_bibtex_value(fields.get('doi', '')),
                abstract=self._clean_bibtex_value(fields.get('abstract', '')),
                entry_type=entry_type,
                extra={
                    k: self._clean_bibtex_value(v)
                    for k, v in fields.items()
                    if k not in ('title', 'author', 'year', 'journal', 'booktitle', 'doi', 'abstract')
                },
            )
            if entry.title:
                entries.append(entry)
        return entries

    def _parse_bibtex_fields(self, body: str) -> Dict[str, str]:
        """解析 BibTeX 条目体中的字段键值对"""
        fields: Dict[str, str] = {}
        # 匹配 field = {value} 或 field = "value" 或 field = number
        pattern = re.compile(r'(\w+)\s*=\s*')
        pos = 0
        while pos < len(body):
            m = pattern.search(body, pos)
            if not m:
                break
            key = m.group(1).lower()
            val_start = m.end()
            value, val_end = self._read_bibtex_value(body, val_start)
            fields[key] = value
            pos = val_end
        return fields

    def _read_bibtex_value(self, text: str, start: int) -> Tuple[str, int]:
        """读取 BibTeX 字段值（处理花括号嵌套）"""
        pos = start
        # 跳过空白
        while pos < len(text) and text[pos] in ' \t\n\r':
            pos += 1
        if pos >= len(text):
            return '', pos

        if text[pos] == '{':
            # 花括号包裹的值
            depth = 1
            pos += 1
            val_start = pos
            while pos < len(text) and depth > 0:
                if text[pos] == '{':
                    depth += 1
                elif text[pos] == '}':
                    depth -= 1
                pos += 1
            return text[val_start:pos - 1], pos
        elif text[pos] == '"':
            # 双引号包裹的值
            pos += 1
            val_start = pos
            while pos < len(text) and text[pos] != '"':
                pos += 1
            value = text[val_start:pos]
            pos += 1  # skip closing quote
            return value, pos
        else:
            # 裸值（数字等）
            val_start = pos
            while pos < len(text) and text[pos] not in ',}\n':
                pos += 1
            return text[val_start:pos].strip(), pos

    def _clean_bibtex_value(self, value: str) -> str:
        """清理 BibTeX 值中的 LaTeX 命令"""
        # 移除花括号
        value = value.replace('{', '').replace('}', '')
        # 替换常见 LaTeX
        value = value.replace('\\&', '&')
        value = value.replace('\\%', '%')
        value = value.replace('\\#', '#')
        value = value.replace('\\~', ' ')
        value = value.replace('\\textit', '')
        value = value.replace('\\textbf', '')
        value = value.replace('\\emph', '')
        # 清理多余空白
        value = re.sub(r'\s+', ' ', value).strip()
        return value

    # ── RIS 解析 ──

    def parse_ris(self, content: str) -> List[ParsedEntry]:
        """解析 RIS 格式文件内容

        提取 TY/AU/TI/JO/PY/DO/AB 等标签。
        """
        entries: List[ParsedEntry] = []
        current: Optional[Dict[str, List[str]]] = None

        for line in content.split('\n'):
            line = line.rstrip()
            if not line:
                continue
            # RIS 标签格式: "TY  - Journal Article" 或 "AU  - Smith, John"
            match = re.match(r'^([A-Z][A-Z0-9])\s*-\s*(.*)', line)
            if not match:
                continue
            tag = match.group(1)
            value = match.group(2).strip()

            if tag == 'TY':
                # 新条目开始
                if current is not None:
                    entries.append(self._ris_dict_to_entry(current))
                current = {'TY': [value]}
            elif tag == 'ER':
                # 条目结束
                if current is not None:
                    entries.append(self._ris_dict_to_entry(current))
                    current = None
            elif current is not None:
                current.setdefault(tag, []).append(value)

        # 处理最后一个条目（可能没有 ER 标签）
        if current is not None:
            entries.append(self._ris_dict_to_entry(current))

        return entries

    def _ris_dict_to_entry(self, data: Dict[str, List[str]]) -> ParsedEntry:
        """将 RIS 标签字典转换为 ParsedEntry"""
        return ParsedEntry(
            title=', '.join(data.get('TI', data.get('T1', []))),
            authors='; '.join(data.get('AU', data.get('A1', []))),
            year=', '.join(data.get('PY', data.get('Y1', [])))[:4] if data.get('PY', data.get('Y1')) else '',
            journal=', '.join(data.get('JO', data.get('JF', data.get('T2', [])))),
            doi=', '.join(data.get('DO', [])),
            abstract=', '.join(data.get('AB', data.get('N2', []))),
            entry_type=', '.join(data.get('TY', [''])),
            extra={k: '; '.join(v) for k, v in data.items()
                   if k not in ('TY', 'AU', 'A1', 'TI', 'T1', 'PY', 'Y1', 'JO', 'JF', 'T2', 'DO', 'AB', 'N2', 'ER')},
        )

    # ── CSV 解析 ──

    def parse_csv(self, content: str) -> List[ParsedEntry]:
        """解析 CSV 格式文件内容

        基于表头列名自动映射字段。
        """
        entries: List[ParsedEntry] = []
        reader = csv.DictReader(io.StringIO(content))
        # 列名映射（支持多种常见列名）
        col_map = {
            'title': ['title', '标题', 'ti', 'article_title'],
            'authors': ['authors', 'author', '作者', 'au'],
            'year': ['year', '年份', 'py', 'publication_year', 'date'],
            'journal': ['journal', '期刊', 'jo', 'source', 'publication_title', 'venue'],
            'doi': ['doi', 'DOI'],
            'abstract': ['abstract', '摘要', 'ab'],
        }

        for row in reader:
            entry = ParsedEntry()
            for field, aliases in col_map.items():
                for alias in aliases:
                    if alias in row and row[alias]:
                        setattr(entry, field, str(row[alias]).strip())
                        break
            if entry.title:
                entries.append(entry)
        return entries

    # ── EndNote XML 解析 ──

    def parse_endnote_xml(self, content: str) -> List[ParsedEntry]:
        """解析 EndNote XML 格式（简化版）"""
        entries: List[ParsedEntry] = []
        # 简单的正则提取，避免引入 xml.etree 依赖问题
        record_pattern = re.compile(r'<record>(.*?)</record>', re.DOTALL)
        for match in record_pattern.finditer(content):
            record = match.group(1)
            entry = ParsedEntry(
                title=self._xml_tag(record, 'title'),
                authors=self._xml_tag(record, 'authors'),
                year=self._xml_tag(record, 'year'),
                journal=self._xml_tag(record, 'periodical', attr='full-title'),
                doi=self._xml_tag(record, 'doi'),
                abstract=self._xml_tag(record, 'abstract'),
                entry_type=self._xml_tag(record, 'ref-type', attr='name'),
            )
            if entry.title:
                entries.append(entry)
        return entries

    def _xml_tag(self, xml: str, tag: str, attr: Optional[str] = None) -> str:
        """从 XML 片段中提取标签文本"""
        if attr:
            m = re.search(rf'<{tag}[^>]*{attr}="([^"]*)"', xml)
            return m.group(1) if m else ''
        m = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', xml, re.DOTALL)
        return m.group(1).strip() if m else ''

    # ── 自动检测格式 ──

    def detect_format(self, filename: str, content: str) -> str:
        """根据文件名和内容自动检测格式

        返回: 'bibtex' | 'ris' | 'csv' | 'endnote_xml'
        """
        lower_name = filename.lower()
        if lower_name.endswith('.bib'):
            return 'bibtex'
        if lower_name.endswith('.ris'):
            return 'ris'
        if lower_name.endswith('.csv'):
            return 'csv'
        if lower_name.endswith('.xml'):
            return 'endnote_xml'
        # 根据内容推断
        if '@' in content and re.search(r'@\w+\{', content):
            return 'bibtex'
        if 'TY  -' in content:
            return 'ris'
        if '<records>' in content or '<record>' in content:
            return 'endnote_xml'
        return 'csv'

    def parse_file(self, filename: str, content: str) -> List[ParsedEntry]:
        """根据自动检测的格式解析文件"""
        fmt = self.detect_format(filename, content)
        parsers = {
            'bibtex': self.parse_bibtex,
            'ris': self.parse_ris,
            'csv': self.parse_csv,
            'endnote_xml': self.parse_endnote_xml,
        }
        parser = parsers.get(fmt, self.parse_csv)
        return parser(content)

    # ── 导出功能 ──

    def export_bibtex(self, papers: List[Dict]) -> str:
        """将文献列表导出为 BibTeX 格式"""
        lines: List[str] = []
        for p in papers:
            entry_type = p.get('entry_type', 'article') or 'article'
            key = self._make_bibtex_key(p)
            lines.append(f'@{entry_type}{{{key},')
            if p.get('title'):
                lines.append(f'  title = {{{p["title"]}}},')
            if p.get('authors'):
                lines.append(f'  author = {{{p["authors"]}}},')
            if p.get('year'):
                lines.append(f'  year = {{{p["year"]}}},')
            if p.get('journal'):
                lines.append(f'  journal = {{{p["journal"]}}},')
            if p.get('doi'):
                lines.append(f'  doi = {{{p["doi"]}}},')
            if p.get('abstract'):
                lines.append(f'  abstract = {{{p["abstract"]}}},')
            lines.append('}')
            lines.append('')
        return '\n'.join(lines)

    def export_ris(self, papers: List[Dict]) -> str:
        """将文献列表导出为 RIS 格式"""
        lines: List[str] = []
        for p in papers:
            lines.append(f'TY  - {p.get("entry_type", "JOUR") or "JOUR"}')
            if p.get('title'):
                lines.append(f'TI  - {p["title"]}')
            if p.get('authors'):
                for author in p['authors'].split('; '):
                    if author.strip():
                        lines.append(f'AU  - {author.strip()}')
            if p.get('year'):
                lines.append(f'PY  - {p["year"]}')
            if p.get('journal'):
                lines.append(f'JO  - {p["journal"]}')
            if p.get('doi'):
                lines.append(f'DO  - {p["doi"]}')
            if p.get('abstract'):
                lines.append(f'AB  - {p["abstract"]}')
            lines.append('ER  - ')
            lines.append('')
        return '\n'.join(lines)

    def export_csv(self, papers: List[Dict]) -> str:
        """将文献列表导出为 CSV 格式"""
        output = io.StringIO()
        fieldnames = ['title', 'authors', 'year', 'journal', 'doi', 'abstract']
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for p in papers:
            row = {f: str(p.get(f, '')) for f in fieldnames}
            writer.writerow(row)
        return output.getvalue()

    def export_papers(self, papers: List[Dict], fmt: str) -> str:
        """按指定格式导出文献"""
        exporters = {
            'bibtex': self.export_bibtex,
            'ris': self.export_ris,
            'csv': self.export_csv,
        }
        exporter = exporters.get(fmt, self.export_csv)
        return exporter(papers)

    def _make_bibtex_key(self, paper: Dict) -> str:
        """生成 BibTeX 引用键"""
        author_part = ''
        if paper.get('authors'):
            first_author = paper['authors'].split(';')[0].split(',')[0].strip()
            author_part = re.sub(r'[^a-zA-Z]', '', first_author)[:10]
        year_part = str(paper.get('year', ''))[:4]
        title_part = ''
        if paper.get('title'):
            words = paper['title'].split()[:2]
            title_part = ''.join(w.capitalize() for w in words if w)
        return f"{author_part}{year_part}{title_part}" or str(uuid.uuid4())[:8]

    # ── 统计功能 ──

    def compute_statistics(self, papers: List[Dict]) -> Dict:
        """计算文献统计信息

        返回按年份、期刊、关键词的分布统计。
        """
        by_year: Dict[str, int] = {}
        by_journal: Dict[str, int] = {}
        by_keyword: Dict[str, int] = {}

        for p in papers:
            # 年份统计
            year = str(p.get('year', '未知'))
            by_year[year] = by_year.get(year, 0) + 1

            # 期刊统计
            journal = p.get('journal') or '未知期刊'
            by_journal[journal] = by_journal.get(journal, 0) + 1

            # 关键词统计
            keywords = p.get('keywords', [])
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(';') if k.strip()]
            for kw in keywords:
                by_keyword[kw] = by_keyword.get(kw, 0) + 1

        # 排序
        by_year = dict(sorted(by_year.items()))
        by_journal = dict(sorted(by_journal.items(), key=lambda x: -x[1])[:20])
        by_keyword = dict(sorted(by_keyword.items(), key=lambda x: -x[1])[:30])

        return {
            'total': len(papers),
            'by_year': by_year,
            'by_journal': by_journal,
            'by_keyword': by_keyword,
        }


# 全局单例
literature_batch_service = LiteratureBatchService()
