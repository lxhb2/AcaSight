---
name: zotero-manager
description: Zotero 文献管理技能。当你需要访问、搜索、阅读 Zotero 文献库中的论文 PDF 或元数据时使用。支持：搜索论文、查看文献信息、提取 PDF 内容与批注、管理文献集合。触发词：Zotero、论文、文献、PDF、引用、参考文献。
---

# Zotero Manager

## 概述

Zotero 是一个流行的学术文献管理工具。此技能提供从 Zotero 数据库读取和管理论文的能力。

**数据位置：**
- 数据库：`C:\Users\Administrator\Zotero\zotero.sqlite`
- PDF 存储：`C:\Users\Administrator\Zotero\storage\`

**重要提示：** 运行 Python 脚本时添加 `-X utf8` 参数以正确处理中文：
```bash
python -X utf8 query_zotero.py search "关键词"
```

## 核心功能

### 1. 搜索文献

使用 `scripts/query_zotero.py` 脚本查询数据库：

```bash
# 搜索所有文献（最近20篇）
python -X utf8 query_zotero.py search "" 20

# 搜索特定关键词
python -X utf8 query_zotero.py search "浮选" 10

# 获取某篇文献的完整元数据
python -X utfoto.py metadata <item_key>
```

### 2. 获取文献集合

```bash
# 列出所有收藏夹
python -X utf8 query_zotero.py collections
```

### 3. 定位 PDF 文件

每个文献在 storage/ 下有对应文件夹，文件夹名即是 item key：

```powershell
# 查找某篇论文的 PDF
$key = "2Y3USE6G"  # 文献 key
Get-ChildItem "C:\Users\Administrator\Zotero\storage\$key\*.pdf" | Select-Object Name, FullName
```

### 4. 提取 PDF 内容

需要先定位 PDF 路径，然后使用 PDF 技能提取内容。详见 `references/pdf-extraction.md`

### 5. 批注管理

Zotero 的 PDF 批注数据在数据库中：

```sql
SELECT annotations.annotationID, annotations.annotationText, 
       annotations.annotationColor, items.key
FROM annotations
JOIN items ON annotations.itemID = items.itemID
WHERE items.key = '目标KEY';
```

## 工作流程

1. **用户请求搜索/查看文献** → 使用 `query_zotero.py` 查询数据库
2. **需要读取 PDF 内容** → 定位 PDF 文件后用 PDF 技能提取
3. **需要管理文献** → 提示用户使用 Zotero 桌面客户端

## 脚本使用

### query_zotero.py

```
用法: query_zotero.py <command> [args]

命令:
  search [query] [limit]  搜索文献（默认20篇）
  metadata <key>          获取文献完整元数据
  collections             列出所有收藏夹
```

## 注意事项

- Zotero 数据库在 Zotero 运行时可能被锁定，查询时确保 Zotero 已关闭
- storage/ 下的文件夹名是 Zotero item key，可与数据库关联
- 脚本输出可能有编码问题，添加 `-X utf8` 参数解决
- PDF 文件名可能有编码问题，使用 `Get-ChildItem -Name` 获取正确名称
