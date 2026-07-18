# AcaSight 科研级绘图引擎 — 下一步开发计划

> 综合《绘图模块升级方案v2》《科研级绘图引擎v3.0深度重构方案》《XRD与响应面3D绘图升级方案》三份文档，结合现有代码库状态制定

> **状态：Phase 1~4 全部完成** ✅ | 提交 `6218393` | 44 files, 5011 insertions

---

## 一、现状评估

### 1.1 已有能力

| 模块 | 文件 | 状态 |
|------|------|------|
| 通用图表面板 | `ChartPanel.tsx` | ✅ 已有 — 基于 Plotly.js，支持 scatter/line/bar/pie/histogram/box/heatmap/3d-scatter |
| 学术模板 | `chartTemplates.ts` | ✅ 已有 — 12个模板（XRD/TG/FTIR/UV-Vis/Raman/CV/Nyquist/应力应变等） |
| AI自动推荐 | `chart_auto.py` | ✅ 已有 — AI推荐图表类型+轴映射 |
| 原始数据导入 | `dataPreprocessApi` | ✅ 已有 — 支持 XRD/XPS/Raman/FTIR/TGA/UV-Vis 仪器格式 |
| 拟合曲线 | `ChartPanel.tsx` | ⚠️ 基础 — 仅前端线性/多项式拟合，无后端拟合引擎 |
| 导出 | `ChartPanel.tsx` | ⚠️ 基础 — 仅前端 Plotly.toImage 导出 PNG/SVG |

### 1.2 核心差距（对比三份方案）

| 能力 | 现状 | 目标 |
|------|------|------|
| XRD堆叠图+PDF卡片棒图 | ❌ 仅有单条XRD折线模板 | 多曲线Y偏移堆叠 + PDF标准卡片竖线 + hkl标注 |
| 响应面3D图+等高线图 | ❌ 无 | Plotly 3D Surface + Contour + 实验点标注 |
| 光谱处理引擎 | ❌ 无 | 基线校正/平滑/寻峰/多峰拟合（后端进程池） |
| Raman/XPS分峰拟合 | ❌ 无 | Pseudo-Voigt多峰拟合 + Shirley背景 + 残差图 |
| 期刊主题引擎 | ❌ 仅学术模式开关 | Nature/Science/ACS/RSC/Elsevier 5种主题JSON |
| Schema驱动渲染 | ❌ 前后端各自渲染 | 统一PlotSchema JSON → 前端Plotly预览 + 后端Kaleido导出 |
| 交互式编辑器 | ❌ 仅侧边栏配置 | 点击选中→属性面板 + 图层管理 + LaTeX轴标签 |
| AI Function Calling | ❌ 仅对话推荐 | Agent直接调用绘图工具出图 |
| 后端计算隔离 | ❌ 无 | ProcessPoolExecutor + 异步任务 + SSE进度 |

### 1.3 现有依赖

**前端已安装**：`plotly.js-dist-min`, `react-plotly.js`, `@types/plotly.js`

**后端已安装**：`numpy`, `pandas`, `openpyxl`

**后端需新增**：`scipy`, `matplotlib`, `plotly`, `kaleido`, `lmfit`, `pymatgen`, `scikit-learn`

---

## 二、架构设计（采纳v3.0重构方案）

### 2.1 Schema-Driven Rendering 架构

核心原则：**前后端共享一套 PlotSchema JSON，消除渲染双轨割裂**

```
用户操作 → 生成 PlotSchema JSON
              │
              ├─→ 前端 Plotly.js 交互预览（旋转/缩放/点击编辑）
              │
              └─→ 后端 Plotly Python + Kaleido 出版级导出（300dpi+）
                   （放弃 Matplotlib 复杂图谱组装，仅保留必须场景）
```

### 2.2 计算与IO分离架构

```
前端请求 → FastAPI API
              │
              ├─→ 轻量计算（<1s）：直接 await 执行
              │
              └─→ CPU密集计算（>1s）：
                    run_in_executor(ProcessPoolExecutor)
                    │
                    ├─→ 短任务（1-5s）：等待返回
                    └─→ 长任务（>5s）：返回 task_id → SSE推送进度
```

### 2.3 PlotStore 状态管理

从全局 Zustand 抽离为独立 PlotStore，状态机模式：

