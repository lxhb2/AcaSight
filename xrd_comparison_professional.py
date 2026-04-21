"""
铜硫矿 XRD 对比图 - 专业版
突出选矿过程中目的组分的变化
包含标准参考谱图
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

# 目的组分（铜硫化物）- 这是选矿的目标矿物
TARGET_MINERALS = {
    "chalcopyrite": {
        "name": "Chalcopyrite", "name_cn": "黄铜矿",
        "formula": "CuFeS₂",
        "formula_mathtext": r"CuFeS$_{2}$",
        "peaks": [29.42, 34.84, 36.63, 47.43, 56.98],
        "relative_intensities": [100, 30, 25, 20, 15],
        "color": "#E74C3C",  # 红色系 - 主要目的组分
        "elements": ["Cu", "Fe", "S"]
    },
    "chalcocite": {
        "name": "Chalcocite", "name_cn": "辉铜矿",
        "formula": "Cu₂S",
        "formula_mathtext": r"Cu$_{2}$S",
        "peaks": [26.55, 30.08, 37.95, 43.92, 47.87],
        "relative_intensities": [40, 100, 35, 30, 25],
        "color": "#9B59B6",  # 紫色系
        "elements": ["Cu", "S"]
    },
    "covellite": {
        "name": "Covellite", "name_cn": "铜蓝",
        "formula": "CuS",
        "formula_mathtext": r"CuS",
        "peaks": [27.68, 29.58, 31.78, 47.87, 56.54],
        "relative_intensities": [50, 60, 100, 45, 40],
        "color": "#3498DB",  # 蓝色系
        "elements": ["Cu", "S"]
    },
    "bornite": {
        "name": "Bornite", "name_cn": "斑铜矿",
        "formula": "Cu₅FeS₄",
        "formula_mathtext": r"Cu$_{5}$FeS$_{4}$",
        "peaks": [28.96, 31.26, 37.74, 46.14, 53.87],
        "relative_intensities": [70, 100, 50, 40, 35],
        "color": "#F39C12",  # 橙色系
        "elements": ["Cu", "Fe", "S"]
    },
}

# 脉石矿物（非目的组分）
GANGUE_MINERALS = {
    "quartz": {
        "name": "Quartz", "name_cn": "石英",
        "formula": "SiO₂",
        "formula_mathtext": r"SiO$_{2}$",
        "peaks": [20.85, 26.65, 36.54, 39.46, 42.45, 50.14],
        "relative_intensities": [22, 100, 10, 8, 7, 14],
        "color": "#7F8C8D",  # 灰色系
    },
    "pyrite": {
        "name": "Pyrite", "name_cn": "黄铁矿",
        "formula": "FeS₂",
        "formula_mathtext": r"FeS$_{2}$",
        "peaks": [28.51, 33.08, 37.10, 40.80, 47.42, 56.33],
        "relative_intensities": [35, 100, 55, 52, 20, 25],
        "color": "#27AE60",  # 绿色系
    },
    "calcite": {
        "name": "Calcite", "name_cn": "方解石",
        "formula": "CaCO₃",
        "formula_mathtext": r"CaCO$_{3}$",
        "peaks": [23.04, 29.42, 35.98, 39.42, 43.18, 47.48],
        "relative_intensities": [18, 100, 14, 12, 11, 15],
        "color": "#95A5A6",
    },
}


def parse_bruker_raw_v3(file_path):
    """解析 Bruker RAW 格式"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    data_start = 5108
    num_points = (len(data) - data_start) // 4
    
    intensities = []
    for i in range(num_points):
        pos = data_start + i * 4
        if pos + 4 <= len(data):
            val = struct.unpack("<f", data[pos:pos+4])[0]
            intensities.append(val)
    
    intensities = np.array(intensities)
    step = 0.02
    start_angle = 27.0
    angles = np.linspace(start_angle, start_angle + step * (num_points - 1), num_points)
    
    return angles, intensities


def generate_reference_pattern(angle_range, peaks, intensities, peak_width=0.15):
    """生成标准参考谱图（模拟PDF卡片）"""
    pattern = np.zeros_like(angle_range, dtype=float)
    for peak, intensity in zip(peaks, intensities):
        if angle_range[0] <= peak <= angle_range[-1]:
            # 使用高斯峰形
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
        
        if len(matches) >= 2:
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


