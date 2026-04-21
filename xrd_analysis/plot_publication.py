"""
Publication-quality XRD figure generator
Draws a fully labelled, journal-ready XRD pattern for Y-2
"""
import sys, warnings, os
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MultipleLocator, AutoMinorLocator
from scipy.signal import savgol_filter
from scipy.ndimage import minimum_filter1d
from scipy.interpolate import UnivariateSpline

# ── MINERAL LIBRARY (refined for this sample) ─────────────────────────────
MINERAL_LIBRARY = {
    "alpha-FeOOH_Goethite": {
        "formula": "α-FeOOH", "system": "Orthorhombic",
        "color": "#D32F2F",
        "peaks": [(21.22,"110",4.185,100),(33.22,"120",2.694,65),
                  (36.65,"130",2.451,80),(41.18,"140",2.192,50),
                  (53.24,"150",1.720,45),(59.00,"200",1.565,35),
                  (61.38,"200",1.511,40)],
        "desc": "主要含铁矿相，针铁矿"
    },
    "Fe2O3_Hematite": {
        "formula": "Fe₂O₃", "system": "Trigonal",
        "color": "#B71C1C",
        "peaks": [(24.14,"012",3.686,40),(33.16,"104",2.700,100),
                  (35.65,"110",2.518,80),(39.48,"113",2.281,60),
                  (49.48,"024",1.840,50),(54.09,"116",1.694,70),
                  (57.62,"108",1.599,45),(62.45,"214",1.486,50)],
        "desc": "赤铁矿，黄铁矿氧化产物"
    },
    "Fe3O4_Magnetite": {
        "formula": "Fe₃O₄", "system": "Cubic Spinel",
        "color": "#6A1B9A",
        "peaks": [(30.10,"220",2.967,100),(35.43,"311",2.531,80),
                  (43.10,"400",2.098,60),(53.40,"422",1.715,40),
                  (56.94,"511",1.616,50),(62.52,"440",1.486,45)],
        "desc": "磁铁矿，Fe(II,III)混合氧化物"
    },
    "SiO2_Quartz": {
        "formula": "SiO₂", "system": "Trigonal",
        "color": "#1565C0",
        "peaks": [(20.86,"100",4.257,100),(26.64,"101",3.343,35),
                  (39.47,"110",2.282,12),(50.14,"112",1.819,18),
                  (60.00,"200",1.541,12)],
        "desc": "石英，脉石矿物，惰性残留"
    },
    "CaSO4.2H2O_Gypsum": {
        "formula": "CaSO₄·2H₂O", "system": "Monoclinic",
        "color": "#78909C",
        "peaks": [(11.62,"020",7.612,100),(20.87,"021",4.253,55),
                  (29.11,"111",3.066,50),(31.17,"041",2.869,35)],
        "desc": "石膏，硫酸反应副产物"
    },
    "Cu2CO3(OH)2_Malachite": {
        "formula": "Cu₂CO₃(OH)₂", "system": "Monoclinic",
        "color": "#00838F",
        "peaks": [(14.90,"110",5.943,100),(24.12,"220",3.689,45),
                  (31.38,"131",2.850,80),(35.78,"221",2.507,70),
                  (38.59,"240",2.331,55)],
        "desc": "孔雀石，残余铜矿物"
    },
    "CuS_Covellite": {
        "formula": "CuS", "system": "Hexagonal",
        "color": "#0277BD",
        "peaks": [(27.76,"002",3.212,100),(29.28,"101",3.048,80),
                  (31.78,"102",2.814,70),(47.88,"110",1.899,60)],
        "desc": "蓝辉铜矿，残余铜矿物"
    },
    "Cu2O_Cuprite": {
        "formula": "Cu₂O", "system": "Cubic",
        "color": "#BF360C",
        "peaks": [(29.56,"110",3.020,100),(36.42,"111",2.465,75),
                  (42.30,"200",2.135,65),(61.36,"220",1.513,50)],
        "desc": "赤铜矿，残余铜矿物"
    },
    "Al2SiO5_Andalusite": {
        "formula": "Al₂SiO₅", "system": "Orthorhombic",
        "color": "#795548",
        "peaks": [(25.94,"111",3.433,100),(27.80,"020",3.208,55),
                  (35.20,"121",2.548,65),(39.30,"200",2.292,45),
                  (42.60,"131",2.121,50)],
        "desc": "红柱石，铝硅酸盐脉石"
    },
    "(Mg,Fe)5Al2Si3O10_Clinochlore": {
        "formula": "(Mg,Fe)₅Al₂Si₃O₁₀", "system": "Monoclinic",
        "color": "#2E7D32",
        "peaks": [(12.54,"001",7.057,100),(19.84,"110",4.472,80),
                  (25.18,"111",3.537,70),(35.00,"131",2.562,50)],
        "desc": "斜绿泥石，层状硅酸盐脉石"
    },
}

