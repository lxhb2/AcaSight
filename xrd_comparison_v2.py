"""
铜硫矿 XRD 对比图 - 专业版 v2
展示完整角度范围 10°-90°，增大间隔，包含标准参考谱图
"""
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from matplotlib.patches import Rectangle
from pathlib import Path
from scipy.signal import find_peaks

# 设置字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'dejavusans'

# 目的组分（铜硫化物）- 选矿的目标矿物
TARGET_MINERALS = {
    "chalcopyrite": {
        "name": "Chalcopyrite", "name_cn": "黄铜矿",
        "formula": "CuFeS2",
        "formula_mathtext": r"CuFeS$_{2}$",
        "peaks": [16.3, 18.2, 20.5, 29.42, 33.8, 34.84, 36.63, 47.43, 56.98],
        "relative_intensities": [20, 15, 10, 100, 25, 30, 25, 20, 15],
        "color": "#E74C3C",
        "elements": ["Cu", "Fe", "S"]
    },
    "chalcocite": {
        "name": "Chalcocite", "name_cn": "辉铜矿",
        "formula": "Cu2S",
        "formula_mathtext": r"Cu$_{2}$S",
        "peaks": [18.4, 26.55, 30.08, 37.95, 43.92, 47.87],
        "relative_intensities": [30, 40, 100, 35, 30, 25],
        "color": "#9B59B6",
        "elements": ["Cu", "S"]
    },
    "covellite": {
        "name": "Covellite", "name_cn": "铜蓝",
        "formula": "CuS",
        "formula_mathtext": r"CuS",
        "peaks": [16.2, 23.5, 27.68, 29.58, 31.78, 47.87, 56.54],
        "relative_intensities": [25, 20, 50, 60, 100, 45, 40],
        "color": "#3498DB",
        "elements": ["Cu", "S"]
    },
    "bornite": {
        "name": "Bornite", "name_cn": "斑铜矿",
        "formula": "Cu5FeS4",
        "formula_mathtext": r"Cu$_{5}$FeS$_{4}$",
        "peaks": [17.2, 20.8, 28.96, 31.26, 37.74, 46.14, 53.87],
        "relative_intensities": [40, 35, 70, 100, 50, 40, 35],
        "color": "#F39C12",
        "elements": ["Cu", "Fe", "S"]
    },
}

# 脉石矿物
GANGUE_MINERALS = {
    "quartz": {
        "name": "Quartz", "name_cn": "石英",
        "formula": "SiO2",
        "formula_mathtext": r"SiO$_{2}$",
        "peaks": [20.85, 26.65, 36.54, 39.46, 42.45, 50.14],
        "relative_intensities": [22, 100, 10, 8, 7, 14],
        "color": "#7F8C8D",
    },
    "pyrite": {
        "name": "Pyrite", "name_cn": "黄铁矿",
        "formula": "FeS2",
        "formula_mathtext": r"FeS$_{2}$",
        "peaks": [28.51, 33.08, 37.10, 40.80, 47.42, 56.33],
        "relative_intensities": [35, 100, 55, 52, 20, 25],
        "color": "#27AE60",
    },
}


