"""
XRD_Analysis.py ? ?????? XRD ????????????
?? Jade (????) + Origin (??)
=======================================================
???
  1. ????  ? ?? .txt (??) / .raw (PANalytical) / .csv
  2. ????  ? ???Kalpha2 ???BKG ?????
  3. ????  ? ? ICDD PDF-4 ????????????
  4. ????  ? ?? Rietveld ????????
  5. ?????  ? ????????/?Minerals Engineering???
  6. ????  ? JSON ?? + PDF / PNG ??

???QClaw AI | ?????????????
"""

from __future__ import annotations
import os, sys, re, time, json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import warnings

import numpy as np
import pandas as pd

# ?? ?? ??????????????????????????????????????????????
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

# ?? ???? & ?? ??????????????????????????????????
from scipy.signal import savgol_filter, find_peaks
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import minimum_filter1d, gaussian_filter1d


# ??????????????????????????????????????????????????????
#  ????????????????? PDF ????
#  ??: ICDD PDF-4+ / AMCSD / Mineral Handbook
#  ??: (2theta_CuKalpha, hkl, d_A, I%)
# ??????????????????????????????????????????????????????
MINERAL_LIBRARY: Dict[str, Dict] = {

    "alpha-FeOOH_Goethite_???": {
        "formula":     "alpha-FeOOH",
        "system":      "Orthorhombic",
        "space_group": "Pbnm",
        "a": 4.608, "b": 9.951, "c": 3.021,
        "peaks": [
            (21.22, "110", 4.185, 100),
            (33.22, "120", 2.694, 65),
            (36.65, "130", 2.451, 80),
            (39.50, "021", 2.280, 30),
            (41.18, "140", 2.192, 50),
            (53.24, "150", 1.720, 45),
            (59.00, "200", 1.565, 35),
            (61.38, "200", 1.511, 40),
        ],
        "color": "#D32F2F",
        "description": "?????????????????????",
    },

    "Fe2O3_Hematite_???": {
        "formula":     "Fe2O3",
        "system":      "Trigonal",
        "space_group": "R-3c",
        "a": 5.036, "b": 5.036, "c": 13.749,
        "peaks": [
            (24.14, "012", 3.686, 40),
            (33.16, "104", 2.700, 100),
            (35.65, "110", 2.518, 80),
            (39.48, "113", 2.281, 60),
            (40.85, "202", 2.208, 30),
            (49.48, "024", 1.840, 50),
            (54.09, "116", 1.694, 70),
            (57.62, "108", 1.599, 45),
            (62.45, "214", 1.486, 50),
        ],
        "color": "#E53935",
        "description": "?????????????????????????",
    },

    "Fe3O4_Magnetite_???": {
        "formula":     "Fe3O4",
        "system":      "Cubic (Spinel)",
        "space_group": "Fd-3m",
        "a": 8.396,
        "peaks": [
            (18.29, "111", 4.850, 30),
            (30.10, "220", 2.967, 100),
            (35.43, "311", 2.531, 80),
            (37.06, "222", 2.423, 20),
            (43.10, "400", 2.098, 60),
            (53.40, "422", 1.715, 40),
            (56.94, "511", 1.616, 50),
            (62.52, "440", 1.486, 45),
        ],
        "color": "#6A1B9A",
        "description": "Fe(II,III)????????????????????",
    },

    "?-FeOOH_Lepidocrocite_???": {
        "formula":     "?-FeOOH",
        "system":      "Orthorhombic",
        "space_group": "Cmcm",
        "a": 3.870, "b": 12.50, "c": 3.070,
        "peaks": [
            (14.14, "020", 6.260, 100),
            (27.05, "110", 3.295, 90),
            (36.43, "130", 2.463, 70),
            (47.18, "200", 1.925, 60),
            (53.90, "060", 1.700, 40),
        ],
        "color": "#AD1457",
        "description": "?-FeOOH???????????/???????",
    },

    "SiO2_Quartz_??": {
        "formula":     "SiO2",
        "system":      "Trigonal",
        "space_group": "P3211",
        "a": 4.913, "b": 4.913, "c": 5.405,
        "peaks": [
            (20.86, "100", 4.257, 100),
            (26.64, "101", 3.343, 35),
            (39.47, "110", 2.282, 12),
            (42.45, "102", 2.129, 10),
            (50.14, "112", 1.819, 18),
            (55.00, "202", 1.668, 10),
            (60.00, "200", 1.541, 12),
        ],
        "color": "#1565C0",
        "description": "??????????????????????????",
    },

    "(Mg,Fe)5Al2Si3O10_Clinochlore_????": {
        "formula":     "(Mg,Fe)5Al2Si3O10(OH)8",
        "system":      "Monoclinic",
        "space_group": "C2/m",
        "peaks": [
            (12.54, "001", 7.057, 100),
            (19.84, "110", 4.472, 80),
            (25.18, "111", 3.537, 70),
            (35.00, "131", 2.562, 50),
            (45.90, "220", 1.976, 40),
        ],
        "color": "#2E7D32",
        "description": "????????????????",
    },

    "CaMg(CO3)2_Dolomite_???": {
        "formula":     "CaMg(CO3)2",
        "system":      "Trigonal",
        "space_group": "R-3",
        "a": 4.808, "b": 4.808, "c": 16.010,
        "peaks": [
            (24.12, "012", 3.690, 25),
            (30.96, "104", 2.887, 100),
            (37.42, "110", 2.402, 40),
            (44.52, "202", 2.034, 45),
            (51.08, "108", 1.787, 35),
        ],
        "color": "#795548",
        "description": "??????????????????????",
    },

    "FeS2_Pyrite_???": {
        "formula":     "FeS2",
        "system":      "Cubic",
        "space_group": "Pa-3",
        "a": 5.418,
        "peaks": [
            (28.51, "111", 3.129, 100),
            (33.08, "200", 2.706, 85),
            (37.09, "210", 2.423, 90),
            (40.78, "211", 2.212, 80),
            (47.30, "220", 1.921, 55),
            (56.28, "311", 1.633, 50),
        ],
        "color": "#FF6F00",
        "description": "????????????????????",
    },

    "CuS_Covellite_????": {
        "formula":     "CuS",
        "system":      "Hexagonal",
        "space_group": "P63/mmc",
        "a": 3.792, "b": 3.792, "c": 16.340,
        "peaks": [
            (27.76, "002", 3.212, 100),
            (29.28, "101", 3.048, 80),
            (31.78, "102", 2.814, 70),
            (47.88, "110", 1.899, 60),
            (59.30, "108", 1.558, 45),
        ],
        "color": "#0277BD",
        "description": "CuS ??????????????????",
    },

    "Cu2CO3(OH)2_Malachite_???": {
        "formula":     "Cu2CO3(OH)2",
        "system":      "Monoclinic",
        "space_group": "P21/c",
        "a": 9.502, "b": 11.974, "c": 3.240,
        "peaks": [
            (14.90, "110", 5.943, 100),
            (24.12, "220", 3.689, 45),
            (31.38, "131", 2.850, 80),
            (35.78, "221", 2.507, 70),
            (38.59, "240", 2.331, 55),
        ],
        "color": "#00838F",
        "description": "??????????????????",
    },

    "CoOOH_Heterogenite_???": {
        "formula":     "CoOOH",
        "system":      "Trigonal",
        "space_group": "R-3m",
        "a": 2.855, "b": 2.855, "c": 13.150,
        "peaks": [
            (32.60, "101", 2.745, 100),
            (38.20, "104", 2.354, 80),
            (52.10, "110", 1.755, 60),
            (61.50, "116", 1.509, 50),
        ],
        "color": "#4527A0",
        "description": "Co(III)??????????????????",
    },

    "CaSO4?2H2O_Gypsum_??": {
        "formula":     "CaSO4?2H2O",
        "system":      "Monoclinic",
        "space_group": "C2/c",
        "peaks": [
            (11.62, "020", 7.612, 100),
            (20.87, "021", 4.253, 55),
            (29.11, "111", 3.066, 50),
            (31.17, "041", 2.869, 35),
            (40.64, "141", 2.220, 25),
        ],
        "color": "#90A4AE",
        "description": "??????????????????????????",
    },

    "CaCO3_Calcite_???": {
        "formula":     "CaCO3",
        "system":      "Trigonal",
        "space_group": "R-3c",
        "a": 4.990, "b": 4.990, "c": 17.060,
        "peaks": [
            (23.05, "012", 3.858, 20),
            (29.40, "104", 3.036, 100),
            (39.48, "110", 2.281, 20),
            (43.15, "202", 2.095, 18),
            (47.12, "108", 1.927, 12),
        ],
        "color": "#BDBDBD",
        "description": "?????????????????????????",
    },

    "Cu2O_Cuprite_???": {
        "formula":     "Cu2O",
        "system":      "Cubic",
        "space_group": "Pn-3m",
        "a": 4.270,
        "peaks": [
            (29.56, "110", 3.020, 100),
            (36.42, "111", 2.465, 75),
            (42.30, "200", 2.135, 65),
            (61.36, "220", 1.513, 50),
        ],
        "color": "#BF360C",
        "description": "???????????????????????",
    },

    "Al2SiO5_Andalusite_???": {
        "formula":     "Al2SiO5",
        "system":      "Orthorhombic",
        "space_group": "Pnnm",
        "peaks": [
            (21.03, "110", 4.225, 50),
            (25.94, "111", 3.433, 100),
            (27.80, "020", 3.208, 55),
            (35.20, "121", 2.548, 65),
            (39.30, "200", 2.292, 45),
            (42.60, "131", 2.121, 50),
        ],
        "color": "#BF360C",
        "description": "???????????????",
    },

    "Al2SiO5_Kyanite_???": {
        "formula":     "Al2SiO5",
        "system":      "Triclinic",
        "space_group": "P-1",
        "peaks": [
            (12.10, "100", 7.311, 40),
            (20.90, "110", 4.248, 55),
            (25.50, "020", 3.492, 100),
            (30.80, "112", 2.902, 60),
            (35.10, "022", 2.555, 50),
        ],
        "color": "#0277BD",
        "description": "??????????????/?????",
    },
}


