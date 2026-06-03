"""Spectrum processing engine: baseline correction, smoothing, peak detection, fitting."""
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from scipy.optimize import curve_fit
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve
import structlog

logger = structlog.get_logger()


# === Baseline Correction ===

def baseline_als(y: np.ndarray, lam: float = 1e5, p: float = 0.01, niter: int = 10) -> np.ndarray:
    """Asymmetric Least Squares baseline estimation (Eilers & Boelens 2005)."""
    L = len(y)
    # Second-order difference matrix D (L-2 x L)
    D = diags([1, -2, 1], [0, 1, 2], shape=(L - 2, L)).toarray()
    H = lam * D.T.dot(D)
    w = np.ones(L)
    for _ in range(niter):
        W = diags(w, 0, shape=(L, L))
        Z = W + H
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y <= z)
    return z


def baseline_snip(y: np.ndarray, niter: int = 40) -> np.ndarray:
    """SNIP baseline estimation (Statistics-sensitive Non-linear Iterative Peak-clipping)."""
    z = np.copy(y).astype(float)
    for i in range(niter, 0, -1):
        for j in range(i, len(z) - i):
            z[j] = min(z[j], 0.5 * (z[j - i] + z[j + i]))
    return z


def baseline_poly(x: np.ndarray, y: np.ndarray, degree: int = 3) -> np.ndarray:
    """Polynomial baseline estimation."""
    coeffs = np.polyfit(x, y, degree)
    return np.polyval(coeffs, x)


def baseline_shirley(y: np.ndarray, max_iter: int = 50, tol: float = 1e-3) -> np.ndarray:
    """Shirley background for XPS spectra."""
    bg = np.zeros_like(y, dtype=float)
    y_left = y[0]
    y_right = y[-1]
    for _ in range(max_iter):
        bg_new = y_right + 0.5 * np.cumsum(y - bg)[::-1] / len(y) * (y_left - y_right)
        if np.allclose(bg, bg_new, atol=tol):
            break
        bg = bg_new
    return bg


def correct_baseline(x: np.ndarray, y: np.ndarray, method: str = "als", params: dict = None) -> dict:
    """Apply baseline correction and return corrected data + baseline."""
    params = params or {}
    if method == "als":
        baseline = baseline_als(y, lam=params.get("lam", 1e5), p=params.get("p", 0.01), niter=params.get("niter", 10))
    elif method == "snip":
        baseline = baseline_snip(y, niter=params.get("niter", 40))
    elif method == "poly":
        baseline = baseline_poly(x, y, degree=params.get("degree", 3))
    elif method == "shirley":
        baseline = baseline_shirley(y, max_iter=params.get("max_iter", 50))
    else:
        raise ValueError(f"Unknown baseline method: {method}")

    corrected = y - baseline
    return {
        "x": x.tolist(),
        "y_original": y.tolist(),
        "baseline": baseline.tolist(),
        "y_corrected": corrected.tolist(),
        "method": method,
    }


# === Smoothing ===

def smooth_savgol(y: np.ndarray, window_length: int = 11, polyorder: int = 3) -> np.ndarray:
    """Savitzky-Golay smoothing filter."""
    if window_length % 2 == 0:
        window_length += 1
    return savgol_filter(y, window_length, polyorder)


def smooth_moving_avg(y: np.ndarray, window: int = 5) -> np.ndarray:
    """Simple moving average smoothing."""
    kernel = np.ones(window) / window
    return np.convolve(y, kernel, mode="same")


def smooth_data(y: np.ndarray, method: str = "savgol", params: dict = None) -> dict:
    """Apply smoothing filter."""
    params = params or {}
    if method == "savgol":
        smoothed = smooth_savgol(y, window_length=params.get("window_length", 11), polyorder=params.get("polyorder", 3))
    elif method == "moving_avg":
        smoothed = smooth_moving_avg(y, window=params.get("window", 5))
    else:
        raise ValueError(f"Unknown smoothing method: {method}")

    return {
        "y_original": y.tolist(),
        "y_smoothed": smoothed.tolist(),
        "method": method,
    }


# === Peak Detection ===

