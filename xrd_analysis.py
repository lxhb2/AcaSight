"""
铜硫矿 XRD 数据分析脚本
分析原矿、精矿、尾矿的 Bruker RAW 格式数据
"""
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from pathlib import Path

# 期刊样式配置
JOURNAL_STYLES = {
    "nature": {"figsize": (3.5, 2.625), "fontsize": 7, "linewidth": 0.75, "tick_width": 0.5, "labelpad": 2, "tick_dir": "out", "dpi": 600, "font": "Arial", "colors": ["#0C5DA5", "#FF6B35", "#00B945", "#845B97", "#FFBC00"]},
    "science": {"figsize": (3.5, 2.625), "fontsize": 7, "linewidth": 0.75, "tick_width": 0.5, "labelpad": 2, "tick_dir": "out", "dpi": 600, "font": "Arial"},
    "cell": {"figsize": (4.5, 3.375), "fontsize": 8, "linewidth": 1.0, "tick_width": 0.6, "labelpad": 3, "tick_dir": "out", "dpi": 600, "font": "Arial"},
}

# 矿物数据库
MINERAL_DATABASE = {
    "pyrite": {"name": "Pyrite", "formula": "FeS₂", "peaks": [28.51, 33.08, 37.10, 40.80, 47.42, 56.33], "category": "sulfide"},
    "chalcopyrite": {"name": "Chalcopyrite", "formula": "CuFeS₂", "peaks": [29.42, 34.84, 36.63, 47.43, 56.98], "category": "sulfide"},
    "covellite": {"name": "Covellite", "formula": "CuS", "peaks": [28.04, 31.78, 47.87, 56.54], "category": "sulfide"},
    "chalcocite": {"name": "Chalcocite", "formula": "Cu₂S", "peaks": [26.55, 30.08, 43.92, 47.87], "category": "sulfide"},
    "bornite": {"name": "Bornite", "formula": "Cu₅FeS₄", "peaks": [28.96, 31.26, 37.74, 46.14], "category": "sulfide"},
    "quartz": {"name": "Quartz", "formula": "SiO₂", "peaks": [20.85, 26.65, 36.54, 39.46, 42.45, 45.80, 50.14], "category": "oxide"},
    "calcite": {"name": "Calcite", "formula": "CaCO₃", "peaks": [23.04, 29.42, 35.98, 39.42, 43.18, 47.48], "category": "carbonate"},
    "dolomite": {"name": "Dolomite", "formula": "CaMg(CO₃)₂", "peaks": [24.02, 30.92, 37.32, 41.18, 43.88, 51.08], "category": "carbonate"},
}

def parse_bruker_raw(file_path):
    """解析 Bruker RAW 格式 XRD 数据"""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    with open(file_path, "rb") as f:
        data = f.read()
    
    # 检测 RAW 格式版本
    if data[:4] == b"RAW1":
        # RAW V1 格式
        num_points = struct.unpack("<I", data[44:48])[0]
        start_angle = struct.unpack("<f", data[48:52])[0]
        end_angle = struct.unpack("<f", data[52:56])[0]
        # 搜索数据起始位置
        for i in range(256, min(len(data), 1024)):
            if data[i:i+4] == b"\x00\x00\x00\x00":
                data_start = i + 4
                break
        else:
            data_start = 512
        
    elif data[:4] == b"RAW2":
        # RAW V2 格式
        num_points = struct.unpack("<I", data[64:68])[0]
        start_angle = struct.unpack("<f", data[68:72])[0]
        end_angle = struct.unpack("<f", data[72:76])[0]
        data_start = 512
        
    elif data[:4] == b"RAW3":
        # RAW V3 格式
        num_points = struct.unpack("<I", data[80:84])[0]
        start_angle = struct.unpack("<d", data[88:96])[0]
        end_angle = struct.unpack("<d", data[96:104])[0]
        data_start = 1024
    else:
        # 尝试通用解析
        num_points = len(data) // 4
        start_angle = 5.0
        end_angle = 90.0
        data_start = 0
    
    # 读取强度数据
    intensities = []
    for i in range(num_points):
        pos = data_start + i * 4
        if pos + 4 <= len(data):
            intensity = struct.unpack("<f", data[pos:pos+4])[0]
            if 0 <= intensity < 1e8 and not np.isnan(intensity):
                intensities.append(intensity)
    
    # 生成角度数组
    angles = np.linspace(start_angle, end_angle, len(intensities))
    
    print(f"  解析成功: {len(intensities)} 个数据点")
    print(f"  2θ 范围: {float(angles[0]):.2f}° - {float(angles[-1]):.2f}°")
    
    return angles, np.array(intensities)


