"""
智能分析XRF数据
根据图片特征和数值模式识别Cu和S的品位
"""

import os
import json
import re
from datetime import datetime

# 读取提取的数据
with open(r'C:\Users\Administrator\.qclaw\workspace\xrf_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=' * 80)
print('XRF扫描数据分析')
print('=' * 80)

# 分析每张图片
valid_samples = []

for i, item in enumerate(data):
    file = item['file']
    percentages = item['all_percentages']
    cu_values = item['cu_values']
    s_values = item['s_values']
    text = item['text']
    
    print(f'\n{i+1}. {file}')
    print(f'   提取的百分比数: {len(percentages)}')
    
    # 如果有明确的Cu和S值
    if cu_values and s_values:
        cu = float(cu_values[0])
        s = float(s_values[0])
        print(f'   ✓ Cu: {cu}%')
        print(f'   ✓ S: {s}%')
        valid_samples.append({
            'file': file,
            'cu': cu,
            's': s
        })
    elif percentages:
        # 尝试从百分比列表中推断Cu和S
        # XRF结果通常按含量从高到低排列
        # 对于铜硫矿精矿，Si、Fe、Al、S、Cu是主要元素
        
        # 去重并转换为浮点数
        unique_values = []
        seen = set()
        for p in percentages:
            if p not in seen:
                seen.add(p)
                unique_values.append(float(p))
        
        print(f'   所有百分比: {unique_values[:8]}')
        
        # 查找文本中是否有Si、Fe、Al、S、Cu等标记
        has_si = 'Si' in text or 'si' in text
        has_fe = 'Fe' in text or 'fe' in text
        has_cu = 'Cu' in text or 'cu' in text
        has_s = 'S:' in text or 'S ' in text
        
        print(f'   包含元素: Si={has_si}, Fe={has_fe}, Cu={has_cu}, S={has_s}')
        
        # 如果文本中提到了这些元素，尝试按位置提取
        if unique_values:
            # 通常Si含量最高，然后是Fe
            # S和Cu的值需要从文本中定位
            if len(unique_values) >= 6:
                # 假设前几个值是 Si, Fe, Al, S, Cu...
                print(f'   推测: Si≈{unique_values[0]}%, Fe≈{unique_values[1]}%')

print('\n' + '=' * 80)
print('总结')
print('=' * 80)

print(f'\n成功提取Cu和S值的图片数: {len(valid_samples)}')
print('\n有效样本:')
for sample in valid_samples:
    print(f"  {sample['file']}: Cu={sample['cu']}%, S={sample['s']}%")

# 保存有效样本
output_path = r'C:\Users\Administrator\.qclaw\workspace\valid_xrf_samples.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(valid_samples, f, ensure_ascii=False, indent=2)

print(f'\n有效样本数据已保存到: {output_path}')

print('\n' + '=' * 80)
print('需要用户确认的信息:')
print('=' * 80)
print('''
1. 图片顺序：这22张图片是按什么顺序排列的？
   - 是否按时间顺序对应Z1-Z7试验组？
   - 每个试验组3次测试，共7组，应该有21张图片

2. 原矿品位：原矿的铜品位和硫品位分别是多少？
   - 这是计算回收率的关键参数

3. 图片分组：能否确认哪些图片属于同一个试验组？

请提供以上信息，以便准确计算平均值和回收率。
''')
