"""XRD stacked chart + PDF card stick diagram generator."""
import numpy as np
from typing import Optional
import structlog

logger = structlog.get_logger()


def generate_xrd_stacked_schema(
    xrd_datasets: list[dict],
    pdf_cards: list[dict],
    config: dict,
) -> dict:
    """
    Generate a PlotSchema for XRD stacked chart with PDF card stick diagrams.

    Args:
        xrd_datasets: [{"two_theta": [...], "intensity": [...], "label": str, "color": str}]
        pdf_cards: [{"two_theta": [...], "intensity": [...], "card_id": str, "color": str, "hkl": list[str]|None}]
        config: {"y_offset": float, "two_theta_range": [min, max], "line_width": float, "show_hkl": bool, ...}

    Returns:
        PlotSchema dict
    """
    y_offset = config.get("y_offset", 1.2)
    two_theta_range = config.get("two_theta_range", [10, 80])
    line_width = config.get("line_width", 0.8)
    show_hkl = config.get("show_hkl", False)
    stick_width = config.get("stick_width", 1.5)
    font_size = config.get("font_size", 9)
    show_y_ticks = config.get("show_y_ticks", False)

    traces = []
    annotations = []

    has_pdf_cards = len(pdf_cards) > 0

    # === XRD stacked curves (main subplot row 1) ===
    for i, dataset in enumerate(xrd_datasets):
        two_theta = np.array(dataset["two_theta"])
        intensity = np.array(dataset["intensity"], dtype=float)
        # Normalize and offset
        max_i = intensity.max() if intensity.max() > 0 else 1
        y_normalized = intensity / max_i
        y_offset_val = i * y_offset

        trace = {
            "type": "scatter",
            "mode": "lines",
            "x": two_theta.tolist(),
            "y": (y_normalized + y_offset_val).tolist(),
            "name": dataset.get("label", f"Sample {i+1}"),
            "line": {"width": line_width, "color": dataset.get("color", "#333333")},
            "hovertemplate": "2θ: %{x:.2f}°<br>Intensity: %{y:.2f}<extra></extra>",
            "_row": 1,
            "_col": 1,
        }
        traces.append(trace)

        # Sample label annotation
        annotations.append({
            "x": two_theta_range[1] + 1,
            "y": y_offset_val + 0.5,
            "text": dataset.get("label", f"Sample {i+1}"),
            "showarrow": False,
            "font": {"size": font_size},
            "xref": "x",
            "yref": "y",
            "row": 1,
            "col": 1,
        })

    # === PDF card stick diagrams (each card gets its own subplot row) ===
    for j, card in enumerate(pdf_cards):
        row_idx = j + 2  # rows are 1-indexed, XRD is row 1
        card_theta = np.array(card["two_theta"])
        card_intensity = np.array(card["intensity"], dtype=float)
        max_card_i = card_intensity.max() if card_intensity.max() > 0 else 1
        card_hkl = card.get("hkl", None)

        for k, (theta, rel_i) in enumerate(zip(card_theta, card_intensity / max_card_i)):
            stick_trace = {
                "type": "scatter",
                "mode": "lines",
                "x": [theta, theta],
                "y": [0, rel_i],
                "showlegend": k == 0,
                "name": card.get("card_id", f"PDF Card {j+1}"),
                "line": {"width": stick_width, "color": card.get("color", "#d62728")},
                "hoverinfo": "skip",
                "_row": row_idx,
                "_col": 1,
            }
            traces.append(stick_trace)

            # hkl annotation
            if show_hkl and card_hkl and k < len(card_hkl):
                annotations.append({
                    "x": theta,
                    "y": rel_i + 0.05,
                    "text": card_hkl[k],
                    "showarrow": False,
                    "font": {"size": max(font_size - 2, 6), "color": card.get("color", "#d62728")},
                    "textangle": -90,
                    "xref": f"x{row_idx if row_idx > 1 else ''}",
                    "yref": f"y{row_idx if row_idx > 1 else ''}",
                })

        # Card label
        annotations.append({
            "x": two_theta_range[1] + 1,
            "y": 0.5,
            "text": card.get("card_id", f"PDF Card {j+1}"),
            "showarrow": False,
            "font": {"size": font_size, "color": card.get("color", "#d62728")},
            "xref": f"x{row_idx if row_idx > 1 else ''}",
            "yref": f"y{row_idx if row_idx > 1 else ''}",
        })

    # === Build layout ===
    n_rows = 1 + len(pdf_cards)
    row_heights = [3] + [1] * len(pdf_cards)

    # Build subplot specs
    specs = [[{"secondary_y": False}] for _ in range(n_rows)]

    layout = {
        "showlegend": True,
        "legend": {"font": {"size": font_size}},
        "height": max(400, 200 + 120 * len(xrd_datasets) + 80 * len(pdf_cards)),
        "margin": {"l": 50, "r": 60, "t": 20, "b": 40},
    }

    # XRD subplot axis config
    layout["xaxis"] = {
        "title": {"text": "2θ (°)", "font": {"size": font_size + 1}},
        "range": two_theta_range,
        "showgrid": False,
        "linewidth": 1,
        "linecolor": "#333",
        "mirror": True,
    }
    layout["yaxis"] = {
        "showticklabels": show_y_ticks,
        "showgrid": False,
        "zeroline": False,
        "linewidth": 1,
        "linecolor": "#333",
        "mirror": True,
    }

    # PDF card subplot axes
    for j in range(len(pdf_cards)):
        row_idx = j + 2
        x_key = f"xaxis{row_idx}" if row_idx > 1 else "xaxis"
        y_key = f"yaxis{row_idx}" if row_idx > 1 else "yaxis"
        layout[x_key] = {
            "range": two_theta_range,
            "showgrid": False,
            "linewidth": 1,
            "linecolor": "#333",
            "mirror": True,
        }
        layout[y_key] = {
            "range": [0, 1.2],
            "showticklabels": False,
            "showgrid": False,
            "zeroline": False,
            "linewidth": 1,
            "linecolor": "#333",
            "mirror": True,
        }

    # Bottom x-axis label
    if len(pdf_cards) > 0:
        last_x_key = f"xaxis{n_rows}" if n_rows > 1 else "xaxis"
        layout[last_x_key]["title"] = {"text": "2θ (°)", "font": {"size": font_size + 1}}

    schema = {
        "_chart_type": "xrd_stacked",
        "traces": traces,
        "layout": layout,
        "subplots": {
            "rows": n_rows,
            "cols": 1,
            "shared_xaxes": True,
            "shared_yaxes": False,
            "row_heights": row_heights,
            "specs": specs,
        },
        "annotations": annotations,
        "export": {
            "width": 800,
            "height": max(400, 200 + 120 * len(xrd_datasets) + 80 * len(pdf_cards)),
            "scale": 2,
        },
    }
    return schema


def parse_jade_txt(content: str) -> dict:
    """Parse Jade-exported PDF card txt data.
    Format: 2theta  I(f)  d  hkl (space/tab separated)
    """
    lines = content.strip().split("\n")
    two_theta = []
    intensity = []
    hkl_list = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            try:
                two_theta.append(float(parts[0]))
                intensity.append(float(parts[1]))
                if len(parts) >= 4:
                    hkl_list.append(parts[3])
                else:
                    hkl_list.append("")
            except ValueError:
                continue
    return {
        "two_theta": two_theta,
        "intensity": intensity,
        "hkl": hkl_list if any(hkl_list) else None,
    }
