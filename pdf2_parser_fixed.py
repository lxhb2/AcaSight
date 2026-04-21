#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 固定宽度格式解析器
基于实际文件分析的正确解析器
"""

import re
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import sys

class PDF2FixedWidthParser:
    """PDF2-2004 固定宽度格式解析器"""
    
    def __init__(self, txt_path: str, db_path: str = None):
        self.txt_path = Path(txt_path)
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.txt_path.parent / "pdf2_complete.db"
        
        # 基于实际文件分析的关键位置
        # 每张卡片似乎是80字符宽的多行
        self.card_width = 80
        
    def parse_fixed_width(self, lines: List[str]) -> Dict:
        """解析固定宽度格式的卡片"""
        if not lines:
            return {}
            
        result = {}
        
        # 第一行包含卡片号
        first_line = lines[0].rstrip()
        if first_line.startswith('M') and len(first_line) >= 9:
            card_num_str = first_line[:9]
            try:
                result['card_num'] = int(card_num_str[1:])  # 去掉M
            except:
                result['card_num'] = 0
        
        # 解析所有行
        for line in lines:
            line = line.rstrip()
            if len(line) < 10:
                continue
                
            # 查找字段标记 (如 P010001X1, P010001X4, 等)
            # 字段标记在固定位置
            if len(line) >= 15 and line[10:11] == 'P':
                # 提取字段标记 (位置10-18)
                field_mark = line[10:18].strip()
                if field_mark:
                    # 提取内容 (位置18-80)
                    content = line[18:].strip()
                    result[field_mark] = content
        
        return result
    
    def extract_structured_info(self, raw_card: Dict) -> Dict:
        """从原始字段提取结构化信息"""
        card = raw_card.copy()
        
        # 1. 化合物名称 (X5字段)
        x5 = card.get('P010001X5', '')
        if x5:
            # 清理特殊字符
            name = x5
            # 移除$G, $A, $B等特殊标记
            name = re.sub(r'\$[A-Z]', '', name)
            # 移除末尾的"P"标记
            name = name.rstrip(' P')
            card['name'] = name.strip()
        
        # 2. 化学式 (X6或X7字段)
        formula = card.get('P010001X6', '') or card.get('P010001X7', '')
        if formula:
            # 清理化学式
            formula = formula.strip()
            # 移除可能的字段标记后缀
            formula = re.sub(r'^[A-Z]\d+\s+', '', formula)
            card['formula'] = formula
        
        # 3. CAS号 (X4字段)
        x4 = card.get('P010001X4', '')
        if x4:
            # 查找CAS号模式
            cas_match = re.search(r'(\d{2,7}-\d{2}-\d{1})', x4)
            if cas_match:
                card['cas'] = cas_match.group(1)
            # 检查卡片类型
            if 'O' in x4:
                card['type'] = 'Organic'
            elif 'I' in x4:
                card['type'] = 'Inorganic'
            elif 'M' in x4:
                card['type'] = 'Mineral'
        
        # 4. 实验条件 (X9字段)
        x9 = card.get('P010001X9', '')
        if x9:
            # 提取辐射源
            radiation_match = re.search(r'(Cu|Mo|Co|Fe|Cr)K(a|α)', x9, re.IGNORECASE)
            if radiation_match:
                element = radiation_match.group(1).upper()
                card['radiation'] = f"{element} Kα"
            
            # 提取波长
            wavelength_match = re.search(r'(\d+\.\d+)', x9)
            if wavelength_match:
                card['wavelength'] = float(wavelength_match.group(1))
        
        # 5. 衍射峰数据 (查找所有XI字段)
        peaks = []
        for key, value in card.items():
            if 'XI' in key and value:
                # XI字段格式: "3.22000  3             3.15000  3"
                # 解析d值和强度对
                pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', value)
                for d_str, i_str in pairs:
                    try:
                        d = float(d_str)
                        i = int(i_str)
                        peaks.append((d, i))
                    except ValueError:
                        continue
        
        if peaks:
            card['peaks'] = peaks
            # 按强度排序
            peaks.sort(key=lambda x: x[1], reverse=True)
            card['sorted_peaks'] = peaks[:20]  # 保留前20个最强峰
        
        # 6. 参考文献 (X8字段)
        x8 = card.get('P010001X8', '')
        if x8:
            # 提取作者和年份
            author_match = re.search(r'([A-Za-z\s,\.]+)\s+(\d{4})', x8)
            if author_match:
                card['author'] = author_match.group(1).strip()
                card['year'] = int(author_match.group(2))
        
        return card
    
    def parse_file_chunked(self, chunk_size_mb: int = 50) -> int:
        """分块解析大文件"""
        print(f"开始解析 {self.txt_path}...")
        file_size_mb = self.txt_path.stat().st_size / 1024 / 1024
        print(f"文件大小: {file_size_mb:.1f} MB")
        
        # 创建数据库
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_cards (
            card_num INTEGER PRIMARY KEY,
            name TEXT,
            formula TEXT,
            cas TEXT,
            type TEXT,
            radiation TEXT,
            wavelength REAL,
            author TEXT,
            year INTEGER,
            peaks_json TEXT,
            sorted_peaks_json TEXT,
            raw_fields_json TEXT
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON pdf2_cards(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_formula ON pdf2_cards(formula)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cas ON pdf2_cards(cas)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON pdf2_cards(type)')
        
        inserted = 0
        chunk_size = chunk_size_mb * 1024 * 1024
        
        with open(self.txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            buffer = ""
            position = 0
            
            while True:
                # 读取块
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                buffer += chunk
                position += len(chunk)
                
                print(f"读取进度: {position / 1024 / 1024:.1f} MB / {file_size_mb:.1f} MB")
                
                # 分割卡片
                cards = self._split_cards(buffer)
                
                # 处理完整的卡片
                for card_text in cards[:-1]:  # 最后一张可能不完整
                    try:
                        card = self._parse_single_card(card_text)
                        if card and card.get('card_num'):
                            self._save_card(cursor, card)
                            inserted += 1
                            
                            if inserted % 1000 == 0:
                                print(f"已解析: {inserted} 张卡片")
                                conn.commit()
                    except Exception as e:
                        print(f"解析卡片时出错: {e}")
                        continue
                
                # 保留最后一张不完整的卡片到下一个缓冲区
                buffer = cards[-1] if cards else ""
        
        # 处理最后一张卡片
        if buffer.strip():
            try:
                card = self._parse_single_card(buffer)
                if card and card.get('card_num'):
                    self._save_card(cursor, card)
                    inserted += 1
            except Exception as e:
                print(f"解析最后一张卡片时出错: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"解析完成！成功插入 {inserted} 张卡片")
        print(f"数据库保存到: {self.db_path}")
        
        return inserted
    
    def _split_cards(self, text: str) -> List[str]:
        """按卡片边界分割文本"""
        # 卡片以"M"开头，后跟9位数字
        pattern = r'(?=M\d{9})'
        parts = re.split(pattern, text)
        return parts
    
    def _parse_single_card(self, card_text: str) -> Optional[Dict]:
        """解析单张卡片"""
        if not card_text.strip():
            return None
        
        lines = card_text.strip().split('\n')
        raw_card = self.parse_fixed_width(lines)
        
        if not raw_card:
            return None
        
        structured_card = self.extract_structured_info(raw_card)
        
        # 添加原始文本（限制长度）
        structured_card['raw_text_sample'] = card_text[:1000]
        
        return structured_card
    
    def _save_card(self, cursor, card: Dict):
        """保存卡片到数据库"""
        peaks_json = json.dumps(card.get('peaks', []))
        sorted_peaks_json = json.dumps(card.get('sorted_peaks', []))
        raw_fields_json = json.dumps({k: v for k, v in card.items() 
                                     if k.startswith('P0100')})
        
        cursor.execute('''
        INSERT OR REPLACE INTO pdf2_cards 
        (card_num, name, formula, cas, type, radiation, wavelength, 
         author, year, peaks_json, sorted_peaks_json, raw_fields_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            card.get('card_num'),
            card.get('name', ''),
            card.get('formula', ''),
            card.get('cas', ''),
            card.get('type', ''),
            card.get('radiation', ''),
            card.get('wavelength'),
            card.get('author', ''),
            card.get('year'),
            peaks_json,
            sorted_peaks_json,
            raw_fields_json
        ))

def test_small_sample():
    """测试解析小样本"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    # 读取前1MB数据
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        sample = f.read(1024 * 1024)  # 1MB
    
    parser = PDF2FixedWidthParser(txt_path, ":memory:")
    
    # 分割卡片
    cards = parser._split_cards(sample)
    print(f"在1MB样本中找到 {len(cards)} 张卡片")
    
    # 解析前3张
    for i, card_text in enumerate(cards[1:4], 1):  # 跳过第一个空字符串
        print(f"\n{'='*60}")
        print(f"解析卡片 #{i}")
        print(f"{'='*60}")
        
        card = parser._parse_single_card(card_text)
        if card:
            print(f"卡片号: {card.get('card_num')}")
            print(f"名称: {card.get('name')}")
            print(f"化学式: {card.get('formula')}")
            print(f"CAS号: {card.get('cas')}")
            print(f"类型: {card.get('type')}")
            print(f"辐射源: {card.get('radiation')}")
            print(f"波长: {card.get('wavelength')}")
            
            peaks = card.get('sorted_peaks', [])
            if peaks:
                print(f"最强峰 (前5个):")
                for d, i in peaks[:5]:
                    print(f"  d={d:.3f} Å, I={i}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python pdf2_parser_fixed.py <pdf2.txt文件路径> [数据库路径]")
        print("示例: python pdf2_parser_fixed.py F:\\桌面\\pdf2.txt F:\\桌面\\pdf2_full.db")
        print("\n测试模式: python pdf2_parser_fixed.py --test")
        return
    
    if sys.argv[1] == '--test':
        test_small_sample()
        return
    
    txt_path = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    parser = PDF2FixedWidthParser(txt_path, db_path)
    parser.parse_file_chunked(chunk_size_mb=100)  # 100MB块

if __name__ == '__main__':
    main()