"""DOE plot generator: Pareto, main effects, interaction effects."""
import numpy as np
import structlog

logger = structlog.get_logger()


def generate_pareto_schema(
    effects: list[dict],
    config: dict,
) -> dict:
    """Generate PlotSchema for Pareto chart of standardized effects.

    Args:
        effects: [{"name": str, "effect": float, "significant": bool}]
        config: {"alpha_line": float, ...}
    """
    sorted_effects = sorted(effects, key=lambda x: abs(x["effect"]))

    names = [e["name"] for e in sorted_effects]
    values = [abs(e["effect"]) for e in sorted_effects]
    colors = ["#d62728" if e.get("significant", False) else "#1f77b4" for e in sorted_effects]

    traces = [{
        "type": "bar",
        "x": values,
        "y": names,
        "orientation": "h",
        "marker": {"color": colors},
        "name": "Standardized Effect",
    }]

    # Significance reference line
    alpha_line = config.get("alpha_line", None)
    shapes = []
    if alpha_line is not None:
        shapes.append({
            "type": "line",
            "x0": alpha_line, "x1": alpha_line,
            "y0": -0.5, "y1": len(names) - 0.5,
            "line": {"width": 2, "dash": "dash", "color": "#d62728"},
        })

    layout = {
        "xaxis": {"title": {"text": "Standardized Effect"}},
        "yaxis": {"title": {"text": ""}},
        "height": max(300, len(names) * 30 + 100),
        "showlegend": False,
        "shapes": shapes,
        "margin": {"l": 100, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "pareto",
        "traces": traces,
        "layout": layout,
        "export": {"width": 700, "height": max(300, len(names) * 30 + 100), "scale": 2},
    }


def generate_main_effects_schema(
    factors: list[dict],
    config: dict,
) -> dict:
    """Generate PlotSchema for main effects plot.

    Args:
        factors: [{"name": str, "levels": [float, ...], "means": [float, ...]}]
    """
    traces = []
    colors = ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B"]

    for i, factor in enumerate(factors):
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "x": factor["levels"],
            "y": factor["means"],
            "name": factor["name"],
            "line": {"width": 2, "color": colors[i % len(colors)]},
            "marker": {"size": 8, "color": colors[i % len(colors)]},
        })

    layout = {
        "xaxis": {"title": {"text": config.get("x_label", "Factor Level")}},
        "yaxis": {"title": {"text": config.get("y_label", "Mean Response")}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "main_effects",
        "traces": traces,
        "layout": layout,
        "export": {"width": 600, "height": 500, "scale": 2},
    }


def generate_interaction_schema(
    factor1_levels: list[float],
    factor2_levels: list[float],
    means_matrix: list[list[float]],
    factor1_name: str,
    factor2_name: str,
    config: dict,
) -> dict:
    """Generate PlotSchema for interaction effects plot.

    Args:
        factor1_levels: Levels of factor 1
        factor2_levels: Levels of factor 2
        means_matrix: Response means [factor2_level][factor1_level]
        factor1_name: Name of factor 1
        factor2_name: Name of factor 2
    """
    traces = []
    colors = ["#4C78A8", "#F58518", "#E45756", "#72B7B2"]

    for j, level in enumerate(factor2_levels):
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "x": factor1_levels,
            "y": [means_matrix[j][i] if i < len(means_matrix[j]) else 0 for i in range(len(factor1_levels))],
            "name": f"{factor2_name}={level}",
            "line": {"width": 2, "color": colors[j % len(colors)]},
            "marker": {"size": 8},
        })

    layout = {
        "xaxis": {"title": {"text": factor1_name}},
        "yaxis": {"title": {"text": config.get("y_label", "Mean Response")}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "interaction",
        "traces": traces,
        "layout": layout,
        "export": {"width": 600, "height": 500, "scale": 2},
    }
