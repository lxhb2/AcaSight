#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 数据库解析器
将588MB的pdf2.txt文件解析为SQLite数据库
"""

import re
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

class PDF2Parser:
    """PDF2-2004 数据库解析器"""
    
    def __init__(self, txt_path: str, db_path: str = None):
        self.txt_path = Path(txt_path)
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.txt_path.parent / "pdf2_full.db"
        
        # 字段位置映射（基于样本分析）
        self.field_positions = {
            'card_num': (0, 9),      # M000010001
            'type_marker': (11, 12), # P
            'x1': (15, 80),          # 分子量等
            'x4': (80, 160),         # 卡片类型 + CAS号
            'x5': (160, 240),        # 化合物名称
            'x6': (240, 320),        # 化学式1
            'x7': (320, 400),        # 化学式2
            'x8': (400, 480),        # 参考文献
            'x9': (480, 560),        # 实验条件
            'xf': (560, 640),        # 补充信息
            'xg': (640, 720),        # 2θ范围
        }
        
        # 正则表达式模式
        self.card_start_pattern = re.compile(r'^M\d{9}')
        self.field_pattern = re.compile(r'P\d+X(\d+)([A-Z]?)')
        
    def parse_card(self, card_text: str) -> Optional[Dict]:
        """解析单个卡片"""
        if not card_text.strip():
            return None
            
        lines = card_text.strip().split('\n')
        if not lines:
            return None
            
        # 提取卡片号
        first_line = lines[0]
        card_match = self.card_start_pattern.match(first_line)
        if not card_match:
            return None
            
        card_num = card_match.group()
        card_num_int = int(card_num[1:])  # 去掉开头的M
        
        result = {
            'card_num': card_num_int,
            'raw_text': card_text,
        }
        
        # 解析字段
        for line in lines:
            # 查找字段标记
            field_matches = list(self.field_pattern.finditer(line))
            if not field_matches:
                continue
                
            for match in field_matches:
                field_type = match.group(1)  # X后面的数字
                field_suffix = match.group(2) or ''  # 可能的字母后缀
                field_key = f'x{field_type}{field_suffix.lower()}'
                
                # 提取字段内容（从字段标记结束到下一个字段标记开始）
                start_pos = match.end()
                next_match = None
                for m2 in field_matches:
                    if m2.start() > match.start():
                        next_match = m2
                        break
                
                if next_match:
                    end_pos = next_match.start()
                else:
                    end_pos = len(line)
                
                field_content = line[start_pos:end_pos].strip()
                if field_content:
                    result[field_key] = field_content
        
        # 提取关键信息
        self._extract_key_info(result)
        
        return result
    
    def _extract_key_info(self, card: Dict):
        """从原始字段中提取结构化信息"""
        
        # 1. 提取化合物名称 (x5)
        if 'x5' in card:
            name = card['x5']
            # 清理特殊字符
            name = name.replace('$G', '').replace('$A', '').replace('$B', '')
            name = name.replace('$', '').strip()
            card['name'] = name
        
        # 2. 提取化学式 (x6或x7)
        formula = card.get('x6') or card.get('x7') or ''
        formula = formula.strip()
        if formula:
            # 清理化学式中的空格和特殊字符
            formula = re.sub(r'\s+', ' ', formula)
            card['formula'] = formula
        
        # 3. 提取CAS号 (从x4字段)
        if 'x4' in card:
            x4 = card['x4']
            # CAS号通常是数字-数字-数字格式
            cas_match = re.search(r'(\d{2,7}-\d{2}-\d{1})', x4)
            if cas_match:
                card['cas'] = cas_match.group(1)
        
        # 4. 提取辐射源和波长 (x9字段)
        if 'x9' in card:
            x9 = card['x9']
            # 常见辐射源: CuKa1, MoKa1, CoKa等
            radiation_match = re.search(r'(Cu|Mo|Co|Fe|Cr)K(a|α)(\d?)', x9, re.IGNORECASE)
            if radiation_match:
                element = radiation_match.group(1).upper()
                card['radiation'] = f"{element} Kα"
            
            # 提取波长
            wavelength_match = re.search(r'(\d+\.\d+)', x9)
            if wavelength_match:
                card['wavelength'] = float(wavelength_match.group(1))
        
        # 5. 提取衍射峰数据 (XI字段)
        peaks = []
        for key in card:
            if key.startswith('xi'):
                # XI字段格式: "3.22000  3             3.15000  3"
                xi_content = card[key]
                # 解析d值和强度对
                pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', xi_content)
                for d_str, i_str in pairs:
                    try:
                        d = float(d_str)
                        i = int(i_str)
                        peaks.append((d, i))
                    except ValueError:
                        continue
        
        if peaks:
            card['peaks'] = peaks
            # 计算2θ范围（如果xg字段存在）
            if 'xg' in card:
                xg = card['xg']
                tth_matches = re.findall(r'(\d+\.\d+)', xg)
                if len(tth_matches) >= 2:
                    try:
                        card['tth_min'] = float(tth_matches[0])
                        card['tth_max'] = float(tth_matches[1])
                    except ValueError:
                        pass
    
    def parse_file(self, batch_size: int = 1000) -> int:
        """解析整个文件并存入数据库"""
        
        print(f"开始解析 {self.txt_path}...")
        print(f"文件大小: {self.txt_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        # 创建数据库
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建表
        # 创建表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_cards (
            card_num INTEGER PRIMARY KEY,
            name TEXT,
            formula TEXT,
            cas TEXT,
            radiation TEXT,
            wavelength REAL,
            tth_min REAL,
            tth_max REAL,
            peaks_json TEXT,
            raw_text TEXT
        )
        ''')
        
        # 分别创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON pdf2_cards(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_formula ON pdf2_cards(formula)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cas ON pdf2_cards(cas)')
        
        # 读取文件
        with open(self.txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        print("文件读取完成，开始分割卡片...")
        
        # 分割卡片（以M开头+9位数字）
        card_texts = re.split(r'(?=M\d{9})', content)
        total_cards = len(card_texts) - 1  # 第一个可能是空字符串
        
        print(f"找到 {total_cards} 张卡片")
        
        # 解析并插入
        inserted = 0
        for i, card_text in enumerate(card_texts[1:], 1):  # 跳过第一个空字符串
            if i % 1000 == 0:
                print(f"处理进度: {i}/{total_cards} ({i/total_cards*100:.1f}%)")
            
            try:
                card = self.parse_card(card_text)
                if card:
                    # 准备插入数据
                    peaks_json = json.dumps(card.get('peaks', []))
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO pdf2_cards 
                    (card_num, name, formula, cas, radiation, wavelength, 
                     tth_min, tth_max, peaks_json, raw_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        card.get('card_num'),
                        card.get('name', ''),
                        card.get('formula', ''),
                        card.get('cas', ''),
                        card.get('radiation', ''),
                        card.get('wavelength'),
                        card.get('tth_min'),
                        card.get('tth_max'),
                        peaks_json,
                        card.get('raw_text', '')[:10000]  # 限制长度
                    ))
                    
                    inserted += 1
                    
                    # 批量提交
                    if inserted % batch_size == 0:
                        conn.commit()
                        
            except Exception as e:
                print(f"解析卡片 {i} 时出错: {e}")
                continue
        
        # 最终提交
        conn.commit()
        conn.close()
        
        print(f"解析完成！成功插入 {inserted} 张卡片")
        print(f"数据库保存到: {self.db_path}")
        
        return inserted

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python parse_pdf2.py <pdf2.txt文件路径> [数据库路径]")
        print("示例: python parse_pdf2.py F:\\桌面\\pdf2.txt")
        return
    
    txt_path = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    parser = PDF2Parser(txt_path, db_path)
    parser.parse_file()

if __name__ == '__main__':
    main()