import React, { useCallback, useState } from 'react';
import { Upload, Box } from 'lucide-react';
import { plotApi } from '@/services/plotService';
import { PlotSchemaRenderer } from '@/components/Charts/Common/PlotSchemaRenderer';

interface RSMDataPoint {
  x: number; y: number; z: number;
}

export const ResponseSurface3D: React.FC = () => {
  const [data, setData] = useState<RSMDataPoint[]>([]);
  const [schema, setSchema] = useState<any>(null);
  const [contourSchema, setContourSchema] = useState<any>(null);
  const [phase, setPhase] = useState<'idle' | 'processing'>('idle');
  const [error, setError] = useState('');
  const [viewMode, setViewMode] = useState<'3d' | 'contour'>('3d');
  const [fitResult, setFitResult] = useState<any>(null);
  const [config, setConfig] = useState({
    colorscale: 'Viridis',
    interpolation: 'cubic',
    gridResolution: 50,
    fitQuadratic: false,
    showDataPoints: true,
    markOptimum: true,
    xLabel: 'Factor A',
    yLabel: 'Factor B',
    zLabel: 'Response',
  });
  const fileRef = React.useRef<HTMLInputElement>(null);

  const handleFileImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const points: RSMDataPoint[] = [];
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('//')) continue;
        const parts = trimmed.split(/[\t,;\s]+/).filter(Boolean);
        if (parts.length >= 3) {
          const x = parseFloat(parts[0]);
          const y = parseFloat(parts[1]);
          const z = parseFloat(parts[2]);
          if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
            points.push({ x, y, z });
          }
        }
      }
      if (points.length < 3) {
        setError('需要至少3个数据点（X Y Z三列）');
        return;
      }
      setData(points);
      setError('');
    } catch (err) {
      setError('文件读取失败');
    }
    e.target.value = '';
  }, []);

  const handleGenerate = useCallback(async () => {
    if (data.length < 3) { setError('请先导入数据'); return; }
    setPhase('processing');
    setError('');
    try {
      const xData = data.map(d => d.x);
      const yData = data.map(d => d.y);
      const zData = data.map(d => d.z);
      const cfg: any = {
        colorscale: config.colorscale,
        interpolation: config.interpolation,
        grid_resolution: config.gridResolution,
        fit_quadratic: config.fitQuadratic,
        show_data_points: config.showDataPoints,
        mark_optimum: config.markOptimum,
        x_label: config.xLabel,
        y_label: config.yLabel,
        z_label: config.zLabel,
      };
      const [surfaceRes, contourRes] = await Promise.all([
        plotApi.generateRSMSurface3d(xData, yData, zData, cfg),
        plotApi.generateRSMContour(xData, yData, zData, cfg),
      ]);
      setSchema(surfaceRes.schema);
      setContourSchema(contourRes.schema);
      // Fit model
      if (config.fitQuadratic) {
        try {
          const fit = await plotApi.fitRSMModel(xData, yData, zData, 2);
          setFitResult(fit);
        } catch { /* optional */ }
      }
    } catch (err) {
      setError('生成失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setPhase('idle');
    }
  }, [data, config]);

  const handleExport = useCallback(async (format: string) => {
    const currentSchema = viewMode === '3d' ? schema : contourSchema;
    if (!currentSchema) return;
    setPhase('processing');
    try {
      const result = await plotApi.exportPlot(currentSchema, format);
      const a = document.createElement('a');
      a.href = result.image_url;
      a.download = `rsm_${viewMode}.${format}`;
      a.click();
    } catch (err) {
      setError('导出失败');
    } finally {
      setPhase('idle');
    }
  }, [schema, contourSchema, viewMode]);

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)', color: 'var(--ink)', fontSize: 13 }}>
      {/* Left sidebar */}
      <div style={{ width: 280, borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', background: 'var(--sidebar-bg)', overflow: 'auto' }}>
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Box size={14} /> 响应面分析
          </span>
        </div>

        {/* Data import */}
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6 }}>XYZ 数据</div>
          <button onClick={() => fileRef.current?.click()} style={{ width: '100%', padding: '6px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            <Upload size={12} /> 导入 XYZ 数据
          </button>
          <input ref={fileRef} type="file" accept=".csv,.txt,.tsv,.dat,.xlsx" onChange={handleFileImport} style={{ display: 'none' }} />
          <div style={{ fontSize: 10, color: 'var(--mute)', marginTop: 4 }}>支持 CSV/TXT (X Y Z 三列)</div>
          {data.length > 0 && (
            <div style={{ marginTop: 4, fontSize: 11, color: 'var(--accent)' }}>{data.length} 个数据点已加载</div>
          )}
        </div>

        {/* Config */}
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6 }}>绘图参数</div>

          <div style={{ marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: 'var(--mute)' }}>色彩映射</span>
            <select value={config.colorscale} onChange={e => setConfig({...config, colorscale: e.target.value})} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }}>
              <option value="Viridis">Viridis</option>
              <option value="Cividis">Cividis</option>
              <option value="Coolwarm">Coolwarm</option>
              <option value="Jet">Jet</option>
              <option value="Hot">Hot</option>
              <option value="Plasma">Plasma</option>
            </select>
          </div>

          <div style={{ marginBottom: 4 }}>
            <span style={{ fontSize: 10, color: 'var(--mute)' }}>插值方法</span>
            <select value={config.interpolation} onChange={e => setConfig({...config, interpolation: e.target.value})} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }}>
              <option value="cubic">Cubic (三次样条)</option>
              <option value="linear">Linear (线性)</option>
              <option value="nearest">Nearest (最近邻)</option>
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, marginBottom: 3 }}>
            <span style={{ color: 'var(--mute)', minWidth: 50 }}>网格密度</span>
            <input type="range" min={20} max={100} step={5} value={config.gridResolution} onChange={e => setConfig({...config, gridResolution: parseInt(e.target.value)})} style={{ flex: 1, height: 3, accentColor: 'var(--accent)' }} />
            <span style={{ color: 'var(--mute)', minWidth: 20 }}>{config.gridResolution}</span>
          </div>

          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, cursor: 'pointer', marginBottom: 3 }}>
            <input type="checkbox" checked={config.fitQuadratic} onChange={e => setConfig({...config, fitQuadratic: e.target.checked})} />
            二次回归拟合
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, cursor: 'pointer', marginBottom: 3 }}>
            <input type="checkbox" checked={config.showDataPoints} onChange={e => setConfig({...config, showDataPoints: e.target.checked})} />
            显示实验点
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, cursor: 'pointer', marginBottom: 3 }}>
            <input type="checkbox" checked={config.markOptimum} onChange={e => setConfig({...config, markOptimum: e.target.checked})} />
            标注最优点
          </label>

          <div style={{ marginTop: 6 }}>
            {['xLabel', 'yLabel', 'zLabel'].map(key => (
              <div key={key} style={{ marginBottom: 3 }}>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>{key === 'xLabel' ? 'X轴' : key === 'yLabel' ? 'Y轴' : 'Z轴'} 标签</span>
                <input value={(config as any)[key]} onChange={e => setConfig({...config, [key]: e.target.value})} style={{ width: '100%', padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }} />
              </div>
            ))}
          </div>
        </div>

        {/* Fit result */}
        {fitResult && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>拟合结果</div>
            <div style={{ fontSize: 10, fontFamily: 'monospace', wordBreak: 'break-all', background: 'var(--bg-secondary)', padding: 4, borderRadius: 3, marginBottom: 4 }}>
              {fitResult.equation}
            </div>
            <div style={{ fontSize: 10, color: 'var(--accent)' }}>R² = {fitResult.r_squared}</div>
            {fitResult.optimum && (
              <div style={{ fontSize: 10, color: '#059669', marginTop: 2 }}>
                最优点: ({fitResult.optimum.x1?.toFixed(2)}, {fitResult.optimum.x2?.toFixed(2)}) → {fitResult.optimum.y_pred?.toFixed(2)}
              </div>
            )}
          </div>
        )}

        {/* Generate & Export */}
        <div style={{ padding: 8, marginTop: 'auto', borderTop: '1px solid var(--border-color)' }}>
          <button onClick={handleGenerate} disabled={phase === 'processing' || data.length < 3} style={{ width: '100%', padding: '8px 0', borderRadius: 6, border: 'none', background: phase === 'processing' ? 'var(--mute)' : 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            {phase === 'processing' ? '生成中...' : '生成图表'}
          </button>
          {(schema || contourSchema) && (
            <>
              <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
                <button onClick={() => setViewMode('3d')} style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: viewMode === '3d' ? '2px solid var(--accent)' : '1px solid var(--border-color)', background: viewMode === '3d' ? 'var(--accent)20' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>3D曲面</button>
                <button onClick={() => setViewMode('contour')} style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: viewMode === 'contour' ? '2px solid var(--accent)' : '1px solid var(--border-color)', background: viewMode === 'contour' ? 'var(--accent)20' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>等高线</button>
              </div>
              <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                {['png', 'svg', 'pdf'].map(fmt => (
                  <button key={fmt} onClick={() => handleExport(fmt)} style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>{fmt.toUpperCase()}</button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Center: Chart */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {error && <div style={{ padding: '6px 12px', background: '#fef2f2', color: '#dc2626', fontSize: 11, borderBottom: '1px solid #fecaca' }}>{error}</div>}
        <div style={{ flex: 1, minHeight: 0 }}>
          <PlotSchemaRenderer schema={viewMode === '3d' ? schema : contourSchema} height="100%" />
        </div>
      </div>
    </div>
  );
};
