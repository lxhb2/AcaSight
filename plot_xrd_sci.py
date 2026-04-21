#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
XRD SCI Figure Plotter
支持: RAS_RAW文本格式数据, PDF卡片自动匹配, 峰位标注
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import json, re, warnings
warnings.filterwarnings('ignore')

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.signal import find_peaks

# ============================================================
# 用户设置
# ============================================================
SAMPLES = {
    '26': {
        'path': r'F:\桌面\26.txt',
        'color': '#2563EB',   # 蓝色
        'label': 'Sample 26',
        'linewidth': 0.9,
    },
    '32': {
        'path': r'F:\桌面\32.txt',
        'color': '#DC2626',   # 红色
        'label': 'Sample 32',
        'linewidth': 0.9,
    },
}

PDF_PATH = r'C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Pro-New\data\pdf_database.json'
PDF4_PATH = r'C:\Users\Administrator\.qclaw\workspace\Sci-XRD-Pro-New\data\pdf4_data.json'

XMIN, XMAX = 5.0, 90.0
XMIN_DISPLAY = 10.0
DPI = 600
PEAK_TOLERANCE = 0.35   # 物相匹配容差 (deg)
MIN_MATCH_PEAKS = 2      # 最少匹配峰数才认定为该物相
MIN_PEAK_HEIGHT = 500    # cps above median for peak detection

# 配色方案
MINERAL_COLORS = [
    '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3',
    '#FF7F00', '#A65628', '#F781BF', '#999999',
]
PDF_COLORS = ['#E41A1C', '#4DAF4A', '#377EB8', '#984EA3']

# ============================================================
# 解析 RAS_RAW 文本格式
# ============================================================
def parse_ras_raw(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    angles, intensities = [], []
    in_data = False
    for line in lines:
        s = line.strip()
        if s.startswith('#Intensity'):
            in_data = True
            continue
        if not in_data:
            continue
        if not s or s.startswith('*') or s.startswith('#'):
            continue
        parts = s.split()
        if len(parts) >= 2:
            try:
                angles.append(float(parts[0]))
                intensities.append(float(parts[1]))
            except ValueError:
                continue

    return np.array(angles), np.array(intensities)


def detect_peaks(angles, intensities, height_above=None, distance=5):
    """检测峰位"""
    median = np.median(intensities)
    if height_above is None:
        std = np.std(intensities)
        threshold = median + MIN_PEAK_HEIGHT
    else:
        threshold = height_above

    mask = (angles >= XMIN_DISPLAY) & (angles <= XMAX)
    ang = angles[mask]
    inten = intensities[mask]

    peaks, props = find_peaks(inten, height=threshold, distance=distance,
                               prominence=100)
    return [(ang[p], inten[p]) for p in peaks]


# ============================================================
# 加载 PDF 数据库
# ============================================================
def load_pdf():
    all_pdf = []
    for p in [PDF_PATH, PDF4_PATH]:
        try:
            with open(p, encoding='utf-8') as f:
                data = json.load(f)
            for item in data:
                if item['pdf_no'] not in {x['pdf_no'] for x in all_pdf}:
                    all_pdf.append(item)
        except Exception:
            pass
    return all_pdf


def match_phases(peaks, pdf_data, tolerance=PEAK_TOLERANCE, min_match=MIN_MATCH_PEAKS):
    """将检测到的峰与PDF卡片匹配"""
    matched = []
    for mineral in pdf_data:
        mineral_2theta = mineral['2theta']
        mineral_intens = mineral['intensities']

        count = 0
        matched_peaks = []
        for p_angle, p_inten in peaks:
            for ref_angle, ref_inten in zip(mineral_2theta, mineral_intens):
                if abs(p_angle - ref_angle) < tolerance:
                    count += 1
                    matched_peaks.append((p_angle, ref_angle, ref_inten, mineral['name'], mineral['pdf_no']))
                    break

        if count >= min_match:
            # 计算匹配度 (归一化)
            matched_peaks.sort(key=lambda x: x[2], reverse=True)
            matched.append({
                'name': mineral['name'],
                'formula': mineral.get('formula', ''),
                'pdf_no': mineral['pdf_no'],
                'matched_count': count,
                'matched_peaks': matched_peaks,
                'total_peaks': len(mineral_2theta),
            })

    matched.sort(key=lambda x: x['matched_count'], reverse=True)
    return matched


# ============================================================
# 绘图函数
# ============================================================
def setup_style():
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'font.size': 10,
        'axes.labelsize': 12,
        'axes.titlesize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'axes.linewidth': 1.0,
        'xtick.direction': 'in', 'ytick.direction': 'in',
        'xtick.major.size': 5, 'xtick.minor.size': 2.5,
        'ytick.major.size': 5, 'ytick.minor.size': 2.5,
        'axes.grid': False,
        'savefig.dpi': DPI,
        'savefig.bbox': 'tight',
        'savefig.pad_inches': 0.05,
    })


