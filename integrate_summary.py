#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合summary.dat到数据库
"""

import sqlite3
import struct
from pathlib import Path
from typing import List, Dict
import sys

def integrate_summary_dat():
    """整合summary.dat文件"""
    summary_path = Path(r"D:\百度网盘下载\XRD数据软件MDI Jade 6.5\PDF2-2004\summary.dat")
    db_path = Path(r"F:\桌面\pdf2_final_complete.db")
    
    if not summary_path.exists():
        print(f"未找到summary.dat文件: {summary_path}")
        return
    
    if not db_path.exists():
        print(f"未找到数据库文件: {db_path}")
        return
    
    print(f"开始整合 {summary_path}...")
    file_size = summary_path.stat().st_size
    print(f"文件大小: {file_size / 1024 / 1024:.1f} MB")
    
    # 连接到数据库
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 创建summary表（如果不存在）
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pdf2_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_index INTEGER UNIQUE,
        name TEXT,
        formula TEXT,
        info TEXT
    )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_name ON pdf2_summary(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_formula ON pdf2_summary(formula)')
    
    # 解析summary.dat
    # 根据分析，文件结构似乎是：
    # 名称(80字节) + 化学式(40字节) + 信息(20字节) + 填充/分隔符
    
    records = []
    
    with open(summary_path, 'rb') as f:
        data = f.read()
    
    pos = 0
    record_index = 0
    
    while pos < len(data):
        # 读取名称 (80字节)
        if pos + 80 > len(data):
            break
        
        name_bytes = data[pos:pos+80]
        try:
            name = name_bytes.decode('utf-8').rstrip()
        except:
            name = name_bytes.decode('latin-1').rstrip()
        
        pos += 80
        
        # 读取化学式 (40字节)
        if pos + 40 > len(data):
            break
        
        formula_bytes = data[pos:pos+40]
        try:
            formula = formula_bytes.decode('utf-8').rstrip()
        except:
            formula = formula_bytes.decode('latin-1').rstrip()
        
        pos += 40
        
        # 读取信息 (20字节)
        if pos + 20 > len(data):
            break
        
        info_bytes = data[pos:pos+20]
        try:
            info = info_bytes.decode('utf-8').rstrip()
        except:
            info = info_bytes.decode('latin-1').rstrip()
        
        pos += 20
        
        # 跳过可能的填充或分隔符
        # 查找下一个非空名称的开始
        while pos < len(data) and data[pos] == 0:
            pos += 1
        
        # 如果名称不为空，添加到记录
        if name.strip():
            record = {
                'card_index': record_index,
                'name': name.strip(),
                'formula': formula.strip(),
                'info': info.strip()
            }
            records.append(record)
            record_index += 1
            
            if record_index % 10000 == 0:
                print(f"已解析 {record_index} 条记录")
    
    print(f"解析完成！找到 {len(records)} 条记录")
    
    # 插入数据库
    print("插入数据库...")
    
    for i, record in enumerate(records):
        cursor.execute('''
        INSERT OR REPLACE INTO pdf2_summary (card_index, name, formula, info)
        VALUES (?, ?, ?, ?)
        ''', (record['card_index'], record['name'], record['formula'], record['info']))
        
        if i % 10000 == 0:
            conn.commit()
            print(f"已插入 {i} 条记录")
    
    conn.commit()
    
    # 创建与主表的关联
    print("创建与主表的关联...")
    
    # 创建视图，将summary与cards关联
    cursor.execute('''
    CREATE VIEW IF NOT EXISTS v_cards_with_summary AS
    SELECT 
        c.card_num,
        c.card_num_str,
        COALESCE(s.name, c.name) as display_name,
        COALESCE(s.formula, c.formula) as display_formula,
        c.cas,
        c.card_type,
        c.radiation,
        c.wavelength,
        c.n_peaks,
        c.d_min,
        c.d_max,
        c.i_max,
        s.info as summary_info
    FROM pdf2_cards c
    LEFT JOIN pdf2_summary s ON c.card_num = s.card_index + 1000
    ''')
    
    # 验证关联
    cursor.execute('SELECT COUNT(*) FROM pdf2_summary')
    summary_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM v_cards_with_summary WHERE display_name != name')
    updated_count = cursor.fetchone()[0]
    
    print(f"\n整合完成！")
    print(f"summary记录数: {summary_count}")
    print(f"更新名称的卡片数: {updated_count}")
    
    # 显示示例
    print("\n整合后的示例 (前5张卡片):")
    cursor.execute('''
    SELECT card_num_str, display_name, display_formula, card_type 
    FROM v_cards_with_summary 
    LIMIT 5
    ''')
    
    for row in cursor.fetchall():
        print(f"  卡片号: {row[0]}")
        print(f"  名称: {row[1]}")
        print(f"  化学式: {row[2]}")
        print(f"  类型: {row[3]}")
        print()
    
    conn.close()
    
    print(f"数据库已更新: {db_path}")

def integrate_mineral_dat():
    """整合mineral.dat文件"""
    mineral_path = Path(r"D:\百度网盘下载\XRD数据软件MDI Jade 6.5\PDF2-2004\mineral.dat")
    db_path = Path(r"F:\桌面\pdf2_final_complete.db")
    
    if not mineral_path.exists():
        print(f"未找到mineral.dat文件: {mineral_path}")
        return
    
    if not db_path.exists():
        print(f"未找到数据库文件: {db_path}")
        return
    
    print(f"开始整合 {mineral_path}...")
    
    with open(mineral_path, 'rb') as f:
        data = f.read()
    
    try:
        text = data.decode('utf-8')
    except:
        text = data.decode('latin-1')
    
    # mineral.dat格式分析:
    # "ADA 4 Andalusite            4      ADA 5 arsenate ..."
    # 似乎是矿物代码和名称的映射
    
    import re
    
    # 尝试不同的解析模式
    minerals = []
    
    # 模式1: 代码 + 数字 + 名称 + 数字
    pattern1 = re.compile(r'([A-Z]{2,4})\s+(\d+)\s+([A-Za-z\-]+)\s+(\d+)')
    matches1 = pattern1.findall(text)
    
    for code, code_num, name, name_num in matches1:
        minerals.append({
            'code': code,
            'code_num': int(code_num),
            'name': name,
            'name_num': int(name_num)
        })
    
    # 模式2: 名称后可能有空格和数字
    pattern2 = re.compile(r'([A-Z]{2,4})\s+(\d+)\s+([A-Za-z\-]+\s+[A-Za-z\-]*)\s+(\d+)')
    matches2 = pattern2.findall(text)
    
    for code, code_num, name, name_num in matches2:
        minerals.append({
            'code': code,
            'code_num': int(code_num),
            'name': name.strip(),
            'name_num': int(name_num)
        })
    
    print(f"找到 {len(minerals)} 种矿物")
    
    if minerals:
        print("\n前10种矿物:")
        for i, mineral in enumerate(minerals[:10]):
            print(f"  {i+1}. {mineral['code']} ({mineral['code_num']}): {mineral['name']}")
        
        # 插入数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_minerals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            code_num INTEGER,
            name TEXT,
            name_num INTEGER
        )
        ''')
        
        for mineral in minerals:
            cursor.execute('''
            INSERT OR REPLACE INTO pdf2_minerals (code, code_num, name, name_num)
            VALUES (?, ?, ?, ?)
            ''', (mineral['code'], mineral['code_num'], mineral['name'], mineral['name_num']))
        
        conn.commit()
        conn.close()
        
        print(f"\n矿物数据已整合到数据库")
    else:
        print("未解析到矿物数据")

def main():
    """主函数"""
    print("PDF2-2004 数据整合工具")
    print("=" * 60)
    
    print("1. 整合summary.dat...")
    integrate_summary_dat()
    
    print("\n" + "=" * 60)
    print("2. 整合mineral.dat...")
    integrate_mineral_dat()
    
    print("\n" + "=" * 60)
    print("整合完成！")

if __name__ == '__main__':
    main()