def plot_professional_comparison(datasets, minerals_list, output_path):
    """绘制专业对比图：上部样品谱图 + 下部标准参考谱图"""
    
    # 创建画布 - 上部大区域用于样品，下部用于标准谱图
    fig = plt.figure(figsize=(14, 12), dpi=150)
    
    # 使用GridSpec实现复杂布局
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.15)
    ax_samples = fig.add_subplot(gs[0])
    ax_refs = fig.add_subplot(gs[1])
    
    # 颜色方案
    colors = {
        "raw": "#3498DB",      # 蓝色 - 原矿
        "conc": "#E74C3C",     # 红色 - 精矿（重点突出）
        "tail": "#27AE60",     # 绿色 - 尾矿
    }
    
    labels = {
        "raw": "Raw Ore (原矿)",
        "conc": "Concentrate (精矿)",
        "tail": "Tailings (尾矿)"
    }
    
    offset = 60  # 偏移量更大
    
    # ========== 上部：样品XRD谱图 ==========
    sample_order = ["raw", "conc", "tail"]
    
    for i, key in enumerate(sample_order):
        angle, intensity = datasets[key]
        minerals = minerals_list[key]
        
        # 归一化
        intensity_norm = intensity / np.max(intensity) * 100
        y_shift = i * offset
        
        ax_samples.plot(angle, intensity_norm + y_shift, 
                       color=colors[key], linewidth=0.8, 
                       label=labels[key], alpha=0.9)
        
        # 标注目的组分峰位
        for mineral in minerals[:4]:  # 主要目的组分
            if mineral["matched_peaks"]:
                # 找最强峰
                peak_angle = mineral["matched_peaks"][0]
                idx = np.argmin(np.abs(angle - peak_angle))
                y_pos = intensity_norm[idx] + y_shift + 3
                
                # 标注化学式
                ax_samples.annotate(
                    mineral["formula_mathtext"],
                    xy=(peak_angle, y_pos),
                    fontsize=8,
                    ha="center",
                    va="bottom",
                    rotation=90,
                    color=mineral["color"],
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.1", facecolor="white", 
                             edgecolor="none", alpha=0.9)
                )
    
    ax_samples.set_ylabel("Intensity (a.u.)", fontsize=12, fontweight="bold")
    ax_samples.legend(fontsize=11, frameon=True, loc="upper right", 
                     fancybox=True, shadow=True)
    ax_samples.set_xlim(27, 83)
    ax_samples.set_ylim(-5, 200)
    ax_samples.grid(which="major", linestyle="-", linewidth=0.3, alpha=0.5)
    ax_samples.tick_params(labelsize=10)
    
    # 添加样品名称标签（左侧）
    for i, key in enumerate(sample_order):
        y_pos = i * offset + 50
        ax_samples.annotate(
            labels[key],
            xy=(27.5, y_pos),
            fontsize=10,
            fontweight="bold",
            color=colors[key],
            va="center",
            ha="left"
        )
    
    # 添加标题
    ax_samples.set_title("Copper Sulfide Ore XRD Comparison\n铜硫矿选矿过程XRD对比分析", 
                        fontsize=14, fontweight="bold", pad=15)
    
    # ========== 下部：标准参考谱图 ==========
    angle_ref = np.linspace(27, 83, 5000)
    
    # 绘制目的组分的标准谱图
    y_offset_ref = 0
    ref_colors = []
    ref_labels = []
    
    for key, mineral in TARGET_MINERALS.items():
        pattern = generate_reference_pattern(
            angle_ref, 
            mineral["peaks"], 
            mineral["relative_intensities"],
            peak_width=0.12
        )
        pattern_norm = pattern / np.max(pattern) * 80 if np.max(pattern) > 0 else pattern
        
        ax_refs.fill_between(angle_ref, y_offset_ref, pattern_norm + y_offset_ref,
                            alpha=0.6, color=mineral["color"], 
                            label=f"{mineral['name_cn']} ({mineral['formula_mathtext']})")
        ax_refs.plot(angle_ref, pattern_norm + y_offset_ref, 
                    color=mineral["color"], linewidth=0.8)
        
        # 标注矿物名称
        ax_refs.annotate(
            f"{mineral['formula_mathtext']}\n{mineral['name_cn']}",
            xy=(80, y_offset_ref + 40),
            fontsize=8,
            ha="right",
            va="center",
            color=mineral["color"],
            fontweight="bold"
        )
        
        y_offset_ref += 100
    
    ax_refs.set_xlabel("2θ (°)", fontsize=12, fontweight="bold")
    ax_refs.set_ylabel("Reference\nPatterns", fontsize=10)
    ax_refs.set_xlim(27, 83)
    ax_refs.set_ylim(-5, y_offset_ref + 20)
    ax_refs.grid(which="major", linestyle="-", linewidth=0.3, alpha=0.5)
    ax_refs.tick_params(labelsize=10)
    
    # 添加分隔线和说明
    ax_refs.axhline(y=0, color='black', linewidth=1.5)
    ax_refs.text(27.5, y_offset_ref + 10, 
                "Standard Reference Patterns (PDF Cards) / 标准参考谱图",
                fontsize=9, fontweight="bold", va="top")
    
    plt.tight_layout()
    
    # 保存
    fig.savefig(output_path, dpi=300, bbox_inches="tight", 
               facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  已保存: {output_path}")
    
    return fig


def plot_enhanced_comparison(datasets, minerals_list, output_path):
    """
    增强版对比图 - 突出目的组分变化
    使用阴影区域标注目的组分峰位
    """
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    
    # 颜色方案
    colors = {
        "raw": "#3498DB",      # 蓝色
        "conc": "#E74C3C",     # 红色（精矿-重点）
        "tail": "#27AE60",     # 绿色
    }
    
    labels = {
        "raw": "Raw Ore (原矿)",
        "conc": "Concentrate (精矿)",
        "tail": "Tailings (尾矿)"
    }
    
    offset = 70
    
    # 绘制样品谱图
    sample_order = ["raw", "conc", "tail"]
    
    for i, key in enumerate(sample_order):
        angle, intensity = datasets[key]
        minerals = minerals_list[key]
        
        intensity_norm = intensity / np.max(intensity) * 100
        y_shift = i * offset
        
        # 绘制谱线
        ax.plot(angle, intensity_norm + y_shift, 
               color=colors[key], linewidth=1.0, 
               label=labels[key], alpha=0.95)
        
        # 填充曲线下方
        ax.fill_between(angle, y_shift, intensity_norm + y_shift,
                        alpha=0.15, color=colors[key])
        
        # 在左侧添加样品标签
        ax.annotate(
            labels[key],
            xy=(27.3, y_shift + 50),
            fontsize=11,
            fontweight="bold",
            color=colors[key],
            va="center"
        )
    
    # 标注目的组分峰位（在顶部）
    # 收集所有目的组分的主要峰位
    target_peak_positions = []
    for mineral in minerals_list["conc"][:4]:  # 以精矿识别的矿物为准
        for peak in mineral["matched_peaks"][:2]:  # 每个矿物取前两个峰
            target_peak_positions.append((peak, mineral["formula_mathtext"], mineral["color"]))
    
    # 在顶部添加峰位标注
    for peak_pos, formula, color in target_peak_positions:
        # 绘制垂直虚线贯穿所有谱图
        ax.axvline(x=peak_pos, color=color, linestyle="--", 
                  linewidth=0.8, alpha=0.5)
        
        # 在顶部标注化学式
        ax.annotate(
            formula,
            xy=(peak_pos, 205),
            fontsize=9,
            ha="center",
            va="bottom",
            color=color,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", 
                     edgecolor=color, linewidth=1, alpha=0.9)
        )
    
    # 设置轴
    ax.set_xlabel("2θ (°)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Intensity (a.u.)", fontsize=14, fontweight="bold")
    ax.set_xlim(27, 83)
    ax.set_ylim(-10, 220)
    
    # 添加网格
    ax.grid(which="major", linestyle="-", linewidth=0.4, alpha=0.6)
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    
    # 标题
    ax.set_title("Copper Sulfide Ore XRD - Flotation Process Analysis\n" +
                "铜硫矿选矿过程XRD分析 - 目的组分富集效果对比",
                fontsize=16, fontweight="bold", pad=20)
    
    # 添加说明框
    textstr = "目的组分 (Target Minerals):\n" + \
              "• CuFeS₂ (黄铜矿 Chalcopyrite)\n" + \
              "• Cu₂S (辉铜矿 Chalcocite)\n" + \
              "• CuS (铜蓝 Covellite)\n" + \
              "• Cu₅FeS₄ (斑铜矿 Bornite)"
    
    props = dict(boxstyle='round,pad=0.5', facecolor='lightyellow', 
                edgecolor='orange', alpha=0.9)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props, fontweight="normal")
    
    # 添加变化趋势说明
    trend_text = "变化趋势:\n" + \
                 "原矿 → 精矿: 目的组分峰增强\n" + \
                 "精矿 → 尾矿: 目的组分峰减弱"
    props2 = dict(boxstyle='round,pad=0.5', facecolor='lightcyan',
                 edgecolor='blue', alpha=0.9)
    ax.text(0.02, 0.75, trend_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=props2)
    
    plt.tight_layout()
    
    fig.savefig(output_path, dpi=300, bbox_inches="tight", 
               facecolor="white", edgecolor="none")
    plt.close(fig)
    print(f"  已保存: {output_path}")
    
    return fig


