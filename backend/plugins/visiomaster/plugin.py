"""
VisioMaster Plugin
Visio图纸重建插件 — 将AI生成的流程图、架构图等重建为可编辑的Visio图纸

将图表JSON数据转换为Visio兼容格式，支持VSDX导出
"""

import json
import os
import zipfile
import uuid
from datetime import datetime
from typing import Any

from app.services.plugin_system import AcaSightPlugin


class VisiomasterPlugin(AcaSightPlugin):
    """Visio图纸重建插件"""

    _SHAPE_MAP = {
        "rectangle": "Process",
        "rounded_rectangle": "Process",
        "diamond": "Decision",
        "ellipse": "Terminator",
        "circle": "Terminator",
        "parallelogram": "InputOutput",
        "cylinder": "DataStorage",
        "hexagon": "Preparation",
        "trapezoid": "ManualOperation",
    }

    _CONNECTOR_MAP = {
        "arrow": "Arrow",
        "line": "Line",
        "dashed": "DashedArrow",
        "double_arrow": "DoubleArrow",
    }

    async def on_load(self, config: dict) -> None:
        """加载时注册钩子"""
        await super().on_load(config)
        self.register_hook("post_chart", self.post_chart)
        self._default_format = config.get("default_format", "vsdx")
        self._page_width = config.get("page_width", 11.69)
        self._page_height = config.get("page_height", 8.27)

    async def on_enable(self) -> None:
        """启用"""
        pass

    async def on_disable(self) -> None:
        """禁用"""
        pass

    async def on_unload(self) -> None:
        """卸载"""
        pass

    async def post_chart(self, chart_data: dict, **kwargs) -> dict:
        """
        post_chart 钩子处理器

        在图表生成后自动提供Visio转换建议
        """
        if not chart_data:
            return {"offered": False, "reason": "no_chart_data"}

        diagram_type = chart_data.get("type", "unknown")
        supported_types = {"flowchart", "architecture", "network", "org_chart", "sequence", "class_diagram"}

        if diagram_type not in supported_types:
            return {
                "offered": True,
                "supported": False,
                "reason": f"diagram_type '{diagram_type}' not optimally supported",
                "suggested_types": list(supported_types),
            }

        conversion_preview = self._preview_conversion(chart_data)

        return {
            "offered": True,
            "supported": True,
            "diagram_type": diagram_type,
            "conversion_preview": conversion_preview,
            "available_formats": ["vsdx"],
            "message": "Visio conversion available — call convert_to_visio or export_vsdx to proceed",
        }

    async def convert_to_visio(self, diagram_data: dict, format: str = "vsdx") -> dict:
        """
        将图表JSON数据转换为Visio兼容格式

        Args:
            diagram_data: 图表数据，包含 nodes, edges, layout 等字段
            format: 输出格式，默认 vsdx

        Returns:
            包含 shapes, connectors, layout 信息的结构化数据
        """
        if not diagram_data:
            return {"success": False, "error": "empty_diagram_data"}

        if format.lower() != "vsdx":
            return {"success": False, "error": f"unsupported_format: {format}", "supported": ["vsdx"]}

        nodes = diagram_data.get("nodes", [])
        edges = diagram_data.get("edges", [])
        layout_config = diagram_data.get("layout", {})

        shapes = self._build_shapes(nodes)
        connectors = self._build_connectors(edges, shapes)
        layout = self._build_layout(layout_config, shapes, connectors)
        pages = self._build_pages(shapes, connectors, layout)

        return {
            "success": True,
            "format": format,
            "diagram_type": diagram_data.get("type", "generic"),
            "shapes": shapes,
            "connectors": connectors,
            "layout": layout,
            "pages": pages,
            "metadata": {
                "source_node_count": len(nodes),
                "source_edge_count": len(edges),
                "converted_at": datetime.utcnow().isoformat() + "Z",
                "plugin_version": "1.0.0",
            },
        }

    async def export_vsdx(self, diagram_data: dict, output_path: str) -> dict:
        """
        导出为VSDX格式文件

        Args:
            diagram_data: 图表数据
            output_path: 输出文件路径

        Returns:
            导出结果，包含文件路径和大小
        """
        if not diagram_data:
            return {"success": False, "error": "empty_diagram_data"}

        conversion = await self.convert_to_visio(diagram_data, format="vsdx")
        if not conversion.get("success"):
            return {"success": False, "error": conversion.get("error", "conversion_failed")}

        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            vsdx_bytes = self._generate_vsdx(conversion)
            with open(output_path, "wb") as f:
                f.write(vsdx_bytes)

            file_size = os.path.getsize(output_path)
            return {
                "success": True,
                "output_path": output_path,
                "file_size": file_size,
                "shape_count": len(conversion["shapes"]),
                "connector_count": len(conversion["connectors"]),
                "page_count": len(conversion["pages"]),
            }
        except Exception as e:
            return {"success": False, "error": f"export_failed: {str(e)}"}

    def _preview_conversion(self, chart_data: dict) -> dict:
        """生成转换预览摘要"""
        nodes = chart_data.get("nodes", [])
        edges = chart_data.get("edges", [])
        shape_types = set()
        for node in nodes:
            shape_type = node.get("shape", "rectangle")
            shape_types.add(self._SHAPE_MAP.get(shape_type, "Process"))
        return {
            "total_shapes": len(nodes),
            "total_connectors": len(edges),
            "shape_types": list(shape_types),
            "estimated_complexity": "low" if len(nodes) < 10 else "medium" if len(nodes) < 30 else "high",
        }

    def _build_shapes(self, nodes: list) -> list:
        """将节点列表转换为Visio形状定义"""
        shapes = []
        for idx, node in enumerate(nodes):
            node_id = node.get("id", str(idx))
            shape_type = node.get("shape", "rectangle")
            visio_master = self._SHAPE_MAP.get(shape_type, "Process")

            x = node.get("x", 0)
            y = node.get("y", 0)
            width = node.get("width", 1.0)
            height = node.get("height", 0.5)

            shape = {
                "id": f"shape_{node_id}",
                "name": node.get("label", f"Shape_{idx}"),
                "master": visio_master,
                "original_type": shape_type,
                "position": {
                    "x": float(x),
                    "y": float(y),
                },
                "size": {
                    "width": float(width),
                    "height": float(height),
                },
                "text": node.get("label", ""),
                "style": self._build_shape_style(node),
            }

            if "fill_color" in node or "stroke_color" in node:
                shape["format"] = {
                    "fill_color": node.get("fill_color", "#FFFFFF"),
                    "stroke_color": node.get("stroke_color", "#000000"),
                    "stroke_width": node.get("stroke_width", 0.01),
                }

            shapes.append(shape)
        return shapes

    def _build_shape_style(self, node: dict) -> dict:
        """构建形状样式"""
        style = {
            "font": node.get("font", "Calibri"),
            "font_size": node.get("font_size", 10),
            "text_align": node.get("text_align", "center"),
            "vertical_align": node.get("vertical_align", "middle"),
        }
        return style

    def _build_connectors(self, edges: list, shapes: list) -> list:
        """将边列表转换为Visio连接器定义"""
        shape_index = {s["id"]: s for s in shapes}
        connectors = []

        for idx, edge in enumerate(edges):
            source_id = edge.get("source", edge.get("from", ""))
            target_id = edge.get("target", edge.get("to", ""))
            edge_id = edge.get("id", str(idx))

            source_shape_id = f"shape_{source_id}"
            target_shape_id = f"shape_{target_id}"

            connector_type = edge.get("type", "arrow")
            visio_connector = self._CONNECTOR_MAP.get(connector_type, "Arrow")

            connector = {
                "id": f"connector_{edge_id}",
                "name": edge.get("label", f"Connector_{idx}"),
                "master": visio_connector,
                "original_type": connector_type,
                "source": {
                    "shape_id": source_shape_id,
                    "connection_point": edge.get("source_point", "Bottom"),
                },
                "target": {
                    "shape_id": target_shape_id,
                    "connection_point": edge.get("target_point", "Top"),
                },
                "text": edge.get("label", ""),
                "style": {
                    "stroke_color": edge.get("stroke_color", "#000000"),
                    "stroke_width": edge.get("stroke_width", 0.01),
                    "stroke_pattern": edge.get("stroke_pattern", "solid"),
                },
            }

            routing = edge.get("routing")
            if routing:
                connector["routing"] = routing

            connectors.append(connector)
        return connectors

    def _build_layout(self, layout_config: dict, shapes: list, connectors: list) -> dict:
        """构建布局信息"""
        layout_type = layout_config.get("type", "auto")
        direction = layout_config.get("direction", "top_to_bottom")

        if shapes:
            min_x = min(s["position"]["x"] for s in shapes)
            min_y = min(s["position"]["y"] for s in shapes)
            max_x = max(s["position"]["x"] + s["size"]["width"] for s in shapes)
            max_y = max(s["position"]["y"] + s["size"]["height"] for s in shapes)
            bounds = {"min_x": min_x, "min_y": min_y, "max_x": max_x, "max_y": max_y}
        else:
            bounds = {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0}

        return {
            "type": layout_type,
            "direction": direction,
            "page_width": layout_config.get("page_width", self._page_width),
            "page_height": layout_config.get("page_height", self._page_height),
            "margin": layout_config.get("margin", 0.5),
            "spacing": layout_config.get("spacing", 0.25),
            "bounds": bounds,
            "auto_route": layout_config.get("auto_route", True),
        }

    def _build_pages(self, shapes: list, connectors: list, layout: dict) -> list:
        """构建页面结构"""
        page = {
            "id": f"page_{uuid.uuid4().hex[:8]}",
            "name": "Page-1",
            "width": layout["page_width"],
            "height": layout["page_height"],
            "shape_ids": [s["id"] for s in shapes],
            "connector_ids": [c["id"] for c in connectors],
        }
        return [page]

    def _generate_vsdx(self, conversion: dict) -> bytes:
        """
        生成VSDX文件字节流

        VSDX是Open Packaging Convention格式 (ZIP包含XML部件)
        这里生成一个最小有效的VSDX结构
        """
        import io

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", self._content_types_xml())
            zf.writestr("_rels/.rels", self._rels_xml())
            zf.writestr("visio/document.xml", self._document_xml(conversion))
            zf.writestr("visio/_rels/document.xml.rels", self._document_rels_xml())
            zf.writestr("visio/pages/pages.xml", self._pages_manifest_xml(conversion))
            zf.writestr("visio/pages/_rels/pages.xml.rels", self._pages_rels_xml(conversion))
            zf.writestr("visio/pages/page1.xml", self._page_xml(conversion))

        return buffer.getvalue()

    def _content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/visio/document.xml" ContentType="application/vnd.ms-visio.drawing.main+xml"/>'
            '<Override PartName="/visio/pages/pages.xml" ContentType="application/vnd.ms-visio.pages+xml"/>'
            '<Override PartName="/visio/pages/page1.xml" ContentType="application/vnd.ms-visio.page+xml"/>'
            '</Types>'
        )

    def _rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/document" Target="visio/document.xml"/>'
            '</Relationships>'
        )

    def _document_xml(self, conversion: dict) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<VisioDocument xmlns="http://schemas.microsoft.com/office/visio/2012/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<DocumentProperties>'
            f'<Creator>AcaSight VisioMaster Plugin v1.0.0</Creator>'
            f'<TimeCreated>{datetime.utcnow().isoformat()}Z</TimeCreated>'
            '</DocumentProperties>'
            '</VisioDocument>'
        )

    def _document_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.microsoft.com/visio/2010/relationships/pages" Target="pages/pages.xml"/>'
            '</Relationships>'
        )

    def _pages_manifest_xml(self, conversion: dict) -> str:
        pages = conversion.get("pages", [])
        page_refs = ""
        for i, page in enumerate(pages, 1):
            page_refs += f'<Page ID="{i}" Name="{page["name"]}" r:id="rId{i}"/>'
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Pages xmlns="http://schemas.microsoft.com/office/visio/2012/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'{page_refs}'
            '</Pages>'
        )

    def _pages_rels_xml(self, conversion: dict) -> str:
        pages = conversion.get("pages", [])
        rels = ""
        for i in range(1, len(pages) + 1):
            rels += f'<Relationship Id="rId{i}" Type="http://schemas.microsoft.com/visio/2010/relationships/page" Target="page{i}.xml"/>'
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'{rels}'
            '</Relationships>'
        )

    def _page_xml(self, conversion: dict) -> str:
        shapes_xml = ""
        for shape in conversion.get("shapes", []):
            pos = shape["position"]
            size = shape["size"]
            fmt = shape.get("format", {})
            fill_color = fmt.get("fill_color", "#FFFFFF")
            stroke_color = fmt.get("stroke_color", "#000000")

            shapes_xml += (
                f'<Shape ID="{shape["id"]}" NameU="{shape["name"]}" Type="Shape" Master="{shape["master"]}">'
                f'<Cell N="PinX" V="{pos["x"] + size["width"] / 2}"/>'
                f'<Cell N="PinY" V="{pos["y"] + size["height"] / 2}"/>'
                f'<Cell N="Width" V="{size["width"]}"/>'
                f'<Cell N="Height" V="{size["height"]}"/>'
                f'<Cell N="FillForegnd" V="{fill_color}"/>'
                f'<Cell N="LineColor" V="{stroke_color}"/>'
                f'<Text>{shape.get("text", "")}</Text>'
                f'</Shape>'
            )

        connectors_xml = ""
        for conn in conversion.get("connectors", []):
            style = conn.get("style", {})
            connectors_xml += (
                f'<Shape ID="{conn["id"]}" NameU="{conn["name"]}" Type="Connector" Master="{conn["master"]}">'
                f'<Cell N="BeginX" V="0" F="{conn["source"]["shape_id"]}!Connections.{conn["source"]["connection_point"]}.X"/>'
                f'<Cell N="BeginY" V="0" F="{conn["source"]["shape_id"]}!Connections.{conn["source"]["connection_point"]}.Y"/>'
                f'<Cell N="EndX" V="0" F="{conn["target"]["shape_id"]}!Connections.{conn["target"]["connection_point"]}.X"/>'
                f'<Cell N="EndY" V="0" F="{conn["target"]["shape_id"]}!Connections.{conn["target"]["connection_point"]}.Y"/>'
                f'<Cell N="LineColor" V="{style.get("stroke_color", "#000000")}"/>'
                f'<Text>{conn.get("text", "")}</Text>'
                f'</Shape>'
            )

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<PageContents xmlns="http://schemas.microsoft.com/office/visio/2012/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'{shapes_xml}'
            f'{connectors_xml}'
            '</PageContents>'
        )


__acasight_plugin__ = VisiomasterPlugin()