def detect_peaks(x: np.ndarray, y: np.ndarray, params: dict = None) -> dict:
    """Detect peaks in spectrum data."""
    params = params or {}
    prominence = params.get("prominence", None)
    height = params.get("height", None)
    distance = params.get("distance", None)
    width = params.get("width", None)

    indices, properties = find_peaks(
        y,
        prominence=prominence,
        height=height,
        distance=distance,
        width=width,
    )

    peaks = []
    for i, idx in enumerate(indices):
        peak_info = {
            "index": int(idx),
            "x": float(x[idx]),
            "y": float(y[idx]),
        }
        if "prominences" in properties:
            peak_info["prominence"] = float(properties["prominences"][i])
        if "widths" in properties:
            peak_info["fwhm"] = float(properties["widths"][i])
        peaks.append(peak_info)

    return {
        "peaks": peaks,
        "n_peaks": len(peaks),
    }


# === Multi-Peak Fitting ===

def pseudo_voigt(x, amplitude, center, sigma, alpha=0.5):
    """Pseudo-Voigt function: alpha*Lorentzian + (1-alpha)*Gaussian."""
    gaussian = amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))
    lorentzian = amplitude / (1 + ((x - center) / sigma) ** 2)
    return alpha * lorentzian + (1 - alpha) * gaussian


def gaussian(x, amplitude, center, sigma):
    """Gaussian peak function."""
    return amplitude * np.exp(-((x - center) ** 2) / (2 * sigma ** 2))


def lorentzian(x, amplitude, center, sigma):
    """Lorentzian peak function."""
    return amplitude / (1 + ((x - center) / sigma) ** 2)


PEAK_FUNCTIONS = {
    "gaussian": gaussian,
    "lorentzian": lorentzian,
    "pvoigt": pseudo_voigt,
}


