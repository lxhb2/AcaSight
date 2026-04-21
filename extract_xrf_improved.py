"""
改进的XRF数据提取
使用图像预处理提高OCR识别率
"""

import os
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
import json

# 图片文件夹
folder = r'F:\桌面\新建文件夹'

# 获取所有图片文件
image_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

print(f'找到 {len(image_files)} 张图片\n')

# 存储提取的数据
results = []

for i, img_file in enumerate(image_files, 1):
    img_path = os.path.join(folder, img_file)
    
    try:
        # 打开图片
        img = Image.open(img_path)
        
        # 图像预处理
        # 转换为灰度图
        img_gray = img.convert('L')
        
        # 增强对比度
        enhancer = ImageEnhance.Contrast(img_gray)
        img_enhanced = enhancer.enhance(2.0)
        
        # 锐化
        img_sharp = img_enhanced.filter(ImageFilter.SHARPEN)
        
        # OCR识别 - 尝试多次
        texts = []
        
        # 尝试1: 原始图像
        text1 = pytesseract.image_to_string(img, lang='chi_sim+eng')
        texts.append(text1)
        
        # 尝试2: 预处理后的图像
        text2 = pytesseract.image_to_string(img_sharp, lang='chi_sim+eng')
        texts.append(text2)
        
        # 尝试3: 使用英文识别（提高数字识别率）
        text3 = pytesseract.image_to_string(img_sharp, lang='eng')
        texts.append(text3)
        
        # 合并文本
        combined_text = '\n'.join([t for t in texts if t.strip()])
        
        # 提取关键数据
        # 查找Cu和S的值
        cu_values = re.findall(r'Cu[:\s]+(\d+\.?\d*)', combined_text, re.IGNORECASE)
        s_values = re.findall(r'S[:\s]+(\d+\.?\d*)', combined_text)
        
        # 提取所有百分比数字
        all_percentages = re.findall(r'(\d+\.\d+)%', combined_text)
        
        print(f'{i}. {img_file}')
        print(f'   Cu值: {cu_values}')
        print(f'   S值: {s_values}')
        print(f'   所有百分比: {all_percentages[:10]}')  # 只显示前10个
        print()
        
        results.append({
            'file': img_file,
            'cu_values': cu_values,
            's_values': s_values,
            'all_percentages': all_percentages,
            'text': combined_text
        })
        
    except Exception as e:
        print(f'{i}. {img_file} - 错误: {e}')
        print()

# 保存结果
output_path = r'C:\Users\Administrator\.qclaw\workspace\xrf_extracted.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f'\n结果已保存到: {output_path}')
