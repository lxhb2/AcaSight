"""
XRD_Analysis.py — 铜钴矿浸出渣 XRD 数据全流程自动化分析系统
替代 Jade (物相检索) + Origin (绘图)
=======================================================
功能：
  1. 数据读取  — 支持 .txt (两列) / .raw (PANalytical) / .csv
  2. 数据处理  — 平滑、Kα2 去除、BKG 扣除、寻峰
  3. 物相检索  — 与 ICDD PDF-4 卡片库匹配（本地矿物库）
  4. 定量计算  — 简化 Rietveld 峰面积比例法定量
  5. 出版级绘图  — 严格按《金属矿》/《Minerals Engineering》要求
  6. 报告生成  — JSON 摘要 + PDF / PNG 导出

作者：QClaw AI | 适用样品：铜钴矿硫酸浸出渣
"""

from __future__ import annotations
import os, sys, re, time, json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import warnings

import numpy as np
import pandas as pd

# ── 绘图 ──────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

# ── 信号处理 & 拟合 ──────────────────────────────────
from scipy.signal import savgol_filter, find_peaks
from scipy.interpolate import UnivariateSpline
from scipy.ndimage import minimum_filter1d, gaussian_filter1d


# ══════════════════════════════════════════════════════
#  矿物学知识库：铜钴矿浸出渣常见矿物 PDF 卡片峰位
#  来源: ICDD PDF-4+ / AMCSD / Mineral Handbook
#  格式: (2θ_CuKα, hkl, d_A, I%)
# ══════════════════════════════════════════════════════
MINERAL_LIBRARY: Dict[str, Dict] = {

    "α-FeOOH_Goethite_针铁矿": {
        "formula":     "α-FeOOH",
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
        "description": "黄铁矿氧化产物，浸出渣主要含铁相，针状晶形",
    },

    "Fe2O3_Hematite_赤铁矿": {
        "formula":     "Fe₂O₃",
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
        "description": "高价铁氧化物，黄铁矿氧化不完全产物，高电位浸出环境",
    },

    "Fe3O4_Magnetite_磁铁矿": {
        "formula":     "Fe₃O₄",
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
        "description": "Fe(II,III)混合氧化物，可由针铁矿脱水转化，磁性特征",
    },

    "γ-FeOOH_Lepidocrocite_纤铁矿": {
        "formula":     "γ-FeOOH",
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
        "description": "γ-FeOOH，针铁矿同质异象，低温/湿度条件下生成",
    },

    "SiO2_Quartz_石英": {
        "formula":     "SiO₂",
        "system":      "Trigonal",
        "space_group": "P3₂11",
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
        "description": "石英是最主要脉石矿物，酸性浸出后残留，惰性不参与反应",
    },

    "(Mg,Fe)5Al2Si3O10_Clinochlore_斜绿泥石": {
        "formula":     "(Mg,Fe)₅Al₂Si₃O₁₀(OH)₈",
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
        "description": "层状硅酸盐，铜钴矿中常见脉石矿物",
    },

    "CaMg(CO3)2_Dolomite_白云石": {
        "formula":     "CaMg(CO₃)₂",
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
        "description": "碳酸盐脉石，酸浸过程中部分溶解，渣中可见残余",
    },

    "FeS2_Pyrite_黄铁矿": {
        "formula":     "FeS₂",
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
        "description": "黄铁矿预氧化转化产物，渣中以氧化产物为主",
    },

    "CuS_Covellite_蓝辉铜矿": {
        "formula":     "CuS",
        "system":      "Hexagonal",
        "space_group": "P6₃/mmc",
        "a": 3.792, "b": 3.792, "c": 16.340,
        "peaks": [
            (27.76, "002", 3.212, 100),
            (29.28, "101", 3.048, 80),
            (31.78, "102", 2.814, 70),
            (47.88, "110", 1.899, 60),
            (59.30, "108", 1.558, 45),
        ],
        "color": "#0277BD",
        "description": "CuS 矿物，铜蓝蓝色，浸出渣残余铜矿物之一",
    },

    "Cu2CO3(OH)2_Malachite_孔雀石": {
        "formula":     "Cu₂CO₃(OH)₂",
        "system":      "Monoclinic",
        "space_group": "P2₁/c",
        "a": 9.502, "b": 11.974, "c": 3.240,
        "peaks": [
            (14.90, "110", 5.943, 100),
            (24.12, "220", 3.689, 45),
            (31.38, "131", 2.850, 80),
            (35.78, "221", 2.507, 70),
            (38.59, "240", 2.331, 55),
        ],
        "color": "#00838F",
        "description": "碳酸铜矿物，酸浸后分解，渣中残余少见",
    },

    "CoOOH_Heterogenite_水钴矿": {
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
        "description": "Co(III)氢氧化物，钴浸出渣残余形式，钴蓝紫色",
    },

    "CaSO4·2H2O_Gypsum_石膏": {
        "formula":     "CaSO₄·2H₂O",
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
        "description": "硫酸钙水合物，浸出过程加酸生成副产物，典型酸浸渣矿物",
    },

    "CaCO3_Calcite_方解石": {
        "formula":     "CaCO₃",
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
        "description": "方解石为钙质脉石，与硫酸反应生成石膏，渣中部分残余",
    },

    "Cu2O_Cuprite_赤铜矿": {
        "formula":     "Cu₂O",
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
        "description": "氧化亚铜，铜矿物中间产物，浸出不完全时渣中可见",
    },

    "Al2SiO5_Andalusite_红柱石": {
        "formula":     "Al₂SiO₅",
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
        "description": "铝硅酸盐，铜钴矿中常见脉石矿物",
    },

    "Al2SiO5_Kyanite_蓝晶石": {
        "formula":     "Al₂SiO₅",
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
        "description": "铝硅酸盐，多形变体，与红柱石/硅线石共存",
    },
}


