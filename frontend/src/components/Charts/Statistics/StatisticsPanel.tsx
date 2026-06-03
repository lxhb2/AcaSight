import React, { useState, useCallback } from 'react';
import { BarChart3, Grid3x3, Target } from 'lucide-react';
import { plotApi } from '@/services/plotService';
import { PlotSchemaRenderer } from '@/components/Charts/Common/PlotSchemaRenderer';

type StatTab = 'anova' | 'correlation' | 'pca';

export const StatisticsPanel: React.FC = () => {
  const [tab, setTab] = useState<StatTab>('anova');
  const [schema, setSchema] = useState<any>(null);
  const [phase, setPhase] = useState<'idle' | 'processing'>('idle');
  const [error, setError] = useState('');

  // ANOVA state
  const [anovaGroups, setAnovaGroups] = useState('[{"name":"Control","mean":85.2,"sd":3.1,"n":5},{"name":"Treatment A","mean":92.1,"sd":2.8,"n":5},{"name":"Treatment B","mean":88.5,"sd":4.2,"n":5}]');
  const [anovaComparisons, setAnovaComparisons] = useState('[{"group1":"Control","group2":"Treatment A","significant":true,"letters":"a"},{"group1":"Control","group2":"Treatment B","significant":false,"letters":"ab"},{"group1":"Treatment A","group2":"Treatment B","significant":true,"letters":"b"}]');

  // Correlation state
  const [corrVariables, setCorrVariables] = useState('["Temp","Time","Yield","Purity"]');
  const [corrMatrix, setCorrMatrix] = useState('[[1,0.85,0.72,-0.31],[0.85,1,0.64,-0.28],[0.72,0.64,1,-0.45],[-0.31,-0.28,-0.45,1]]');

  // PCA state
  const [pcaScores, setPcaScores] = useState('[[1.2,0.5],[2.1,-0.3],[-0.8,1.1],[0.5,0.8],[-1.5,-0.7],[0.3,-1.2]]');
  const [pcaLoadings, setPcaLoadings] = useState('[[0.7,0.3],[0.6,-0.5],[0.5,0.6],[-0.3,0.8]]');
  const [pcaVariance, setPcaVariance] = useState('[65.3,22.1]');
  const [pcaVarNames, setPcaVarNames] = useState('["Temp","Time","Yield","Purity"]');
  const [pcaGroups, setPcaGroups] = useState('["A","A","B","B","C","C"]');

  const handleGenerate = useCallback(async () => {
    setPhase('processing');
    setError('');
    try {
      if (tab === 'anova') {
        const res = await plotApi.generateAnovaBar(JSON.parse(anovaGroups), JSON.parse(anovaComparisons), {});
        setSchema(res.schema);
      } else if (tab === 'correlation') {
        const res = await plotApi.generateCorrelationHeatmap(JSON.parse(corrVariables), JSON.parse(corrMatrix), null, {});
        setSchema(res.schema);
      } else if (tab === 'pca') {
        const res = await plotApi.generatePCABiplot(JSON.parse(pcaScores), JSON.parse(pcaLoadings), JSON.parse(pcaVariance), JSON.parse(pcaGroups), JSON.parse(pcaVarNames), {});
        setSchema(res.schema);
      }
    } catch (err) {
      setError('生成失败: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setPhase('idle');
    }
  }, [tab, anovaGroups, anovaComparisons, corrVariables, corrMatrix, pcaScores, pcaLoadings, pcaVariance, pcaVarNames, pcaGroups]);

  const handleExport = useCallback(async (format: string) => {
    if (!schema) return;
    try {
      const result = await plotApi.exportPlot(schema, format);
      const a = document.createElement('a');
      a.href = result.image_url;
      a.download = `stats_${tab}.${format}`;
      a.click();
    } catch (err) { setError('导出失败'); }
  }, [schema, tab]);

  const tabs: { key: StatTab; label: string; icon: React.ReactNode }[] = [
    { key: 'anova', label: 'ANOVA', icon: <BarChart3 size={12} /> },
    { key: 'correlation', label: '相关热力图', icon: <Grid3x3 size={12} /> },
    { key: 'pca', label: 'PCA', icon: <Target size={12} /> },
  ];

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--bg-primary)', color: 'var(--ink)', fontSize: 13 }}>
      {/* Left sidebar */}
      <div style={{ width: 300, borderRight: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', background: 'var(--sidebar-bg)', overflow: 'auto' }}>
        <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: 12, fontWeight: 600 }}>统计分析</span>
        </div>

        {/* Tab selector */}
        <div style={{ display: 'flex', gap: 2, padding: 8, borderBottom: '1px solid var(--border-color)' }}>
          {tabs.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: tab === t.key ? '2px solid var(--accent)' : '1px solid var(--border-color)', background: tab === t.key ? 'var(--accent)20' : 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 3 }}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={{ padding: 8, flex: 1, overflow: 'auto' }}>
          {tab === 'anova' && (
            <>
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>分组数据 (JSON)</div>
              <textarea value={anovaGroups} onChange={e => setAnovaGroups(e.target.value)} style={{ width: '100%', height: 80, padding: 4, fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4, marginTop: 6 }}>比较结果 (JSON)</div>
              <textarea value={anovaComparisons} onChange={e => setAnovaComparisons(e.target.value)} style={{ width: '100%', height: 60, padding: 4, fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
            </>
          )}
          {tab === 'correlation' && (
            <>
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>变量名 (JSON)</div>
              <textarea value={corrVariables} onChange={e => setCorrVariables(e.target.value)} style={{ width: '100%', height: 30, padding: 4, fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4, marginTop: 6 }}>相关矩阵 (JSON)</div>
              <textarea value={corrMatrix} onChange={e => setCorrMatrix(e.target.value)} style={{ width: '100%', height: 80, padding: 4, fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
            </>
          )}
          {tab === 'pca' && (
            <>
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4 }}>PC Scores (JSON)</div>
              <textarea value={pcaScores} onChange={e => setPcaScores(e.target.value)} style={{ width: '100%', height: 50, padding: 4, fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4, marginTop: 4 }}>Loadings (JSON)</div>
              <textarea value={pcaLoadings} onChange={e => setPcaLoadings(e.target.value)} style={{ width: '100%', height: 40, padding: 4, fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4, marginTop: 4 }}>方差解释率 (%)</div>
              <input value={pcaVariance} onChange={e => setPcaVariance(e.target.value)} style={{ width: '100%', padding: '2px 4px', fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }} />
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4, marginTop: 4 }}>变量名</div>
              <input value={pcaVarNames} onChange={e => setPcaVarNames(e.target.value)} style={{ width: '100%', padding: '2px 4px', fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }} />
              <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 4, marginTop: 4 }}>分组标签</div>
              <input value={pcaGroups} onChange={e => setPcaGroups(e.target.value)} style={{ width: '100%', padding: '2px 4px', fontSize: 9, fontFamily: 'monospace', borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }} />
            </>
          )}
        </div>

        {/* Generate & Export */}
        <div style={{ padding: 8, borderTop: '1px solid var(--border-color)' }}>
          <button onClick={handleGenerate} disabled={phase === 'processing'} style={{ width: '100%', padding: '8px 0', borderRadius: 6, border: 'none', background: phase === 'processing' ? 'var(--mute)' : 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
            {phase === 'processing' ? '生成中...' : '生成图表'}
          </button>
          {schema && (
            <div style={{ display: 'flex', gap: 4, marginTop: 6 }}>
              {['png', 'svg', 'pdf'].map(fmt => (
                <button key={fmt} onClick={() => handleExport(fmt)} style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>{fmt.toUpperCase()}</button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Center: Chart */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {error && <div style={{ padding: '6px 12px', background: '#fef2f2', color: '#dc2626', fontSize: 11 }}>{error}</div>}
        <div style={{ flex: 1, minHeight: 0 }}>
          <PlotSchemaRenderer schema={schema} height="100%" />
        </div>
      </div>
    </div>
  );
};