def fit_peaks(
    x: np.ndarray,
    y: np.ndarray,
    peak_positions: list[float],
    peak_type: str = "pvoigt",
    max_fev: int = 10000,
) -> dict:
    """Multi-peak fitting.

    Args:
        x: X data
        y: Y data
        peak_positions: Initial peak position guesses
        peak_type: 'gaussian', 'lorentzian', or 'pvoigt'
        max_fev: Maximum function evaluations

    Returns:
        Fitted parameters, fitted curve, residual, R²
    """
    n_peaks = len(peak_positions)
    peak_func = PEAK_FUNCTIONS.get(peak_type, pseudo_voigt)

    # Build multi-peak model
    def model(x, *params):
        result = np.zeros_like(x)
        for i in range(n_peaks):
            if peak_type == "pvoigt":
                amp, cen, sig, alpha = params[4*i], params[4*i+1], params[4*i+2], params[4*i+3]
                result += pseudo_voigt(x, amp, cen, sig, alpha)
            else:
                amp, cen, sig = params[3*i], params[3*i+1], params[3*i+2]
                result += peak_func(x, amp, cen, sig)
        return result

    # Initial guesses and bounds
    p0 = []
    bounds_lower = []
    bounds_upper = []

    for pos in peak_positions:
        # Estimate amplitude from data near peak position
        idx = np.argmin(np.abs(x - pos))
        amp_guess = max(y[idx], 1.0)

        if peak_type == "pvoigt":
            p0.extend([amp_guess, pos, 10.0, 0.5])
            bounds_lower.extend([0, -np.inf, 0.1, 0.0])
            bounds_upper.extend([np.inf, np.inf, 1000, 1.0])
        else:
            p0.extend([amp_guess, pos, 10.0])
            bounds_lower.extend([0, -np.inf, 0.1])
            bounds_upper.extend([np.inf, np.inf, 1000])

    try:
        popt, pcov = curve_fit(
            model, x, y, p0=p0,
            bounds=(bounds_lower, bounds_upper),
            maxfev=max_fev,
        )
    except RuntimeError as e:
        return {"error": f"Fitting failed: {str(e)}", "success": False}

    # Calculate fitted curve and R²
    y_fitted = model(x, *popt)
    ss_res = np.sum((y - y_fitted) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Extract individual peak parameters
    fitted_peaks = []
    for i in range(n_peaks):
        if peak_type == "pvoigt":
            amp, cen, sig, alpha = popt[4*i], popt[4*i+1], popt[4*i+2], popt[4*i+3]
            fitted_peaks.append({
                "amplitude": float(amp),
                "center": float(cen),
                "sigma": float(sig),
                "alpha": float(alpha),
                "fwhm": float(2 * sig * np.sqrt(2 * np.log(2)) * (1 - alpha) + 2 * sig * alpha),
            })
        else:
            amp, cen, sig = popt[3*i], popt[3*i+1], popt[3*i+2]
            fwhm = 2 * sig * np.sqrt(2 * np.log(2)) if peak_type == "gaussian" else 2 * sig
            fitted_peaks.append({
                "amplitude": float(amp),
                "center": float(cen),
                "sigma": float(sig),
                "fwhm": float(fwhm),
            })

    # Generate individual peak curves for plotting
    individual_curves = []
    for i in range(n_peaks):
        if peak_type == "pvoigt":
            amp, cen, sig, alpha = popt[4*i], popt[4*i+1], popt[4*i+2], popt[4*i+3]
            curve = pseudo_voigt(x, amp, cen, sig, alpha)
        else:
            amp, cen, sig = popt[3*i], popt[3*i+1], popt[3*i+2]
            curve = peak_func(x, amp, cen, sig)
        individual_curves.append(curve.tolist())

    return {
        "success": True,
        "r_squared": round(float(r_squared), 6),
        "fitted_peaks": fitted_peaks,
        "y_fitted": y_fitted.tolist(),
        "y_residual": (y - y_fitted).tolist(),
        "individual_curves": individual_curves,
        "peak_type": peak_type,
        "n_peaks": n_peaks,
    }


def generate_spectrum_fit_schema(
    x: np.ndarray,
    y: np.ndarray,
    fit_result: dict,
    config: dict,
) -> dict:
    """Generate PlotSchema for spectrum with peak fitting results."""
    traces = []
    colors = config.get("peak_colors", ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"])

    # Original data (scatter)
    traces.append({
        "type": "scatter",
        "mode": "lines",
        "x": x.tolist(),
        "y": y.tolist(),
        "name": "Original",
        "line": {"width": 1, "color": "#333"},
    })

    # Fitted curve
    if fit_result.get("y_fitted"):
        traces.append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": fit_result["y_fitted"],
            "name": "Fit (R²={:.4f})".format(fit_result.get("r_squared", 0)),
            "line": {"width": 1.5, "color": "#e74c3c", "dash": "dot"},
        })

    # Individual peak curves (filled)
    if fit_result.get("individual_curves"):
        for i, curve in enumerate(fit_result["individual_curves"]):
            color = colors[i % len(colors)]
            peak_info = fit_result["fitted_peaks"][i] if i < len(fit_result["fitted_peaks"]) else {}
            traces.append({
                "type": "scatter",
                "mode": "lines",
                "x": x.tolist(),
                "y": curve,
                "name": f"Peak {i+1}" + (f" ({peak_info.get('center', 0):.1f})" if peak_info else ""),
                "line": {"width": 1, "color": color},
                "fill": "tozeroy" if i == 0 else None,
                "fillcolor": color + "30",
            })

    x_label = config.get("x_label", "Raman Shift (cm⁻¹)")
    y_label = config.get("y_label", "Intensity")

    layout = {
        "xaxis": {"title": {"text": x_label}},
        "yaxis": {"title": {"text": y_label}},
        "height": 500,
        "showlegend": True,
        "margin": {"l": 60, "r": 20, "t": 30, "b": 50},
    }

    schema = {
        "_chart_type": "spectrum_fit",
        "traces": traces,
        "layout": layout,
        "export": {"width": 800, "height": 500, "scale": 2},
    }

    # Add residual subplot if requested
    if config.get("show_residual", True) and fit_result.get("y_residual"):
        schema["subplots"] = {
            "rows": 2,
            "cols": 1,
            "shared_xaxes": True,
            "shared_yaxes": False,
            "row_heights": [3, 1],
            "specs": [[{"secondary_y": False}], [{"secondary_y": False}]],
        }
        # Move original and fit traces to row 1
        for t in schema["traces"]:
            t["_row"] = 1
            t["_col"] = 1
        # Add residual trace in row 2
        schema["traces"].append({
            "type": "scatter",
            "mode": "lines",
            "x": x.tolist(),
            "y": fit_result["y_residual"],
            "name": "Residual",
            "line": {"width": 1, "color": "#7f7f7f"},
            "_row": 2,
            "_col": 1,
        })
        schema["layout"]["xaxis2"] = {"title": {"text": x_label}}
        schema["layout"]["yaxis2"] = {"title": {"text": "Residual"}}
        schema["layout"]["height"] = 600

    return schema