def print_analysis_summary(minerals_list):
    """打印分析总结"""
    print("\n" + "=" * 70)
    print("选矿过程目的组分变化分析")
    print("=" * 70)
    
    print("\n【目的组分定义】铜硫化物是选矿的目标矿物：")
    for key, m in TARGET_MINERALS.items():
        # 使用普通文本格式
        formula_plain = m['formula'].replace('₂', '2').replace('₄', '4').replace('₅', '5')
        print(f"  - {m['name_cn']} ({formula_plain}) - 主要元素: {', '.join(m['elements'])}")
    
    print("\n" + "-" * 70)
    print("各样品中目的组分识别结果：")
    print("-" * 70)
    
    sample_names = {
        "raw": "原矿 (Raw Ore)",
        "conc": "精矿 (Concentrate)", 
        "tail": "尾矿 (Tailings)"
    }
    
    for key, minerals in minerals_list.items():
        print(f"\n{sample_names[key]}:")
        if not minerals:
            print("  未检测到明显目的组分")
            continue
        for m in minerals:
            peak_count = len(m["matched_peaks"])
            avg_intensity = np.mean(m["matched_heights"]) * 100
            formula_plain = m['formula'].replace('₂', '2').replace('₄', '4').replace('₅', '5')
            print(f"  [+] {m['name_cn']} ({formula_plain})")
            print(f"      匹配峰数: {peak_count}, 平均相对强度: {avg_intensity:.1f}%")


