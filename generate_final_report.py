"""
最终XRF数据整理和报告生成
"""

import pandas as pd
import numpy as np
from datetime import datetime

# 按时间顺序提取的数据（从上面的输出）
extracted_data = [
    {'seq': 1, 'cu': 1.72, 's': 4.90, 'source': 'inferred'},
    {'seq': 2, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 3, 'cu': 1.98, 's': 4.88, 'source': 'inferred'},
    {'seq': 4, 'cu': 1.89, 's': 5.54, 'source': 'inferred'},
    {'seq': 5, 'cu': 1.26, 's': 2.00, 'source': 'explicit'},
    {'seq': 6, 'cu': 1.92, 's': 5.30, 'source': 'inferred'},
    {'seq': 7, 'cu': 1.83, 's': 4.71, 'source': 'explicit'},
    {'seq': 8, 'cu': 2.06, 's': 5.00, 'source': 'explicit'},
    {'seq': 9, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 10, 'cu': 1.45, 's': 3.76, 'source': 'explicit'},
    {'seq': 11, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 12, 'cu': 1.37, 's': 5.63, 'source': 'inferred'},
    {'seq': 13, 'cu': 3.48, 's': 5.33, 'source': 'inferred'},
    {'seq': 14, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 15, 'cu': 3.48, 's': 5.15, 'source': 'inferred'},
    {'seq': 16, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 17, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 18, 'cu': None, 's': None, 'source': 'failed'},
    {'seq': 19, 'cu': 2.25, 's': 5.78, 'source': 'inferred'},
    {'seq': 20, 'cu': 2.12, 's': 5.64, 'source': 'inferred'},
    {'seq': 21, 'cu': 1.98, 's': 5.60, 'source': 'inferred'},
    {'seq': 22, 'cu': None, 's': None, 'source': 'failed'},
]

# 精矿重量
concentrate_weights = {
    'Z1': 14, 'Z2': 13, 'Z3': 14, 'Z4': 16,
    'Z5': 18, 'Z6': 10, 'Z7': 10
}

# 原矿重量
ore_weight = 100

print('=' * 80)
print('XRF扫描数据最终分析报告')
print('=' * 80)
print(f'\n生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
print(f'图片总数: 22张')
print(f'成功提取: 14张')
print(f'数据缺失: 8张')

# 尝试按试验组分组（假设前21张为Z1-Z7，每组3张）
print('\n' + '=' * 80)
print('试验组数据汇总（基于时间顺序推测）')
print('=' * 80)

groups = []
for group_idx in range(7):
    group_name = f'Z{group_idx + 1}'
    start_idx = group_idx * 3
    end_idx = start_idx + 3
    
    group_data = extracted_data[start_idx:end_idx]
    
    # 提取有效数据
    cu_values = [d['cu'] for d in group_data if d['cu'] is not None]
    s_values = [d['s'] for d in group_data if d['s'] is not None]
    
    if cu_values and s_values:
        cu_avg = sum(cu_values) / len(cu_values)
        s_avg = sum(s_values) / len(s_values)
        valid_count = len(cu_values)
    else:
        cu_avg = None
        s_avg = None
        valid_count = 0
    
    groups.append({
        '编号': group_name,
        '精矿重量(g)': concentrate_weights[group_name],
        '有效样本数': valid_count,
        '铜测试1(%)': group_data[0]['cu'] if group_data[0]['cu'] else '缺失',
        '铜测试2(%)': group_data[1]['cu'] if group_data[1]['cu'] else '缺失',
        '铜测试3(%)': group_data[2]['cu'] if group_data[2]['cu'] else '缺失',
        '铜平均(%)': round(cu_avg, 2) if cu_avg else '缺失',
        '硫测试1(%)': group_data[0]['s'] if group_data[0]['s'] else '缺失',
        '硫测试2(%)': group_data[1]['s'] if group_data[1]['s'] else '缺失',
        '硫测试3(%)': group_data[2]['s'] if group_data[2]['s'] else '缺失',
        '硫平均(%)': round(s_avg, 2) if s_avg else '缺失'
    })
    
    print(f'\n{group_name}:')
    print(f'  精矿重量: {concentrate_weights[group_name]}g')
    print(f'  有效样本: {valid_count}/3')
    if cu_values:
        print(f'  Cu: {cu_values} -> 平均: {cu_avg:.2f}%')
    if s_values:
        print(f'  S: {s_values} -> 平均: {s_avg:.2f}%')

# 创建DataFrame
df = pd.DataFrame(groups)

# 保存到Excel
output_path = r'C:\Users\Administrator\.qclaw\workspace\XRF试验数据汇总.xlsx'
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='数据汇总', index=False)
    
    # 添加说明sheet
    instructions = pd.DataFrame({
        '重要说明': [
            '1. 本表数据基于图片时间顺序推测分组',
            '2. 部分数据因OCR识别失败而缺失',
            '3. 请手动核对并补充缺失数据',
            '',
            '计算回收率需要：',
            '1. 原矿的铜品位(%)',
            '2. 原矿的硫品位(%)',
            '',
            '回收率计算公式：',
            '回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%',
            '',
            '例如：',
            '原矿铜品位 = 0.5%',
            '精矿重量 = 14g',
            '精矿铜品位 = 1.26%',
            '铜回收率 = (14 × 1.26%) / (100 × 0.5%) × 100% = 35.28%'
        ]
    })
    instructions.to_excel(writer, sheet_name='说明', index=False)

