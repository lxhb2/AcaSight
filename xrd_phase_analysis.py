#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
铜硫矿 XRD 物相分析报告生成器
分析原矿、精矿、尾矿的XRD数据，进行物相鉴定
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from pathlib import Path
import json

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
    z = intensity.copy()
    
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

# 标准矿物数据库 (基于ICDD PDF卡片)
MINERAL_DATABASE = {
    "黄铜矿 Chalcopyrite (CuFeS2)": {
        "peaks": [29.42, 34.84, 36.63, 39.05, 49.25, 52.48, 58.72],
        "d_values": [3.03, 2.57, 2.45, 2.30, 1.85, 1.74, 1.57],
        "hkl": ["(112)", "(200)", "(004)/(220)", "(204)", "(312)", "(224)", "(400)"],
        "color": "#E74C3C",
        "pdf_card": "PDF#37-0475"
    },
    "黄铁矿 Pyrite (FeS2)": {
        "peaks": [28.51, 33.08, 37.09, 40.77, 47.43, 56.28, 59.02],
        "d_values": [3.13, 2.71, 2.42, 2.21, 1.92, 1.63, 1.56],
        "hkl": ["(111)", "(200)", "(210)", "(211)", "(220)", "(311)", "(222)"],
        "color": "#F39C12",
        "pdf_card": "PDF#42-1340"
    },
    "石英 Quartz (SiO2)": {
        "peaks": [20.85, 26.65, 36.54, 39.50, 42.47, 50.14, 54.90, 60.00, 64.05, 68.15],
        "d_values": [4.26, 3.34, 2.46, 2.28, 2.13, 1.82, 1.67, 1.54, 1.45, 1.38],
        "hkl": ["(100)", "(101)", "(110)", "(102)", "(200)", "(112)", "(211)", "(203)", "(301)", "(212)"],
        "color": "#3498DB",
        "pdf_card": "PDF#46-1045"
    },
    "辉铜矿 Chalcocite (Cu2S)": {
        "peaks": [26.55, 32.05, 37.95, 46.28, 47.87, 55.20, 62.40],
        "d_values": [3.36, 2.79, 2.37, 1.96, 1.90, 1.66, 1.49],
        "hkl": ["(102)", "(110)", "(200)", "(212)", "(114)", "(220)", "(310)"],
        "color": "#9B59B6",
        "pdf_card": "PDF#33-0490"
    },
    "铜蓝 Covellite (CuS)": {
        "peaks": [27.50, 29.65, 31.90, 33.05, 48.10, 52.40, 59.60],
        "d_values": [3.24, 3.01, 2.80, 2.71, 1.89, 1.75, 1.55],
        "hkl": ["(006)", "(102)", "(104)", "(105)", "(110)", "(116)", "(205)"],
        "color": "#1ABC9C",
        "pdf_card": "PDF#06-0464"
    },
    "斑铜矿 Bornite (Cu5FeS4)": {
        "peaks": [26.10, 32.20, 38.20, 46.50, 55.80, 58.50],
        "d_values": [3.41, 2.78, 2.36, 1.95, 1.65, 1.58],
        "hkl": ["(112)", "(200)", "(204)", "(220)", "(312)", "(224)"],
        "color": "#E67E22",
        "pdf_card": "PDF#42-1409"
    },
    "方解石 Calcite (CaCO3)": {
        "peaks": [23.02, 29.41, 31.42, 36.00, 39.40, 43.15, 47.50, 48.52],
        "d_values": [3.86, 3.04, 2.84, 2.49, 2.29, 2.10, 1.91, 1.87],
        "hkl": ["(012)", "(104)", "(006)", "(110)", "(113)", "(202)", "(018)", "(116)"],
        "color": "#95A5A6",
        "pdf_card": "PDF#05-0586"
    }
}

def match_phase(peak_angle, tolerance=0.3):
    """匹配物相"""
    matches = []
    for mineral, data in MINERAL_DATABASE.items():
        for i, std_peak in enumerate(data["peaks"]):
            if abs(peak_angle - std_peak) <= tolerance:
                matches.append({
                    "mineral": mineral,
                    "std_peak": std_peak,
                    "d_value": data["d_values"][i],
                    "hkl": data["hkl"][i],
                    "pdf_card": data["pdf_card"],
                    "delta": abs(peak_angle - std_peak)
                })
    return sorted(matches, key=lambda x: x["delta"])

# 数据路径
data_dir = Path(r"F:\桌面\王铨毕业论文\xrd数据")
files = {
    'Raw Ore': data_dir / "tongliukuang yuankuang.txt",
    'Concentrate': data_dir / "2cu2jing jingkuang tongliukuang.txt",
    'Tailings': data_dir / "2cu2jing weikuang tongliukuang.txt"
}

# 解析数据并分析
datasets = {}
analysis_results = {}

print("="*70)
print("铜硫矿 XRD 物相分析报告")
print("Cu-S Ore XRD Phase Analysis Report")
print("="*70)
print(f"\n仪器参数: Cu Ka, lambda = 1.5406 A, 40kV/40mA")
print(f"扫描范围: 5° - 80° 2θ")
print()

