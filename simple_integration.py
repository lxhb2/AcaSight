#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版数据整合
"""

import sqlite3
from pathlib import Path

def simple_integration():
    """简化版数据整合"""
    db_path = Path(r"F:\桌面\pdf2_final_complete.db")
    
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("1. 清理旧表...")
    cursor.execute('DROP TABLE IF EXISTS pdf2_summary')
    cursor.execute('DROP VIEW IF EXISTS v_cards_with_summary')
    cursor.execute('DROP TABLE IF EXISTS pdf2_minerals')
    
    print("2. 创建优化表结构...")
    
    # 创建增强的cards表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pdf2_cards_enhanced AS
    SELECT 
        c.*,
        NULL as summary_name,
        NULL as summary_formula,
        NULL as mineral_code,
        NULL as mineral_name
    FROM pdf2_cards c
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enhanced_name ON pdf2_cards_enhanced(summary_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enhanced_formula ON pdf2_cards_enhanced(summary_formula)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_enhanced_mineral ON pdf2_cards_enhanced(mineral_name)')
    
    conn.commit()
    
    print("3. 更新卡片名称和化学式...")
    
    # 示例：手动更新一些常见矿物的名称
    common_updates = [
        # (原始名称模式, 新名称, 新化学式)
        ("B-Naphthylbismuth", "β-Naphthylbismuth dioxide", "C10H7BiO2"),
        ("odium hippurate", "Sodium hippurate", "C9H8NNaO3"),
        ("arium phenolsulfonate", "Barium phenolsulfonate", "C12H9BaO7S2"),
        ("otassium phenoxide", "Potassium phenoxide", "C6H5KO"),
    ]
    
    for old_pattern, new_name, new_formula in common_updates:
        cursor.execute('''
        UPDATE pdf2_cards_enhanced 
        SET summary_name = ?, summary_formula = ?
        WHERE name LIKE ? AND summary_name IS NULL
        ''', (new_name, new_formula, f'%{old_pattern}%'))
    
    # 更新矿物类型卡片
    cursor.execute('''
    UPDATE pdf2_cards_enhanced 
    SET mineral_name = name
    WHERE card_type = 'Mineral' AND mineral_name IS NULL
    ''')
    
    conn.commit()
    
    print("4. 创建快速搜索视图...")
    
    cursor.execute('''
    CREATE VIEW IF NOT EXISTS v_quick_search AS
    SELECT 
        card_num,
        card_num_str,
        COALESCE(summary_name, name) as display_name,
        COALESCE(summary_formula, formula) as display_formula,
        cas,
        card_type,
        radiation,
        wavelength,
        n_peaks,
        d_min,
        d_max,
        i_max,
        mineral_name
    FROM pdf2_cards_enhanced
    ''')
    
    print("5. 验证结果...")
    
    cursor.execute('SELECT COUNT(*) FROM pdf2_cards_enhanced')
    total_cards = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM pdf2_cards_enhanced WHERE summary_name IS NOT NULL')
    updated_names = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM pdf2_cards_enhanced WHERE mineral_name IS NOT NULL')
    mineral_cards = cursor.fetchone()[0]
    
    print(f"\n整合结果:")
    print(f"  总卡片数: {total_cards}")
    print(f"  更新名称的卡片: {updated_names}")
    print(f"  矿物卡片: {mineral_cards}")
    
    print("\n示例查询 (前5张卡片):")
    cursor.execute('''
    SELECT card_num_str, display_name, display_formula, card_type, mineral_name
    FROM v_quick_search 
    LIMIT 5
    ''')
    
    for row in cursor.fetchall():
        print(f"  卡片: {row[0]}")
        print(f"    名称: {row[1]}")
        print(f"    化学式: {row[2]}")
        print(f"    类型: {row[3]}")
        if row[4]:
            print(f"    矿物: {row[4]}")
        print()
    
    # 创建常用查询函数
    print("6. 创建常用查询函数...")
    
    # 按d值搜索的优化函数
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS common_queries (
        query_type TEXT,
        query_key TEXT,
        result_count INTEGER,
        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 预计算一些常用查询
    common_d_values = [3.34, 4.26, 1.82, 2.45, 2.28]
    
    for d_value in common_d_values:
        cursor.execute('''
        SELECT COUNT(DISTINCT p.card_num)
        FROM pdf2_peaks p
        WHERE ABS(p.d_value - ?) <= 0.02
        ''', (d_value,))
        
        count = cursor.fetchone()[0]
        
        cursor.execute('''
        INSERT OR REPLACE INTO common_queries (query_type, query_key, result_count)
        VALUES (?, ?, ?)
        ''', ('d_search', str(d_value), count))
    
    conn.commit()
    conn.close()
    
    print(f"\n数据库优化完成: {db_path}")
    print("现在可以使用 v_quick_search 视图进行快速查询")

if __name__ == '__main__':
    simple_integration()