def detect_peaks(angle, intensity, threshold=0.05, min_distance=15):
    """检测衍射峰"""
    from scipy.signal import find_peaks
    intensity_norm = intensity / np.max(intensity)
    peaks, properties = find_peaks(intensity_norm, height=threshold, distance=min_distance, prominence=0.02)
    return peaks


def identify_minerals(angle, intensity, threshold=0.05, tolerance=0.5):
    """识别矿物相"""
    peak_indices = detect_peaks(angle, intensity, threshold=threshold)
    sample_peaks = angle[peak_indices]
    
    identified = []
    for key, mineral in MINERAL_DATABASE.items():
        ref_peaks = np.array(mineral["peaks"])
        matches = 0
        matched_peaks = []
        for ref_peak in ref_peaks:
            for sample_peak in sample_peaks:
                if abs(sample_peak - ref_peak) <= tolerance:
                    matches += 1
                    matched_peaks.append(sample_peak)
                    break
        
        if matches >= 2:
            identified.append({
                "key": key,
                "name": mineral["name"],
                "formula": mineral["formula"],
                "category": mineral["category"],
                "matched_peaks": matched_peaks,
                "match_score": matches / len(ref_peaks),
                "reference_peaks": ref_peaks.tolist(),
            })
    
    identified.sort(key=lambda x: x["match_score"], reverse=True)
    return identified


def apply_style(ax, journal="nature"):
    """应用期刊样式"""
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["nature"])
    plt.rcParams["font.family"] = st["font"]
    plt.rcParams["font.size"] = st["fontsize"]
    
    for spine in ax.spines.values():
        spine.set_linewidth(st["tick_width"])
        spine.set_color("black")
    
    ax.tick_params(direction=st["tick_dir"], axis="both", which="major",
                   length=4, width=st["tick_width"], labelsize=st["fontsize"])
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.yaxis.set_minor_locator(AutoMinorLocator(2))
    ax.grid(which="major", linestyle="-", linewidth=0.3, color="#AAAAAA", alpha=0.5)
    ax.grid(which="minor", linestyle=":", linewidth=0.2, color="#BBBBBB", alpha=0.3)
    ax.set_axisbelow(True)


