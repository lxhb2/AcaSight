"""
铜硫矿 XRD 对比图 - 最终版 v3
正确解析 10-87° 数据，增大间隔，保留标准参考谱图
"""
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from pathlib import Path
from scipy.signal import find_peaks

# 设置字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'dejavusans'

# 目的组分（铜硫化物）
TARGET_MINERALS = {
    "chalcopyrite": {
        "name": "Chalcopyrite", "name_cn": "Huang Tong Kuang",
        "formula_mathtext": r"CuFeS$_{2}$",
        "peaks": [29.42, 34.84, 36.63, 47.43, 56.98],
        "color": "#E74C3C",
    },
    "chalcocite": {
        "name": "Chalcocite", "name_cn": "Hui Tong Kuang",
        "formula_mathtext": r"Cu$_{2}$S",
        "peaks": [26.55, 30.08, 37.95, 43.92, 47.87],
        "color": "#9B59B6",
    },
    "covellite": {
        "name": "Covellite", "name_cn": "Tong Lan",
        "formula_mathtext": r"CuS",
        "peaks": [27.68, 29.58, 31.78, 47.87, 56.54],
        "color": "#3498DB",
    },
    "bornite": {
        "name": "Bornite", "name_cn": "Ban Tong Kuang",
        "formula_mathtext": r"Cu$_{5}$FeS$_{4}$",
        "peaks": [28.96, 31.26, 37.74, 46.14, 53.87],
        "color": "#F39C12",
    },
}