# ??????????????????????????????????????????????????????
#  Publication color schemes (colorblind-safe)
# ??????????????????????????????????????????????????????
PUB_COLORS = [
    "#1A1A1A",  # 0: black
    "#E64A19",  # 1: deep orange
    "#1565C0",  # 2: blue
    "#2E7D32",  # 3: green
    "#7B1FA2",  # 4: purple
    "#00838F",  # 5: cyan
    "#F57F17",  # 6: gold
    "#C62828",  # 7: dark red
    "#00695C",  # 8: dark teal
    "#4527A0",  # 9: deep violet
    "#37474F",  # 10: blue grey
    "#D84315",  # 11: burnt orange
]


# ??????????????????????????????????????????????????????
#  Journal figure standards
# ??????????????????????????????????????????????????????
JOURNAL_STYLE = {
    "default": {
        "figsize":     (8, 5.5),
        "fontsize":    11,
        "linewidth":   1.2,
        "tick_width":  0.8,
        "labelpad":    4,
        "tick_dir":    "in",
        "minor_ticks": True,
    },
    "Minerals Engineering": {
        "figsize":     (8, 5.5),
        "fontsize":    11,
        "linewidth":   1.2,
        "tick_width":  0.8,
        "labelpad":    4,
        "tick_dir":    "in",
        "minor_ticks": True,
        "frame_alpha": 0.8,
    },
    "Metallurgy": {         # ???/??????
        "figsize":     (8, 5.5),
        "fontsize":    10.5,
        "linewidth":   1.0,
        "tick_width":  0.7,
        "labelpad":    4,
        "tick_dir":    "in",
        "minor_ticks": True,
    },
    "CNS": {               # Nature / Cell / Science
        "figsize":     (9, 6),
        "fontsize":    12,
        "linewidth":   1.4,
        "tick_width":  1.0,
        "labelpad":    5,
        "tick_dir":    "in",
        "minor_ticks": True,
    },
    "Chinese Journal": {    # ??????
        "figsize":     (8, 5.5),
        "fontsize":    10.5,
        "linewidth":   1.0,
        "tick_width":  0.7,
        "labelpad":    4,
        "tick_dir":    "in",
        "minor_ticks": True,
        "use_tex":     False,
    },
}


