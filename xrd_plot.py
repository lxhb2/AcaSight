#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
铜硫矿 XRD 学术级绘图脚本
  1. 三样品堆叠对比图（含 PDF 标准峰竖线）
  2. 三张单样品物相标注图（峰位标号 + 右上角物相列表）
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import numpy as np
import os
from pathlib import Path

# ── 中文字体 ──────────────────────────────────────────────
CHINESE_FONTS = ["SimHei", "Microsoft YaHei", "SimSun", "Arial"]
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = CHINESE_FONTS
plt.rcParams['axes.unicode_minus'] = False

# ── 路径配置 ───────────────────────────────────────────────
DATA_DIR = Path(r"F:\桌面\王铨毕业论文\xrd数据")
FILE_RAW  = DATA_DIR / "tongliukuang yuankuang.txt"
FILE_CONC = DATA_DIR / "2cu2jing jingkuang tongliukuang_converted.txt"
FILE_TAIL = DATA_DIR / "2cu2jing weikuang tongliukuang.txt"

LABEL_RAW  = "原矿 (Raw Ore)"
LABEL_CONC = "精矿 (Concentrate)"
LABEL_TAIL = "尾矿 (Tailings)"

OUT_DIR = Path(r"F:\桌面\王铨毕业论文\xrd数据")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 颜色 ────────────────────────────────────────────────────
C_RAW  = "#1F4E79"
C_CONC = "#C00000"
C_TAIL = "#2E7D32"

# ── PDF 标准卡片衍射峰（2θ, 相对强度%）──────────────────────
PDF_CARDS = {
    "SiO2 (PDF#46-1045)": [
        (20.85, 35), (26.65, 100), (36.54, 12), (39.47, 15),
        (42.45, 8), (50.14, 20), (55.06, 6), (60.00, 28), (68.15, 17),
    ],
    "Cu2S (PDF#33-0490)": [
        (26.55, 100), (30.04, 40), (31.18, 45),
        (37.78, 20), (45.92, 35), (46.02, 30), (53.78, 18),
    ],
    "CuFeS2 (PDF#37-0475)": [
        (29.42, 100), (33.10, 10), (36.63, 12),
        (48.72, 10), (57.88, 20), (59.02, 15),
    ],
    "CuS (PDF#06-0464)": [
        (26.96, 50), (28.01, 30), (31.38, 30),
        (33.05, 100), (47.92, 40), (52.68, 30), (59.40, 20),
    ],
    "FeS2 (PDF#42-1340)": [
        (28.51, 30), (33.07, 55), (37.09, 30), (40.79, 55),
        (47.45, 30), (56.28, 100), (59.02, 40),
    ],
}

PHASES_RAW = [
    ("SiO2 (PDF#46-1045)",   C_RAW),
    ("Cu2S (PDF#33-0490)",   C_CONC),
]
PHASES_CONC = [
    ("CuFeS2 (PDF#37-0475)", C_CONC),
    ("Cu2S (PDF#33-0490)",   "#8B4513"),
    ("FeS2 (PDF#42-1340)",   C_TAIL),
]
PHASES_TAIL = [
    ("SiO2 (PDF#46-1045)",   C_RAW),
    ("FeS2 (PDF#42-1340)",   C_TAIL),
]

# ── 辅助函数 ───────────────────────────────────────────────
def load_xrd_txt(filepath):
    """读取 XRD txt/csv 数据文件"""
    angles, intensities = [], []
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            line = line.rstrip(',').strip()
            parts = [p.strip() for p in line.split(',')] if ',' in line else line.split()
            if len(parts) >= 2:
                try:
                    a, i = float(parts[0]), float(parts[1])
                    if i < 0:
                        continue
                    angles.append(a)
                    intensities.append(i)
                except ValueError:
                    continue
    return np.array(angles), np.array(intensities)


def clip_xy(x, y, xmin, xmax):
    """截取X范围内的数据"""
    mask = (x >= xmin) & (x <= xmax)
    return x[mask], np.maximum(y[mask], 0.0)