def make_legend_handles(pdf_colors):
    """创建图例 handles"""
    handles = []
    for color, name in zip(pdf_colors, phase_names):
        handles.append(
            Line2D([0], [0], color=color, lw=1.5, ls='--',
                   label=name)
        )
    return handles


# ============================================================
# 主程序
# ============================================================
print('=' * 60)
print('XRD SCI Figure Generator')
print('=' * 60)

# 加载所有 PDF 数据
pdf_data = load_pdf()
print(f'Loaded {len(pdf_data)} PDF cards')

# 解析样品数据
sample_data = {}
all_peaks = {}
all_phases = {}

for sid, info in SAMPLES.items():
    ang, inten = parse_ras_raw(info['path'])
    mask = (ang >= XMIN) & (ang <= XMAX)
    ang, inten = ang[mask], inten[mask]
    sample_data[sid] = (ang, inten)

    peaks = detect_peaks(ang, inten)
    peaks.sort(key=lambda x: x[1], reverse=True)
    all_peaks[sid] = peaks
    print(f'\nSample {sid}: {len(ang)} points, range {ang[0]:.2f}-{ang[-1]:.2f} deg')
    print(f'  Max intensity: {inten.max():.0f} cps at {ang[inten.argmax()]:.2f} deg')
    print(f'  Background (median): {np.median(inten):.0f} cps')
    print(f'  Top peaks:')
    for a, i in peaks[:8]:
        print(f'    2theta={a:.2f} deg, I={i:.0f} cps')

    # 物相匹配
    phases = match_phases(peaks, pdf_data)
    all_phases[sid] = phases
    print(f'  Matched phases ({len(phases)}):')
    for ph in phases[:5]:
        print(f'    {ph["name"]} ({ph["formula"]}) [{ph["pdf_no"]}]: {ph["matched_count"]} peaks matched')
        for mp in ph['matched_peaks'][:3]:
            print(f'      Measured {mp[0]:.2f} ~ PDF {mp[1]:.2f} deg (I={mp[2]})')

print()
print('=' * 60)

# ============================================================
# 图 1: 堆叠对比图
# ============================================================
setup_style()

fig, ax = plt.subplots(figsize=(9, 5))

max_intensity = max(np.max(inten) for _, inten in sample_data.values())
y_step = max_intensity * 0.85
y_offsets = {}
legend_handles = []

for i, (sid, info) in enumerate(SAMPLES.items()):
    ang, inten = sample_data[sid]
    offset = i * y_step
    y_offsets[sid] = offset
    shifted = inten + offset
    color = info['color']

    ax.plot(ang, shifted, color=color, lw=info['linewidth'], solid_capstyle='round')
    ax.fill_between(ang, offset, shifted, color=color, alpha=0.10)

    # 样品标签
    ax.text(XMIN_DISPLAY - 0.3, offset + max_intensity * 0.03,
            info['label'], va='bottom', ha='left',
            fontsize=9, color=color, fontweight='bold')

    legend_handles.append(
        Line2D([0], [0], color=color, lw=1.5, label=info['label'])
    )

# PDF 标准峰竖线
phase_names = []
color_idx = 0
for sid, phases in all_phases.items():
    color = SAMPLES[sid]['color']
    for phase in phases[:3]:  # 最多3个物相
        name_str = f'{phase["name"]} [{phase["pdf_no"]}]'
        if name_str in phase_names:
            continue
        phase_names.append(name_str)
        pc = PDF_COLORS[color_idx % len(PDF_COLORS)]
        color_idx += 1

        for mp in phase['matched_peaks']:
            ref_angle = mp[1]
            if XMIN_DISPLAY <= ref_angle <= XMAX:
                ax.axvline(ref_angle, color=pc, lw=0.8, ls='--',
                           alpha=0.75, ymin=0, ymax=0.22)

# Y轴只留刻度参考
ax.set_yticks([])
for sp in ['left', 'right']:
    ax.spines[sp].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_linewidth(1.2)

# X轴
ax.set_xlim(XMIN_DISPLAY, XMAX)
ax.set_xlabel(r'2$\theta$ (°)', fontweight='bold', fontsize=12)
ax.set_ylabel('Intensity (cps)', fontweight='bold', fontsize=12)

ax.set_xticks(np.arange(20, XMAX + 1, 10))
ax.set_xticks(np.arange(15, XMAX, 5), minor=True)
ax.tick_params(axis='x', which='major', length=5, width=1.0)
ax.tick_params(axis='x', which='minor', length=2.5, width=0.8)