def plot_xrd_single(angle, intensity, sample_name, minerals=None, journal="nature", 
                    output=None, color=None, show_peaks=True):
    """绘制单样品 XRD 图谱"""
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["nature"])
    
    fig, ax = plt.subplots(figsize=st["figsize"], dpi=st["dpi"])
    apply_style(ax, journal)
    
    # 归一化
    intensity_norm = intensity / np.max(intensity) * 100
    plot_color = color if color else st["colors"][0]
    
    ax.plot(angle, intensity_norm, color=plot_color, linewidth=st["linewidth"])
    ax.set_xlabel("2θ (°)", fontsize=st["fontsize"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=st["fontsize"])
    
    if sample_name:
        ax.set_title(sample_name, fontsize=st["fontsize"]+1, pad=10)
    
    ax.set_xlim(angle.min(), angle.max())
    ax.set_ylim(0, 115)
    
    # 标注矿物峰
    if minerals and show_peaks:
        ylim = ax.get_ylim()
        for i, mineral in enumerate(minerals[:5]):  # 最多标注5个矿物
            for peak in mineral["matched_peaks"][:2]:  # 每个矿物最多2个峰
                ax.axvline(x=peak, color="#888888", linestyle="--", linewidth=0.5, alpha=0.6)
                ax.annotate(
                    f"{mineral['name']}\n{mineral['formula']}",
                    xy=(peak, ylim[1] - 10 * (i + 1)),
                    fontsize=5,
                    ha="center",
                    va="top",
                    rotation=90,
                    bbox=dict(boxstyle="round,pad=0.15", facecolor="white", edgecolor="none", alpha=0.85)
                )
    
    plt.tight_layout()
    
    if output:
        fig.savefig(output, dpi=st["dpi"], bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  已保存: {output}")
    
    return fig, ax


def plot_xrd_comparison(datasets, labels, journal="nature", output=None, offset=30):
    """绘制多样品对比图"""
    st = JOURNAL_STYLES.get(journal.lower(), JOURNAL_STYLES["nature"])
    
    fig, ax = plt.subplots(figsize=(6, 4), dpi=st["dpi"])
    apply_style(ax, journal)
    
    for i, (angle, intensity) in enumerate(datasets):
        intensity_norm = intensity / np.max(intensity) * 100
        y_shift = i * offset
        color = st["colors"][i % len(st["colors"])]
        ax.plot(angle, intensity_norm + y_shift, color=color, linewidth=st["linewidth"], label=labels[i])
    
    ax.set_xlabel("2θ (°)", fontsize=st["fontsize"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=st["fontsize"])
    ax.legend(fontsize=st["fontsize"]-1, frameon=False, loc="upper right")
    
    ax.set_xlim(min(d[0].min() for d in datasets), max(d[0].max() for d in datasets))
    ax.set_ylim(-5, len(datasets) * offset + 115)
    
    plt.tight_layout()
    
    if output:
        fig.savefig(output, dpi=st["dpi"], bbox_inches="tight", facecolor="white")
        plt.close(fig)
        print(f"  已保存: {output}")
    
    return fig, ax


def main():
    # 文件路径
    raw_file = r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\tongliukuang yuankuang.raw"
    concentrate_file = r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing jingkuang tongliukuang.raw"
    tailings_file = r"F:\xwechat_files\wxid_02k0z8c1gb8i22_115d\msg\file\2026-04\2cu2jing weikuang tongliukuang.raw"
    
    output_dir = Path(r"C:\Users\Administrator\.qclaw\workspace")
    
    print("=" * 60)
    print("铜硫矿 XRD 数据分析")
    print("=" * 60)
    
    # 解析原矿数据
    print("\n[1/3] 解析原矿数据...")
    angle_raw, intensity_raw = parse_bruker_raw(raw_file)
    
    # 解析精矿数据
    print("\n[2/3] 解析精矿数据...")
    angle_conc, intensity_conc = parse_bruker_raw(concentrate_file)
    
    # 解析尾矿数据
    print("\n[3/3] 解析尾矿数据...")
    angle_tail, intensity_tail = parse_bruker_raw(tailings_file)
    
    # 矿物相识别
    print("\n" + "=" * 60)
    print("矿物相识别结果")
    print("=" * 60)
    
    print("\n【原矿】识别出的矿物:")
    minerals_raw = identify_minerals(angle_raw, intensity_raw)
    for m in minerals_raw[:6]:
        print(f"  ✓ {m['name']} ({m['formula']}) - 匹配峰: {[f'{p:.2f}°' for p in m['matched_peaks']]}")
    if not minerals_raw:
        print("  未识别到已知矿物相")
    
    print("\n【精矿】识别出的矿物:")
    minerals_conc = identify_minerals(angle_conc, intensity_conc)
    for m in minerals_conc[:6]:
        print(f"  ✓ {m['name']} ({m['formula']}) - 匹配峰: {[f'{p:.2f}°' for p in m['matched_peaks']]}")
    if not minerals_conc:
        print("  未识别到已知矿物相")
    
    print("\n【尾矿】识别出的矿物:")
    minerals_tail = identify_minerals(angle_tail, intensity_tail)
    for m in minerals_tail[:6]:
        print(f"  ✓ {m['name']} ({m['formula']}) - 匹配峰: {[f'{p:.2f}°' for p in m['matched_peaks']]}")
    if not minerals_tail:
        print("  未识别到已知矿物相")
    
    # 生成图谱
    print("\n" + "=" * 60)
    print("生成 XRD 图谱")
    print("=" * 60)
    
    # 三样品对比图
    print("\n[1/4] 生成三样品对比图...")
    datasets = [(angle_raw, intensity_raw), (angle_conc, intensity_conc), (angle_tail, intensity_tail)]
    labels = ["Raw Ore (原矿)", "Concentrate (精矿)", "Tailings (尾矿)"]
    plot_xrd_comparison(datasets, labels, journal="nature", 
                        output=str(output_dir / "copper_sulfide_comparison.png"), offset=30)
    
    # 单样品图谱
    print("\n[2/4] 生成原矿图谱...")
    plot_xrd_single(angle_raw, intensity_raw, "Copper Sulfide Raw Ore (原矿)", 
                   minerals=minerals_raw, journal="nature",
                   output=str(output_dir / "raw_ore_xrd.png"), color=JOURNAL_STYLES["nature"]["colors"][0])
    
    print("\n[3/4] 生成精矿图谱...")
    plot_xrd_single(angle_conc, intensity_conc, "Copper Sulfide Concentrate (精矿)", 
                   minerals=minerals_conc, journal="nature",
                   output=str(output_dir / "concentrate_xrd.png"), color=JOURNAL_STYLES["nature"]["colors"][1])
    
    print("\n[4/4] 生成尾矿图谱...")
    plot_xrd_single(angle_tail, intensity_tail, "Copper Sulfide Tailings (尾矿)", 
                   minerals=minerals_tail, journal="nature",
                   output=str(output_dir / "tailings_xrd.png"), color=JOURNAL_STYLES["nature"]["colors"][2])
    
    print("\n" + "=" * 60)
    print("分析完成！")
    print("=" * 60)
    print(f"\n生成的文件保存在: {output_dir}")
    print("  1. copper_sulfide_comparison.png - 三样品对比图")
    print("  2. raw_ore_xrd.png - 原矿单样品图谱")
    print("  3. concentrate_xrd.png - 精矿单样品图谱")
    print("  4. tailings_xrd.png - 尾矿单样品图谱")


if __name__ == "__main__":
    main()
