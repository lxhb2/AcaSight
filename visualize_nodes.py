import cv2
import numpy as np
import json

# 读取分析结果
with open(r'C:\Users\Administrator\.qclaw\workspace\pdf_images\analysis.json', 'r', encoding='utf-8') as f:
    analysis = json.load(f)

# 读取原始图像
img = cv2.imread(r'C:\Users\Administrator\.qclaw\workspace\pdf_images\page_1.png')

# 在图像上绘制识别出的节点
for node in analysis['nodes']:
    # 绘制矩形框
    cv2.rectangle(img, 
                  (node['x'], node['y']), 
                  (node['x'] + node['width'], node['y'] + node['height']),
                  (0, 255, 0), 2)
    
    # 添加标签
    label = f"N{node['id']}"
    cv2.putText(img, label, 
                (node['x'], node['y'] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

# 保存标注后的图像
output_path = r'C:\Users\Administrator\.qclaw\workspace\pdf_images\page_1_annotated.png'
cv2.imwrite(output_path, img)

print(f'标注图像已保存: {output_path}')
print(f'\n识别的节点总数: {len(analysis["nodes"])}')
print('\n节点详细信息:')
for node in analysis['nodes']:
    print(f"  节点 {node['id']}:")
    print(f"    位置: ({node['x']}, {node['y']})")
    print(f"    尺寸: {node['width']} x {node['height']}")
    print(f"    面积: {node['area']}")
    print(f"    宽高比: {node['aspect_ratio']}")