# ── 峰检测 ──────────────────────────────────────────────────
def detect_peaks(x, y, label):
    """
    基于样品类型自适应峰检测，返回 (peak_x, peak_y) 数组
    - 精矿：高分辨率数据，只在 20-60° 局部用大窗口 savgol，prominence=8%
    - 原矿/尾矿：小窗口 savgol，全谱 5-80°，prominence=5%
    """
    from scipy.signal import find_peaks, savgol_filter

    is_conc = "Concentrate" in label

    if is_conc:
        # 精矿：仅在 20-60° 局部检峰（大窗口平滑降噪）
        m2 = (x >= 20) & (x <= 60)
        ys = savgol_filter(y[m2], window_length=51, polyorder=3)
        peaks, _ = find_peaks(ys,
                              height=ys.max() * 0.30,
                              prominence=ys.max() * 0.08,
                              distance=20)
        px = x[m2][peaks]
        py = ys[peaks]                    # ← 从平滑数据取峰高，避免索引 bug
        # 补充低角区主峰（5-12°），标为"石英"
        if len(px) < 4:
            m_low = (x >= 5) & (x <= 12)
            if m_low.sum() > 50:
                ys_l = savgol_filter(y[m_low], window_length=21, polyorder=3)
                pk_l, _ = find_peaks(ys_l, height=ys_l.max()*0.5, prominence=ys_l.max()*0.2)
                if len(pk_l) > 0:
                    top = pk_l[np.argmax(ys_l[pk_l])]
                    px = np.append(px, x[m_low][top])
                    py = np.append(py, ys_l[top])
    else:
        # 原矿/尾矿：小窗口平滑，保留真实峰形
        ys = savgol_filter(y, window_length=7, polyorder=3)
        peaks, _ = find_peaks(ys,
                              height=ys.max() * 0.08,
                              prominence=ys.max() * 0.04,
                              distance=10)
        px = x[peaks]
        py = ys[peaks]

    if len(px) == 0:
        idx = np.argmax(y)
        px = np.array([x[idx]])
        py = np.array([y[idx]])

    # 取最强前 8 个
    if len(px) > 8:
        idx = np.argsort(py)[-8:]
        px = px[np.sort(idx)]
        py = py[np.sort(idx)]

    return px, py


# ── 物相自动指认 ──────────────────────────────────────────
def assign_phases(px, py, label):
    """
    根据实测峰位置与 PDF 标准峰最近距离，自动指认物相
    返回 dict: {峰序号(int): "矿物名 英文名"}
    """
    # PDF 参考峰（取每个矿物最强的那条）
    pdf_ref = [
        (20.85, "SiO2"),
        (26.65, "SiO2"),
        (29.42, "CuFeS2"),
        (31.18, "Cu2S"),
        (33.05, "CuS"),
        (36.54, "SiO2"),
        (50.14, "SiO2"),
        (56.28, "FeS2"),
        (57.88, "CuFeS2"),
        (59.40, "CuS"),
        (60.00, "SiO2"),
    ]
    # 中文名称映射
    name_cn = {
        "SiO2":    "石英 SiO2",
        "CuFeS2":  "黄铜矿 CuFeS2",
        "Cu2S":    "辉铜矿 Cu2S",
        "CuS":     "铜蓝 CuS",
        "FeS2":    "黄铁矿 FeS2",
    }

    assignments = {}
    used_phases = {}          # 防止同一个矿物重复指给不同峰
    for i, p in enumerate(px):
        diffs = [(abs(p - ref), ph) for ref, ph in pdf_ref]
        diffs.sort()
        best_delta, best_ph = diffs[0]
        # 如果该矿物已用过，选次优
        if best_ph in used_phases and len(diffs) > 1:
            for delta, ph in diffs[1:]:
                if ph not in used_phases:
                    best_delta, best_ph = delta, ph
                    break
        used_phases[best_ph] = best_delta
        assignments[i + 1] = name_cn.get(best_ph, best_ph)
    return assignments


