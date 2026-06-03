"""FTIR spectrum plot generator."""
import numpy as np
import structlog
from app.services.plot.spectrum_engine import correct_baseline

logger = structlog.get_logger()


def generate_ftir_spectrum_schema(
    x_data: list[float],
    y_data: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for FTIR spectrum."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)

    # Mode: transmittance or absorbance
    mode = config.get("mode", "transmittance")
    if mode == "absorbance" and np.all(y > 0):
        # Convert transmittance to absorbance: A = -log10(T/100)
        y_display = -np.log10(y / 100)
    else:
        y_display = y

    # Baseline correction
    baseline_method = config.get("baseline_method", None)
    baseline = None
    if baseline_method:
        br = correct_baseline(x, y_display, method=baseline_method, params=config.get("baseline_params", {}))
        y_display = np.array(br["y_corrected"])
        baseline = br["baseline"]

    traces = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": y_display.tolist(),
            "name": mode.capitalize(),
            "line": {"width": 1.5, "color": "#1f77b4"},
        },
    ]
    if baseline is not None:
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": baseline,
            "name": "Baseline",
            "line": {"width": 1, "color": "#d62728", "dash": "dash"},
        })

    # Peak annotations
    peak_annotations = config.get("peak_annotations", [])
    for ann in peak_annotations:
        traces.append({
            "type": "scatter",
            "mode": "markers+text",
            "x": [ann.get("x", 0)],
            "y": [ann.get("y", 0)],
            "text": [ann.get("label", "")],
            "textposition": "top center",
            "marker": {"size": 6, "color": "#e74c3c"},
            "showlegend": False,
        })

    y_label = "Transmittance (%)" if mode == "transmittance" else "Absorbance (a.u.)"

    layout = {
        "xaxis": {"title": {"text": "Wavenumber (cm⁻¹)"}, "autorange": "reversed"},
        "yaxis": {"title": {"text": y_label}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "ftir_spectrum",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }
