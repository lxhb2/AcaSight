#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
铜硫矿 XRD 对比分析 - 论文级图表
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# 设置字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11

def parse_bruker_raw(filepath):
    """解析 Bruker RAW 格式"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    data_section = content.split('[Data]')[-1]
    angles, intensities = [], []
    
    for line in data_section.strip().split('\n'):
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                angles.append(float(parts[0].strip()))
                intensities.append(float(parts[1].strip()))
            except:
                continue
    
    return np.array(angles), np.array(intensities)

def remove_background(intensity, lam=1e6, p=0.01):
    """ALS 背景扣除"""
    L = len(intensity)
    D = np.diff(np.eye(L), n=2)
    D = lam * D.T @ D
    w = np.ones(L)
    z = intensity.copy()  # 初始化 z
    
    for _ in range(10):
        W = np.diag(w)
        try:
            C = np.linalg.cholesky(W + D)
            z = np.linalg.solve(C, np.linalg.solve(C.T, w * intensity))
        except:
            break
        w = p * (intensity > z) + (1 - p) * (intensity < z)
    
    result = intensity - z
    result[result < 0] = 0
    return result

# 矿物峰位数据库
MINERALS = {
    "Chalcopyrite\nCuFeS2": {"peaks": [29.42, 34.84, 36.63, 49.25], "color": "#E74C3C"},
    "Pyrite\nFeS2": {"peaks": [28.51, 33.08, 37.09, 56.28], "color": "#F39C12"},
    "Quartz\nSiO2": {"peaks": [20.85, 26.65, 36.54, 50.14], "color": "#3498DB"},
    "Chalcocite\nCu2S": {"peaks": [26.55, 37.95, 47.87], "color": "#9B59B6"},
}

# 数据路径
data_dir = Path(r"F:\桌面\王铨毕业论文\xrd数据")
files = {
    'Raw Ore': data_dir / "tongliukuang yuankuang.txt",
    'Concentrate': data_dir / "2cu2jing jingkuang tongliukuang.txt",
    'Tailings': data_dir / "2cu2jing weikuang tongliukuang.txt"
}

# 解析数据
datasets = {}
for name, path in files.items():
    if path.exists():
        angle, intensity = parse_bruker_raw(path)
        smoothed = savgol_filter(intensity, 15, 3)
        bg_removed = remove_background(smoothed)
        datasets[name] = (angle, bg_removed)

# 创建论文级对比图
fig, ax = plt.subplots(figsize=(14, 10))

colors = {'Raw Ore': '#2C3E50', 'Concentrate': '#E74C3C', 'Tailings': '#27AE60'}
offsets = {'Raw Ore': 0, 'Concentrate': 600, 'Tailings': 1200}
labels_cn = {'Raw Ore': '原矿', 'Concentrate': '精矿', 'Tailings': '尾矿'}

# 绘制图谱
for name, (angle, intensity) in datasets.items():
    ax.plot(angle, intensity + offsets[name], color=colors[name], 
            linewidth=0.8, label=f'{labels_cn[name]} ({name})')

# 标注矿物峰位
y_pos = max(offsets.values()) + 150
for mineral, info in MINERALS.items():
    for peak in info['peaks']:
        ax.axvline(x=peak, color=info['color'], linestyle='--', alpha=0.5, linewidth=1)
    # 在第一个峰位置标注矿物名
    ax.text(info['peaks'][0], y_pos, mineral, fontsize=9, ha='center', 
            color=info['color'], fontweight='bold', rotation=90, va='bottom')

ax.set_xlabel('2Theta (degree)', fontsize=14)
ax.set_ylabel('Intensity (a.u.)', fontsize=14)
ax.set_title('XRD Patterns of Copper Sulfide Ore Flotation Products\n(Cu Ka, lambda=1.5406 A)', 
             fontsize=16, fontweight='bold')
ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(5, 80)
ax.set_ylim(-50, y_pos + 200)

# 添加标注
ax.annotate('', xy=(20, 300), xytext=(20, 500),
            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
ax.text(21, 400, 'Quartz peak\nenriched', fontsize=9, color='#3498DB')

ax.annotate('', xy=(29.4, 700), xytext=(29.4, 900),
            arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
ax.text(30.5, 800, 'Chalcopyrite\nmain peak', fontsize=9, color='#E74C3C')

plt.tight_layout()

# 保存
output = data_dir / "XRD_Flotation_Comparison_Thesis.png"
plt.savefig(output, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[OK] Saved: {output}")

# 同时保存到工作区
output2 = Path(r"C:\Users\Administrator\.qclaw\workspace\XRD_Flotation_Comparison.png")
plt.savefig(output2, dpi=200, bbox_inches='tight', facecolor='white')
print(f"[OK] Saved: {output2}")

# 创建单独的分图
fig2, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
fig2.suptitle('XRD Analysis of Copper Sulfide Ore', fontsize=16, fontweight='bold')

for idx, (name, (angle, intensity)) in enumerate(datasets.items()):
    ax = axes[idx]
    ax.fill_between(angle, 0, intensity, alpha=0.4, color=colors[name])
    ax.plot(angle, intensity, color=colors[name], linewidth=0.7)
    
    # 寻峰并标注
    peaks, _ = find_peaks(intensity, height=0.05*np.max(intensity), 
                         prominence=0.03*np.max(intensity), distance=50)
    
    for p in peaks[:12]:
        pa = angle[p]
        pi = intensity[p]
        ax.annotate(f'{pa:.1f}', xy=(pa, pi), xytext=(pa, pi+20),
                   fontsize=7, ha='center', color='darkred', alpha=0.8)
    
    ax.set_ylabel('Intensity (a.u.)', fontsize=11)
    ax.set_title(f'{labels_cn[name]} ({name}) - {len(peaks)} peaks detected', fontsize=12, loc='left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(5, 80)

axes[-1].set_xlabel('2Theta (degree)', fontsize=12)
plt.tight_layout()

output3 = data_dir / "XRD_Individual_Patterns.png"
plt.savefig(output3, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[OK] Saved: {output3}")

# 输出分析结果
print("\n" + "="*60)
print("XRD Analysis Results")
print("="*60)

for name, (angle, intensity) in datasets.items():
    peaks, _ = find_peaks(intensity, height=0.05*np.max(intensity), prominence=0.03*np.max(intensity))
    peak_angles = angle[peaks]
    
    print(f"\n[{labels_cn[name]}] Main peaks:")
    for pa in sorted(peak_angles)[:10]:
        match = ""
        for mineral, info in MINERALS.items():
            for sp in info['peaks']:
                if abs(pa - sp) < 0.8:
                    match = f" <-- {mineral.split(chr(10))[0]}"
                    break
        print(f"  2Theta = {pa:.2f} deg{match}")

print("\n[Done] Analysis complete!")
