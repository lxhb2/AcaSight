#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
XRD Plotting Script for Academic Publications
Generates two types of figures:
  1. Stacked XRD pattern (multi-sample vertical offset + bottom PDF reference peaks)
  2. Annotated single-sample XRD (peak numbers + phase list in upper-right)

Dependencies: pip install matplotlib numpy scipy
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import csv
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np
from scipy.signal import find_peaks

# ── 用户参数 ──────────────────────────────────────────────────────────
SAMPLES = {
    'Y-2': {
        'file': r'C:\Users\Administrator\.qclaw\workspace\Y-2_corrected.csv',
        'color': '#1f77b4',
        'offset': 0,
    },
    # 如有更多样品，在此添加，例如:
    # '精矿': {
    #     'file': r'C:\path\to\concentrate.csv',
    #     'color': '#d62728',
    #     'offset': 0,
    # },
}

# ── 物相 PDF 标准峰（2θ °）────────────────────────────
# 用户可自行修改，或运行 auto_annotate=True 让程序自动找峰
PHASE_PEAKS = {
    'Stibnite\n(PDF#42-1423)': [17.72, 20.24, 21.56, 22.86, 24.95,
                                  27.35, 29.93, 32.63, 34.61, 37.98,
                                  40.22, 42.68, 47.07, 48.67, 52.28],
    'Senarmontite\n(PDF#71-0495)': [13.07, 26.17, 30.97, 38.22, 43.57],
}
# 每个物相在堆叠图底部显示的颜色
PHASE_COLORS = ['#e41a1c', '#4daf4a']

# 峰标注（来自自动检测，手动校正版）
# 格式: {样品名: [(2theta, 峰号, 物相名), ...]}
PEAK_ANNOTATIONS = {
    'Y-2': [
        (20.20, '1', 'Stibnite'),
        (21.57, '2', 'Stibnite'),
        (22.83, '3', 'Stibnite'),
        (27.90, '4', 'Stibnite'),
        (29.85, '5', 'Stibnite'),
        (32.50, '6', 'Stibnite'),
        (38.05, '7', 'Stibnite'),
        (52.27, '8', 'Stibnite'),
    ],
}

# 绘图范围
XMIN, XMAX = 10.0, 80.0
DPI = 600
Y_OFFSET_STEP = 50   # 堆叠样品间的Y偏移量

# ─────────────────────────────────────────────────────────────────────

def load_xrd(path):
    angles, intensities = [], []
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            angles.append(float(row[0]))
            intensities.append(float(row[1]))
    return np.array(angles), np.array(intensities)


def detect_peaks(angles, intensities, height_above_bg=5.0, distance=5):
    """自动检测峰位"""
    bg = np.median(intensities)
    peaks, _ = find_peaks(intensities, height=bg + height_above_bg,
                          distance=distance)
    return [(angles[p], intensities[p]) for p in peaks]


def setup_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans'],
        'font.size': 10,
        'axes.linewidth': 1.0,
        'axes.labelsize': 11,
        'axes.titlesize': 10,
        'xtick.direction': 'in',
        'ytick.direction': 'in',
        'xtick.major.size': 4,
        'ytick.major.size': 4,
        'xtick.minor.size': 2,
        'ytick.minor.size': 2,
        'axes.grid': False,
        'figure.dpi': DPI,
        'savefig.dpi': DPI,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
        'font.weight': 'normal',
        'axes.labelweight': 'normal',
    })