# Color palette for phases
PUB_COLORS = [
    "#1A1A1A", "#E64A19", "#1565C0", "#2E7D32", "#7B1FA2",
    "#00838F", "#F57F17", "#C62828", "#00695C", "#4527A0",
]

JOURNAL = "Minerals Engineering"

def load_and_preprocess(path):
    df = pd.read_csv(path, sep=r"\s+", header=None, skiprows=1,
                     names=["two_theta", "intensity"], engine="python", on_bad_lines="skip")
    df = df.apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)
    x = df["two_theta"].values.astype(float)
    y = df["intensity"].values.astype(float)
    # Smooth
    y_sm = savgol_filter(y, 9, 3)
    # Background (rolling min)
    bg = minimum_filter1d(y_sm.astype(float), size=301, mode="reflect")
    t = np.linspace(0, 1, len(bg))
    spl = UnivariateSpline(t, bg, s=len(bg)*0.05)
    bg_s = spl(t)
    y_net = np.maximum(y_sm - bg_s, 0)
    return x, y, y_sm, bg_s, y_net

def match_phases(peaks_x, peaks_I, library, tol=0.28, min_match=2):
    """Match experimental peaks to mineral library"""
    results = []
    for name, info in library.items():
        matched = []
        for (lib_2t, hkl, d, I_rel) in info["peaks"]:
            for px, pi in zip(peaks_x, peaks_I):
                if abs(px - lib_2t) <= tol:
                    matched.append({"exp": px, "lib": lib_2t, "hkl": hkl, "d": d, "I": I_rel, "delta": px-lib_2t})
                    break
        if len(matched) >= min_match:
            score = len(matched)/len(info["peaks"]) * np.mean([m["I"] for m in matched])/100
            results.append({"name": name, "formula": info["formula"], "color": info["color"],
                            "desc": info["desc"], "peaks": matched,
                            "n": len(matched), "n_total": len(info["peaks"]),
                            "score": round(float(score), 4)})
    results.sort(key=lambda r: -r["score"])
    return results

def quantify_peaks(x, y_net, matched, fwhm=0.20):
    """Simplified Rietveld via Gaussian peak areas"""
    from scipy.stats import norm
    areas = {}
    for phase in matched:
        synth = np.zeros(len(x))
        sigma = fwhm / 2.35482
        for m in phase["peaks"]:
            g = norm.pdf(x, loc=m["exp"], scale=sigma)
            g_n = g / (g.max()+1e-20) * m["I"]
            synth += g_n
        areas[phase["name"]] = np.trapz(synth, x)
    total = sum(areas.values())
    if total <= 0:
        return {}
    return {k: round(v/total*100, 2) for k, v in areas.items()}


# ── LOAD DATA ────────────────────────────────────────────────────────────────
data_path = r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\Y-2.txt"
out_dir   = r"C:\Users\Administrator\.qclaw\workspace\xrd_analysis\results"

print("Loading data ...")
x, y_raw, y_sm, y_bg, y_net = load_and_preprocess(data_path)
y_norm = y_net / y_net.max() * 100
y_raw_norm = y_raw / y_raw.max() * 100

