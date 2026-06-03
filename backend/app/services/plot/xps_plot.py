"""XPS spectrum plot + peak fitting generator."""
import numpy as np
from typing import Optional
import structlog
from app.services.plot.spectrum_engine import (
    correct_baseline, fit_peaks, generate_spectrum_fit_schema,
)

logger = structlog.get_logger()


def generate_xps_spectrum_schema(
    x_data: list[float],
    y_data: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for XPS spectrum (raw view)."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)

    # Shirley background by default for XPS
    baseline_method = config.get("baseline_method", "shirley")
    baseline_result = correct_baseline(x, y, method=baseline_method, params=config.get("baseline_params", {}))
    y_corrected = np.array(baseline_result["y_corrected"])

    traces = [
        {
            "type": "scatter",
            "mode": "markers",
            "x": x.tolist(),
            "y": y.tolist(),
            "name": "Raw Data",
            "marker": {"size": 3, "color": "#333"},
        },
        {
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": baseline_result["baseline"],
            "name": "Shirley BG",
            "line": {"width": 1, "color": "#d62728", "dash": "dash"},
        },
        {
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": y_corrected.tolist(),
            "name": "BG Corrected",
            "line": {"width": 1.5, "color": "#1f77b4"},
        },
    ]

    element = config.get("element", "C 1s")
    x_label = config.get("x_label", f"Binding Energy (eV)")
    y_label = config.get("y_label", "Intensity (a.u.)")

    layout = {
        "xaxis": {"title": {"text": x_label}, "autorange": "reversed"},
        "yaxis": {"title": {"text": y_label}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
        "title": {"text": f"XPS {element}", "font": {"size": 14}},
    }

    return {
        "_chart_type": "xps_spectrum",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }


def generate_xps_peak_fit_schema(
    x_data: list[float],
    y_data: list[float],
    peak_positions: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for XPS spectrum with multi-peak fitting."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)

    # Shirley background
    baseline_method = config.get("baseline_method", "shirley")
    br = correct_baseline(x, y, method=baseline_method, params=config.get("baseline_params", {}))
    y_corrected = np.array(br["y_corrected"])

    # Peak fitting
    peak_type = config.get("peak_type", "pvoigt")
    fit_result = fit_peaks(x, y_corrected, peak_positions, peak_type)

    if not fit_result.get("success", False):
        return {"error": fit_result.get("error", "Fitting failed"), "success": False}

    element = config.get("element", "C 1s")
    config["x_label"] = config.get("x_label", "Binding Energy (eV)")
    config["y_label"] = config.get("y_label", "Intensity (a.u.)")
    config["show_residual"] = config.get("show_residual", True)

    schema = generate_spectrum_fit_schema(x, y_corrected, fit_result, config)

    # Add raw data + background traces to the schema (in row 1)
    raw_trace = {
        "type": "scatter",
        "mode": "markers",
        "x": x.tolist(),
        "y": y.tolist(),
        "name": "Raw Data",
        "marker": {"size": 3, "color": "#999"},
        "_row": 1,
        "_col": 1,
    }
    bg_trace = {
        "type": "scatter",
        "mode": "lines",
        "x": x.tolist(),
        "y": br["baseline"],
        "name": "Shirley BG",
        "line": {"width": 1, "color": "#d62728", "dash": "dash"},
        "_row": 1,
        "_col": 1,
    }
    schema["traces"] = [raw_trace, bg_trace] + schema["traces"]

    return {
        "success": True,
        "schema": schema,
        "fit_result": fit_result,
    }
