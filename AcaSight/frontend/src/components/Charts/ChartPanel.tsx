import React, { useState, useRef, useMemo, useCallback } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import {
  Upload, Trash2, Settings, Grid, Layers, Sparkles, GraduationCap,
  ScatterChart, LineChart, BarChart, PieChart, Activity, Type,
  PenTool,
} from 'lucide-react';
import { CHART_TEMPLATES } from './chartTemplates';
import { useTheme } from '@/contexts/ThemeContext';
import { useApp } from '@/contexts/AppContext';

const Plot = createPlotlyComponent(Plotly);

type ChartType = 'scatter' | 'line' | 'bar' | 'pie' | 'histogram' | 'box' | 'heatmap' | '3d-scatter';

interface ColumnDef { key: string; label: string; type: 'number' | 'string' | 'date' }

interface ChartPanelProps {
  data?: any[];
  columns?: ColumnDef[];
  onDataChange?: (data: any[], columns: ColumnDef[]) => void;
}

const CHART_TYPES: { id: ChartType; label: string; icon: any }[] = [
  { id: 'scatter', label: '散点图', icon: ScatterChart },
  { id: 'line', label: '折线图', icon: LineChart },
  { id: 'bar', label: '柱状图', icon: BarChart },
  { id: 'pie', label: '饼图', icon: PieChart },
  { id: 'histogram', label: '直方图', icon: Activity },
  { id: 'box', label: '箱线图', icon: Grid },
  { id: 'heatmap', label: '热图', icon: Grid },
  { id: '3d-scatter', label: '3D 散点', icon: Type },
];

