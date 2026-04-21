# Sci-XRD 技能完整报告

**生成日期**: 2026-04-10  
**技能路径**: `C:\Users\Administrator\.qclaw\skills\sci-xrd`

---

## 一、项目概述

Sci-XRD 是一个类似 MDI Jade 的通用 XRD（X射线衍射）数据分析工具，面向材料、地质、化学领域。支持任意矿物/材料的数据分析 + 论文配图。

### 核心定位
- **目标用户**: 材料科学、地质学、化学研究人员
- **主要用途**: XRD数据分析、物相鉴定、出版级图谱生成
- **对标软件**: MDI Jade 6.5

---

## 二、文件结构

```
sci-xrd/
├── manifest.json              # 技能清单
├── skill.json                 # 技能配置
├── SKILL.md                   # 技能文档（用户手册）
├── sci_xrd.py                 # 核心分析模块 (1450+ 行)
├── pdf_database.db            # PDF2-2004 SQLite数据库 (26.7MB)
├── pdf_minerals.db            # 矿物专用数据库
├── gui/
│   ├── xrd_gui.py            # PyQt6 GUI主程序 (1200+ 行)
│   ├── start_gui.bat         # Windows启动脚本
│   ├── start_gui.sh          # Linux/Mac启动脚本
│   └── start_gui_debug.bat   # Windows调试启动
├── scripts/
│   ├── pdf2_to_sqlite.py     # PDF2.dat → SQLite转换器
│   ├── cif_xrd_compare.py    # CIF文件对比分析
│   └── download_cod_cif.py   # COD数据库CIF下载
├── cif_files/
│   ├── 黄铁矿.cif            # Pyrite CIF文件
│   └── 黄铜矿.cif            # Chalcopyrite CIF文件
└── test_cif/                 # 测试CIF文件夹
```

---

## 三、核心功能模块

### 3.1 数据解析模块 (sci_xrd.py)

#### 支持的数据格式
| 格式 | 扩展名 | 状态 |
|------|--------|------|
| Bruker RAW | `.raw` | ✅ RAW1.01 & RAW2.00 |
| Rigaku RAS | `.ras` `.rasx` | ✅ SmartLab / D/max |
| PANalytical XRDML | `.xrdml` | ✅ Empyrean XML |
| 文本两列 | `.txt` `.xy` `.csv` `.dat` | ✅ 空格/逗号/制表符 |

#### 数据处理流程
```
原始数据 → 平滑(Savitzky-Golay) → 背景扣除(ALS) → 归一化 → 寻峰 → 物相匹配 → 绘图
```

#### 关键算法
1. **ALS背景扣除**: 非对称最小二乘，参数 λ=1e6, p=0.01
2. **Savitzky-Golay平滑**: 窗口可调 (默认11点，3阶多项式)
3. **寻峰算法**: scipy.signal.find_peaks，支持高度/突出度/间距阈值
4. **FOM物相匹配**: 综合评分 (d-FOM×40% + I-FOM×20% + Δd/d×20% + M-FOM×20%)
5. **Hanawalt检索**: 经典前3强峰匹配
6. **Scherrer晶粒尺寸**: D = Kλ/(βcosθ), K=0.89

### 3.2 内置矿物库 (COMMON_MINERALS)

| 化学式 | 矿物名 | 主要d值 (Å) |
|--------|--------|-------------|
| CuFeS₂ | Chalcopyrite 黄铜矿 | 3.03, 1.86, 1.59 |
| FeS₂ | Pyrite 黄铁矿 | 2.71, 2.42, 2.09 |
| Cu₂S | Chalcocite 辉铜矿 | 3.05, 2.40, 1.98 |
| CuS | Covellite 铜蓝 | 2.81, 1.89, 1.56 |
| Cu₅FeS₄ | Bornite 斑铜矿 | 3.16, 2.74, 1.94 |
| SiO₂ | Quartz 石英 | 3.35, 4.25, 1.82 |
| CaCO₃ | Calcite 方解石 | 3.04, 2.29, 2.10 |
| Fe₂O₃ | Hematite 赤铁矿 | 2.70, 2.52, 1.69 |
| Fe₃O₄ | Magnetite 磁铁矿 | 2.53, 2.97, 2.10 |
| PbS | Galena 方铅矿 | 2.97, 3.44, 2.09 |
| ZnS | Sphalerite 闪锌矿 | 3.12, 1.91, 1.63 |

### 3.3 PDF2数据库

