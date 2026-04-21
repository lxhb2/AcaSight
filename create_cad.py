import ezdxf
import json
from ezdxf.enums import TextEntityAlignment

# 创建新的DXF文档
doc = ezdxf.new()
msp = doc.modelspace()

# 设置图层
doc.layers.new(name='FLOWCHART_NODES', dxfattribs={'color': 2})  # 黄色
doc.layers.new(name='FLOWCHART_TEXT', dxfattribs={'color': 3})   # 绿色
doc.layers.new(name='FLOWCHART_ARROWS', dxfattribs={'color': 1}) # 红色

# 读取分析结果
with open(r'C:\Users\Administrator\.qclaw\workspace\pdf_images\analysis.json', 'r', encoding='utf-8') as f:
    analysis = json.load(f)

# 绘制流程图节点
scale = 0.1  # 缩放因子
for node in analysis['nodes']:
    # 计算CAD坐标(将像素坐标转换为CAD坐标)
    x = node['x'] * scale
    y = node['y'] * scale
    w = node['width'] * scale
    h = node['height'] * scale
    
    # 绘制矩形节点
    msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
        dxfattribs={'layer': 'FLOWCHART_NODES'}
    )
    
    # 添加节点标签
    center_x = x + w / 2
    center_y = y + h / 2
    msp.add_text(
        f"N{node['id']}",
        dxfattribs={
            'layer': 'FLOWCHART_TEXT',
            'height': 5
        }
    ).set_placement((center_x, center_y), align=TextEntityAlignment.MIDDLE_CENTER)

# 添加图框和标题
msp.add_text(
    "流程优化设计图 - 第1页",
    dxfattribs={'height': 10}
).set_placement((10, 100), align=TextEntityAlignment.LEFT)

# 添加节点统计信息
info_text = f"识别节点数: {len(analysis['nodes'])}"
msp.add_text(
    info_text,
    dxfattribs={'height': 5}
).set_placement((10, 80), align=TextEntityAlignment.LEFT)

# 保存DXF文件
output_path = r'C:\Users\Administrator\.qclaw\workspace\flowchart_page1.dxf'
doc.saveas(output_path)

print(f'CAD文件已创建: {output_path}')
print(f'\n文件包含:')
print(f'  - {len(analysis["nodes"])} 个流程图节点')
print(f'  - 节点标注图层: FLOWCHART_NODES')
print(f'  - 文本标注图层: FLOWCHART_TEXT')
print(f'\n请使用AutoCAD或其他CAD软件打开此文件')
