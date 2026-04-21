#!/usr/bin/env python3
"""
铜硫矿 XRD 数据分析
分析原矿、精矿、尾矿的 XRD 数据，生成对比图
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from scipy.ndimage import gaussian_filter1d
import re
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
plt.rcParams['axes.unicode_minus'] = False

def parse_bruker_raw(filepath):
    """解析 Bruker RAW 格式文件"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 查找数据部分
    data_section = content.split('[Data]')[-1]
    
    angles = []
    intensities = []
    
    for line in data_section.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('Angle'):
            continue
        
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                angle = float(parts[0].strip())
                intensity = float(parts[1].strip())
                angles.append(angle)
                intensities.append(intensity)
            except ValueError:
                continue
    
    return np.array(angles), np.array(intensities)

def remove_background(intensity, lam=1e6, p=0.01, n_iter=10):
    """ALS 背景扣除"""
    L = len(intensity)
    D = np.diff(np.eye(L), n=2)
    D = lam * D.T @ D
    w = np.ones(L)
    
    for _ in range(n_iter):
        W = np.diag(w)
        try:
            C = np.linalg.cholesky(W + D)
            z = np.linalg.solve(C, np.linalg.solve(C.T, w * intensity))
        except:
            z = intensity.copy()
            break
        w = p * (intensity > z) + (1 - p) * (intensity < z)
    
    background = z
    bg_removed = intensity - background
    bg_removed[bg_removed < 0] = 0
    return bg_removed, background

# 矿物标准峰位数据库 (Cu Kα)
MINERAL_DATABASE = {
    "黄铜矿": {
        "formula": "CuFeS₂",
        "peaks": [29.42, 34.84, 36.63, 39.87, 47.43, 49.25, 56.98, 58.65],
        "color": "#E74C3C"
    },
    "黄铁矿": {
        "formula": "FeS₂",
        "peaks": [28.51, 33.08, 37.09, 40.84, 47.44, 56.28, 59.02, 61.70],
        "color": "#F39C12"
    },
    "辉铜矿": {
        "formula": "Cu₂S",
        "peaks": [26.55, 30.08, 37.95, 43.92, 47.87, 53.25, 57.45],
        "color": "#3498DB"
    },
    "铜蓝": {
        "formula": "CuS",
        "peaks": [27.68, 29.58, 31.78, 33.15, 47.87, 52.42, 56.54],
        "color": "#9B59B6"
    },
    "斑铜矿": {
        "formula": "Cu₅FeS₄",
        "peaks": [28.96, 31.26, 37.74, 46.14, 53.87, 55.45],
        "color": "#1ABC9C"
    },
    "石英": {
        "formula": "SiO₂",
        "peaks": [20.85, 26.65, 36.54, 39.46, 42.45, 50.14, 54.88, 60.02],
        "color": "#95A5A6"
    }
}

# 文件路径
data_dir = Path(r"F:\桌面\王铨毕业论文\xrd数据")
files = {
    '原矿': data_dir / "tongliukuang yuankuang.txt",
    '精矿': data_dir / "2cu2jing jingkuang tongliukuang.txt",
    '尾矿': data_dir / "2cu2jing weikuang tongliukuang.txt"
}

# 解析数据
print("解析 XRD 数据...")
datasets = {}
for name, filepath in files.items():
    if filepath.exists():
        angle, intensity = parse_bruker_raw(filepath)
        datasets[name] = (angle, intensity)
        print(f"  {name}: {len(angle)} 数据点, 范围 {angle.min():.1f}° - {angle.max():.1f}°")

# 创建论文级对比图
fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
fig.suptitle('铜硫矿 XRD 图谱对比分析', fontsize=16, fontweight='bold', y=0.98)

colors = {'原矿': '#2C3E50', '精矿': '#E74C3C', '尾矿': '#27AE60'}
offset = 0

