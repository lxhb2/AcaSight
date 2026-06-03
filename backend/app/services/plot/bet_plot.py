"""BET adsorption isotherm + BJH pore size distribution plot generator."""
import numpy as np
from typing import Optional
import structlog

logger = structlog.get_logger()


def generate_bet_isotherm_schema(
    p_po_ads: list[float],
    v_ads: list[float],
    p_po_des: Optional[list[float]],
    v_des: Optional[list[float]],
    config: dict,
) -> dict:
    """Generate PlotSchema for BET adsorption isotherm."""
    traces = [
        {
            "type": "scatter",
            "mode": "lines+markers",
            "x": p_po_ads,
            "y": v_ads,
            "name": "Adsorption",
            "marker": {"size": 4, "color": "#1f77b4"},
            "line": {"width": 1.5, "color": "#1f77b4"},
        },
    ]

    if p_po_des and v_des:
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "x": p_po_des,
            "y": v_des,
            "name": "Desorption",
            "marker": {"size": 4, "color": "#d62728"},
            "line": {"width": 1.5, "color": "#d62728"},
        })

    layout = {
        "xaxis": {"title": {"text": "P/P₀"}},
        "yaxis": {"title": {"text": "Volume (cm³/g STP)"}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "bet_isotherm",
        "traces": traces,
        "layout": layout,
        "export": {"width": 700, "height": 500, "scale": 2},
    }


def generate_bjh_pore_schema(
    pore_diameter: list[float],
    dv_dd: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for BJH pore size distribution."""
    traces = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": pore_diameter,
            "y": dv_dd,
            "name": "BJH Distribution",
            "line": {"width": 1.5, "color": "#1f77b4"},
            "fill": "tozeroy",
            "fillcolor": "rgba(31, 119, 180, 0.2)",
        },
    ]

    layout = {
        "xaxis": {"title": {"text": "Pore Diameter (nm)"}, "type": "log"},
        "yaxis": {"title": {"text": "dV/dD (cm³/g·nm)"}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "bjh_pore",
        "traces": traces,
        "layout": layout,
        "export": {"width": 700, "height": 500, "scale": 2},
    }