```typescript
interface PlotState {
  phase: 'idle' | 'importing' | 'processing' | 'rendering' | 'exporting';
  plotSchema: PlotSchema | null;          // 核心数据契约
  processingTaskId: string | null;        // 异步任务ID
  editorState: {
    selectedElement: TraceKey | null;
    layers: LayerConfig[];
  };
  fittedData: FittedResult | null;        // 后端拟合结果
}
```

### 2.4 与AcaSight生态融合

| 现有模块 | 融合方式 |
|----------|----------|
| 11维度数据 | 文献research_methods维度自动提取实验参数（如Cu Kα波长）填入XRD配置 |
| 文献唯一编号 | 图表自动继承文献编号（FLT-ZH-2024-01），物相鉴定结果反向写回维度 |
| AI写作工作台 | 图表交叉引用，写作中一键插入图表 |
| Excalidraw白板 | Plotly→SVG→ExcalidrawElement注入白板，支持圈阅标注 |
| 学术Agent | Function Calling：plot_xrd / plot_rsm / plot_raman 等工具 |
| PDF阅读器 | 选中图表→提取数据→直接进入绘图流程 |

---

## 三、分阶段开发计划

### Phase 1：基础设施 + XRD堆叠图（P0，2-3周）✅ 已完成

> 目标：验证 Schema-Driven 架构，完成最核心的 XRD 绘图能力

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 1.1 | 安装科学计算依赖 | P0 | `pip install scipy matplotlib plotly kaleido lmfit` |
| 1.2 | 进程池计算网关 | P0 | `ProcessPoolExecutor(max_workers=2)` + `run_in_executor` |
| 1.3 | 统一绘图API路由 | P0 | `backend/app/routers/plot.py`，整合所有绘图端点 |
| 1.4 | XRD堆叠图后端 | P0 | 多曲线Y偏移堆叠 + PDF卡片竖线，PlotSchema输出 |
| 1.5 | CIF文件解析 | P1 | `pymatgen XRDCalculator` → 衍射峰数据（进程池隔离） |
| 1.6 | Jade txt解析 | P1 | 解析Jade导出的PDF卡片数据 |
| 1.7 | Kaleido导出管线 | P0 | PlotSchema → Plotly Python → Kaleido → PNG/PDF/SVG |
| 1.8 | 期刊主题引擎 | P1 | `themes/nature.json` 等5种主题，PlotSchema中引用theme_id |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 1.9 | PlotStore状态管理 | P0 | 独立Zustand store，状态机模式 |
| 1.10 | Plotly动态加载优化 | P0 | `React.lazy` + `manualChunks`，按需加载 |
| 1.11 | XRDStackedChart组件 | P0 | PlotSchema驱动，多曲线堆叠 + PDF卡片竖线 |
| 1.12 | PDFCardManager组件 | P0 | 手动输入2θ+I% / 从CIF解析 / 从Jade导入 |
| 1.13 | XRDConfigPanel组件 | P0 | Y偏移量/2θ范围/线宽/hkl标注/颜色配置 |
| 1.14 | PlotSchema渲染器 | P0 | 通用渲染器：PlotSchema → Plotly traces + layout |
| 1.15 | 期刊主题选择器 | P1 | Nature/Science/ACS/RSC/Elsevier 一键切换 |

#### API端点

```
POST /api/plot/xrd/stacked          # XRD堆叠图（PlotSchema输出）
POST /api/plot/xrd/parse-cif        # CIF→衍射峰数据
POST /api/plot/xrd/parse-jade       # Jade txt→衍射峰数据
POST /api/plot/export               # PlotSchema→高清图片导出
GET  /api/plot/themes               # 获取期刊主题列表
```

#### 交付物

- XRD堆叠图完整可用（多曲线+PDF卡片+hkl标注）
- Schema-Driven架构验证通过
- Kaleido 300dpi导出可用
- 至少Nature/ACS两种主题

---

### Phase 2：响应面3D + 光谱处理引擎 + AI一体化（P0，3-4周）✅ 已完成

