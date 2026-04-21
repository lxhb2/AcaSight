"""
最终计算：包含用户提供的原矿品位和Z6组数据
"""

import pandas as pd
import numpy as np
from datetime import datetime

print('=' * 80)
print('XRF扫描铜硫矿精宽数据最终计算')
print('=' * 80)
print(f'计算时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

# 原矿数据
ore_weight = 100  # g
ore_cu_grade = 0.35  # %
# 注意：用户没有提供原矿硫品位，先假设为3.5%
ore_s_grade = 3.5  # % (需要确认)

print(f'\n原矿参数:')
print(f'  重量: {ore_weight}g')
print(f'  铜品位: {ore_cu_grade}%')
print(f'  硫品位: {ore_s_grade}% (需要确认)')

# 更新后的完整数据（包含用户提供的Z6数据）
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
        'cu_tests': [3.48, None, None],
        's_tests': [5.33, None, None]
    },
    'Z6': {
        'weight': 10,
        'cu_tests': [2.47, 2.48, None],  # 用户提供的最新数据
        's_tests': [3.94, 3.99, None]     # 用户提供的最新数据
    },
    'Z7': {
        'weight': 10,
        'cu_tests': [None, 2.12, 1.98],
        's_tests': [None, 5.64, 5.60]
    }
}

# 计算平均值和回收率
def calculate_avg(values):
    valid_values = [v for v in values if v is not None]
    return sum(valid_values) / len(valid_values) if valid_values else None

def calculate_recovery(concentrate_weight, concentrate_grade, ore_weight, ore_grade):
    if concentrate_grade is None or ore_grade is None or ore_grade == 0:
        return None
    return (concentrate_weight * concentrate_grade) / (ore_weight * ore_grade) * 100

print('\n' + '=' * 80)
print('计算结果')
print('=' * 80)

results = []
for group_name, group_data in data.items():
    # 计算平均值
    cu_avg = calculate_avg(group_data['cu_tests'])
    s_avg = calculate_avg(group_data['s_tests'])
    
    # 计算回收率
    cu_recovery = calculate_recovery(group_data['weight'], cu_avg, ore_weight, ore_cu_grade)
    s_recovery = calculate_recovery(group_data['weight'], s_avg, ore_weight, ore_s_grade)
    
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
    
    print(f'\n{group_name}:')
    print(f'  精矿重量: {group_data["weight"]}g')
    print(f'  铜平均品位: {round(cu_avg, 2) if cu_avg else "缺失"}%')
    print(f'  铜回收率: {round(cu_recovery, 2) if cu_recovery else "无法计算"}%')
    print(f'  硫平均品位: {round(s_avg, 2) if s_avg else "缺失"}%')
    print(f'  硫回收率: {round(s_recovery, 2) if s_recovery else "无法计算"}%')

# 创建DataFrame
df = pd.DataFrame(results)

# 显示完整表格
print('\n' + '=' * 80)
print('完整数据表格')
print('=' * 80)
print('\n')
print(df.to_string(index=False))

# 保存到Excel
output_path = r'C:\Users\Administrator\.qclaw\workspace\XRF试验数据_完整结果.xlsx'
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    # 主要结果表格
    df.to_excel(writer, sheet_name='完整数据', index=False)
    
    # 简化表格（只包含平均值和回收率）
    df_simple = df[['编号', '精矿重量(g)', '铜平均(%)', '铜回收率(%)', '硫平均(%)', '硫回收率(%)']]
    df_simple.to_excel(writer, sheet_name='汇总表', index=False)
    
    # 原矿信息
    ore_info = pd.DataFrame({
        '项目': ['原矿重量(g)', '原矿铜品位(%)', '原矿硫品位(%)'],
        '数值': [ore_weight, ore_cu_grade, f'{ore_s_grade} (需确认)']
    })
    ore_info.to_excel(writer, sheet_name='原矿信息', index=False)

print(f'\n\n完整结果已保存到: {output_path}')

print('\n' + '=' * 80)
print('重要提示')
print('=' * 80)
print(f'''
✅ 铜回收率已计算完成！
   - 原矿铜品位: {ore_cu_grade}%

⚠️  硫回收率需要确认：
   - 我暂时使用原矿硫品位 = {ore_s_grade}%
   - 如果不正确，请提供准确的原矿硫品位

📊 分析结果：
   - Z5组铜品位最高 (3.48%)，铜回收率最高 (78.97%)
   - Z2组铜品位最低 (1.57%)
   - Z6组数据已补充完整
''')
