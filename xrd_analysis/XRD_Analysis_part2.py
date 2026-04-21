                p2t = p["exp_2theta"]
                # 计算此峰在此角度的归一化高度
                idx = np.searchsorted(x, p2t)
                h_at_peak = y_n[idx] if idx < len(y_n) else 0
                ax.axvline(p2t, ymin=0, ymax=h_at_peak / 110,
                           color=c, linewidth=0.7,
                           linestyle=":", alpha=0.7, zorder=3)

        # 标注最强峰
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

    # ── 样式设置 ─────────────────────────────────────
    _apply_style(ax, st)
    ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=st["fontsize"],
                  labelpad=st["labelpad"])
    ax.set_ylabel("Intensity (% of maximum)", fontsize=st["fontsize"],
                  labelpad=st["labelpad"])
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(-2, 112)

    # ── 2θ 标记（常用衍射角）────────────────────────
    for angle in [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]:
        ax.axvline(angle, color="#DDDDDD", linewidth=0.3,
                   linestyle="-", zorder=1)

    # ── 图例 ─────────────────────────────────────────
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

    # ── 标题 ─────────────────────────────────────────
    ax.set_title(
        f"XRD Pattern of {sample_name}\n"
        f"Copper-Cobalt Ore Leaching Residue",
        fontsize=st["fontsize"] + 1,
        fontweight="bold",
        pad=10,
    )

    # ── 期刊要求说明文字 ──────────────────────────────
    if journal == "Minerals Engineering":
        caption = (
            "Fig. XRD diffraction pattern of copper-cobalt leaching residue. "
            "Cu Kα radiation (λ = 1.5406 Å). "
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
    print(f"  [PLOT] → {output_path}")
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
    多样品 XRD 对比图（Y轴偏移叠加，替代 Origin 堆叠图）
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
        # Y轴标签
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
    ax.set_title("XRD Patterns — Copper-Cobalt Leaching Residues",
                 fontsize=st["fontsize"] + 1, fontweight="bold", pad=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, format="png", bbox_inches="tight")
    plt.close(fig)
    print(f"  [PLOT] Comparison → {output_path}")
    return output_path


def plot_phase_pie(
    quantification: Dict[str, float],
    output_path: str,
    journal: str = "Minerals Engineering",
    dpi: int = 600,
) -> str:
    """物相定量饼图（补充 Rietveld 结果）"""
    if not quantification:
        print("  [SKIP] No quantification data")
        return ""

    st = JOURNAL_STYLE.get(journal, JOURNAL_STYLE["default"])
    labels = list(quantification.keys())
    sizes = list(quantification.values())
    # 取矿物短名
    labels_short = [l.split("_")[0] for l in labels]

    # 颜色分配
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
    print(f"  [PLOT] Pie chart → {output_path}")
    return output_path


def plot_peak_table(
    peaks: List[Dict],
    matched_phases: List[Dict],
    output_path: str,
    sample_name: str = "Y-2",
) -> str:
    """生成峰位表（PDF 或 PNG）"""
    fig, ax = plt.subplots(figsize=(12, max(3, len(peaks[:25]) * 0.4 + 1)))
    ax.axis("off")

    col_labels = ["#", r"$2\theta$ (°)", "I (a.u.)",
                  "Prominence", "Matched Phase", "hkl", r"$\Delta 2\theta$ (°)", "d (Å)"]

    # 构建表格数据
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
                    delta_cell = f"{mp['Δ2θ']:.3f}"
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

    # 表头样式
    for j in range(len(col_labels)):
        table[0, j].set_facecolor("#2C3E50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    for i in range(len(rows)):
        bg = "#EBF5FB" if i % 2 == 0 else "white"
        for j in range(len(col_labels)):
            table[i + 1, j].set_facecolor(bg)

    ax.set_title(f"Peak Table — {sample_name} XRD Analysis",
                 fontsize=11, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, format="png", bbox_inches="tight")
    plt.close(fig)
    print(f"  [PLOT] Peak table → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════
#  MAIN ANALYSIS PIPELINE
# ══════════════════════════════════════════════════════

def analyze_xrd(
    data_path: str,
    output_dir: Optional[str] = None,
    sample_name: str = "Y-2",
    smooth_window: int = 9,
    smooth_poly: int = 3,
    background_method: str = "ALS",   # "ALS" or "rolling"
    journal: str = "Minerals Engineering",
    peak_height_ratio: float = 0.03,
    peak_prominence: float = 0.008,
    peak_tolerance: float = 0.28,
    rietveld_width: float = 0.18,
    dpi: int = 600,
    run_quantification: bool = True,
    verbose: bool = True,
) -> Dict:
    """
    XRD 全流程自动化分析

    Parameters
    ----------
    data_path         : XRD 数据文件路径
    output_dir         : 输出目录（默认数据文件同目录/xrd_output/）
    sample_name        : 样品名称（用于图表标题和文件名）
    smooth_window/poly : SG 平滑参数
    background_method  : "ALS" (推荐) 或 "rolling"
    journal            : 目标期刊样式
    peak_height_ratio  : 寻峰最小高度比（相对最大峰 %）
    peak_prominence    : 峰突出度（归一化后）
    peak_tolerance     : 物相匹配容差（°）
    rietveld_width     : 定量峰宽 FWHM（°）
    dpi                : 图片分辨率
    run_quantification : 是否执行定量计算

    Returns
    -------
    report: dict（含所有结果）
    """
    t0 = time.time()
    dp = Path(data_path)
    out_dir = Path(output_dir) if output_dir else dp.parent / "xrd_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  XRD Analysis — Cu/Co Leaching Residue")
    print(f"  Sample : {sample_name}")
    print(f"  Data   : {dp.name}")
    print(f"  Output : {out_dir}")
    print(f"  Style  : {journal}")
    print(f"{sep}\n")

    # ── 1. 加载数据 ───────────────────────────────────
    print("[Step 1/7] Loading data ...")
    df = load_xrd_auto(str(dp))
    x = df["two_theta"].values.astype(np.float64)
    y_raw = df["intensity"].values.astype(np.float64)

    # ── 2. 平滑 & Kα2 去除 ────────────────────────────
    print("[Step 2/7] Preprocessing ...")
    y_sm = smooth_savgol(y_raw, window=smooth_window, poly=smooth_poly)
    y_kalpha = remove_kalpha2(x, y_sm)
    print(f"  [SMOOTH] SG(w={smooth_window}, p={smooth_poly})")
    print(f"  [Kα2]    Removed (Δ2θ=0.03°)")

    # ── 3. 背景扣除 ───────────────────────────────────
    print("[Step 3/7] Background subtraction ...")
    if background_method == "ALS":
        y_bkg = background_als(y_kalpha)
    else:
        y_bkg, _ = background_rolling_min(y_kalpha)
    y_net = np.maximum(y_kalpha - y_bkg, 0)
    print(f"  [BACKGROUND] {background_method} method applied")
    print(f"  [NET] Max intensity: {y_net.max():.1f} (bg-corrected)")

    # ── 4. 寻峰 ───────────────────────────────────────
    print("[Step 4/7] Peak detection ...")
    peaks = find_peaks_2theta(
        x, y_raw, y_bkg,
        height_ratio=peak_height_ratio,
        prominence=peak_prominence,
        distance=12,
    )
    print(f"  [PEAKS] Found {len(peaks)} peaks "
          f"(height ≥ {peak_height_ratio*100:.0f}%, promin. ≥ {peak_prominence:.3f})")
    if verbose and peaks:
        print("  Top 10 peaks:")
        for pk in peaks[:10]:
            print(f"    2θ={pk['two_theta']:.2f}°  "
                  f"I={pk['intensity']:.0f}  prom.={pk['prominence']:.3f}")

    # ── 5. 物相匹配 ───────────────────────────────────
    print("[Step 5/7] Phase matching ...")
    matched = match_phases(peaks, tol_2theta=peak_tolerance, min_matched=2)
    print(f"  [PHASES] Identified {len(matched)} candidate phases")
    for ph in matched[:6]:
        print(f"    ✓ {ph['name']:<45} "
              f"(matched {ph['n_matched']}/{ph['n_total']} peaks, "
              f"score={ph['score']:.4f})")

    # ── 6. 定量 ───────────────────────────────────────
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

    # ── 7. 绘图 ───────────────────────────────────────
    print("[Step 7/7] Generating figures ...")

    # 7a: 主图谱
    fig_main = out_dir / f"{sample_name}_XRD_main.{fmt_from_journal(journal)}"
    plot_xrd(
        x, y_raw, y_net, y_bkg, matched,
        output_path=str(fig_main),
        sample_name=sample_name,
        journal=journal,
        dpi=dpi,
    )

    # 7b: 峰位表
    fig_table = out_dir / f"{sample_name}_peak_table.png"
    plot_peak_table(peaks, matched, str(fig_table), sample_name=sample_name)

    # 7c: 定量饼图
    fig_pie = ""
    if quantification:
        fig_pie = plot_phase_pie(
            quantification,
            str(out_dir / f"{sample_name}_phase_pie.png"),
            journal=journal,
        )

    # ── 8. 生成 JSON 报告 ─────────────────────────────
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
            "wavelength": "Cu Kα 1.5406 Å",
        },
    }

    report_path = out_dir / f"{sample_name}_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  [REPORT] JSON → {report_path}")

    print(f"\n{sep}")
    print(f"  ✅ Analysis complete in {elapsed:.1f}s")
    print(f"  📁 Output: {out_dir}")
    print(f"{sep}\n")

    return report


def fmt_from_journal(journal: str) -> str:
    """根据期刊返回合适格式"""
    if journal == "Minerals Engineering":
        return "eps"
    return "png"


# ══════════════════════════════════════════════════════
#  BATCH PROCESSING
# ══════════════════════════════════════════════════════

def batch_analyze(
    data_dir: str,
    output_dir: str,
    sample_prefix: str = "",
    pattern: str = "*.txt",
    **kwargs,
) -> List[Dict]:
    """批量分析目录下所有 XRD 文件"""
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


# ══════════════════════════════════════════════════════
#  STANDALONE RUN
# ══════════════════════════════════════════════════════
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
                        help="Phase match tolerance (default 0.28°)")
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
