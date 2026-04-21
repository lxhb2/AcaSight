# PDF 内容提取指南

## 基础提取

使用 Python 的 `pdfplumber` 或 `PyPDF2` 提取文本：

```python
import pdfplumber

def extract_pdf_text(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text
```

## 提取批注/注释

Zotero 的 PDF 批注存储在数据库中：

```sql
-- 查看文献的 PDF 批注
SELECT annotations.annotationID, annotations.annotationText, 
       annotations.annotationColor, items.key
FROM annotations
JOIN items ON annotations.itemID = items.itemID
WHERE items.key = '目标KEY';
```

## 提取高亮文本

```python
# 提取 PDF 高亮区域
import pdfplumber

def extract_highlights(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for annot in page.annots or []:
                if annot['type'] == 'highlight':
                    yield annot
```

## 文本搜索

```bash
# 在所有 PDF 中搜索关键词
$query = "浮选"
Get-ChildItem "C:\Users\Administrator\Zotero\storage" -Recurse -Filter "*.pdf" | ForEach-Object {
    $content = (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue)
    if ($content -match $query) {
        Write-Host $_.Directory.Name ": $query"
    }
}
```