- **来源**: ICDD PDF2-2004 (商业数据库)
- **规模**: 35,750物相，277,426峰位，18,200化学式
- **格式**: SQLite (26.7MB)
- **字段**: PDF编号、名称、化学式、晶系、空间群、晶胞参数、密度、辐射类型、d值、强度、密勒指数

### 3.4 绘图系统

#### 期刊风格预设
| 风格 | 尺寸 | DPI | 用途 |
|------|------|-----|------|
| `nature` | 3.5×2.4 in | 600 | Nature期刊 |
| `science` | 3.5×2.4 in | 600 | Science期刊 |
| `cell` | 4.5×3.0 in | 600 | Cell期刊 |
| `thesis` | 9.0×5.5 in | 150 | 学位论文 |
| `default` | 8.0×5.0 in | 150 | 通用 |

#### 配色方案
- 曲线: `#ACACAE` (浅灰)
- 主峰线: `#2A292C` (深灰)
- 次峰线: `#B0B0B2` (浅灰)
- 物相色盘: 10色循环

### 3.5 GUI界面功能

#### 左侧面板
1. **数据加载**
   - 加载单个XRD文件
   - 加载多个文件对比 ✅ 新增
   - 元素搜索 (S/M功能) ✅ 新增

2. **数据预处理**
   - Savitzky-Golay平滑 (窗口5-51)
   - ALS背景扣除 (λ参数1e3-1e8)

3. **寻峰设置**
   - 最小峰高 (0.1-50%)
   - 突出度 (0.1-20%)
   - 最小间距 (1-50点)

4. **物相鉴定**
   - 启用矿物库匹配
   - d-spacing容差 (0.01-2.0 Å)

5. **图谱设置**
   - 2θ范围 (0-90°)
   - 标注类型 (d/formula/none)
   - 对比间距 (0-100%) ✅ 新增

#### 中间面板
- Matplotlib交互式图谱
- 支持缩放/平移
- 实时更新

#### 右侧面板
- 峰位表格 (序号/2θ/d值/强度/Scherrer尺寸)
- 物相表格 (矿物名/化学式/匹配峰数/FOM分数)
- 日志输出

---

## 四、API接口

### 4.1 一键分析
```python
from sci_xrd import analyze_xrd

result = analyze_xrd(
    filepath="sample.raw",
    output_png="result.png",
    style="thesis",
    calibration_offset=-1.9,
    smooth_window=11,
    remove_bg=True,
    peak_height_min=15.0,
    annotate="formula",
)
```

### 4.2 FOM物相匹配
```python
from sci_xrd import match_minerals

results = match_minerals(
    d_list=[3.03, 1.86, 1.59],
    intensity_list=[100, 85, 60],
    tolerance=0.05,
    min_score=30.0,
    min_peaks=2,
)
# 返回: score, d_fom, i_fom, delta_fom, m_fom, n_matches, matches
```

### 4.3 PDF数据库检索
```python
from sci_xrd import PDFDatabase

db = PDFDatabase()
results = db.search_by_d(
    d_list=[3.03, 1.86, 1.59],
    tolerance=0.03,
    min_match=2,
    top_n=10
)
```

### 4.4 Scherrer分析
```python
from sci_xrd import scherrer_analysis

peaks = [
    {'twotheta': 29.5, 'fwhm': 0.15, 'intensity': 100},
    {'twotheta': 36.0, 'fwhm': 0.25, 'intensity': 80},
]
results = scherrer_analysis(peaks)
# 返回: crystallite_size_nm, note
```

---

## 五、技术实现细节

### 5.1 代码统计
| 文件 | 行数 | 功能 |
|------|------|------|
| sci_xrd.py | ~1450 | 核心分析模块 |
| xrd_gui.py | ~1200 | PyQt6 GUI |
| pdf2_to_sqlite.py | ~400 | 数据库转换 |
| cif_xrd_compare.py | ~200 | CIF分析 |
| **总计** | **~3250** | |

### 5.2 依赖库
```
numpy >= 1.20
scipy >= 1.7
matplotlib >= 3.4
PyQt6 >= 6.0 (GUI)
sqlite3 (内置)
```

### 5.3 编码处理
- 源文件: UTF-8 with BOM (Windows兼容)
- GUI字体: Microsoft YaHei → SimSun 回退
- 控制台: pythonw.exe 避免GBK乱码

---

## 六、已知问题与限制

### 6.1 当前问题
1. **RAW文件解析**: 部分Bruker RAW文件角度范围识别不准确
2. **PDF数据库**: 仅包含2004版，缺少新矿物数据
3. **CIF解析**: 依赖pymatgen，未完全集成

