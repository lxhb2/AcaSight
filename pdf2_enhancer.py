#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 数据库增强工具
整合summary.dat和mineral.dat，优化算法
"""

import sqlite3
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

class PDF2Enhancer:
    """PDF2数据库增强工具"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.base_dir = self.db_path.parent
        
    def parse_summary_dat(self) -> List[Dict]:
        """解析summary.dat文件"""
        summary_path = self.base_dir / "summary.dat"
        if not summary_path.exists():
            print(f"未找到summary.dat文件: {summary_path}")
            return []
        
        print(f"开始解析 {summary_path}...")
        file_size = summary_path.stat().st_size
        print(f"文件大小: {file_size / 1024 / 1024:.1f} MB")
        
        records = []
        
        with open(summary_path, 'rb') as f:
            # 读取整个文件
            data = f.read()
        
        # 分析文件结构
        # 看起来是固定宽度格式
        # 每行似乎包含: 名称(80字符) + 化学式(40字符) + 其他信息
        
        pos = 0
        record_count = 0
        
        while pos < len(data):
            # 读取名称 (最多80字符)
            if pos + 80 > len(data):
                break
                
            name_bytes = data[pos:pos+80]
            try:
                name = name_bytes.decode('utf-8').rstrip()
            except:
                name = name_bytes.decode('latin-1').rstrip()
            
            pos += 80
            
            # 读取化学式 (最多40字符)
            if pos + 40 > len(data):
                break
                
            formula_bytes = data[pos:pos+40]
            try:
                formula = formula_bytes.decode('utf-8').rstrip()
            except:
                formula = formula_bytes.decode('latin-1').rstrip()
            
            pos += 40
            
            # 读取其他信息 (20字符)
            if pos + 20 > len(data):
                break
                
            info_bytes = data[pos:pos+20]
            try:
                info = info_bytes.decode('utf-8').rstrip()
            except:
                info = info_bytes.decode('latin-1').rststrip()
            
            pos += 20
            
            # 跳过可能的填充或分隔符
            # 查找下一个非空名称的开始
            while pos < len(data) and data[pos] == 0:
                pos += 1
            
            # 如果名称不为空，添加到记录
            if name.strip():
                record = {
                    'name': name.strip(),
                    'formula': formula.strip(),
                    'info': info.strip(),
                    'record_index': record_count
                }
                records.append(record)
                record_count += 1
                
                if record_count % 10000 == 0:
                    print(f"已解析 {record_count} 条记录")
        
        print(f"解析完成！找到 {len(records)} 条记录")
        return records
    
    def parse_mineral_dat(self) -> List[Dict]:
        """解析mineral.dat文件"""
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
        
        # mineral.dat似乎是矿物代码和名称的映射
        # 格式: "ADA 4 Andalusite            4      ADA 5 arsenate ..."
        
        minerals = []
        
        # 使用正则表达式提取矿物信息
        # 模式: 代码(3字符) + 空格 + 数字 + 空格 + 名称 + 空格 + 数字
        pattern = re.compile(r'([A-Z]{3})\s+(\d+)\s+([A-Za-z\-]+)\s+(\d+)')
        
        matches = pattern.findall(text)
        for code, code_num, name, name_num in matches:
            mineral = {
                'code': code,
                'code_num': int(code_num),
                'name': name,
                'name_num': int(name_num)
            }
            minerals.append(mineral)
        
        print(f"解析完成！找到 {len(minerals)} 种矿物")
        
        # 显示前10种矿物
        print("\n前10种矿物:")
        for i, mineral in enumerate(minerals[:10]):
            print(f"  {i+1}. {mineral['code']} ({mineral['code_num']}): {mineral['name']}")
        
        return minerals
    
    def enhance_database(self):
        """增强数据库"""
        if not self.db_path.exists():
            print(f"数据库不存在: {self.db_path}")
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        print("开始增强数据库...")
        
        # 1. 创建summary表
        print("\n1. 创建summary表...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            formula TEXT,
            info TEXT,
            record_index INTEGER
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_name ON pdf2_summary(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_summary_formula ON pdf2_summary(formula)')
        
        # 2. 创建minerals表
        print("2. 创建minerals表...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_minerals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            code_num INTEGER,
            name TEXT,
            name_num INTEGER
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_minerals_code ON pdf2_minerals(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_minerals_name ON pdf2_minerals(name)')
        
        # 3. 创建增强的搜索视图
        print("3. 创建增强的搜索视图...")
        
        # 视图1: 卡片与摘要的联合视图
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS v_cards_enhanced AS
        SELECT 
            c.card_num,
            c.card_num_str,
            COALESCE(s.name, c.name) as name,
            COALESCE(s.formula, c.formula) as formula,
            c.cas,
            c.card_type,
            c.radiation,
            c.wavelength,
            c.n_peaks,
            c.d_min,
            c.d_max,
            c.i_max
        FROM pdf2_cards c
        LEFT JOIN pdf2_summary s ON c.card_num_str = 'M' || printf('%09d', s.record_index + 1000)
        ''')
        
        # 视图2: 矿物相关卡片
        cursor.execute('''
        CREATE VIEW IF NOT EXISTS v_mineral_cards AS
        SELECT 
            c.*,
            m.code as mineral_code,
            m.name as mineral_name
        FROM pdf2_cards c
        JOIN pdf2_minerals m ON c.name LIKE '%' || m.name || '%'
        WHERE c.card_type = 'Mineral' OR c.card_type = 'Inorganic'
        ''')
        
        # 4. 创建优化搜索函数
        print("4. 创建优化搜索函数...")
        
        # 函数1: 按d值范围搜索
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_search_cache (
            search_key TEXT PRIMARY KEY,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        
        # 5. 解析并插入数据
        print("\n5. 解析并插入数据...")
        
        # 解析summary.dat
        summary_records = self.parse_summary_dat()
        if summary_records:
            print(f"插入 {len(summary_records)} 条summary记录...")
            for record in summary_records:
                cursor.execute('''
                INSERT OR REPLACE INTO pdf2_summary (name, formula, info, record_index)
                VALUES (?, ?, ?, ?)
                ''', (record['name'], record['formula'], record['info'], record['record_index']))
            
            conn.commit()
            print("summary数据插入完成")
        
        # 解析mineral.dat
        mineral_records = self.parse_mineral_dat()
        if mineral_records:
            print(f"插入 {len(mineral_records)} 条mineral记录...")
            for record in mineral_records:
                cursor.execute('''
                INSERT OR REPLACE INTO pdf2_minerals (code, code_num, name, name_num)
                VALUES (?, ?, ?, ?)
                ''', (record['code'], record['code_num'], record['name'], record['name_num']))
            
            conn.commit()
            print("mineral数据插入完成")
        
        # 6. 创建统计信息
        print("\n6. 创建统计信息...")
        
        cursor.execute('SELECT COUNT(*) FROM pdf2_summary')
        summary_count = cursor.fetchone()[0]
        print(f"  summary记录数: {summary_count}")
        
        cursor.execute('SELECT COUNT(*) FROM pdf2_minerals')
        mineral_count = cursor.fetchone()[0]
        print(f"  矿物种类数: {mineral_count}")
        
        cursor.execute('SELECT COUNT(DISTINCT card_type) FROM pdf2_cards')
        card_types = cursor.fetchone()[0]
        print(f"  卡片类型数: {card_types}")
        
        # 卡片类型分布
        cursor.execute('''
        SELECT card_type, COUNT(*) as count 
        FROM pdf2_cards 
        GROUP BY card_type 
        ORDER BY count DESC
        ''')
        print("  卡片类型分布:")
        for card_type, count in cursor.fetchall():
            print(f"    {card_type or 'Unknown'}: {count:,}")
        
        conn.close()
        
        print(f"\n数据库增强完成！")
        print(f"增强后的数据库: {self.db_path}")
    
    def create_optimized_search(self):
        """创建优化搜索功能"""
        if not self.db_path.exists():
            print(f"数据库不存在: {self.db_path}")
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        print("创建优化搜索功能...")
        
        # 1. 创建d值搜索优化索引
        print("1. 创建d值搜索优化索引...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_peaks_d_range ON pdf2_peaks(d_value)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_peaks_intensity ON pdf2_peaks(intensity)')
        
        # 2. 创建物相鉴定辅助表
        print("2. 创建物相鉴定辅助表...")
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_phase_matching (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_num INTEGER,
            d_values_json TEXT,
            i_values_json TEXT,
            fingerprint TEXT,
            FOREIGN KEY (card_num) REFERENCES pdf2_cards(card_num)
        )
        ''')
        
        # 3. 创建常用矿物表
        print("3. 创建常用矿物表...")
        common_minerals = [
            ('QUARTZ', 'SiO2', '石英'),
            ('CALCITE', 'CaCO3', '方解石'),
            ('DOLOMITE', 'CaMg(CO3)2', '白云石'),
            ('FELDSPAR', '(K,Na)AlSi3O8', '长石'),
            ('PYRITE', 'FeS2', '黄铁矿'),
            ('HEMATITE', 'Fe2O3', '赤铁矿'),
            ('MAGNETITE', 'Fe3O4', '磁铁矿'),
            ('GYPSUM', 'CaSO4·2H2O', '石膏'),
            ('HALITE', 'NaCl', '岩盐'),
            ('FLUORITE', 'CaF2', '萤石')
        ]
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_common_minerals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mineral_name TEXT,
            formula TEXT,
            chinese_name TEXT,
            common_d_values TEXT
        )
        ''')
        
        for mineral_name, formula, chinese_name in common_minerals:
            cursor.execute('''
            INSERT OR REPLACE INTO pdf2_common_minerals (mineral_name, formula, chinese_name)
            VALUES (?, ?, ?)
            ''', (mineral_name, formula, chinese_name))
        
        conn.commit()
        conn.close()
        
        print("优化搜索功能创建完成")
    
    def run_benchmark(self):
        """运行性能基准测试"""
        if not self.db_path.exists():
            print(f"数据库不存在: {self.db_path}")
            return
        
        import time
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        print("运行性能基准测试...")
        
        # 测试1: d值搜索
        print("\n1. d值搜索测试 (d=3.34 ±0.02)...")
        start_time = time.time()
        cursor.execute('''
        SELECT COUNT(DISTINCT p.card_num) 
        FROM pdf2_peaks p
        WHERE ABS(p.d_value - 3.34) <= 0.02
        ''')
        count = cursor.fetchone()[0]
        elapsed = time.time() - start_time
        print(f"  找到 {count} 张卡片，耗时 {elapsed*1000:.1f} ms")
        
        # 测试2: 名称搜索
        print("\n2. 名称搜索测试 (包含'quartz')...")
        start_time = time.time()
        cursor.execute('''
        SELECT COUNT(*) 
        FROM pdf2_cards 
        WHERE name LIKE '%quartz%'
        ''')
        count = cursor.fetchone()[0]
        elapsed = time.time() - start_time
        print(f"  找到 {count} 张卡片，耗时 {elapsed*1000:.1f} ms")
        
        # 测试3: 化学式搜索
        print("\n3. 化学式搜索测试 (包含'SiO2')...")
        start_time = time.time()
        cursor.execute('''
        SELECT COUNT(*) 
        FROM pdf2_cards 
        WHERE formula LIKE '%SiO2%'
        ''')
        count = cursor.fetchone()[0]
        elapsed = time.time() - start_time
        print(f"  找到 {count} 张卡片，耗时 {elapsed*1000:.1f} ms")
        
        # 测试4: 多峰匹配
        print("\n4. 多峰匹配测试 (3个峰)...")
        test_peaks = [(3.34, 100), (4.26, 80), (1.82, 60)]
        
        start_time = time.time()
        
        # 构建查询
        query = '''
        SELECT DISTINCT c.card_num, c.name, c.formula, 
               COUNT(p.d_value) as matched_peaks,
               AVG(ABS(p.d_value - ?)) as avg_d_error
        FROM pdf2_cards c
        JOIN pdf2_peaks p ON c.card_num = p.card_num
        WHERE (ABS(p.d_value - ?) <= 0.02 AND p.intensity >= ?)
           OR (ABS(p.d_value - ?) <= 0.02 AND p.intensity >= ?)
           OR (ABS(p.d_value - ?) <= 0.02 AND p.intensity >= ?)
        GROUP BY c.card_num
        HAVING matched_peaks >= 2
        ORDER BY avg_d_error ASC
        LIMIT 10
        '''
        
        params = []
        for d, i in test_peaks:
            params.extend([d, d, i*0.5])  # d值, d值(重复), 强度阈值
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        elapsed = time.time() - start_time
        print(f"  找到 {len(results)} 张匹配卡片，耗时 {elapsed*1000:.1f} ms")
        
        if results:
            print("  前3个匹配结果:")
            for i, (card_num, name, formula, matched_peaks, avg_error) in enumerate(results[:3]):
                print(f"    {i+1}. {name} ({formula}), 匹配峰: {matched_peaks}, 平均误差: {avg_error:.4f} Å")
        
        conn.close()
        
        print("\n基准测试完成！")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("PDF2-2004 数据库增强工具")
        print("=" * 60)
        print("用法: python pdf2_enhancer.py <数据库路径> [命令]")
        print()
        print("命令:")
        print("  --enhance         增强数据库 (整合summary/mineral)")
        print("  --optimize        优化搜索功能")
        print("  --benchmark       运行性能基准测试")
        print("  --all             执行所有操作")
        print()
        print("示例:")
        print("  python pdf2_enhancer.py F:\\桌面\\pdf2_final_complete.db --all")
        return
    
    db_path = sys.argv[1]
    command = '--all' if len(sys.argv) < 3 else sys.argv[2]
    
    enhancer = PDF2Enhancer(db_path)
    
    if command == '--enhance' or command == '--all':
        enhancer.enhance_database()
    
    if command == '--optimize' or command == '--all':
        enhancer.create_optimized_search()
    
    if command == '--benchmark' or command == '--all':
        enhancer.run_benchmark()

if __name__ == '__main__':
    main()