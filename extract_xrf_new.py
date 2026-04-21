"""
重新提取XRF数据 - 基于新的文件名
文件名格式：Z组号-测试序号.jpg，以及原矿.jpg
"""

import os
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
import json

# 图片文件夹
folder = r'F:\桌面\新建文件夹'

# 获取所有图片文件
image_files = sorted(os.listdir(folder))

print('=' * 80)
print('XRF数据重新提取（基于新文件名）')
print('=' * 80)

# 存储所有数据
all_data = {}
ore_data = None  # 原矿数据

for img_file in image_files:
    img_path = os.path.join(folder, img_file)
    
    try:
        # 打开图片
        img = Image.open(img_path)
        
        # 图像预处理
        img_gray = img.convert('L')
        enhancer = ImageEnhance.Contrast(img_gray)
        img_enhanced = enhancer.enhance(2.0)
        img_sharp = img_enhanced.filter(ImageFilter.SHARPEN)
        
        # OCR识别
        text = pytesseract.image_to_string(img_sharp, lang='chi_sim+eng')
        
        # 提取Cu和S的值
        cu_values = re.findall(r'Cu[:\s]+(\d+\.?\d*)', text, re.IGNORECASE)
        s_values = re.findall(r'S[:\s]+(\d+\.?\d*)', text)
        
        # 提取所有百分比
        all_percentages = re.findall(r'(\d+\.\d+)%', text)
        
        # 判断文件类型
        if img_file == '原矿.jpg':
            print(f'\n【原矿数据】')
            ore_data = {
                'file': img_file,
                'cu_values': cu_values,
                's_values': s_values,
                'all_percentages': all_percentages,
                'text': text
            }
        else:
            # 解析文件名：Z1-1.jpg -> Z1组，第1次测试
            match = re.match(r'(Z\d+)-(\d+)\.jpg', img_file)
            if match:
                group_name = match.group(1)
                test_num = int(match.group(2))
                
                if group_name not in all_data:
                    all_data[group_name] = {}
                
                all_data[group_name][test_num] = {
                    'file': img_file,
                    'cu_values': cu_values,
                    's_values': s_values,
                    'all_percentages': all_percentages,
                    'text': text
                }
                
                print(f'{group_name}-{test_num}: Cu={cu_values}, S={s_values}')
    
    except Exception as e:
        print(f'{img_file} - 错误: {e}')

print('\n' + '=' * 80)
print('原矿数据分析')
print('=' * 80)

if ore_data:
    print(f'文件: {ore_data["file"]}')
    print(f'提取的Cu值: {ore_data["cu_values"]}')
    print(f'提取的S值: {ore_data["s_values"]}')
    print(f'所有百分比: {ore_data["all_percentages"]}')
    print(f'\n原始文本:')
    print(ore_data["text"][:500])

# 保存所有数据
output_data = {
    'ore': ore_data,
    'groups': all_data
}

output_path = r'C:\Users\Administrator\.qclaw\workspace\xrf_data_new.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)

print(f'\n\n数据已保存到: {output_path}')
