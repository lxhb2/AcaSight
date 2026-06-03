import React, { useCallback, useState } from 'react';
import { Settings, Palette } from 'lucide-react';
import { PlotSchemaRenderer } from '@/components/Charts/Common/PlotSchemaRenderer';
import type { PlotSchema } from '@/types/plot';

interface ChartEditorProps {
  schema: PlotSchema | null;
  height?: string | number;
  onSchemaChange?: (schema: PlotSchema) => void;
}

export const ChartEditor: React.FC<ChartEditorProps> = ({ schema, height = '100%', onSchemaChange }) => {
  const [selectedTrace, setSelectedTrace] = useState<number | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  const handleElementClick = useCallback((traceIndex: number, _pointIndex: number) => {
    setSelectedTrace(traceIndex);
    setShowEditor(true);
  }, []);

  const handlePropertyChange = useCallback((key: string, value: any) => {
    if (!schema || selectedTrace === null || !onSchemaChange) return;
    const traces = [...schema.traces];
    const trace = { ...traces[selectedTrace] };
    if (key === 'line.color' && trace.line) {
      trace.line = { ...trace.line, color: value };
    } else if (key === 'line.width' && trace.line) {
      trace.line = { ...trace.line, width: value };
    } else if (key === 'name') {
      trace.name = value;
    }
    traces[selectedTrace] = trace;
    onSchemaChange({ ...schema, traces });
  }, [schema, selectedTrace, onSchemaChange]);

  const selectedTraceData = schema && selectedTrace !== null ? schema.traces[selectedTrace] : null;

  return (
    <div style={{ display: 'flex', height: '100%', position: 'relative' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <PlotSchemaRenderer schema={schema} height={height} onElementClick={handleElementClick} />
      </div>

      {/* Editor toggle button */}
      <button
        onClick={() => setShowEditor(!showEditor)}
        style={{
          position: 'absolute', top: 8, right: 8, zIndex: 10,
          width: 28, height: 28, borderRadius: 4,
          border: '1px solid var(--border-color)', background: 'var(--bg-primary)',
          color: 'var(--ink)', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}
        title="Toggle Editor"
      >
        <Settings size={14} />
      </button>

      {/* Property panel */}
      {showEditor && selectedTraceData && (
        <div style={{
          width: 220, borderLeft: '1px solid var(--border-color)',
          background: 'var(--sidebar-bg)', overflow: 'auto', padding: 8,
          fontSize: 11, color: 'var(--ink)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Palette size={12} /> 属性编辑
          </div>

          <div style={{ marginBottom: 6 }}>
            <span style={{ color: 'var(--mute)', fontSize: 9 }}>名称</span>
            <input
              value={selectedTraceData.name || ''}
              onChange={e => handlePropertyChange('name', e.target.value)}
              style={{ width: '100%', padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }}
            />
          </div>

          {selectedTraceData.line && (
            <>
              <div style={{ marginBottom: 6 }}>
                <span style={{ color: 'var(--mute)', fontSize: 9 }}>线条颜色</span>
                <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  <input type="color" value={selectedTraceData.line.color || '#333'} onChange={e => handlePropertyChange('line.color', e.target.value)} style={{ width: 24, height: 20, border: 'none', cursor: 'pointer' }} />
                  <span style={{ fontSize: 9, color: 'var(--mute)' }}>{selectedTraceData.line.color}</span>
                </div>
              </div>
              <div style={{ marginBottom: 6 }}>
                <span style={{ color: 'var(--mute)', fontSize: 9 }}>线宽</span>
                <input type="range" min={0.5} max={5} step={0.5} value={selectedTraceData.line.width || 1} onChange={e => handlePropertyChange('line.width', parseFloat(e.target.value))} style={{ width: '100%', height: 3, accentColor: 'var(--accent)' }} />
              </div>
            </>
          )}

          <div style={{ marginTop: 12, fontSize: 9, color: 'var(--mute)' }}>
            点击图表元素选中后编辑属性
          </div>
        </div>
      )}
    </div>
  );
};
