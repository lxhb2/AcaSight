# PDF2-2004 数据库分析与改进方案

## 一、PDF2-2004 文件夹内容分析

### 1.1 主要数据文件

| 文件 | 大小 | 内容 | 用途 |
|------|------|------|------|
| **pdf2.dat** | 588 MB | PDF2-2004 主数据库，163,835 张卡片 | d-spacing、强度、矿物名、化学式、晶体学数据 |
| **summary.dat** | 12.4 MB | 摘要索引 | 矿物名、化学式快速查找 |
| **mineral.dat** | 17 KB | 矿物分类数据 | Strunz 分类码、相关矿物 |
| **codens.dat** | 269 KB | COD 编号列表 | 链接到 Crystallography Open Database |
| **JCPDS.DAT** | 16 MB | JCPDS 数据 | 备用参考数据 |
| **inorgngr.dat** | 19 MB | 无机物分组 | 化学分类 |

### 1.2 索引文件 (Winind/ 和 Vaxind/)

- **JCPDS.IND** - JCPDS 编号索引 (二进制)
- **PDF2.IDX** - PDF2 快速检索索引 (21 MB)
- **CHEM.IND** - 化学元素索引
- **MINERAL.IND** - 矿物名索引
- **HANAWALT.IND** - Hanawalt 检索索引

### 1.3 CIF 文件 (cif/)

包含晶体结构信息 (CIF 格式)，可用于：
- 晶格参数精修
- 结构因子计算
- 模拟 XRD 图谱

## 二、pdf2.dat 格式解析结果

### 2.1 卡片结构 (T-format 示例)

```
M000010842       ← M-card 头 (卡片号 010842)
D010842T1  797E  ← T1: 参考强度 (科学计数法)
D010842T2I-42d  122  4  4.283  282.81  ← T2: hkl, 空间群参数
D010842T3I-42d  122  4  4.38A  4.310  183.51  282.81  ← T3: 更多参数
D010842T4I M     ← T4: Primary/Alternate 标记
D010842T5Copper Iron Sulfide  P 1  ← T5: 矿物英文名
D010842T6Chalcopyrite  M 2  ← T6: 矿物名
D010842T6Cu Fe S2  ← T6: 化学式
D010842T8ANCHAM  10  475 1938 Hanawalt. et al.  ← T8: 期刊参考
D010842T9DANASG  UC 2  ← T9: 晶体系统代码
D010842T9tI  16.00  ← T9: 空间群 (tI = 四方 I-中心)
D010842TADelete: ...  ← TA: 注释
D010842TBBrassy yellow  ← TB: 颜色
D010842TG3.03000100  1  1  2C  ← TG: 第一个 d-I 峰 + hkl
D010842TI1.86000 83  2  2  0C  ← TI: 后续 d-I 峰 + hkl
D010842TI1.59000 20  3  1  2C
...
D010842TIB 3.03/X 1.86/8 ...  ← TIB: 峰摘要
```

### 2.2 峰数据格式

- **d-spacing**: 5 位小数 (如 3.03000)
- **Intensity**: 整数 (如 100)
- **hkl**: 晶面指数 (如 1 1 2)
- **SG code**: 晶体系统代码 (如 C = Cubic, T = Tetragonal)

### 2.3 已提取的关键矿物 (30种)