print(f'\n\n汇总表格已保存到: {output_path}')

# 创建最终的Markdown报告
report = f"""# XRF扫描铜硫矿精宽数据分析报告

## 基本信息
- **分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **图片总数**: 22张
- **成功提取**: 14张
- **数据缺失**: 8张
- **试验组数**: 7组（Z1-Z7）
- **每组测试次数**: 3次

## 数据汇总表

| 编号 | 精矿重量(g) | 有效样本数 | 铜平均(%) | 硫平均(%) |
|------|-------------|------------|-----------|-----------|
"""

for g in groups:
    cu_avg_str = f"{g['铜平均(%)']}" if g['铜平均(%)'] != '缺失' else '缺失'
    s_avg_str = f"{g['硫平均(%)']}" if g['硫平均(%)'] != '缺失' else '缺失'
    report += f"| {g['编号']} | {g['精矿重量(g)']} | {g['有效样本数']}/3 | {cu_avg_str} | {s_avg_str} |\n"

report += """
## 详细数据

"""

for g in groups:
    report += f"""### {g['编号']}
- **精矿重量**: {g['精矿重量(g)']}g
- **有效样本数**: {g['有效样本数']}/3

| 测试序号 | 铜品位Cu(%) | 硫品位S(%) |
|----------|-------------|------------|
| 1 | {g['铜测试1(%)']} | {g['硫测试1(%)']} |
| 2 | {g['铜测试2(%)']} | {g['硫测试2(%)']} |
| 3 | {g['铜测试3(%)']} | {g['硫测试3(%)']} |
| **平均** | **{g['铜平均(%)']}** | **{g['硫平均(%)']}** |

"""

report += """## 回收率计算（需要原矿品位）

为了计算回收率，请提供：
1. **原矿铜品位**: ?%
2. **原矿硫品位**: ?%

### 计算公式
```
回收率 = (精矿重量 × 精矿品位) / (原矿重量 × 原矿品位) × 100%
```

### 计算示例
假设原矿铜品位 = 0.5%，则：
- Z1铜回收率 = (14 × 1.26%) / (100 × 0.5%) × 100% = 35.28%

## 数据质量说明

⚠️ **重要提示**：
1. 部分数据因OCR识别限制而缺失
2. 标注为"inferred"的数据是从百分比列表中推断的
3. 标注为"explicit"的数据是明确识别到"Cu:"和"S:"标记的
4. 建议手动核对所有数据

## 文件列表

已生成的文件：
1. `XRF试验数据汇总.xlsx` - Excel格式的汇总表格
2. `XRF数据整理模板.xlsx` - 包含图片列表的模板
3. `XRF分析报告.md` - 本报告

---
*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
*工具: OpenClaw AI Assistant*
"""

# 保存Markdown报告
report_path = r'C:\Users\Administrator\.qclaw\workspace\XRF分析报告.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report)

print(f'Markdown报告已保存到: {report_path}')

print('\n' + '=' * 80)
print('下一步操作')
print('=' * 80)
print('''
请提供以下信息以完成回收率计算：
1. 原矿的铜品位(%)
2. 原矿的硫品位(%)

提供后，我将：
1. 计算每个试验组的铜回收率和硫回收率
2. 生成完整的最终表格
3. 创建可视化图表（如需要）
''')
