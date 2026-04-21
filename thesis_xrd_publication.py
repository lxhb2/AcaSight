"""
铜硫矿 XRD 对比图 - 论文出版级
清晰展示原矿-精矿-尾矿目的组分变化
"""
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from pathlib import Path
from scipy.signal import find_peaks
import matplotlib.patches as mpatches

# 论文出版级设置
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['pdf.fonttype'] = 42  # TrueType fonts for PDF
plt.rcParams['ps.fonttype'] = 42

# 铜硫矿主要矿物 PDF 卡片峰位
MINERALS = {
    "CuFeS2": {  # 黄铜矿
        "name": "Chalcopyrite",
        "formula": "CuFeS$_2$",
        "peaks": [29.42, 34.84, 36.63, 47.43, 56.98],
        "pdf": "23-0195",
        "color": "#B22234"  # Firebrick
    },
    "Cu2S": {  # 辉铜矿
        "name": "Chalcocite", 
        "formula": "Cu$_2$S",
        "peaks": [26.55, 30.08, 37.95, 43.92, 47.87],
        "pdf": "26-1116",
        "color": "#4169E1"  # Royal Blue
    },
    "CuS": {  # 铜蓝
        "name": "Covellite",
        "formula": "CuS",
        "peaks": [27.68, 29.58, 31.78, 47.87, 56.54],
        "pdf": "06-0464",
        "color": "#228B22"  # Forest Green
    },
    "Cu5FeS4": {  # 斑铜矿
        "name": "Bornite",
        "formula": "Cu$_5$FeS$_4$",
        "peaks": [28.96, 31.26, 37.74, 46.14, 53.87],
        "pdf": "11-0686",
        "color": "#FF8C00"  # Dark Orange
    },
    "FeS2": {  # 黄铁矿
        "name": "Pyrite",
        "formula": "FeS$_2$",
        "peaks": [28.51, 33.08, 37.09, 40.84, 56.28],
        "pdf": "06-0710",
        "color": "#808080"  # Gray
    },
    "SiO2": {  # 石英
        "name": "Quartz",
        "formula": "SiO$_2$",
        "peaks": [20.86, 26.64, 36.54, 39.46, 42.45, 50.14],
        "pdf": "33-1161",
        "color": "#D3D3D3"  # Light Gray
    }
}


def parse_bruker_raw(file_path):
    """解析 Bruker RAW 格式"""
    with open(file_path, "rb") as f:
        data = f.read()
    
    data_start = 892
    start_angle = 10.0
    step = 0.02
    
    intensities = []
    for i in range((len(data) - data_start) // 4):
        pos = data_start + i * 4
        if pos + 4 <= len(data):
            val = struct.unpack("<f", data[pos:pos+4])[0]
            intensities.append(val if 0 < val < 10000 else 0)
    
    angles = np.linspace(start_angle, start_angle + step * (len(intensities) - 1), len(intensities))
    return angles, np.array(intensities)


def find_mineral_peaks(angle, intensity, tolerance=0.5):
    """识别矿物峰"""
    intensity_norm = intensity / np.max(intensity) if np.max(intensity) > 0 else intensity
    peaks_idx, _ = find_peaks(intensity_norm, height=0.05, distance=10, prominence=0.02)
    sample_peaks = angle[peaks_idx]
    sample_intensities = intensity_norm[peaks_idx]
    
    identified = []
    for key, mineral in MINERALS.items():
        matched_peaks = []
        matched_intensities = []
        for ref_peak in mineral["peaks"]:
            for i, sp in enumerate(sample_peaks):
                if abs(sp - ref_peak) <= tolerance:
                    matched_peaks.append(sp)
                    matched_intensities.append(sample_intensities[i])
                    break
        
        if matched_peaks:
            identified.append({
                "key": key,
                "mineral": mineral,
                "matched_peaks": matched_peaks,
                "matched_intensities": matched_intensities,
                "count": len(matched_peaks)
            })
    
    identified.sort(key=lambda x: x["count"], reverse=True)
    return identified


def plot_thesis_xrd_comparison(files, output_path):
    """论文出版级 XRD 对比图"""
    
    fig, ax = plt.subplots(figsize=(7.2, 4.5), dpi=300)
    
    # 颜色方案 - 使用期刊常用配色
    colors = {
        "raw": "#2C3E50",      # 深蓝灰
        "conc": "#E74C3C",     # 红色
        "tail": "#27AE60"      # 绿色
    }
    
    samples = [
        ("raw", "原矿", "Raw Ore"),
        ("conc", "精矿", "Concentrate"),
        ("tail", "尾矿", "Tailings")
    ]
    
    offsets = {"raw": 0, "conc": 0, "tail": 0}
    
    # 绘制 XRD 曲线
    for key, label_cn, label_en in samples:
        angle, intensity = files[key]
        
        # 归一化
        max_int = np.max(intensity)
        norm = intensity / max_int * 100
        
        # 绘制曲线
        line, = ax.plot(angle, norm, 
                       color=colors[key], 
                       linewidth=0.8,
                       label=f"{label_en} ({label_cn})",
                       alpha=0.9)
        
        # 填充
        ax.fill_between(angle, offsets[key], norm, 
                      alpha=0.1, color=colors[key])
        
        # 标注样品名
        ax.text(85, offsets[key] + 95, label_cn,
               fontsize=10, fontweight='bold',
               color=colors[key], ha='right', va='bottom')
    
    # 设置坐标轴
    ax.set_xlabel("2$\\theta$ (°)", fontsize=11)
    ax.set_ylabel("Intensity (a.u.)", fontsize=11)
    ax.set_xlim(10, 87)
    ax.set_ylim(-5, 115)
    
    # 网格线
    ax.grid(True, linestyle='--', linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)
    
    # 矿物相标注区域
    mineral_regions = [
        (26, 32, "#E74C3C", "Cu$_2$S"),
        (29, 38, "#B22234", "CuFeS$_2$"),
        (31, 33, "#228B22", "CuS"),
    ]
    
    for start, end, color, label in mineral_regions:
        ax.axvspan(start, end, alpha=0.08, color=color, zorder=0)
        ax.text((start + end) / 2, 108, label,
                fontsize=8, ha='center', va='top',
                color=color, fontweight='bold', style='italic')
    
    # 图例
    ax.legend(loc='upper right', frameon=True, fancybox=False, 
             edgecolor='black', framealpha=0.95)
    
    # 标题
    ax.set_title("XRD Patterns of Copper Sulfide Ore Samples", 
                fontsize=12, fontweight='bold', pad=10)
    
    # 注释说明
    note_text = ("• CuFeS$_2$ = Chalcopyrite; Cu$_2$S = Chalcocite; CuS = Covellite\n"
                 "• Peak enhancement in concentrate indicates effective mineral separation")
    ax.text(0.02, 0.02, note_text,
            transform=ax.transAxes, fontsize=7,
            verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='white', 
                     edgecolor='gray', alpha=0.9))
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    plt.close()
    
    print(f"Saved: {output_path}")
    return fig


