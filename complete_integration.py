#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 数据完整整合优化
"""

import sqlite3
import struct
import re
from pathlib import Path
from typing import List, Dict, Tuple
import sys
import time

class CompletePDF2Integration:
    """PDF2-2004 数据完整整合"""
    
    def __init__(self):
        self.base_dir = Path(r"D:\百度网盘下载\XRD数据软件MDI Jade 6.5\PDF2-2004")
        self.db_path = Path(r"F:\桌面\pdf2_final_complete.db")
        
        if not self.base_dir.exists():
            raise FileNotFoundError(f"PDF2目录不存在: {self.base_dir}")
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库不存在: {self.db_path}")
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
    
    def parse_summary_dat_complete(self) -> List[Dict]:
        """完整解析summary.dat文件"""
        summary_path = self.base_dir / "summary.dat"
        if not summary_path.exists():
            print(f"未找到summary.dat文件: {summary_path}")
            return []
        
        print(f"开始完整解析 {summary_path}...")
        file_size = summary_path.stat().st_size
        print(f"文件大小: {file_size / 1024 / 1024:.1f} MB")
        
        records = []
        
        with open(summary_path, 'rb') as f:
            data = f.read()
        
        # 分析文件结构
        # 根据之前的分析，每张卡片似乎占用144字节
        # 名称(80字节) + 化学式(40字节) + 其他信息(24字节)
        
        record_size = 144  # 假设的记录大小
        total_records = len(data) // record_size
        
        print(f"预计记录数: {total_records:,}")
        
        for i in range(total_records):
            pos = i * record_size
            
            if pos + 80 > len(data):
                break
            
            # 读取名称 (80字节)
            name_bytes = data[pos:pos+80]
            try:
                name = name_bytes.decode('utf-8').rstrip('\x00').strip()
            except:
                name = name_bytes.decode('latin-1').rstrip('\x00').strip()
            
            # 读取化学式 (40字节)
            formula_bytes = data[pos+80:pos+120]
            try:
                formula = formula_bytes.decode('utf-8').rstrip('\x00').strip()
            except:
                formula = formula_bytes.decode('latin-1').rstrip('\x00').strip()
            
            # 读取其他信息 (24字节)
            info_bytes = data[pos+120:pos+144]
            try:
                info = info_bytes.decode('utf-8').rstrip('\x00').strip()
            except:
                info = info_bytes.decode('latin-1').rstrip('\x00').strip()
            
            # 清理名称中的特殊字符
            name = self._clean_name(name)
            
            if name:  # 只添加非空记录
                record = {
                    'card_index': i + 1,  # 从1开始
                    'name': name,
                    'formula': formula,
                    'info': info
                }
                records.append(record)
            
            if (i + 1) % 10000 == 0:
                print(f"已解析 {i+1:,} 条记录")
        
        print(f"解析完成！找到 {len(records)} 条有效记录")
        return records
    
    def _clean_name(self, name: str) -> str:
        """清理化合物名称"""
        if not name:
            return name
        
        # 处理特殊前缀
        special_prefixes = {
            '$G': 'β-',    # beta
            '$A': 'α-',    # alpha
            '$D': 'Δ-',    # delta
            '$B': '',      # 可能表示某种格式
            '$S': '',      # 可能表示某种格式
        }
        
        for prefix, replacement in special_prefixes.items():
            if name.startswith(prefix):
                name = replacement + name[len(prefix):]
        
        # 处理其他特殊字符
        name = name.replace('$', '')
        
        # 标准化常见化合物名称
        name_replacements = {
            'odium': 'Sodium',
            'otassium': 'Potassium',
            'arium': 'Barium',
            'alcium': 'Calcium',
            'agnesium': 'Magnesium',
            'luminum': 'Aluminum',
            'ron': 'Iron',
            'opper': 'Copper',
            'inc': 'Zinc',
            'ead': 'Lead',
            'ilver': 'Silver',
            'old': 'Gold',
        }
        
        for wrong, correct in name_replacements.items():
            if name.startswith(wrong):
                name = correct + name[len(wrong):]
        
        return name
    
    def parse_mineral_dat_complete(self) -> List[Dict]:
        """完整解析mineral.dat文件"""
        mineral_path = self.base_dir / "mineral.dat"
        if not mineral_path.exists():
            print(f"未找到mineral.dat文件: {mineral_path}")
            return []
        
        print(f"开始解析 {mineral_path}...")
        
        with open(mineral_path, 'rb') as f:
            data = f.read()
        
        try:
            text = data.decode('utf-8')
        except:
            text = data.decode('latin-1')
        
        # mineral.dat 格式分析
        # 似乎是矿物代码和名称的紧凑格式
        # 示例: "ADA 4 Andalusite            4      ADA 5 arsenate ..."
        
        minerals = []
        
        # 使用更灵活的正则表达式
        # 匹配模式: 代码(2-4大写字母) + 空格 + 数字 + 空格 + 名称(可能包含空格) + 空格 + 数字
        pattern = re.compile(r'([A-Z]{2,4})\s+(\d+)\s+([A-Za-z\-][A-Za-z\-\s]*?)\s+(\d+)')
        
        matches = pattern.findall(text)
        
        for code, code_num, name, name_num in matches:
            # 清理名称
            name = name.strip()
            
            mineral = {
                'code': code.strip(),
                'code_num': int(code_num),
                'name': name,
                'name_num': int(name_num),
                'full_name': f"{name} ({code})"
            }
            minerals.append(mineral)
        
        print(f"解析完成！找到 {len(minerals)} 种矿物")
        
        # 显示示例
        print("\n矿物示例 (前10种):")
        for i, mineral in enumerate(minerals[:10]):
            print(f"  {i+1}. {mineral['code']}: {mineral['name']}")
        
        return minerals
    
    def integrate_all_data(self):
        """整合所有数据"""
        print("开始PDF2-2004数据完整整合...")
        print("=" * 60)
        
        start_time = time.time()
        
        # 1. 备份当前数据库
        print("1. 备份当前数据库...")
        backup_path = self.db_path.with_suffix('.db.backup')
        import shutil
        shutil.copy2(self.db_path, backup_path)
        print(f"   备份已创建: {backup_path}")
        
        # 2. 创建增强表结构
        print("\n2. 创建增强表结构...")
        cursor = self.conn.cursor()
        
        # 删除旧表（如果存在）
        cursor.execute('DROP TABLE IF EXISTS pdf2_summary_complete')
        cursor.execute('DROP TABLE IF EXISTS pdf2_minerals_complete')
        cursor.execute('DROP VIEW IF EXISTS v_enhanced_cards')
        
        # 创建完整的summary表
        cursor.execute('''
        CREATE TABLE pdf2_summary_complete (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_index INTEGER UNIQUE,
            name TEXT,
            formula TEXT,
            info TEXT,
            cleaned_name TEXT,
            name_length INTEGER,
            formula_length INTEGER
        )
        ''')
        
        # 创建完整的minerals表
        cursor.execute('''
        CREATE TABLE pdf2_minerals_complete (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            code_num INTEGER,
            name TEXT,
            name_num INTEGER,
            full_name TEXT,
            UNIQUE(code, name)
        )
        ''')
        
        self.conn.commit()
        
        # 3. 解析并插入summary数据
        print("\n3. 解析并插入summary数据...")
        summary_records = self.parse_summary_dat_complete()
        
        if summary_records:
            print(f"插入 {len(summary_records):,} 条summary记录...")
            for i, record in enumerate(summary_records):
                cursor.execute('''
                INSERT OR REPLACE INTO pdf2_summary_complete 
                (card_index, name, formula, info, cleaned_name, name_length, formula_length)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['card_index'],
                    record['name'],
                    record['formula'],
                    record['info'],
                    self._clean_name(record['name']),
                    len(record['name']),
                    len(record['formula'])
                ))
                
                if (i + 1) % 10000 == 0:
                    self.conn.commit()
                    print(f"   已插入 {i+1:,} 条记录")
            
            self.conn.commit()
            print("   summary数据插入完成")
        
        # 4. 解析并插入mineral数据
        print("\n4. 解析并插入mineral数据...")
        mineral_records = self.parse_mineral_dat_complete()
        
        if mineral_records:
            print(f"插入 {len(mineral_records)} 条mineral记录...")
            for record in mineral_records:
                cursor.execute('''
                INSERT OR REPLACE INTO pdf2_minerals_complete 
                (code, code_num, name, name_num, full_name)
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    record['code'],
                    record['code_num'],
                    record['name'],
                    record['name_num'],
                    record['full_name']
                ))
            
            self.conn.commit()
            print("   mineral数据插入完成")
        
        # 5. 创建增强视图
        print("\n5. 创建增强视图...")
        
        # 主增强视图
        cursor.execute('''
        CREATE VIEW v_enhanced_cards AS
        SELECT 
            c.card_num,
            c.card_num_str,
            -- 优先使用清理后的summary名称，然后是原始名称
            COALESCE(
                s.cleaned_name,
                CASE 
                    WHEN c.name LIKE 'odium%' THEN 'Sodium' || SUBSTR(c.name, 6)
                    WHEN c.name LIKE 'otassium%' THEN 'Potassium' || SUBSTR(c.name, 9)
                    WHEN c.name LIKE 'arium%' THEN 'Barium' || SUBSTR(c.name, 6)
                    WHEN c.name LIKE 'alcium%' THEN 'Calcium' || SUBSTR(c.name, 7)
                    WHEN c.name LIKE '$G%' THEN 'β-' || SUBSTR(c.name, 3)
                    WHEN c.name LIKE '$A%' THEN 'α-' || SUBSTR(c.name, 3)
                    ELSE c.name
                END,
                c.name
            ) as display_name,
            
            -- 优先使用summary化学式，然后是原始化学式
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
            m.code as mineral_code,
            m.name as mineral_name,
            m.full_name as mineral_full_name,
            
            -- summary信息
            s.info as summary_info,
            s.name_length,
            s.formula_length
            
        FROM pdf2_cards c
        LEFT JOIN pdf2_summary_complete s ON c.card_num = s.card_index + 1000
        LEFT JOIN pdf2_minerals_complete m ON (
            c.card_type = 'Mineral' 
            AND (c.name LIKE '%' || m.name || '%' OR m.name LIKE '%' || c.name || '%')
        )
        ''')
        
        # 快速搜索视图
        cursor.execute('''
        CREATE VIEW v_quick_search_enhanced AS
        SELECT 
            card_num,
            card_num_str,
            display_name,
            display_formula,
            cas,
            card_type,
            radiation,
            wavelength,
            n_peaks,
            d_min,
            d_max,
            i_max,
            mineral_code,
            mineral_name,
            summary_info
        FROM v_enhanced_cards
        ''')
        
        # 矿物专用视图
        cursor.execute('''
        CREATE VIEW v_minerals_only AS
        SELECT *
        FROM v_enhanced_cards
        WHERE mineral_name IS NOT NULL
        ORDER BY mineral_name, i_max DESC
        ''')
        
        self.conn.commit()
        
        # 6. 创建索引
        print("\n6. 创建优化索引...")
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_card_index ON pdf2_summary_complete(card_index)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_cleaned_name ON pdf2_summary_complete(cleaned_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_minerals_code ON pdf2_minerals_complete(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_minerals_name ON pdf2_minerals_complete(name)')
        
        # 7. 更新统计信息
        print("\n7. 更新统计信息...")
        
        cursor.execute('SELECT COUNT(*) FROM pdf2_summary_complete')
        summary_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM pdf2_minerals_complete')
        mineral_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM v_enhanced_cards WHERE display_name != name')
        updated_names = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT mineral_name) FROM v_enhanced_cards WHERE mineral_name IS NOT NULL')
        unique_minerals = cursor.fetchone()[0]
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("数据整合完成！")
        print("=" * 60)
        print(f"整合耗时: {elapsed:.1f} 秒")
        print(f"summary记录数: {summary_count:,}")
        print(f"矿物种类数: {mineral_count}")
        print(f"更新名称的卡片: {updated_names:,}")
        print(f"唯一矿物数: {unique_minerals}")
        
        # 显示整合后的示例
        print("\n整合后的示例 (前5张卡片):")
        cursor.execute('''
        SELECT card_num_str, display_name, display_formula, card_type, mineral_name
        FROM v_quick_search_enhanced 
        LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            print(f"\n卡片: {row['card_num_str']}")
            print(f"  名称: {row['display_name']}")
            print(f"  化学式: {row['display_formula']}")
            print(f"  类型: {row['card_type']}")
            if row['mineral_name']:
                print(f"  矿物: {row['mineral_name']}")
        
        print("\n矿物示例 (前5种):")
        cursor.execute('''
        SELECT mineral_name, COUNT(*) as card_count, 
               AVG(n_peaks) as avg_peaks, MAX(i_max) as max_intensity
        FROM v_minerals_only 
        GROUP BY mineral_name
        ORDER BY card_count DESC
        LIMIT 5
        ''')
        
        for row in cursor.fetchall():
            print(f"\n矿物: {row['mineral_name']}")
            print(f"  卡片数: {row['card_count']}")
            print(f"  平均峰数: {row['avg_peaks']:.1f}")
            print(f"  最大强度: {row['max_intensity']}")
        
        cursor.close()
        self.conn.close()
        
        print("\n" + "=" * 60)
        print(f"数据库已完整优化: {self.db_path}")
        print("可用视图:")
        print("  • v_enhanced_cards - 完整增强视图")
        print("  • v_quick_search_enhanced - 快速搜索视图")
        print("  • v_minerals_only - 矿物专用视图")
        print("=" * 60)

def main():
    """主函数"""
    print("PDF2-2004 数据完整整合优化工具")
    print("=" * 60)
    
    try:
        integrator = CompletePDF2Integration()
        integrator.integrate_all_data()
        
    except FileNotFoundError as e:
        print(f"错误: {e}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()