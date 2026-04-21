import cv2
import numpy as np
from PIL import Image
import json
import sys

# 设置UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# 读取第一页图像
img_path = r'C:\Users\Administrator\.qclaw\workspace\pdf_images\page_1.png'
img = cv2.imread(img_path)

if img is None:
    print('无法读取图像')
else:
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 二值化
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    print(f'检测到 {len(contours)} 个轮廓')
    
    # 筛选可能是流程图节点的轮廓(面积较大的矩形区域)
    nodes = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > 500:  # 过滤小轮廓
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # 判断是否为矩形节点
            if 0.2 < aspect_ratio < 5 and w > 30 and h > 20:
                nodes.append({
                    'id': i,
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'area': int(area),
                    'aspect_ratio': round(aspect_ratio, 2)
                })
    
    print(f'识别出 {len(nodes)} 个可能的流程图节点')
    print('\n节点信息:')
    for node in nodes[:10]:  # 只显示前10个
        print(f"  节点 {node['id']}: 位置({node['x']}, {node['y']}), 尺寸({node['width']}x{node['height']}), 面积={node['area']}")
    
    # 保存分析结果
    result = {
        'total_contours': len(contours),
        'nodes': nodes
    }
    
    with open(r'C:\Users\Administrator\.qclaw\workspace\pdf_images\analysis.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print('\n分析结果已保存')

# 分析所有4页
for page_num in range(1, 5):
    img_path = f'C:\\Users\\Administrator\\.qclaw\\workspace\\pdf_images\\page_{page_num}.png'
    img = cv2.imread(img_path)
    
    if img is not None:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f'\n第{page_num}页: {len(contours)} 个轮廓')
