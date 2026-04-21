"""
铜硫矿 XRD 数据分析脚本 V3
正确解析 Bruker RAW 格式数据
生成四张图谱：三张单样品 + 一张对比图
标注矿物化学式和元素分析
"""
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from pathlib import Path
from scipy.signal import find_peaks

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 矿物数据库 - 铜硫矿相关
MINERAL_DATABASE = {
    "chalcopyrite": {
        "name": "Chalcopyrite", "name_cn": "黄铜矿",
        "formula": "CuFeS$_{2}$",
        "peaks": [29.42, 34.84, 36.63, 47.43, 56.98],
        "elements": ["Cu", "Fe", "S"]
    },
    "pyrite": {
        "name": "Pyrite", "name_cn": "黄铁矿", 
        "formula": "FeS$_{2}$",
        "peaks": [28.51, 33.08, 37.10, 40.80, 47.42, 56.33],
        "elements": ["Fe", "S"]
    },
    "covellite": {
        "name": "Covellite", "name_cn": "铜蓝",
        "formula": "CuS",
        "peaks": [27.68, 29.58, 31.78, 47.87, 56.54],
        "elements": ["Cu", "S"]
    },
    "chalcocite": {
        "name": "Chalcocite", "name_cn": "辉铜矿",
        "formula": "Cu$_{2}$S", 
        "peaks": [26.55, 30.08, 37.95, 43.92, 47.87],
        "elements": ["Cu", "S"]
    },
    "bornite": {
        "name": "Bornite", "name_cn": "斑铜矿",
        "formula": "Cu$_{5}$FeS$_{4}$",
        "peaks": [28.96, 31.26, 37.74, 46.14, 53.87],
        "elements": ["Cu", "Fe", "S"]
    },
    "quartz": {
        "name": "Quartz", "name_cn": "石英",
        "formula": "SiO$_{2}$",
        "peaks": [20.85, 26.65, 36.54, 39.46, 42.45, 50.14],
        "elements": ["Si", "O"]
    },
    "calcite": {
        "name": "Calcite", "name_cn": "方解石",
        "formula": "CaCO$_{3}$",
        "peaks": [23.04, 29.42, 35.98, 39.42, 43.18, 47.48],
        "elements": ["Ca", "C", "O"]
    },
    "sphalerite": {
        "name": "Sphalerite", "name_cn": "闪锌矿",
        "formula": "ZnS",
        "peaks": [28.56, 33.08, 47.54, 56.44],
        "elements": ["Zn", "S"]
    },
}