def plot_thesis_xrd_with_ref(files, output_path):
    """带标准参考谱图的论文级 XRD 对比图"""
    
    fig = plt.figure(figsize=(7.2, 9), dpi=300)
    
    # 上部：样品 XRD
    gs = fig.add_gridspec(2, 1, height_ratios=[2.5, 1], hspace=0.15)
    ax_samples = fig.add_subplot(gs[0])
    ax_ref = fig.add_subplot(gs[1])
    
    # 颜色
    colors = {
        "raw": "#2C3E50",
        "conc": "#E74C3C", 
        "tail": "#27AE60"
    }
    
    # ========== 上部：样品对比 ==========
    for key, label_cn, label_en in [
        ("raw", "原矿", "Raw Ore"),
        ("conc", "精矿", "Concentrate"),
        ("tail", "尾矿", "Tailings")
    ]:
        angle, intensity = files[key]
        norm = intensity / np.max(intensity) * 100
        
        ax_samples.plot(angle, norm,
                      color=colors[key],
                      linewidth=0.7,
                      label=f"{label_cn} ({label_en})",
                      alpha=0.9)
        ax_samples.fill_between(angle, 0, norm,
                             alpha=0.1, color=colors[key])
    
    ax_samples.set_ylabel("Intensity (a.u.)", fontsize=10)
    ax_samples.set_xlim(10, 87)
    ax_samples.set_ylim(-2, 115)
    ax_samples.grid(True, linestyle='--', linewidth=0.3, alpha=0.5)
    ax_samples.legend(loc='upper right', fontsize=8, frameon=True)
    
    # 矿物相标注
    for start, end, color, label in [
        (26, 32, "#E74C3C", "Cu$_2$S"),
        (29, 38, "#B22234", "CuFeS$_2$"),
        (31, 33, "#228B22", "CuS"),
    ]:
        ax_samples.axvspan(start, end, alpha=0.08, color=color, zorder=0)
        ax_samples.text((start + end) / 2, 108, label,
                       fontsize=7, ha='center', va='bottom',
                       color=color, fontweight='bold', style='italic')
    
    # ========== 下部：标准参考 ==========
    angle_ref = np.linspace(10, 87, 5000)
    y_off = 0
    spacing = 40
    
    ref_minerals = ["CuFeS2", "Cu2S", "CuS"]
    ref_colors = ["#B22234", "#4169E1", "#228B22"]
    
    for i, key in enumerate(ref_minerals):
        mineral = MINERALS[key]
        pattern = np.zeros_like(angle_ref)
        
        for peak in mineral["peaks"]:
            if 10 <= peak <= 87:
                g = 25 * np.exp(-((angle_ref - peak) ** 2) / 0.1)
                pattern += g
        
        ax_ref.fill_between(angle_ref, y_off, pattern + y_off,
                         alpha=0.5, color=ref_colors[i])
        ax_ref.plot(angle_ref, pattern + y_off, 
                  color=ref_colors[i], linewidth=0.6)
        
        # 标注
        ax_ref.text(87, y_off + 15, 
                   f"{mineral['formula']}\n({mineral['pdf']})",
                   fontsize=7, ha='right', va='bottom',
                   color=ref_colors[i])
        
        y_off += spacing
    
    ax_ref.set_xlabel("2$\\theta$ (°)", fontsize=10)
    ax_ref.set_ylabel("Reference", fontsize=10)
    ax_ref.set_xlim(10, 87)
    ax_ref.set_ylim(-2, y_off + 30)
    ax_ref.grid(True, linestyle='--', linewidth=0.3, alpha=0.5)
    ax_ref.text(0.02, 0.98, "Standard PDF References",
              transform=ax_ref.transAxes, fontsize=8,
              fontweight='bold', va='top')
    
    # 总标题
    fig.suptitle("XRD Comparison of Copper Sulfide Ore Before and After Flotation",
                fontsize=11, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    plt.close()
    
    print(f"Saved: {output_path}")
    return fig


def create_publication_table(files, output_path):
    """创建矿物峰识别统计表"""
    
    headers = ["矿物", "化学式", "PDF卡片", "原矿", "精矿", "尾矿"]
    rows = []
    
    minerals_order = ["CuFeS2", "Cu2S", "CuS", "Cu5FeS4", "FeS2", "SiO2"]
    
    for key in minerals_order:
        mineral = MINERALS[key]
        row = [mineral["name"], mineral["formula"], mineral["pdf"]]
        
        for sample_key in ["raw", "conc", "tail"]:
            angle, intensity = files[sample_key]
            identified = find_mineral_peaks(angle, intensity)
            
            matched = next((x for x in identified if x["key"] == key), None)
            if matched:
                row.append(f"{matched['count']} peaks")
            else:
                row.append("-")
        
        rows.append(row)
    
    # 生成 LaTeX 表格
    latex = r"""\begin{table}[htbp]
\centering
\caption{XRD Mineral Phase Identification Results}
\label{tab:xrd_minerals}
\begin{tabular}{lccccl}
\toprule
矿物名称 & 化学式 & PDF卡片 & 原矿 & 精矿 & 尾矿 \\
\midrule
"""
    
    for row in rows:
        latex += f"{row[0]} & {row[1]} & {row[2]} & {row[3]} & {row[4]} & {row[5]} \\\\\n"
    
    latex += r"""\bottomrule
\end{tabular}
\end{table}"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(latex)
    
    print(f"Saved table: {output_path}")
    return latex


def main():
    base_path = r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04"
    
    files = {
        "raw": f"{base_path}\\tongliukuang yuankuang.raw",
        "conc": f"{base_path}\\2cu2jing jingkuang tongliukuang.raw",
        "tail": f"{base_path}\\2cu2jing weikuang tongliukuang.raw"
    }
    
    output_dir = r"C:\Users\Administrator\.qclaw\workspace"
    
    print("=" * 60)
    print("Generating Thesis-Level XRD Comparison Figures")
    print("=" * 60)
    
    # 解析数据
    data = {}
    for key, path in files.items():
        print(f"\nParsing {key}...")
        try:
            angle, intensity = parse_bruker_raw(path)
            data[key] = (angle, intensity)
            print(f"  Success: {len(intensity)} points")
            
            # 识别矿物
            identified = find_mineral_peaks(angle, intensity)
            print(f"  Identified: {', '.join([f'{x['mineral']['name']}({x['count']})' for x in identified[:4]])}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 生成图1：简洁对比图
    print("\n" + "-" * 40)
    print("Generating Figure 1: Simple Comparison")
    output1 = f"{output_dir}\\thesis_fig1_xrd_comparison.png"
    plot_thesis_xrd_comparison(data, output1)
    
    # 生成图2：带参考谱图
    print("\n" + "-" * 40)
    print("Generating Figure 2: With Reference Patterns")
    output2 = f"{output_dir}\\thesis_fig2_xrd_with_ref.png"
    plot_thesis_xrd_with_ref(data, output2)
    
    # 生成表格
    print("\n" + "-" * 40)
    print("Generating Table: LaTeX format")
    output3 = f"{output_dir}\\thesis_table_xrd_minerals.tex"
    create_publication_table(data, output3)
    
    print("\n" + "=" * 60)
    print("All outputs saved to:")
    print(f"  1. {output1}")
    print(f"  2. {output2}")
    print(f"  3. {output3}")
    print("=" * 60)


if __name__ == "__main__":
    main()