# ??????????????????????????????????????????????????????
#  DATA LOADING
# ??????????????????????????????????????????????????????

def load_xrd_txt(path: str) -> pd.DataFrame:
    """?????? XRD .txt / .csv / .dat ??"""
    df = pd.read_csv(path, sep=r"\s+", header=None, skiprows=1,
                     names=["two_theta", "intensity"], engine="python",
                     on_bad_lines="skip")
    df = df.apply(pd.to_numeric, errors="coerce").dropna()
    df = df.reset_index(drop=True)
    df["two_theta"] = df["two_theta"].round(4)
    print(f"  [LOAD] {os.path.basename(path)}: {len(df)} pts, "
          f"2theta={df['two_theta'].min():.2f}?{df['two_theta'].max():.2f}?, "
          f"I_max={df['intensity'].max():.0f} cps")
    return df


def load_xrd_raw(path: str) -> pd.DataFrame:
    """?? PANalytical .raw ??????FI ????"""
    import struct
    with open(path, "rb") as f:
        raw = f.read()

    header_size = int.from_bytes(raw[4:8], "little")
    meas_str = raw[header_size:].split(b"\x00")[0].decode(
        "latin1", errors="replace")
    meas_str = re.sub(r"[^a-zA-Z0-9\s\-:.]", " ", meas_str).strip()

    # ???????
    data_offset = None
    for i in range(header_size + 64, len(raw) - 4, 4):
        val = struct.unpack("<I", raw[i:i + 4])[0]
        if 50 <= val <= 2000:
            data_offset = i
            break

    if data_offset is None:
        raise ValueError("??? .raw ???????????????? .txt ??")

    # ?? counts?uint32 LE?
    counts = []
    i = data_offset
    while i + 4 <= len(raw):
        val = struct.unpack("<I", raw[i:i + 4])[0]
        if val > 0:
            counts.append(val)
        i += 4

    # ???????????? 10.0?
    m = re.search(r"StartAngle\s*[:=]?\s*([\d.]+)", meas_str, re.I)
    start_angle = float(m.group(1)) if m else 10.0

    two_theta = np.arange(start_angle,
                          start_angle + len(counts) * 0.01,
                          0.01)[:len(counts)]
    df = pd.DataFrame({"two_theta": two_theta, "intensity": counts})
    print(f"  [LOAD .raw] {os.path.basename(path)}: {len(df)} pts, "
          f"2theta={df['two_theta'].min():.2f}?{df['two_theta'].max():.2f}?")
    return df


def load_xrd_auto(path: str) -> pd.DataFrame:
    """???????? XRD"""
    ext = Path(path).suffix.lower()
    if ext in {".txt", ".csv", ".dat", ".dx"}:
        return load_xrd_txt(path)
    elif ext == ".raw":
        return load_xrd_raw(path)
    else:
        raise ValueError(f"??????: {ext} | ??: .txt/.csv/.dat/.raw")


# ??????????????????????????????????????????????????????
#  DATA PROCESSING
# ??????????????????????????????????????????????????????

def smooth_savgol(y: np.ndarray, window: int = 9, poly: int = 3) -> np.ndarray:
    """Savitzky-Golay ??"""
    if window > len(y):
        window = len(y) // 2 * 2 + 1
    return savgol_filter(y, window, poly)


def smooth_gaussian(y: np.ndarray, sigma: float = 1.2) -> np.ndarray:
    """Gaussian ??"""
    return gaussian_filter1d(y.astype(float), sigma=sigma)


def background_als(y: np.ndarray, lam: float = 5e4,
                    p: float = 0.001, niter: int = 10) -> np.ndarray:
    """
    Asymmetric Least Squares Smoothing ? ??????
    lam: ?????????????
    p:   ??????0.001 = ???????????
    """
    from scipy.sparse import diags, linalg as sp_linalg
    L = len(y)
    y_arr = np.asarray(y, dtype=np.float64)

    # Tridiagonal second-derivative: d?z/dx? ? z[i-1] - 2z[i] + z[i+1]
    diagonals = [np.full(L - 1, 1.0), np.full(L, -2.0), np.full(L - 1, 1.0)]
    offsets   = [-1, 0, 1]
    L_op = diags(diagonals, offsets, shape=(L, L), format='csr')
    LTL  = L_op.T @ L_op          # (L, L) sparse

    w = np.ones(L, dtype=np.float64)

    for _ in range(niter):
        W = diags(w, shape=(L, L), format='csr')
        try:
            z = sp_linalg.spsolve(LTL * lam + W, y_arr)
        except Exception:
            z = np.zeros(L)
        d = y_arr - z
        d_neg = d < 0
        w[d_neg]  = p * np.exp(d[d_neg] * 2)
        w[~d_neg] = np.exp(-d[~d_neg] * 10)
        w = w / (w.max() + 1e-20) * 1e6

    z = np.clip(z, 0, None)   # background must be non-negative
    bg = gaussian_filter1d(z.astype(float), sigma=2)
    return bg