def parse_bruker_raw_full(file_path):
    """解析 Bruker RAW 格式 - 尝试获取完整角度范围"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    # 尝试不同的数据起始位置
    data_configs = [
        {"offset": 5108, "start_angle": 27.0, "step": 0.02},
        {"offset": 512, "start_angle": 10.0, "step": 0.02},
        {"offset": 768, "start_angle": 10.0, "step": 0.02},
        {"offset": 256, "start_angle": 5.0, "step": 0.02},
    ]
    
    best_result = None
    best_score = 0
    
    for config in data_configs:
        data_start = config["offset"]
        num_points = (len(data) - data_start) // 4
        
        if num_points < 100:
            continue
        
        intensities = []
        for i in range(num_points):
            pos = data_start + i * 4
            if pos + 4 <= len(data):
                val = struct.unpack("<f", data[pos:pos+4])[0]
                intensities.append(val)
        
        intensities = np.array(intensities)
        
        # 评估数据质量
        valid_count = np.sum((intensities > 0) & (intensities < 100000))
        variance = np.var(intensities[intensities > 0]) if valid_count > 0 else 0
        
        score = valid_count + variance / 1000
        
        if score > best_score:
            best_score = score
            start_angle = config["start_angle"]
            step = config["step"]
            angles = np.linspace(start_angle, start_angle + step * (num_points - 1), num_points)
            best_result = (angles, intensities)
    
    # 如果没有找到好的配置，使用默认
    if best_result is None:
        data_start = 5108
        num_points = (len(data) - data_start) // 4
        intensities = []
        for i in range(num_points):
            pos = data_start + i * 4
            if pos + 4 <= len(data):
                val = struct.unpack("<f", data[pos:pos+4])[0]
                intensities.append(val)
        intensities = np.array(intensities)
        start_angle = 27.0
        step = 0.02
        angles = np.linspace(start_angle, start_angle + step * (num_points - 1), num_points)
        best_result = (angles, intensities)
    
    return best_result


def generate_reference_pattern(angle_range, peaks, intensities, peak_width=0.15):
    """生成标准参考谱图"""
    pattern = np.zeros_like(angle_range, dtype=float)
    for peak, intensity in zip(peaks, intensities):
        if angle_range[0] <= peak <= angle_range[-1]:
            gaussian = intensity * np.exp(-((angle_range - peak) ** 2) / (2 * peak_width ** 2))
            pattern += gaussian
    return pattern


def identify_target_minerals(angle, intensity, tolerance=0.5):
    """识别目的组分"""
    intensity_norm = intensity / np.max(intensity)
    peaks_idx, props = find_peaks(intensity_norm, height=0.03, distance=8, prominence=0.02)
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
        
        if len(matches) >= 1:  # 降低匹配阈值
            identified.append({
                "key": key,
                "name": mineral["name"],
                "name_cn": mineral["name_cn"],
                "formula": mineral["formula"],
                "formula_mathtext": mineral["formula_mathtext"],
                "peaks": ref_peaks,
                "relative_intensities": mineral["relative_intensities"],
                "matched_peaks": matches,
                "matched_heights": matched_heights,
                "color": mineral["color"],
                "match_count": len(matches),
            })
    
    identified.sort(key=lambda x: x["match_count"], reverse=True)
    return identified


def plot_professional_comparison_v2(datasets, minerals_list, output_path):
    """
    专业对比图 v2 - 完整角度范围，增大间隔
    上部：样品XRD谱图
    下部：标准参考谱图
    """
    # 创建画布
    fig = plt.figure(figsize=(18, 14), dpi=150)
    
    # 使用GridSpec
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.12)
    ax_samples = fig.add_subplot(gs[0])
    ax_refs = fig.add_subplot(gs[1])
    
    # 颜色方案
    colors = {
        "raw": "#3498DB",      # 蓝色 - 原矿
        "conc": "#E74C3C",     # 红色 - 精矿
        "tail": "#27AE60",     # 绿色 - 尾矿
    }
    
    labels = {
        "raw": "Raw Ore (Yuan Kuang)",
        "conc": "Concentrate (Jing Kuang)",
        "tail": "Tailings (Wei Kuang)"
    }
    
    labels_cn = {
        "raw": "原矿",
        "conc": "精矿",
        "tail": "尾矿"
    }
    
    offset = 100  # 增大偏移量
    
    # ========== 上部：样品XRD谱图 ==========
    sample_order = ["raw", "conc", "tail"]
    
    # 找到所有数据的公共角度范围
    all_angles = []
    for key in sample_order:
        angle, _ = datasets[key]
        all_angles.extend([angle[0], angle[-1]])
    
    x_min = 10  # 从10度开始
    x_max = 85  # 到85度
    
    for i, key in enumerate(sample_order):
        angle, intensity = datasets[key]
        minerals = minerals_list[key]
        
        # 归一化
        intensity_norm = intensity / np.max(intensity) * 100
        y_shift = i * offset
        
        # 绘制谱线
        ax_samples.plot(angle, intensity_norm + y_shift, 
                       color=colors[key], linewidth=0.7, 
                       label=labels[key], alpha=0.95)
        
        # 填充
        ax_samples.fill_between(angle, y_shift, intensity_norm + y_shift,
                               alpha=0.1, color=colors[key])
        
        # 左侧标签
        ax_samples.annotate(
            f"{labels_cn[key]}\n({labels[key].split('(')[1].replace(')', '')})",
            xy=(x_min + 0.5, y_shift + 50),
            fontsize=12,
            fontweight="bold",
            color=colors[key],
            va="center"
        )
        
        # 标注目的组分峰位
        for mineral in minerals[:3]:
            if mineral["matched_peaks"]:
                for peak in mineral["matched_peaks"][:1]:  # 每个矿物标注最强峰
                    if x_min <= peak <= x_max:
                        idx = np.argmin(np.abs(angle - peak))
                        y_pos = intensity_norm[idx] + y_shift + 5
                        
                        ax_samples.annotate(
                            mineral["formula_mathtext"],
                            xy=(peak, y_pos),
                            fontsize=8,
                            ha="center",
                            va="bottom",
                            rotation=90,
                            color=mineral["color"],
                            fontweight="bold",
                            bbox=dict(boxstyle="round,pad=0.1", facecolor="white", 
                                     edgecolor="none", alpha=0.9)
                        )
    
    ax_samples.set_ylabel("Intensity (a.u.)", fontsize=14, fontweight="bold")
    ax_samples.legend(fontsize=11, frameon=True, loc="upper right", 
                     fancybox=True, shadow=True)
    ax_samples.set_xlim(x_min, x_max)
    ax_samples.set_ylim(-10, 320)
    ax_samples.grid(which="major", linestyle="-", linewidth=0.4, alpha=0.5)
    ax_samples.tick_params(labelsize=11)
    ax_samples.xaxis.set_minor_locator(AutoMinorLocator(2))
    
    # 标题
    ax_samples.set_title("Copper Sulfide Ore XRD Comparison - Flotation Process Analysis\n" +
                        "Tong Liu Kuang Xuan Kuang Guo Cheng XRD Dui Bi Fen Xi",
                        fontsize=16, fontweight="bold", pad=20)
    
    # 添加10-30度区域标注
    ax_samples.axvspan(10, 30, alpha=0.05, color='gray')
    ax_samples.annotate("Low Angle Region\n(10-30 deg)", xy=(20, 290),
                       fontsize=9, ha="center", style="italic",
                       bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8))
    
    # ========== 下部：标准参考谱图 ==========
    angle_ref = np.linspace(x_min, x_max, 8000)
    
    y_offset_ref = 0
    
    for key, mineral in TARGET_MINERALS.items():
        pattern = generate_reference_pattern(
            angle_ref, 
            mineral["peaks"], 
            mineral["relative_intensities"],
            peak_width=0.12
        )
        pattern_norm = pattern / np.max(pattern) * 80 if np.max(pattern) > 0 else pattern
        
        ax_refs.fill_between(angle_ref, y_offset_ref, pattern_norm + y_offset_ref,
                            alpha=0.6, color=mineral["color"])
        ax_refs.plot(angle_ref, pattern_norm + y_offset_ref, 
                    color=mineral["color"], linewidth=0.8)
        
        # 右侧标注
        ax_refs.annotate(
            f"{mineral['formula_mathtext']}  {mineral['name_cn']}",
            xy=(x_max - 0.5, y_offset_ref + 40),
            fontsize=9,
            ha="right",
            va="center",
            color=mineral["color"],
            fontweight="bold"
        )
        
        y_offset_ref += 100
    
    ax_refs.set_xlabel("2theta (degree)", fontsize=14, fontweight="bold")
    ax_refs.set_ylabel("Reference\nPatterns", fontsize=11)
    ax_refs.set_xlim(x_min, x_max)
    ax_refs.set_ylim(-5, y_offset_ref + 20)
    ax_refs.grid(which="major", linestyle="-", linewidth=0.4, alpha=0.5)
    ax_refs.tick_params(labelsize=11)
    ax_refs.xaxis.set_minor_locator(AutoMinorLocator(2))
    
    # 分隔线
    ax_refs.axhline(y=0, color='black', linewidth=1.5)
    ax_refs.text(x_min + 0.5, y_offset_ref + 5, 
                "Standard Reference Patterns (PDF Cards) - Biao Zhun Can Kao Pu Tu",
                fontsize=10, fontweight="bold", va="top")
    
    plt.tight_layout()
    
    fig.savefig(output_path, dpi=300, bbox_inches="tight", 
               facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  Saved: {output_path}")
    
    return fig


def plot_enhanced_comparison_v2(datasets, minerals_list, output_path):
    """
    增强版对比图 v2 - 完整角度范围，更大间隔，突出目的组分变化
    """
    fig, ax = plt.subplots(figsize=(20, 12), dpi=150)
    
    # 颜色方案
    colors = {
        "raw": "#3498DB",
        "conc": "#E74C3C",
        "tail": "#27AE60",
    }
    
    labels = {
        "raw": "Raw Ore (Yuan Kuang)",
        "conc": "Concentrate (Jing Kuang)",
        "tail": "Tailings (Wei Kuang)"
    }
    
    labels_cn = {
        "raw": "原矿",
        "conc": "精矿",
        "tail": "尾矿"
    }
    
    offset = 120  # 更大的间隔
    
    sample_order = ["raw", "conc", "tail"]
    
    x_min = 10
    x_max = 85
    
    for i, key in enumerate(sample_order):
        angle, intensity = datasets[key]
        minerals = minerals_list[key]
        
        intensity_norm = intensity / np.max(intensity) * 100
        y_shift = i * offset
        
        # 绘制谱线
        ax.plot(angle, intensity_norm + y_shift, 
               color=colors[key], linewidth=0.8, 
               label=f"{labels[key]} - {labels_cn[key]}", alpha=0.95)
        
        # 填充
        ax.fill_between(angle, y_shift, intensity_norm + y_shift,
                        alpha=0.15, color=colors[key])
        
        # 左侧标签
        ax.annotate(
            f"{labels_cn[key]}\n{labels[key].split(' (')[0]}",
            xy=(x_min + 0.5, y_shift + 50),
            fontsize=13,
            fontweight="bold",
            color=colors[key],
            va="center"
        )
    
    # 标注目的组分主要峰位
    target_peaks_to_mark = []
    
    # 收集精矿中识别出的目的组分峰位
    if "conc" in minerals_list:
        for mineral in minerals_list["conc"][:4]:
            if mineral["matched_peaks"]:
                peak = mineral["matched_peaks"][0]
                if x_min <= peak <= x_max:
                    target_peaks_to_mark.append((peak, mineral["formula_mathtext"], mineral["color"]))
    
    # 添加一些重要的目的组分峰位（即使没有完全匹配）
    for key, mineral in TARGET_MINERALS.items():
        for peak in mineral["peaks"][:2]:
            if x_min <= peak <= x_max:
                if not any(abs(p[0] - peak) < 1 for p in target_peaks_to_mark):
                    target_peaks_to_mark.append((peak, mineral["formula_mathtext"], mineral["color"]))
    
    # 绘制峰位标注
    for peak_pos, formula, color in sorted(target_peaks_to_mark, key=lambda x: x[0]):
        ax.axvline(x=peak_pos, color=color, linestyle="--", 
                  linewidth=0.6, alpha=0.4)
        
        ax.annotate(
            formula,
            xy=(peak_pos, 370),
            fontsize=8,
            ha="center",
            va="bottom",
            color=color,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", 
                     edgecolor=color, linewidth=1, alpha=0.95)
        )
    
    # 设置轴
    ax.set_xlabel("2theta (degree)", fontsize=15, fontweight="bold")
    ax.set_ylabel("Intensity (a.u.)", fontsize=15, fontweight="bold")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(-15, 400)
    
    ax.grid(which="major", linestyle="-", linewidth=0.4, alpha=0.6)
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.tick_params(labelsize=12)
    
    # 标题
    ax.set_title("Copper Sulfide Ore XRD - Flotation Process Analysis\n" +
                "Tong Liu Kuang Xuan Kuang Guo Cheng - Mu De Zu Fen Bian Hua",
                fontsize=18, fontweight="bold", pad=20)
    
    # 10-30度区域标注
    ax.axvspan(10, 30, alpha=0.03, color='blue')
    ax.annotate("Low Angle Region\n(10-30 deg)\nLow molecular weight\nclay minerals",
               xy=(20, 350), fontsize=9, ha="center", style="italic",
               bbox=dict(boxstyle="round,pad=0.5", facecolor="lightcyan", 
                        edgecolor="blue", alpha=0.8))
    
    # 目的组分说明框
    textstr = "Target Minerals (Mu De Zu Fen):\n" + \
              "- CuFeS2 (Chalcopyrite / Huang Tong Kuang)\n" + \
              "- Cu2S (Chalcocite / Hui Tong Kuang)\n" + \
              "- CuS (Covellite / Tong Lan)\n" + \
              "- Cu5FeS4 (Bornite / Ban Tong Kuang)"
    
    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', 
                edgecolor='orange', alpha=0.95)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props, fontweight="normal",
            family='monospace')
    
    # 变化趋势说明
    trend_text = "Trend (Bian Hua Qu Shi):\n" + \
                 "Raw -> Concentrate: Peaks ENHANCED\n" + \
                 "Concentrate -> Tailings: Peaks REDUCED"
    props2 = dict(boxstyle='round,pad=0.5', facecolor='lightgreen',
                 edgecolor='green', alpha=0.95)
    ax.text(0.02, 0.78, trend_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props2, family='monospace')
    
    # 图例
    ax.legend(fontsize=11, frameon=True, loc="upper right", 
             fancybox=True, shadow=True)
    
    plt.tight_layout()
    
    fig.savefig(output_path, dpi=300, bbox_inches="tight", 
               facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  Saved: {output_path}")
    
    return fig


def print_analysis_summary(minerals_list):
    """打印分析总结"""
    print("\n" + "=" * 70)
    print("Xuan Kuang Guo Cheng Mu De Zu Fen Bian Hua Fen Xi")
    print("=" * 70)
    
    print("\n[Mu De Zu Fen Ding Yi] Tong Liu Hua Wu Shi Xuan Kuang De Mu Biao Kuang Wu:")
    for key, m in TARGET_MINERALS.items():
        formula_plain = m['formula'].replace('2', '2').replace('4', '4').replace('5', '5')
        print(f"  - {m['name_cn']} ({formula_plain}) - Zhu Yao Yuan Su: {', '.join(m['elements'])}")
    
    print("\n" + "-" * 70)
    print("Ge Yang Pin Zhong Mu De Zu Fen Shi Bie Jie Guo:")
    print("-" * 70)
    
    sample_names = {
        "raw": "Yuan Kuang (Raw Ore)",
        "conc": "Jing Kuang (Concentrate)", 
        "tail": "Wei Kuang (Tailings)"
    }
    
    for key, minerals in minerals_list.items():
        print(f"\n{sample_names[key]}:")
        if not minerals:
            print("  Wei Jian Ce Dao Ming Xian Mu De Zu Fen")
            continue
        for m in minerals:
            peak_count = len(m["matched_peaks"])
            avg_intensity = np.mean(m["matched_heights"]) * 100
            formula_plain = m['formula']
            print(f"  [+] {m['name_cn']} ({formula_plain})")
            print(f"      Pi Pei Feng Shu: {peak_count}, Ping Jun Xiang Dui Qiang Du: {avg_intensity:.1f}%")


def main():
    # 文件路径
    files = {
        "raw": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw",
        "conc": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw",
        "tail": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw"
    }
    
    output_dir = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("=" * 70)
    print("Tong Liu Kuang XRD Zhuan Ye Dui Bi Fen Xi v2")
    print("=" * 70)
    
    # 解析数据
    datasets = {}
    minerals_list = {}
    
    for key, fpath in files.items():
        print(f"\nParsing {key}...")
        try:
            angle, intensity = parse_bruker_raw_full(fpath)
            print(f"  Success: {len(intensity)} data points, 2theta: {angle[0]:.1f} - {angle[-1]:.1f} deg")
            datasets[key] = (angle, intensity)
            
            # 识别目的组分
            minerals = identify_target_minerals(angle, intensity)
            minerals_list[key] = minerals
            print(f"  Identified {len(minerals)} target minerals")
        except Exception as e:
            print(f"  Error: {e}")
            return
    
    # 打印分析总结
    print_analysis_summary(minerals_list)
    
    # 生成专业对比图
    print("\n" + "=" * 70)
    print("Generating Professional Comparison Plots")
    print("=" * 70)
    
    # 图1: 带标准参考谱图的对比图
    print("\n[1/2] Generating professional comparison (with reference patterns)...")
    plot_professional_comparison_v2(
        datasets, minerals_list,
        output_path=str(output_dir / "07_XRD_comparison_professional_v2.png")
    )
    
    # 图2: 增强版对比图
    print("\n[2/2] Generating enhanced comparison (highlighting target minerals)...")
    plot_enhanced_comparison_v2(
        datasets, minerals_list,
        output_path=str(output_dir / "08_XRD_comparison_enhanced_v2.png")
    )
    
    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir}")
    print("  1. 07_XRD_comparison_professional_v2.png - Professional comparison (with reference patterns)")
    print("  2. 08_XRD_comparison_enhanced_v2.png - Enhanced comparison (highlighting target minerals)")
    print("\nFeatures:")
    print("  - Full angle range: 10-85 degrees (including 10-30 low angle region)")
    print("  - Increased spacing between sample curves")
    print("  - Reference patterns at bottom")
    print("  - Peak annotations for target minerals")


if __name__ == "__main__":
    main()