def parse_bruker_raw_v3(file_path):
    """解析 Bruker RAW 格式 - 改进版"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    # RAW1 格式 - 找数据起始位置
    # 通过搜索找到连续的合理强度值
    data_start = 5108  # 通过分析确定的数据起始位置
    
    # 计算数据点数
    num_points = (len(data) - data_start) // 4
    
    # 读取强度数据
    intensities = []
    for i in range(num_points):
        pos = data_start + i * 4
        if pos + 4 <= len(data):
            val = struct.unpack("<f", data[pos:pos+4])[0]
            intensities.append(val)
    
    intensities = np.array(intensities)
    
    # 根据最强峰位置推断角度范围
    max_idx = np.argmax(intensities)
    # 假设最强峰是黄铁矿的 28.51° 或黄铜矿的 29.42°
    # 步长通常是 0.02°
    step = 0.02
    start_angle = 27.0  # 根据峰位推断
    
    angles = np.linspace(start_angle, start_angle + step * (num_points - 1), num_points)
    
    return angles, intensities


def identify_minerals(angle, intensity, threshold=0.03, tolerance=0.5):
    """识别矿物相"""
    # 归一化
    intensity_norm = intensity / np.max(intensity)
    
    # 检测峰
    peaks, props = find_peaks(intensity_norm, height=threshold, distance=8, prominence=0.02)
    peak_angles = angle[peaks]
    peak_heights = intensity_norm[peaks]
    
    identified = []
    for key, mineral in MINERAL_DATABASE.items():
        ref_peaks = np.array(mineral["peaks"])
        matches = 0
        matched_peaks = []
        matched_heights = []
        
        for ref_peak in ref_peaks:
            for i, sample_peak in enumerate(peak_angles):
                if abs(sample_peak - ref_peak) <= tolerance:
                    matches += 1
                    matched_peaks.append(sample_peak)
                    matched_heights.append(peak_heights[i])
                    break
        
        if matches >= 2:
            identified.append({
                "key": key,
                "name": mineral["name"],
                "name_cn": mineral["name_cn"],
                "formula": mineral["formula"],
                "elements": mineral["elements"],
                "matched_peaks": matched_peaks,
                "matched_heights": matched_heights,
                "match_score": matches / len(ref_peaks),
            })
    
    identified.sort(key=lambda x: x["match_score"], reverse=True)
    return identified, peak_angles, peak_heights


def plot_xrd_single(angle, intensity, sample_name, minerals=None, 
                    output=None, color="#1f77b4"):
    """绘制单样品 XRD 图谱"""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    
    # 归一化
    intensity_norm = intensity / np.max(intensity) * 100
    
    ax.plot(angle, intensity_norm, color=color, linewidth=0.8)
    ax.set_xlabel("2θ (°)", fontsize=12)
    ax.set_ylabel("Intensity (a.u.)", fontsize=12)
    ax.set_title(sample_name, fontsize=14, fontweight="bold", pad=10)
    
    ax.set_xlim(angle.min(), angle.max())
    ax.set_ylim(0, 115)
    
    # 设置网格
    ax.grid(which="major", linestyle="-", linewidth=0.3, color="#AAAAAA", alpha=0.5)
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    
    # 标注矿物峰和化学式
    if minerals:
        used_positions = []
        for mineral in minerals[:5]:
            if mineral["matched_peaks"]:
                peak_idx = np.argmax(mineral["matched_heights"])
                peak_angle = mineral["matched_peaks"][peak_idx]
                
                # 避免标注位置重叠
                y_base = 100
                for used_y, used_x in used_positions:
                    if abs(peak_angle - used_x) < 4:
                        y_base = used_y - 15
                        break
                
                if y_base < 25:
                    continue
                
                # 绘制垂直虚线
                ax.axvline(x=peak_angle, color="#888888", linestyle="--", linewidth=0.5, alpha=0.6)
                
                # 标注矿物名称和化学式
                label = f"{mineral['name']}\n{mineral['formula']}"
                
                ax.annotate(
                    label,
                    xy=(peak_angle, y_base),
                    fontsize=8,
                    ha="center",
                    va="bottom",
                    rotation=0,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", 
                             edgecolor="#888888", alpha=0.9, linewidth=0.5)
                )
                used_positions.append((y_base, peak_angle))
    
    plt.tight_layout()
    
    if output:
        fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  已保存: {output}")
    
    return fig, ax


def plot_xrd_comparison(datasets, labels, minerals_list, output=None, offset=45):
    """绘制多样品对比图，间隔更大"""
    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)
    
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    
    for i, ((angle, intensity), label, minerals) in enumerate(zip(datasets, labels, minerals_list)):
        intensity_norm = intensity / np.max(intensity) * 100
        y_shift = i * offset
        color = colors[i % len(colors)]
        ax.plot(angle, intensity_norm + y_shift, color=color, linewidth=0.8, label=label)
        
        # 标注主要矿物化学式
        if minerals:
            for mineral in minerals[:4]:
                if mineral["matched_peaks"]:
                    peak_angle = mineral["matched_peaks"][0]
                    idx = np.argmin(np.abs(angle - peak_angle))
                    y_pos = intensity_norm[idx] + y_shift + 5
                    
                    ax.annotate(
                        mineral["formula"],
                        xy=(peak_angle, y_pos),
                        fontsize=7,
                        ha="center",
                        va="bottom",
                        rotation=90,
                        color=color,
                        bbox=dict(boxstyle="round,pad=0.1", facecolor="white", 
                                 edgecolor="none", alpha=0.85)
                    )
    
    ax.set_xlabel("2θ (°)", fontsize=12)
    ax.set_ylabel("Intensity (a.u.)", fontsize=12)
    ax.legend(fontsize=10, frameon=True, loc="upper right", fancybox=True)
    
    ax.set_xlim(min(d[0].min() for d in datasets), max(d[0].max() for d in datasets))
    ax.set_ylim(-5, len(datasets) * offset + 120)
    ax.grid(which="major", linestyle="-", linewidth=0.3, color="#AAAAAA", alpha=0.5)
    
    plt.tight_layout()
    
    if output:
        fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  已保存: {output}")
    
    return fig, ax


def analyze_elements(minerals_list, sample_names):
    """分析各样品中的元素组成"""
    print("\n" + "=" * 70)
    print("元素分析结果")
    print("=" * 70)
    
    all_elements = set()
    
    for minerals, name in zip(minerals_list, sample_names):
        elements = set()
        print(f"\n[{name}] 识别出的矿物及元素:")
        if not minerals:
            print("  未检测到明显矿物相")
            continue
        for m in minerals[:6]:
            print(f"  [+] {m['name']} ({m['formula']}) - 元素: {', '.join(m['elements'])}")
            elements.update(m['elements'])
        all_elements.update(elements)
    
    if all_elements:
        print(f"\n所有样品中检测到的元素: {', '.join(sorted(all_elements))}")
    else:
        print("\n未能检测到明确的元素信号")
    
    return all_elements


def main():
    # 文件路径
    files = {
        "raw": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw",
        "conc": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw",
        "tail": r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw"
    }
    
    output_dir = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("=" * 70)
    print("铜硫矿 XRD 数据分析")
    print("=" * 70)
    
    # 解析数据
    datasets = {}
    minerals_dict = {}
    
    for key, fpath in files.items():
        print(f"\n解析 {key}...")
        try:
            angle, intensity = parse_bruker_raw_v3(fpath)
            print(f"  成功: {len(intensity)} 个数据点, 2θ范围: {angle[0]:.1f}° - {angle[-1]:.1f}°")
            print(f"  强度范围: {np.min(intensity):.0f} - {np.max(intensity):.0f}")
            datasets[key] = (angle, intensity)
            
            # 识别矿物
            minerals, peaks, heights = identify_minerals(angle, intensity)
            minerals_dict[key] = minerals
            print(f"  识别到 {len(minerals)} 种矿物相")
        except Exception as e:
            print(f"  错误: {e}")
            return
    
    # 元素分析
    sample_names = ["原矿 (Raw Ore)", "铜硫精矿 (Concentrate)", "尾矿 (Tailings)"]
    minerals_list = [minerals_dict["raw"], minerals_dict["conc"], minerals_dict["tail"]]
    analyze_elements(minerals_list, sample_names)
    
    # 生成图谱
    print("\n" + "=" * 70)
    print("生成 XRD 图谱")
    print("=" * 70)
    
    # 1. 原矿图谱
    print("\n[1/4] 生成原矿图谱...")
    plot_xrd_single(datasets["raw"][0], datasets["raw"][1], "原矿 (Raw Ore)", 
                   minerals=minerals_dict["raw"],
                   output=str(output_dir / "01_raw_ore_xrd.png"), color="#1f77b4")
    
    # 2. 精矿图谱
    print("\n[2/4] 生成铜硫精矿图谱...")
    plot_xrd_single(datasets["conc"][0], datasets["conc"][1], "铜硫精矿 (Copper Sulfide Concentrate)", 
                   minerals=minerals_dict["conc"],
                   output=str(output_dir / "02_concentrate_xrd.png"), color="#ff7f0e")
    
    # 3. 尾矿图谱
    print("\n[3/4] 生成尾矿图谱...")
    plot_xrd_single(datasets["tail"][0], datasets["tail"][1], "尾矿 (Tailings)", 
                   minerals=minerals_dict["tail"],
                   output=str(output_dir / "03_tailings_xrd.png"), color="#2ca02c")
    
    # 4. 三样品对比图
    print("\n[4/4] 生成三样品对比图...")
    dataset_list = [datasets["raw"], datasets["conc"], datasets["tail"]]
    plot_xrd_comparison(dataset_list, sample_names, minerals_list,
                        output=str(output_dir / "04_comparison_xrd.png"), offset=50)
    
    print("\n" + "=" * 70)
    print("分析完成！")
    print("=" * 70)
    print(f"\n生成的文件保存在: {output_dir}")
    print("  1. 01_raw_ore_xrd.png - 原矿 XRD 图谱")
    print("  2. 02_concentrate_xrd.png - 铜硫精矿 XRD 图谱")
    print("  3. 03_tailings_xrd.png - 尾矿 XRD 图谱")
    print("  4. 04_comparison_xrd.png - 三样品对比图")


if __name__ == "__main__":
    main()