> 目标：补全3D绘图能力，上线光谱处理管线，打通AI Function Calling

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 2.1 | 响应面3D图后端 | P0 | scipy griddata插值 + Plotly Surface + Contour |
| 2.2 | 响应面拟合 | P1 | 二次回归拟合 + 方程展示 + 最优点计算 |
| 2.3 | 光谱处理引擎 | P0 | `services/plot/spectrum_engine.py` |
| 2.4 | 基线校正 | P0 | ALS/SNIP/多项式/Shirley（进程池） |
| 2.5 | 平滑滤波 | P0 | Savitzky-Golay / 小波 / 移动平均 |
| 2.6 | 自动寻峰 | P0 | scipy.signal.find_peaks + CWT + 导数法 |
| 2.7 | 多峰拟合 | P0 | lmfit框架，Gaussian/Lorentzian/Pseudo-Voigt |
| 2.8 | AI绘图工具注册 | P0 | Agent Function Calling：plot_xrd / plot_rsm / plot_raman |
| 2.9 | 数据闭环通路 | P1 | PDF阅读器→数据提取→绘图面板；绘图→写作工作台图片引用 |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 2.10 | ResponseSurface3D组件 | P0 | Plotly 3D Surface + 旋转/缩放交互 |
| 2.11 | ContourChart组件 | P0 | Plotly Contour + 实验点叠加 |
| 2.12 | RSMConfigPanel组件 | P0 | 色彩映射/插值方法/网格分辨率/最优点标注 |
| 2.13 | SpectrumProcessor组件 | P0 | 光谱预处理面板（基线/平滑/寻峰/拟合） |
| 2.14 | PeakFitPanel组件 | P1 | 拟合控制面板（峰形选择/初始参数/拟合质量） |
| 2.15 | 异步任务进度条 | P0 | SSE进度展示（拟合/导出等长任务） |

#### API端点

```
# 响应面
POST /api/plot/rsm/surface3d        # 3D响应面
POST /api/plot/rsm/contour          # 等高线图
POST /api/plot/rsm/fit-model        # 拟合响应面方程

# 光谱处理
POST /api/plot/spectrum/baseline    # 基线校正
POST /api/plot/spectrum/smooth      # 平滑滤波
POST /api/plot/spectrum/find-peaks  # 自动寻峰
POST /api/plot/spectrum/fit-peaks   # 多峰拟合
POST /api/plot/spectrum/normalize   # 归一化
```

#### 交付物

- 响应面3D图+等高线图完整可用
- 光谱处理管线可用（基线/平滑/寻峰/拟合）
- AI Agent可直接调用绘图工具出图
- 异步任务SSE进度展示

---

### Phase 3：Raman/XPS专业图谱 + 交互式编辑器（P1，3-4周）✅ 已完成

> 目标：上线材料表征核心图谱，实现类DMSAS点击编辑体验

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 3.1 | Raman绘图后端 | P1 | 光谱图 + 分峰拟合 + 残差图 |
| 3.2 | XPS绘图后端 | P1 | Shirley/Tougaard背景 + 分峰拟合 |
| 3.3 | FTIR绘图后端 | P1 | 透射率/吸光度切换 + 基线校正 + 峰归属 |
| 3.4 | UV-Vis + Tauc Plot | P1 | 吸收光谱 + 切线法求带隙 |
| 3.5 | TGA/DSC绘图后端 | P1 | 双Y轴 + DTG曲线 + 失重台阶标注 |
| 3.6 | BET绘图后端 | P1 | 等温线 + BJH孔径分布 + t-plot |
| 3.7 | XPS自旋轨道分裂约束 | P2 | 面积比固定 + 峰间距固定 |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 3.8 | ChartEditor主框架 | P1 | 点击选中→属性面板编辑 |
| 3.9 | PropertyPanel组件 | P1 | 选中曲线/坐标轴/图例/标注→实时修改 |
| 3.10 | LayerManager组件 | P1 | 图层列表 + 拖拽排序 + 高度比例调整 |
| 3.11 | AxisLabelEditor组件 | P1 | LaTeX/上下标编辑器（KaTeX渲染） |
| 3.12 | RamanSpectrumChart组件 | P1 | 原始曲线+各子峰+拟合曲线+残差图 |
| 3.13 | XPSSpectrumChart组件 | P1 | 散点+拟合总和+各子峰填充+背景虚线 |
| 3.14 | FTIRChart组件 | P1 | 透射率/吸光度切换 + 官能团归属 |
| 3.15 | UVVisChart + TaucPlot | P1 | 吸收光谱 + Tauc切线法 |
| 3.16 | TGA_DSCChart组件 | P1 | 双Y轴 + DTG曲线 |
| 3.17 | BETChart组件 | P1 | 等温线 + 孔径分布 |

#### API端点

