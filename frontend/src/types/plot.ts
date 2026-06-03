/** PlotSchema — unified data contract between frontend and backend */

export interface PlotSchema {
  _chart_type?: string;
  _theme_id?: string;
  traces: PlotTrace[];
  layout: Record<string, any>;
  subplots?: SubplotConfig;
  annotations?: any[];
  export?: ExportConfig;
}

export interface PlotTrace {
  type: string;
  mode?: string;
  x?: number[];
  y?: number[];
  z?: number[][];
  name?: string;
  line?: { width?: number; color?: string; dash?: string };
  marker?: { size?: number; color?: string; symbol?: string };
  text?: string[];
  showlegend?: boolean;
  hovertemplate?: string;
  hoverinfo?: string;
  // Subplot positioning
  _row?: number;
  _col?: number;
  [key: string]: any;
}

export interface SubplotConfig {
  rows: number;
  cols: number;
  shared_xaxes?: boolean;
  shared_yaxes?: boolean;
  row_heights?: number[];
  specs?: any[][];
}

export interface ExportConfig {
  width?: number;
  height?: number;
  scale?: number;
  format?: string;
}

// === XRD specific types ===

export interface XRDDataSet {
  two_theta: number[];
  intensity: number[];
  label: string;
  color: string;
}

export interface PDFCard {
  two_theta: number[];
  intensity: number[];
  card_id: string;
  color: string;
  hkl?: string[];
}

export interface XRDConfig {
  y_offset: number;
  two_theta_range: [number, number];
  line_width: number;
  show_hkl: boolean;
  stick_width: number;
  show_y_ticks: boolean;
  font_size: number;
}

export const DEFAULT_XRD_CONFIG: XRDConfig = {
  y_offset: 1.2,
  two_theta_range: [10, 80],
  line_width: 0.8,
  show_hkl: false,
  stick_width: 1.5,
  show_y_ticks: false,
  font_size: 9,
};

// === Theme types ===

export interface PlotTheme {
  id: string;
  name: string;
  layout: Record<string, any>;
  width_mm?: number;
  dpi?: number;
  colors?: string[];
}