| 矿物 | PDF卡号 | 主峰 d (Å) | 主峰 I | 化学式 |
|------|---------|-----------|--------|--------|
| Chalcopyrite | 010842 | 3.030 | 100 | CuFeS2 |
| Pyrite | 011295 | 1.630 | 100 | FeS2 |
| Covellite | 011296 | 1.890 | 100 | CuS |
| Galena | 010983 | 2.970 | 100 | PbS |
| Sphalerite | 011294 | 3.120 | 100 | ZnS |
| Quartz | 010870 | 3.350 | 100 | SiO2 |
| Calcite | 010861 | 3.040 | 100 | CaCO3 |
| Magnetite | 011103 | 2.530 | 100 | Fe3O4 |
| Hematite | 011104 | 2.690 | 100 | Fe2O3 |
| Dolomite | 011075 | 2.890 | 100 | CaMg(CO3)2 |
| Fluorite | 011145 | 1.930 | 100 | CaF2 |
| Barite | 011149 | 2.100 | 100 | BaSO4 |
| Goethite | 011117 | 2.450 | 80 | FeO(OH) |
| Cuprite | 011302 | 2.440 | 100 | Cu2O |
| Malachite | 011203 | 2.860 | 100 | Cu2CO3(OH)2 |
| Azurite | 011204 | 5.100 | 71 | Cu3(CO3)2(OH)2 |
| Anglesite | 011205 | 3.000 | 100 | PbSO4 |
| Cassiterite | 010982 | 3.400 | 100 | SnO2 |
| Rutile | 011121 | 1.690 | 100 | TiO2 |
| Anatase | 011122 | 3.520 | 100 | TiO2 |
| Zircon | 011006 | 3.600 | 83 | ZrSiO4 |
| Apatite | 011007 | 3.080 | 100 | Ca5(PO4)3(F,Cl,OH) |
| Scheelite | 011008 | 3.090 | 100 | CaWO4 |
| Beryl | 011009 | 3.230 | 100 | Be3Al2Si6O18 |
| Sillimanite | 011010 | 2.200 | 100 | Al2SiO5 |
| Spinel | 011011 | 2.480 | 100 | MgAl2O4 |
| Chromite | 011012 | 2.480 | 100 | FeCr2O4 |
| Hausmannite | 011013 | 2.480 | 100 | Mn3O4 |
| Pyrolusite | 011014 | 3.110 | 100 | MnO2 |

## 三、可插入数据库的额外信息

### 3.1 从 mineral.dat 提取

- **Strunz 分类码**: PYR, CAL, QTZ 等
- **矿物分组**: 相关矿物结构
- **Nickel-Strunz 编号**: 如 PYR 3 (第3类硫化物)

### 3.2 从 codens.dat 提取

- **COD 编号**: 链接到 Crystallography Open Database
- 可获取完整晶体结构数据

### 3.3 从 CIF 文件提取

- **晶格参数**: a, b, c, alpha, beta, gamma
- **原子位置**: 完整晶体结构
- **空间群**: 完整空间群符号

## 四、提升匹配准确率的方案

### 4.1 当前问题

1. **仅 d-spacing 匹配**: 不考虑强度比例
2. **无元素过滤**: 返回无关矿物
3. **固定容差**: 未考虑 2θ 角度影响
4. **无双峰验证**: 未要求多个峰同时匹配

### 4.2 改进方案

#### 方案 1: 强度比例验证

```python
def match_with_intensity_ratio(exp_peaks, ref_peaks, tolerance=0.02):
    """
    不仅匹配 d-spacing，还验证强度比例
    
    例如: 如果实验峰 d=3.03(I=100) 和 d=1.86(I=83)
    参考峰也应具有相似的强度比例
    """
    # 归一化强度到 0-100
    exp_max = max(p['I'] for p in exp_peaks)
    ref_max = max(p['I'] for p in ref_peaks)
    
    # 计算强度比例差异
    ratio_diff = abs(exp_I/exp_max - ref_I/ref_max)
    if ratio_diff > 0.3:  # 30% 容差
        score *= 0.5  # 降低匹配分数
```

#### 方案 2: 元素过滤

```python
def filter_by_elements(candidates, user_elements):
    """
    根据用户指定的元素过滤候选矿物
    
    例如: 用户指定 Cu, Fe, S
    只返回包含这些元素的矿物
    """
    filtered = []
    for mineral in candidates:
        formula = mineral['formula']  # "Cu Fe S2"
        elements = parse_formula(formula)  # ['Cu', 'Fe', 'S']
        
        # 检查是否所有实验元素都在矿物中
        if all(e in elements for e in user_elements):
            filtered.append(mineral)
    return filtered
```

#### 方案 3: 综合评分系统

```python
def calculate_match_score(exp_peaks, ref_peaks):
    """
    综合评分 = d精度 × 强度吻合度 × 元素一致性
    """
    score = 0
    matched_peaks = 0
    
    for exp_d, exp_I in exp_peaks:
        # 找最佳匹配的参考峰
        best_match = None
        best_score = 0
        
        for ref_d, ref_I in ref_peaks:
            # d-spacing 匹配度
            d_diff = abs(exp_d - ref_d) / exp_d
            if d_diff > 0.02:  # 2% 容差
                continue
            
            # 强度吻合度
            I_ratio_sim = 1 - abs(exp_I/100 - ref_I/100)
            
            # 综合分数
            peak_score = (1 - d_diff) * I_ratio_sim
            
            if peak_score > best_score:
                best_score = peak_score
                best_match = (ref_d, ref_I)
        
        if best_match:
            score += best_score
            matched_peaks += 1
    
    # 要求至少匹配 3 个峰
    if matched_peaks < 3:
        return 0
    
    # 归一化到 0-100
    return min(100, score * 100 / len(exp_peaks))
```

