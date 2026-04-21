# XRD_Analysis 使用说明

## 文件结构

```
xrd_analysis/
  XRD_Analysis_combined.py   # 核心分析库（完整函数集）
  plot_publication.py        # 出版级图表绘制
  run_analysis.py            # 快速运行脚本
  results/
    Y-2_XRD_main.eps        # EPS矢量图（主图）
    Y-2_XRD_publication.png  # 高清PNG（出版级）
    Y-2_phase_quant.png      # 定量饼图
    Y-2_peak_table.png       # 峰位表
    Y-2_report.json          # 完整JSON报告
```

## 使用方法

### 1. 快速运行（命令行）
```bash
python run_analysis.py
# 或指定参数：
python XRD_Analysis_combined.py "your_data.txt" -n "Sample-1" -j "Minerals Engineering" -d 600
```

### 2. Python 调用
```python
from XRD_Analysis_combined import analyze_xrd

report = analyze_xrd(
    data_path  = "Y-2.txt",
    output_dir = "./output",
    sample_name = "Y-2",
    journal    = "Minerals Engineering",  # or: "CNS", "Metallurgy", "Chinese Journal"
    dpi        = 600,
    peak_tolerance = 0.30,  # ±°物相匹配容差
)
```

### 3. 批量处理
```python
from XRD_Analysis_combined import batch_analyze

batch_analyze(
    data_dir  = "/path/to/xrd_files/",
    output_dir = "./batch_results",
    pattern   = "*.txt",
    sample_prefix = "Sample",
    journal   = "Minerals Engineering",
)
```

## 支持文件格式

| 格式 | 说明 | 状态 |
|------|------|------|
| `.txt` | 两列 2θ / Intensity | ✅ |
| `.csv` | CSV格式 | ✅ |
| `.raw` | PANalytical二进制 | ✅ |
| `.xrdml` | XML格式 | ⚠️ 需额外库 |

## 物相库（铜钴矿浸出渣）

内置矿物库包含 16 种铜钴矿常见矿物：
- 铁氧化物：赤铁矿、磁铁矿、针铁矿、纤铁矿
- 铜矿物：孔雀石、蓝辉铜矿、赤铜矿
- 脉石：石英、斜绿泥石、白云石、方解石
- 其他：石膏、黄铁矿、水钴矿、红柱石/蓝晶石

## 绘图标准

本系统按以下出版标准绘图：
- **Minerals Engineering**: 8×5.5 inch, 1.2pt线宽, EPS输出
- **CNS/Nature/Science**: 9×6 inch, 1.4pt线宽
- **中文期刊**: 8×5.5 inch, 10.5pt字号
- 所有图统一: Cu Kα辐射标注 (λ=1.5406 Å), 期刊Figure caption

## 注意事项

1. **定量精度**: 当前使用简化Rietveld（峰面积比），适用于半定量
   - 精确Rietveld全谱拟合需安装 Fullprof Suite / GSAS-II
2. **物相库扩展**: 可添加更多矿物卡片，格式见 MINERAL_LIBRARY
3. **Windows编码**: 输出含中文字符时注意控制台编码，建议使用 `--journal` 参数

## 典型实验参数

铜钴矿硫酸浸出渣 XRD 分析推荐参数：
```python
analyze_xrd(
    smooth_window   = 9,       # SG平滑窗口
    smooth_poly     = 3,       # SG多项式阶数
    background_method = 'ALS',  # 或 'rolling'
    peak_height_ratio = 0.025, # 最小峰高比
    peak_prominence  = 0.005,  # 峰突出度
    peak_tolerance   = 0.30,   # ±0.30° 匹配容差
)
```
