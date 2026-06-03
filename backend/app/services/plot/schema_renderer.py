"""Schema-driven renderer: PlotSchema JSON -> Plotly Figure -> Image export."""
import json
import uuid
from pathlib import Path
from typing import Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import structlog

logger = structlog.get_logger()

EXPORTS_DIR = Path(__file__).parent.parent.parent.parent / "static" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def schema_to_figure(schema: dict) -> go.Figure:
    """Convert a PlotSchema dict to a Plotly Figure object."""
    traces = schema.get("traces", [])
    layout = schema.get("layout", {})
    subplots = schema.get("subplots", None)

    if subplots:
        rows = subplots.get("rows", 1)
        cols = subplots.get("cols", 1)
        shared_xaxes = subplots.get("shared_xaxes", False)
        shared_yaxes = subplots.get("shared_yaxes", False)
        row_heights = subplots.get("row_heights", None)
        specs = subplots.get("specs", None)

        fig = make_subplots(
            rows=rows, cols=cols,
            shared_xaxes=shared_xaxes,
            shared_yaxes=shared_yaxes,
            row_heights=row_heights,
            specs=specs,
        )
        for trace_data in traces:
            row = trace_data.pop("_row", 1)
            col = trace_data.pop("_col", 1)
            trace = _build_trace(trace_data)
            fig.add_trace(trace, row=row, col=col)
    else:
        fig = go.Figure()
        for trace_data in traces:
            trace_data = dict(trace_data)
            trace = _build_trace(trace_data)
            fig.add_trace(trace)

    fig.update_layout(**layout)
    return fig


def _build_trace(data: dict) -> go.Trace:
    """Build a Plotly trace from trace data dict."""
    trace_type = data.pop("type", "scatter")
    # Map common trace types
    trace_classes = {
        "scatter": go.Scatter,
        "bar": go.Bar,
        "surface": go.Surface,
        "contour": go.Contour,
        "scatter3d": go.Scatter3d,
        "heatmap": go.Heatmap,
        "pie": go.Pie,
        "box": go.Box,
        "histogram": go.Histogram,
    }
    trace_cls = trace_classes.get(trace_type, go.Scatter)
    # Filter out internal keys
    clean_data = {k: v for k, v in data.items() if not k.startswith("_")}
    return trace_cls(**clean_data)


def export_figure(schema: dict, format: str = "png", width: int = 1200, height: int = 800, scale: int = 2) -> str:
    """Export a PlotSchema to image file. Returns the relative URL path."""
    fig = schema_to_figure(schema)

    # Apply export dimensions from schema if available
    export_config = schema.get("export", {})
    w = export_config.get("width", width)
    h = export_config.get("height", height)
    s = export_config.get("scale", scale)

    filename = f"{schema.get('_chart_type', 'chart')}_{uuid.uuid4().hex[:8]}.{format}"
    filepath = EXPORTS_DIR / filename

    fig.write_image(str(filepath), format=format, width=w, height=h, scale=s)

    return f"/static/exports/{filename}"


def schema_to_json(schema: dict) -> str:
    """Serialize PlotSchema to JSON string."""
    return json.dumps(schema, ensure_ascii=False, default=str)