def background_rolling_min(y: np.ndarray,
                            window: int = 301) -> Tuple[np.ndarray, np.ndarray]:
    """????? + ?????ALS ??????"""
    bg = minimum_filter1d(y.astype(float), size=window, mode="reflect")
    t = np.linspace(0, 1, len(bg))
    spl = UnivariateSpline(t, bg, s=len(bg) * 0.05)
    bg_s = spl(t)
    y_corr = np.maximum(y - bg_s, 0)
    return bg_s, y_corr


def remove_kalpha2(x: np.ndarray, y: np.ndarray,
                   delta: float = 0.03) -> np.ndarray:
    """Kalpha2 ????Cu Kalpha, delta2theta ? 0.03??"""
    y2 = y.copy().astype(float)
    for i in range(len(x)):
        j = np.searchsorted(x, x[i] + delta)
        if j < len(y):
            y2[i] = y[i] - 0.5 * y[j] if y[j] < y[i] * 1.5 else y[i]
    return np.maximum(y2, 0)


# ??????????????????????????????????????????????????????
#  PEAK DETECTION
# ??????????????????????????????????????????????????????

def find_peaks_2theta(
    x: np.ndarray,
    y: np.ndarray,
    y_bkg: np.ndarray,
    height_ratio: float = 0.03,
    prominence: float = 0.008,
    distance: int = 12,
    width_min: int = 3,
) -> List[Dict]:
    """
    ????????????????
    height_ratio: ???????????
    prominence:   ???????????
    ??: [{"two_theta": float, "intensity": float, "prominence": float, ...}, ...]
    """
    y_net = np.maximum(y - y_bkg, 0)
    y_norm = y_net / max(y_net.max(), 1)

    peaks, props = find_peaks(
        y_norm,
        height=height_ratio,
        prominence=prominence,
        distance=distance,
        width=width_min,
    )
    result = []
    for i, idx in enumerate(peaks):
        result.append({
            "two_theta":    round(float(x[idx]), 4),
            "intensity":    round(float(y_net[idx]), 2),
            "intensity_raw": round(float(y[idx]), 2),
            "norm":         round(float(y_norm[idx]), 4),
            "prominence":   round(float(props["prominences"][i]), 4),
            "width":        round(float(props["widths"][i]) * (x[1] - x[0]), 3),
            "left_idx":     int(props["left_ips"][i]) if "left_ips" in props else idx - 2,
            "right_idx":    int(props["right_ips"][i]) if "right_ips" in props else idx + 2,
        })
    result.sort(key=lambda p: -p["intensity"])
    return result


# ??????????????????????????????????????????????????????
#  PHASE MATCHING
# ??????????????????????????????????????????????????????

def match_phases(
    peaks: List[Dict],
    library: Dict = MINERAL_LIBRARY,
    tol_2theta: float = 0.28,
    min_matched: int = 2,
) -> List[Dict]:
    """
    ???????? vs ???
    tol_2theta: 2theta ?????????? ?0.28?????????????
    min_matched: ??????
    ??: ????????????
    """
    results = []
    for mname, info in library.items():
        m_peaks = info["peaks"]
        matched = []
        for ep in peaks:
            for lp in m_peaks:
                d2t = abs(ep["two_theta"] - lp[0])
                if d2t <= tol_2theta:
                    matched.append({
                        "exp_2theta":   ep["two_theta"],
                        "lib_2theta":   lp[0],
                        "hkl":          lp[1],
                        "d_A":          lp[2],
                        "I_rel":        lp[3],
                        "delta2theta":         round(d2t, 4),
                    })
                    break  # ???????????

        if len(matched) >= min_matched:
            # ????????? / ??? * ?????? * (1 - ??delta2theta???)
            score = (
                len(matched) / len(m_peaks)
                * np.mean([m["I_rel"] for m in matched]) / 100
                * (1 - np.mean([abs(m["delta2theta"]) for m in matched]) / tol_2theta)
            )
            results.append({
                "name":        mname,
                "formula":     info.get("formula", ""),
                "system":      info.get("system", ""),
                "color":       info.get("color", "#888888"),
                "peaks":       matched,
                "n_matched":   len(matched),
                "n_total":     len(m_peaks),
                "score":       round(float(score), 4),
                "description": info.get("description", ""),
            })

    results.sort(key=lambda r: -r["score"])
    return results


# ??????????????????????????????????????????????????????
#  QUANTIFICATION (Simplified Rietveld ? Peak Area Ratio)
# ??????????????????????????????????????????????????????