```
POST /api/plot/raman/spectrum       # Raman光谱图
POST /api/plot/raman/peak-fit       # Raman分峰拟合
POST /api/plot/xps/spectrum         # XPS光谱图
POST /api/plot/xps/peak-fit         # XPS分峰拟合
POST /api/plot/ftir/spectrum        # FTIR光谱图
POST /api/plot/uvvis/spectrum       # UV-Vis光谱图
POST /api/plot/uvvis/tauc           # Tauc Plot
POST /api/plot/thermal/tga-dsc      # TGA/DSC图
POST /api/plot/bet/isotherm         # BET等温线图
```

#### 交付物

- Raman/XPS/FTIR/UV-Vis/TGA-DSC/BET 六大材料表征图谱可用
- 点击式图表编辑器可用
- LaTeX轴标签编辑器可用
- 图层管理系统可用

---

### Phase 4：统计分析图 + 白板融合 + 高级功能（P2，3-4周）✅ 已完成

> 目标：补全统计分析能力，Excalidraw深度融合，完善期刊生态

#### 后端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 4.1 | 方差分析→标注字母柱状图 | P1 | ANOVA + 多重比较 + 字母标注 |
| 4.2 | 相关分析→热力图 | P1 | 相关系数矩阵 + 星号显著性 |
| 4.3 | PCA→双标图 | P1 | PC1 vs PC2 + 载荷向量 + 置信椭圆 |
| 4.4 | Pareto/主效应/交互效应图 | P2 | DOE配套图表 |
| 4.5 | Rietveld精修图 | P2 | Obs+Calc+Diff+Bragg四层 |
| 4.6 | XPS Doniach-Sunjic模型 | P2 | 非对称峰形 + 自旋轨道分裂 |

#### 前端任务

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 4.7 | ANOVABarChart组件 | P1 | 带误差棒+字母标注柱状图 |
| 4.8 | CorrelationHeatmap组件 | P1 | 相关系数热力图+星号 |
| 4.9 | PCABiplot组件 | P1 | 散点+载荷箭头+椭圆 |
| 4.10 | 白板图表融合 | P2 | Plotly→SVG→ExcalidrawElement注入 |
| 4.11 | 拖拽式图例/标注编辑 | P2 | 图表内拖拽移动 |
| 4.12 | 批量出图 | P2 | 多文件批量导入/出图 |
| 4.13 | 图表模板保存/复用 | P2 | 用户自定义模板持久化 |

#### API端点

```
POST /api/plot/stats/anova-bar          # 方差分析柱状图
POST /api/plot/stats/correlation-heatmap # 相关热力图
POST /api/plot/stats/pca-biplot         # PCA双标图
POST /api/plot/rsm/pareto               # Pareto图
POST /api/plot/rsm/main-effects         # 主效应图
POST /api/plot/rsm/interaction          # 交互效应图
POST /api/plot/xrd/refinement           # Rietveld精修图
```

#### 交付物

- 统计分析三大图（ANOVA/热力图/PCA）可用
- 图表→Excalidraw白板无缝注入
- 5种期刊主题完整可用
- 批量出图功能

---

## 四、新增文件结构

