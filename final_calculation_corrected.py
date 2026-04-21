"""
最终计算：使用用户确认的正确数据
"""

import pandas as pd
import numpy as np
from datetime import datetime

print('=' * 80)
print('XRF扫描铜硫矿精宽数据最终计算（修正版）')
print('=' * 80)
print(f'计算时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# 原矿数据
ore_weight = 100  # g
ore_cu_grade = 0.35  # %
ore_s_grade = 3.5  # % (待确认)

print(f'\n原矿参数:')
print(f'  重量: {ore_weight}g')
print(f'  铜品位: {ore_cu_grade}%')
print(f'  硫品位: {ore_s_grade}% (待确认)')

# 完整正确的数据
data = {
    'Z1': {
        'weight': 14,
        'cu_tests': [1.72, None, 1.98],
        's_tests': [4.90, None, 4.88]
    },
    'Z2': {
        'weight': 13,
        'cu_tests': [1.89, 1.26, None],
        's_tests': [5.54, 3.79, 5.30]
    },
    'Z3': {
        'weight': 14,
        'cu_tests': [1.99, 2.06, None],
        's_tests': [4.81, 5.00, None]
    },
    'Z4': {
        'weight': 16,
        'cu_tests': [2.18, None, 1.89],
        's_tests': [3.76, 3.67, 5.63]
    },
    'Z5': {
        'weight': 18,
        'cu_tests': [1.41, 1.42, 1.50],  # 用户确认的正确数据
        's_tests': [3.48, 3.54, 3.48]   # 用户确认的正确数据
    },
    'Z6': {
        'weight': 10,
        'cu_tests': [2.47, 2.48, None],
        's_tests': [3.94, 3.99, None]
    },
    'Z7': {
        'weight': 10,
        'cu_tests': [None, 2.12, 1.98],
        's_tests': [None, 5.64, 5.60]
    }
}

# 计算函数
def calculate_avg(values):
    valid_values = [v for v in values if v is not None]
    return sum(valid_values) / len(valid_values) if valid_values else None

def calculate_recovery(concentrate_weight, concentrate_grade, ore_weight, ore_grade):
    if concentrate_grade is None or ore_grade is None or ore_grade == 0:
        return None
    return (concentrate_weight * concentrate_grade) / (ore_weight * ore_grade) * 100

# 计算所有结果
results = []
print('\n' + '=' * 80)
print('各组数据详情')
print('=' * 80)

for group_name in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7']:
    group_data = data[group_name]
    
    # 计算平均值
    cu_avg = calculate_avg(group_data['cu_tests'])
    s_avg = calculate_avg(group_data['s_tests'])
    
    # 计算回收率
    cu_recovery = calculate_recovery(group_data['weight'], cu_avg, ore_weight, ore_cu_grade)
    s_recovery = calculate_recovery(group_data['weight'], s_avg, ore_weight, ore_s_grade)
    
    # 统计有效样本数
    cu_valid = sum(1 for v in group_data['cu_tests'] if v is not None)
    s_valid = sum(1 for v in group_data['s_tests'] if v is not None)
    
    print(f'\n{group_name}:')
    print(f'  铜测试值: {group_data["cu_tests"]} -> 平均: {round(cu_avg, 2) if cu_avg else "缺失"}%')
    print(f'  硫测试值: {group_data["s_tests"]} -> 平均: {round(s_avg, 2) if s_avg else "缺失"}%')
    print(f'  铜回收率: {round(cu_recovery, 2) if cu_recovery else "无法计算"}%')
    print(f'  硫回收率: {round(s_recovery, 2) if s_recovery else "无法计算"}%')
    
    results.append({
        '编号': group_name,
        '精矿重量(g)': group_data['weight'],
        '铜测试1(%)': group_data['cu_tests'][0] if group_data['cu_tests'][0] else '缺失',
        '铜测试2(%)': group_data['cu_tests'][1] if group_data['cu_tests'][1] else '缺失',
        '铜测试3(%)': group_data['cu_tests'][2] if group_data['cu_tests'][2] else '缺失',
        '铜平均(%)': round(cu_avg, 2) if cu_avg else '缺失',
        '铜回收率(%)': round(cu_recovery, 2) if cu_recovery else '无法计算',
        '硫测试1(%)': group_data['s_tests'][0] if group_data['s_tests'][0] else '缺失',
        '硫测试2(%)': group_data['s_tests'][1] if group_data['s_tests'][1] else '缺失',
        '硫测试3(%)': group_data['s_tests'][2] if group_data['s_tests'][2] else '缺失',
        '硫平均(%)': round(s_avg, 2) if s_avg else '缺失',
        '硫回收率(%)': round(s_recovery, 2) if s_recovery else '无法计算'
    })

# 创建DataFrame
df = pd.DataFrame(results)

# 显示完整表格
print('\n' + '=' * 80)
print('完整数据表格')
print('=' * 80)
print('\n')
print(df.to_string(index=False))

# 创建简化汇总表
df_summary = df[['编号', '精矿重量(g)', '铜平均(%)', '铜回收率(%)', '硫平均(%)', '硫回收率(%)']]

print('\n' + '=' * 80)
print('汇总表（平均值和回收率）')
print('=' * 80)
print('\n')
print(df_summary.to_string(index=False))

# 保存到Excel
output_path = r'C:\Users\Administrator\.qclaw\workspace\XRF试验数据_最终结果.xlsx'
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    # 完整数据
    df.to_excel(writer, sheet_name='完整数据', index=False)
    
    # 汇总表
    df_summary.to_excel(writer, sheet_name='汇总表', index=False)
    
    # 原矿信息
    ore_info = pd.DataFrame({
        '项目': ['原矿重量(g)', '原矿铜品位(%)', '原矿硫品位(%)'],
        '数值': [ore_weight, ore_cu_grade, ore_s_grade]
    })
    ore_info.to_excel(writer, sheet_name='原矿信息', index=False)

print(f'\n\n完整结果已保存到: {output_path}')

# 统计分析
print('\n' + '=' * 80)
print('数据统计分析')
print('=' * 80)

cu_recoveries = [r['铜回收率(%)'] for r in results if isinstance(r['铜回收率(%)'], (int, float))]
s_recoveries = [r['硫回收率(%)'] for r in results if isinstance(r['硫回收率(%)'], (int, float))]

print(f'\n铜回收率:')
print(f'  最高: {max(cu_recoveries):.2f}% (Z{cu_recoveries.index(max(cu_recoveries))+1})')
print(f'  最低: {min(cu_recoveries):.2f}% (Z{cu_recoveries.index(min(cu_recoveries))+1})')
print(f'  平均: {sum(cu_recoveries)/len(cu_recoveries):.2f}%')

print(f'\n硫回收率:')
print(f'  最高: {max(s_recoveries):.2f}%')
print(f'  最低: {min(s_recoveries):.2f}%')
print(f'  平均: {sum(s_recoveries)/len(s_recoveries):.2f}%')

print('\n' + '=' * 80)
print('计算完成！')
print('=' * 80)
print('''
所有数据已正确计算并保存。
原矿硫品位使用了3.5%，如需修正请告知。
''')
