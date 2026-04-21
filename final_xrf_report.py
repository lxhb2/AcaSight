"""
最终计算和报告生成
包含回收率计算
"""

import pandas as pd
import numpy as np
from datetime import datetime

# 提取的数据
data = {
    'Z1': {'cu_avg': 1.85, 's_avg': 4.89, 'weight': 14, 'cu_tests': [1.72, None, 1.98], 's_tests': [4.90, None, 4.88]},
    'Z2': {'cu_avg': 1.57, 's_avg': 4.88, 'weight': 13, 'cu_tests': [1.89, 1.26, None], 's_tests': [5.54, 3.79, 5.30]},
    'Z3': {'cu_avg': 2.02, 's_avg': 4.90, 'weight': 14, 'cu_tests': [1.99, 2.06, None], 's_tests': [4.81, 5.00, None]},
    'Z4': {'cu_avg': 2.04, 's_avg': 4.35, 'weight': 16, 'cu_tests': [2.18, None, 1.89], 's_tests': [3.76, 3.67, 5.63]},
    'Z5': {'cu_avg': 3.48, 's_avg': 5.33, 'weight': 18, 'cu_tests': [3.48, None, None], 's_tests': [5.33, None, None]},
    'Z6': {'cu_avg': None, 's_avg': None, 'weight': 10, 'cu_tests': [None, None, None], 's_tests': [None, None, None]},
    'Z7': {'cu_avg': 2.05, 's_avg': 5.62, 'weight': 10, 'cu_tests': [None, 2.12, 1.98], 's_tests': [None, 5.64, 5.60]}
}

# 原矿重量
ore_weight = 100  # g

print('=' * 80)
print('XRF扫描铜硫矿精宽数据分析报告')
print('=' * 80)
print(f'\n生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')

print('\n' + '=' * 80)
print('数据汇总表')
print('=' * 80)

# 创建汇总表格
table_data = []
for group_name, group_data in data.items():
    row = {
        '编号': group_name,
        '精矿重量(g)': group_data['weight'],
        '铜测试1(%)': group_data['cu_tests'][0] if group_data['cu_tests'][0] else '缺失',
        '铜测试2(%)': group_data['cu_tests'][1] if group_data['cu_tests'][1] else '缺失',
        '铜测试3(%)': group_data['cu_tests'][2] if group_data['cu_tests'][2] else '缺失',
        '铜平均(%)': round(group_data['cu_avg'], 2) if group_data['cu_avg'] else '缺失',
        '硫测试1(%)': group_data['s_tests'][0] if group_data['s_tests'][0] else '缺失',
        '硫测试2(%)': group_data['s_tests'][1] if group_data['s_tests'][1] else '缺失',
        '硫测试3(%)': group_data['s_tests'][2] if group_data['s_tests'][2] else '缺失',
        '硫平均(%)': round(group_data['s_avg'], 2) if group_data['s_avg'] else '缺失'
    }
    table_data.append(row)

df = pd.DataFrame(table_data)

# 显示表格
print('\n')
print(df.to_string(index=False))

# 保存到Excel
output_path = r'C:\Users\Administrator\.qclaw\workspace\XRF试验数据_最终汇总.xlsx'
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='数据汇总', index=False)
    
    # 添加说明sheet
    instructions = pd.DataFrame({
        '说明': [
            '数据说明：',
            '1. 本表数据来自XRF扫描铜硫矿精矿的结果',
            '2. Z1-Z7为试验组编号，每组测试3次',
            '3. "缺失"表示该次测试的OCR识别失败',
            '4. Z6组所有数据均未能成功提取',
            '',
            '回收率计算需要：',
            '原矿铜品位(%)',
            '原矿硫品位(%)',
            '',
            '计算公式：',
            '回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%',
            '',
            '示例：',
            '假设原矿铜品位 = 0.8%',
            'Z1铜回收率 = (14 × 1.85%) / (100 × 0.8%) × 100% = 32.38%'
        ]
    })
    instructions.to_excel(writer, sheet_name='说明', index=False)

print(f'\n\n数据已保存到: {output_path}')

print('\n' + '=' * 80)
print('数据质量分析')
print('=' * 80)

for group_name, group_data in data.items():
    cu_valid = sum(1 for v in group_data['cu_tests'] if v is not None)
    s_valid = sum(1 for v in group_data['s_tests'] if v is not None)
    print(f'{group_name}: Cu有效样本{cu_valid}/3, S有效样本{s_valid}/3')

print('\n' + '=' * 80)
print('下一步：请提供原矿品位')
print('=' * 80)
print('''
为了计算回收率，请告诉我：
1. 原矿的铜品位是多少？（%）
2. 原矿的硫品位是多少？（%）

或者，如果"原矿.jpg"图片中有明确的数据，请告诉我具体数值。

提供后，我将立即计算所有试验组的回收率并生成最终表格！
''')

# 创建一个计算函数，等用户提供原矿品位后可以使用
def calculate_recovery_rate(concentrate_weight, concentrate_grade, ore_weight, ore_grade):
    """
    计算回收率
    回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%
    """
    if concentrate_grade is None or ore_grade is None or ore_grade == 0:
        return None
    return (concentrate_weight * concentrate_grade) / (ore_weight * ore_grade) * 100

# 示例计算（假设原矿铜品位=0.8%，硫品位=3.5%）
print('\n' + '=' * 80)
print('示例计算（假设原矿: Cu=0.8%, S=3.5%）')
print('=' * 80)

ore_cu_example = 0.8
ore_s_example = 3.5

example_data = []
for group_name, group_data in data.items():
    if group_data['cu_avg'] and group_data['s_avg']:
        cu_recovery = calculate_recovery_rate(
            group_data['weight'], group_data['cu_avg'], ore_weight, ore_cu_example
        )
        s_recovery = calculate_recovery_rate(
            group_data['weight'], group_data['s_avg'], ore_weight, ore_s_example
        )
        
        example_data.append({
            '编号': group_name,
            '铜平均(%)': round(group_data['cu_avg'], 2),
            '铜回收率(%)': round(cu_recovery, 2) if cu_recovery else '无法计算',
            '硫平均(%)': round(group_data['s_avg'], 2),
            '硫回收率(%)': round(s_recovery, 2) if s_recovery else '无法计算'
        })

df_example = pd.DataFrame(example_data)
print('\n')
print(df_example.to_string(index=False))

print('\n注意：这是示例计算，请提供实际的原矿品位以获得准确的回收率！')
