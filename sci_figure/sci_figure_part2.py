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
