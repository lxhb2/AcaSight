"""
创建流程图对比可视化
将原始图像和识别结果并排显示
"""

import cv2
import numpy as np
import json

def create_comparison_image(page_num):
    # 读取原始图像
    img_path = f'C:\\Users\\Administrator\\.qclaw\\workspace\\pdf_images\\page_{page_num}.png'
    img = cv2.imread(img_path)
    
    if img is None:
        print(f'无法读取图像: {img_path}')
        return
    
    # 创建副本用于绘制识别结果
    result_img = img.copy()
    
    # 边缘检测
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # 查找轮廓
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 绘制识别的节点
    node_count = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 500:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            if 0.2 < aspect_ratio < 5 and w > 30 and h > 20:
                # 绘制绿色矩形框
                cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # 添加节点编号
                cv2.putText(result_img, f'N{node_count}', 
                           (x + 5, y + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                node_count += 1
    
    # 绘制检测到的线条
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                            minLineLength=30, maxLineGap=10)
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # 绘制红色线条
            cv2.line(result_img, (x1, y1), (x2, y2), (0, 0, 255), 1)
    
    # 添加统计信息
    cv2.putText(result_img, f'Nodes: {node_count}', 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if lines is not None:
        cv2.putText(result_img, f'Lines: {len(lines)}', 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 创建对比图像(左右并排)
    h, w = img.shape[:2]
    comparison = np.zeros((h, w * 2, 3), dtype=np.uint8)
    comparison[:, :w] = img
    comparison[:, w:] = result_img
    
    # 添加标签
    cv2.putText(comparison, 'Original', (w // 2 - 50, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(comparison, 'Detected', (w + w // 2 - 50, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # 保存对比图像
    output_path = f'C:\\Users\\Administrator\\.qclaw\\workspace\\pdf_images\\comparison_page{page_num}.png'
    cv2.imwrite(output_path, comparison)
    print(f'对比图像已保存: {output_path}')

# 处理所有页面
for page_num in range(1, 5):
    create_comparison_image(page_num)

print('\n所有对比图像已生成!')