# 右上角物相图例
all_phase_str = '\n'.join(phase_names[:8])
if all_phase_str:
    ax.text(0.99, 0.99, all_phase_str,
            transform=ax.transAxes, fontsize=7,
            va='top', ha='right',
            bbox=dict(boxstyle='round,pad=0.3', fc='white',
                      ec='lightgray', alpha=0.90),
            family='monospace')

plt.tight_layout()
out1 = r'C:\Users\Administrator\.qclaw\workspace\xrd_stacked.png'
plt.savefig(out1, dpi=DPI, bbox_inches='tight', facecolor='white')
plt.close()
print(f'[OK] Stacked plot saved: {out1}')

# ============================================================
# 图 2-3: 单样品标注图
# ============================================================
phase_colors_map = {}  # phase_name -> color

for i, (sid, info) in enumerate(SAMPLES.items()):
    setup_style()
    fig, ax = plt.subplots(figsize=(9, 4.5))

    ang, inten = sample_data[sid]
    phases = all_phases[sid]

    # 谱线
    ax.plot(ang, inten, color=info['color'], lw=0.9)
    ax.fill_between(ang, 0, inten, color=info['color'], alpha=0.10)

    max_inten = inten.max()
    bg = np.median(inten)

    # 建立物相颜色映射
    used_colors = []
    for ph in phases:
        name_str = f'{ph["name"]} [{ph["pdf_no"]}]'
        if name_str not in phase_colors_map:
            for c in MINERAL_COLORS:
                if c not in used_colors:
                    phase_colors_map[name_str] = c
                    used_colors.append(c)
                    break

    # 标注已匹配峰
    peak_num = 0
    annotated_angles = {}

    for ph in phases:
        name_str = f'{ph["name"]} [{ph["pdf_no"]}]'
        pc = phase_colors_map.get(name_str, '#666666')

        for meas_angle, ref_angle, ref_inten, name, pdf_no in ph['matched_peaks']:
            # 找最近测量角度的索引
            idx = np.argmin(np.abs(ang - meas_angle))
            peak_y = inten[idx]

            # 避免重叠
            for prev_a in annotated_angles:
                if abs(meas_angle - prev_a) < 0.5:
                    break
            else:
                peak_num += 1
                annotated_angles[meas_angle] = peak_num

                label_y = peak_y + max(peak_y * 0.06, 40)

                ax.annotate(
                    str(peak_num),
                    xy=(meas_angle, peak_y),
                    xytext=(meas_angle, label_y),
                    fontsize=8, color='black', fontweight='bold',
                    ha='center', va='bottom',
                    arrowprops=dict(arrowstyle='-', color='gray',
                                   lw=0.6, shrinkA=0, shrinkB=0),
                    bbox=dict(boxstyle='circle,pad=0.2', fc='white',
                              ec='gray', alpha=0.85, lw=0.5)
                )

                # 在峰上画一条短线指示
                ax.plot([meas_angle, meas_angle], [peak_y, label_y - 8],
                        color=pc, lw=0.6, ls=':', alpha=0.8)

    # 右上角物相列表
    phase_text_parts = []
    peak_counter = 0
    for ph in phases:
        name_str = f'{ph["name"]} [{ph["pdf_no"]}]'
        phase_text_parts.append(f'  {name_str}')

    if phase_text_parts:
        phase_text = 'Matched Phases:\n' + '\n'.join(phase_text_parts[:6])
        ax.text(0.99, 0.99, phase_text,
                transform=ax.transAxes, fontsize=7.5,
                va='top', ha='right',
                bbox=dict(boxstyle='round,pad=0.4', fc='white',
                          ec='lightgray', alpha=0.92))

    # 坐标轴
    ax.set_xlim(XMIN_DISPLAY, XMAX)
    ax.set_ylim(0, max_inten * 1.28)
    ax.set_xlabel(r'2$\theta$ (°)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Intensity (cps)', fontweight='bold', fontsize=12)
    ax.set_title(f'XRD Pattern — {info["label"]}', fontsize=12, fontweight='bold', pad=8)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.0)
    ax.spines['bottom'].set_linewidth(1.0)

    ax.set_xticks(np.arange(20, XMAX + 1, 10))
    ax.set_xticks(np.arange(15, XMAX, 5), minor=True)
    ax.tick_params(axis='x', which='major', length=5, width=1.0)
    ax.tick_params(axis='x', which='minor', length=2.5, width=0.8)

    plt.tight_layout()
    out2 = rf'C:\Users\Administrator\.qclaw\workspace\xrd_{sid}_annotated.png'
    plt.savefig(out2, dpi=DPI, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'[OK] Annotated plot saved: {out2}')

print()
print('=' * 60)
print('Done! All figures generated.')
print('Files:')
print('  1. xrd_stacked.png        -- Stacked comparison plot')
print('  2. xrd_26_annotated.png  -- Sample 26 annotated')
print('  3. xrd_32_annotated.png  -- Sample 32 annotated')
print('=' * 60)
