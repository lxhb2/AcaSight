import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from scipy.signal import find_peaks
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# Mineral database - using mathtext subscripts
# CuFeS2, FeS2, CuS, Cu2S, Cu5FeS4, SiO2, CaCO3, CaMg(CO3)2, MoS2, ZnS
MINERAL_DB = {
    "Chalcopyrite":  {"formula_tex": r"$\mathrm{CuFeS_2}$", "peaks": [29.42, 34.84, 36.63, 47.43, 56.98, 49.28], "color": "#C0392B"},
    "Pyrite":        {"formula_tex": r"$\mathrm{FeS_2}$",   "peaks": [28.51, 33.08, 37.10, 40.80, 47.42, 56.33], "color": "#D4AC0D"},
    "Covellite":     {"formula_tex": r"$\mathrm{CuS}$",    "peaks": [28.04, 31.78, 47.87, 56.54, 29.28],        "color": "#1A5276"},
    "Chalcocite":    {"formula_tex": r"$\mathrm{Cu_2S}$",  "peaks": [26.55, 30.08, 43.92, 47.87, 32.88],          "color": "#7D3C98"},
    "Bornite":       {"formula_tex": r"$\mathrm{Cu_5FeS_4}$", "peaks": [28.96, 31.26, 37.74, 46.14, 57.38],        "color": "#E67E22"},
    "Quartz":        {"formula_tex": r"$\mathrm{SiO_2}$",   "peaks": [20.85, 26.65, 36.54, 39.46, 42.45, 50.14],  "color": "#27AE60"},
    "Calcite":       {"formula_tex": r"$\mathrm{CaCO_3}$",  "peaks": [23.04, 29.42, 35.98, 39.42, 43.18, 47.48],  "color": "#16A085"},
    "Dolomite":      {"formula_tex": r"$\mathrm{CaMg(CO_3)_2}$", "peaks": [24.02, 30.92, 37.32, 41.18, 43.88, 51.08], "color": "#8E44AD"},
    "Molybdenite":   {"formula_tex": r"$\mathrm{MoS_2}$",   "peaks": [14.38, 32.67, 39.53, 44.14, 49.78, 58.33], "color": "#C0392B"},
    "Sphalerite":    {"formula_tex": r"$\mathrm{ZnS}$",    "peaks": [28.56, 33.08, 47.54, 56.44, 59.17, 76.95], "color": "#1E8449"},
}

STYLE = {
    "figsize_single": (5.8, 3.6),
    "figsize_compare": (9.0, 5.0),
    "fontsize": 9,
    "lw": 0.9,
    "tick_w": 0.5,
    "tick_dir": "out",
    "dpi": 600,
    "colors": ["#1A77C4", "#E64A19", "#2E7D32"],
}


def parse_raw(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    chunk = data[892:892+4000]
    vals = list(struct.unpack(f'<{len(chunk)//4}f', chunk))
    intensities = [vals[i] for i in range(3, len(vals), 4) if vals[i] >= 0]
    angles = np.linspace(5.0, 90.0, len(intensities))
    return angles, np.array(intensities)


def identify_minerals(angle, intensity, threshold=0.06, tolerance=0.55):
    norm = intensity / np.max(intensity)
    peak_idx, _ = find_peaks(norm, height=threshold, distance=8, prominence=0.025)
    sample_peaks = angle[peak_idx]

    identified = []
    for name, info in MINERAL_DB.items():
        ref_peaks = np.array(info["peaks"])
        matches, matched = [], []
        for rp in ref_peaks:
            for sp in sample_peaks:
                if abs(sp - rp) <= tolerance:
                    matches.append(rp)
                    matched.append(sp)
                    break
        if len(matches) >= 2:
            identified.append({
                "name": name,
                "formula_tex": info["formula_tex"],
                "ref_peaks": ref_peaks,
                "matched_peaks": matched,
                "score": len(matches) / len(ref_peaks),
                "color": info["color"]
            })
    identified.sort(key=lambda x: x["score"], reverse=True)
    return identified


def apply_style(ax):
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["font.size"] = STYLE["fontsize"]
    plt.rcParams["mathtext.fontset"] = "stix"
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)
        spine.set_color("black")
    ax.tick_params(direction=STYLE["tick_dir"], axis="both", which="major",
                  length=3.5, width=STYLE["tick_w"], labelsize=STYLE["fontsize"])
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    ax.grid(which="major", linestyle="-", linewidth=0.3, color="#CCCCCC", alpha=0.5)
    ax.grid(which="minor", linestyle=":", linewidth=0.15, color="#DDDDDD", alpha=0.35)
    ax.set_axisbelow(True)