def quantify_phases(
    x: np.ndarray,
    y_net: np.ndarray,
    matched_phases: List[Dict],
    peak_width_fwhm: float = 0.18,
) -> Dict[str, float]:
    """
    ?? Rietveld ???????????????
    ?? Pseudo-Voigt ?????Gaussian ???
    ??: {mineral_short_name: wt%}
    """
    from scipy.stats import norm

    areas = {}
    for phase in matched_phases:
        name = phase["name"]
        if name not in MINERAL_LIBRARY:
            continue
        peaks_lib = MINERAL_LIBRARY[name]["peaks"]
        synth = np.zeros_like(x)
        sigma = peak_width_fwhm / 2.35482

        for (pos, hkl, d, I) in peaks_lib:
            idx = np.searchsorted(x, pos)
            if 0 < idx < len(x) - 1:
                g = norm.pdf(x, loc=pos, scale=sigma)
                g_norm = g / g.max() * I
                synth += g_norm

        area = np.trapz(synth, x)
        areas[name.split("_")[0]] = area  # short key

    total = sum(areas.values())
    if total <= 0:
        return {}
    return {k: round(v / total * 100, 2) for k, v in areas.items()}


# ??????????????????????????????????????????????????????
#  PUBLICATION-QUALITY PLOTTING
# ??????????????????????????????????????????????????????

def _apply_style(ax, style: Dict):
    """Apply journal style to an Axes object"""
    for sp in ax.spines.values():
        sp.set_linewidth(style["tick_width"])
        sp.set_color("black")
    ax.tick_params(
        direction=style["tick_dir"], axis="both", which="major",
        length=5, width=style["tick_width"],
        labelsize=style["fontsize"] - 1,
        top=True, right=True,
    )
    if style.get("minor_ticks", True):
        ax.tick_params(which="minor", length=2.5,
                       width=style["tick_width"] * 0.6,
                       top=True, right=True)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(2))

    ax.grid(which="major", linestyle="-", linewidth=0.4,
            color="#AAAAAA", alpha=0.6)
    ax.grid(which="minor", linestyle=":", linewidth=0.3,
            color="#BBBBBB", alpha=0.4)
    ax.set_axisbelow(True)
    for tick in ax.get_xticklabels() + ax.get_yticklabels():
        tick.set_fontname("DejaVu Sans")
        tick.set_fontsize(style["fontsize"] - 1)


def plot_xrd(
    x: np.ndarray,
    y_raw: np.ndarray,
    y_proc: np.ndarray,
    y_bkg: np.ndarray,
    matched_phases: List[Dict],
    output_path: str,
    sample_name: str = "Y-2",
    journal: str = "Minerals Engineering",
    dpi: int = 600,
    fmt: str = "png",
    show_phase_bands: bool = True,
    show_peak_labels: bool = True,
    show_background: bool = False,
    show_inset_waxs: bool = False,
) -> str:
    """
    ??? XRD ????????
    journal: "Minerals Engineering" | "Metallurgy" | "CNS" | "Chinese Journal"
    """
    st = JOURNAL_STYLE.get(journal, JOURNAL_STYLE["default"])
    fig, ax = plt.subplots(figsize=st["figsize"], dpi=dpi)

    # ?? ??????% of max?????????????????????????
    y_n = y_proc / max(y_proc.max(), 1) * 100
    y_raw_n = y_raw / max(y_raw.max(), 1) * 100
    y_bg_n = y_bkg / max(y_raw.max(), 1) * 100

    # ?? ??? ??????????????????????????????????????
    if show_background:
        ax.fill_between(x, 0, y_bg_n, color="#C8D8E8",
                        alpha=0.45, label="Background", zorder=1)
        ax.plot(x, y_bg_n, color="#5588AA",
                linewidth=0.8, linestyle="--", zorder=2)

    # ?? ????????????????????????????????????
    ax.plot(x, y_raw_n, color="#AAAAAA",
            linewidth=0.6, alpha=0.5, zorder=2)

    # ?? ??? ???????????????????????????????????????
    ax.fill_between(x, 0, y_n, color="#3A7ABD", alpha=0.18, zorder=3)
    ax.plot(x, y_n, color="#1A3A6B",
            linewidth=st["linewidth"], zorder=4, label=sample_name)

    # ?? ???? ?????????????????????????????????????
    handles = []
    labels_list = []
    colors = iter(PUB_COLORS[1:])

    for phase in matched_phases[:8]:
        c = next(colors)
        pks = phase["peaks"]
        handles.append(mpatches.Patch(facecolor=c, alpha=0.7,
                                       label=phase["name"]))
        labels_list.append(phase["name"])

        if show_phase_bands:
            for p in pks:

                p2t = p["exp_2theta"]
                # ??????????????
                idx = np.searchsorted(x, p2t)
                h_at_peak = y_n[idx] if idx < len(y_n) else 0
                ax.axvline(p2t, ymin=0, ymax=h_at_peak / 110,
                           color=c, linewidth=0.7,
                           linestyle=":", alpha=0.7, zorder=3)

        # ?????
        if show_peak_labels and pks:
            top = max(pks, key=lambda pp: pp["I_rel"])
            ax.annotate(
                f"{phase['name']}\n({top['hkl']})",
                xy=(top["exp_2theta"], 88),
                xytext=(top["exp_2theta"] + 0.8, 72),
                fontsize=6.5,
                color=c,
                fontfamily="DejaVu Sans",
                arrowprops=dict(arrowstyle="->", color=c, lw=0.7),
                ha="left",
                rotation=0,
                bbox=dict(boxstyle="round,pad=0.2",
                          facecolor="white", alpha=0.7, edgecolor=c, lw=0.5),
            )

    # ?? ???? ?????????????????????????????????????
    _apply_style(ax, st)
    ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=st["fontsize"],
                  labelpad=st["labelpad"])
    ax.set_ylabel("Intensity (% of maximum)", fontsize=st["fontsize"],
                  labelpad=st["labelpad"])
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(-2, 112)

    # ?? 2theta ?????????????????????????????????
    for angle in [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]:
        ax.axvline(angle, color="#DDDDDD", linewidth=0.3,
                   linestyle="-", zorder=1)

    # ?? ?? ?????????????????????????????????????????
    ax.legend(handles=handles,
              loc="upper right",
              fontsize=7.5,
              framealpha=0.9,
              edgecolor="gray",
              fancybox=False,
              ncol=1,
              borderaxespad=0.3,
              labelspacing=0.4,
              handlelength=1.2,
              handletextpad=0.4,
              columnspacing=0.5,
              title="Phases identified",
              title_fontsize=8)

    # ?? ?? ?????????????????????????????????????????
    ax.set_title(
        f"XRD Pattern of {sample_name}\n"
        f"Copper-Cobalt Ore Leaching Residue",
        fontsize=st["fontsize"] + 1,
        fontweight="bold",
        pad=10,
    )

    # ?? ???????? ??????????????????????????????
    if journal == "Minerals Engineering":
        caption = (
            "Fig. XRD diffraction pattern of copper-cobalt leaching residue. "
            "Cu Kalpha radiation (lambda = 1.5406 ?). "
            "Phases: " + ", ".join(p["name"] for p in matched_phases[:5]) + "."
        )
        ax.text(0.01, -0.16, caption,
                transform=ax.transAxes, fontsize=7.5,
                fontfamily="DejaVu Sans", style="italic",
                va="top", wrap=True)

    plt.tight_layout(rect=[0, 0.04, 1, 0.97])
    plt.savefig(output_path, dpi=dpi, format=fmt,
                bbox_inches="tight")
    plt.close(fig)
    print(f"  [PLOT] ? {output_path}")
    return output_path


