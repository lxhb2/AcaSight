import React, { useState, useMemo, useCallback, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import {
  Upload, Trash2, Settings, Grid, Layers, Sparkles, GraduationCap,
  ScatterChart, LineChart, BarChart, PieChart, Activity, Type,
  PenTool, LucideIcon, FlaskConical, Loader2,
} from 'lucide-react';
import { CHART_TEMPLATES } from './chartTemplates';
import { useTheme } from '@/contexts/ThemeContext';
import { useApp, usePanels } from '@/contexts/AppContext';
import { chartApi, dataPreprocessApi } from '@/services/api';
import { openFile, openTextFile, saveFile } from '@/lib/tauri-adapter';


const Plot = createPlotlyComponent(Plotly);

type ChartType = 'scatter' | 'line' | 'bar' | 'pie' | 'histogram' | 'box' | 'heatmap' | '3d-scatter';

interface ColumnDef { key: string; label: string; type: 'number' | 'string' | 'date' }

interface ChartPanelProps {
  data?: Record<string, unknown>[];
  columns?: ColumnDef[];
  onDataChange?: (data: Record<string, unknown>[], columns: ColumnDef[]) => void;
}

const CHART_TYPES: { id: ChartType; label: string; icon: LucideIcon }[] = [
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
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [wizardDesc, setWizardDesc] = useState('');
  const [wizardChartType, setWizardChartType] = useState<ChartType | null>(null);
  const [wizardLoading, setWizardLoading] = useState(false);
  const [wizardSuggestion, setWizardSuggestion] = useState<{ chart_type: string; reason: string; x_col: string; y_cols: string[] } | null>(null);
  const [rawImporting, setRawImporting] = useState(false);
  const [rawInstrument, setRawInstrument] = useState('auto');
  const { } = useTheme();
  const { setPendingNoteContent } = useApp();
  const { togglePanel, openPanels } = usePanels();

  const numericCols = useMemo(() => columns.filter(c => c.type === 'number').map(c => c.key), [columns]);

  // 解析列定义
  const parseCols = useCallback((arr: Record<string, unknown>[]): ColumnDef[] => {
    const sample = arr[0] || {};
    return Object.keys(sample).map(k => ({
      key: k, label: k,
      type: typeof sample[k] === 'number' ? 'number' : 'string',
    }));
  }, []);

  // 自动检测文件分隔符（支持 , \t ; | : 空格）
  const detectDelimiter = (text: string): string => {
    const lines = text.split('\n').filter(l => l.trim()).slice(0, 20);
    if (lines.length < 2) return ',';
    const candidates = [',', '\t', ';', '|', ':', ' '];
    let bestDelim = ',';
    let bestScore = -1;
    for (const d of candidates) {
      // 对空格分隔符：检测连续2+空格的行覆盖率
      const pattern = d === ' ' ? / {2,}/g : (d === '\t' ? /\t/g : new RegExp('\\' + d, 'g'));
      const counts = lines.map(l => (l.match(pattern) || []).length);
      const nonZero = counts.filter(c => c > 0).length;
      const coverage = nonZero / lines.length;
      if (coverage < 0.5) continue;
      const avg = counts.reduce((a,b)=>a+b,0) / lines.length;
      if (avg < 0.5) continue;
      const variance = counts.reduce((s,c) => s + (c-avg)**2, 0) / counts.length;
      const score = avg * coverage / (1 + variance);
      if (score > bestScore) { bestScore = score; bestDelim = d; }
    }
    return bestDelim;
  };

  const parseCSV = useCallback((text: string, delimiter: string = ','): { headers: string[]; rows: string[][] } => {
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
    const rows: string[][] = [];
    let current = '', inQuotes = false;
    let row: string[] = [];
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
  const handleFile = useCallback(async () => {
    const ext = (name: string) => name.split('.').pop()?.toLowerCase() || '';
    try {
      // 先尝试用 openTextFile（适用于 CSV/JSON/TSV/TXT）
      const textFiles = await openTextFile({ filters: [{ name: 'Data', extensions: ['csv', 'json', 'tsv', 'txt'] }, { name: 'Excel', extensions: ['xlsx', 'xls'] }] });
      if (!textFiles.length) return;
      const file = textFiles[0];
      const e = ext(file.name);

      if (e === 'json') {
        const json = JSON.parse(file.content);
        const arr = Array.isArray(json) ? json : [json];
        const cols = parseCols(arr);
        setData(arr); setColumns(cols); setSelectedTemplate('');
        if (onDataChange) onDataChange(arr, cols);
      } else if (e === 'xlsx' || e === 'xls') {
        // Excel 需要二进制内容，重新用 openFile 获取
        const binFiles = await openFile({ filters: [{ name: 'Excel', extensions: ['xlsx', 'xls'] }] });
        if (!binFiles.length) return;
        const ExcelJS = await import('exceljs');
        const wb = new ExcelJS.Workbook();
        await wb.xlsx.load(binFiles[0].content.buffer as ArrayBuffer);
        const ws = wb.worksheets[0];
        if (!ws || ws.rowCount < 2) return;
        const headers: string[] = [];
        const headerRow = ws.getRow(1);
        headerRow.eachCell({ includeEmpty: true }, (cell, colNumber) => {
          headers[colNumber - 1] = String(cell.value ?? '');
        });
        const arr: Record<string, unknown>[] = [];
        ws.eachRow((row, rowNumber) => {
          if (rowNumber <= 1) return;
          const obj: Record<string, unknown> = {};
          let hasValue = false;
          row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
            const h = headers[colNumber - 1];
            if (h) { obj[h] = cell.value ?? ''; hasValue = true; }
          });
          if (hasValue) arr.push(obj);
        });
        const cols = parseCols(arr);
        setData(arr); setColumns(cols); setSelectedTemplate('');
        if (onDataChange) onDataChange(arr, cols);
      } else {
        // CSV / TSV / TXT — 自动检测分隔符
        const text = file.content;
        const delim = e === 'txt' ? detectDelimiter(text) : (e === 'tsv' ? '\t' : ',');
        const { headers, rows } = parseCSV(text, delim);
        if (headers.length < 1 || rows.length < 1) return;
        const arr = rows.map(r => {
          const obj: Record<string, unknown> = {};
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
  }, [onDataChange, parseCols, parseCSV]);

  const handleRawImport = useCallback(async () => {
    setRawImporting(true);
    try {
      const files = await openFile({ filters: [{ name: 'Raw Data', extensions: ['txt', 'csv', 'tsv', 'dat', 'xy', 'raw', 'asc', 'prn'] }] });
      if (!files.length) return;
      const f = files[0];
      // 从返回内容创建 File 对象传给 dataPreprocessApi.parse
      const file = new File([f.content.buffer as ArrayBuffer], f.name);
      const result = await dataPreprocessApi.parse(file, rawInstrument, 'chart_data');
      if (result.ok && result.data && result.data.length > 0) {
        const arr = (result.data as Record<string, unknown>[]).map(row => {
          const clean: Record<string, unknown> = {};
          for (const [k, v] of Object.entries(row)) {
            if (k.trim()) clean[k] = v;
          }
          return clean;
        });
        const cols = parseCols(arr);
        setData(arr);
        setColumns(cols);
        setSelectedTemplate('');
        setXCol(cols[0]?.key || '');
        setYCols(cols.filter(c => c.type === 'number' && c.key !== cols[0]?.key).slice(0, 4).map(c => c.key));
        if (onDataChange) onDataChange(arr, cols);
      } else {
        console.warn('[RawImport] result not ok or empty data:', result);
        alert('数据预处理返回为空，请检查文件格式');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.error('Raw data preprocess error:', msg);
      alert('数据预处理失败: ' + msg);
    } finally {
      setRawImporting(false);
    }
  }, [rawInstrument, onDataChange, parseCols]);

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
    const traces: Record<string, unknown>[] = [];
    const yArr = yCols.length ? yCols : numericCols.filter(c => c !== xCol);
    yArr.forEach((yKey, idx) => {
      const trace: Record<string, unknown> = { name: yKey, type: chartType === 'line' ? 'scatter' : chartType };
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
    const xaxis: Record<string, unknown> = {
      title: { text: xCol, font: { size: chartFontSize } },
      showgrid: isAcademic ? false : showGrid,
      gridcolor: 'rgba(128,128,128,0.15)',
      zeroline: isAcademic ? false : undefined,
      linecolor: isAcademic ? '#333' : undefined,
      linewidth: isAcademic ? 1.5 : undefined,
      mirror: isAcademic ? 'ticks' as const : undefined,
      tickfont: { size: chartFontSize - 2 },
    };
    const yaxis: Record<string, unknown> = {
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
      const opts: Record<string, unknown> = { format: fmt, width: 1200, height: 800, scale: 2 };
      const url = await Plotly.toImage(el, opts);
      const base64 = url.split(',')[1];
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      await saveFile(bytes, { filters: [{ name: fmt.toUpperCase(), extensions: [fmt] }], defaultPath: 'chart.' + fmt });
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
      const config = await chartApi.autoGenerate({ description: autoDesc, columns: cols, sample_data: sample, total_rows: data.length });
      if (config.chart_type) setChartType(config.chart_type as ChartType);
      if (config.x_col) setXCol(config.x_col);
      if (config.y_cols) setYCols(config.y_cols);
      if (config.academic_mode !== undefined) setAcademicMode(config.academic_mode);
      if (config.show_grid !== undefined) setShowGrid(config.show_grid);
      setAutoReason(config.reason || '推荐完成');
    } catch (e: unknown) {
      console.error('Auto chart failed:', e);
      setAutoReason('推荐失败: ' + (e instanceof Error ? e.message : String(e)));
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
      const config = await chartApi.refine({ description: autoDesc, current_config: currentConfig, columns: cols, sample_data: sample, total_rows: data.length });
      if (config.chart_type) setChartType(config.chart_type as ChartType);
      if (config.x_col) setXCol(config.x_col);
      if (config.y_cols) setYCols(config.y_cols);
      setAutoReason(config.reason || '优化完成');
    } catch (e: unknown) {
      console.error('Refine chart failed:', e);
      setAutoReason('优化失败: ' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setAutoLoading(false);
    }
  }, [autoDesc, data, columns, chartType, xCol, yCols, academicMode, showGrid]);

  const handleWizardStart = useCallback(async () => {
    if (!wizardDesc.trim()) return;
    setWizardLoading(true);
    try {
      const cols = columns.length > 0
        ? columns.map(c => ({ key: c.key, label: c.label, type: c.type }))
        : [{ key: 'auto', label: 'auto', type: 'string' as const }];
      const sample = data.length > 0 ? data.slice(0, 3) : [{}];
      const result = await chartApi.autoGenerate({ description: wizardDesc, columns: cols, sample_data: sample, total_rows: data.length || 0 });
      setWizardSuggestion({ chart_type: result.chart_type, reason: result.reason || '', x_col: result.x_col, y_cols: result.y_cols });
      setWizardChartType(result.chart_type as ChartType);
      setWizardStep(1);
    } catch (e: unknown) {
      setWizardSuggestion({ chart_type: 'scatter', reason: '推荐失败: ' + (e instanceof Error ? e.message : String(e)), x_col: '', y_cols: [] });
      setWizardStep(1);
    } finally {
      setWizardLoading(false);
    }
  }, [wizardDesc, columns, data]);

  const handleWizardApply = useCallback(() => {
    if (!wizardSuggestion) return;
    if (wizardChartType) setChartType(wizardChartType);
    if (wizardSuggestion.x_col) setXCol(wizardSuggestion.x_col);
    if (wizardSuggestion.y_cols.length) setYCols(wizardSuggestion.y_cols);
    setAutoDesc(wizardDesc);
    setAutoReason(wizardSuggestion.reason);
    setWizardOpen(false);
    setWizardStep(0);
    setWizardDesc('');
    setWizardSuggestion(null);
    setWizardChartType(null);
  }, [wizardSuggestion, wizardChartType, wizardDesc]);

  const handleWizardCancel = useCallback(() => {
    setWizardOpen(false);
    setWizardStep(0);
    setWizardDesc('');
    setWizardSuggestion(null);
    setWizardChartType(null);
  }, []);

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
            <select value={fitType} onChange={e => setFitType(e.target.value as typeof fitType)} style={{ width: '100%', padding: 3, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', fontSize: 10, marginBottom: 4 }}>
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
          <button onClick={handleFile} title="上传数据" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11 }}>
            <Upload size={12} /> 上传数据
          </button>
          <div style={{ position: 'relative', display: 'inline-flex' }}>
            <button onClick={handleRawImport} disabled={rawImporting} title="原始仪器数据导入 (XRD/XPS/Raman等)" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, border: '1px solid #059669', background: 'rgba(5,150,105,0.08)', color: '#059669', cursor: rawImporting ? 'not-allowed' : 'pointer', fontSize: 11, opacity: rawImporting ? 0.6 : 1 }}>
              {rawImporting ? <Loader2 size={12} className="spin" /> : <FlaskConical size={12} />} 原始数据
            </button>
            <select value={rawInstrument} onChange={e => setRawInstrument(e.target.value)} style={{ position: 'absolute', right: -2, bottom: -2, fontSize: 8, border: '1px solid var(--border-color)', borderRadius: 2, background: 'var(--bg-secondary)', color: 'var(--ink)', padding: '0 2px', lineHeight: 1, opacity: 0.7, cursor: 'pointer' }}>
              <option value="auto">自动</option>
              <option value="xrd">XRD</option>
              <option value="xps">XPS</option>
              <option value="raman">Raman</option>
              <option value="ftir">FTIR</option>
              <option value="mass_spec">质谱</option>
              <option value="tga_dsc">TGA/DSC</option>
              <option value="uv_vis">UV-Vis</option>
            </select>
          </div>
          <button onClick={() => { setData([]); setColumns([]); setSelectedTemplate(''); }} title="清除数据" style={{ padding: '3px 6px', borderRadius: 4, border: 'none', background: 'transparent', color: '#ef4444', cursor: 'pointer' }}>
            <Trash2 size={12} />
          </button>
          <button onClick={() => setWizardOpen(true)} title="AI绘图向导" style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 4, border: '1px solid #6366f1', background: 'rgba(99,102,241,0.08)', color: '#6366f1', cursor: 'pointer', fontSize: 11 }}>
            <Sparkles size={12} /> AI向导
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
                <button onClick={handleFile} style={{ padding: '8px 20px', borderRadius: 8, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13 }}>
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
      {wizardOpen && (
        <div style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: 'var(--glass-bg)', backdropFilter: 'blur(var(--glass-blur))', WebkitBackdropFilter: 'blur(var(--glass-blur))', borderRadius: 12, border: '1px solid var(--hairline)', boxShadow: 'var(--glass-shadow)', width: 480, maxHeight: '80vh', overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid var(--hairline)' }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sparkles size={16} style={{ color: '#6366f1' }} /> AI 绘图向导
              </span>
              <button onClick={handleWizardCancel} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute)', fontSize: 16 }}>×</button>
            </div>

            <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--hairline)' }}>
              {['描述需求', '选择图表', '确认生成'].map((label, i) => (
                <div key={i} style={{ flex: 1, padding: '8px 0', textAlign: 'center', fontSize: 11, fontWeight: wizardStep === i ? 600 : 400, color: wizardStep === i ? '#6366f1' : wizardStep > i ? 'var(--accent)' : 'var(--mute)', borderBottom: wizardStep === i ? '2px solid #6366f1' : '2px solid transparent', transition: 'all 0.2s' }}>
                  {i + 1}. {label}
                </div>
              ))}
            </div>

            <div style={{ padding: 16, flex: 1 }}>
              {wizardStep === 0 && (
                <div>
                  <p style={{ fontSize: 12, color: 'var(--body)', marginBottom: 12 }}>描述你想要绘制的图表，AI 将为你推荐最合适的图表类型和配置。</p>
                  <textarea
                    value={wizardDesc}
                    onChange={e => setWizardDesc(e.target.value)}
                    placeholder="例如：绘制温度随时间变化的折线图，展示不同材料的应力-应变曲线对比..."
                    style={{ width: '100%', height: 100, padding: 8, borderRadius: 8, border: '1px solid var(--hairline)', background: 'var(--canvas-soft)', color: 'var(--ink)', fontSize: 12, resize: 'vertical', outline: 'none' }}
                  />
                  <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                    {['散点图展示数据分布', '柱状图对比各组差异', '折线图展示趋势变化', '热图展示相关性矩阵'].map(hint => (
                      <button key={hint} onClick={() => setWizardDesc(hint)} style={{ padding: '3px 8px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer', fontSize: 10 }}>
                        {hint}
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
                    <button onClick={handleWizardCancel} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer', fontSize: 12 }}>取消</button>
                    <button onClick={handleWizardStart} disabled={wizardLoading || !wizardDesc.trim()} style={{ padding: '6px 16px', borderRadius: 6, border: 'none', background: wizardLoading || !wizardDesc.trim() ? 'var(--mute)' : '#6366f1', color: '#fff', cursor: wizardLoading || !wizardDesc.trim() ? 'not-allowed' : 'pointer', fontSize: 12, opacity: wizardLoading || !wizardDesc.trim() ? 0.5 : 1 }}>
                      {wizardLoading ? '分析中...' : '下一步'}
                    </button>
                  </div>
                </div>
              )}

              {wizardStep === 1 && wizardSuggestion && (
                <div>
                  <div style={{ padding: 12, borderRadius: 8, background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.15)', marginBottom: 12 }}>
                    <div style={{ fontSize: 11, color: '#6366f1', fontWeight: 600, marginBottom: 4 }}>AI 推荐理由</div>
                    <div style={{ fontSize: 12, color: 'var(--body)', lineHeight: 1.5 }}>{wizardSuggestion.reason || '根据您的描述推荐了合适的图表类型'}</div>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--mute)', marginBottom: 8 }}>选择图表类型：</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                    {CHART_TYPES.map(t => (
                      <button key={t.id} onClick={() => setWizardChartType(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px', borderRadius: 8, border: wizardChartType === t.id ? '2px solid #6366f1' : '1px solid var(--hairline)', background: wizardChartType === t.id ? 'rgba(99,102,241,0.08)' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11, transition: 'all 0.15s' }}>
                        <t.icon size={14} style={{ color: wizardChartType === t.id ? '#6366f1' : 'var(--mute)' }} /> {t.label}
                      </button>
                    ))}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                    <button onClick={() => setWizardStep(0)} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer', fontSize: 12 }}>上一步</button>
                    <button onClick={() => setWizardStep(2)} disabled={!wizardChartType} style={{ padding: '6px 16px', borderRadius: 6, border: 'none', background: !wizardChartType ? 'var(--mute)' : '#6366f1', color: '#fff', cursor: !wizardChartType ? 'not-allowed' : 'pointer', fontSize: 12, opacity: !wizardChartType ? 0.5 : 1 }}>下一步</button>
                  </div>
                </div>
              )}

              {wizardStep === 2 && wizardSuggestion && (
                <div>
                  <div style={{ padding: 12, borderRadius: 8, background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', marginBottom: 12 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', marginBottom: 8 }}>配置摘要</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', fontSize: 11 }}>
                      <span style={{ color: 'var(--mute)' }}>图表类型</span><span style={{ color: 'var(--ink)' }}>{CHART_TYPES.find(t => t.id === wizardChartType)?.label}</span>
                      <span style={{ color: 'var(--mute)' }}>X 轴</span><span style={{ color: 'var(--ink)' }}>{wizardSuggestion.x_col || '(自动选择)'}</span>
                      <span style={{ color: 'var(--mute)' }}>Y 轴</span><span style={{ color: 'var(--ink)' }}>{wizardSuggestion.y_cols.join(', ') || '(自动选择)'}</span>
                      <span style={{ color: 'var(--mute)' }}>学术样式</span><span style={{ color: 'var(--ink)' }}>默认关闭</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
                    <button onClick={() => setWizardStep(1)} style={{ padding: '6px 16px', borderRadius: 6, border: '1px solid var(--hairline)', background: 'transparent', color: 'var(--body)', cursor: 'pointer', fontSize: 12 }}>上一步</button>
                    <button onClick={handleWizardApply} style={{ padding: '6px 20px', borderRadius: 6, border: 'none', background: '#6366f1', color: '#fff', cursor: 'pointer', fontSize: 12, display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Sparkles size={12} /> 生成图表
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