def plot_single(angle, intensity, sample_name, minerals, output_path, color):
    fig, ax = plt.subplots(figsize=STYLE["figsize_single"], dpi=STYLE["dpi"])
    apply_style(ax)

    norm = intensity / np.max(intensity) * 100
    ax.plot(angle, norm, color=color, linewidth=STYLE["lw"])

    # Peak markers & labels
    ymax = 115
    ylim = ax.get_ylim()
    for i, m in enumerate(minerals[:5]):
        y_frac = 0.90 - i * 0.065
        y_pos = y_frac * ymax
        label_y = y_frac * ymax * 0.98
        # Draw tick line at reference peak position
        ax.axvline(x=m["ref_peaks"][0], color="#999999", linestyle="--",
                   linewidth=0.6, alpha=0.7)
        ax.annotate(f"{m['name']}\n{m['formula_tex']}",
                    xy=(m["ref_peaks"][0], y_pos),
                    fontsize=6, ha="center", va="top", rotation=90,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="none", alpha=0.9))

    ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=STYLE["fontsize"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=STYLE["fontsize"])
    ax.set_title(sample_name, fontsize=10, pad=8)
    ax.set_xlim(5, 90)
    ax.set_ylim(0, ymax)

    if minerals:
        ax.legend(
            [plt.Line2D([0], [0], color=m["color"], lw=1.2) for m in minerals[:5]],
            [f"{m['name']}  {m['formula_tex']}" for m in minerals[:5]],
            fontsize=6, loc="upper right", frameon=True,
            fancybox=False, edgecolor="#888888"
        )

    plt.tight_layout()
    fig.savefig(output_path, dpi=STYLE["dpi"], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {output_path}")


def plot_comparison(datasets, labels, output_path, offset=55):
    fig, ax = plt.subplots(figsize=STYLE["figsize_compare"], dpi=STYLE["dpi"])
    apply_style(ax)

    for i, (angle, intensity) in enumerate(datasets):
        norm = intensity / np.max(intensity) * 100
        ax.plot(angle, norm + i * offset, color=STYLE["colors"][i],
                linewidth=STYLE["lw"], label=labels[i])

    ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=STYLE["fontsize"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=STYLE["fontsize"])
    ax.legend(fontsize=8.5, loc="upper right", frameon=True,
              fancybox=False, edgecolor="#888888")
    x_min = min(d[0].min() for d in datasets)
    x_max = max(d[0].max() for d in datasets)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-8, len(datasets) * offset + 115)

    plt.tight_layout()
    fig.savefig(output_path, dpi=STYLE["dpi"], bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {output_path}")


def main():
    out_dir = Path(r"C:\Users\Administrator\.qclaw\workspace")

    files = [
        (r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw",
         "Copper Sulfide Raw Ore", "raw_ore_xrd.png"),
        (r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw",
         "Copper Sulfide Concentrate", "concentrate_xrd.png"),
        (r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw",
         "Copper Sulfide Tailings", "tailings_xrd.png"),
    ]

    datasets, mineral_results = [], []
    print("=" * 65)
    print("XRD Analysis for Copper Sulfide Ores")
    print("=" * 65)

    for i, (fp, sname, fname) in enumerate(files):
        print(f"\n[Sample {i+1}/3] {sname}")
        angle, intensity = parse_raw(fp)
        print(f"  Data points: {len(intensity)}, "
              f"Intensity range: {np.min(intensity):.1f} - {np.max(intensity):.1f}")
        print(f"  2theta range: {angle[0]:.1f} - {angle[-1]:.1f}")

        minerals = identify_minerals(angle, intensity)
        mineral_results.append(minerals)
        datasets.append((angle, intensity))

        print(f"  Identified minerals ({len(minerals)}):")
        for m in minerals[:6]:
            peaks_str = ", ".join([f"{p:.2f}" for p in m["matched_peaks"]])
            print(f"    + {m['name']:15s} {m['formula_tex']}  peaks: {peaks_str}")
        if not minerals:
            print("    No matches found")

        plot_single(angle, intensity, sname, minerals,
                    str(out_dir / fname), STYLE["colors"][i])

    print(f"\n[4/4] Generating comparison plot...")
    labels = ["Raw Ore", "Concentrate", "Tailings"]
    plot_comparison(datasets, labels,
                    str(out_dir / "copper_sulfide_comparison.png"), offset=55)

    print("\n" + "=" * 65)
    print("Done! Generated files:")
    print("  1. raw_ore_xrd.png")
    print("  2. concentrate_xrd.png")
    print("  3. tailings_xrd.png")
    print("  4. copper_sulfide_comparison.png")
    print("=" * 65)


if __name__ == "__main__":
    main()
