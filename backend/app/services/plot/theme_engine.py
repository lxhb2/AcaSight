"""Journal theme engine for academic plot styling."""
import json
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()

THEMES_DIR = Path(__file__).parent.parent.parent.parent / "themes"

def load_theme(theme_id: str) -> dict:
    """Load a journal theme by ID (e.g., 'nature', 'acs')."""
    theme_path = THEMES_DIR / f"{theme_id}.json"
    if not theme_path.exists():
        logger.warning("Theme not found, using default", theme_id=theme_id)
        return get_default_theme()
    with open(theme_path, "r", encoding="utf-8") as f:
        return json.load(f)

def list_themes() -> list[dict]:
    """List all available themes."""
    themes = []
    if THEMES_DIR.exists():
        for p in sorted(THEMES_DIR.glob("*.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    themes.append({"id": data.get("id", p.stem), "name": data.get("name", p.stem)})
            except Exception:
                pass
    return themes

def get_default_theme() -> dict:
    """Default academic theme."""
    return {
        "id": "default",
        "name": "Default Academic",
        "layout": {
            "font": {"family": "Arial", "size": 12, "color": "#333"},
            "paper_bgcolor": "#fff",
            "plot_bgcolor": "#fff",
            "xaxis": {"linewidth": 1, "showline": True, "linecolor": "#333", "tickwidth": 1},
            "yaxis": {"linewidth": 1, "showline": True, "linecolor": "#333", "tickwidth": 1},
            "margin": {"l": 60, "r": 20, "t": 30, "b": 50}
        },
        "width_mm": 89,
        "dpi": 300,
        "colors": ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B"]
    }

def apply_theme_to_schema(schema: dict, theme_id: str) -> dict:
    """Apply a theme to a PlotSchema, merging theme layout into schema layout."""
    theme = load_theme(theme_id)
    schema = dict(schema)  # shallow copy
    layout = dict(schema.get("layout", {}))
    theme_layout = theme.get("layout", {})
    # Deep merge theme layout (theme values override)
    for key, value in theme_layout.items():
        if isinstance(value, dict) and isinstance(layout.get(key), dict):
            layout[key] = {**layout[key], **value}
        else:
            layout[key] = value
    schema["layout"] = layout
    # Apply theme colors to traces if not explicitly set
    theme_colors = theme.get("colors", [])
    traces = list(schema.get("traces", []))
    for i, trace in enumerate(traces):
        if "line" in trace and "color" not in trace["line"] and theme_colors:
            trace = dict(trace)
            trace["line"] = dict(trace["line"])
            trace["line"]["color"] = theme_colors[i % len(theme_colors)]
            traces[i] = trace
    schema["traces"] = traces
    schema["_theme_id"] = theme_id
    return schema
