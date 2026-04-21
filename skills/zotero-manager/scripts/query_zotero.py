#!/usr/bin/env python3
"""
Zotero 数据库查询工具
查询 Zotero sqlite 数据库获取文献信息
"""
import sqlite3
import json
import sys
from pathlib import Path

DB_PATH = r"C:\Users\Administrator\Zotero\zotero.sqlite"


def search_items(query="", limit=20):
    """搜索文献"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if query:
        sql = """
        SELECT items.key, items.itemID, itemDataValues.value as title, 
               creators.lastName, creators.firstName, items.dateModified,
               fields.fieldName, itemDataValues.value
        FROM items 
        JOIN itemData ON items.itemID = itemData.itemID 
        JOIN fields ON itemData.fieldID = fields.fieldID 
        JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
        LEFT JOIN itemCreators ON items.itemID = itemCreators.itemID
        LEFT JOIN creators ON itemCreators.creatorID = creators.creatorID
        WHERE itemDataValues.value LIKE ?
        ORDER BY items.dateModified DESC
        LIMIT ?
        """
        cursor.execute(sql, (f"%{query}%", limit))
    else:
        sql = """
        SELECT items.key, items.itemID, itemDataValues.value as title,
               items.dateModified
        FROM items 
        JOIN itemData ON items.itemID = itemData.itemID 
        JOIN fields ON itemData.fieldID = fields.fieldID 
        JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
        WHERE fields.fieldName = 'title'
        ORDER BY items.dateModified DESC
        LIMIT ?
        """
        cursor.execute(sql, (limit,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_item_metadata(item_key):
    """获取单篇文献的完整元数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取基本信息
    sql = """
    SELECT items.key, itemDataValues.value, fields.fieldName
    FROM items 
    JOIN itemData ON items.itemID = itemData.itemID 
    JOIN fields ON itemData.fieldID = fields.fieldID 
    JOIN itemDataValues ON itemData.valueID = itemDataValues.valueID
    WHERE items.key = ?
    """
    cursor.execute(sql, (item_key,))
    
    metadata = {"key": item_key}
    for row in cursor.fetchall():
        metadata[row["fieldName"]] = row["value"]
    
    # 获取作者
    sql_creators = """
    SELECT creators.lastName, creators.firstName, fields.fieldName
    FROM items
    JOIN itemCreators ON items.itemID = itemCreators.itemID
    JOIN creators ON itemCreators.creatorID = creators.creatorID
    JOIN fields ON itemCreators.orderIndex = fields.fieldID
    WHERE items.key = ?
    """
    cursor.execute(sql_creators, (item_key,))
    metadata["creators"] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return metadata


def list_collections():
    """列出所有收藏夹/集合"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    sql = """
    SELECT collectionID, collectionName, parentCollectionID
    FROM collections
    ORDER BY collectionName
    """
    cursor.execute(sql)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: query_zotero.py <search|metadata|collections> [参数]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        results = search_items(query)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif command == "metadata":
        if len(sys.argv) < 3:
            print("需要提供 item key")
            sys.exit(1)
        result = get_item_metadata(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif command == "collections":
        results = list_collections()
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    else:
        print(f"未知命令: {command}")
        sys.exit(1)