def plot_xrd_comparison(
    data_dict: Dict[str, pd.DataFrame],
    output_path: str,
    matched_phases_all: Optional[Dict[str, List[Dict]]] = None,
    journal: str = "Minerals Engineering",
    show_legend: bool = True,
    offset_step: float = 20.0,
    dpi: int = 600,
) -> str:
    """
    ??? XRD ????Y???????? Origin ????
    data_dict: {sample_name: DataFrame(two_theta, intensity)}
    matched_phases_all: {sample_name: matched_phases}
    """
    st = JOURNAL_STYLE.get(journal, JOURNAL_STYLE["default"])
    fig, ax = plt.subplots(figsize=(10, 5 + len(data_dict) * 0.6), dpi=dpi)

    ref_x = list(data_dict.values())[0]["two_theta"].values

    for idx, (name, df) in enumerate(data_dict.items()):
        x = df["two_theta"].values
        y = df["intensity"].values
        y_n = y / max(y.max(), 1) * 100
        offset = idx * offset_step
        y_shifted = y_n + offset

        ax.plot(x, y_shifted,
                color=PUB_COLORS[idx % len(PUB_COLORS)],
                linewidth=st["linewidth"],
                label=name,
                zorder=3)
        ax.fill_between(x, offset, y_shifted,
                        color=PUB_COLORS[idx % len(PUB_COLORS)],
                        alpha=0.12, zorder=2)
        # Y???
        ax.text(x.min() - 0.6, offset + 50,
                name, fontsize=9, va="center", ha="right",
                color=PUB_COLORS[idx % len(PUB_COLORS)], fontweight="bold")

    _apply_style(ax, st)
    ax.set_xlim(ref_x.min(), ref_x.max())
    ax.set_ylim(-10, len(data_dict) * offset_step + 10)
    ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=st["fontsize"])
    ax.set_ylabel("Intensity (a.u., offset)", fontsize=st["fontsize"])
    if show_legend:
        ax.legend(loc="upper right", fontsize=9,
                  framealpha=0.9, fancybox=False)
    ax.set_title("XRD Patterns ? Copper-Cobalt Leaching Residues",
                 fontsize=st["fontsize"] + 1, fontweight="bold", pad=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, format="png", bbox_inches="tight")
    plt.close(fig)
    print(f"  [PLOT] Comparison ? {output_path}")
    return output_path


def plot_phase_pie(
    quantification: Dict[str, float],
    output_path: str,
    journal: str = "Minerals Engineering",
    dpi: int = 600,
) -> str:
    """????????? Rietveld ???"""
    if not quantification:
        print("  [SKIP] No quantification data")
        return ""

    st = JOURNAL_STYLE.get(journal, JOURNAL_STYLE["default"])
    labels = list(quantification.keys())
    sizes = list(quantification.values())
    # ?????
    labels_short = [l.split("_")[0] for l in labels]

    # ????
    colors = []
    for name in labels:
        if name in MINERAL_LIBRARY and MINERAL_LIBRARY[name].get("color"):
            colors.append(MINERAL_LIBRARY[name]["color"])
        else:
            colors.append(PUB_COLORS[len(colors) % len(PUB_COLORS)])

    fig, ax = plt.subplots(figsize=(7, 7), dpi=dpi)
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels_short,
        colors=colors,
        autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
        pctdistance=0.75,
        startangle=90,
        wedgeprops=dict(linewidth=0.8, edgecolor="white"),
        textprops=dict(fontsize=9, fontfamily="DejaVu Sans"),
        explode=[0.02] * len(sizes),
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.set_title("Phase Quantification (wt%)\nSimplified Rietveld",
                 fontsize=st["fontsize"] + 1, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, format="png", bbox_inches="tight")
    plt.close(fig)
    print(f"  [PLOT] Pie chart ? {output_path}")
    return output_path


