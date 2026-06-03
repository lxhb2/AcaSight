"""Raman spectrum plot + peak fitting generator."""
import numpy as np
from typing import Optional
import structlog
from app.services.plot.spectrum_engine import (
    correct_baseline, smooth_data, detect_peaks, fit_peaks, generate_spectrum_fit_schema,
)

logger = structlog.get_logger()


def generate_raman_spectrum_schema(
    x_data: list[float],
    y_data: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for Raman spectrum (raw view, no fitting)."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)

    # Optional baseline correction
    baseline_method = config.get("baseline_method", None)
    baseline_result = None
    if baseline_method:
        baseline_result = correct_baseline(x, y, method=baseline_method, params=config.get("baseline_params", {}))
        y_display = np.array(baseline_result["y_corrected"])
    else:
        y_display = y

    # Optional smoothing
    smooth_method = config.get("smooth_method", None)
    if smooth_method:
        smooth_result = smooth_data(y_display, method=smooth_method, params=config.get("smooth_params", {}))
        y_display = np.array(smooth_result["y_smoothed"])

    traces = []

    # Original data
    traces.append({
        "type": "scatter",
        "mode": "lines",
        "x": x.tolist(),
        "y": y.tolist(),
        "name": "Original",
        "line": {"width": 1, "color": "#999"},
    })

    # Baseline
    if baseline_result:
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": baseline_result["baseline"],
            "name": "Baseline",
            "line": {"width": 1, "color": "#d62728", "dash": "dash"},
        })

    # Processed data
    if baseline_method or smooth_method:
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": y_display.tolist(),
            "name": "Processed",
            "line": {"width": 1.5, "color": "#1f77b4"},
        })

    # Multiple spectra stacking
    extra_spectra = config.get("extra_spectra", [])
    y_offset = config.get("y_offset", 1.2)
    for i, spec in enumerate(extra_spectra):
        offset = (i + 1) * y_offset
        spec_y = np.array(spec["y"], dtype=float)
        if baseline_method:
            br = correct_baseline(np.array(spec["x"]), spec_y, method=baseline_method, params=config.get("baseline_params", {}))
            spec_y = np.array(br["y_corrected"])
        spec_y_norm = spec_y / (spec_y.max() if spec_y.max() > 0 else 1) + offset
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": spec["x"],
            "y": spec_y_norm.tolist(),
            "name": spec.get("label", f"Spectrum {i+2}"),
            "line": {"width": 1, "color": spec.get("color", f"#{hash(str(i)) % 0xFFFFFF:06x}")},
        })

    x_label = config.get("x_label", "Raman Shift (cm⁻¹)")
    y_label = config.get("y_label", "Intensity (a.u.)")

    layout = {
        "xaxis": {"title": {"text": x_label}, "autorange": "reversed"},
        "yaxis": {"title": {"text": y_label}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "raman_spectrum",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }


def generate_raman_peak_fit_schema(
    x_data: list[float],
    y_data: list[float],
    peak_positions: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for Raman spectrum with multi-peak fitting."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)

    # Preprocessing
    baseline_method = config.get("baseline_method", "als")
    if baseline_method:
        br = correct_baseline(x, y, method=baseline_method, params=config.get("baseline_params", {}))
        y_processed = np.array(br["y_corrected"])
    else:
        y_processed = y

    smooth_method = config.get("smooth_method", None)
    if smooth_method:
        sr = smooth_data(y_processed, method=smooth_method, params=config.get("smooth_params", {}))
        y_processed = np.array(sr["y_smoothed"])

    # Peak fitting
    peak_type = config.get("peak_type", "pvoigt")
    fit_result = fit_peaks(x, y_processed, peak_positions, peak_type)

    if not fit_result.get("success", False):
        return {"error": fit_result.get("error", "Fitting failed"), "success": False}

    # Generate schema
    config["x_label"] = config.get("x_label", "Raman Shift (cm⁻¹)")
    config["y_label"] = config.get("y_label", "Intensity (a.u.)")
    schema = generate_spectrum_fit_schema(x, y_processed, fit_result, config)

    return {
        "success": True,
        "schema": schema,
        "fit_result": fit_result,
    }
