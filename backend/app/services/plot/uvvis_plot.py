"""UV-Vis absorption spectrum + Tauc Plot generator."""
import numpy as np
import structlog

logger = structlog.get_logger()


def generate_uvvis_spectrum_schema(
    x_data: list[float],
    y_data: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for UV-Vis absorption spectrum."""
    x = np.array(x_data, dtype=float)  # wavelength in nm
    y = np.array(y_data, dtype=float)  # absorbance

    traces = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": y.tolist(),
            "name": "Absorbance",
            "line": {"width": 1.5, "color": "#1f77b4"},
        },
    ]

    # Multiple samples overlay
    extra_samples = config.get("extra_samples", [])
    colors = ["#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
    for i, sample in enumerate(extra_samples):
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": sample["x"],
            "y": sample["y"],
            "name": sample.get("label", f"Sample {i+2}"),
            "line": {"width": 1.5, "color": colors[i % len(colors)]},
        })

    layout = {
        "xaxis": {"title": {"text": "Wavelength (nm)"}},
        "yaxis": {"title": {"text": "Absorbance (a.u.)"}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "uvvis_spectrum",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }


def generate_tauc_plot_schema(
    x_data: list[float],
    y_data: list[float],
    config: dict,
) -> dict:
    """Generate Tauc Plot for band gap determination.

    For direct bandgap: (αhν)² vs hν
    For indirect bandgap: (αhν)^(1/2) vs hν
    """
    x = np.array(x_data, dtype=float)  # wavelength in nm
    y = np.array(y_data, dtype=float)  # absorbance (proportional to α)

    bandgap_type = config.get("bandgap_type", "direct")  # direct or indirect
    thickness = config.get("thickness", 1.0)  # sample thickness factor

    # Convert wavelength to energy: E(eV) = 1240 / λ(nm)
    hnu = 1240.0 / x

    # α ∝ absorbance, so (αhν)^n
    alpha = y * thickness
    if bandgap_type == "direct":
        y_tauc = (alpha * hnu) ** 2
        y_label = "(αhν)² (a.u.)"
    else:
        y_tauc = (alpha * hnu) ** 0.5
        y_label = "(αhν)^(1/2) (a.u.)"

    # Auto-fit linear region for bandgap estimation
    # Find the steepest linear region
    bandgap_estimate = None
    coeffs = None
    if config.get("estimate_bandgap", True) and len(y_tauc) > 10:
        # Simple approach: fit line to the rising edge
        dy = np.diff(y_tauc)
        # Find region of maximum slope
        window = min(20, len(dy) // 3)
        if window > 2:
            slopes = np.convolve(dy, np.ones(window) / window, mode="valid")
            max_slope_idx = np.argmax(slopes)
            start = max_slope_idx
            end = min(max_slope_idx + window, len(hnu) - 1)

            # Linear fit
            coeffs = np.polyfit(hnu[start:end], y_tauc[start:end], 1)
            # Bandgap = x-intercept
            if coeffs[0] != 0:
                bandgap_estimate = -coeffs[1] / coeffs[0]

    traces = [
        {
            "type": "scatter",
            "mode": "lines",
            "x": hnu.tolist(),
            "y": y_tauc.tolist(),
            "name": f"Tauc ({bandgap_type})",
            "line": {"width": 1.5, "color": "#1f77b4"},
        },
    ]

    # Add tangent line if bandgap estimated
    if bandgap_estimate is not None and bandgap_estimate > 0:
        x_line = np.linspace(bandgap_estimate, hnu.max(), 50)
        y_line = coeffs[0] * x_line + coeffs[1]
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x_line.tolist(),
            "y": y_line.tolist(),
            "name": f"Tangent (Eg={bandgap_estimate:.2f} eV)",
            "line": {"width": 1.5, "color": "#d62728", "dash": "dash"},
        })
        # Vertical line at bandgap
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": [bandgap_estimate, bandgap_estimate],
            "y": [0, max(y_tauc) * 0.5],
            "name": f"Eg = {bandgap_estimate:.2f} eV",
            "line": {"width": 1, "color": "#d62728", "dash": "dot"},
        })

    layout = {
        "xaxis": {"title": {"text": "Photon Energy (eV)"}},
        "yaxis": {"title": {"text": y_label}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    result = {
        "_chart_type": "tauc_plot",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }
    if bandgap_estimate is not None:
        result["_bandgap_estimate"] = round(bandgap_estimate, 4)
    return result