def plot_peak_table(
    peaks: List[Dict],
    matched_phases: List[Dict],
    output_path: str,
    sample_name: str = "Y-2",
) -> str:
    """Generate peak position table (PNG)"""
    if not peaks:
        print("  [SKIP] No peaks to tabulate")
        return ""
    fig, ax = plt.subplots(figsize=(12, max(3, len(peaks[:25]) * 0.4 + 1)))
    ax.axis("off")

    col_labels = ["#", r"$2\theta$ (?)", "I (a.u.)",
                  "Prominence", "Matched Phase", "hkl", r"$\Delta 2\theta$ (?)", "d (?)"]

    # ??????
    rows = []
    for i, pk in enumerate(peaks[:25], 1):
        phase_name = ""
        hkl_cell = ""
        d_cell = ""
        delta_cell = ""
        for ph in matched_phases:
            for mp in ph["peaks"]:
                if abs(mp["exp_2theta"] - pk["two_theta"]) < 0.05:
                    phase_name = ph["name"].split("_")[-1]
                    hkl_cell = mp["hkl"]
                    d_cell = f"{mp['d_A']:.3f}"
                    delta_cell = f"{mp['delta2theta']:.3f}"
                    break
            if phase_name:
                break
        rows.append([
            str(i),
            f"{pk['two_theta']:.2f}",
            f"{pk['intensity']:.0f}",
            f"{pk['prominence']:.3f}",
            phase_name,
            hkl_cell,
            delta_cell,
            d_cell,
        ])

    table = ax.table(
        cellText=rows,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.6)

    # ????
    for j in range(len(col_labels)):
        table[0, j].set_facecolor("#2C3E50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    for i in range(len(rows)):
        bg = "#EBF5FB" if i % 2 == 0 else "white"
        for j in range(len(col_labels)):
            table[i + 1, j].set_facecolor(bg)

    ax.set_title(f"Peak Table ? {sample_name} XRD Analysis",
                 fontsize=11, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, format="png", bbox_inches="tight")
    plt.close(fig)
    print(f"  [PLOT] Peak table ? {output_path}")
    return output_path


# ??????????????????????????????????????????????????????
#  MAIN ANALYSIS PIPELINE
# ??????????????????????????????????????????????????????

def analyze_xrd(
    data_path: str,
    output_dir: Optional[str] = None,
    sample_name: str = "Y-2",
    smooth_window: int = 9,
    smooth_poly: int = 3,
    background_method: str = "rolling",   # "ALS" or "rolling"
    journal: str = "Minerals Engineering",
    peak_height_ratio: float = 0.025,
    peak_prominence: float = 0.005,
    peak_tolerance: float = 0.30,
    rietveld_width: float = 0.18,
    dpi: int = 600,
    run_quantification: bool = True,
    verbose: bool = True,
) -> Dict:
    """
    XRD ????????

    Parameters
    ----------
    data_path         : XRD ??????
    output_dir         : ??????????????/xrd_output/?
    sample_name        : ????????????????
    smooth_window/poly : SG ????
    background_method  : "ALS" (??) ? "rolling"
    journal            : ??????
    peak_height_ratio  : ????????????? %?
    peak_prominence    : ??????????
    peak_tolerance     : ?????????
    rietveld_width     : ???? FWHM???
    dpi                : ?????
    run_quantification : ????????

    Returns
    -------
    report: dict???????
    """
    t0 = time.time()
    dp = Path(data_path)
    out_dir = Path(output_dir) if output_dir else dp.parent / "xrd_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  XRD Analysis ? Cu/Co Leaching Residue")
    print(f"  Sample : {sample_name}")
    print(f"  Data   : {dp.name}")
    print(f"  Output : {out_dir}")
    print(f"  Style  : {journal}")
    print(f"{sep}\n")

    # ?? 1. ???? ???????????????????????????????????
    print("[Step 1/7] Loading data ...")
    df = load_xrd_auto(str(dp))
    x = df["two_theta"].values.astype(np.float64)
    y_raw = df["intensity"].values.astype(np.float64)

    # ?? 2. ?? & Kalpha2 ?? ????????????????????????????
    print("[Step 2/7] Preprocessing ...")
    y_sm = smooth_savgol(y_raw, window=smooth_window, poly=smooth_poly)
    y_kalpha = remove_kalpha2(x, y_sm)
    print(f"  [SMOOTH] SG(w={smooth_window}, p={smooth_poly})")
    print(f"  [Kalpha2]    Removed (delta2theta=0.03?)")

    # ?? 3. ???? ???????????????????????????????????
    print("[Step 3/7] Background subtraction ...")
    if background_method == "ALS":
        y_bkg = background_als(y_kalpha)
    else:
        y_bkg, _ = background_rolling_min(y_kalpha)
    y_net = np.maximum(y_kalpha.astype(float) - y_bkg, 0)
    print(f"  [BACKGROUND] {background_method} method applied")
    print(f"  [NET] Max intensity: {y_net.max():.1f} (bg-corrected)")

    # ?? 4. ?? ???????????????????????????????????????
    print("[Step 4/7] Peak detection ...")
    peaks = find_peaks_2theta(
        x, y_raw, y_bkg,
        height_ratio=peak_height_ratio,
        prominence=peak_prominence,
        distance=12,
    )
    print(f"  [PEAKS] Found {len(peaks)} peaks "
          f"(height ? {peak_height_ratio*100:.0f}%, promin. ? {peak_prominence:.3f})")
    if verbose and peaks:
        print("  Top 10 peaks:")
        for pk in peaks[:10]:
            print(f"    2theta={pk['two_theta']:.2f}?  "
                  f"I={pk['intensity']:.0f}  prom.={pk['prominence']:.3f}")

    # ?? 5. ???? ???????????????????????????????????
    print("[Step 5/7] Phase matching ...")
    matched = match_phases(peaks, tol_2theta=peak_tolerance, min_matched=2)
    print(f"  [PHASES] Identified {len(matched)} candidate phases")
    for ph in matched[:6]:
        print(f"    ? {ph['name']:<45} "
              f"(matched {ph['n_matched']}/{ph['n_total']} peaks, "
              f"score={ph['score']:.4f})")

    # ?? 6. ?? ???????????????????????????????????????
    quantification = {}
    if run_quantification and matched:
        print("[Step 6/7] Phase quantification ...")
        quantification = quantify_phases(
            x, y_net, matched,
            peak_width_fwhm=rietveld_width,
        )
        print(f"  [QUANT] Simplified Rietveld (peak area ratio):")
        for k, v in quantification.items():
            print(f"    {k:<20}: {v:6.2f} wt%")
        total_q = sum(quantification.values())
        print(f"    {'TOTAL':<20}: {total_q:6.2f} wt%")

    # ?? 7. ?? ???????????????????????????????????????
    print("[Step 7/7] Generating figures ...")

    # 7a: ???
    fig_main = out_dir / f"{sample_name}_XRD_main.{fmt_from_journal(journal)}"
    plot_xrd(
        x, y_raw, y_net, y_bkg, matched,
        output_path=str(fig_main),
        sample_name=sample_name,
        journal=journal,
        dpi=dpi,
    )

    # 7b: ???
    fig_table = out_dir / f"{sample_name}_peak_table.png"
    plot_peak_table(peaks, matched, str(fig_table), sample_name=sample_name)

    # 7c: ????
    fig_pie = ""
    if quantification:
        fig_pie = plot_phase_pie(
            quantification,
            str(out_dir / f"{sample_name}_phase_pie.png"),
            journal=journal,
        )

    # ?? 8. ?? JSON ?? ?????????????????????????????
    elapsed = time.time() - t0
    report = {
        "sample": sample_name,
        "data_file": str(dp),
        "analysis_time_s": round(elapsed, 2),
        "data_summary": {
            "n_points": int(len(df)),
            "two_theta_range": [float(x.min()), float(x.max())],
            "step_size": float(np.mean(np.diff(x))),
            "max_intensity_raw": float(y_raw.max()),
            "max_intensity_net": float(y_net.max()),
            "n_peaks_detected": len(peaks),
        },
        "preprocessing": {
            "smoothing": f"SG(w={smooth_window}, p={smooth_poly})",
            "kalpha2_removal": True,
            "background_method": background_method,
        },
        "peaks": peaks[:30],
        "phases_identified": [
            {
                "name": p["name"],
                "formula": p["formula"],
                "system": p["system"],
                "n_matched_peaks": p["n_matched"],
                "score": p["score"],
                "description": p["description"],
            }
            for p in matched
        ],
        "quantification": quantification,
        "output_files": {
            "main_figure": str(fig_main),
            "peak_table": str(fig_table),
            "pie_chart": str(fig_pie) if fig_pie else None,
        },
        "plot_settings": {
            "journal": journal,
            "dpi": dpi,
            "wavelength": "Cu Kalpha 1.5406 ?",
        },
    }

    report_path = out_dir / f"{sample_name}_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  [REPORT] JSON ? {report_path}")

    print(f"\n{sep}")
    print(f"  [OK] Analysis complete in {elapsed:.1f}s")
    print(f"  ? Output: {out_dir}")
    print(f"{sep}\n")

    return report