# ── 图1：三样品堆叠对比图 ──────────────────────────────────
def plot_stacked_comparison(angles_raw, ints_raw,
                            angles_conc, ints_conc,
                            angles_tail, ints_tail,
                            output_path):
    def prep(y):
        mn, mx = y.min(), y.max()
        return (y - mn) / (mx - mn) * 1.08

    yr, yc, yt = prep(ints_raw), prep(ints_conc), prep(ints_tail)
    yr_w, yc_w, yt_w = yr * 1.0, yc * 0.85, yt * 0.70

    s1, s2, s3 = 0.0, 1.00, 2.00
    x_min, x_max = 5, 80
    xr1, yr1 = clip_xy(angles_raw,  yr_w + s1, x_min, x_max)
    xr2, yr2 = clip_xy(angles_conc, yc_w + s2, x_min, x_max)
    xr3, yr3 = clip_xy(angles_tail, yt_w + s3, x_min, x_max)

    y1_top = yr_w.max()
    y2_top = yc_w.max()
    y3_top = yt_w.max()
    y_top_global = s3 + y3_top

    fig, ax = plt.subplots(figsize=(14, 8.5))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.plot(xr1, yr1, color=C_RAW,  linewidth=1.2)
    ax.plot(xr2, yr2, color=C_CONC, linewidth=1.2)
    ax.plot(xr3, yr3, color=C_TAIL, linewidth=1.2)

    # 样品名
    ax.text(0.025, (s1 + y1_top) / y_top_global, LABEL_RAW,
            transform=ax.transAxes, fontsize=11, color=C_RAW,
            fontweight='bold', va='bottom')
    ax.text(0.025, (s2 + y2_top) / y_top_global, LABEL_CONC,
            transform=ax.transAxes, fontsize=11, color=C_CONC,
            fontweight='bold', va='bottom')
    ax.text(0.025, (s3 + y3_top) / y_top_global, LABEL_TAIL,
            transform=ax.transAxes, fontsize=11, color=C_TAIL,
            fontweight='bold', va='bottom')

    # PDF 标准峰竖线
    phase_colors = {
        "SiO2 (PDF#46-1045)":   C_RAW,
        "Cu2S (PDF#33-0490)":   C_CONC,
        "CuFeS2 (PDF#37-0475)": C_CONC,
        "CuS (PDF#06-0464)":    "#8B4513",
        "FeS2 (PDF#42-1340)":   C_TAIL,
    }
    spectrum_phases = [
        (s1, y1_top, PHASES_RAW),
        (s2, y2_top, PHASES_CONC),
        (s3, y3_top, PHASES_TAIL),
    ]
    drawn = {}
    for base_shift, y_top, phases in spectrum_phases:
        for phase_name, pcolor in phases:
            if phase_name in drawn:
                continue
            drawn[phase_name] = True
            color = phase_colors.get(phase_name, '#555555')
            for tth, rel_int in PDF_CARDS.get(phase_name, []):
                if not (x_min <= tth <= x_max):
                    continue
                h = (rel_int / 100.0) * y_top * 0.88
                ax.vlines(tth, base_shift, base_shift + h,
                          color=color, linewidth=1.6, alpha=0.65)
                ax.hlines(base_shift + h, tth - 0.20, tth + 0.20,
                          color=color, linewidth=1.6, alpha=0.65)

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-0.18, y_top_global + 0.08)
    ax.set_xlabel("2θ (°)", fontsize=13)
    ax.set_ylabel("Intensity (a.u.)", fontsize=13)
    ax.set_xticks(np.arange(10, 85, 5))
    ax.tick_params(axis='both', labelsize=11)
    ax.tick_params(axis='x', direction='in', length=5, width=1.2, bottom=True)
    ax.tick_params(axis='y', direction='in', length=5, width=1.2, left=True)

    # 上/右轴线（无刻度）
    for ax2 in [ax.twiny(), ax.twinx()]:
        ax2.tick_params(length=0)
        ax2.spines['top'].set_linewidth(1.2)
        ax2.spines['right'].set_linewidth(1.2)
        ax2.spines['left'].set_visible(False)
        ax2.spines['bottom'].set_visible(False)
        ax2.set_xlim(ax.get_xlim())
        ax2.set_ylim(ax.get_ylim())

    patches = [
        mpatches.Patch(color=C_RAW,  label=LABEL_RAW),
        mpatches.Patch(color=C_CONC, label=LABEL_CONC),
        mpatches.Patch(color=C_TAIL, label=LABEL_TAIL),
    ]
    ax.legend(handles=patches, loc='upper right', fontsize=10,
              frameon=True, framealpha=0.92, edgecolor='gray', fancybox=False)

    plt.tight_layout(pad=1.5)
    fig.savefig(output_path, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"[OK] 堆叠对比图已保存: {output_path}")


