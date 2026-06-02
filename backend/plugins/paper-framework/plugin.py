"""
Paper Framework Plugin
论文框架图草图生成 — 支持手绘风格，自动生成论文结构/方法流程/实验架构图

订阅钩子:
  - post_write: 检测写作内容中的框架关键词，建议生成图表
  - pre_chart: 提供框架图模板

提供功能:
  - generate_framework_diagram: 论文整体结构图
  - generate_method_flowchart: 方法流程图
  - generate_experiment_architecture: 实验架构图
"""

import uuid
from typing import Any, Dict, List

from app.services.plugin_system import AcaSightPlugin


FRAMEWORK_KEYWORDS = {
    "framework", "architecture", "pipeline", "workflow", "methodology",
    "approach", "model", "system", "overview", "structure",
    "框架", "架构", "流程", "方法", "模型", "系统", "概述",
}

VALID_STYLES = {"hand-drawn", "clean", "sketch", "formal"}

TEMPLATE_LIBRARY = {
    "framework": {
        "name": "Paper Framework",
        "description": "Overall paper structure diagram",
        "default_style": "hand-drawn",
        "layout": "top-down",
        "placeholders": ["title", "sections", "connections"],
    },
    "method_flowchart": {
        "name": "Method Flowchart",
        "description": "Step-by-step method flow",
        "default_style": "hand-drawn",
        "layout": "left-to-right",
        "placeholders": ["steps", "decisions", "branches"],
    },
    "experiment_architecture": {
        "name": "Experiment Architecture",
        "description": "Component and connection diagram",
        "default_style": "hand-drawn",
        "layout": "layered",
        "placeholders": ["components", "connections", "data_flow"],
    },
}


