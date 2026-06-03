"""Statistical analysis plot generator: ANOVA bar, correlation heatmap, PCA biplot."""
import numpy as np
from typing import Optional
import structlog

logger = structlog.get_logger()


def generate_anova_bar_schema(
    groups: list[dict],
    comparisons: list[dict],
    config: dict,
) -> dict:
    """Generate PlotSchema for ANOVA bar chart with letter annotations.

    Args:
        groups: [{"name": str, "mean": float, "sd": float, "n": int, "color": str}]
        comparisons: [{"group1": str, "group2": str, "significant": bool, "letters": str}]
        config: Plot configuration
    """
    traces = []

    names = [g["name"] for g in groups]
    means = [g["mean"] for g in groups]
    sds = [g.get("sd", 0) for g in groups]
    colors = [g.get("color", "#4C78A8") for g in groups]

    # Bar trace with error bars
    traces.append({
        "type": "bar",
        "x": names,
        "y": means,
        "error_y": {"type": "data", "array": sds, "visible": True, "width": 2},
        "marker": {"color": colors},
        "name": "Mean ± SD",
    })

    # Letter annotations for significance
    annotations = []
    for i, g in enumerate(groups):
        letter = ""
        for comp in comparisons:
            if comp.get("group1") == g["name"] or comp.get("group2") == g["name"]:
                letter = comp.get("letters", "")
                break
        if letter:
            annotations.append({
                "x": g["name"],
                "y": g["mean"] + g.get("sd", 0) + max(means) * 0.05,
                "text": letter,
                "showarrow": False,
                "font": {"size": 12, "color": "#000"},
            })

    # Significance stars
    y_max = max(m + s for m, s in zip(means, sds))
    star_annotations = []
    for comp in comparisons:
        if comp.get("significant", False):
            g1_idx = names.index(comp["group1"]) if comp["group1"] in names else None
            g2_idx = names.index(comp["group2"]) if comp["group2"] in names else None
            if g1_idx is not None and g2_idx is not None:
                y_star = y_max + y_max * 0.1
                star_annotations.append({
                    "x": comp["group1"],
                    "y": y_star,
                    "text": "",
                    "showarrow": False,
                })

    all_annotations = annotations + star_annotations

    layout = {
        "xaxis": {"title": {"text": config.get("x_label", "Group")}},
        "yaxis": {"title": {"text": config.get("y_label", "Value")}},
        "height": 500,
        "showlegend": False,
        "annotations": all_annotations,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "anova_bar",
        "traces": traces,
        "layout": layout,
        "export": {"width": 600, "height": 500, "scale": 2},
    }


def generate_correlation_heatmap_schema(
    variables: list[str],
    corr_matrix: list[list[float]],
    p_matrix: Optional[list[list[float]]],
    config: dict,
) -> dict:
    """Generate PlotSchema for correlation coefficient heatmap.

    Args:
        variables: Variable names
        corr_matrix: Correlation coefficient matrix (n x n)
        p_matrix: P-value matrix (optional, for significance stars)
        config: Plot configuration
    """
    n = len(variables)
    z = np.array(corr_matrix)

    # Build text annotations
    text = []
    for i in range(n):
        row = []
        for j in range(n):
            val = f"{z[i][j]:.2f}"
            if p_matrix:
                p = p_matrix[i][j]
                if p < 0.001:
                    val += "***"
                elif p < 0.01:
                    val += "**"
                elif p < 0.05:
                    val += "*"
            row.append(val)
        text.append(row)

    colorscale = config.get("colorscale", "RdBu_r")

    traces = [{
        "type": "heatmap",
        "z": z.tolist(),
        "x": variables,
        "y": variables,
        "text": text,
        "texttemplate": "%{text}",
        "textfont": {"size": 10},
        "colorscale": colorscale,
        "zmin": -1,
        "zmax": 1,
        "colorbar": {"title": "r", "thickness": 15},
    }]

    layout = {
        "xaxis": {"side": "bottom", "tickangle": -45},
        "yaxis": {"autorange": "reversed"},
        "height": max(400, n * 50 + 100),
        "margin": {"l": 80, "r": 20, "t": 30, "b": 80},
    }

    return {
        "_chart_type": "correlation_heatmap",
        "traces": traces,
        "layout": layout,
        "export": {"width": max(500, n * 50 + 100), "height": max(400, n * 50 + 100), "scale": 2},
    }


def generate_pca_biplot_schema(
    scores: list[list[float]],
    loadings: list[list[float]],
    variance_explained: list[float],
    group_labels: Optional[list[str]],
    variable_names: list[str],
    config: dict,
) -> dict:
    """Generate PlotSchema for PCA biplot (scores + loading vectors).

    Args:
        scores: PC scores (n_samples x 2)
        loadings: Loading vectors (n_variables x 2)
        variance_explained: [PC1_var%, PC2_var%]
        group_labels: Group label for each sample (optional)
        variable_names: Variable names for loading arrows
        config: Plot configuration
    """
    scores_arr = np.array(scores)
    loadings_arr = np.array(loadings)

    traces = []

    # Score scatter
    if group_labels:
        unique_groups = list(set(group_labels))
        colors = ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B", "#EECA3B"]
        for i, group in enumerate(unique_groups):
            mask = [j for j, g in enumerate(group_labels) if g == group]
            traces.append({
                "type": "scatter",
                "mode": "markers",
                "x": scores_arr[mask, 0].tolist(),
                "y": scores_arr[mask, 1].tolist(),
                "name": group,
                "marker": {"size": 8, "color": colors[i % len(colors)], "opacity": 0.7},
            })
    else:
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": scores_arr[:, 0].tolist(),
            "y": scores_arr[:, 1].tolist(),
            "name": "Samples",
            "marker": {"size": 8, "color": "#4C78A8", "opacity": 0.7},
        })

    # Loading vectors (arrows)
    scale = config.get("loading_scale", max(np.abs(scores_arr).max(), 1) * 0.8 / max(np.abs(loadings_arr).max(), 0.01))
    for i, name in enumerate(variable_names):
        if i < len(loadings_arr):
            traces.append({
                "type": "scatter",
                "mode": "lines+markers+text",
                "x": [0, loadings_arr[i, 0] * scale],
                "y": [0, loadings_arr[i, 1] * scale],
                "name": name,
                "text": ["", name],
                "textposition": "top center",
                "textfont": {"size": 9, "color": "#d62728"},
                "line": {"width": 1.5, "color": "#d62728"},
                "marker": {"size": 4, "color": "#d62728", "symbol": "arrow"},
                "showlegend": False,
            })

    pc1_var = variance_explained[0] if len(variance_explained) > 0 else 0
    pc2_var = variance_explained[1] if len(variance_explained) > 1 else 0

    layout = {
        "xaxis": {"title": {"text": f"PC1 ({pc1_var:.1f}%)"}, "zeroline": True, "zerolinewidth": 1, "zerolinecolor": "#ccc"},
        "yaxis": {"title": {"text": f"PC2 ({pc2_var:.1f}%)"}, "zeroline": True, "zerolinewidth": 1, "zerolinecolor": "#ccc", "scaleanchor": "x", "scaleratio": 1},
        "height": 600,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    return {
        "_chart_type": "pca_biplot",
        "traces": traces,
        "layout": layout,
        "export": {"width": 700, "height": 600, "scale": 2},
    }
