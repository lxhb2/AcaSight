"""TGA/DSC thermal analysis plot generator."""
import numpy as np
from typing import Optional
import structlog

logger = structlog.get_logger()


def generate_tga_dsc_schema(
    x_data: list[float],
    tga_data: list[float],
    dsc_data: Optional[list[float]],
    config: dict,
) -> dict:
    """Generate PlotSchema for TGA/DSC thermal analysis curves."""
    x = np.array(x_data, dtype=float)  # Temperature (°C)
    tga = np.array(tga_data, dtype=float)  # Weight (%)

    traces = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": tga.tolist(),
            "name": "TGA",
            "line": {"width": 1.5, "color": "#1f77b4"},
            "yaxis": "y",
        },
    ]

    # DTG curve (derivative of TGA)
    if config.get("show_dtg", True):
        dtg = np.gradient(tga, x)
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": dtg.tolist(),
            "name": "DTG",
            "line": {"width": 1, "color": "#2ca02c", "dash": "dot"},
            "yaxis": "y",
        })

    # DSC curve (right Y axis)
    if dsc_data:
        dsc = np.array(dsc_data, dtype=float)
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": dsc.tolist(),
            "name": "DSC",
            "line": {"width": 1.5, "color": "#d62728"},
            "yaxis": "y2",
        })

    # Weight loss step annotations
    step_annotations = config.get("step_annotations", [])
    for ann in step_annotations:
        traces.append({
            "type": "scatter",
            "mode": "markers+text",
            "x": [ann.get("temp", 0)],
            "y": [ann.get("weight", 0)],
            "text": [ann.get("label", "")],
            "textposition": "top center",
            "marker": {"size": 6, "color": "#e74c3c"},
            "showlegend": False,
        })

    layout = {
        "xaxis": {"title": {"text": "Temperature (°C)"}},
        "yaxis": {
            "title": {"text": "Weight (%)"},
            "side": "left",
        },
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 60, "t": 30, "b": 50},
    }

    if dsc_data:
        layout["yaxis2"] = {
            "title": {"text": "Heat Flow (mW)"},
            "side": "right",
            "overlaying": "y",
        }

    return {
        "_chart_type": "tga_dsc",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }
