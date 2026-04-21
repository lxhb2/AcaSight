#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库清理和优化
移除重复表，保留最佳版本
"""

import sqlite3
from pathlib import Path

def cleanup_database():
    """清理数据库，移除重复表"""
    db_path = Path(r"F:\桌面\pdf2_final_complete.db")
    
    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("开始数据库清理和优化...")
    print("=" * 60)
    
    # 1. 检查当前表
    print("1. 当前数据库表:")
    cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    for name, type_ in tables:
        cursor.execute(f'SELECT COUNT(*) FROM "{name}"')
        count = cursor.fetchone()[0]
        print(f"  {name}: {count:,} 条记录")
    
    # 2. 清理重复的summary表
    print("\n2. 清理重复的summary表...")
    summary_tables = [t[0] for t in tables if 'summary' in t[0].lower()]
    
    if len(summary_tables) > 1:
        print(f"  找到 {len(summary_tables)} 个summary表: {summary_tables}")
        
        # 保留最新的表，删除旧的
        keep_table = 'pdf2_summary_final'  # 最新版本
        for table in summary_tables:
            if table != keep_table:
                print(f"  删除旧表: {table}")
                cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
    
    # 3. 清理重复的mineral表
    print("\n3. 清理重复的mineral表...")
    mineral_tables = [t[0] for t in tables if 'mineral' in t[0].lower() and 'common' not in t[0].lower()]
    
    if len(mineral_tables) > 1:
        print(f"  找到 {len(mineral_tables)} 个mineral表: {mineral_tables}")
        
        # 保留最新的表
        keep_table = 'pdf2_minerals_final'  # 最新版本
        for table in mineral_tables:
            if table != keep_table:
                print(f"  删除旧表: {table}")
                cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
    
    # 4. 清理无用的表
    print("\n4. 清理无用的表...")
    useless_tables = ['pdf2_phase_matching', 'pdf2_search_cache', 'search_cache']
    
    for table in useless_tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if cursor.fetchone():
            print(f"  删除无用表: {table}")
            cursor.execute(f'DROP TABLE IF EXISTS "{table}"')
    
    # 5. 优化视图
    print("\n5. 优化视图...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
    views = cursor.fetchall()
    
    print(f"  当前视图 ({len(views)}个):")
    for view in views:
        print(f"    {view[0]}")
    
    # 推荐使用的主视图
    main_views = ['v_final_search', 'v_quick_search_enhanced', 'v_minerals_only']
    
    # 删除可能冲突的旧视图
    old_views = ['v_cards_enhanced', 'v_enhanced_cards', 'v_mineral_cards', 'v_quick_search']
    for view in old_views:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='view' AND name='{view}'")
        if cursor.fetchone():
            print(f"  删除旧视图: {view}")
            cursor.execute(f'DROP VIEW IF EXISTS "{view}"')
    
    conn.commit()
    
    # 6. 重新创建优化的主视图
    print("\n6. 创建优化的主视图...")
    
    # 确保使用正确的表名
    summary_table = 'pdf2_summary_final'
    mineral_table = 'pdf2_minerals_final'
    
    # 创建统一的主视图
    cursor.execute('DROP VIEW IF EXISTS v_main_search')
    
    cursor.execute(f'''
    CREATE VIEW v_main_search AS
    SELECT 
        c.card_num,
        c.card_num_str,
        -- 名称处理
        CASE 
            WHEN s.name IS NOT NULL THEN 
                CASE 
                    WHEN s.name LIKE '$G%' THEN 'β-' || SUBSTR(s.name, 3)
                    WHEN s.name LIKE '$A%' THEN 'α-' || SUBSTR(s.name, 3)
                    WHEN s.name LIKE 'odium%' THEN 'Sodium' || SUBSTR(s.name, 6)
                    WHEN s.name LIKE 'otassium%' THEN 'Potassium' || SUBSTR(c.name, 9)
                    WHEN s.name LIKE 'arium%' THEN 'Barium' || SUBSTR(c.name, 6)
                    ELSE s.name
                END
            WHEN c.name LIKE 'odium%' THEN 'Sodium' || SUBSTR(c.name, 6)
            WHEN c.name LIKE 'otassium%' THEN 'Potassium' || SUBSTR(c.name, 9)
            WHEN c.name LIKE 'arium%' THEN 'Barium' || SUBSTR(c.name, 6)
            ELSE c.name
        END as display_name,
        
        -- 化学式处理
        COALESCE(s.formula, c.formula) as display_formula,
        
        c.cas,
        c.card_type,
        c.radiation,
        c.wavelength,
        c.n_peaks,
        c.d_min,
        c.d_max,
        c.i_max,
        
        -- 矿物信息
        m.full_name as mineral_info,
        
        -- 是否为矿物
        CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END as is_mineral,
        
        -- 卡片质量指标
        CASE 
            WHEN c.n_peaks >= 20 THEN 'High'
            WHEN c.n_peaks >= 10 THEN 'Medium'
            ELSE 'Low'
        END as data_quality
        
    FROM pdf2_cards c
    LEFT JOIN {summary_table} s ON c.card_num = s.card_index + 1000
    LEFT JOIN {mineral_table} m ON (
        c.card_type = 'Mineral' 
        AND (c.name LIKE '%' || m.name || '%' OR m.name LIKE '%' || c.name || '%')
    )
    ''')
    
    # 7. 创建索引优化
    print("\n7. 创建优化索引...")
    
    # 删除旧索引
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
    old_indexes = cursor.fetchall()
    
    if old_indexes:
        print(f"  删除 {len(old_indexes)} 个旧索引...")
        for index in old_indexes:
            cursor.execute(f'DROP INDEX IF EXISTS "{index[0]}"')
    
    # 创建关键索引
    indexes = [
        ('idx_cards_card_num', 'pdf2_cards(card_num)'),
        ('idx_peaks_card_num', 'pdf2_peaks(card_num)'),
        ('idx_peaks_d_value', 'pdf2_peaks(d_value)'),
        ('idx_peaks_intensity', 'pdf2_peaks(intensity)'),
        ('idx_summary_card_index', f'{summary_table}(card_index)'),
        ('idx_summary_name', f'{summary_table}(name)'),
        ('idx_minerals_name', f'{mineral_table}(name)'),
    ]
    
    for index_name, index_def in indexes:
        print(f"  创建索引: {index_name}")
        cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}')
    
    conn.commit()
    
    # 8. 分析表优化
    print("\n8. 分析表优化...")
    cursor.execute('ANALYZE')
    
    # 9. 最终统计
    print("\n9. 最终数据库统计...")
    
    cursor.execute("SELECT COUNT(*) FROM pdf2_cards")
    total_cards = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM pdf2_peaks")
    total_peaks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM v_main_search WHERE is_mineral = 1")
    mineral_cards = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT display_name) FROM v_main_search")
    unique_names = cursor.fetchone()[0]
    
    print(f"  总卡片数: {total_cards:,}")
    print(f"  峰数据总数: {total_peaks:,}")
    print(f"  矿物卡片数: {mineral_cards}")
    print(f"  唯一化合物名称: {unique_names:,}")
    
    # 显示优化后的表结构
    print("\n10. 优化后的表结构:")
    cursor.execute("SELECT name, type FROM sqlite_master ORDER BY type, name")
    final_items = cursor.fetchall()
    
    tables_final = [i for i in final_items if i[1] == 'table']
    views_final = [i for i in final_items if i[1] == 'view']
    indexes_final = [i for i in final_items if i[1] == 'index']
    
    print(f"  表 ({len(tables_final)}个):")
    for name, _ in tables_final:
        cursor.execute(f'SELECT COUNT(*) FROM "{name}"')
        count = cursor.fetchone()[0]
        print(f"    {name}: {count:,} 条记录")
    
    print(f"\n  视图 ({len(views_final)}个):")
    for name, _ in views_final:
        print(f"    {name}")
    
    print(f"\n  索引 ({len(indexes_final)}个):")
    for name, _ in indexes_final:
        print(f"    {name}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 60)
    print("数据库清理和优化完成！")
    print("=" * 60)
    print(f"数据库: {db_path}")
    print("主视图: v_main_search (推荐使用)")
    print("=" * 60)
    print("使用建议:")
    print("  1. 使用 v_main_search 进行所有查询")
    print("  2. 通过 card_num 关联 pdf2_peaks 表进行峰搜索")
    print("  3. 利用索引优化查询性能")
    print("=" * 60)

if __name__ == '__main__':
    cleanup_database()