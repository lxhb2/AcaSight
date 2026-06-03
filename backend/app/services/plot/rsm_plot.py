"""Response Surface Methodology (RSM) 3D surface + contour plot generator."""
import numpy as np
from scipy.interpolate import griddata
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import structlog

logger = structlog.get_logger()


def generate_rsm_surface_schema(
    x_data: list[float],
    y_data: list[float],
    z_data: list[float],
    config: dict,
) -> dict:
    """
    Generate PlotSchema for 3D response surface + contour plot.

    Args:
        x_data: Factor 1 values
        y_data: Factor 2 values
        z_data: Response values
        config: Plot configuration dict
    """
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)
    z = np.array(z_data, dtype=float)

    grid_res = config.get("grid_resolution", 50)
    interpolation = config.get("interpolation", "cubic")
    colorscale = config.get("colorscale", "Viridis")
    show_data_points = config.get("show_data_points", True)
    mark_optimum = config.get("mark_optimum", True)
    x_label = config.get("x_label", "Factor A")
    y_label = config.get("y_label", "Factor B")
    z_label = config.get("z_label", "Response")
    fit_quadratic = config.get("fit_quadratic", False)

    # Grid interpolation
    xi = np.linspace(x.min(), x.max(), grid_res)
    yi = np.linspace(y.min(), y.max(), grid_res)
    XI, YI = np.meshgrid(xi, yi)

    if fit_quadratic:
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(np.column_stack([x, y]))
        model = LinearRegression().fit(X_poly, z)
        ZI = model.predict(poly.transform(np.column_stack([XI.ravel(), YI.ravel()])))
        ZI = ZI.reshape(XI.shape)
    else:
        ZI = griddata((x, y), z, (XI, YI), method=interpolation)

    # Build traces
    traces = []

    # 3D Surface trace
    surface_trace = {
        "type": "surface",
        "x": xi.tolist(),
        "y": yi.tolist(),
        "z": ZI.tolist(),
        "colorscale": colorscale,
        "opacity": 0.9,
        "contours": {
            "z": {"show": True, "usecolormap": True, "projectz": True}
        },
        "colorbar": {"title": z_label, "thickness": 15, "len": 0.8},
    }
    traces.append(surface_trace)

    # Data points on surface
    if show_data_points:
        scatter3d_trace = {
            "type": "scatter3d",
            "mode": "markers",
            "x": x.tolist(),
            "y": y.tolist(),
            "z": z.tolist(),
            "marker": {"size": 5, "color": "red", "symbol": "circle"},
            "name": "Experimental Points",
        }
        traces.append(scatter3d_trace)

    # Optimum point
    opt_info = None
    if mark_optimum:
        opt_idx = int(np.argmax(z))
        opt_x, opt_y, opt_z = float(x[opt_idx]), float(y[opt_idx]), float(z[opt_idx])
        opt_info = {"x": opt_x, "y": opt_y, "z": opt_z}
        traces.append({
            "type": "scatter3d",
            "mode": "markers",
            "x": [opt_x],
            "y": [opt_y],
            "z": [opt_z],
            "marker": {"size": 10, "color": "lime", "symbol": "diamond", "line": {"width": 2, "color": "black"}},
            "name": f"Optimum ({opt_z:.2f})",
        })

    layout = {
        "scene": {
            "xaxis": {"title": {"text": x_label}},
            "yaxis": {"title": {"text": y_label}},
            "zaxis": {"title": {"text": z_label}},
            "camera": {"eye": {"x": 1.5, "y": 1.5, "z": 0.8}},
        },
        "height": 600,
        "margin": {"l": 0, "r": 0, "t": 30, "b": 0},
    }

    schema = {
        "_chart_type": "rsm_surface3d",
        "traces": traces,
        "layout": layout,
        "export": {"width": 900, "height": 700, "scale": 2},
        "_optimum": opt_info,
    }
    return schema