# ── 图2-4：单样品物相标注图 ─────────────────────────────────
def plot_single_sample(angle, intensity, label, phases, output_path, color='#1F4E79'):
    from scipy.signal import find_peaks, savgol_filter

    mask = (angle >= 5) & (angle <= 80)
    x, y = angle[mask], intensity[mask]

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    ax.plot(x, y, color=color, linewidth=1.2)
    ax.fill_between(x, y, alpha=0.08, color=color)

    # ── 峰检测 ────────────────────────────────────────────
    px, py = detect_peaks(x, y, label)

    # ── 自动物相指认 ──────────────────────────────────────
    phase_assign = assign_phases(px, py, label)

    # ── 峰位数字标注（圆圈+数字） ─────────────────────────
    for i, (bx, by) in enumerate(zip(px, py), start=1):
        ax.annotate(str(i),
                    xy=(bx, by),
                    xytext=(bx, by + y.max() * 0.065),
                    ha='center', va='bottom',
                    fontsize=11, fontweight='bold', color=color,
                    bbox=dict(boxstyle='circle,pad=0.2',
                              fc='white', ec=color, lw=1.0, alpha=0.9))

    # ── PDF 标准峰竖线 ────────────────────────────────────
    phase_colors = {
        "SiO2 (PDF#46-1045)":   C_RAW,
        "Cu2S (PDF#33-0490)":    C_CONC,
        "CuFeS2 (PDF#37-0475)": C_CONC,
        "CuS (PDF#06-0464)":    "#8B4513",
        "FeS2 (PDF#42-1340)":   C_TAIL,
    }
    drawn = {}
    for phase_name, pcolor in phases:
        if phase_name not in drawn:
            drawn[phase_name] = True
            color_p = phase_colors.get(phase_name, '#555555')
            for tth, rel_int in PDF_CARDS.get(phase_name, []):
                if 5 <= tth <= 80:
                    h = (rel_int / 100.0) * y.max() * 0.22
                    ax.plot([tth, tth], [-y.max() * 0.03, -y.max() * 0.03 + h],
                            color=color_p, linewidth=1.5, alpha=0.50,
                            linestyle='--', solid_capstyle='butt')

    # ── 右上角物相列表（无边框） ────────────────────────────
    legend_items = [f"{i} — {phase_assign.get(i, '')}" for i in range(1, len(px) + 1)]
    legend_text = "  " + "\n  ".join(legend_items)
    ax.text(0.98, 0.97, "Peak Index:\n" + legend_text,
            transform=ax.transAxes,
            fontsize=10, va='top', ha='right',
            bbox=dict(boxstyle='square,pad=0.4',
                      fc='white', edgecolor='none', alpha=0.90))

    # ── 坐标轴 ────────────────────────────────────────────
    ax.set_xlim(5, 80)
    ax.set_ylim(-y.max() * 0.05, y.max() * 1.18)
    ax.set_xlabel("2θ (°)", fontsize=13)
    ax.set_ylabel("Intensity (cps)", fontsize=13)
    ax.set_xticks(np.arange(10, 85, 5))
    ax.tick_params(axis='both', labelsize=11)
    ax.tick_params(axis='x', direction='in', length=5, width=1.2, bottom=True)
    ax.tick_params(axis='y', direction='in', length=5, width=1.2, left=True)

    # 上/右轴线（无刻度）
    ax_top = ax.twiny()
    ax_top.tick_params(length=0)
    ax_top.spines['top'].set_linewidth(1.2)
    ax_top.spines['right'].set_visible(False)
    ax_top.spines['left'].set_visible(False)
    ax_top.spines['bottom'].set_visible(False)
    ax_top.set_xlim(ax.get_xlim())

    ax_right = ax.twinx()
    ax_right.tick_params(length=0)
    ax_right.spines['right'].set_linewidth(1.2)
    ax_right.spines['top'].set_visible(False)
    ax_right.spines['left'].set_visible(False)
    ax_right.spines['bottom'].set_visible(False)
    ax_right.set_ylim(ax.get_ylim())

    ax.set_title(label, fontsize=14, fontweight='bold', pad=10)

    plt.tight_layout(pad=1.5)
    fig.savefig(output_path, dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"[OK] 单样品图已保存: {output_path}")


