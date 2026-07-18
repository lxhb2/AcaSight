import React, { useCallback, useState } from 'react';
import { Upload, Waves } from 'lucide-react';
import { plotApi } from '@/services/plotService';
import { PlotSchemaRenderer } from '@/components/Charts/Common/PlotSchemaRenderer';
import { openTextFile } from '@/lib/tauri-adapter';

interface SpectrumData {
  x: number[];
  y: number[];
  label: string;
}

interface SpectrumProcessorProps {
  defaultSpectrumType?: string;
}

export const SpectrumProcessor: React.FC<SpectrumProcessorProps> = ({ defaultSpectrumType }) => {
  const [spectrumData, setSpectrumData] = useState<SpectrumData | null>(null);
  const [processedY, setProcessedY] = useState<number[] | null>(null);
  const [baseline, setBaseline] = useState<number[] | null>(null);
  const [peaks, setPeaks] = useState<any[]>([]);
  const [fitSchema, setFitSchema] = useState<any>(null);
  const [fitResult, setFitResult] = useState<any>(null);
  const [phase, setPhase] = useState<'idle' | 'processing'>('idle');
  const [error, setError] = useState('');
  const [step, setStep] = useState<'import' | 'baseline' | 'smooth' | 'peaks' | 'fit'>('import');

  // Config
  const [baselineMethod, setBaselineMethod] = useState('als');
  const [smoothMethod, setSmoothMethod] = useState('savgol');
  const [peakType, setPeakType] = useState('pvoigt');
  const [spectrumType, setSpectrumType] = useState<'raman' | 'xps' | 'ftir'>(() => {
    if (defaultSpectrumType === 'xps') return 'xps';
    if (defaultSpectrumType === 'ftir') return 'ftir';
    return 'raman';
  });

  const handleFileImport = useCallback(async () => {
    const files = await openTextFile({ filters: [{ name: 'Spectrum Data', extensions: ['csv', 'txt', 'tsv', 'dat', 'spc', 'jdx'] }] });
    if (!files.length) return;
    const file = files[0];
    try {
      const text = file.content;
      const lines = text.trim().split('\n');
      const x: number[] = [];
      const y: number[] = [];
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#') || trimmed.startsWith('//')) continue;
        const parts = trimmed.split(/[\t,;\s]+/).filter(Boolean);
        if (parts.length >= 2) {
          const xv = parseFloat(parts[0]);
          const yv = parseFloat(parts[1]);
          if (!isNaN(xv) && !isNaN(yv)) { x.push(xv); y.push(yv); }
        }
      }
      if (x.length < 5) { setError('数据点太少'); return; }
      setSpectrumData({ x, y, label: file.name.replace(/\.[^.]+$/, '') });
      setProcessedY(null);
      setBaseline(null);
      setPeaks([]);
      setFitSchema(null);
      setFitResult(null);
      setStep('baseline');
      setError('');
    } catch (err) { setError('文件读取失败'); }
  }, []);

  const handleBaseline = useCallback(async () => {
    if (!spectrumData) return;
    setPhase('processing');
    try {
      const result = await plotApi.spectrumBaseline(spectrumData.x, spectrumData.y, baselineMethod, {});
      setBaseline(result.baseline);
      setProcessedY(result.y_corrected);
      setStep('smooth');
      setError('');
    } catch (err) { setError('基线校正失败'); }
    finally { setPhase('idle'); }
  }, [spectrumData, baselineMethod]);

  const handleSmooth = useCallback(async () => {
    if (!spectrumData) return;
    setPhase('processing');
    try {
      const yInput = processedY || spectrumData.y;
      const result = await plotApi.spectrumSmooth(yInput, smoothMethod, {});
      setProcessedY(result.y_smoothed);
      setStep('peaks');
      setError('');
    } catch (err) { setError('平滑失败'); }
    finally { setPhase('idle'); }
  }, [spectrumData, processedY, smoothMethod]);

  const handleFindPeaks = useCallback(async () => {
    if (!spectrumData) return;
    setPhase('processing');
    try {
      const yInput = processedY || spectrumData.y;
      const result = await plotApi.spectrumFindPeaks(spectrumData.x, yInput, { prominence: 0.05 });
      setPeaks(result.peaks);
      setStep('fit');
      setError('');
    } catch (err) { setError('寻峰失败'); }
    finally { setPhase('idle'); }
  }, [spectrumData, processedY]);

  const handleFit = useCallback(async () => {
    if (!spectrumData || peaks.length === 0) return;
    setPhase('processing');
    try {
      const yInput = processedY || spectrumData.y;
      const peakPositions = peaks.map(p => p.x);
      const xLabel = spectrumType === 'raman' ? 'Raman Shift (cm⁻¹)' : spectrumType === 'xps' ? 'Binding Energy (eV)' : 'Wavenumber (cm⁻¹)';
      const result = await plotApi.spectrumFitPeaks(spectrumData.x, yInput, peakPositions, peakType, { x_label: xLabel, show_residual: true });
      setFitSchema(result.schema);
      setFitResult(result.fit_result);
      setError('');
    } catch (err) { setError('拟合失败: ' + (err instanceof Error ? err.message : String(err))); }
    finally { setPhase('idle'); }
  }, [spectrumData, processedY, peaks, peakType, spectrumType]);

  // Build preview schema from current data
  const previewSchema = React.useMemo(() => {
    if (!spectrumData) return null;
    const traces: any[] = [
      { type: 'scatter', mode: 'lines', x: spectrumData.x, y: spectrumData.y, name: 'Original', line: { width: 1, color: '#999' } },
    ];
    if (processedY) {
      traces.push({ type: 'scatter', mode: 'lines', x: spectrumData.x, y: processedY, name: 'Processed', line: { width: 1.5, color: '#1f77b4' } });
    }
    if (baseline) {
      traces.push({ type: 'scatter', mode: 'lines', x: spectrumData.x, y: baseline, name: 'Baseline', line: { width: 1, color: '#d62728', dash: 'dash' } });
    }
    if (peaks.length > 0) {
      traces.push({
        type: 'scatter', mode: 'markers',
        x: peaks.map(p => p.x), y: peaks.map(p => p.y),
        name: 'Peaks', marker: { size: 8, color: '#e74c3c', symbol: 'triangle-up' },
      });
    }
    return { traces, layout: { height: 400, xaxis: { title: 'X' }, yaxis: { title: 'Intensity' } } };
  }, [spectrumData, processedY, baseline, peaks]);

  const currentSchema = fitSchema || previewSchema;

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)', color: 'var(--ink)', fontSize: 13 }}>
      {/* Left sidebar */}
      <div style={{ width: 280, borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', background: 'var(--sidebar-bg)', overflow: 'auto' }}>
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Waves size={14} /> 光谱处理引擎
          </span>
        </div>

        {/* Step indicator */}
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)', display: 'flex', gap: 2 }}>
          {[
            { key: 'import', label: '导入', icon: '1' },
            { key: 'baseline', label: '基线', icon: '2' },
            { key: 'smooth', label: '平滑', icon: '3' },
            { key: 'peaks', label: '寻峰', icon: '4' },
            { key: 'fit', label: '拟合', icon: '5' },
          ].map(s => (
            <div key={s.key} style={{ flex: 1, textAlign: 'center', padding: '3px 0', borderRadius: 3, fontSize: 9, background: step === s.key ? 'var(--accent)20' : 'transparent', color: step === s.key ? 'var(--accent)' : 'var(--mute)', border: step === s.key ? '1px solid var(--accent)' : '1px solid transparent' }}>
              {s.label}
            </div>
          ))}
        </div>

        {/* Spectrum type */}
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>光谱类型</div>
          <select value={spectrumType} onChange={e => setSpectrumType(e.target.value as any)} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }}>
            <option value="raman">Raman</option>
            <option value="xps">XPS</option>
            <option value="ftir">FTIR</option>
          </select>
        </div>

        {/* Import */}
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <button onClick={handleFileImport} style={{ width: '100%', padding: '6px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 11, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
            <Upload size={12} /> 导入光谱数据
          </button>
          {spectrumData && <div style={{ marginTop: 4, fontSize: 10, color: 'var(--accent)' }}>{spectrumData.label} ({spectrumData.x.length}pts)</div>}
        </div>

        {/* Baseline */}
        {spectrumData && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>基线校正</div>
            <select value={baselineMethod} onChange={e => setBaselineMethod(e.target.value)} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', marginBottom: 4 }}>
              <option value="als">ALS (非对称最小二乘)</option>
              <option value="snip">SNIP</option>
              <option value="poly">多项式拟合</option>
              {spectrumType === 'xps' && <option value="shirley">Shirley (XPS)</option>}
            </select>
            <button onClick={handleBaseline} disabled={phase === 'processing'} style={{ width: '100%', padding: '4px 0', borderRadius: 4, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 10 }}>
              {baseline ? '重新校正' : '执行基线校正'}
            </button>
          </div>
        )}

        {/* Smooth */}
        {processedY && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>平滑滤波</div>
            <select value={smoothMethod} onChange={e => setSmoothMethod(e.target.value)} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', marginBottom: 4 }}>
              <option value="savgol">Savitzky-Golay</option>
              <option value="moving_avg">移动平均</option>
            </select>
            <button onClick={handleSmooth} disabled={phase === 'processing'} style={{ width: '100%', padding: '4px 0', borderRadius: 4, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 10 }}>
              执行平滑
            </button>
          </div>
        )}

        {/* Peak detection */}
        {processedY && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>寻峰 ({peaks.length} 个峰)</div>
            <button onClick={handleFindPeaks} disabled={phase === 'processing'} style={{ width: '100%', padding: '4px 0', borderRadius: 4, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 10 }}>
              自动寻峰
            </button>
          </div>
        )}

        {/* Fitting */}
        {peaks.length > 0 && (
          <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>多峰拟合</div>
            <select value={peakType} onChange={e => setPeakType(e.target.value)} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', marginBottom: 4 }}>
              <option value="pvoigt">Pseudo-Voigt</option>
              <option value="gaussian">Gaussian</option>
              <option value="lorentzian">Lorentzian</option>
            </select>
            <button onClick={handleFit} disabled={phase === 'processing'} style={{ width: '100%', padding: '4px 0', borderRadius: 4, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 10 }}>
              执行拟合
            </button>
            {fitResult && (
              <div style={{ marginTop: 4, fontSize: 10, color: 'var(--accent)' }}>
                R² = {fitResult.r_squared} | {fitResult.n_peaks} 峰
              </div>
            )}
          </div>
        )}

        {error && <div style={{ padding: 8, color: '#dc2626', fontSize: 10 }}>{error}</div>}
      </div>

      {/* Center: Chart */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <div style={{ flex: 1, minHeight: 0 }}>
          <PlotSchemaRenderer schema={currentSchema} height="100%" />
        </div>
      </div>
    </div>
  );
};