def generate_contour_schema(
    x_data: list[float],
    y_data: list[float],
    z_data: list[float],
    config: dict,
) -> dict:
    """Generate PlotSchema for 2D contour plot."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)
    z = np.array(z_data, dtype=float)

    grid_res = config.get("grid_resolution", 50)
    interpolation = config.get("interpolation", "cubic")
    colorscale = config.get("colorscale", "Viridis")
    show_data_points = config.get("show_data_points", True)
    mark_optimum = config.get("mark_optimum", True)
    contour_levels = config.get("contour_levels", 15)
    show_labels = config.get("contour_showlabels", True)
    x_label = config.get("x_label", "Factor A")
    y_label = config.get("y_label", "Factor B")
    z_label = config.get("z_label", "Response")
    fit_quadratic = config.get("fit_quadratic", False)

    xi = np.linspace(x.min(), x.max(), grid_res)
    yi = np.linspace(y.min(), y.max(), grid_res)
    XI, YI = np.meshgrid(xi, yi)

    if fit_quadratic:
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(np.column_stack([x, y]))
        model = LinearRegression().fit(X_poly, z)
        ZI = model.predict(poly.transform(np.column_stack([XI.ravel(), YI.ravel()])))
        ZI = ZI.reshape(XI.shape)
    else:
        ZI = griddata((x, y), z, (XI, YI), method=interpolation)

    traces = []

    contour_trace = {
        "type": "contour",
        "x": xi.tolist(),
        "y": yi.tolist(),
        "z": ZI.tolist(),
        "colorscale": colorscale,
        "contours": {
            "showlabels": show_labels,
            "labelfont": {"size": 10},
            "start": None,
            "end": None,
            "size": None,
            "ncontours": contour_levels,
        },
        "colorbar": {"title": z_label, "thickness": 15},
        "line": {"width": 0.5},
    }
    traces.append(contour_trace)

    if show_data_points:
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": x.tolist(),
            "y": y.tolist(),
            "marker": {"size": 8, "color": "red", "symbol": "x"},
            "name": "Experimental Points",
        })

    if mark_optimum:
        opt_idx = int(np.argmax(z))
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": [float(x[opt_idx])],
            "y": [float(y[opt_idx])],
            "marker": {"size": 15, "color": "lime", "symbol": "star", "line": {"width": 2, "color": "black"}},
            "name": f"Optimum ({float(z[opt_idx]):.2f})",
        })

    layout = {
        "xaxis": {"title": {"text": x_label}},
        "yaxis": {"title": {"text": y_label}, "scaleanchor": "x", "scaleratio": 1},
        "height": 600,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    schema = {
        "_chart_type": "rsm_contour",
        "traces": traces,
        "layout": layout,
        "export": {"width": 700, "height": 600, "scale": 2},
    }
    return schema


def fit_response_model(
    x_data: list[float],
    y_data: list[float],
    z_data: list[float],
    degree: int = 2,
) -> dict:
    """Fit a polynomial response surface model and return equation + statistics."""
    x = np.array(x_data, dtype=float)
    y = np.array(y_data, dtype=float)
    z = np.array(z_data, dtype=float)

    poly = PolynomialFeatures(degree=degree)
    X_poly = poly.fit_transform(np.column_stack([x, y]))
    model = LinearRegression().fit(X_poly, z)

    r_squared = model.score(X_poly, z)
    coefficients = model.coef_.tolist()
    intercept = float(model.intercept_)

    # Find optimum for quadratic
    optimum = None
    if degree == 2:
        # For y = b0 + b1*x1 + b2*x2 + b3*x1^2 + b4*x1*x2 + b5*x2^2
        # dy/dx1 = b1 + 2*b3*x1 + b4*x2 = 0
        # dy/dx2 = b2 + b4*x1 + 2*b5*x2 = 0
        try:
            b = [intercept] + coefficients
            if len(b) >= 6:
                A = np.array([[2*b[3], b[4]], [b[4], 2*b[5]]])
                B = np.array([-b[1], -b[2]])
                opt = np.linalg.solve(A, B)
                opt_x1, opt_x2 = float(opt[0]), float(opt[1])
                if x.min() <= opt_x1 <= x.max() and y.min() <= opt_x2 <= y.max():
                    opt_z = model.predict(poly.transform([[opt_x1, opt_x2]]))[0]
                    optimum = {"x1": opt_x1, "x2": opt_x2, "y_pred": float(opt_z)}
        except np.linalg.LinAlgError:
            pass

    # Build equation string
    feature_names = poly.get_feature_names_out(["X1", "X2"])
    terms = [f"{coefficients[i]:.4f}*{feature_names[i+1]}" for i in range(len(coefficients)-1) if abs(coefficients[i+1]) > 1e-10]
    equation = f"Y = {intercept:.4f}"
    if terms:
        equation += " + " + " + ".join(terms)

    return {
        "equation": equation,
        "r_squared": round(r_squared, 6),
        "intercept": round(intercept, 6),
        "coefficients": [round(c, 6) for c in coefficients],
        "feature_names": feature_names.tolist(),
        "optimum": optimum,
        "degree": degree,
    }