def parse_bruker_raw_correct(file_path):
    """正确解析 Bruker RAW 格式 - 从偏移 892 开始"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    # 正确的起始偏移和角度
    data_start = 892  # 真正 XRD 数据起始
    start_angle = 10.0  # 从 10 度开始
    step = 0.02  # 步长
    
    num_points = (len(data) - data_start) // 4
    intensities = []
    
    for i in range(num_points):
        pos = data_start + i * 4
        if pos + 4 <= len(data):
            val = struct.unpack("<f", data[pos:pos+4])[0]
            # 过滤不合理值
            if 0 < val < 10000:
                intensities.append(val)
            else:
                intensities.append(0)
    
    intensities = np.array(intensities)
    angles = np.linspace(start_angle, start_angle + step * (len(intensities) - 1), len(intensities))
    
    return angles, intensities


def generate_reference_pattern(angle_range, peaks, intensity, peak_width=0.15):
    """生成标准参考谱图"""
    pattern = np.zeros_like(angle_range, dtype=float)
    for peak in peaks:
        if angle_range[0] <= peak <= angle_range[-1]:
            gaussian = intensity * np.exp(-((angle_range - peak) ** 2) / (2 * peak_width ** 2))
            pattern += gaussian
    return pattern


def identify_target_minerals(angle, intensity, tolerance=0.5):
    """识别目的组分"""
    intensity_norm = intensity / np.max(intensity) if np.max(intensity) > 0 else intensity
    peaks_idx, props = find_peaks(intensity_norm, height=0.05, distance=10, prominence=0.02)
    sample_peaks = angle[peaks_idx]
    
    identified = []
    for key, mineral in TARGET_MINERALS.items():
        ref_peaks = mineral["peaks"]
        matches = []
        matched_heights = []
        
        for ref_peak in ref_peaks:
            for i, sp in enumerate(sample_peaks):
                if abs(sp - ref_peak) <= tolerance:
                    matches.append(sp)
                    matched_heights.append(intensity_norm[peaks_idx[i]])
                    break
        
        if len(matches) >= 1:
            identified.append({
                "key": key,
                "name": mineral["name"],
                "name_cn": mineral["name_cn"],
                "formula_mathtext": mineral["formula_mathtext"],
                "peaks": ref_peaks,
                "matched_peaks": matches,
                "matched_heights": matched_heights,
                "color": mineral["color"],
                "match_count": len(matches),
            })
    
    identified.sort(key=lambda x: x["match_count"], reverse=True)
    return identified


def plot_comparison_final(datasets, minerals_list, output_path):
    """
    最终版对比图
    - 完整 10-87° 角度范围
    - 样品间隔更大
    - 包含标准参考谱图
    """
    fig = plt.figure(figsize=(20, 14), dpi=150)
    
    # 上部：样品 XRD 谱图
    # 下部：标准参考谱图
    gs = fig.add_gridspec(2, 1, height_ratios=[3.5, 1], hspace=0.15)
    ax_samples = fig.add_subplot(gs[0])
    ax_refs = fig.add_subplot(gs[1])
    
    # 颜色
    colors = {"raw": "#2C3E50", "conc": "#C0392B", "tail": "#27AE60"}
    labels = {
        "raw": "Raw Ore (Yuan Kuang)",
        "conc": "Concentrate (Jing Kuang)", 
        "tail": "Tailings (Wei Kuang)"
    }
    labels_cn = {"raw": "Yuan Kuang", "conc": "Jing Kuang", "tail": "Wei Kuang"}
    
    offset = 150  # 增大间隔
    
    sample_order = ["raw", "conc", "tail"]
    x_min, x_max = 10, 87
    
    # ========== 上部：样品 XRD ==========
    for i, key in enumerate(sample_order):
        angle, intensity = datasets[key]
        minerals = minerals_list[key]
        
        # 归一化到 0-100
        max_int = np.max(intensity)
        intensity_norm = intensity / max_int * 100 if max_int > 0 else intensity
        y_shift = i * offset
        
        # 绘制谱线
        ax_samples.plot(angle, intensity_norm + y_shift, 
                       color=colors[key], linewidth=0.8, 
                       label=f"{labels[key]}", alpha=0.9)
        
        # 填充
        ax_samples.fill_between(angle, y_shift, intensity_norm + y_shift,
                              alpha=0.15, color=colors[key])
        
        # 左侧标签
        ax_samples.annotate(
            f"{labels_cn[key]}",
            xy=(x_min + 0.5, y_shift + 75),
            fontsize=14,
            fontweight="bold",
            color=colors[key],
            va="center"
        )
        
        # 标注目的组分峰
        for mineral in minerals[:4]:
            if mineral["matched_peaks"]:
                for peak in mineral["matched_peaks"][:2]:
                    if x_min <= peak <= x_max:
                        idx = np.argmin(np.abs(angle - peak))
                        y_pos = intensity_norm[idx] + y_shift + 8
                        
                        ax_samples.annotate(
                            mineral["formula_mathtext"],
                            xy=(peak, y_pos),
                            fontsize=9,
                            ha="center",
                            va="bottom",
                            rotation=90,
                            color=mineral["color"],
                            fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.1", facecolor="white", 
                                     edgecolor="none", alpha=0.9)
                        )
    
    ax_samples.set_ylabel("Intensity (a.u.)", fontsize=14, fontweight="bold")
    ax_samples.legend(fontsize=12, frameon=True, loc="upper right", fancybox=True)
    ax_samples.set_xlim(x_min, x_max)
    ax_samples.set_ylim(-10, 480)
    ax_samples.grid(which="major", linestyle="-", linewidth=0.4, alpha=0.5)
    ax_samples.tick_params(labelsize=12)
    ax_samples.xaxis.set_minor_locator(AutoMinorLocator(2))
    
    ax_samples.set_title("Copper Sulfide Ore XRD Comparison - Flotation Process Analysis\n" +
                        "Tong Liu Kuang Xuan Kuang Guo Cheng XRD Dui Bi Fen Xi",
                        fontsize=16, fontweight="bold", pad=20)
    
    # 10-30 度区域标注
    ax_samples.axvspan(10, 30, alpha=0.03, color='blue')
    ax_samples.annotate("Low Angle Region\n(10-30 deg)", xy=(20, 460),
                       fontsize=10, ha="center", style="italic",
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.9))
    
    # ========== 下部：标准参考谱图 ==========
    angle_ref = np.linspace(x_min, x_max, 8000)
    y_offset = 0
    
    for key, mineral in TARGET_MINERALS.items():
        pattern = generate_reference_pattern(angle_ref, mineral["peaks"], 80, peak_width=0.15)
        
        ax_refs.fill_between(angle_ref, y_offset, pattern + y_offset,
                            alpha=0.6, color=mineral["color"])
        ax_refs.plot(angle_ref, pattern + y_offset, color=mineral["color"], linewidth=0.8)
        
        # 右侧标注
        ax_refs.annotate(
            f"{mineral['formula_mathtext']}  {mineral['name_cn']}",
            xy=(x_max - 0.5, y_offset + 40),
            fontsize=10,
            ha="right",
            va="center",
            color=mineral["color"],
            fontweight="bold"
        )
        
        y_offset += 100
    
    ax_refs.set_xlabel("2theta (degree)", fontsize=14, fontweight="bold")
    ax_refs.set_ylabel("Reference\nPatterns", fontsize=11)
    ax_refs.set_xlim(x_min, x_max)
    ax_refs.set_ylim(-5, y_offset + 30)
    ax_refs.grid(which="major", linestyle="-", linewidth=0.4, alpha=0.5)
    ax_refs.tick_params(labelsize=11)
    
    ax_refs.axhline(y=0, color='black', linewidth=1.5)
    ax_refs.text(x_min + 0.5, y_offset + 10, 
                "Standard Reference Patterns (PDF Cards)",
                fontsize=11, fontweight="bold", va="top")
    
    plt.tight_layout()
    
    fig.savefig(output_path, dpi=300, bbox_inches="tight", 
               facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  Saved: {output_path}")
    
    return fig


def main():
    files = {
        "raw": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw",
        "conc": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw",
        "tail": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw"
    }
    
    output_dir = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("=" * 70)
    print("Tong Liu Kuang XRD Final Version v3")
    print("Correct data parsing: 10-87 degrees, increased spacing")
    print("=" * 70)
    
    datasets = {}
    minerals_list = {}
    
    for key, fpath in files.items():
        print(f"\nParsing {key}...")
        try:
            angle, intensity = parse_bruker_raw_correct(fpath)
            print(f"  Success: {len(intensity)} points, 2theta: {angle[0]:.1f} - {angle[-1]:.1f} deg")
            print(f"  Max intensity: {np.max(intensity):.1f}")
            datasets[key] = (angle, intensity)
            
            minerals = identify_target_minerals(angle, intensity)
            minerals_list[key] = minerals
            print(f"  Identified {len(minerals)} target minerals")
            for m in minerals[:3]:
                print(f"    - {m['name_cn']} ({m['formula_mathtext']}) matched {m['match_count']} peaks")
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            return
    
    # 生成图
    print("\n" + "=" * 70)
    print("Generating Final Comparison Plot")
    print("=" * 70)
    
    output_path = str(output_dir / "09_XRD_comparison_final.png")
    plot_comparison_final(datasets, minerals_list, output_path)
    
    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)
    print(f"\nOutput: {output_path}")


if __name__ == "__main__":
    main()
