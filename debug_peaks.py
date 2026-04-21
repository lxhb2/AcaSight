#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试峰数据提取
"""

import re
from pathlib import Path

def debug_peak_extraction():
    """调试峰数据提取"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    # 读取第一张卡片
    with open(txt_path, 'rb') as f:
        # 查找第一张卡片
        data = f.read(5000)
    
    # 查找卡片开始
    card_start = data.find(b'M000010001')
    if card_start == -1:
        print("未找到卡片")
        return
    
    # 查找卡片结束（下一张卡片开始）
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
    
    print("卡片文本 (前500字符):")
    print(card_text[:500])
    print("\n" + "="*60)
    
    # 查找XI字段
    print("查找XI字段...")
    
    # 方法1: 使用正则表达式查找所有XI字段
    xi_pattern = re.compile(r'P\d+X(I)([A-Z]?)\s*(.*?)(?=P\d+X|$)', re.DOTALL)
    xi_matches = xi_pattern.findall(card_text)
    
    print(f"找到 {len(xi_matches)} 个XI字段")
    
    for i, (field_num, suffix, content) in enumerate(xi_matches):
        print(f"\nXI字段 #{i+1} (后缀: '{suffix}'):")
        print(f"内容长度: {len(content)} 字符")
        print(f"内容前100字符: {repr(content[:100])}")
        
        # 尝试解析d值和强度
        # XI字段格式通常是: "3.22000  3             3.15000  3"
        # 数字对: 浮点数 + 空格 + 整数
        
        # 方法1: 简单的空格分割
        parts = content.strip().split()
        print(f"分割部分: {len(parts)} 个")
        if len(parts) >= 2:
            print(f"前几个部分: {parts[:10]}")
        
        # 方法2: 正则表达式匹配数字对
        number_pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', content)
        print(f"找到的数字对: {len(number_pairs)} 个")
        if number_pairs:
            print(f"前5个数字对:")
            for j, (d_str, i_str) in enumerate(number_pairs[:5]):
                print(f"  {j+1}. d={d_str}, I={i_str}")
    
    print("\n" + "="*60)
    print("完整卡片文本分析:")
    
    # 显示卡片中所有字段
    all_fields = re.findall(r'P\d+X(\d+)([A-Z]?)\s*(.*?)(?=P\d+X|$)', card_text, re.DOTALL)
    print(f"总共找到 {len(all_fields)} 个字段")
    
    field_types = {}
    for field_num, suffix, content in all_fields:
        key = f"X{field_num}{suffix}"
        if key not in field_types:
            field_types[key] = 0
        field_types[key] += 1
    
    print("字段类型统计:")
    for field_type, count in sorted(field_types.items()):
        print(f"  {field_type}: {count}个")

if __name__ == '__main__':
    debug_peak_extraction()