def plot_stacked_xrd(SAMPLES, PHASE_PEAKS, PHASE_COLORS,
                      XMIN=10, XMAX=80, out_path='stacked_xrd.png'):
    """多样品堆叠 XRD 图 + 底部 PDF 标准峰竖线"""
    setup_style()

    # 加载数据
    sample_data = {}
    max_intensity = 0
    for name, info in SAMPLES.items():
        ang, inten = load_xrd(info['file'])
        mask = (ang >= XMIN) & (ang <= XMAX)
        ang, inten = ang[mask], inten[mask]
        sample_data[name] = (ang, inten)
        if inten.max() > max_intensity:
            max_intensity = inten.max()

    n_samples = len(SAMPLES)
    fig_h = 2.5 + n_samples * 1.8 + 0.8
    fig, ax = plt.subplots(figsize=(8, fig_h))

    # 分区: 上部=样品, 下部=标准峰
    y_offset = 0
    offsets = {}
    colors = []
    handles = []

    for i, (name, info) in enumerate(SAMPLES.items()):
        ang, inten = sample_data[name]
        offset = y_offset
        offsets[name] = offset
        shifted = inten + offset
        color = info['color']
        ax.plot(ang, shifted, color=color, linewidth=0.8, solid_capstyle='round')
        ax.fill_between(ang, offset, shifted, color=color, alpha=0.15)
        ax.text(XMIN - 0.5, offset + 5, name, va='bottom', ha='right',
                fontsize=9, color=color, fontweight='bold')
        y_offset += max_intensity + Y_OFFSET_STEP
        colors.append(color)
        handles.append(Line2D([0], [0], color=color, linewidth=1.5, label=name))

    # 底部标注区（留白）
    y_offset += 10

    # PDF 标准峰竖线
    legend_patches = []
    for (phase_label, peaks), pc in zip(PHASE_PEAKS.items(), PHASE_COLORS):
        for pk in peaks:
            if XMIN <= pk <= XMAX:
                ax.axvline(pk, color=pc, linewidth=0.7, linestyle='--',
                           alpha=0.7, ymin=0, ymax=0.25)
        # 图例
        legend_patches.append(
            Line2D([0], [0], color=pc, linewidth=1.5, linestyle='--',
                   label=phase_label.replace('\n', ' '))
        )

    # 坐标轴
    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(-5, y_offset)
    ax.set_xlabel(r'2$\theta$ (°)', fontweight='bold')
    ax.set_ylabel('Intensity (cps)', fontweight='bold')

    # Y轴只保留刻度参考
    ax.set_yticks([])
    ax.spines['left'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['bottom'].set_linewidth(1.2)

    # 主刻度 + 次刻度
    ax.set_xticks(np.arange(20, XMAX + 1, 10))
    ax.set_xticks(np.arange(15, XMAX, 5), minor=True)
    ax.tick_params(axis='x', which='major', length=5, width=1.0)
    ax.tick_params(axis='x', which='minor', length=2.5, width=0.8)

    # 图例
    ax.legend(handles=handles + legend_patches,
              loc='upper right', frameon=True, fontsize=8,
              framealpha=0.9, edgecolor='gray')

    plt.tight_layout()
    plt.savefig(out_path, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'[OK] Stacked plot saved: {out_path}')
    return out_path


def plot_annotated_xrd(sample_name, angles, intensities,
                       peaks, out_path='annotated_xrd.png',
                       XMIN=10, XMAX=80):
    """单样品物相标注 XRD 图"""
    setup_style()

    fig, ax = plt.subplots(figsize=(8, 4.5))

    # 谱线
    mask = (angles >= XMIN) & (angles <= XMAX)
    ang = angles[mask]
    inten = intensities[mask]

    ax.plot(ang, inten, color='#1f77b4', linewidth=0.8)
    ax.fill_between(ang, 0, inten, color='#1f77b4', alpha=0.12)

    # 标注每个峰
    for (theta, num, phase) in peaks:
        idx = np.argmin(np.abs(ang - theta))
        peak_y = inten[idx]
        # 标注位置：峰顶上方 10% 或 20 cps
        label_y = peak_y + max(peak_y * 0.08, 15)

        ax.annotate(
            num,
            xy=(theta, peak_y),
            xytext=(theta, label_y),
            fontsize=8, color='black', fontweight='bold',
            ha='center', va='bottom',
            arrowprops=dict(arrowstyle='-', color='gray',
                            linewidth=0.6, shrinkA=0, shrinkB=0),
            bbox=dict(boxstyle='circle,pad=0.2', fc='white',
                      ec='gray', alpha=0.8, lw=0.5)
        )

    # 右上角物相列表
    right_text = '\n'.join(
        f'{n} — {p}' for (_, n, p) in sorted(peaks, key=lambda x: int(x[1]))
    )
    ax.text(0.97, 0.97, right_text,
            transform=ax.transAxes, fontsize=7.5,
            va='top', ha='right',
            bbox=dict(boxstyle='round,pad=0.4', fc='white',
                      ec='lightgray', alpha=0.92),
            family='sans-serif')

    # 坐标轴
    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(0, inten.max() * 1.25)
    ax.set_xlabel(r'2$\theta$ (°)', fontweight='bold')
    ax.set_ylabel('Intensity (cps)', fontweight='bold')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.0)
    ax.spines['bottom'].set_linewidth(1.0)

    ax.set_xticks(np.arange(20, XMAX + 1, 10))
    ax.set_xticks(np.arange(15, XMAX, 5), minor=True)
    ax.tick_params(axis='x', which='major', length=5, width=1.0)
    ax.tick_params(axis='x', which='minor', length=2.5, width=0.8)

    ax.set_title(sample_name, fontsize=11, fontweight='bold', pad=8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f'[OK] Annotated plot saved: {out_path}')
    return out_path


def main():
    print('=' * 60)
    print('XRD Academic Plot Generator')
    print('=' * 60)

    # ── 1. 堆叠对比图 ───────────────────────────────────────────
    print('\n[1] Generating stacked XRD plot ...')
    plot_stacked_xrd(
        SAMPLES, PHASE_PEAKS, PHASE_COLORS,
        XMIN=XMIN, XMAX=XMAX,
        out_path=r'C:\Users\Administrator\.qclaw\workspace\xrd_stacked.png'
    )

    # ── 2. 单样品标注图 ─────────────────────────────────────────
    print('\n[2] Generating annotated XRD plots ...')
    for name, info in SAMPLES.items():
        ang, inten = load_xrd(info['file'])
        peaks = PEAK_ANNOTATIONS.get(name, [])
        if not peaks:
            # 自动检测峰
            detected = detect_peaks(ang, inten)
            peaks = [(t, str(i + 1), 'Unknown') for i, (t, _) in enumerate(detected[:10])]
        out = rf'C:\Users\Administrator\.qclaw\workspace\xrd_{name}_annotated.png'
        plot_annotated_xrd(name, ang, inten, peaks, out_path=out,
                           XMIN=XMIN, XMAX=XMAX)

    print('\n' + '=' * 60)
    print('Done! Output files:')
    print('  1. xrd_stacked.png        -- Stacked comparison')
    for name in SAMPLES:
        print(f'  2. xrd_{name}_annotated.png -- Annotated sample')
    print('=' * 60)


if __name__ == '__main__':
    main()
