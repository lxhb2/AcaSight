/**
 * 图表模板 - Origin 风格预置模板
 * 适用于材料科学、XRD、热重分析、红外光谱等常见学术图表
 */

export type TemplateId =
  | 'xrd-pattern'
  | 'tg-curve'
  | 'ftir-spectrum'
  | 'sem-eds'
  | 'uv-vis'
  | 'raman'
  | 'cv-curve'
  | 'nyquist'
  | 'stress-strain'
  | 'time-series'
  | 'bar-comparison'
  | 'scatter-correlation';

export interface ChartTemplate {
  id: TemplateId;
  name: string;
  nameCn: string;
  description: string;
  icon: string;
  defaultChartType: string;
  suggestedXLabel: string;
  suggestedYLabel: string;
  exampleData: Record<string, number | string>[];
  layout?: Partial<{
    showLegend: boolean;
    logX: boolean;
    logY: boolean;
    xTickAngle: number;
    yTickAngle: number;
    fontSize: number;
    lineWidth: number;
    markerSize: number;
    showGrid: boolean;
    gridColor: string;
    paperBgColor: string;
    plotBgColor: string;
  }>;
}

export const CHART_TEMPLATES: ChartTemplate[] = [
  {
    id: 'xrd-pattern',
    name: 'XRD Pattern',
    nameCn: 'XRD 图谱',
    description: 'X 射线衍射图谱，2θ-Intensity 坐标系',
    icon: '📊',
    defaultChartType: 'line',
    suggestedXLabel: '2θ (degrees)',
    suggestedYLabel: 'Intensity (counts)',
    exampleData: Array.from({ length: 60 }, (_, i) => ({
      '2θ (deg)': Math.round((20 + i * 0.5) * 10) / 10,
      'Intensity': Math.round(100 + Math.sin(i * 0.8) * 80 + Math.random() * 20),
    })),
    layout: { showLegend: true, xTickAngle: 0, yTickAngle: 0, fontSize: 12, lineWidth: 1.5, markerSize: 0, showGrid: true, gridColor: 'rgba(200,200,200,0.3)', paperBgColor: '#ffffff', plotBgColor: '#fafafa' },
  },
  {
    id: 'tg-curve',
    name: 'TG/DTG Curve',
    nameCn: '热重曲线',
    description: '热重分析曲线，温度-质量变化',
    icon: '🔥',
    defaultChartType: 'line',
    suggestedXLabel: 'Temperature (°C)',
    suggestedYLabel: 'Mass (%)',
    exampleData: Array.from({ length: 80 }, (_, i) => ({
      'Temp (°C)': Math.round((200 + i * 10)),
      'Mass (%)': Math.round((100 - i * 0.3 + Math.sin(i * 0.2) * 2) * 100) / 100,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, lineWidth: 2, markerSize: 0 },
  },
  {
    id: 'ftir-spectrum',
    name: 'FTIR Spectrum',
    nameCn: '红外光谱',
    description: '傅里叶变换红外光谱，波数-透过率',
    icon: '🌈',
    defaultChartType: 'line',
    suggestedXLabel: 'Wavenumber (cm⁻¹)',
    suggestedYLabel: 'Transmittance (%)',
    exampleData: Array.from({ length: 100 }, (_, i) => ({
      'Wavenumber': Math.round((4000 - i * 35)),
      'Transmittance': Math.round((70 + Math.sin(i * 0.3) * 25 + Math.random() * 5) * 10) / 10,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 11, lineWidth: 1.2, markerSize: 0 },
  },
  {
    id: 'uv-vis',
    name: 'UV-Vis Spectrum',
    nameCn: '紫外可见光谱',
    description: '紫外-可见吸收光谱，波长-吸光度',
    icon: '💜',
    defaultChartType: 'line',
    suggestedXLabel: 'Wavelength (nm)',
    suggestedYLabel: 'Absorbance (a.u.)',
    exampleData: Array.from({ length: 60 }, (_, i) => ({
      'Wavelength (nm)': Math.round((200 + i * 10)),
      'Absorbance': Math.max(0, Math.round((Math.exp(-((i - 25) ** 2) / 100) * 3 + Math.random() * 0.05) * 1000) / 1000),
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, lineWidth: 1.5, markerSize: 0 },
  },
  {
    id: 'cv-curve',
    name: 'CV Curve',
    nameCn: '循环伏安曲线',
    description: '循环伏安曲线，电压-电流密度',
    icon: '⚡',
    defaultChartType: 'line',
    suggestedXLabel: 'Potential (V vs. Ref)',
    suggestedYLabel: 'Current Density (mA/cm²)',
    exampleData: Array.from({ length: 100 }, (_, i) => ({
      'Potential (V)': Math.round((-0.5 + i * 0.01) * 1000) / 1000,
      'Current (mA)': Math.round((Math.sin(i * 0.1) * 2 + Math.cos(i * 0.05) * 0.5) * 100) / 100,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, lineWidth: 1.5, markerSize: 0 },
  },
  {
    id: 'nyquist',
    name: 'Nyquist Plot',
    nameCn: '阻抗 Nyquist 图',
    description: '电化学阻抗谱，Z\' - Z\'\' 阻抗图',
    icon: '📐',
    defaultChartType: 'scatter',
    suggestedXLabel: "Z' (Ω)",
    suggestedYLabel: "Z'' (Ω)",
    exampleData: Array.from({ length: 40 }, (_, i) => {
      const t = (i / 40) * Math.PI;
      return {
        "Z_prime (Ω)": Math.round((10 + t * 5 + Math.random() * 0.5) * 100) / 100,
        "Z_double (Ω)": Math.round((-t * 3 + Math.random() * 0.3) * 100) / 100,
      };
    }),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, markerSize: 6 },
  },
  {
    id: 'stress-strain',
    name: 'Stress-Strain',
    nameCn: '应力-应变曲线',
    description: '材料力学应力应变曲线',
    icon: '📈',
    defaultChartType: 'line',
    suggestedXLabel: 'Strain (%)',
    suggestedYLabel: 'Stress (MPa)',
    exampleData: Array.from({ length: 50 }, (_, i) => ({
      'Strain (%)': Math.round(i * 0.2 * 100) / 100,
      'Stress (MPa)': Math.round(Math.min(400, i * 8 + Math.sin(i * 0.5) * 20) * 10) / 10,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, lineWidth: 2, markerSize: 0 },
  },
  {
    id: 'time-series',
    name: 'Time Series',
    nameCn: '时序数据',
    description: '通用时间序列，折线图展示趋势',
    icon: '📉',
    defaultChartType: 'line',
    suggestedXLabel: 'Time',
    suggestedYLabel: 'Value',
    exampleData: Array.from({ length: 30 }, (_, i) => ({
      'Time (s)': i * 10,
      'Value': Math.round((100 + i * 2 + Math.sin(i * 0.3) * 30 + Math.random() * 10) * 10) / 10,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, lineWidth: 1.5, markerSize: 4 },
  },
  {
    id: 'bar-comparison',
    name: 'Bar Comparison',
    nameCn: '柱状对比图',
    description: '多组数据柱状图对比',
    icon: '📊',
    defaultChartType: 'bar',
    suggestedXLabel: 'Sample',
    suggestedYLabel: 'Value',
    exampleData: [
      { Sample: 'Sample A', Value: 85.3, Error: 2.1 },
      { Sample: 'Sample B', Value: 72.8, Error: 1.8 },
      { Sample: 'Sample C', Value: 91.5, Error: 3.2 },
      { Sample: 'Sample D', Value: 65.2, Error: 1.5 },
      { Sample: 'Sample E', Value: 78.9, Error: 2.4 },
    ],
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12 },
  },
  {
    id: 'scatter-correlation',
    name: 'Scatter Correlation',
    nameCn: '散点相关性',
    description: '两组数据',
    icon: '🔴',
    defaultChartType: 'scatter',
    suggestedXLabel: 'X',
    suggestedYLabel: 'Y',
    exampleData: Array.from({ length: 30 }, (_, i) => ({
      X: Math.round((Math.random() * 100) * 10) / 10,
      Y: Math.round((30 + i * 0.5 + Math.random() * 20) * 10) / 10,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12, markerSize: 7 },
  },
  {
    id: 'sem-eds',
    name: 'SEM/EDS',
    nameCn: '能谱图',
    description: 'SEM-EDS 元素分布图',
    icon: '⚛️',
    defaultChartType: 'bar',
    suggestedXLabel: 'Element',
    suggestedYLabel: 'Atomic %',
    exampleData: [
      { Element: 'C', 'Atomic %': 23.5 },
      { Element: 'O', 'Atomic %': 35.2 },
      { Element: 'Si', 'Atomic %': 18.7 },
      { Element: 'Al', 'Atomic %': 12.1 },
      { Element: 'Fe', 'Atomic %': 10.5 },
    ],
    layout: { showGrid: true, xTickAngle: 0, fontSize: 12 },
  },
  {
    id: 'raman',
    name: 'Raman Spectrum',
    nameCn: '拉曼光谱',
    description: '拉曼光谱图，波数-强度',
    icon: '📊',
    defaultChartType: 'line',
    suggestedXLabel: 'Raman Shift (cm⁻¹)',
    suggestedYLabel: 'Intensity (a.u.)',
    exampleData: Array.from({ length: 80 }, (_, i) => ({
      'Raman Shift': Math.round((400 + i * 25)),
      'Intensity': Math.round((500 + Math.exp(-((i - 30) ** 2) / 80) * 3000 + Math.random() * 100) * 10) / 10,
    })),
    layout: { showGrid: true, xTickAngle: 0, fontSize: 11, lineWidth: 1.2, markerSize: 0 },
  },
];

export function getTemplate(id: TemplateId): ChartTemplate | undefined {
  return CHART_TEMPLATES.find(t => t.id === id);
}
