#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的解析器
"""

import re
import json
from pathlib import Path

def test_fixed_parser():
    """测试修复后的解析器"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    # 读取第一张卡片
    with open(txt_path, 'rb') as f:
        data = f.read(5000)
    
    # 查找第一张卡片
    card_start = data.find(b'M000010001')
    if card_start == -1:
        print("未找到卡片")
        return
    
    # 查找卡片结束
    card_end = data.find(b'M000010002', card_start)
    if card_end == -1:
        card_data = data[card_start:]
    else:
        card_data = data[card_start:card_end]
    
    # 解码
    try:
        card_text = card_data.decode('utf-8')
    except:
        card_text = card_data.decode('latin-1')
    
    print("测试修复后的字段解析...")
    
    # 使用修复后的正则表达式
    field_pattern = re.compile(r'P\d+X(\d+|I)([A-Z]?)')
    fields = []
    
    pos = 0
    while pos < len(card_text):
        match = field_pattern.search(card_text, pos)
        if not match:
            break
        
        field_num = match.group(1)
        field_suffix = match.group(2) or ''
        field_end = match.end()
        
        # 查找字段内容结束
        next_match = field_pattern.search(card_text, field_end)
        content_end = next_match.start() if next_match else len(card_text)
        
        content = card_text[field_end:content_end].strip()
        
        fields.append((field_num, field_suffix, content))
        pos = content_end
    
    print(f"找到 {len(fields)} 个字段")
    
    # 显示字段类型
    field_types = {}
    for field_num, suffix, content in fields:
        key = f"X{field_num}{suffix}"
        if key not in field_types:
            field_types[key] = 0
        field_types[key] += 1
    
    print("字段类型统计:")
    for field_type, count in sorted(field_types.items()):
        print(f"  {field_type}: {count}个")
    
    # 特别检查XI字段
    print("\nXI字段详情:")
    xi_fields = [(suffix, content) for field_num, suffix, content in fields if field_num == 'I']
    
    for i, (suffix, content) in enumerate(xi_fields):
        print(f"\nXI字段 #{i+1} (后缀: '{suffix}'):")
        
        # 解析d值和强度
        number_pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', content)
        print(f"  找到 {len(number_pairs)} 个峰")
        
        if number_pairs:
            print(f"  前5个峰:")
            for j, (d_str, i_str) in enumerate(number_pairs[:5]):
                print(f"    {j+1}. d={d_str} A, I={i_str}")
    
    # 测试峰数据提取函数
    print("\n" + "="*60)
    print("测试完整的峰数据提取:")
    
    peaks = []
    for field_num, suffix, content in fields:
        if field_num == 'I' and not suffix:  # 只处理XI，不处理XIO等
            # 解析d值和强度对
            pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', content)
            for d_str, i_str in pairs:
                try:
                    d = float(d_str)
                    i = int(i_str)
                    peaks.append((d, i))
                except ValueError:
                    continue
    
    if peaks:
        print(f"提取到 {len(peaks)} 个峰")
        peaks.sort(key=lambda x: x[1], reverse=True)
        print("按强度排序的前10个峰:")
        for i, (d, intensity) in enumerate(peaks[:10], 1):
            print(f"  {i}. d={d:.3f} A, I={intensity}")
        
        # 统计信息
        d_values = [p[0] for p in peaks]
        i_values = [p[1] for p in peaks]
        print(f"\n统计信息:")
        print(f"  d值范围: {min(d_values):.3f} - {max(d_values):.3f} A")
        print(f"  平均强度: {sum(i_values)/len(i_values):.1f}")
        print(f"  最大强度: {max(i_values)}")
    else:
        print("未提取到峰数据")

if __name__ == '__main__':
    test_fixed_parser()