class PaperFrameworkPlugin(AcaSightPlugin):
    """论文框架图草图生成插件"""

    async def on_load(self, config: dict) -> None:
        await super().on_load(config)
        self.register_hook("post_write", self._on_post_write)
        self.register_hook("pre_chart", self._on_pre_chart)
        self._default_style = config.get("default_style", "hand-drawn")

    async def on_enable(self) -> None:
        pass

    async def on_disable(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    # ── Hook Handlers ──

    async def _on_post_write(self, content: str, **kwargs) -> dict:
        """
        post_write 钩子处理器

        检查写作内容是否包含框架相关关键词，
        若匹配则建议生成对应的框架图。
        """
        if not content:
            return {"suggested": False, "reason": "empty_content"}

        matched_keywords = self._detect_framework_keywords(content)
        if not matched_keywords:
            return {"suggested": False, "reason": "no_framework_keywords"}

        suggestions = self._build_suggestions(matched_keywords, content)
        return {
            "suggested": True,
            "matched_keywords": list(matched_keywords),
            "suggestions": suggestions,
        }

    async def _on_pre_chart(self, chart_type: str = "", **kwargs) -> dict:
        """
        pre_chart 钩子处理器

        根据请求的 chart_type 提供对应的框架图模板。
        若 chart_type 为空则返回全部可用模板。
        """
        if not chart_type:
            return {
                "templates_available": True,
                "templates": TEMPLATE_LIBRARY,
            }

        template_key = chart_type if chart_type in TEMPLATE_LIBRARY else "framework"
        template = TEMPLATE_LIBRARY[template_key]
        return {
            "templates_available": True,
            "template": template,
            "chart_type": template_key,
        }

    # ── Public API (provides) ──

    async def generate_framework_diagram(
        self,
        paper_title: str,
        sections: list,
        style: str = "hand-drawn",
    ) -> dict:
        """
        生成论文整体结构图

        Args:
            paper_title: 论文标题
            sections: 章节列表，每项为 {"name": str, "subsections": list}
            style: 绘图风格 (hand-drawn / clean / sketch / formal)

        Returns:
            包含图表 JSON 规范的字典，供前端渲染
        """
        style = style if style in VALID_STYLES else self._default_style

        nodes = self._build_framework_nodes(paper_title, sections)
        edges = self._build_framework_edges(sections)

        diagram_id = str(uuid.uuid4())

        return {
            "diagram_id": diagram_id,
            "diagram_type": "framework",
            "style": style,
            "paper_title": paper_title,
            "spec": {
                "type": "directed_graph",
                "layout": "top-down",
                "nodes": nodes,
                "edges": edges,
            },
            "render_hints": {
                "font_family": "sketch" if style == "hand-drawn" else "sans-serif",
                "stroke_style": "rough" if style in ("hand-drawn", "sketch") else "solid",
                "fill_opacity": 0.85,
                "border_radius": 8 if style == "hand-drawn" else 2,
            },
            "metadata": {
                "section_count": len(sections),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        }

    async def generate_method_flowchart(
        self,
        method_steps: list,
        style: str = "hand-drawn",
    ) -> dict:
        """
        生成方法流程图

        Args:
            method_steps: 方法步骤列表，每项为 {"name": str, "type": str, "detail": str}
                          type 可选: process / decision / io / start_end
            style: 绘图风格

        Returns:
            包含流程图 JSON 规范的字典，供前端渲染
        """
        style = style if style in VALID_STYLES else self._default_style

        nodes = self._build_flowchart_nodes(method_steps)
        edges = self._build_flowchart_edges(method_steps)

        diagram_id = str(uuid.uuid4())

        return {
            "diagram_id": diagram_id,
            "diagram_type": "method_flowchart",
            "style": style,
            "spec": {
                "type": "flowchart",
                "layout": "left-to-right",
                "nodes": nodes,
                "edges": edges,
            },
            "render_hints": {
                "font_family": "sketch" if style == "hand-drawn" else "sans-serif",
                "stroke_style": "rough" if style in ("hand-drawn", "sketch") else "solid",
                "fill_opacity": 0.85,
                "node_shapes": {
                    "process": "rectangle",
                    "decision": "diamond",
                    "io": "parallelogram",
                    "start_end": "rounded_rectangle",
                },
            },
            "metadata": {
                "step_count": len(method_steps),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        }

    async def generate_experiment_architecture(
        self,
        components: list,
        connections: list,
        style: str = "hand-drawn",
    ) -> dict:
        """
        生成实验架构图

        Args:
            components: 组件列表，每项为 {"name": str, "type": str, "layer": int}
                        type 可选: dataset / model / module / output / tool
            connections: 连接列表，每项为 {"from": str, "to": str, "label": str, "type": str}
                         type 可选: data_flow / control / feedback
            style: 绘图风格

        Returns:
            包含架构图 JSON 规范的字典，供前端渲染
        """
        style = style if style in VALID_STYLES else self._default_style

        nodes = self._build_architecture_nodes(components)
        edges = self._build_architecture_edges(connections)

        layers = self._group_by_layer(components)

        diagram_id = str(uuid.uuid4())

        return {
            "diagram_id": diagram_id,
            "diagram_type": "experiment_architecture",
            "style": style,
            "spec": {
                "type": "architecture",
                "layout": "layered",
                "layers": layers,
                "nodes": nodes,
                "edges": edges,
            },
            "render_hints": {
                "font_family": "sketch" if style == "hand-drawn" else "sans-serif",
                "stroke_style": "rough" if style in ("hand-drawn", "sketch") else "solid",
                "fill_opacity": 0.85,
                "layer_spacing": 80,
                "component_shapes": {
                    "dataset": "cylinder",
                    "model": "hexagon",
                    "module": "rectangle",
                    "output": "document",
                    "tool": "gear",
                },
            },
            "metadata": {
                "component_count": len(components),
                "connection_count": len(connections),
                "layer_count": len(layers),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
            },
        }

    # ── Internal Helpers ──

    def _detect_framework_keywords(self, content: str) -> set:
        content_lower = content.lower()
        return {kw for kw in FRAMEWORK_KEYWORDS if kw in content_lower}

    def _build_suggestions(self, keywords: set, content: str) -> list:
        suggestions = []
        framework_words = {"framework", "architecture", "overview", "structure", "框架", "架构", "概述"}
        method_words = {"pipeline", "workflow", "methodology", "approach", "流程", "方法"}
        experiment_words = {"model", "system", "模型", "系统"}

        if keywords & framework_words:
            suggestions.append({
                "type": "framework",
                "action": "generate_framework_diagram",
                "reason": "Content describes a paper framework or architecture",
            })
        if keywords & method_words:
            suggestions.append({
                "type": "method_flowchart",
                "action": "generate_method_flowchart",
                "reason": "Content describes a method or workflow",
            })
        if keywords & experiment_words:
            suggestions.append({
                "type": "experiment_architecture",
                "action": "generate_experiment_architecture",
                "reason": "Content describes a model or system architecture",
            })

        return suggestions

    def _build_framework_nodes(self, title: str, sections: list) -> list:
        nodes = [{"id": "root", "label": title, "type": "title", "level": 0}]
        for i, section in enumerate(sections):
            sec_name = section if isinstance(section, str) else section.get("name", f"Section {i+1}")
            sec_id = f"section_{i}"
            nodes.append({"id": sec_id, "label": sec_name, "type": "section", "level": 1})
            if isinstance(section, dict) and "subsections" in section:
                for j, sub in enumerate(section["subsections"]):
                    sub_name = sub if isinstance(sub, str) else sub.get("name", f"Subsection {j+1}")
                    nodes.append({
                        "id": f"{sec_id}_sub_{j}",
                        "label": sub_name,
                        "type": "subsection",
                        "level": 2,
                    })
        return nodes

    def _build_framework_edges(self, sections: list) -> list:
        edges = []
        for i in range(len(sections)):
            edges.append({"source": "root", "target": f"section_{i}", "label": ""})
            if i > 0:
                edges.append({
                    "source": f"section_{i-1}",
                    "target": f"section_{i}",
                    "label": "next",
                    "style": "dashed",
                })
        return edges

    def _build_flowchart_nodes(self, steps: list) -> list:
        nodes = []
        for i, step in enumerate(steps):
            if isinstance(step, str):
                step = {"name": step, "type": "process", "detail": ""}
            node_id = f"step_{i}"
            nodes.append({
                "id": node_id,
                "label": step.get("name", f"Step {i+1}"),
                "type": step.get("type", "process"),
                "detail": step.get("detail", ""),
            })
        return nodes

    def _build_flowchart_edges(self, steps: list) -> list:
        edges = []
        for i in range(len(steps) - 1):
            step = steps[i] if isinstance(steps[i], dict) else {"name": steps[i], "type": "process"}
            edge = {
                "source": f"step_{i}",
                "target": f"step_{i+1}",
                "label": "",
            }
            if step.get("type") == "decision":
                edge["branches"] = {"yes": f"step_{i+1}", "no": f"step_{i+2}" if i+2 < len(steps) else "end"}
            edges.append(edge)
        return edges

    def _build_architecture_nodes(self, components: list) -> list:
        nodes = []
        for i, comp in enumerate(components):
            if isinstance(comp, str):
                comp = {"name": comp, "type": "module", "layer": 0}
            nodes.append({
                "id": f"comp_{i}",
                "label": comp.get("name", f"Component {i+1}"),
                "type": comp.get("type", "module"),
                "layer": comp.get("layer", 0),
            })
        return nodes

    def _build_architecture_edges(self, connections: list) -> list:
        edges = []
        for i, conn in enumerate(connections):
            if isinstance(conn, dict):
                edges.append({
                    "source": conn.get("from", ""),
                    "target": conn.get("to", ""),
                    "label": conn.get("label", ""),
                    "type": conn.get("type", "data_flow"),
                })
            elif isinstance(conn, (list, tuple)) and len(conn) >= 2:
                edges.append({
                    "source": conn[0],
                    "target": conn[1],
                    "label": conn[2] if len(conn) > 2 else "",
                    "type": "data_flow",
                })
        return edges

    def _group_by_layer(self, components: list) -> list:
        layer_map: Dict[int, List[Dict[str, Any]]] = {}
        for i, comp in enumerate(components):
            if isinstance(comp, str):
                comp = {"name": comp, "type": "module", "layer": 0}
            layer = comp.get("layer", 0)
            if layer not in layer_map:
                layer_map[layer] = []
            layer_map[layer].append({
                "id": f"comp_{i}",
                "label": comp.get("name", f"Component {i+1}"),
                "type": comp.get("type", "module"),
            })
        return [
            {"layer": layer, "components": layer_map[layer]}
            for layer in sorted(layer_map.keys())
        ]


__acasight_plugin__ = PaperFrameworkPlugin()
