#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF2-2004 最终解析器 - 支持大文件分块处理
"""

import re
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Generator
import sys
import time

class PDF2FinalParser:
    """PDF2-2004 最终解析器"""
    
    def __init__(self, txt_path: str, db_path: str = None):
        self.txt_path = Path(txt_path)
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = self.txt_path.parent / "pdf2_final.db"
        
        # 编译正则表达式（修复转义警告）
        self.card_start_pattern = re.compile(b'M\\d{9}')
        
    def setup_database(self):
        """设置数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建主表
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
            raw_data BLOB,
            n_peaks INTEGER,
            d_min REAL,
            d_max REAL,
            i_max INTEGER
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_card_num ON pdf2_cards(card_num)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON pdf2_cards(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_formula ON pdf2_cards(formula)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cas ON pdf2_cards(cas)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_type ON pdf2_cards(card_type)')
        
        # 创建峰数据表（用于快速搜索）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pdf2_peaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_num INTEGER,
            d_value REAL,
            intensity INTEGER,
            FOREIGN KEY (card_num) REFERENCES pdf2_cards(card_num)
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_peak_d ON pdf2_peaks(d_value)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_peak_card ON pdf2_peaks(card_num)')
        
        conn.commit()
        conn.close()
        
        print(f"数据库已设置: {self.db_path}")
    
    def parse_file_chunked(self, chunk_size_mb: int = 100):
        """分块解析大文件"""
        print(f"开始解析 {self.txt_path}...")
        file_size = self.txt_path.stat().st_size
        file_size_mb = file_size / 1024 / 1024
        print(f"文件大小: {file_size_mb:.1f} MB")
        
        self.setup_database()
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        chunk_size = chunk_size_mb * 1024 * 1024
        buffer = b""
        total_cards = 0
        start_time = time.time()
        
        with open(self.txt_path, 'rb') as f:
            while True:
                # 读取块
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                position = f.tell()
                buffer += chunk
                
                print(f"读取进度: {position / 1024 / 1024:.1f} MB / {file_size_mb:.1f} MB")
                
                # 查找卡片边界
                card_positions = []
                for match in self.card_start_pattern.finditer(buffer):
                    card_positions.append(match.start())
                
                # 处理完整的卡片（除了最后一个）
                for i in range(len(card_positions) - 1):
                    start_pos = card_positions[i]
                    end_pos = card_positions[i + 1]
                    card_data = buffer[start_pos:end_pos]
                    
                    try:
                        card_info = self.parse_card_data(card_data)
                        if card_info:
                            self.save_card(cursor, card_info)
                            total_cards += 1
                            
                            if total_cards % 10000 == 0:
                                conn.commit()
                                elapsed = time.time() - start_time
                                rate = total_cards / elapsed if elapsed > 0 else 0
                                print(f"已处理: {total_cards} 张卡片, 速率: {rate:.1f} 卡片/秒")
                                
                    except Exception as e:
                        # 静默错误，继续处理
                        continue
                
                # 保留最后一张不完整的卡片到下一个缓冲区
                if card_positions:
                    buffer = buffer[card_positions[-1]:]
                else:
                    buffer = b""
        
        # 处理最后一张卡片
        if buffer.strip():
            try:
                card_info = self.parse_card_data(buffer)
                if card_info:
                    self.save_card(cursor, card_info)
                    total_cards += 1
            except Exception as e:
                print(f"处理最后一张卡片时出错: {e}")
        
        conn.commit()
        conn.close()
        
        elapsed = time.time() - start_time
        print(f"\n解析完成！")
        print(f"总卡片数: {total_cards}")
        print(f"总耗时: {elapsed:.1f} 秒")
        print(f"平均速率: {total_cards/elapsed:.1f} 卡片/秒")
        print(f"数据库保存到: {self.db_path}")
        
        return total_cards
    
    def parse_card_data(self, card_data: bytes) -> Optional[Dict]:
        """解析卡片数据"""
        try:
            # 解码为文本
            card_text = card_data.decode('utf-8', errors='ignore')
        except:
            card_text = card_data.decode('latin-1', errors='ignore')
        
        if not card_text.strip():
            return None
        
        # 提取卡片号
        card_match = re.match(r'^(M\d{9})', card_text)
        if not card_match:
            return None
        
        card_num_str = card_match.group(1)
        card_num = int(card_num_str[1:])
        
        result = {
            'card_num': card_num,
            'card_num_str': card_num_str,
            'raw_data': card_data[:2000],  # 保存前2000字节
        }
        
        # 解析字段
        self._parse_card_fields(card_text, result)
        
        return result
    
    def _parse_card_fields(self, card_text: str, result: Dict):
        """解析卡片字段"""
        
        # 查找所有字段
        # 注意：X后面的可能是数字或罗马数字I
        field_pattern = re.compile(r'P\d+X(\d+|I)([A-Z]?)')
        fields = []
        
        pos = 0
        while pos < len(card_text):
            match = field_pattern.search(card_text, pos)
            if not match:
                break
            
            field_num = match.group(1)  # 可能是'1', '2', ... 或'I'
            field_suffix = match.group(2) or ''
            field_start = match.start()
            field_end = match.end()
            
            # 查找字段内容结束
            next_match = field_pattern.search(card_text, field_end)
            content_end = next_match.start() if next_match else len(card_text)
            
            content = card_text[field_end:content_end].strip()
            
            fields.append((field_num, field_suffix, content))
            pos = content_end
        
        # 处理字段
        for field_num, suffix, content in fields:
            if field_num == '1':
                result['x1'] = content
            elif field_num == '4':
                result['x4'] = content
                # 卡片类型
                if 'O' in content:
                    result['card_type'] = 'Organic'
                elif 'I' in content:
                    result['card_type'] = 'Inorganic'
                elif 'M' in content:
                    result['card_type'] = 'Mineral'
                else:
                    result['card_type'] = 'Unknown'
                # CAS号
                cas_match = re.search(r'(\d{2,7}-\d{2}-\d{1})', content)
                if cas_match:
                    result['cas'] = cas_match.group(1)
            elif field_num == '5':
                # 化合物名称
                name = content
                # 清理特殊字符
                name = re.sub(r'\$[A-Z]', '', name)
                # 移除末尾标记
                name = re.sub(r'\s+P\s*$', '', name)
                name = name.strip()
                result['name'] = name
            elif field_num == '6':
                result['formula'] = content.strip()
            elif field_num == '7' and 'formula' not in result:
                result['formula'] = content.strip()
            elif field_num == '8':
                result['reference'] = content
                # 提取年份
                year_match = re.search(r'(\d{4})', content)
                if year_match:
                    try:
                        result['year'] = int(year_match.group(1))
                    except:
                        pass
            elif field_num == '9':
                result['x9'] = content
                # 辐射源
                radiation_match = re.search(r'(Cu|Mo|Co|Fe|Cr)K(a|α|A)', content, re.IGNORECASE)
                if radiation_match:
                    element = radiation_match.group(1).upper()
                    result['radiation'] = f"{element} Kα"
                # 波长
                wavelength_match = re.search(r'(\d+\.\d+)', content)
                if wavelength_match:
                    try:
                        result['wavelength'] = float(wavelength_match.group(1))
                    except:
                        pass
            elif field_num == 'I':
                # 峰数据
                if 'peaks_raw' not in result:
                    result['peaks_raw'] = []
                result['peaks_raw'].append(content)
        
        # 处理峰数据
        if 'peaks_raw' in result:
            peaks = []
            for raw_peak in result['peaks_raw']:
                # 解析d值和强度
                pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', raw_peak)
                for d_str, i_str in pairs:
                    try:
                        d = float(d_str)
                        i = int(i_str)
                        peaks.append((d, i))
                    except:
                        continue
            
            if peaks:
                # 按强度排序
                peaks.sort(key=lambda x: x[1], reverse=True)
                result['peaks'] = peaks
                result['peaks_json'] = json.dumps(peaks)
                result['n_peaks'] = len(peaks)
                
                # 计算统计信息
                d_values = [p[0] for p in peaks]
                i_values = [p[1] for p in peaks]
                result['d_min'] = min(d_values) if d_values else 0
                result['d_max'] = max(d_values) if d_values else 0
                result['i_max'] = max(i_values) if i_values else 0
            
            del result['peaks_raw']
    
    def save_card(self, cursor, card_info: Dict):
        """保存卡片到数据库"""
        # 插入主表
        cursor.execute('''
        INSERT OR REPLACE INTO pdf2_cards 
        (card_num, card_num_str, name, formula, cas, card_type, 
         radiation, wavelength, reference, year, peaks_json, raw_data,
         n_peaks, d_min, d_max, i_max)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            card_info.get('raw_data', b''),
            card_info.get('n_peaks', 0),
            card_info.get('d_min', 0),
            card_info.get('d_max', 0),
            card_info.get('i_max', 0)
        ))
        
        # 插入峰数据表
        peaks = card_info.get('peaks', [])
        card_num = card_info.get('card_num')
        
        for d, i in peaks:
            cursor.execute('''
            INSERT INTO pdf2_peaks (card_num, d_value, intensity)
            VALUES (?, ?, ?)
            ''', (card_num, d, i))

def test_sample():
    """测试样本解析"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    parser = PDF2FinalParser(txt_path, ":memory:")
    
    # 读取前200KB
    with open(txt_path, 'rb') as f:
        data = f.read(200 * 1024)
    
    print(f"读取了 {len(data)} 字节")
    
    # 查找卡片
    card_positions = []
    for match in parser.card_start_pattern.finditer(data):
        card_positions.append(match.start())
    
    print(f"找到 {len(card_positions)} 张卡片")
    
    # 解析前5张
    for i in range(min(5, len(card_positions))):
        start_pos = card_positions[i]
        end_pos = card_positions[i + 1] if i + 1 < len(card_positions) else len(data)
        
        card_data = data[start_pos:end_pos]
        card_info = parser.parse_card_data(card_data)
        
        if card_info:
            print(f"\n{'='*60}")
            print(f"卡片 #{i+1}: {card_info.get('card_num_str')}")
            print(f"{'='*60}")
            print(f"名称: {card_info.get('name')}")
            print(f"化学式: {card_info.get('formula')}")
            print(f"CAS号: {card_info.get('cas')}")
            print(f"类型: {card_info.get('card_type')}")
            print(f"辐射源: {card_info.get('radiation')}")
            print(f"波长: {card_info.get('wavelength')}")
            print(f"参考文献: {card_info.get('reference', '')[:50]}...")
            print(f"年份: {card_info.get('year')}")
            
            peaks = card_info.get('peaks', [])
            if peaks:
                print(f"峰数量: {len(peaks)}")
                print(f"最强峰 (前5个):")
                for j, (d, i) in enumerate(peaks[:5], 1):
                    print(f"  {j}. d={d:.3f} Å, I={i}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("PDF2-2004 数据库解析器")
        print("=" * 60)
        print("用法: python pdf2_parser_final.py <命令> [参数]")
        print()
        print("命令:")
        print("  --test          测试解析前几张卡片")
        print("  --parse <文件>  解析完整文件")
        print("  --db <路径>     指定数据库路径")
        print()
        print("示例:")
        print("  python pdf2_parser_final.py --test")
        print("  python pdf2_parser_final.py --parse F:\\桌面\\pdf2.txt")
        print("  python pdf2_parser_final.py --parse F:\\桌面\\pdf2.txt --db F:\\桌面\\pdf2.db")
        return
    
    if sys.argv[1] == '--test':
        test_sample()
        return
    
    if sys.argv[1] == '--parse' and len(sys.argv) >= 3:
        txt_path = sys.argv[2]
        db_path = None
        
        if '--db' in sys.argv:
            db_idx = sys.argv.index('--db')
            if db_idx + 1 < len(sys.argv):
                db_path = sys.argv[db_idx + 1]
        
        print("开始解析PDF2-2004数据库...")
        print(f"输入文件: {txt_path}")
        if db_path:
            print(f"输出数据库: {db_path}")
        
        parser = PDF2FinalParser(txt_path, db_path)
        parser.parse_file_chunked(chunk_size_mb=200)  # 200MB块
        
        return
    
    print("错误: 未知命令")
    main()

if __name__ == '__main__':
    main()