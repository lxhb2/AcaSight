"""
XRF数据整理和计算工具
假设图片按时间顺序分组，每组3张
"""

import json
import pandas as pd
import numpy as np

# 读取提取的数据
with open(r'C:\Users\Administrator\.qclaw\workspace\xrf_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 用户提供的精矿重量
concentrate_weights = {
    'Z1': 14,
    'Z2': 13,
    'Z3': 14,
    'Z4': 16,
    'Z5': 18,
    'Z6': 10,
    'Z7': 10
}

# 原矿重量
ore_weight = 100  # g

print('=' * 80)
print('XRF扫描数据整理')
print('=' * 80)

# 提取所有有效数据（按图片顺序）
all_samples = []

for i, item in enumerate(data):
    percentages = item['all_percentages']
    cu_values = item['cu_values']
    s_values = item['s_values']
    
    # 如果有明确的Cu和S值
    if cu_values and s_values:
        cu = float(cu_values[0])
        s = float(s_values[0])
        all_samples.append({
            'index': i + 1,
            'file': item['file'],
            'cu': cu,
            's': s,
            'type': 'explicit'
        })
    elif percentages and len(percentages) >= 5:
        # 尝试从百分比列表中推断
        # 去重
        unique_values = []
        seen = set()
        for p in percentages:
            if p not in seen:
                seen.add(p)
                unique_values.append(float(p))
        
        # 假设：对于铜硫矿精矿
        # Si含量最高（28-32%），Fe次之（7-10%）
        # S在3-6%之间，Cu在1-3%之间
        
        if len(unique_values) >= 6:
            # 尝试找到Cu和S
            # 通常是第4或第5个值
            possible_cu = None
            possible_s = None
            
            for j, val in enumerate(unique_values):
                if 1.0 <= val <= 3.5:  # Cu的典型范围
                    if possible_cu is None:
                        possible_cu = val
                elif 3.0 <= val <= 7.0:  # S的典型范围
                    if possible_s is None:
                        possible_s = val
            
            if possible_cu and possible_s:
                all_samples.append({
                    'index': i + 1,
                    'file': item['file'],
                    'cu': possible_cu,
                    's': possible_s,
                    'type': 'inferred'
                })

print(f'\n提取到 {len(all_samples)} 个有效样本')

# 显示提取的样本
print('\n提取的样本数据:')
for sample in all_samples:
    print(f"  {sample['index']}. {sample['file'][:30]}... Cu={sample['cu']:.2f}%, S={sample['s']:.2f}% ({sample['type']})")

# 按试验组分组（假设按顺序每3张为一组）
# 7组试验，每组3次，共21张图片
# 但我们有22张，可能第一张或最后一张是额外的

if len(all_samples) >= 21:
    # 按3个一组分组
    groups = []
    for i in range(0, 21, 3):
        group = all_samples[i:i+3]
        groups.append(group)
    
    # 计算每组的平均值
    print('\n' + '=' * 80)
    print('按试验组分组（假设按顺序每3张为一组）')
    print('=' * 80)
    
    results = []
    for i, group in enumerate(groups):
        group_name = f'Z{i+1}'
        cu_values = [s['cu'] for s in group]
        s_values = [s['s'] for s in group]
        
        cu_avg = np.mean(cu_values)
        s_avg = np.mean(s_values)
        
        print(f'\n{group_name}:')
        print(f'  Cu: {cu_values} -> 平均: {cu_avg:.2f}%')
        print(f'  S: {s_values} -> 平均: {s_avg:.2f}%')
        
        results.append({
            '编号': group_name,
            '铜品位(%)': round(cu_avg, 2),
            '硫品位(%)': round(s_avg, 2)
        })
    
    # 创建DataFrame
    df = pd.DataFrame(results)
    print('\n' + '=' * 80)
    print('结果表格')
    print('=' * 80)
    print(df.to_string(index=False))

else:
    print(f'\n提取的有效样本数({len(all_samples)})不足，无法按预期分组')
    print('请手动确认图片与试验组的对应关系')

# 保存结果
output_path = r'C:\Users\Administrator\.qclaw\workspace\xrf_results.xlsx'
if 'df' in locals():
    df.to_excel(output_path, index=False)
    print(f'\n结果已保存到: {output_path}')

print('\n' + '=' * 80)
print('重要提示')
print('=' * 80)
print('''
由于OCR识别的限制，部分图片的数据可能不准确或缺失。
建议您：

1. 手动核对图片，确认哪些图片属于哪个试验组
2. 提供原矿的铜品位和硫品位（用于计算回收率）
3. 如果有原矿的XRF扫描图，请提供

回收率计算公式：
回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%
''')
