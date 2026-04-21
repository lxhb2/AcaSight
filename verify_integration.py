#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证数据整合结果
"""

import sqlite3
from pathlib import Path

def verify_integration():
    """验证数据整合结果"""
    db_path = Path(r"F:\桌面\pdf2_final_complete.db")
    
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("PDF2-2004 数据整合验证报告")
    print("=" * 60)
    
    # 1. 检查表
    print("\n1. 数据库表结构:")
    cursor.execute("SELECT name, type FROM sqlite_master ORDER BY type, name")
    
    tables = []
    views = []
    
    for name, type_ in cursor.fetchall():
        if type_ == 'table':
            tables.append(name)
        elif type_ == 'view':
            views.append(name)
    
    print(f"  表 ({len(tables)}个):")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM \"{table}\"")
        count = cursor.fetchone()[0]
        print(f"    {table}: {count:,} 条记录")
    
    print(f"\n  视图 ({len(views)}个):")
    for view in views:
        print(f"    {view}")
    
    # 2. 检查summary数据
    print("\n2. Summary数据整合:")
    if 'pdf2_summary_final' in tables:
        cursor.execute("SELECT COUNT(*) FROM pdf2_summary_final")
        summary_count = cursor.fetchone()[0]
        print(f"  summary记录数: {summary_count:,}")
        
        # 检查名称清理
        cursor.execute("""
        SELECT name, 
               CASE 
                   WHEN name LIKE '$G%' THEN 'β-' || SUBSTR(name, 3)
                   WHEN name LIKE '$A%' THEN 'α-' || SUBSTR(name, 3)
                   WHEN name LIKE 'odium%' THEN 'Sodium' || SUBSTR(name, 6)
                   ELSE name
               END as cleaned_name
        FROM pdf2_summary_final 
        WHERE name LIKE '$%' OR name LIKE 'odium%'
        LIMIT 5
        """)
        
        print("  名称清理示例:")
        for original, cleaned in cursor.fetchall():
            print(f"    {original} → {cleaned}")
    else:
        print("  summary表不存在")
    
    # 3. 检查mineral数据
    print("\n3. Mineral数据整合:")
    if 'pdf2_minerals_final' in tables:
        cursor.execute("SELECT COUNT(*) FROM pdf2_minerals_final")
        mineral_count = cursor.fetchone()[0]
        print(f"  矿物种类数: {mineral_count}")
        
        cursor.execute("SELECT code, name, full_name FROM pdf2_minerals_final LIMIT 10")
        print("  矿物示例:")
        for code, name, full_name in cursor.fetchall():
            print(f"    {full_name}")
    
    # 4. 检查最终视图
    print("\n4. 最终搜索视图:")
    if 'v_final_search' in views:
        cursor.execute("SELECT COUNT(*) FROM v_final_search")
        total_cards = cursor.fetchone()[0]
        print(f"  总卡片数: {total_cards:,}")
        
        cursor.execute("SELECT COUNT(*) FROM v_final_search WHERE is_mineral = 1")
        mineral_cards = cursor.fetchone()[0]
        print(f"  矿物卡片数: {mineral_cards}")
        
        cursor.execute("""
        SELECT COUNT(DISTINCT display_name) 
        FROM v_final_search 
        WHERE display_name LIKE 'β-%' OR display_name LIKE 'α-%'
        """)
        special_names = cursor.fetchone()[0]
        print(f"  特殊名称卡片 (α/β前缀): {special_names}")
        
        # 显示整合后的示例
        print("\n  整合后的卡片示例 (前5张):")
        cursor.execute("""
        SELECT card_num_str, display_name, display_formula, card_type,
               CASE WHEN is_mineral = 1 THEN '是' ELSE '否' END as is_mineral
        FROM v_final_search 
        LIMIT 5
        """)
        
        for row in cursor.fetchall():
            print(f"\n    卡片: {row[0]}")
            print(f"      名称: {row[1]}")
            print(f"      化学式: {row[2]}")
            print(f"      类型: {row[3]}")
            print(f"      是否为矿物: {row[4]}")
    
    # 5. 性能测试
    print("\n5. 性能测试:")
    
    # 测试d值搜索
    import time
    start = time.time()
    cursor.execute("""
    SELECT COUNT(DISTINCT p.card_num)
    FROM pdf2_peaks p
    WHERE ABS(p.d_value - 3.34) <= 0.02
    """)
    d_search_count = cursor.fetchone()[0]
    d_search_time = time.time() - start
    
    print(f"  d值搜索 (3.34±0.02):")
    print(f"    结果数: {d_search_count:,}")
    print(f"    耗时: {d_search_time*1000:.1f} ms")
    
    # 测试名称搜索
    start = time.time()
    cursor.execute("""
    SELECT COUNT(*)
    FROM v_final_search
    WHERE display_name LIKE '%Sodium%'
    """)
    name_search_count = cursor.fetchone()[0]
    name_search_time = time.time() - start
    
    print(f"\n  名称搜索 ('Sodium'):")
    print(f"    结果数: {name_search_count}")
    print(f"    耗时: {name_search_time*1000:.1f} ms")
    
    # 6. 数据质量统计
    print("\n6. 数据质量统计:")
    
    cursor.execute("SELECT COUNT(*) FROM v_final_search WHERE display_formula IS NOT NULL AND display_formula != ''")
    formula_count = cursor.fetchone()[0]
    print(f"  有化学式的卡片: {formula_count:,} ({formula_count/total_cards*100:.1f}%)")
    
    cursor.execute("SELECT COUNT(*) FROM v_final_search WHERE cas IS NOT NULL AND cas != ''")
    cas_count = cursor.fetchone()[0]
    print(f"  有CAS号的卡片: {cas_count:,} ({cas_count/total_cards*100:.1f}%)")
    
    cursor.execute("SELECT AVG(n_peaks) FROM v_final_search WHERE n_peaks > 0")
    avg_peaks = cursor.fetchone()[0]
    print(f"  平均峰数/卡片: {avg_peaks:.1f}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("验证完成！")
    print(f"数据库: {db_path}")
    print("主要视图: v_final_search")
    print("=" * 60)

if __name__ == '__main__':
    verify_integration()