### 6.2 功能限制
- 不支持Rietveld精修
- 不支持定量相分析
- 不支持原位XRD时间序列分析
- 不支持2D探测器数据处理

---

## 七、后续更新迭代建议

### 7.1 高优先级 (核心功能完善)

#### 1. RAW文件解析增强
- **问题**: 当前RAW1.01解析header中2θ参数提取不稳定
- **方案**: 
  - 逆向工程更多RAW格式变体
  - 添加文件签名检测自动识别格式版本
  - 支持RAW4.0 (Bruker D8最新格式)
- **价值**: ⭐⭐⭐⭐⭐ (基础功能稳定性)

#### 2. PDF数据库更新
- **问题**: 当前使用2004版，已20年未更新
- **方案**:
  - 支持PDF-4+ 数据库导入
  - 添加COD (Crystallography Open Database) 在线检索
  - 实现AMCSD (American Mineralogist) 数据接口
- **价值**: ⭐⭐⭐⭐⭐ (数据时效性)

#### 3. Rietveld精修集成
- **问题**: 无法进行定量相分析和晶胞精修
- **方案**:
  - 集成GSAS-II Python接口
  - 或调用FullProf自动化脚本
  - 提供基础精修参数GUI
- **价值**: ⭐⭐⭐⭐⭐ (专业级功能)

### 7.2 中优先级 (功能扩展)

#### 4. 定量相分析
- **方案**: 参考强度比(RIR)法、Rietveld法
- **输出**: 各相质量百分比、误差估计
- **价值**: ⭐⭐⭐⭐

#### 5. 批量处理功能
- **方案**: 
  - 文件夹批量分析
  - 结果导出为Excel/CSV
  - 批量图谱拼接对比
- **价值**: ⭐⭐⭐⭐

#### 6. 原位XRD支持
- **方案**:
  - 时间序列数据加载
  - 热图(heatmap)显示
  - 峰位/强度随时间变化曲线
- **价值**: ⭐⭐⭐⭐

#### 7. 机器学习辅助鉴定
- **方案**:
  - 训练CNN峰形识别模型
  - 物相自动推荐排序
  - 异常峰检测
- **价值**: ⭐⭐⭐⭐

### 7.3 低优先级 (优化增强)

#### 8. 图谱美化增强
- 添加阴影填充选项
- 支持对数坐标显示
- 多图谱瀑布图(waterfall)
- 3D晶体结构预览

#### 9. 报告生成
- 一键生成PDF分析报告
- 包含图谱、峰表、物相鉴定结果
- 支持自定义报告模板

#### 10. 跨平台优化
- Linux/Mac完整测试
- 打包为独立可执行文件
- 添加安装程序

### 7.4 技术债务

#### 11. 代码重构
- 将GUI与核心逻辑进一步分离
- 添加单元测试覆盖
- 完善类型注解
- 添加性能 profiling

#### 12. 文档完善
- 添加API参考文档
- 编写用户教程视频脚本
- 添加示例数据集

---

## 八、使用建议

### 8.1 日常使用流程
```
1. 加载XRD数据文件
2. 调整平滑窗口和背景扣除参数
3. 设置寻峰阈值
4. 运行分析
5. 检查物相鉴定结果
6. 调整角度校准偏移(如需要)
7. 导出出版级图谱
```

### 8.2 参数调优建议
- **平滑窗口**: 数据噪声大时增大(15-21)，保留细节时减小(5-9)
- **背景扣除λ**: 基线漂移大时增大(1e7)，弱峰检测时减小(1e5)
- **峰检测高度**: 主峰分析15-20%，全峰分析5-10%
- **d-spacing容差**: 高质量数据0.03-0.05，一般数据0.08-0.1

### 8.3 故障排查
- **角度范围错误**: 使用calibration_offset参数校准
- **物相匹配不准**: 调整tolerance，或手动指定phases
- **GUI启动失败**: 检查PyQt6安装，使用调试脚本查看错误

---

## 九、总结

Sci-XRD 技能已完成核心功能开发，具备：
- ✅ 多格式数据解析
- ✅ 标准数据处理流程
- ✅ FOM/Hanawalt物相匹配
- ✅ 出版级图谱生成
- ✅ PyQt6图形界面
- ✅ PDF2数据库存储

**当前状态**: 可用，适合日常XRD数据分析
**建议下一步**: 优先解决RAW解析稳定性，考虑集成GSAS-II实现Rietveld精修

---

*报告生成者: QClaw AI*  
*技能版本: 1.0*  
*最后更新: 2026-04-10*
