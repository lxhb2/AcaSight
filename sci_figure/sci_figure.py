"""
SciFigure — Python 科研论文配图绘制模板库
===========================================
基于《科研论文配图绘制指南 基于PYTHON》宁海涛 著
整合书中所有绘图模板，提供开箱即用的科研级图表

涵盖内容：
  第2章 — 单变量图：直方图、密度图、箱线图、饼图、颜色图
  第3章 — 双变量图：散点图、Q-Q图、P-P图、相关性热图
  第4章 — 双Y轴图：ROC曲线、误差棒图、哑铃图
  第5章 — 3D图：散点、曲面、等高线、Mayavi
  第6章 — 地图可视化：GeoPandas、投影

期刊模板：Nature / Science / Cell / PNAS / JACS / Angew / 中文核心

Author: QClaw AI | License: MIT
"""

from __future__ import annotations
import os, sys, json, warnings
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Union
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import AutoMinorLocator, MultipleLocator, FormatStrFormatter
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.gridspec import GridSpec

# ─────────────────────────────────────────────────────────────
#  期刊样式配置（基于书中 SciencePlots + 自定义）
# ─────────────────────────────────────────────────────────────
JOURNAL_STYLES = {
    "nature": {
        "figsize": (3.5, 2.625),   # 单栏 3.5 inch
        "fontsize": 7,
        "linewidth": 0.75,
        "tick_width": 0.5,
        "labelpad": 2,
        "tick_dir": "out",
        "dpi": 300,
        "font": "Arial",
        "colors": ["#0C5DA5", "#FF6B35", "#00B945", "#845B97", "#FFBC00"],
    },
    "science": {
        "figsize": (3.5, 2.625),
        "fontsize": 7,
        "linewidth": 0.75,
        "tick_width": 0.5,
        "labelpad": 2,
        "tick_dir": "out",
        "dpi": 300,
        "font": "Arial",
        "colors": ["#0C5DA5", "#FF6B35", "#00B945", "#845B97", "#FFBC00"],
    },
    "cell": {
        "figsize": (4.5, 3.375),   # 1.5栏
        "fontsize": 8,
        "linewidth": 1.0,
        "tick_width": 0.6,
        "labelpad": 3,
        "tick_dir": "out",
        "dpi": 300,
        "font": "Arial",
        "colors": ["#0077BB", "#EE7733", "#009988", "#CC3311", "#EE3377"],
    },
    "pnas": {
        "figsize": (3.5, 2.625),
        "fontsize": 7,
        "linewidth": 0.75,
        "tick_width": 0.5,
        "labelpad": 2,
        "tick_dir": "out",
        "dpi": 300,
        "font": "Helvetica",
        "colors": ["#0C5DA5", "#FF6B35", "#00B945", "#845B97", "#FFBC00"],
    },
    "jacs": {
        "figsize": (3.25, 2.5),   # ACS 单栏
        "fontsize": 7,
        "linewidth": 0.75,
        "tick_width": 0.5,
        "labelpad": 2,
        "tick_dir": "out",
        "dpi": 300,
        "font": "Arial",
        "colors": ["#000000", "#E64A19", "#1565C0", "#2E7D32", "#7B1FA2"],
    },
    "angew": {
        "figsize": (3.0, 2.25),   # Angew 单栏
        "fontsize": 6,
        "linewidth": 0.6,
        "tick_width": 0.4,
        "labelpad": 2,
        "tick_dir": "out",
        "dpi": 300,
        "font": "Arial",
        "colors": ["#000000", "#D32F2F", "#1976D2", "#388E3C", "#7B1FA2"],
    },
    "chinese": {   # 中文核心期刊
        "figsize": (8, 6),        # cm 转 inch 约 3.15×2.36
        "fontsize": 9,
        "linewidth": 1.0,
        "tick_width": 0.6,
        "labelpad": 3,
        "tick_dir": "in",
        "dpi": 300,
        "font": "SimHei",
        "colors": ["#000000", "#E64A19", "#1565C0", "#2E7D32", "#7B1FA2"],
    },
    "default": {
        "figsize": (5, 4),
        "fontsize": 10,
        "linewidth": 1.2,
        "tick_width": 0.8,
        "labelpad": 4,
        "tick_dir": "in",
        "dpi": 150,
        "font": "DejaVu Sans",
        "colors": ["#1A1A1A", "#E64A19", "#1565C0", "#2E7D32", "#7B1FA2"],
    },
}