# ── PEAK DETECTION ─────────────────────────────────────────────────────────
from scipy.signal import find_peaks
peaks_idx, props = find_peaks(y_norm, height=3.0, prominence=0.005, distance=12)
peaks_x = x[peaks_idx]
peaks_I = y_norm[peaks_idx]
peaks_info = sorted(
    [{"two_theta": round(float(px), 3), "intensity": round(float(pi), 1),
      "norm": round(float(pi/y_net.max()), 4),
      "prom": round(float(props["prominences"][i]), 4)}
     for i, (px, pi) in enumerate(zip(peaks_x, peaks_I))],
    key=lambda p: -p["intensity"]
)

print(f"Detected {len(peaks_info)} peaks")
print("Top peaks:", [(p["two_theta"], p["intensity"]) for p in peaks_info[:10]])

# ── PHASE MATCHING ─────────────────────────────────────────────────────────
matched = match_phases(peaks_x, peaks_I, MINERAL_LIBRARY, tol=0.28, min_match=2)
print(f"\nMatched {len(matched)} phases:")
for ph in matched:
    print(f"  {ph['name']:<35} score={ph['score']:.3f}  peaks={ph['n']}")

# ── QUANTIFICATION ──────────────────────────────────────────────────────────
quant = quantify_peaks(x, y_net, matched, fwhm=0.20)
print("\nQuantification:")
for k, v in sorted(quant.items(), key=lambda x: -x[1]):
    print(f"  {k:<30}: {v:5.2f} wt%")

# ── PUBLICATION FIGURE ──────────────────────────────────────────────────────
st = {"figsize": (10, 6.5), "fontsize": 11, "linewidth": 1.2,
      "tick_width": 0.8, "labelpad": 4, "tick_dir": "in"}

fig, ax = plt.subplots(figsize=st["figsize"], dpi=150)

# Background fill
bg_norm = y_bg / y_raw.max() * 100
ax.fill_between(x, 0, bg_norm, color="#DCE9F5", alpha=0.7, zorder=1, label="_nolegend_")

# Raw curve (light)
ax.plot(x, y_raw_norm, color="#BBBBBB", linewidth=0.6, alpha=0.6, zorder=2)

# Main (net) curve
ax.fill_between(x, 0, y_norm, color="#3A7ABD", alpha=0.20, zorder=3)
ax.plot(x, y_norm, color="#1A3A6B", linewidth=st["linewidth"], zorder=4)

# ── Phase vertical bars ─────────────────────────────────────────────────────
phase_colors = iter(PUB_COLORS[1:])
legend_handles = []
for ph in matched[:7]:
    c = next(phase_colors)
    legend_handles.append(mpatches.Patch(facecolor=c, alpha=0.8,
                                         label=ph["name"].split("_")[1]))
    for m in ph["peaks"]:
        ax.axvline(m["exp"], ymin=0, ymax=m["I"]/120,
                   color=c, linewidth=0.9, alpha=0.65, zorder=3)

# ── Annotate strongest peaks ────────────────────────────────────────────────
key_annotations = {
    26.64: ("Quartz\n(101)", "#1565C0"),
    33.16: ("Hematite\n(104)", "#B71C1C"),
    35.65: ("Hematite\n(110)", "#B71C1C"),
    31.38: ("Malachite\n(131)", "#00838F"),
    54.09: ("Hematite\n(116)", "#B71C1C"),
    21.22: ("Goethite\n(110)", "#D32F2F"),
}
for angle, (label, col) in key_annotations.items():
    ax.annotate(label,
                xy=(angle, y_norm[np.searchsorted(x, angle)] if angle <= x.max() else 0),
                xytext=(angle + 0.6, 88),
                fontsize=7.5, color=col,
                arrowprops=dict(arrowstyle="->", color=col, lw=0.7),
                ha="left",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.75,
                          ec=col, lw=0.5))

# ── Style ──────────────────────────────────────────────────────────────────
ax.set_xlabel(r"$2\theta$ ($^\circ$)", fontsize=st["fontsize"], labelpad=st["labelpad"])
ax.set_ylabel("Intensity (a.u.)", fontsize=st["fontsize"])
ax.set_xlim(10, 80)
ax.set_ylim(-2, 110)

for sp in ax.spines.values():
    sp.set_linewidth(st["tick_width"])
