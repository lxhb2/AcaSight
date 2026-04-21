"""
根据图片文件名的时间戳排序并分组
"""

import os
import json
import re
from datetime import datetime

# 图片文件夹
folder = r'F:\桌面\新建文件夹'

# 获取所有图片文件及其时间戳
files = os.listdir(folder)
image_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

# 提取时间戳
file_times = []
for f in image_files:
    # 从文件名中提取时间戳
    # wx_camera_1774532632546.jpg -> 1774532632546
    match = re.search(r'(\d{13})', f)
    if match:
        timestamp = int(match.group(1))
        file_times.append((f, timestamp))
    else:
        # mmexport开头的文件
        file_times.append((f, 0))

# 按时间戳排序
file_times.sort(key=lambda x: x[1])

print('=' * 80)
print('图片按时间戳排序结果')
print('=' * 80)

for i, (f, ts) in enumerate(file_times, 1):
    if ts > 0:
        # 转换为可读时间
        dt = datetime.fromtimestamp(ts / 1000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        time_str = 'N/A'
    
    print(f'{i:2d}. {f[:40]:<40} 时间: {time_str}')

# 读取提取的数据
with open(r'C:\Users\Administrator\.qclaw\workspace\xrf_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 创建文件名到数据的映射
data_map = {item['file']: item for item in data}

# 按排序后的顺序提取数据
print('\n' + '=' * 80)
print('按时间顺序提取的XRF数据')
print('=' * 80)

samples = []
for i, (filename, ts) in enumerate(file_times, 1):
    if filename in data_map:
        item = data_map[filename]
        percentages = item['all_percentages']
        cu_values = item['cu_values']
        s_values = item['s_values']
        
        if cu_values and s_values:
            cu = float(cu_values[0])
            s = float(s_values[0])
            source = 'explicit'
        elif percentages and len(percentages) >= 5:
            # 推断
            unique_values = []
            seen = set()
            for p in percentages:
                if p not in seen:
                    seen.add(p)
                    unique_values.append(float(p))
            
            possible_cu = None
            possible_s = None
            
            for val in unique_values:
                if 1.0 <= val <= 3.5 and possible_cu is None:
                    possible_cu = val
                elif 3.0 <= val <= 7.0 and possible_s is None:
                    possible_s = val
            
            if possible_cu and possible_s:
                cu = possible_cu
                s = possible_s
                source = 'inferred'
            else:
                cu = None
                s = None
                source = 'failed'
        else:
            cu = None
            s = None
            source = 'failed'
        
        if cu and s:
            samples.append({
                'index': i,
                'file': filename,
                'cu': cu,
                's': s,
                'source': source
            })
            print(f'{i:2d}. Cu={cu:5.2f}%, S={s:5.2f}% ({source})')
        else:
            print(f'{i:2d}. [无法提取数据]')

print(f'\n成功提取: {len(samples)} 个样本')

# 如果有足够的样本，按组分组
if len(samples) >= 21:
    print('\n' + '=' * 80)
    print('假设前21张为试验组Z1-Z7（每组3张）')
    print('=' * 80)
    
    groups_data = []
    for group_idx in range(7):
        start_idx = group_idx * 3
        end_idx = start_idx + 3
        group_samples = samples[start_idx:end_idx]
        
        group_name = f'Z{group_idx + 1}'
        
        if len(group_samples) == 3:
            cu_values = [s['cu'] for s in group_samples]
            s_values = [s['s'] for s in group_samples]
            
            cu_avg = sum(cu_values) / len(cu_values)
            s_avg = sum(s_values) / len(s_values)
            
            groups_data.append({
                '编号': group_name,
                'Cu测试1': cu_values[0],
                'Cu测试2': cu_values[1],
                'Cu测试3': cu_values[2],
                'Cu平均': round(cu_avg, 2),
                'S测试1': s_values[0],
                'S测试2': s_values[1],
                'S测试3': s_values[2],
                'S平均': round(s_avg, 2)
            })
            
            print(f'{group_name}: Cu={cu_values} -> {cu_avg:.2f}% | S={s_values} -> {s_avg:.2f}%')
    
    # 保存为Excel
    import pandas as pd
    df = pd.DataFrame(groups_data)
    
    # 添加精矿重量列
    weights = {'Z1': 14, 'Z2': 13, 'Z3': 14, 'Z4': 16, 'Z5': 18, 'Z6': 10, 'Z7': 10}
    df['精矿重量(g)'] = df['编号'].map(weights)
    
    # 调整列顺序
    df = df[['编号', '精矿重量(g)', 'Cu测试1', 'Cu测试2', 'Cu测试3', 'Cu平均', 
             'S测试1', 'S测试2', 'S测试3', 'S平均']]
    
    output_path = r'C:\Users\Administrator\.qclaw\workspace\XRF试验数据_初步结果.xlsx'
    df.to_excel(output_path, index=False)
    
    print(f'\n初步结果已保存到: {output_path}')
    print('\n注意：此结果基于图片时间顺序推测，请手动核对！')

print('\n' + '=' * 80)
print('重要提示')
print('=' * 80)
print('''
为了计算回收率，还需要：
1. 原矿的铜品位和硫品位
2. 确认图片分组是否正确

回收率公式：
回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%

例如：如果原矿铜品位为0.5%，则
铜回收率 = (14g × 1.26%) / (100g × 0.5%) × 100% = 35.28%
''')
