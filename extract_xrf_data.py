"""
XRF扫描图片数据提取工具
提取铜硫矿精矿的品位数据
"""

import os
import pytesseract
from PIL import Image
import re
import json
import pandas as pd

# 图片文件夹
folder = r'F:\桌面\新建文件夹'

# 获取所有图片文件
image_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

print(f'找到 {len(image_files)} 张图片')
print('\n开始处理图片...\n')

# 存储所有提取的数据
all_data = []

for i, img_file in enumerate(image_files, 1):
    img_path = os.path.join(folder, img_file)
    
    try:
        # 打开图片
        img = Image.open(img_path)
        
        # OCR识别
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        
        print(f'{i}. {img_file}')
        print('-' * 60)
        print(text[:300] if len(text) > 300 else text)
        print()
        
        # 尝试提取数据
        data = {
            'file': img_file,
            'text': text
        }
        
        all_data.append(data)
        
    except Exception as e:
        print(f'{i}. {img_file} - 错误: {e}')
        print()

# 保存提取的文本
output_path = r'C:\Users\Administrator\.qclaw\workspace\xrf_data.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f'\n文本数据已保存到: {output_path}')