#### 方案 4: 自适应容差

```python
def adaptive_tolerance(d_spacing, wavelength=1.5406):
    """
    根据 d-spacing 计算自适应容差
    
    小 d 值 (高角度) 需要更严格的容差
    因为 Δd/d = -cot(θ) × Δθ
    """
    import math
    
    # 计算 2θ
    theta = math.asin(wavelength / (2 * d_spacing))
    two_theta = math.degrees(2 * theta)
    
    # 高角度区域容差更严格
    if two_theta > 60:
        return 0.01  # 1%
    elif two_theta > 40:
        return 0.015  # 1.5%
    else:
        return 0.02  # 2%
```

#### 方案 5: 多峰同时匹配

```python
def require_multiple_peaks(exp_peaks, ref_peaks, min_matches=3):
    """
    要求至少 min_matches 个峰同时匹配
    
    避免单峰巧合匹配
    """
    matches = 0
    for exp_d, exp_I in exp_peaks:
        for ref_d, ref_I in ref_peaks:
            if abs(exp_d - ref_d) / exp_d < 0.02:
                matches += 1
                break
    
    return matches >= min_matches
```

## 五、推荐的数据库表结构

```sql
-- 主矿物表
CREATE TABLE minerals (
    id INTEGER PRIMARY KEY,
    pdf_card_id TEXT UNIQUE,      -- PDF-XXXXX
    mineral_name TEXT,            -- 矿物名
    chemical_formula TEXT,        -- 化学式
    formula_parsed TEXT,          -- 解析后的元素列表 JSON
    space_group TEXT,             -- 空间群
    crystal_system TEXT,          -- 晶系
    strunz_code TEXT,             -- Strunz 分类码
    journal_ref TEXT,             -- 期刊参考
    quality TEXT,                 -- Primary/Alternate
    color TEXT,                   -- 颜色
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 峰数据表
CREATE TABLE peaks (
    id INTEGER PRIMARY KEY,
    mineral_id INTEGER,
    d_spacing REAL,               -- d值 (Å)
    intensity INTEGER,            -- 相对强度
    hkl_h INTEGER,                -- 晶面指数 h
    hkl_k INTEGER,                -- 晶面指数 k
    hkl_l INTEGER,                -- 晶面指数 l
    FOREIGN KEY (mineral_id) REFERENCES minerals(id)
);

-- 元素索引表 (用于快速元素过滤)
CREATE TABLE mineral_elements (
    mineral_id INTEGER,
    element TEXT,
    FOREIGN KEY (mineral_id) REFERENCES minerals(id)
);

-- 索引
CREATE INDEX idx_peaks_d ON peaks(d_spacing);
CREATE INDEX idx_minerals_formula ON minerals(chemical_formula);
CREATE INDEX idx_mineral_elements ON mineral_elements(element);
```

## 六、实施计划

### Phase 1: 数据提取 (已完成)
- ✅ 解析 pdf2.dat 格式
- ✅ 提取 30 种关键矿物
- ✅ 验证峰数据准确性

### Phase 2: 数据库构建
- [ ] 创建 SQLite 数据库
- [ ] 插入提取的矿物数据
- [ ] 添加元素索引
- [ ] 从 mineral.dat 添加 Strunz 分类

### Phase 3: 匹配算法改进
- [ ] 实现强度比例验证
- [ ] 实现元素过滤
- [ ] 实现综合评分系统
- [ ] 实现自适应容差
- [ ] 实现多峰同时匹配

### Phase 4: 测试与优化
- [ ] 使用已知样品测试
- [ ] 调整评分权重
- [ ] 优化查询性能

## 七、文件清单

已生成文件:
- `_pdf2_explore.py` - PDF2 格式解析脚本
- `_pdf2_extract_full.py` - 完整提取脚本
- `pdf2_minerals.json` - 提取的矿物数据 (JSON)

建议新增:
- `build_database.py` - 构建 SQLite 数据库
- `match_algorithm.py` - 改进的匹配算法
- `element_parser.py` - 化学式解析器