for idx, (name, (angle, intensity)) in enumerate(datasets.items()):
    ax = axes[idx]
    
    # 平滑处理
    smoothed = savgol_filter(intensity, window_length=15, polyorder=3)
    
    # 背景扣除
    bg_removed, bg = remove_background(smoothed)
    
    # 寻峰
    peaks, props = find_peaks(
        bg_removed,
        height=0.03 * np.max(bg_removed),
        prominence=0.02 * np.max(bg_removed),
        distance=30
    )
    
    # 绘制图谱
    ax.fill_between(angle, 0, bg_removed, alpha=0.3, color=colors[name])
    ax.plot(angle, bg_removed, color=colors[name], linewidth=0.8, label=name)
    ax.plot(angle, bg, '--', color='gray', linewidth=0.5, alpha=0.5, label='背景')
    
    # 标注峰位
    peak_angles = angle[peaks]
    peak_intensities = bg_removed[peaks]
    
    for i, (pa, pi) in enumerate(zip(peak_angles[:15], peak_intensities[:15])):
        # 检查是否匹配已知矿物峰位
        matched_mineral = None
        for mineral, info in MINERAL_DATABASE.items():
            for std_peak in info['peaks']:
                if abs(pa - std_peak) < 0.5:
                    matched_mineral = mineral
                    break
            if matched_mineral:
                break
        
        # 标注峰位
        ax.annotate(f'{pa:.1f}°', 
                   xy=(pa, pi), 
                   xytext=(pa, pi + 30),
                   fontsize=7, 
                   ha='center',
                   color='red' if matched_mineral else 'black',
                   alpha=0.8)
    
    ax.set_ylabel('强度 (a.u.)', fontsize=11)
    ax.set_title(f'{name} - 检测到 {len(peaks)} 个衍射峰', fontsize=12, loc='left')
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(5, 80)

axes[-1].set_xlabel('2θ (°)', fontsize=12)
plt.tight_layout()

# 保存图片
output_path = Path(r"F:\桌面\王铨毕业论文\xrd数据\XRD对比图_铜硫矿.png")
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"\n[OK] 图谱已保存: {output_path}")

# 创建三合一对比图（论文级）
fig2, ax2 = plt.subplots(figsize=(14, 8))

# 偏移量设置
offsets = {'原矿': 0, '精矿': 500, '尾矿': 1000}

for name, (angle, intensity) in datasets.items():
    smoothed = savgol_filter(intensity, window_length=15, polyorder=3)
    bg_removed, _ = remove_background(smoothed)
    
    ax2.plot(angle, bg_removed + offsets[name], 
            color=colors[name], linewidth=0.8, label=name)

# 标注主要矿物峰位
for mineral, info in MINERAL_DATABASE.items():
    for peak in info['peaks'][:3]:  # 只标注前3个主要峰
        ax2.axvline(x=peak, color=info['color'], linestyle='--', alpha=0.4, linewidth=0.8)
        ax2.text(peak, max(offsets.values()) + 100, mineral, 
                rotation=90, fontsize=8, ha='center', va='bottom',
                color=info['color'], alpha=0.7)

ax2.set_xlabel('2θ (°)', fontsize=12)
ax2.set_ylabel('强度 (a.u., 偏移显示)', fontsize=12)
ax2.set_title('铜硫矿浮选前后 XRD 图谱对比\n(Cu Kα, λ=1.5406 Å)', fontsize=14, fontweight='bold')
ax2.legend(loc='upper right', fontsize=10)
ax2.grid(True, alpha=0.3, linestyle='--')
ax2.set_xlim(5, 80)

output_path2 = Path(r"F:\桌面\王铨毕业论文\xrd数据\XRD三合一对比图_论文级.png")
plt.savefig(output_path2, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[OK] 论文级对比图已保存: {output_path2}")

# 分析结果
print("\n" + "="*60)
print("XRD 分析结果")
print("="*60)

for name, (angle, intensity) in datasets.items():
    smoothed = savgol_filter(intensity, window_length=15, polyorder=3)
    bg_removed, _ = remove_background(smoothed)
    
    peaks, _ = find_peaks(bg_removed, height=0.05*np.max(bg_removed), prominence=0.03*np.max(bg_removed))
    peak_angles = angle[peaks]
    
    print(f"\n【{name}】")
    print(f"  主要衍射峰: {len(peaks)} 个")
    
    # 匹配矿物
    matched_minerals = {}
    for pa in peak_angles:
        for mineral, info in MINERAL_DATABASE.items():
            for std_peak in info['peaks']:
                if abs(pa - std_peak) < 0.8:
                    if mineral not in matched_minerals:
                        matched_minerals[mineral] = []
                    matched_minerals[mineral].append(pa)
    
    if matched_minerals:
        print("  识别矿物相:")
        for mineral, peaks in sorted(matched_minerals.items(), key=lambda x: -len(x[1])):
            print(f"    - {mineral} ({MINERAL_DATABASE[mineral]['formula']}): {len(peaks)} 个匹配峰")

plt.show()