# ── 主程序 ──────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  铜硫矿 XRD 学术绘图")
    print("=" * 55)

    print(">>> 读取 XRD 数据...")
    ang_raw,  int_raw  = load_xrd_txt(FILE_RAW)
    ang_conc, int_conc = load_xrd_txt(FILE_CONC)
    ang_tail, int_tail = load_xrd_txt(FILE_TAIL)
    print(f"    原矿: {len(ang_raw)}  数据点")
    print(f"    精矿: {len(ang_conc)}  数据点")
    print(f"    尾矿: {len(ang_tail)}  数据点")

    # 峰检测预览
    print("\n>>> 峰检测预览...")
    for name, ang, ints, label in [
        ("原矿", ang_raw, int_raw, LABEL_RAW),
        ("精矿", ang_conc, int_conc, LABEL_CONC),
        ("尾矿", ang_tail, int_tail, LABEL_TAIL),
    ]:
        ang = ang[ints >= 0]; ints = ints[ints >= 0]
        m = (ang >= 5) & (ang <= 80)
        px, py = detect_peaks(ang[m], ints[m], label)
        assign = assign_phases(px, py, label)
        print(f"    {name}: {[f'{p:.1f}°→{assign[i+1]}' for i,p in enumerate(px)]}")

    print("\n>>> [1/4] 绘制三样品堆叠对比图...")
    plot_stacked_comparison(
        ang_raw, int_raw, ang_conc, int_conc, ang_tail, int_tail,
        OUT_DIR / "XRD_三合一堆叠图_学术版.png"
    )

    print("\n>>> [2/4] 绘制原矿单样品标注图...")
    plot_single_sample(ang_raw, int_raw, LABEL_RAW, PHASES_RAW,
                       OUT_DIR / "XRD_原矿_物相标注.png", color=C_RAW)

    print("\n>>> [3/4] 绘制精矿单样品标注图...")
    plot_single_sample(ang_conc, int_conc, LABEL_CONC, PHASES_CONC,
                       OUT_DIR / "XRD_精矿_物相标注.png", color=C_CONC)

    print("\n>>> [4/4] 绘制尾矿单样品标注图...")
    plot_single_sample(ang_tail, int_tail, LABEL_TAIL, PHASES_TAIL,
                       OUT_DIR / "XRD_尾矿_物相标注.png", color=C_TAIL)

    print("\n" + "=" * 55)
    print("  全部完成！图片位于:")
    print(f"  {OUT_DIR}")
    print("=" * 55)


if __name__ == "__main__":
    main()
