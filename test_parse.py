#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试PDF2解析器
"""

import re
import json
from pathlib import Path

def test_parse_first_cards():
    """测试解析前几张卡片"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    # 读取前100KB数据
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        # 读取足够的数据以包含多张卡片
        chunk_size = 200000  # 200KB
        data = f.read(chunk_size)
    
    print(f"读取了 {len(data)} 字符")
    
    # 分割卡片
    card_pattern = re.compile(r'(M\d{9}.*?)(?=M\d{9}|$)')
    cards = card_pattern.findall(data, re.DOTALL)
    
    print(f"找到 {len(cards)} 张卡片")
    
    # 解析前5张卡片
    for i, card_text in enumerate(cards[:5]):
        print(f"\n{'='*60}")
        print(f"卡片 #{i+1}")
        print(f"{'='*60}")
        
        # 提取卡片号
        card_match = re.match(r'^(M\d{9})', card_text)
        if card_match:
            print(f"卡片号: {card_match.group(1)}")
        
        # 提取字段
        field_pattern = re.compile(r'P\d+X(\d+)([A-Z]?)\s*(.*?)(?=P\d+X|$)')
        fields = field_pattern.findall(card_text)
        
        for field_num, suffix, content in fields[:10]:  # 只显示前10个字段
            field_key = f"X{field_num}{suffix}"
            content_trimmed = content.strip()[:80]
            if content_trimmed:
                print(f"{field_key:8}: {content_trimmed}")
        
        # 特别关注XI字段（峰数据）
        xi_fields = [(f"X{num}{suffix}", cont) for num, suffix, cont in fields 
                    if num == 'I' and cont.strip()]
        
        if xi_fields:
            print(f"\n峰数据字段 ({len(xi_fields)}个):")
            for field_key, content in xi_fields:
                # 解析d值和强度
                pairs = re.findall(r'(\d+\.\d+)\s+(\d+)', content)
                if pairs:
                    d_values = [float(p[0]) for p in pairs[:5]]  # 前5个d值
                    i_values = [int(p[1]) for p in pairs[:5]]    # 前5个强度
                    print(f"  {field_key}: d={d_values}, I={i_values}")
        
        # 查找化合物名称 (X5字段)
        x5_fields = [cont for num, suffix, cont in fields if num == '5' and cont.strip()]
        if x5_fields:
            name = x5_fields[0].strip()
            # 清理特殊字符
            name = re.sub(r'\$[A-Z]', '', name)
            print(f"\n化合物名称: {name}")
        
        # 查找化学式 (X6/X7字段)
        formula_fields = [cont for num, suffix, cont in fields 
                         if num in ['6', '7'] and cont.strip()]
        if formula_fields:
            formula = formula_fields[0].strip()
            print(f"化学式: {formula}")
        
        # 查找CAS号 (可能在X4字段)
        x4_fields = [cont for num, suffix, cont in fields if num == '4' and cont.strip()]
        if x4_fields:
            x4_content = x4_fields[0]
            # 查找CAS号模式
            cas_match = re.search(r'(\d{2,7}-\d{2}-\d{1})', x4_content)
            if cas_match:
                print(f"CAS号: {cas_match.group(1)}")
        
        print(f"卡片长度: {len(card_text)} 字符")

def analyze_file_structure():
    """分析文件结构"""
    txt_path = Path(r"F:\桌面\pdf2.txt")
    
    # 读取文件开头
    with open(txt_path, 'rb') as f:
        # 读取前5000字节
        data = f.read(5000)
    
    # 尝试不同编码
    try:
        text = data.decode('utf-8')
        print("编码: UTF-8")
    except UnicodeDecodeError:
        try:
            text = data.decode('latin-1')
            print("编码: Latin-1")
        except:
            text = data.decode('cp1252')
            print("编码: CP1252")
    
    print(f"\n文件开头 (前500字符):")
    print(text[:500])
    
    # 分析换行符
    lines = text.split('\n')
    print(f"\n行数: {len(lines)}")
    
    # 检查是否有明显的字段分隔符
    print("\n常见模式分析:")
    
    # 查找所有字段标记
    field_marks = re.findall(r'P\d+X\d+[A-Z]?', text)
    unique_marks = set(field_marks)
    print(f"找到 {len(field_marks)} 个字段标记，{len(unique_marks)} 种类型")
    
    # 统计最常见的字段
    from collections import Counter
    field_counter = Counter(field_marks)
    print("\n最常见的字段标记:")
    for field, count in field_counter.most_common(10):
        print(f"  {field}: {count}次")

if __name__ == '__main__':
    print("PDF2-2004 数据库结构分析")
    print("=" * 60)
    
    # 分析文件结构
    analyze_file_structure()
    
    print("\n" + "=" * 60)
    print("解析前几张卡片:")
    print("=" * 60)
    
    # 测试解析
    test_parse_first_cards()