export const ChartPanel: React.FC<ChartPanelProps> = ({ data: externalData, columns: externalCols, onDataChange }) => {
  const [data, setData] = useState<any[]>(externalData || []);
  const [columns, setColumns] = useState<ColumnDef[]>(externalCols || []);
  const [chartType, setChartType] = useState<ChartType>('scatter');
  const [xCol, setXCol] = useState('');
  const [yCols, setYCols] = useState<string[]>([]);
  const [showGrid, setShowGrid] = useState(true);
  const [darkBg, setDarkBg] = useState(false);
  const [configOpen, setConfigOpen] = useState(true);
  const [dataOpen, setDataOpen] = useState(true);
  const [exporting, setExporting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const chartRef = useRef<any>(null);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [fitType, setFitType] = useState<'none' | 'linear' | 'polynomial'>('none');
  const [fitOrder, setFitOrder] = useState(2);
  const [errorYCol, setErrorYCol] = useState('');
  const [legendPos, setLegendPos] = useState<'top' | 'right' | 'bottom' | 'left'>('right');
  const [xRange, setXRange] = useState<[number, number] | null>(null);
  const [yRange, setYRange] = useState<[number, number] | null>(null);
  const [xMinStr, setXMinStr] = useState('');
  const [xMaxStr, setXMaxStr] = useState('');
  const [yMinStr, setYMinStr] = useState('');
  const [yMaxStr, setYMaxStr] = useState('');
  const [autoDesc, setAutoDesc] = useState('');
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoReason, setAutoReason] = useState('');
  const [chartFontSize, setChartFontSize] = useState(14);
  const [academicMode, setAcademicMode] = useState(false);
  const { } = useTheme();
  const { setPendingNoteContent, togglePanel, openPanels } = useApp();

  const numericCols = useMemo(() => columns.filter(c => c.type === 'number').map(c => c.key), [columns]);

  // 解析列定义
  const parseCols = useCallback((arr: any[]): ColumnDef[] => {
    const sample = arr[0] || {};
    return Object.keys(sample).map(k => ({
      key: k, label: k,
      type: typeof sample[k] === 'number' ? 'number' : 'string',
    }));
  }, []);

  // 智能CSV解析（处理引号/科学计数法）
  // 自动检测文件分隔符（支持 , \t ; | : 空格）
  const detectDelimiter = (text: string): string => {
    const lines = text.split('\n').filter(l => l.trim()).slice(0, 20);
    if (lines.length < 2) return ',';
    const candidates = [',', '\t', ';', '|', ':'];
    let bestDelim = ',';
    let bestScore = -1;
    for (const d of candidates) {
      const counts = lines.map(l => (l.match(new RegExp(d === '\t' ? '\\t' : '\\' + d, 'g')) || []).length);
      const nonZero = counts.filter(c => c > 0).length;
      const coverage = nonZero / lines.length;
      if (coverage < 0.5) continue;
      const avg = counts.reduce((a,b)=>a+b,0) / lines.length;
      const variance = counts.reduce((s,c) => s + (c-avg)**2, 0) / counts.length;
      if (avg < 0.5) continue;
      const score = avg * coverage / (1 + variance);
      if (score > bestScore) { bestScore = score; bestDelim = d; }
    }
    return bestDelim;
  };

  const parseCSV = useCallback((text: string, delimiter: string = ','): { headers: string[]; rows: any[][] } => {
    // 对空格分隔做预处理：多个空格归一化为制表符
    let normalized = text;
    if (delimiter === ' ') {
      const lines = text.split('\n');
      normalized = lines.map(l => l.replace(/"([^"]*)"/g, (_, inner) => inner.replace(/\s{2,}/g, '\t'))).map(l => l.replace(/\s{2,}/g, '\t')).join('\n');
      delimiter = '\t';
    }
    // 构建分隔符集合
    const delims = new Set(delimiter === '\t' ? ['\t'] : [delimiter]);
    // 兜底：对未知分隔符也保留基本分隔符
    if (!['\t', ',', ';'].includes(delimiter)) {
      delims.add(','); delims.add('\t'); delims.add(';');
    }
    const rows: any[][] = [];
    let current = '', inQuotes = false;
    let row: any[] = [];
    for (let i = 0; i < normalized.length; i++) {
      const ch = normalized[i];
      if (ch === '"') { inQuotes = !inQuotes; }
      else if (delims.has(ch) && !inQuotes) {
        row.push(current.trim()); current = '';
      }
      else if ((ch === '\n' || ch === '\r') && !inQuotes) {
        if (current || row.length) { row.push(current.trim()); rows.push(row); }
        current = ''; row = [];
        if (ch === '\r' && normalized[i + 1] === '\n') i++;
      }
      else { current += ch; }
    }
    if (current || row.length) { row.push(current.trim()); rows.push(row); }
    const headers = rows[0]?.map(h => h.replace(/^"|"$/g, '')) || [];
    const dataRows = rows.slice(1).filter(r => r.some(v => v));
    return { headers, rows: dataRows };
  }, []);

  // 应用模板
  const applyTemplate = useCallback((id: string) => {
    const tpl = CHART_TEMPLATES.find(t => t.id === id);
    if (!tpl) return;
    setSelectedTemplate(id);
    setChartType(tpl.defaultChartType as ChartType);
    const d = [...tpl.exampleData];
    setData(d);
    const cols = parseCols(d);
    setColumns(cols);
    setXCol(cols[0]?.key || '');
    setYCols(cols.filter(c => c.type === 'number' && c.key !== cols[0]?.key).slice(0, 4).map(c => c.key));
    if (tpl.layout?.showGrid !== undefined) setShowGrid(tpl.layout.showGrid);
    if (tpl.layout?.paperBgColor) setDarkBg(tpl.layout.paperBgColor !== '#ffffff');
    if (onDataChange) onDataChange(d, cols);
  }, [onDataChange, parseCols]);

  // 解析上传文件 (CSV / JSON / XLSX)
  const handleFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    try {
      if (ext === 'json') {
        const text = await file.text();
        const json = JSON.parse(text);
        const arr = Array.isArray(json) ? json : [json];
        const cols = parseCols(arr);
        setData(arr); setColumns(cols); setSelectedTemplate('');
        if (onDataChange) onDataChange(arr, cols);
      } else if (ext === 'xlsx' || ext === 'xls') {
        const XLSX = await import('xlsx');
        const buf = await file.arrayBuffer();
        const wb = XLSX.read(buf, { type: 'array' });
        const ws = wb.Sheets[wb.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json<any[]>(ws, { header: 1 });
        if (rows.length < 2) return;
        const headers = rows[0].map(String);
        const arr = rows.slice(1).filter(r => r.some(v => v !== undefined)).map(r => {
          const obj: any = {};
          headers.forEach((h, i) => { obj[h] = r[i] ?? ''; });
          return obj;
        });
        const cols = parseCols(arr);
        setData(arr); setColumns(cols); setSelectedTemplate('');
        if (onDataChange) onDataChange(arr, cols);
      } else {
        // CSV / TSV / TXT — 自动检测分隔符
        const text = await file.text();
        const delim = ext === 'txt' ? detectDelimiter(text) : (ext === 'tsv' ? '\t' : ',');
        const { headers, rows } = parseCSV(text, delim);
        if (headers.length < 1 || rows.length < 1) return;
        const arr = rows.map(r => {
          const obj: any = {};
          headers.forEach((h, i) => {
            const v = String(r[i] ?? '').trim();
            obj[h] = isNaN(Number(v)) || v === '' ? v : Number(v);
          });
          return obj;
        });
        const cols = parseCols(arr);
        setData(arr); setColumns(cols); setSelectedTemplate('');
        if (onDataChange) onDataChange(arr, cols);
      }
    } catch (err) { console.error('Parse error:', err); }
    e.target.value = '';
  }, [onDataChange, parseCols, parseCSV]);

  // 多项式拟合计算
  const calcPolyFit = useCallback((xArr: number[], yArr: number[], order: number) => {
    const n = xArr.length;
    if (n < order + 1) return null;
    const A: number[][] = [];
    for (let i = 0; i <= order; i++) {
      A.push([]);
      for (let j = 0; j <= order; j++) {
        let sum = 0;
        for (let k = 0; k < n; k++) sum += Math.pow(xArr[k], i + j);
        A[i].push(sum);
      }
    }
    const b: number[] = [];
    for (let i = 0; i <= order; i++) {
      let sum = 0;
      for (let k = 0; k < n; k++) sum += Math.pow(xArr[k], i) * yArr[k];
      b.push(sum);
    }
    const N = order + 1;
    for (let i = 0; i < N; i++) {
      let maxRow = i;
      for (let j = i + 1; j < N; j++) if (Math.abs(A[j][i]) > Math.abs(A[maxRow][i])) maxRow = j;
      [A[i], A[maxRow]] = [A[maxRow], A[i]];
      [b[i], b[maxRow]] = [b[maxRow], b[i]];
      for (let j = i + 1; j < N; j++) {
        const f = A[j][i] / A[i][i];
        for (let k = i; k < N; k++) A[j][k] -= f * A[i][k];
        b[j] -= f * b[i];
      }
    }
    const coeff: number[] = new Array(N).fill(0);
    for (let i = N - 1; i >= 0; i--) {
      coeff[i] = b[i];
      for (let j = i + 1; j < N; j++) coeff[i] -= A[i][j] * coeff[j];
      coeff[i] /= A[i][i];
    }
    const xMin = Math.min(...xArr), xMax = Math.max(...xArr);
    const step = (xMax - xMin) / 200;
    const fitX: number[] = [], fitY: number[] = [];
    for (let x = xMin; x <= xMax; x += step) {
      let y = 0;
      for (let i = 0; i < N; i++) y += coeff[i] * Math.pow(x, i);
      fitX.push(x); fitY.push(y);
    }
    return { fitX, fitY, coeff: coeff.map(c => Math.round(c * 10000) / 10000) };
  }, []);

  // 生成 Plotly trace
  const plotData = useMemo(() => {
    if (!data.length || !xCol) return [];
    const traces: any[] = [];
    const yArr = yCols.length ? yCols : numericCols.filter(c => c !== xCol);
    yArr.forEach((yKey, idx) => {
      const trace: any = { name: yKey, type: chartType === 'line' ? 'scatter' : chartType };
      if (chartType === 'scatter' || chartType === 'line' || chartType === '3d-scatter') {
        trace.x = data.map(r => r[xCol]);
        trace.y = data.map(r => r[yKey]);
        trace.mode = chartType === 'line' ? 'lines+markers' : 'markers';
        if (errorYCol && data[0]?.[errorYCol] !== undefined) {
          trace.error_y = { array: data.map(r => Number(r[errorYCol]) || 0), visible: true, color: 'rgba(128,128,128,0.5)' };
        }
      } else if (chartType === 'bar') {
        trace.x = data.map(r => r[xCol]);
        trace.y = data.map(r => r[yKey]);
        trace.type = 'bar';
        if (errorYCol && data[0]?.[errorYCol] !== undefined) {
          trace.error_y = { array: data.map(r => Number(r[errorYCol]) || 0), visible: true, color: 'rgba(128,128,128,0.5)' };
        }
      } else if (chartType === 'pie') {
        trace.labels = data.map(r => r[xCol]);
        trace.values = data.map(r => r[yKey]);
        trace.type = 'pie';
        trace.hole = 0.4;
      } else if (chartType === 'histogram') {
        trace.x = data.map(r => r[xCol]);
        trace.type = 'histogram';
        trace.nbinsx = 20;
      } else if (chartType === 'box') {
        trace.y = data.map(r => r[xCol]);
        trace.type = 'box';
        trace.name = xCol;
      }
      trace.marker = trace.marker || { color: `hsl(${idx * 47 % 360}, 65%, 55%)` };
      traces.push(trace);

      // 拟合曲线
      if ((fitType === 'linear' || fitType === 'polynomial') && (chartType === 'scatter' || chartType === 'line')) {
        const xd = data.map(r => Number(r[xCol])).filter(v => !isNaN(v));
        const yd = data.map(r => Number(r[yKey])).filter(v => !isNaN(v));
        if (xd.length >= 2) {
          const result = fitType === 'linear'
            ? (() => {
                const n = xd.length, sx = xd.reduce((a, b) => a + b, 0), sy = yd.reduce((a, b) => a + b, 0);
                const sxx = xd.reduce((a, b) => a + b * b, 0), sxy = xd.reduce((a, b, i) => a + b * yd[i], 0);
                const m = (n * sxy - sx * sy) / (n * sxx - sx * sx);
                const b0 = (sy - m * sx) / n;
                const xMn = Math.min(...xd), xMx = Math.max(...xd);
                return { fitX: [xMn, xMx], fitY: [b0 + m * xMn, b0 + m * xMx], coeff: [Math.round(b0*10000)/10000, Math.round(m*10000)/10000] };
              })()
            : calcPolyFit(xd, yd, fitOrder);
          if (result) {
            traces.push({
              x: result.fitX, y: result.fitY,
              mode: 'lines', type: 'scatter',
              name: `拟合 ${yKey} (${fitType === 'linear' ? '线性' : '多项式'+fitOrder})`,
              line: { dash: 'dash', width: 2, color: `hsl(${(idx*47+120)%360}, 55%, 50%)` },
            });
          }
        }
      }
    });
    return traces;
  }, [data, xCol, yCols, numericCols, chartType, fitType, fitOrder, errorYCol, calcPolyFit]);

  const layout = useMemo(() => {
    const isAcademic = academicMode;
    const xaxis: any = {
      title: { text: xCol, font: { size: chartFontSize } },
      showgrid: isAcademic ? false : showGrid,
      gridcolor: 'rgba(128,128,128,0.15)',
      zeroline: isAcademic ? false : undefined,
      linecolor: isAcademic ? '#333' : undefined,
      linewidth: isAcademic ? 1.5 : undefined,
      mirror: isAcademic ? 'ticks' as const : undefined,
      tickfont: { size: chartFontSize - 2 },
    };
    const yaxis: any = {
      title: { text: yCols.join(', ') || 'Y', font: { size: chartFontSize } },
      showgrid: isAcademic ? false : showGrid,
      gridcolor: 'rgba(128,128,128,0.15)',
      zeroline: isAcademic ? false : undefined,
      linecolor: isAcademic ? '#333' : undefined,
      linewidth: isAcademic ? 1.5 : undefined,
      mirror: isAcademic ? 'ticks' as const : undefined,
      tickfont: { size: chartFontSize - 2 },
    };
    if (xRange) xaxis.range = xRange;
    if (yRange) yaxis.range = yRange;
    const bgColor = isAcademic ? '#ffffff' : (darkBg ? '#1a1a1a' : '#ffffff');
    const textColor = isAcademic ? '#333333' : (darkBg ? '#e0e0e0' : '#333333');
    return {
      title: { text: `${CHART_TYPES.find(t => t.id === chartType)?.label || ''} 图表`, font: { size: chartFontSize + 2, color: textColor } },
      xaxis, yaxis,
      paper_bgcolor: bgColor,
      plot_bgcolor: isAcademic ? '#ffffff' : (darkBg ? '#1a1a1a' : '#fafafa'),
      font: { color: textColor, size: chartFontSize, family: isAcademic ? 'Arial, Helvetica, sans-serif' : undefined },
      margin: isAcademic ? { l: 70, r: 30, t: 50, b: 60 } : { l: 60, r: 30, t: 50, b: 50 },
      showlegend: true,
      legend: {
        x: legendPos === 'right' ? 1.02 : legendPos === 'left' ? -0.1 : 0.5,
        y: legendPos === 'top' ? 1.15 : legendPos === 'bottom' ? -0.2 : 0.5,
        orientation: (legendPos === 'top' || legendPos === 'bottom') ? 'h' : 'v',
        xanchor: legendPos === 'left' ? 'left' : legendPos === 'right' ? 'right' : 'center',
        yanchor: legendPos === 'top' ? 'top' : legendPos === 'bottom' ? 'bottom' : 'middle',
        font: { size: chartFontSize - 1 },
      },
      hovermode: 'closest' as const,
    };
  }, [chartType, xCol, yCols, showGrid, darkBg, legendPos, xRange, yRange, chartFontSize, academicMode]);

  const config = useMemo(() => ({
    displayModeBar: true as const,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d'],
    responsive: true,
  }), []);

  const handleExport = async (fmt: 'png' | 'svg' | 'pdf') => {
    if (!chartRef.current) return;
    setExporting(true);
    try {
      const el = chartRef.current.el;
      const opts = { format: fmt, width: 1200, height: 800, scale: 2 } as any;
      const url = await Plotly.toImage(el, opts);
      const a = document.createElement('a');
      a.href = url; a.download = `chart.${fmt}`; a.click();
    } catch (e) { console.error('Export failed:', e); }
    finally { setExporting(false); }
  };

  // AI 自动推荐图表
  const handleAutoChart = useCallback(async () => {
    if (!autoDesc.trim() || !data.length) return;
    setAutoLoading(true); setAutoReason('');
    try {
      const cols = columns.map(c => ({ key: c.key, label: c.label, type: c.type }));
      const sample = data.slice(0, 3);
      const resp = await fetch('http://localhost:9000/api/chart/auto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: autoDesc, columns: cols, sample_data: sample, total_rows: data.length }),
      });
      const config = await resp.json();
      if (resp.status === 200) {
        if (config.chart_type) setChartType(config.chart_type);
        if (config.x_col) setXCol(config.x_col);
        if (config.y_cols) setYCols(config.y_cols);
        setAutoReason(config.reason || '推荐完成');
      } else {
        setAutoReason('推荐失败: ' + (config.detail || 'unknown'));
      }
    } catch (e: any) {
      console.error('Auto chart failed:', e);
      setAutoReason('推荐失败: ' + (e?.message || String(e)));
    } finally {
      setAutoLoading(false);
    }
  }, [autoDesc, data, columns]);

  // AI 半自动向导：基于当前配置优化
  const handleRefineChart = useCallback(async () => {
    if (!autoDesc.trim() || !data.length) return;
    setAutoLoading(true); setAutoReason('');
    try {
      const cols = columns.map(c => ({ key: c.key, label: c.label, type: c.type }));
      const sample = data.slice(0, 3);
      const currentConfig = { chart_type: chartType, x_col: xCol, y_cols: yCols, academic_mode: academicMode, show_grid: showGrid };
      const resp = await fetch('http://localhost:9000/api/chart/auto/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: autoDesc, current_config: currentConfig, columns: cols, sample_data: sample, total_rows: data.length }),
      });
      const config = await resp.json();
      if (resp.status === 200) {
        if (config.chart_type) setChartType(config.chart_type);
        if (config.x_col) setXCol(config.x_col);
        if (config.y_cols) setYCols(config.y_cols);
        setAutoReason(config.reason || '优化完成');
      } else {
        setAutoReason('优化失败: ' + (config.detail || 'unknown'));
      }
    } catch (e: any) {
      console.error('Refine chart failed:', e);
      setAutoReason('优化失败: ' + (e?.message || String(e)));
    } finally {
      setAutoLoading(false);
    }
  }, [autoDesc, data, columns, chartType, xCol, yCols, academicMode, showGrid]);

  const toggleYCol = (key: string) => {
    setYCols(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)', color: 'var(--ink)', fontSize: 13 }}>
      {/* Left sidebar: config */}
      {configOpen && (
        <div style={{ width: 240, borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', background: 'var(--sidebar-bg)', overflow: 'auto' }}>
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, fontWeight: 600 }}>图表配置</span>
            <button onClick={() => setConfigOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)' }}>×</button>
          </div>

          {/* Template selector */}
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Layers size={12} /> 学术模板
            </div>
            <select
              value={selectedTemplate}
              onChange={e => { if (e.target.value) applyTemplate(e.target.value); }}
              style={{ width: '100%', padding: 4, borderRadius: 4, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 11 }}
            >
              <option value="">🎨 选择模板...</option>
              {CHART_TEMPLATES.map(t => (
                <option key={t.id} value={t.id}>{t.icon} {t.nameCn}</option>
              ))}
            </select>
            {selectedTemplate && (
              <div style={{ fontSize: 10, color: 'var(--mute)', marginTop: 4 }}>
                {CHART_TEMPLATES.find(t => t.id === selectedTemplate)?.description}
              </div>
            )}
          </div>

          {/* Chart type */}
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase' }}>图表类型</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
              {CHART_TYPES.map(t => (
                <button
                  key={t.id}
                  onClick={() => setChartType(t.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4, padding: '4px 6px',
                    borderRadius: 6, border: chartType === t.id ? '1.5px solid var(--accent)' : '1px solid var(--border-color)',
                    background: chartType === t.id ? 'var(--bg-active)' : 'transparent',
                    color: 'var(--ink)', cursor: 'pointer', fontSize: 11,
                  }}
                >
                  <t.icon size={12} /> {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* AI Auto Chart */}
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Sparkles size={12} /> AI 智能推荐
            </div>
            <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
              <input
                type="text"
                value={autoDesc}
                onChange={e => setAutoDesc(e.target.value)}
                placeholder="描述你想要什么图表..."
                style={{ flex: 1, padding: '4px 6px', borderRadius: 4, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 11 }}
                onKeyDown={e => e.key === 'Enter' && (autoReason && !autoReason.startsWith('推荐失败') ? handleRefineChart() : handleAutoChart())}
              />
              <button
                onClick={autoReason && !autoReason.startsWith('推荐失败') ? handleRefineChart : handleAutoChart}
                disabled={autoLoading || !autoDesc.trim()}
                style={{ padding: '4px 8px', borderRadius: 4, border: 'none', background: autoLoading ? 'var(--mute)' : 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 11 }}
              >
                {autoLoading ? '...' : (autoReason && !autoReason.startsWith('推荐失败') ? '优化' : 'Go')}
              </button>
            </div>
            {autoReason && (
              <div style={{ fontSize: 10, color: autoReason.startsWith('推荐失败') ? 'var(--danger)' : 'var(--mute)', fontStyle: 'italic' }}>{autoReason}</div>
            )}
          </div>

          {/* X axis */}
          {columns.length > 0 && (
            <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase' }}>X 轴</div>
              <select value={xCol} onChange={e => setXCol(e.target.value)} style={{ width: '100%', padding: 4, borderRadius: 4, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 12 }}>
                <option value="">-- 选择列 --</option>
                {columns.map(c => <option key={c.key} value={c.key}>{c.label} ({c.type})</option>)}
              </select>
            </div>
          )}

          {/* Y axis */}
          {numericCols.length > 0 && (
            <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase' }}>Y 轴（多选）</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2, maxHeight: 120, overflow: 'auto' }}>
                {numericCols.map(k => (
                  <label key={k} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, cursor: 'pointer' }}>
                    <input type="checkbox" checked={yCols.includes(k) || (yCols.length === 0 && k !== xCol)} onChange={() => toggleYCol(k)} />
                    {k}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Style */}
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase' }}>样式</div>
            {/* 学术模式开关 */}
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, cursor: 'pointer', marginBottom: 4, color: academicMode ? 'var(--accent)' : 'var(--ink)' }}>
              <input type="checkbox" checked={academicMode} onChange={e => setAcademicMode(e.target.checked)} />
              <GraduationCap size={12} /> 学术样式
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, cursor: 'pointer', marginBottom: 4 }}>
              <input type="checkbox" checked={showGrid} onChange={e => setShowGrid(e.target.checked)} disabled={academicMode} /> 显示网格
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, cursor: 'pointer', marginBottom: 6 }}>
              <input type="checkbox" checked={darkBg} onChange={e => setDarkBg(e.target.checked)} disabled={academicMode} /> 深色背景
            </label>
            {/* 字体大小滑块 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10 }}>
              <span style={{ color: 'var(--mute)', whiteSpace: 'nowrap' }}>字号</span>
              <input type="range" min={8} max={24} value={chartFontSize} onChange={e => setChartFontSize(Number(e.target.value))} style={{ flex: 1, height: 3, accentColor: 'var(--accent)' }} />
              <span style={{ color: 'var(--mute)', minWidth: 24, textAlign: 'right' }}>{chartFontSize}px</span>
            </div>
          </div>

          {/* Axis ranges */}
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Settings size={12} /> 坐标轴范围
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3, marginBottom: 4 }}>
              <input type="text" placeholder="X min" value={xMinStr} onChange={e => setXMinStr(e.target.value)} onBlur={() => { const v = parseFloat(xMinStr); const prev = xRange; if (!isNaN(v)) setXRange([v, prev?.[1] ?? v + 1]); }} style={{ padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', width: '100%' }} />
              <input type="text" placeholder="X max" value={xMaxStr} onChange={e => setXMaxStr(e.target.value)} onBlur={() => { const v = parseFloat(xMaxStr); const prev = xRange; if (!isNaN(v)) setXRange(prev ? [prev[0], v] : [0, v]); }} style={{ padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', width: '100%' }} />
              <input type="text" placeholder="Y min" value={yMinStr} onChange={e => setYMinStr(e.target.value)} onBlur={() => { const v = parseFloat(yMinStr); const prev = yRange; if (!isNaN(v)) setYRange([v, prev?.[1] ?? v + 1]); }} style={{ padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', width: '100%' }} />
              <input type="text" placeholder="Y max" value={yMaxStr} onChange={e => setYMaxStr(e.target.value)} onBlur={() => { const v = parseFloat(yMaxStr); const prev = yRange; if (!isNaN(v)) setYRange(prev ? [prev[0], v] : [0, v]); }} style={{ padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', width: '100%' }} />
            </div>
            <button onClick={() => { setXRange(null); setYRange(null); setXMinStr(''); setXMaxStr(''); setYMinStr(''); setYMaxStr(''); }} style={{ padding: '2px 6px', fontSize: 9, borderRadius: 3, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--mute)', cursor: 'pointer', width: '100%' }}>重置范围</button>
          </div>

          {/* Fitting */}
          {(chartType === 'scatter' || chartType === 'line') && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Activity size={12} /> 拟合曲线
            </div>
            <select value={fitType} onChange={e => setFitType(e.target.value as any)} style={{ width: '100%', padding: 3, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 10, marginBottom: 4 }}>
              <option value="none">无拟合</option>
              <option value="linear">线性拟合 y=ax+b</option>
              <option value="polynomial">多项式拟合</option>
            </select>
            {fitType === 'polynomial' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10 }}>
                <span style={{ color: 'var(--mute)' }}>阶数：</span>
                {[2, 3, 4].map(o => (
                  <button key={o} onClick={() => setFitOrder(o)} style={{ padding: '1px 6px', borderRadius: 3, border: fitOrder === o ? '1.5px solid var(--accent)' : '1px solid var(--border-color)', background: fitOrder === o ? 'var(--bg-active)' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>{o}</button>
                ))}
              </div>
            )}
          </div>
          )}

          {/* Error bars */}
          {(chartType === 'scatter' || chartType === 'line' || chartType === 'bar') && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Grid size={12} /> 误差棒（Y 误差列）
            </div>
            <select value={errorYCol} onChange={e => setErrorYCol(e.target.value)} style={{ width: '100%', padding: 3, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 10 }}>
              <option value="">无</option>
              {numericCols.filter(c => c !== xCol).map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          )}

          {/* Legend position */}
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase' }}>图例位置</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 3 }}>
              {([{ id: 'top', label: '上' }, { id: 'right', label: '右' }, { id: 'bottom', label: '下' }, { id: 'left', label: '左' }] as const).map(p => (
                <button key={p.id} onClick={() => setLegendPos(p.id)} style={{ padding: '3px 0', borderRadius: 3, border: legendPos === p.id ? '1.5px solid var(--accent)' : '1px solid var(--border-color)', background: legendPos === p.id ? 'var(--bg-active)' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>{p.label}</button>
              ))}
            </div>
          </div>

          {/* Export */}
          <div style={{ padding: 8, marginTop: 'auto' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, textTransform: 'uppercase' }}>导出</div>
            <div style={{ display: 'flex', gap: 4 }}>
              {(['png', 'svg'] as const).map(fmt => (
                <button key={fmt} onClick={() => handleExport(fmt)} disabled={exporting}
                  style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10, opacity: exporting ? 0.5 : 1 }}>
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
            <button
              onClick={async () => {
                if (!chartRef.current) return;
                try {
                  const el = chartRef.current.el;
                  const url = await Plotly.toImage(el, { format: 'png', width: 1200, height: 800, scale: 2 });
                  const chartTypeLabel = CHART_TYPES.find(t => t.id === chartType)?.label || '图表';
                  const md = `## ${chartTypeLabel}\n\n![${chartTypeLabel}](${url})\n\n**数据**: ${data.length} 行 × ${columns.length} 列\n\n**X 轴**: ${xCol} | **Y 轴**: ${yCols.join(', ') || '自动'}\n\n${academicMode ? '*学术样式*' : ''}\n`;
                  setPendingNoteContent(md);
                  if (!openPanels.includes('notes')) togglePanel('notes');
                } catch { /* ignore */ }
              }}
              style={{ width: '100%', marginTop: 4, padding: '4px 0', borderRadius: 4, border: '1px solid var(--accent)', background: 'transparent', color: 'var(--accent)', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}
            >
              <PenTool size={10} /> 发送到笔记
            </button>
          </div>
        </div>
      )}

      {/* Center: chart + toolbar */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', borderBottom: '1px solid var(--border-color)', flexWrap: 'wrap' }}>
          <button onClick={() => fileRef.current?.click()} title="上传数据" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11 }}>
            <Upload size={12} /> 上传数据
          </button>
          <input ref={fileRef} type="file" accept=".csv,.json,.xlsx,.xls,.tsv,.txt" onChange={handleFile} style={{ display: 'none' }} />
          <button onClick={() => { setData([]); setColumns([]); setSelectedTemplate(''); }} title="清除数据" style={{ padding: '3px 6px', borderRadius: 4, border: 'none', background: 'transparent', color: '#ef4444', cursor: 'pointer' }}>
            <Trash2 size={12} />
          </button>
          <div style={{ width: 1, height: 16, background: 'var(--border-color)', margin: '0 4px' }} />
          <button onClick={() => setConfigOpen(o => !o)} title="配置面板" style={{ padding: '3px 6px', borderRadius: 4, border: 'none', background: configOpen ? 'var(--bg-active)' : 'transparent', color: 'var(--ink)', cursor: 'pointer' }}>
            <Settings size={12} />
          </button>
          <button onClick={() => setDataOpen(o => !o)} title="数据面板" style={{ padding: '3px 6px', borderRadius: 4, border: 'none', background: dataOpen ? 'var(--bg-active)' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11 }}>
            <Grid size={12} /> 数据
          </button>
          <div style={{ flex: 1 }} />
          {selectedTemplate && (
            <span style={{ fontSize: 10, color: 'var(--accent)', background: 'var(--bg-active)', padding: '2px 6px', borderRadius: 4 }}>
              {CHART_TEMPLATES.find(t => t.id === selectedTemplate)?.icon} {CHART_TEMPLATES.find(t => t.id === selectedTemplate)?.nameCn}
            </span>
          )}
          <span style={{ fontSize: 10, color: 'var(--mute)' }}>
            {data.length ? `${data.length} rows x ${columns.length} cols` : 'Upload data or pick template'}
          </span>
        </div>

        {/* Chart area */}
        <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
          {data.length && xCol ? (
            <Plot
              ref={chartRef}
              data={plotData}
              layout={layout}
              config={config}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--mute)' }}>
              <Layers size={48} style={{ marginBottom: 16, opacity: 0.3 }} />
              <p style={{ fontSize: 14, marginBottom: 8 }}>选择模板或上传数据开始绘图</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <select
                  value={selectedTemplate}
                  onChange={e => { if (e.target.value) applyTemplate(e.target.value); }}
                  style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 12 }}
                >
                  <option value="">🎨 选择学术模板...</option>
                  {CHART_TEMPLATES.map(t => (
                    <option key={t.id} value={t.id}>{t.icon} {t.nameCn} — {t.name}</option>
                  ))}
                </select>
                <button onClick={() => fileRef.current?.click()} style={{ padding: '8px 20px', borderRadius: 8, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13 }}>
                  上传文件
                </button>
              </div>
              <p style={{ fontSize: 11, marginTop: 8, color: 'var(--mute)' }}>支持 CSV、TSV、JSON、Excel (.xlsx/.xls)</p>
            </div>
          )}
        </div>
      </div>

      {/* Right: data table */}
      {dataOpen && data.length > 0 && (
        <div style={{ width: 320, borderLeft: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', background: 'var(--sidebar-bg)', overflow: 'auto' }}>
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, fontWeight: 600 }}>数据预览 ({data.length} 行)</span>
            <button onClick={() => setDataOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)' }}>×</button>
          </div>
          <div style={{ flex: 1, overflow: 'auto' }}>
            <table style={{ width: '100%', fontSize: 10, borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'var(--bg-secondary)', zIndex: 1 }}>
                <tr>
                  {columns.map(c => (
                    <th key={c.key} style={{ padding: '2px 4px', border: '1px solid var(--border-color)', textAlign: 'left', fontWeight: 600, whiteSpace: 'nowrap' }}>{c.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 100).map((row, ri) => (
                  <tr key={ri} style={{ background: ri % 2 === 0 ? 'var(--bg-primary)' : 'var(--bg-secondary)' }}>
                    {columns.map(c => (
                      <td key={c.key} style={{ padding: '1px 4px', border: '1px solid var(--border-color)', whiteSpace: 'nowrap', maxWidth: 100, overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(row[c.key] ?? '')}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {data.length > 100 && (
              <div style={{ padding: 4, textAlign: 'center', fontSize: 10, color: 'var(--mute)' }}>...仅显示前 100 行</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