def fmt_from_journal(journal: str) -> str:
    """??????????"""
    if journal == "Minerals Engineering":
        return "eps"
    return "png"


# ??????????????????????????????????????????????????????
#  BATCH PROCESSING
# ??????????????????????????????????????????????????????

def batch_analyze(
    data_dir: str,
    output_dir: str,
    sample_prefix: str = "",
    pattern: str = "*.txt",
    **kwargs,
) -> List[Dict]:
    """????????? XRD ??"""
    import glob
    files = glob.glob(os.path.join(data_dir, pattern))
    results = []
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        if sample_prefix and not name.startswith(sample_prefix):
            name = f"{sample_prefix}_{name}"
        try:
            r = analyze_xrd(fp, output_dir, sample_name=name, **kwargs)
            results.append(r)
        except Exception as e:
            print(f"  [ERROR] {fp}: {e}")
    return results


# ??????????????????????????????????????????????????????
#  STANDALONE RUN
# ??????????????????????????????????????????????????????
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="XRD Analysis for Cu/Co Leaching Residue")
    parser.add_argument("data", help="XRD data file (.txt/.raw)")
    parser.add_argument("-o", "--output", default=None, help="Output directory")
    parser.add_argument("-n", "--name", default="", help="Sample name")
    parser.add_argument("-j", "--journal", default="Minerals Engineering",
                        choices=list(JOURNAL_STYLE.keys()),
                        help="Target journal style")
    parser.add_argument("-d", "--dpi", type=int, default=600,
                        help="Figure DPI (default: 600)")
    parser.add_argument("--no-quant", dest="run_quant", action="store_false",
                        help="Skip quantification")
    parser.add_argument("--bg", default="ALS", choices=["ALS", "rolling"],
                        help="Background method")
    parser.add_argument("--tol", type=float, default=0.28,
                        help="Phase match tolerance (default 0.28?)")
    args = parser.parse_args()

    sample_name = args.name or Path(args.data).stem

    report = analyze_xrd(
        data_path=args.data,
        output_dir=args.output,
        sample_name=sample_name,
        journal=args.journal,
        dpi=args.dpi,
        background_method=args.bg,
        peak_tolerance=args.tol,
        run_quantification=args.run_quant,
    )