```
frontend/src/
├── components/
│   └── Charts/
│       ├── ChartPanel.tsx              # 现有，保留为通用图表入口
│       ├── chartTemplates.ts           # 现有，保留
│       ├── Materials/                  # 🆕 材料表征图谱
│       │   ├── XRD/
│       │   │   ├── XRDStackedChart.tsx
│       │   │   ├── XRDRefinementChart.tsx
│       │   │   └── PDFCardManager.tsx
│       │   ├── Raman/
│       │   │   ├── RamanSpectrumChart.tsx
│       │   │   └── RamanPeakFitChart.tsx
│       │   ├── XPS/
│       │   │   ├── XPSSpectrumChart.tsx
│       │   │   └── XPSPeakFitChart.tsx
│       │   ├── FTIR/
│       │   │   └── FTIRSpectrumChart.tsx
│       │   ├── UVVis/
│       │   │   ├── UVVisChart.tsx
│       │   │   └── TaucPlotChart.tsx
│       │   ├── Thermal/
│       │   │   └── TGA_DSCChart.tsx
│       │   └── BET/
│       │       └── BETChart.tsx
│       ├── DOE/                        # 🆕 实验设计图
│       │   ├── ResponseSurface3D.tsx
│       │   ├── ContourChart.tsx
│       │   ├── ParetoChart.tsx
│       │   ├── MainEffectsChart.tsx
│       │   └── InteractionChart.tsx
│       ├── Statistics/                 # 🆕 统计分析图
│       │   ├── ANOVABarChart.tsx
│       │   ├── CorrelationHeatmap.tsx
│       │   ├── PCABiplot.tsx
│       │   ├── ViolinPlot.tsx
│       │   └── ROCChart.tsx
│       ├── Editor/                     # 🆕 图表编辑器
│       │   ├── ChartEditor.tsx
│       │   ├── PropertyPanel.tsx
│       │   ├── LayerManager.tsx
│       │   ├── AxisLabelEditor.tsx
│       │   └── ThemeSelector.tsx
│       └── Common/                     # 🆕 通用组件
│           ├── DataImportPanel.tsx
│           ├── SpectrumProcessor.tsx
│           ├── PeakFitPanel.tsx
│           ├── ChartExportPanel.tsx
│           └── PlotSchemaRenderer.tsx  # 核心渲染器
├── services/
│   └── plotService.ts                  # 🆕 绘图API服务层
└── store/
    └── plotStore.ts                    # 🆕 绘图状态管理

backend/app/
├── services/
│   └── plot/                           # 🆕 绘图服务
│       ├── spectrum_engine.py          # 光谱处理引擎
│       ├── baseline.py                 # 基线校正
│       ├── smoothing.py                # 平滑滤波
│       ├── peak_detection.py           # 寻峰
│       ├── peak_fitting.py             # 多峰拟合
│       ├── xrd_plot.py                 # XRD绘图
│       ├── raman_plot.py               # Raman绘图
│       ├── xps_plot.py                 # XPS绘图
│       ├── ftir_plot.py                # FTIR绘图
│       ├── uvvis_plot.py               # UV-Vis绘图
│       ├── rsm_plot.py                 # 响应面绘图
│       ├── stats_plot.py               # 统计绘图
│       ├── cif_parser.py               # CIF文件解析
│       ├── theme_engine.py             # 期刊主题引擎
│       └── schema_renderer.py          # PlotSchema→Plotly+Kaleido渲染
├── routers/
│   └── plot.py                         # 🆕 统一绘图API路由
└── themes/                             # 🆕 期刊主题JSON
    ├── nature.json
    ├── science.json
    ├── acs.json
    ├── rsc.json
    └── elsevier.json
```

---

## 五、关键技术决策

### 5.1 渲染方案：Plotly统一，放弃Matplotlib复杂组装

| 场景 | 方案 | 理由 |
|------|------|------|
| 交互预览 | Plotly.js | 已有依赖，交互体验好 |
| 出版导出 | Plotly Python + Kaleido | 与前端PlotSchema 100%一致 |
| 特殊期刊排版 | Matplotlib（仅此场景） | 解析PlotSchema动态映射plt.rcParams |

### 5.2 计算隔离：进程池 + SSE

```python
executor = ProcessPoolExecutor(max_workers=2)

async def async_fit(x_data, y_data, params):
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        executor, _sync_fit, x_data, y_data, params
    )
    return result
```

超过5s的任务（XPS约束拟合、Rietveld精修）改为异步任务模式：API返回task_id，前端SSE获取进度。

### 5.3 Plotly.js包体积控制

```typescript
// 动态加载，不打入主bundle
const Plot = React.lazy(() => import('react-plotly.js'));

// vite.config.ts manualChunks
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        plotly: ['plotly.js-dist-min', 'react-plotly.js']
      }
    }
  }
}
```

### 5.4 AI Function Calling 工具定义

```json
{
  "name": "plot_xrd_stack",
  "description": "根据数据和文献ID绘制XRD堆叠图并匹配PDF卡片",
  "parameters": {
    "paper_ids": { "type": "array", "items": {"type": "string"}, "description": "AcaSight文献编号" },
    "pdf_card_keywords": { "type": "array", "items": {"type": "string"}, "description": "物相关键词" },
    "style": { "type": "string", "enum": ["Nature", "ACS", "RSC"], "default": "Nature" }
  }
}
```

### 5.5 期刊主题JSON格式

```json
{
  "id": "nature",
  "name": "Nature",
  "layout": {
    "font": { "family": "Arial", "size": 6, "color": "#000" },
    "paper_bgcolor": "#fff",
    "plot_bgcolor": "#fff",
    "xaxis": { "linewidth": 0.5, "showline": true, "linecolor": "#000" },
    "yaxis": { "linewidth": 0.5, "showline": true, "linecolor": "#000" },
    "margin": { "l": 40, "r": 10, "t": 15, "b": 40 }
  },
  "width_mm": 89,
  "dpi": 300,
  "colors": ["#4C78A8", "#F58518", "#E45756", "#72B7B2", "#54A24B"]
}
```