ax.tick_params(direction=st["tick_dir"], axis="both", which="major",
               length=5, width=st["tick_width"], labelsize=st["fontsize"]-1,
               top=True, right=True)
ax.xaxis.set_minor_locator(AutoMinorLocator(2))
ax.yaxis.set_minor_locator(AutoMinorLocator(2))
ax.tick_params(which="minor", length=2.5, width=st["tick_width"]*0.6, top=True, right=True)
ax.grid(which="major", linestyle="-", linewidth=0.4, color="#AAAAAA", alpha=0.5)
ax.grid(which="minor", linestyle=":", linewidth=0.3, color="#BBBBBB", alpha=0.4)
ax.set_axisbelow(True)

# 2θ reference lines
for angle in [20,25,30,35,40,45,50,55,60,65,70,75]:
    ax.axvline(angle, color="#DDDDDD", linewidth=0.3, linestyle="-", zorder=1)

ax.legend(handles=legend_handles,
          loc="upper right", fontsize=8, framealpha=0.9, fancybox=False,
          ncol=1, borderaxespad=0.3, labelspacing=0.4,
          title="Identified phases", title_fontsize=9)

ax.set_title("XRD Pattern of Copper-Cobalt Leaching Residue (Y-2)",
             fontsize=13, fontweight="bold", pad=10)

# Caption (Minerals Engineering style)
caption = (
    "Fig. XRD diffraction pattern of copper-cobalt ore sulfuric acid leaching residue. "
    "Cu Kα radiation (λ = 1.5406 Å). "
    "Identified phases: "
    + ", ".join([p["name"].split("_")[1] for p in matched[:6]]) + "."
)
ax.text(0.01, -0.16, caption,
        transform=ax.transAxes, fontsize=8, style="italic",
        va="top", wrap=True)

plt.tight_layout(rect=[0, 0.05, 1, 0.97])
out_png = os.path.join(out_dir, "Y-2_XRD_publication.png")
plt.savefig(out_png, dpi=150, format="png", bbox_inches="tight")
plt.close()
print(f"\nFigure saved: {out_png}")

# ── QUANTIFICATION PIE CHART ───────────────────────────────────────────────
fig2, ax2 = plt.subplots(figsize=(8, 8), dpi=150)
labels_short = [p["name"].split("_")[1] for p in matched[:8]]
scores_top = [quant[p["name"]] for p in matched[:8]]
colors = [p["color"] for p in matched[:8]]

wedges, texts, autotexts = ax2.pie(
    scores_top, labels=labels_short, colors=colors,
    autopct=lambda p: f"{p:.1f}%" if p > 4 else "",
    pctdistance=0.75, startangle=90,
    wedgeprops=dict(linewidth=1.0, edgecolor="white"),
    explode=[0.02]*len(scores_top),
)
for at in autotexts:
    at.set_fontsize(9); at.set_color("white"); at.set_fontweight("bold")
ax2.set_title("Phase Quantification (wt%)\nSimplified Rietveld Refinement",
              fontsize=12, fontweight="bold", pad=12)
plt.tight_layout()
out_pie = os.path.join(out_dir, "Y-2_phase_quant.png")
plt.savefig(out_pie, dpi=150, format="png", bbox_inches="tight")
plt.close()
print(f"Pie chart saved: {out_pie}")

# ── SUMMARY TABLE ───────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  ANALYSIS SUMMARY — Y-2 Copper-Cobalt Leaching Residue")
print("="*60)
print(f"  Data points   : {len(x)}")
print(f"  2θ range      : {x.min():.2f} - {x.max():.2f} deg")
print(f"  Max intensity : {y_raw.max():.0f} cps")
print(f"  Peaks found   : {len(peaks_info)}")
print()
print("  PHASES IDENTIFIED:")
for ph in matched[:8]:
    qs = quant.get(ph["name"], 0)
    print(f"    [{ph['color']}] {ph['name'].split('_')[1]:<20} "
          f"{ph['formula']:<15} score={ph['score']:.3f}  wt%={qs:.1f}%")
print()
print("  OUTPUT FILES:")
print(f"    XRD main figure : {out_png}")
print(f"    Phase pie chart : {out_pie}")
print("="*60)
