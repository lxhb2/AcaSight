"""
流程图分析和CAD生成工具
从PDF中提取手绘流程图,识别节点、连接线和文本,并生成CAD图纸
"""

import cv2
import numpy as np
import ezdxf
from ezdxf.enums import TextEntityAlignment
import json
import os
from PIL import Image
import pytesseract

class FlowchartAnalyzer:
    def __init__(self, image_path):
        self.image_path = image_path
        self.image = cv2.imread(image_path)
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.nodes = []
        self.connections = []
        self.texts = []
        
    def detect_nodes(self):
        """检测流程图节点"""
        # 二值化
        _, binary = cv2.threshold(self.gray, 200, 255, cv2.THRESH_BINARY_INV)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 筛选节点
        self.nodes = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area > 500:  # 过滤小轮廓
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # 判断是否为流程图节点(矩形或椭圆)
                if 0.2 < aspect_ratio < 5 and w > 30 and h > 20:
                    # 判断节点类型
                    node_type = self._determine_node_type(contour, w, h)
                    
                    self.nodes.append({
                        'id': i,
                        'x': int(x),
                        'y': int(y),
                        'width': int(w),
                        'height': int(h),
                        'area': int(area),
                        'type': node_type,
                        'text': ''  # 待后续填充
                    })
        
        return self.nodes
    
    def _determine_node_type(self, contour, w, h):
        """判断节点类型"""
        # 简化判断:根据宽高比
        aspect_ratio = w / h if h > 0 else 1
        
        if aspect_ratio < 0.6:
            return 'process'  # 竖向矩形(处理过程)
        elif aspect_ratio > 1.5:
            return 'decision'  # 横向矩形(判断)
        else:
            return 'standard'  # 标准矩形
    
    def detect_connections(self):
        """检测连接线"""
        # 边缘检测
        edges = cv2.Canny(self.gray, 50, 150, apertureSize=3)
        
        # 霍夫直线变换
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                 minLineLength=30, maxLineGap=10)
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                self.connections.append({
                    'start': (int(x1), int(y1)),
                    'end': (int(x2), int(y2))
                })
        
        return self.connections
    
    def extract_text(self):
        """提取节点中的文本"""
        for node in self.nodes:
            # 提取节点区域
            x, y, w, h = node['x'], node['y'], node['width'], node['height']
            roi = self.image[y:y+h, x:x+w]
            
            # OCR识别
            try:
                text = pytesseract.image_to_string(roi, lang='chi_sim+eng')
                node['text'] = text.strip()
            except:
                node['text'] = ''
        
        return self.nodes
    
    def generate_cad(self, output_path):
        """生成CAD文件"""
        # 创建DXF文档
        doc = ezdxf.new()
        msp = doc.modelspace()
        
        # 设置图层
        doc.layers.new(name='NODES', dxfattribs={'color': 2})
        doc.layers.new(name='TEXT', dxfattribs={'color': 3})
        doc.layers.new(name='ARROWS', dxfattribs={'color': 1})
        
        scale = 0.1  # 缩放因子
        
        # 绘制节点
        for node in self.nodes:
            x = node['x'] * scale
            y = node['y'] * scale
            w = node['width'] * scale
            h = node['height'] * scale
            
            # 根据节点类型选择形状
            if node['type'] == 'decision':
                # 菱形(判断节点)
                cx, cy = x + w/2, y + h/2
                points = [
                    (cx, y),      # 上
                    (x + w, cy),  # 右
                    (cx, y + h),  # 下
                    (x, cy)       # 左
                ]
                msp.add_lwpolyline(points + [points[0]], 
                                   dxfattribs={'layer': 'NODES'})
            else:
                # 矩形
                msp.add_lwpolyline(
                    [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
                    dxfattribs={'layer': 'NODES'}
                )
            
            # 添加文本
            if node['text']:
                center_x = x + w / 2
                center_y = y + h / 2
                msp.add_text(
                    node['text'][:20],  # 限制文本长度
                    dxfattribs={
                        'layer': 'TEXT',
                        'height': min(5, h * 0.3)
                    }
                ).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)
        
        # 绘制连接线
        for conn in self.connections:
            x1, y1 = conn['start']
            x2, y2 = conn['end']
            msp.add_line(
                (x1 * scale, y1 * scale),
                (x2 * scale, y2 * scale),
                dxfattribs={'layer': 'ARROWS'}
            )
        
        # 添加标题和图框
        msp.add_text(
            "流程优化设计图",
            dxfattribs={'height': 15}
        ).set_placement((10, 150), align=TextEntityAlignment.LEFT)
        
        msp.add_text(
            f"节点数: {len(self.nodes)}  连接线: {len(self.connections)}",
            dxfattribs={'height': 8}
        ).set_placement((10, 130), align=TextEntityAlignment.LEFT)
        
        # 保存文件
        doc.saveas(output_path)
        return output_path

def process_pdf_pages(pdf_images_dir):
    """处理PDF的所有页面"""
    results = []
    
    for page_num in range(1, 5):
        image_path = os.path.join(pdf_images_dir, f'page_{page_num}.png')
        if not os.path.exists(image_path):
            continue
        
        print(f'\n正在处理第 {page_num} 页...')
        
        # 创建分析器
        analyzer = FlowchartAnalyzer(image_path)
        
        # 检测节点
        nodes = analyzer.detect_nodes()
        print(f'  检测到 {len(nodes)} 个节点')
        
        # 检测连接线
        connections = analyzer.detect_connections()
        print(f'  检测到 {len(connections)} 条连接线')
        
        # 提取文本
        analyzer.extract_text()
        print(f'  已提取文本')
        
        # 生成CAD文件
        output_path = os.path.join(pdf_images_dir, f'flowchart_page{page_num}.dxf')
        analyzer.generate_cad(output_path)
        print(f'  CAD文件已保存: {output_path}')
        
        results.append({
            'page': page_num,
            'nodes': len(nodes),
            'connections': len(connections),
            'output_file': output_path
        })
    
    return results

if __name__ == '__main__':
    # 处理PDF页面
    pdf_images_dir = r'C:\Users\Administrator\.qclaw\workspace\pdf_images'
    results = process_pdf_pages(pdf_images_dir)
    
    print('\n' + '='*60)
    print('处理完成!')
    print('='*60)
    
    for result in results:
        print(f"\n第 {result['page']} 页:")
        print(f"  节点数: {result['nodes']}")
        print(f"  连接线: {result['connections']}")
        print(f"  CAD文件: {result['output_file']}")