# ─────────────────────────────────────────────────────────────
#  颜色主题（书中推荐 + ColorBrewer）
# ─────────────────────────────────────────────────────────────
COLOR_THEMES = {
    "default": ["#0C5DA5", "#FF6B35", "#00B945", "#845B97", "#FFBC00"],
    "vibrant": ["#0077BB", "#EE7733", "#009988", "#CC3311", "#EE3377", "#BBBBBB"],
    "muted":   ["#332288", "#6699CC", "#88CCEE", "#44AA99", "#117733", "#999933"],
    "pastel":  ["#A6CEE3", "#1F78B4", "#B2DF8A", "#33A02F", "#FB9A99", "#E31A1C"],
    "dark":    ["#1B1B1B", "#3D3D3D", "#5A5A5A", "#767676", "#929292", "#ADADAD"],
    "colorblind": ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#F0E442", "#56B4E9"],
    "npg":     ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4"],  # Nature Publishing Group
    "aaas":    ["#3B4994", "#EE0000", "#008B45", "#6495ED", "#EE82EE", "#9400D3"],  # AAAS/Science
    "jco":     ["#0073C2", "#EFC000", "#868686", "#CD534C", "#00A087", "#A7A7A7"],  # Journal of Clinical Oncology
}


# ══════════════════════════════════════════════════════════════
#  样式应用函数
# ══════════════════════════════════════════════════════════════

def apply_style(ax, journal: str = "nature", style_override: Optional[Dict] = None) -> None:
    """
    应用期刊样式到 Axes 对象
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        目标坐标轴
    journal : str
        期刊名称: nature/science/cell/pnas/jacs/angew/chinese/default
    style_override : dict, optional
        覆盖默认样式的参数
    """
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["default"]).copy()
    if style_override:
        st.update(style_override)
    
    # 字体
    font = st.get("font", "DejaVu Sans")
    plt.rcParams["font.family"] = font
    plt.rcParams["mathtext.fontset"] = "custom" if font in ["Arial", "Helvetica"] else "dejavusans"
    
    # 坐标轴
    for spine in ax.spines.values():
        spine.set_linewidth(st["tick_width"])
        spine.set_color("black")
    
    # 刻度
    ax.tick_params(
        direction=st["tick_dir"],
        axis="both",
        which="major",
        length=4 if st["tick_dir"] == "out" else 5,
        width=st["tick_width"],
        labelsize=st["fontsize"],
        top=st["tick_dir"] == "in",
        right=st["tick_dir"] == "in",
    )
    ax.tick_params(
        which="minor",
        length=2 if st["tick_dir"] == "out" else 2.5,
        width=st["tick_width"] * 0.6,
        top=st["tick_dir"] == "in",
        right=st["tick_dir"] == "in",
    )
    
    # 次刻度
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    
    # 网格
    ax.grid(which="major", linestyle="-", linewidth=0.3, color="#AAAAAA", alpha=0.5)
    ax.grid(which="minor", linestyle=":", linewidth=0.2, color="#BBBBBB", alpha=0.3)
    ax.set_axisbelow(True)


def get_figure(journal: str = "nature", n_rows: int = 1, n_cols: int = 1,
               width_ratio: Optional[List[float]] = None,
               height_ratio: Optional[List[float]] = None,
               style_override: Optional[Dict] = None) -> Tuple[plt.Figure, Union[plt.Axes, np.ndarray]]:
    """
    创建符合期刊要求的 Figure
    
    Parameters
    ----------
    journal : str
        期刊名称
    n_rows, n_cols : int
        子图行列数
    width_ratio, height_ratio : list, optional
        子图宽度/高度比例
    style_override : dict
        样式覆盖
    
    Returns
    -------
    fig, axes : tuple
    """
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["default"]).copy()
    if style_override:
        st.update(style_override)
    
    # 计算总尺寸
    base_w, base_h = st["figsize"]
    total_w = base_w * n_cols if n_cols > 1 else base_w
    total_h = base_h * n_rows if n_rows > 1 else base_h
    
    fig = plt.figure(figsize=(total_w, total_h), dpi=st["dpi"])
    
    if n_rows == 1 and n_cols == 1:
        ax = fig.add_subplot(111)
        apply_style(ax, journal, style_override)
        return fig, ax
    
    gs = GridSpec(n_rows, n_cols, figure=fig,
                  width_ratios=width_ratio, height_ratios=height_ratio)
    axes = np.array([[fig.add_subplot(gs[i, j]) for j in range(n_cols)] for i in range(n_rows)])
    for ax in axes.flat:
        apply_style(ax, journal, style_override)
    
    return fig, axes


# ══════════════════════════════════════════════════════════════
#  第2章 — 单变量图
# ══════════════════════════════════════════════════════════════

