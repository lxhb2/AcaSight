"""
创建XRF数据整理模板
供用户手动确认和补充
"""

import pandas as pd
import json

# 读取提取的数据
with open(r'C:\Users\Administrator\.qclaw\workspace\xrf_extracted.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 用户提供的精矿重量
weights = {
    'Z1': 14, 'Z2': 13, 'Z3': 14, 'Z4': 16,
    'Z5': 18, 'Z6': 10, 'Z7': 10
}

# 原矿重量
ore_weight = 100

# 创建一个Excel工作簿
writer = pd.ExcelWriter(r'C:\Users\Administrator\.qclaw\workspace\XRF数据整理模板.xlsx', engine='openpyxl')

# Sheet 1: 图片列表
img_list = []
for i, item in enumerate(data):
    percentages = item['all_percentages']
    cu_values = item['cu_values']
    s_values = item['s_values']
    
    cu_str = ', '.join(cu_values) if cu_values else ''
    s_str = ', '.join(s_values) if s_values else ''
    
    img_list.append({
        '序号': i + 1,
        '文件名': item['file'],
        '提取的Cu值(%)': cu_str,
        '提取的S值(%)': s_str,
        '试验组': '',  # 待用户填写
        '备注': ''
    })

df_images = pd.DataFrame(img_list)
df_images.to_excel(writer, sheet_name='图片列表', index=False)

# Sheet 2: 数据录入模板
data_template = []
for i in range(1, 8):
    group = f'Z{i}'
    weight = weights[group]
    
    # 每组3次测试
    for j in range(1, 4):
        data_template.append({
            '试验组': group,
            '测试序号': j,
            '精矿重量(g)': weight,
            '铜品位Cu(%)': '',  # 待填写
            '硫品位S(%)': '',   # 待填写
            '备注': ''
        })

df_template = pd.DataFrame(data_template)
df_template.to_excel(writer, sheet_name='数据录入模板', index=False)

# Sheet 3: 计算模板
calc_template = []
for i in range(1, 8):
    group = f'Z{i}'
    calc_template.append({
        '编号': group,
        '精矿重量(g)': weights[group],
        '铜品位平均值(%)': '',  # 待计算
        '硫品位平均值(%)': '',  # 待计算
        '原矿铜品位(%)': '',   # 待填写
        '原矿硫品位(%)': '',   # 待填写
        '铜回收率(%)': '',     # 待计算
        '硫回收率(%)': ''      # 待计算
    })

df_calc = pd.DataFrame(calc_template)
df_calc.to_excel(writer, sheet_name='计算表格', index=False)

# Sheet 4: 说明
instructions = pd.DataFrame({
    '说明': [
        '1. 图片列表sheet中列出了所有22张图片',
        '2. 请在"试验组"列中填写图片属于哪个试验组（Z1-Z7）',
        '3. 数据录入模板sheet用于录入每组3次测试的数据',
        '4. 计算表格sheet用于汇总和计算回收率',
        '',
        '回收率计算公式：',
        '回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%',
        '',
        '请提供：',
        '1. 原矿的铜品位和硫品位',
        '2. 每张图片对应的试验组',
        '',
        '自动提取的数据仅供参考，请以实际XRF扫描结果为准'
    ]
})
instructions.to_excel(writer, sheet_name='说明', index=False)

writer.close()

print('Excel模板已创建: C:\\Users\\Administrator\\.qclaw\\workspace\\XRF数据整理模板.xlsx')
print('\n请打开Excel文件，在相应sheet中填写数据。')
print('\n特别需要确认：')
print('1. 哪张图片是原矿的XRF扫描结果？')
print('2. 原矿的铜品位和硫品位分别是多少？')
print('3. 其他图片如何分组（Z1-Z7，每组3张）？')
