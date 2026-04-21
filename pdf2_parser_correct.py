#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 正确解析器 - 处理固定宽度无换行符格式
"""

import re
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

class PDF2BinaryParser:
    """PDF2-2004 二进制/固定宽度格式解析器"""
    
    def __init__(self, txt_path: str, db_path: str = None):
        self.txt_path = Path(txt_path)
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.txt_path.parent / "pdf2_complete_v2.db"
        
        # 基于实际分析的模式
        self.card_start_pattern = re.compile(b'M\d{9}')
        
    def parse_binary_file(self) -> int:
        """解析二进制格式文件"""
        print(f"开始解析 {self.txt_path}...")
        file_size = self.txt_path.stat().st_size
        print(f"文件大小: {file_size / 1024 / 1024:.1f} MB")
        
        # 创建数据库
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_num INTEGER UNIQUE,
            card_num_str TEXT,
            name TEXT,
            formula TEXT,
            cas TEXT,
            card_type TEXT,
            radiation TEXT,
            wavelength REAL,
            reference TEXT,
            year INTEGER,
            peaks_json TEXT,
            raw_data BLOB
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_num ON pdf2_cards(card_num)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON pdf2_cards(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_formula ON pdf2_cards(formula)')
        
        # 读取整个文件（二进制模式）
        with open(self.txt_path, 'rb') as f:
            data = f.read()
        
        print("文件读取完成，开始查找卡片...")
        
        # 查找所有卡片起始位置
        card_starts = []
        for match in self.card_start_pattern.finditer(data):
            card_starts.append(match.start())
        
        print(f"找到 {len(card_starts)} 张卡片")
        
        # 解析每张卡片
        inserted = 0
        total_cards = len(card_starts)
        
        for i, start_pos in enumerate(card_starts):
            if i % 1000 == 0:
                print(f"处理进度: {i}/{total_cards} ({i/total_cards*100:.1f}%)")
            
            # 确定卡片结束位置（下一张卡片的开始或文件结束）
            end_pos = card_starts[i + 1] if i + 1 < len(card_starts) else len(data)
            
            # 提取卡片数据
            card_data = data[start_pos:end_pos]
            
            try:
                card_info = self.parse_single_card(card_data)
                if card_info:
                    self.save_card_to_db(cursor, card_info)
                    inserted += 1
                    
                    if inserted % 10000 == 0:
                        conn.commit()
                        print(f"已提交 {inserted} 张卡片")
                        
            except Exception as e:
                print(f"解析卡片 {i} 时出错: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        print(f"解析完成！成功插入 {inserted} 张卡片")
        print(f"数据库保存到: {self.db_path}")
        
        return inserted
    
    def parse_single_card(self, card_data: bytes) -> Optional[Dict]:
        """解析单张卡片数据"""
        try:
            # 尝试UTF-8解码
            card_text = card_data.decode('utf-8', errors='ignore')
        except:
            # 回退到latin-1
            card_text = card_data.decode('latin-1', errors='ignore')
        
        if not card_text.strip():
            return None
        
        # 提取卡片号
        card_match = re.match(r'^(M\d{9})', card_text)
        if not card_match:
            return None
        
        card_num_str = card_match.group(1)
        card_num = int(card_num_str[1:])  # 去掉开头的M
        
        result = {
            'card_num': card_num,
            'card_num_str': card_num_str,
            'raw_data': card_data[:5000],  # 保存前5000字节
        }
        
        # 解析字段 - 使用更灵活的方法
        self._parse_fields_flexible(card_text, result)
        
        return result
    
    def _parse_fields_flexible(self, card_text: str, result: Dict):
        """灵活解析字段"""
        
        # 1. 查找所有字段标记
        field_pattern = re.compile(r'P\d+X(\d+)([A-Z]?)')
        fields = []
        
        pos = 0
        while pos < len(card_text):
            match = field_pattern.search(card_text, pos)
            if not match:
                break
            
            field_num = match.group(1)
            field_suffix = match.group(2) or ''
            field_start = match.start()
            field_end = match.end()
            
            # 查找字段内容结束（下一个字段开始或字符串结束）
            next_match = field_pattern.search(card_text, field_end)
            content_end = next_match.start() if next_match else len(card_text)
            
            content = card_text[field_end:content_end].strip()
            
            fields.append((field_num, field_suffix, content))
            
            pos = content_end
        
        # 2. 处理关键字段
        for field_num, suffix, content in fields:
            field_key = f"x{field_num}{suffix.lower()}"
            
            if field_num == '1':
                # X1: 分子量等
                result['x1'] = content
            elif field_num == '4':
                # X4: 卡片类型 + CAS号
                result['x4'] = content
                # 提取卡片类型
                if 'O' in content:
                    result['card_type'] = 'Organic'
                elif 'I' in content:
                    result['card_type'] = 'Inorganic'
                elif 'M' in content:
                    result['card_type'] = 'Mineral'
                # 提取CAS号
                cas_match = re.search(r'(\d{2,7}-\d{2}-\d{1})', content)
                if cas_match:
                    result['cas'] = cas_match.group(1)
            elif field_num == '5':
                # X5: 化合物名称
                name = content
                # 清理特殊字符
                name = re.sub(r'\$[A-Z]', '', name)
                # 移除末尾的"P"和空格
                name = re.sub(r'\s+P\s*$', '', name)
                name = name.strip()
                result['name'] = name
            elif field_num == '6' or field_num == '7':
                # X6/X7: 化学式
                formula = content.strip()
                if formula and 'formula' not in result:
                    result['formula'] = formula
            elif field_num == '8':
                # X8: 参考文献
                result['reference'] = content
                # 提取年份
                year_match = re.search(r'(\d{4})', content)
                if year_match:
                    try:
                        result['year'] = int(year_match.group(1))
                    except:
                        pass
            elif field_num == '9':
                # X9: 实验条件
                result['x9'] = content
                # 提取辐射源
                radiation_match = re.search(r'(Cu|Mo|Co|Fe|Cr)K(a|α)', content, re.IGNORECASE)
                if radiation_match:
                    element = radiation_match.group(1).upper()
                    result['radiation'] = f"{element} Kα"
                # 提取波长
                wavelength_match = re.search(r'(\d+\.\d+)', content)
                if wavelength_match:
                    try:
                        result['wavelength'] = float(wavelength_match.group(1))
                    except:
                        pass
            elif field_num == 'I':
                # XI: 衍射峰数据
                if 'peaks_raw' not in result:
                    result['peaks_raw'] = []
                result['peaks_raw'].append(content)
        
        # 3. 处理峰数据
        if 'peaks_raw' in result:
            peaks = []
            for raw_peak in result['peaks_raw']:
                # 解析d值和强度对
                pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', raw_peak)
                for d_str, i_str in pairs:
                    try:
                        d = float(d_str)
                        i = int(i_str)
                        peaks.append((d, i))
                    except ValueError:
                        continue
            
            if peaks:
                # 按强度排序
                peaks.sort(key=lambda x: x[1], reverse=True)
                result['peaks'] = peaks
                result['peaks_json'] = json.dumps(peaks)
            
            # 清理临时字段
            del result['peaks_raw']
    
    def save_card_to_db(self, cursor, card_info: Dict):
        """保存卡片信息到数据库"""
        cursor.execute('''
        INSERT OR REPLACE INTO pdf2_cards 
        (card_num, card_num_str, name, formula, cas, card_type, 
         radiation, wavelength, reference, year, peaks_json, raw_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card_info.get('card_num'),
            card_info.get('card_num_str', ''),
            card_info.get('name', ''),
            card_info.get('formula', ''),
            card_info.get('cas', ''),
            card_info.get('card_type', ''),
            card_info.get('radiation', ''),
            card_info.get('wavelength'),
            card_info.get('reference', ''),
            card_info.get('year'),
            card_info.get('peaks_json', ''),
            card_info.get('raw_data', b'')
        ))

def test_parsing():
    """测试解析"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    parser = PDF2BinaryParser(txt_path, ":memory:")
    
    # 读取前100KB数据
    with open(txt_path, 'rb') as f:
        data = f.read(100 * 1024)  # 100KB
    
    print(f"读取了 {len(data)} 字节")
    
    # 查找卡片
    card_starts = []
    for match in parser.card_start_pattern.finditer(data):
        card_starts.append(match.start())
    
    print(f"找到 {len(card_starts)} 张卡片")
    
    # 解析前3张卡片
    for i in range(min(3, len(card_starts))):
        start_pos = card_starts[i]
        end_pos = card_starts[i + 1] if i + 1 < len(card_starts) else len(data)
        
        card_data = data[start_pos:end_pos]
        card_info = parser.parse_single_card(card_data)
        
        if card_info:
            print(f"\n{'='*60}")
            print(f"卡片 #{i+1}")
            print(f"{'='*60}")
            print(f"卡片号: {card_info.get('card_num_str')}")
            print(f"名称: {card_info.get('name')}")
            print(f"化学式: {card_info.get('formula')}")
            print(f"CAS号: {card_info.get('cas')}")
            print(f"类型: {card_info.get('card_type')}")
            print(f"辐射源: {card_info.get('radiation')}")
            print(f"波长: {card_info.get('wavelength')}")
            
            peaks = card_info.get('peaks', [])
            if peaks:
                print(f"峰数量: {len(peaks)}")
                print(f"最强峰 (前3个):")
                for d, i in peaks[:3]:
                    print(f"  d={d:.3f} Å, I={i}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python pdf2_parser_correct.py <pdf2.txt文件路径> [数据库路径]")
        print("示例: python pdf2_parser_correct.py F:\\桌面\\pdf2.txt")
        print("\n测试模式: python pdf2_parser_correct.py --test")
        return
    
    if sys.argv[1] == '--test':
        test_parsing()
        return
    
    txt_path = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    parser = PDF2BinaryParser(txt_path, db_path)
    parser.parse_binary_file()

if __name__ == '__main__':
    main()