def main():
    # 文件路径
    files = {
        "raw": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw",
        "conc": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw",
        "tail": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw"
    }
    
    output_dir = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("=" * 70)
    print("铜硫矿 XRD 专业对比分析")
    print("=" * 70)
    
    # 解析数据
    datasets = {}
    minerals_list = {}
    
    for key, fpath in files.items():
        print(f"\n解析 {key}...")
        try:
            angle, intensity = parse_bruker_raw_v3(fpath)
            print(f"  成功: {len(intensity)} 个数据点, 2θ: {angle[0]:.1f}° - {angle[-1]:.1f}°")
            datasets[key] = (angle, intensity)
            
            # 识别目的组分
            minerals = identify_target_minerals(angle, intensity)
            minerals_list[key] = minerals
            print(f"  识别到 {len(minerals)} 种目的组分")
        except Exception as e:
            print(f"  错误: {e}")
            return
    
    # 打印分析总结
    print_analysis_summary(minerals_list)
    
    # 生成专业对比图
    print("\n" + "=" * 70)
    print("生成专业对比图谱")
    print("=" * 70)
    
    # 图1: 带标准参考谱图的对比图
    print("\n[1/2] 生成专业对比图（含标准参考谱图）...")
    plot_professional_comparison(
        datasets, minerals_list,
        output_path=str(output_dir / "05_XRD_comparison_professional.png")
    )
    
    # 图2: 增强版对比图
    print("\n[2/2] 生成增强版对比图（突出目的组分变化）...")
    plot_enhanced_comparison(
        datasets, minerals_list,
        output_path=str(output_dir / "06_XRD_comparison_enhanced.png")
    )
    
    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)
    print(f"\n生成的专业对比图保存在: {output_dir}")
    print("  1. 05_XRD_comparison_professional.png - 专业对比图（含标准参考谱图）")
    print("  2. 06_XRD_comparison_enhanced.png - 增强版对比图（突出目的组分变化）")


if __name__ == "__main__":
    main()