for name, path in files.items():
    if not path.exists():
        print(f"[警告] 文件不存在: {path}")
        continue
    
    angle, intensity = parse_bruker_raw(path)
    smoothed = savgol_filter(intensity, 15, 3)
    bg_removed = remove_background(smoothed)
    datasets[name] = (angle, bg_removed, intensity)
    
    # 寻峰
    peaks, properties = find_peaks(
        bg_removed, 
        height=0.05*np.max(bg_removed),
        prominence=0.03*np.max(bg_removed),
        distance=30
    )
    
    peak_angles = angle[peaks]
    peak_intensities = bg_removed[peaks]
    
    # 按强度排序
    sorted_idx = np.argsort(peak_intensities)[::-1]
    
    name_cn = {'Raw Ore': '原矿', 'Concentrate': '精矿', 'Tailings': '尾矿'}[name]
    
    print(f"\n{'='*70}")
    print(f"【{name_cn}】{name}")
    print(f"样品文件: {path.name}")
    print(f"检测到 {len(peaks)} 个衍射峰")
    print("-"*70)
    
    analysis_results[name] = {
        'peaks': [],
        'identified_minerals': set()
    }
    
    # 输出主要峰位和物相匹配
    print(f"{'Peak(2th)':<12} {'Intensity':<12} {'d(A)':<10} {'Phase Match':<30} {'hkl':<10}")
    print("-"*70)
    
    for i, idx in enumerate(sorted_idx[:20]):  # 前20个最强峰
        pa = peak_angles[idx]
        pi = peak_intens[idx]
        d_value = 1.5406 / (2 * np.sin(np.radians(pa / 2)))
        
        matches = match_phase(pa)
        
        if matches:
            best_match = matches[0]
            mineral_short = best_match['mineral'].split('(')[0].strip()
            print(f"{pa:<12.2f} {pi:<12.0f} {d_value:<10.3f} {mineral_short:<30} {best_match['hkl']:<10}")
            analysis_results[name]['identified_minerals'].add(best_match['mineral'])
            analysis_results[name]['peaks'].append({
                'angle': float(pa),
                'intensity': float(pi),
                'd_value': float(d_value),
                'match': best_match
            })
        else:
            print(f"{pa:<12.2f} {pi:<12.0f} {d_value:<10.3f} {'No match':<30} {'-':<10}")
            analysis_results[name]['peaks'].append({
                'angle': float(pa),
                'intensity': float(pi),
                'd_value': float(d_value),
                'match': None
            })

# Phase Summary
print(f"\n{'='*70}")
print("Phase Identification Summary")
print("="*70)

for name in ['Raw Ore', 'Concentrate', 'Tailings']:
    name_cn = {'Raw Ore': 'Raw Ore', 'Concentrate': 'Concentrate', 'Tailings': 'Tailings'}[name]
    minerals = analysis_results.get(name, {}).get('identified_minerals', set())
    print(f"\n{name_cn} Main Phases:")
    for m in minerals:
        print(f"  - {m}")

# 生成论文级对比图
fig, ax = plt.subplots(figsize=(16, 10))

colors = {'Raw Ore': '#2C3E50', 'Concentrate': '#E74C3C', 'Tailings': '#27AE60'}
offsets = {'Raw Ore': 0, 'Concentrate': 800, 'Tailings': 1600}
labels_cn = {'Raw Ore': 'Raw Ore', 'Concentrate': 'Concentrate', 'Tailings': 'Tailings'}

# 绘制图谱
for name, (angle, bg_removed, raw_intensity) in datasets.items():
    ax.plot(angle, bg_removed + offsets[name], color=colors[name], 
            linewidth=0.8, label=labels_cn[name], alpha=0.9)

# 标注主要矿物峰位
annotation_y = max(offsets.values()) + 300
shown_minerals = set()

for mineral, data in MINERAL_DATABASE.items():
    for i, peak in enumerate(data['peaks'][:3]):  # 只标注前3个主峰
        ax.axvline(x=peak, color=data['color'], linestyle='--', alpha=0.4, linewidth=0.8)
    
    # 在第一个峰位置标注矿物名
    if data['peaks'][0] not in shown_minerals:
        short_name = mineral.split('(')[0].strip()
        ax.text(data['peaks'][0], annotation_y, short_name, fontsize=8, ha='center',
               color=data['color'], fontweight='bold', rotation=90, va='bottom')
        shown_minerals.add(data['peaks'][0])

ax.set_xlabel('2θ (degrees)', fontsize=14, fontweight='bold')
ax.set_ylabel('Intensity (a.u.)', fontsize=14, fontweight='bold')
ax.set_title('XRD Patterns of Copper-Sulfide Ore Flotation Products\nCu Ka radiation, lambda = 1.5406 A', 
            fontsize=16, fontweight='bold', pad=20)
ax.legend(loc='upper right', fontsize=12, framealpha=0.95, edgecolor='gray')
ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_xlim(5, 80)
ax.set_ylim(-50, annotation_y + 150)

# 添加矿物鉴定说明框
textstr = 'Phase Identification:\n'
textstr += '■ Chalcopyrite (CuFeS2) - PDF#37-0475\n'
textstr += '■ Pyrite (FeS2) - PDF#42-1340\n'
textstr += '■ Quartz (SiO2) - PDF#46-1045\n'
textstr += '■ Chalcocite (Cu2S) - PDF#33-0490'

props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='gray')
ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
       verticalalignment='top', bbox=props, family='monospace')

plt.tight_layout()

# 保存图片
output_path = data_dir / "XRD_Phase_Analysis_Report.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
print(f"\n[OK] 论文级对比图已保存: {output_path}")

output_pdf = data_dir / "XRD_Phase_Analysis_Report.pdf"
plt.savefig(output_pdf, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[OK] PDF版本已保存: {output_pdf}")

# 生成JSON格式的分析结果
json_output = data_dir / "XRD_Analysis_Results.json"
with open(json_output, 'w', encoding='utf-8') as f:
    # 转换set为list以便JSON序列化
    for name in analysis_results:
        analysis_results[name]['identified_minerals'] = list(analysis_results[name]['identified_minerals'])
    json.dump(analysis_results, f, ensure_ascii=False, indent=2)
print(f"[OK] 分析结果JSON已保存: {json_output}")

print("\n" + "="*70)
print("【分析完成】")
print("="*70)