---

## 六、依赖安装计划

### 后端新增

```bash
pip install scipy>=1.11.0 matplotlib>=3.8.0 plotly>=5.18.0 kaleido>=0.2.1 lmfit>=1.2.0 scikit-learn>=1.3.0
```

### CIF解析（Phase 1可选，Phase 2必需）

```bash
pip install pymatgen>=2024.0
```

> 注意：pymatgen依赖链较重（含spglib/monty），MVP阶段先支持手动输入和Jade txt导入，CIF解析作为Phase 1后期加入。

### XPS专用（Phase 3）

```bash
pip install lmfitxps>=0.1.0
```

---

## 七、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 多峰拟合不稳定 | 拟合结果依赖初始参数，易局部最优 | 自动寻峰提供初始估计 + lmfit边界约束 + 用户可手动调参重拟合 |
| Plotly.js 3.5MB体积 | 影响首屏加载 | 动态加载 + manualChunks独立chunk + 按需下载 |
| pymatgen依赖链重 | 增加部署复杂度 | MVP阶段不依赖，CIF解析作为可选功能，长期考虑轻量方案gemmi |
| CPU密集任务阻塞 | 影响平台其他功能响应 | ProcessPoolExecutor隔离 + 异步任务模式 + SSE进度 |
| 前后端渲染不一致 | "所见非所得" | Schema-Driven统一渲染，后端用Plotly+Kaleido而非Matplotlib |
| XPS拟合复杂性 | 自旋轨道分裂+非对称峰形 | MVP先支持基础Gaussian-Lorentzian，Phase 3引入Doniach-Sunjic |

---

## 八、验收标准

### Phase 1 验收

- [ ] 导入3组XRD数据，生成Y偏移堆叠图，曲线不重叠
- [ ] 添加2张PDF标准卡片，竖线棒图正确叠加，颜色区分
- [ ] hkl标注显示在主峰上方，不拥挤
- [ ] 切换Nature主题，字号/线宽/边框自动调整
- [ ] 导出300dpi PNG，与前端预览视觉一致
- [ ] CIF文件上传→自动解析衍射峰→生成PDF卡片数据

### Phase 2 验收

- [ ] 导入XYZ数据，生成3D响应面图，可旋转/缩放
- [ ] 同数据生成等高线图，实验点标注可见
- [ ] Raman数据基线校正→平滑→寻峰→拟合，全流程可操作
- [ ] 拟合结果展示：原始曲线+各子峰+拟合总和+残差图
- [ ] AI Agent对话"帮我画XRD堆叠图"→自动调用工具出图
- [ ] 长任务（拟合）显示SSE进度条

### Phase 3 验收

- [ ] XPS光谱Shirley背景扣除+分峰拟合，化学态标注正确
- [ ] 点击曲线→属性面板弹出→修改颜色/线宽→实时更新
- [ ] LaTeX轴标签编辑器输入$2\\theta\\,(°)$→正确渲染
- [ ] 图层管理：拖拽调整XRD曲线与PDF卡片图层顺序
- [ ] FTIR/UV-Vis/TGA-DSC/BET图谱各自功能完整

### Phase 4 验收

- [ ] 方差分析→自动标注字母柱状图，同字母=无显著差异
- [ ] 图表→Excalidraw白板注入，可在图表上圈阅标注
- [ ] 5种期刊主题一键切换，格式精确匹配
- [ ] 批量导入5个XRD文件→一键出5张堆叠图

---

## 九、与现有代码的兼容策略

| 现有组件 | 处理方式 |
|----------|----------|
| `ChartPanel.tsx` | 保留为通用图表入口，新增"Origin绘图"标签页切换到专业模式 |
| `chartTemplates.ts` | 保留并扩展，新增XRD堆叠/响应面/Raman等专业模板 |
| `chart_auto.py` | 保留AI推荐功能，新增绘图Function Calling工具注册 |
| `dataPreprocessApi` | 复用原始数据导入逻辑，对接新的PlotSchema管线 |

---

## 十、总览时间线

```
Phase 1: 基础设施 + XRD堆叠图          ████████████████████  ✅ 已完成
Phase 2: 响应面3D + 光谱引擎 + AI       ████████████████████  ✅ 已完成
Phase 3: Raman/XPS + 交互编辑器         ████████████████████  ✅ 已完成
Phase 4: 统计图 + 白板融合 + 高级功能    ████████████████████  ✅ 已完成
```
