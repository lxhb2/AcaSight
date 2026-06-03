import React, { useCallback, useState } from 'react';
import { Upload, Trash2, FlaskConical } from 'lucide-react';
import { usePlotStore } from '@/store/plotStore';
import { plotApi } from '@/services/plotService';
import { PlotSchemaRenderer } from '@/components/Charts/Common/PlotSchemaRenderer';
import { PDFCardManager } from './PDFCardManager';
import { XRDConfigPanel } from './XRDConfigPanel';

export const XRDStackedChart: React.FC = () => {
  const {
    xrdDatasets, addXrdDataset, removeXrdDataset, clearXrdDatasets,
    pdfCards,
    xrdConfig, plotSchema, setPlotSchema,
    phase, setPhase, currentThemeId,
  } = usePlotStore();

  const [error, setError] = useState('');
  const xrdFileRef = React.useRef<HTMLInputElement>(null);

  // Parse XRD data file (CSV/TXT)
  const handleXRDFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const twoTheta: number[] = [];
      const intensity: number[] = [];
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('//')) continue;
        const parts = trimmed.split(/[\t,;\s]+/).filter(Boolean);
        if (parts.length >= 2) {
          const x = parseFloat(parts[0]);
          const y = parseFloat(parts[1]);
          if (!isNaN(x) && !isNaN(y)) {
            twoTheta.push(x);
            intensity.push(y);
          }
        }
      }
      if (twoTheta.length < 2) {
        setError('无法解析XRD数据，请检查文件格式（需要2列数值：2θ Intensity）');
        return;
      }
      const label = file.name.replace(/\.[^.]+$/, '');
      const colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'];
      const color = colors[xrdDatasets.length % colors.length];
      addXrdDataset({ two_theta: twoTheta, intensity, label, color });
      setError('');
    } catch (err) {
      setError('文件读取失败: ' + (err instanceof Error ? err.message : String(err)));
    }
    e.target.value = '';
  }, [addXrdDataset, xrdDatasets.length]);

  // Generate chart
  const handleGenerate = useCallback(async () => {
    if (xrdDatasets.length === 0) {
      setError('请先导入XRD数据');
      return;
    }
    setPhase('processing');
    setError('');
    try {
      const result = await plotApi.generateXRDStacked(xrdDatasets, pdfCards, xrdConfig);
      let schema = result.schema;
      // Apply theme if not default
      if (currentThemeId && currentThemeId !== 'default') {
        try {
          const themed = await plotApi.applyTheme(schema, currentThemeId);
          schema = themed.schema;
        } catch { /* fallback to unthemed */ }
      }
      setPlotSchema(schema);
    } catch (err) {
      setError('生成失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setPhase('idle');
    }
  }, [xrdDatasets, pdfCards, xrdConfig, currentThemeId, setPhase, setPlotSchema]);

  // Export
  const handleExport = useCallback(async (format: string) => {
    if (!plotSchema) return;
    setPhase('exporting');
    try {
      const result = await plotApi.exportPlot(plotSchema, format);
      const url = result.image_url;
      const a = document.createElement('a');
      a.href = url;
      a.download = `xrd_stacked.${format}`;
      a.click();
    } catch (err) {
      setError('导出失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setPhase('idle');
    }
  }, [plotSchema, setPhase]);

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)', color: 'var(--ink)', fontSize: 13 }}>
      {/* Left: Config + Data */}
      <div style={{ width: 280, borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', background: 'var(--sidebar-bg)', overflow: 'auto' }}>
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
            <FlaskConical size={14} /> XRD 堆叠图
          </span>
        </div>

        {/* Import XRD data */}
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6 }}>XRD 数据</div>
          <button onClick={() => xrdFileRef.current?.click()} style={{ width: '100%', padding: '6px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            <Upload size={12} /> 导入 XRD 数据
          </button>
          <input ref={xrdFileRef} type="file" accept=".csv,.txt,.tsv,.dat,.xy,.asc" onChange={handleXRDFile} style={{ display: 'none' }} />
          <div style={{ fontSize: 10, color: 'var(--mute)', marginTop: 4 }}>支持 CSV/TXT/DAT (2θ, Intensity)</div>

          {/* Dataset list */}
          {xrdDatasets.length > 0 && (
            <div style={{ marginTop: 6, maxHeight: 120, overflow: 'auto' }}>
              {xrdDatasets.map((ds, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 0', fontSize: 11 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: ds.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{ds.label}</span>
                  <span style={{ color: 'var(--mute)', fontSize: 9 }}>{ds.two_theta.length}pts</span>
                  <button onClick={() => removeXrdDataset(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: 0 }}><Trash2 size={10} /></button>
                </div>
              ))}
            </div>
          )}
          {xrdDatasets.length > 0 && (
            <button onClick={clearXrdDatasets} style={{ marginTop: 4, fontSize: 9, color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>清除全部</button>
          )}
        </div>

        {/* PDF Card Manager */}
        <PDFCardManager />

        {/* Config Panel */}
        <XRDConfigPanel />

        {/* Generate & Export */}
        <div style={{ padding: 8, marginTop: 'auto', borderTop: '1px solid var(--border-color)' }}>
          <button
            onClick={handleGenerate}
            disabled={phase === 'processing' || xrdDatasets.length === 0}
            style={{ width: '100%', padding: '8px 0', borderRadius: 6, border: 'none', background: phase === 'processing' ? 'var(--mute)' : 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}
          >
            {phase === 'processing' ? '生成中...' : '生成图表'}
          </button>
          {plotSchema && (
            <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
              {['png', 'svg', 'pdf'].map((fmt) => (
                <button key={fmt} onClick={() => handleExport(fmt)} disabled={phase === 'exporting'} style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10, opacity: phase === 'exporting' ? 0.5 : 1 }}>
                  {fmt.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Center: Chart */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {error && (
          <div style={{ padding: '6px 12px', background: '#fef2f2', color: '#dc2626', fontSize: 11, borderBottom: '1px solid #fecaca' }}>{error}</div>
        )}
        <div style={{ flex: 1, minHeight: 0 }}>
          <PlotSchemaRenderer schema={plotSchema} height="100%" />
        </div>
      </div>
    </div>
  );
};