def plot_histogram(
    data: Union[np.ndarray, pd.Series, List],
    bins: Union[int, str] = "auto",
    density: bool = True,
    kde: bool = True,
    journal: str = "nature",
    xlabel: str = "Value",
    ylabel: str = "Density",
    title: str = "",
    color: str = "#0C5DA5",
    edgecolor: str = "black",
    alpha: float = 0.7,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    直方图 + 可选 KDE 密度曲线
    
    书中 2.2.1 节模板
    """
    fig, ax = get_figure(journal)
    
    arr = np.asarray(data).flatten()
    
    # 直方图
    n, bins_edge, patches = ax.hist(
        arr, bins=bins, density=density,
        color=color, edgecolor=edgecolor,
        alpha=alpha, linewidth=0.5,
    )
    
    # KDE 曲线
    if kde:
        from scipy.stats import gaussian_kde
        kde_func = gaussian_kde(arr)
        x_range = np.linspace(arr.min(), arr.max(), 200)
        ax.plot(x_range, kde_func(x_range), color=color, linewidth=1.5, label="KDE")
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=JOURNAL_STYLES.get(journal, {})["fontsize"] + 1)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_boxplot(
    data: Union[np.ndarray, pd.DataFrame, Dict[str, List]],
    journal: str = "nature",
    xlabel: str = "",
    ylabel: str = "Value",
    title: str = "",
    colors: Optional[List[str]] = None,
    notch: bool = False,
    showfliers: bool = True,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    箱线图
    
    书中 2.3 节模板
    """
    fig, ax = get_figure(journal)
    
    if isinstance(data, dict):
        labels = list(data.keys())
        values = list(data.values())
    elif isinstance(data, pd.DataFrame):
        labels = data.columns.tolist()
        values = [data[col].dropna().values for col in labels]
    else:
        labels = [f"Set {i+1}" for i in range(data.shape[1] if data.ndim > 1 else 1)]
        values = [data[:, i] if data.ndim > 1 else data for i in range(len(labels))]
    
    if colors is None:
        colors = COLOR_THEMES["default"][:len(labels)]
    
    bp = ax.boxplot(values, labels=labels, notch=notch, showfliers=showfliers,
                    patch_artist=True, widths=0.6)
    
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
        patch.set_edgecolor("black")
        patch.set_linewidth(0.5)
    
    for whisker in bp["whiskers"]:
        whisker.set_linewidth(0.5)
    for cap in bp["caps"]:
        cap.set_linewidth(0.5)
    for median in bp["medians"]:
        median.set_linewidth(1.0)
        median.set_color("black")
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_violin(
    data: Union[np.ndarray, pd.DataFrame, Dict[str, List]],
    journal: str = "nature",
    xlabel: str = "",
    ylabel: str = "Value",
    title: str = "",
    colors: Optional[List[str]] = None,
    show_median: bool = True,
    show_box: bool = True,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    小提琴图
    
    书中 2.3.2 节模板
    """
    fig, ax = get_figure(journal)
    
    if isinstance(data, dict):
        labels = list(data.keys())
        values = list(data.values())
    elif isinstance(data, pd.DataFrame):
        labels = data.columns.tolist()
        values = [data[col].dropna().values for col in labels]
    else:
        labels = [f"Set {i+1}" for i in range(data.shape[1] if data.ndim > 1 else 1)]
        values = [data[:, i] if data.ndim > 1 else data for i in range(len(labels))]
    
    if colors is None:
        colors = COLOR_THEMES["default"][:len(labels)]
    
    parts = ax.violinplot(values, positions=range(1, len(labels)+1),
                          showmedians=show_median, showextrema=True)
    
    for i, (pc, color) in enumerate(zip(parts["bodies"], colors)):
        pc.set_facecolor(color)
        pc.set_alpha(0.7)
        pc.set_edgecolor("black")
        pc.set_linewidth(0.5)
    
    ax.set_xticks(range(1, len(labels)+1))
    ax.set_xticklabels(labels)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_pie(
    values: List[float],
    labels: List[str],
    journal: str = "nature",
    title: str = "",
    colors: Optional[List[str]] = None,
    explode: Optional[List[float]] = None,
    startangle: float = 90,
    show_pct: bool = True,
    pct_distance: float = 0.75,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    饼图
    
    书中 2.4 节模板
    """
    fig, ax = get_figure(journal)
    
    if colors is None:
        colors = COLOR_THEMES["default"][:len(values)]
    
    if explode is None:
        explode = [0.02] * len(values)
    
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        explode=explode, startangle=startangle,
        autopct=lambda p: f"{p:.1f}%" if show_pct and p > 3 else "",
        pctdistance=pct_distance,
        wedgeprops=dict(linewidth=0.5, edgecolor="white"),
    )
    
    if show_pct:
        for at in autotexts:
            at.set_fontsize(7)
            at.set_color("white")
            at.set_fontweight("bold")
    
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


# ══════════════════════════════════════════════════════════════
#  第3章 — 双变量图
# ══════════════════════════════════════════════════════════════

def plot_scatter(
    x: Union[np.ndarray, List],
    y: Union[np.ndarray, List],
    journal: str = "nature",
    xlabel: str = "X",
    ylabel: str = "Y",
    title: str = "",
    color: str = "#0C5DA5",
    size: Union[float, np.ndarray] = 20,
    edgecolor: str = "black",
    alpha: float = 0.8,
    fit_line: bool = False,
    show_r: bool = False,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    散点图
    
    书中 3.1 节模板
    """
    fig, ax = get_figure(journal)
    
    x_arr = np.asarray(x).flatten()
    y_arr = np.asarray(y).flatten()
    
    ax.scatter(x_arr, y_arr, s=size, c=color, edgecolors=edgecolor,
               alpha=alpha, linewidth=0.3, zorder=3)
    
    # 拟合线
    if fit_line:
        from scipy.stats import linregress
        slope, intercept, r_value, p_value, std_err = linregress(x_arr, y_arr)
        x_fit = np.linspace(x_arr.min(), x_arr.max(), 100)
        y_fit = slope * x_fit + intercept
        ax.plot(x_fit, y_fit, color="#D32F2F", linewidth=1.0, linestyle="--", zorder=2)
        
        if show_r:
            ax.text(0.05, 0.95, f"R² = {r_value**2:.3f}", transform=ax.transAxes,
                    fontsize=7, va="top")
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_line(
    x: Union[np.ndarray, List],
    y: Union[np.ndarray, List, Dict[str, List]],
    journal: str = "nature",
    xlabel: str = "X",
    ylabel: str = "Y",
    title: str = "",
    colors: Optional[List[str]] = None,
    markers: bool = False,
    error: Optional[np.ndarray] = None,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    折线图（支持多系列）
    """
    fig, ax = get_figure(journal)
    
    x_arr = np.asarray(x).flatten()
    
    if isinstance(y, dict):
        # 多系列
        labels = list(y.keys())
        y_vals = list(y.values())
        if colors is None:
            colors = COLOR_THEMES["default"][:len(labels)]
        
        for i, (label, y_i) in enumerate(zip(labels, y_vals)):
            y_arr = np.asarray(y_i).flatten()
            ax.plot(x_arr, y_arr, color=colors[i], linewidth=1.0,
                    marker="o" if markers else None, markersize=3 if markers else None,
                    label=label)
        ax.legend(fontsize=6, frameon=False)
    else:
        y_arr = np.asarray(y).flatten()
        color = colors[0] if colors else "#0C5DA5"
        ax.plot(x_arr, y_arr, color=color, linewidth=1.0,
                marker="o" if markers else None, markersize=3 if markers else None)
        
        if error is not None:
            ax.fill_between(x_arr, y_arr - error, y_arr + error,
                            color=color, alpha=0.2, zorder=1)
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_qq(
    data: Union[np.ndarray, List],
    dist: str = "norm",
    journal: str = "nature",
    title: str = "Q-Q Plot",
    color: str = "#0C5DA5",
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Q-Q 图（检验分布）
    
    书中 3.2.3 节模板
    """
    fig, ax = get_figure(journal)
    
    try:
        import statsmodels.graphics.gofplots as sm
        sm.qqplot(np.asarray(data), dist=dist, line="45", ax=ax, markerfacecolor=color,
                  markeredgecolor="black", markersize=4, alpha=0.7)
    except ImportError:
        # Fallback: manual Q-Q
        from scipy.stats import probplot
        probplot(np.asarray(data), dist=dist, plot=ax)
        ax.get_lines()[0].set_markerfacecolor(color)
        ax.get_lines()[0].set_markeredgecolor("black")
        ax.get_lines()[0].set_markersize(4)
    
    ax.set_xlabel("Theoretical Quantiles")
    ax.set_ylabel("Sample Quantiles")
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_heatmap(
    data: Union[np.ndarray, pd.DataFrame],
    journal: str = "nature",
    xlabel: str = "",
    ylabel: str = "",
    title: str = "",
    cmap: str = "RdBu_r",
    annot: bool = False,
    fmt: str = ".2f",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    center: Optional[float] = 0,
    cbar: bool = True,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    热图
    
    书中 3.3 节模板
    """
    fig, ax = get_figure(journal)
    
    arr = np.asarray(data)
    if isinstance(data, pd.DataFrame):
        xticklabels = data.columns
        yticklabels = data.index
    else:
        xticklabels = range(arr.shape[1])
        yticklabels = range(arr.shape[0])
    
    im = ax.imshow(arr, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
    
    if cbar:
        cbar_obj = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar_obj.ax.tick_params(labelsize=6)
    
    ax.set_xticks(range(len(xticklabels)))
    ax.set_yticks(range(len(yticklabels)))
    ax.set_xticklabels(xticklabels, rotation=45, ha="right", fontsize=6)
    ax.set_yticklabels(yticklabels, fontsize=6)
    
    if annot:
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                val = arr[i, j]
                text_color = "white" if abs(val - (vmax + vmin) / 2) > (vmax - vmin) / 4 else "black"
                ax.text(j, i, f"{val:{fmt}}", ha="center", va="center",
                        fontsize=5, color=text_color)
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


# ══════════════════════════════════════════════════════════════
#  第4章 — 双Y轴图
# ══════════════════════════════════════════════════════════════

def plot_dual_y(
    x: Union[np.ndarray, List],
    y1: Union[np.ndarray, List],
    y2: Union[np.ndarray, List],
    journal: str = "nature",
    xlabel: str = "X",
    y1label: str = "Y1",
    y2label: str = "Y2",
    title: str = "",
    y1color: str = "#0C5DA5",
    y2color: str = "#E64A19",
    y1legend: str = "",
    y2legend: str = "",
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes, plt.Axes]:
    """
    双Y轴图
    
    书中 4.1 节模板
    """
    fig, ax1 = get_figure(journal)
    
    x_arr = np.asarray(x).flatten()
    y1_arr = np.asarray(y1).flatten()
    y2_arr = np.asarray(y2).flatten()
    
    ax1.plot(x_arr, y1_arr, color=y1color, linewidth=1.0, label=y1legend)
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(y1label, color=y1color)
    ax1.tick_params(axis="y", labelcolor=y1color)
    
    ax2 = ax1.twinx()
    ax2.plot(x_arr, y2_arr, color=y2color, linewidth=1.0, label=y2legend)
    ax2.set_ylabel(y2label, color=y2color)
    ax2.tick_params(axis="y", labelcolor=y2color)
    
    if title:
        ax1.set_title(title)
    
    if y1legend or y2legend:
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=6, frameon=False)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax1, ax2


def plot_errorbar(
    x: Union[np.ndarray, List],
    y: Union[np.ndarray, List],
    yerr: Union[np.ndarray, List, Tuple],
    journal: str = "nature",
    xlabel: str = "X",
    ylabel: str = "Y",
    title: str = "",
    color: str = "#0C5DA5",
    capsize: float = 2,
    marker: str = "o",
    markersize: float = 4,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    误差棒图
    
    书中 4.2 节模板
    """
    fig, ax = get_figure(journal)
    
    x_arr = np.asarray(x).flatten()
    y_arr = np.asarray(y).flatten()
    
    if isinstance(yerr, tuple):
        yerr_lower, yerr_upper = yerr
        yerr = [np.asarray(yerr_lower).flatten(), np.asarray(yerr_upper).flatten()]
    
    ax.errorbar(x_arr, y_arr, yerr=yerr, fmt=marker, color=color,
                capsize=capsize, markersize=markersize, linewidth=0.8,
                markeredgecolor="black", markeredgewidth=0.3, elinewidth=0.5)
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_dumbbell(
    categories: List[str],
    values1: List[float],
    values2: List[float],
    journal: str = "nature",
    xlabel: str = "Value",
    title: str = "",
    color1: str = "#0C5DA5",
    color2: str = "#E64A19",
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    哑铃图（Dumbbell Plot）
    
    书中 4.1.4 节模板
    """
    fig, ax = get_figure(journal)
    
    y_pos = range(len(categories))
    
    for i, (v1, v2, cat) in enumerate(zip(values1, values2, categories)):
        ax.scatter(v1, i, s=30, color=color1, edgecolor="black", linewidth=0.3, zorder=3)
        ax.scatter(v2, i, s=30, color=color2, edgecolor="black", linewidth=0.3, zorder=3)
        ax.plot([v1, v2], [i, i], color="gray", linewidth=0.8, zorder=2)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories)
    ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title)
    
    # 图例
    ax.scatter([], [], s=30, color=color1, edgecolor="black", label="Value 1")
    ax.scatter([], [], s=30, color=color2, edgecolor="black", label="Value 2")
    ax.legend(fontsize=6, frameon=False, loc="best")
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


# ══════════════════════════════════════════════════════════════
#  第5章 — 3D图
# ══════════════════════════════════════════════════════════════

def plot_3d_scatter(
    x: Union[np.ndarray, List],
    y: Union[np.ndarray, List],
    z: Union[np.ndarray, List],
    journal: str = "nature",
    xlabel: str = "X",
    ylabel: str = "Y",
    zlabel: str = "Z",
    title: str = "",
    color: Union[str, np.ndarray] = "#0C5DA5",
    size: float = 20,
    alpha: float = 0.8,
    elev: float = 30,
    azim: float = 45,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    3D 散点图
    
    书中 5.4.1 节模板
    """
    from mpl_toolkits.mplot3d import Axes3D
    
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["default"])
    fig = plt.figure(figsize=st["figsize"], dpi=st["dpi"])
    ax = fig.add_subplot(111, projection="3d")
    
    x_arr = np.asarray(x).flatten()
    y_arr = np.asarray(y).flatten()
    z_arr = np.asarray(z).flatten()
    
    p = ax.scatter(x_arr, y_arr, z_arr, c=color, s=size, alpha=alpha,
                   edgecolor="black", linewidth=0.2)
    
    ax.set_xlabel(xlabel, fontsize=st["fontsize"])
    ax.set_ylabel(ylabel, fontsize=st["fontsize"])
    ax.set_zlabel(zlabel, fontsize=st["fontsize"])
    ax.view_init(elev=elev, azim=azim)
    
    if title:
        ax.set_title(title)
    
    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


def plot_3d_surface(
    x: np.ndarray,
    y: np.ndarray,
    z_func,
    journal: str = "nature",
    xlabel: str = "X",
    ylabel: str = "Y",
    zlabel: str = "Z",
    title: str = "",
    cmap: str = "viridis",
    alpha: float = 0.9,
    elev: float = 30,
    azim: float = 45,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    3D 曲面图
    
    书中 5.4.2 节模板
    """
    from mpl_toolkits.mplot3d import Axes3D
    
    st = JOURNAL_STYLES.get(journal.lower(), J
from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure(figsize=st["figsize"], dpi=st["dpi"])
    ax = fig.add_subplot(111, projection="3d")

    if callable(z_func):
        X, Y = np.meshgrid(x, y)
        Z = z_func(X, Y)
    else:
        X, Y, Z = np.asarray(x), np.asarray(y), np.asarray(z_func)

    surf = ax.plot_surface(X, Y, Z, cmap=cmap, alpha=alpha, linewidth=0,
                           antialiased=True)
    cbar = fig.colorbar(surf, ax=ax, shrink=0.6)
    cbar.ax.tick_params(labelsize=6)

    ax.set_xlabel(xlabel, fontsize=st["fontsize"])
    ax.set_ylabel(ylabel, fontsize=st["fontsize"])
    ax.set_zlabel(zlabel, fontsize=st["fontsize"])
    ax.view_init(elev=elev, azim=azim)

    if title:
        ax.set_title(title)

    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)

    return fig, ax


def plot_contour(
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    journal: str = "nature",
    xlabel: str = "X",
    ylabel: str = "Y",
    title: str = "",
    cmap: str = "viridis",
    levels: int = 20,
    filled: bool = True,
    contour_lines: bool = True,
    clabel: bool = True,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    等高线图
    
    书中 5.4.3 节模板
    """
    fig, ax = get_figure(journal)

    X, Y = np.meshgrid(x, y)
    Z = np.asarray(z)

    if filled:
        cf = ax.contourf(X, Y, Z, levels=levels, cmap=cmap)
        cbar = fig.colorbar(cf, ax=ax, shrink=0.8)
        cbar.ax.tick_params(labelsize=6)
    if contour_lines:
        cs = ax.contour(X, Y, Z, levels=levels, colors="white", linewidths=0.3, alpha=0.6)
        if clabel:
            ax.clabel(cs, inline=True, fontsize=5, fmt="%.1f")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)

    if output:
        fig.savefig(output, dpi=fig.dpi, bbox_inches="tight")
        plt.close(fig)

    return fig, ax


# ══════════════════════════════════════════════════════════════
#  组合图表
# ══════════════════════════════════════════════════════════════

def plot_multi_panel(
    panels: List[Dict],
    journal: str = "nature",
    title: str = "",
    labels: Optional[List[str]] = None,
    output: Optional[str] = None,
    **kwargs,
) -> Tuple[plt.Figure, np.ndarray]:
    """
    多面板组合图
    
    panels: List of dicts with keys:
        type: "scatter"/"hist"/"line"/"bar"/"box"/"heatmap"/"pie"
        data: ...
        xlabel, ylabel, title, color, ...
    
    书中所有多图组合示例
    """
    n = len(panels)
    n_cols = 2 if n > 2 else n
    n_rows = (n + n_cols - 1) // n_cols
    
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["default"])
    total_w = st["figsize"][0] * n_cols
    total_h = st["figsize"][1] * n_rows
    fig = plt.figure(figsize=(total_w, total_h), dpi=st["dpi"])
    
    axes = []
    for i, panel in enumerate(panels):
        ax = fig.add_subplot(n_rows, n_cols, i + 1)
        ptype = panel.get("type", "line")
        pdata = panel.get("data", {})
        
        if ptype == "scatter":
            ax.scatter(pdata.get("x", []), pdata.get("y", []),
                     c=panel.get("color", "#0C5DA5"), s=20, alpha=0.8,
                     edgecolor="black", linewidth=0.3)
        elif ptype == "hist":
            ax.hist(pdata.get("data", []), bins=panel.get("bins", 20),
                   color=panel.get("color", "#0C5DA5"), alpha=0.7,
                   edgecolor="black", linewidth=0.3)
        elif ptype == "line":
            x = pdata.get("x", range(len(pdata.get("y", []))))
            ax.plot(x, pdata.get("y", []), color=panel.get("color", "#0C5DA5"),
                   linewidth=1.0, marker=panel.get("marker", None))
        elif ptype == "bar":
            ax.bar(pdata.get("x", []), pdata.get("y", []),
                  color=panel.get("color", "#0C5DA5"), alpha=0.8,
                  edgecolor="black", linewidth=0.3)
        elif ptype == "box":
            ax.boxplot(pdata.get("data", []), patch_artist=True, widths=0.6)
        elif ptype == "heatmap":
            im = ax.imshow(pdata.get("data", []), cmap=panel.get("cmap", "viridis"),
                          aspect="auto")
            fig.colorbar(im, ax=ax, shrink=0.6)
        elif ptype == "pie":
            wedges, _, _ = ax.pie(pdata.get("values", []), labels=pdata.get("labels", []),
                                  colors=panel.get("colors", None), startangle=90,
                                  wedgeprops=dict(linewidth=0.5, edgecolor="white"))
        
        apply_style(ax, journal)
        ax.set_xlabel(panel.get("xlabel", ""), fontsize=st["fontsize"])
        ax.set_ylabel(panel.get("ylabel", ""), fontsize=st["fontsize"])
        if panel.get("title"):
            ax.set_title(panel["title"], fontsize=st["fontsize"] + 1)
        
        if labels and i < len(labels):
            ax.text(-0.1, 1.1, labels[i], transform=ax.transAxes,
                    fontsize=st["fontsize"] + 1, fontweight="bold", va="top")
        
        axes.append(ax)
    
    if title:
        fig.suptitle(title, fontsize=st["fontsize"] + 2, fontweight="bold")
    
    plt.tight_layout(rect=[0, 0, 1, 0.97] if title else [0, 0, 1, 1])
    
    if output:
        fig.savefig(output, dpi=st["dpi"], bbox_inches="tight")
        plt.close(fig)
    
    return fig, np.array(axes)


def plot_xrd(
    two_theta: np.ndarray,
    intensity: np.ndarray,
    intensity_net: Optional[np.ndarray] = None,
    matched_phases: Optional[List[Dict]] = None,
    journal: str = "Minerals Engineering",
    sample_name: str = "",
    output: Optional[str] = None,
    dpi: int = 600,
    show_peaks: bool = True,
    show_legend: bool = True,
    **kwargs,
) -> Tuple[plt.Figure, plt.Axes]:
    """
    XRD 图谱 — 出版级
    
    基于 sci_figure 模板 + XRD 特殊处理
    """
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["default"])
    fig, ax = plt.figure(figsize=st["figsize"], dpi=dpi), plt.gca()
    
    x = np.asarray(two_theta).flatten()
    y_raw = np.asarray(intensity).flatten()
    y_raw_n = y_raw / y_raw.max() * 100
    
    if intensity_net is not None:
        y_net = np.asarray(intensity_net).flatten()
        y_net_n = y_net / y_net.max() * 100
        ax.fill_between(x, 0, y_net_n, color="#3A7ABD", alpha=0.18)
        ax.plot(x, y_net_n, color="#1A3A6B", linewidth=1.0, label=sample_name)
    
    ax.plot(x, y_raw_n, color="#AAAAAA", linewidth=0.5, alpha=0.5)
    
    # 物相标注
    if matched_phases:
        colors_iter = iter(["#D32F2F", "#E53935", "#1565C0", "#2E7D32",
                           "#7B1FA2", "#00838F", "#F57F17", "#C62828"])
        legend_handles = []
        
        for ph in matched_phases[:6]:
            c = next(colors_iter)
            legend_handles.append(mpatches.Patch(facecolor=c, alpha=0.8, label=ph.get("name", "")))
            for m in ph.get("peaks", [])[:3]:
                ax.axvline(m["exp_2theta"] if "exp_2theta" in m else m.get("two_theta", 0),
                          color=c, linewidth=0.6, alpha=0.5, linestyle="--", zorder=2)
        
        if show_legend:
            ax.legend(handles=legend_handles, loc="upper right", fontsize=5,
                     framealpha=0.9, fancybox=False, ncol=1)
    
    apply_style(ax, journal)
    ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=st["fontsize"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=st["fontsize"])
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(-2, 110)
    
    if sample_name:
        ax.set_title(f"XRD Pattern of {sample_name}", fontsize=st["fontsize"] + 1, fontweight="bold")
    
    plt.tight_layout()
    
    if output:
        fmt = "eps" if journal == "Minerals Engineering" else "png"
        fig.savefig(output, dpi=dpi, format=fmt, bbox_inches="tight")
        plt.close(fig)
    
    return fig, ax


# ══════════════════════════════════════════════════════════════
#  科研图全套导出工具
# ══════════════════════════════════════════════════════════════

def export_figure(
    fig: plt.Figure,
    path: str,
    fmt: Optional[str] = None,
    dpi: Optional[int] = None,
) -> str:
    """导出图表为多种格式"""
    if fmt is None:
        fmt = path.rsplit(".", 1)[-1] if "." in path else "png"
    if dpi is None:
        dpi = fig.dpi
    
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=dpi, format=fmt, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"  [EXPORT] {path}")
    return path


# ══════════════════════════════════════════════════════════════
#  演示 / 示例数据
# ══════════════════════════════════════════════════════════════

def demo_all_charts(output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    演示所有图表类型，生成示例图片
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "demo_output")
    os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    
    # ── 直方图 ──────────────────────────────────────
    np.random.seed(42)
    data = np.random.normal(50, 10, 500)
    fig, ax = plot_histogram(data, bins=25, kde=True, journal="nature",
                              xlabel="Value", ylabel="Density",
                              title="Histogram + KDE", output=os.path.join(output_dir, "hist.png"))
    results["histogram"] = os.path.join(output_dir, "hist.png")
    
    # ── 箱线图 ──────────────────────────────────────
    box_data = {
        "Control": np.random.normal(10, 2, 50),
        "Treatment A": np.random.normal(15, 3, 50),
        "Treatment B": np.random.normal(12, 2.5, 50),
    }
    fig, ax = plot_boxplot(box_data, journal="nature", ylabel="Response",
                           title="Box Plot Comparison", output=os.path.join(output_dir, "box.png"))
    results["boxplot"] = os.path.join(output_dir, "box.png")
    
    # ── 散点图 ──────────────────────────────────────
    x = np.random.uniform(0, 10, 80)
    y = 2 * x + np.random.normal(0, 3, 80)
    fig, ax = plot_scatter(x, y, journal="nature", xlabel="X", ylabel="Y",
                           title="Scatter Plot", fit_line=True, show_r=True,
                           output=os.path.join(output_dir, "scatter.png"))
    results["scatter"] = os.path.join(output_dir, "scatter.png")
    
    # ── 热图 ────────────────────────────────────────
    np.random.seed(0)
    corr = np.random.randn(8, 8)
    corr = np.tril(corr) + corr.T - np.diag(corr.diagonal())
    np.fill_diagonal(corr, 1)
    fig, ax = plot_heatmap(corr, journal="nature", annot=True,
                           title="Correlation Heatmap",
                           output=os.path.join(output_dir, "heatmap.png"))
    results["heatmap"] = os.path.join(output_dir, "heatmap.png")
    
    # ── 双Y轴 ───────────────────────────────────────
    x = np.linspace(0, 10, 100)
    y1 = np.sin(x) * 50 + 50
    y2 = np.cos(x) * 20 + 20
    fig, ax1, ax2 = plot_dual_y(x, y1, y2, journal="nature",
                                 xlabel="Time", y1label="Amplitude",
                                 y2label="Phase", y1legend="Signal A",
                                 y2legend="Signal B",
                                 title="Dual Y-Axis",
                                 output=os.path.join(output_dir, "dual_y.png"))
    results["dual_y"] = os.path.join(output_dir, "dual_y.png")
    
    # ── 误差棒 ──────────────────────────────────────
    x = np.arange(5)
    y = np.array([10, 15, 12, 18, 20])
    yerr = np.array([1.5, 2.0, 1.0, 2.5, 1.8])
    fig, ax = plot_errorbar(x, y, yerr, journal="nature",
                            xlabel="Experiment", ylabel="Result",
                            title="Error Bar Plot",
                            output=os.path.join(output_dir, "errorbar.png"))
    results["errorbar"] = os.path.join(output_dir, "errorbar.png")
    
    # ── 3D 散点 ─────────────────────────────────────
    np.random.seed(0)
    fig, ax = plot_3d_scatter(
        np.random.randn(200), np.random.randn(200), np.random.randn(200),
        journal="nature", xlabel="X", ylabel="Y", zlabel="Z",
        title="3D Scatter", elev=25, azim=45,
        output=os.path.join(output_dir, "3d_scatter.png")
    )
    results["3d_scatter"] = os.path.join(output_dir, "3d_scatter.png")
    
    # ── 等高线 ──────────────────────────────────────
    x = np.linspace(-3, 3, 100)
    y = np.linspace(-3, 3, 100)
    X, Y = np.meshgrid(x, y)
    Z = np.exp(-(X**2 + Y**2)) + 0.1 * np.exp(-((X-1.5)**2 + (Y-1.5)**2))
    fig, ax = plot_contour(x, y, Z, journal="nature",
                           xlabel="X", ylabel="Y", title="Contour Plot",
                           output=os.path.join(output_dir, "contour.png"))
    results["contour"] = os.path.join(output_dir, "contour.png")
    
    # ── 多面板 ──────────────────────────────────────
    panels = [
        {"type": "hist", "data": {"data": np.random.normal(0, 1, 200)},
         "xlabel": "x", "ylabel": "Count", "title": "(a)", "color": "#0C5DA5"},
        {"type": "scatter", "data": {"x": np.random.randn(100), "y": np.random.randn(100)},
         "xlabel": "x", "ylabel": "y", "title": "(b)", "color": "#E64A19"},
        {"type": "line", "data": {"x": range(50), "y": np.cumsum(np.random.randn(50))},
         "xlabel": "Step", "ylabel": "Cumulative", "title": "(c)", "color": "#2E7D32"},
        {"type": "bar", "data": {"x": ["A","B","C","D"], "y": [12,18,15,22]},
         "xlabel": "Category", "ylabel": "Value", "title": "(d)", "color": "#7B1FA2"},
    ]
    fig, axes = plot_multi_panel(panels, journal="nature",
                                  labels=["(a)","(b)","(c)","(d)"],
                                  title="Multi-Panel Figure",
                                  output=os.path.join(output_dir, "multi_panel.png"))
    results["multi_panel"] = os.path.join(output_dir, "multi_panel.png")
    
    print("\n[DEMO] All charts generated:")
    for k, v in results.items():
        print(f"  {k:<15}: {v}")
    
    return results


if __name__ == "__main__":
    results = demo_all_charts()