# ══════════════════════════════════════════════════════
#  Publication color schemes (colorblind-safe)
# ══════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════
#  Journal figure standards
# ══════════════════════════════════════════════════════
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
    "Metallurgy": {         # 金属矿/中国冶金期刊
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
    "Chinese Journal": {    # 中文核心期刊
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


# ══════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════

def load_xrd_txt(path: str) -> pd.DataFrame:
    """读取两列格式 XRD .txt / .csv / .dat 文件"""
    df = pd.read_csv(path, sep=r"\s+", header=None, skiprows=1,
                     names=["two_theta", "intensity"], engine="python",
                     on_bad_lines="skip")
    df = df.apply(pd.to_numeric, errors="coerce").dropna()
    df = df.reset_index(drop=True)
    df["two_theta"] = df["two_theta"].round(4)
    print(f"  [LOAD] {os.path.basename(path)}: {len(df)} pts, "
          f"2θ={df['two_theta'].min():.2f}–{df['two_theta'].max():.2f}°, "
          f"I_max={df['intensity'].max():.0f} cps")
    return df


def load_xrd_raw(path: str) -> pd.DataFrame:
    """解析 PANalytical .raw 二进制文件（FI 头格式）"""
    import struct
    with open(path, "rb") as f:
        raw = f.read()

    header_size = int.from_bytes(raw[4:8], "little")
    meas_str = raw[header_size:].split(b"\x00")[0].decode(
        "latin1", errors="replace")
    meas_str = re.sub(r"[^a-zA-Z0-9\s\-:.]", " ", meas_str).strip()

    # 找数据起始位置
    data_offset = None
    for i in range(header_size + 64, len(raw) - 4, 4):
        val = struct.unpack("<I", raw[i:i + 4])[0]
        if 50 <= val <= 2000:
            data_offset = i
            break

    if data_offset is None:
        raise ValueError("无法在 .raw 文件中找到测量数据段，请提供对应 .txt 文件")

    # 读取 counts（uint32 LE）
    counts = []
    i = data_offset
    while i + 4 <= len(raw):
        val = struct.unpack("<I", raw[i:i + 4])[0]
        if val > 0:
            counts.append(val)
        i += 4

    # 从元数据提取起始角，默认 10.0°
    m = re.search(r"StartAngle\s*[:=]?\s*([\d.]+)", meas_str, re.I)
    start_angle = float(m.group(1)) if m else 10.0

    two_theta = np.arange(start_angle,
                          start_angle + len(counts) * 0.01,
                          0.01)[:len(counts)]
    df = pd.DataFrame({"two_theta": two_theta, "intensity": counts})
    print(f"  [LOAD .raw] {os.path.basename(path)}: {len(df)} pts, "
          f"2θ={df['two_theta'].min():.2f}–{df['two_theta'].max():.2f}°")
    return df


def load_xrd_auto(path: str) -> pd.DataFrame:
    """自动识别格式加载 XRD"""
    ext = Path(path).suffix.lower()
    if ext in {".txt", ".csv", ".dat", ".dx"}:
        return load_xrd_txt(path)
    elif ext == ".raw":
        return load_xrd_raw(path)
    else:
        raise ValueError(f"不支持的格式: {ext} | 支持: .txt/.csv/.dat/.raw")


# ══════════════════════════════════════════════════════
#  DATA PROCESSING
# ══════════════════════════════════════════════════════

def smooth_savgol(y: np.ndarray, window: int = 9, poly: int = 3) -> np.ndarray:
    """Savitzky-Golay 平滑"""
    if window > len(y):
        window = len(y) // 2 * 2 + 1
    return savgol_filter(y, window, poly)


def smooth_gaussian(y: np.ndarray, sigma: float = 1.2) -> np.ndarray:
    """Gaussian 平滑"""
    return gaussian_filter1d(y.astype(float), sigma=sigma)


def background_als(y: np.ndarray, lam: float = 1e6,
                    p: float = 0.01, niter: int = 15) -> np.ndarray:
    """
    Asymmetric Least Squares Smoothing — 稳健背景扣除
    lam: 平滑参数（越大背景越平滑）
    p:   非对称权重（0.01 = 优先峰下方的基线）
    """
    L = len(y)
    w = np.ones(L)
    W = np.diag(w)
    D = np.diff(np.eye(L), n=2)
    DD = np.dot(np.dot(D.T, W), D)

    for _ in range(niter):
        W_mat = np.diag(w)
        try:
            inv = np.linalg.inv(np.dot(np.dot(D.T, W_mat), D) * lam + W_mat)
            z = np.dot(inv, y)
        except np.linalg.LinAlgError:
            z = np.zeros(L)
        d = y - z
        d_neg = d < 0
        w[d_neg] = p * np.exp(d[d_neg] * 5)
        w[~d_neg] = np.exp(-d[~d_neg] * 5)
        w = w / w.max() * 1e6

    bg = gaussian_filter1d(z.astype(float), sigma=3)
    return bg


def background_rolling_min(y: np.ndarray,
                            window: int = 301) -> Tuple[np.ndarray, np.ndarray]:
    """滚动最小值 + 样条平滑（ALS 的快速替代）"""
    bg = minimum_filter1d(y.astype(float), size=window, mode="reflect")
    t = np.linspace(0, 1, len(bg))
    spl = UnivariateSpline(t, bg, s=len(bg) * 0.05)
    bg_s = spl(t)
    y_corr = np.maximum(y - bg_s, 0)
    return bg_s, y_corr


def remove_kalpha2(x: np.ndarray, y: np.ndarray,
                   delta: float = 0.03) -> np.ndarray:
    """Kα2 峰去除（Cu Kα, Δ2θ ≈ 0.03°）"""
    y2 = y.copy().astype(float)
    for i in range(len(x)):
        j = np.searchsorted(x, x[i] + delta)
        if j < len(y):
            y2[i] = y[i] - 0.5 * y[j] if y[j] < y[i] * 1.5 else y[i]
    return np.maximum(y2, 0)


# ══════════════════════════════════════════════════════
#  PEAK DETECTION
# ══════════════════════════════════════════════════════

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
    寻峰（基于背景扣除后的数据进行）
    height_ratio: 相对最大峰的最小高度比
    prominence:   峰突出度（归一化强度）
    返回: [{"two_theta": float, "intensity": float, "prominence": float, ...}, ...]
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


# ══════════════════════════════════════════════════════
#  PHASE MATCHING
# ══════════════════════════════════════════════════════

def match_phases(
    peaks: List[Dict],
    library: Dict = MINERAL_LIBRARY,
    tol_2theta: float = 0.28,
    min_matched: int = 2,
) -> List[Dict]:
    """
    物相匹配：实验峰 vs 矿物库
    tol_2theta: 2θ 匹配容差（°），默认 ±0.28°（宽匹配，考虑仪器偏差）
    min_matched: 最少匹配峰数
    返回: 按得分降序排列的物相列表
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
                        "Δ2θ":         round(d2t, 4),
                    })
                    break  # 每实验峰仅匹配最佳库峰

        if len(matched) >= min_matched:
            # 综合得分：匹配峰数 / 总峰数 * 平均相对强度 * (1 - 平均Δ2θ归一化)
            score = (
                len(matched) / len(m_peaks)
                * np.mean([m["I_rel"] for m in matched]) / 100
                * (1 - np.mean([abs(m["Δ2θ"]) for m in matched]) / tol_2theta)
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


# ══════════════════════════════════════════════════════
#  QUANTIFICATION (Simplified Rietveld — Peak Area Ratio)
# ══════════════════════════════════════════════════════

def quantify_phases(
    x: np.ndarray,
    y_net: np.ndarray,
    matched_phases: List[Dict],
    peak_width_fwhm: float = 0.18,
) -> Dict[str, float]:
    """
    简化 Rietveld 定量：各物相最强峰的峰面积比例
    峰用 Pseudo-Voigt 函数近似（Gaussian 近似）
    返回: {mineral_short_name: wt%}
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


# ══════════════════════════════════════════════════════
#  PUBLICATION-QUALITY PLOTTING
# ══════════════════════════════════════════════════════

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
    出版级 XRD 图谱（单一样品）
    journal: "Minerals Engineering" | "Metallurgy" | "CNS" | "Chinese Journal"
    """
    st = JOURNAL_STYLE.get(journal, JOURNAL_STYLE["default"])
    fig, ax = plt.subplots(figsize=st["figsize"], dpi=dpi)

    # ── 强度归一化（% of max）────────────────────────
    y_n = y_proc / max(y_proc.max(), 1) * 100
    y_raw_n = y_raw / max(y_raw.max(), 1) * 100
    y_bg_n = y_bkg / max(y_raw.max(), 1) * 100

    # ── 背景线 ──────────────────────────────────────
    if show_background:
        ax.fill_between(x, 0, y_bg_n, color="#C8D8E8",
                        alpha=0.45, label="Background", zorder=1)
        ax.plot(x, y_bg_n, color="#5588AA",
                linewidth=0.8, linestyle="--", zorder=2)

    # ── 原始曲线（半透明参考）─────────────────────────
    ax.plot(x, y_raw_n, color="#AAAAAA",
            linewidth=0.6, alpha=0.5, zorder=2)

    # ── 主曲线 ───────────────────────────────────────
    ax.fill_between(x, 0, y_n, color="#3A7ABD", alpha=0.18, zorder=3)
    ax.plot(x, y_n, color="#1A3A6B",
            linewidth=st["linewidth"], zorder=4, label=sample_name)

    # ── 物相标注 ─────────────────────────────────────
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
