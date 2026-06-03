import React from 'react';
import { Eye, EyeOff, GripVertical } from 'lucide-react';
import type { PlotSchema } from '@/types/plot';

interface LayerManagerProps {
  schema: PlotSchema | null;
  onSchemaChange?: (schema: PlotSchema) => void;
}

export const LayerManager: React.FC<LayerManagerProps> = ({ schema, onSchemaChange }) => {
  if (!schema?.traces?.length) {
    return <div style={{ padding: 8, fontSize: 10, color: 'var(--mute)' }}>暂无图层</div>;
  }

  const toggleVisibility = (index: number) => {
    if (!onSchemaChange || !schema) return;
    const traces = schema.traces.map((t, i) => {
      if (i === index) {
        return { ...t, visible: t.visible === false ? true : (t.visible === true ? false : true) };
      }
      return t;
    });
    onSchemaChange({ ...schema, traces });
  };

  return (
    <div style={{ padding: 8 }}>
      <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, fontWeight: 600 }}>图层管理</div>
      {schema.traces.map((trace, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '3px 4px',
          borderRadius: 3, marginBottom: 2, fontSize: 10,
          background: trace.visible === false ? 'var(--bg-secondary)' : 'transparent',
          opacity: trace.visible === false ? 0.5 : 1,
        }}>
          <GripVertical size={10} style={{ color: 'var(--mute)', cursor: 'grab' }} />
          <span style={{
            width: 8, height: 8, borderRadius: 2, flexShrink: 0,
            background: (trace as any).line?.color || (trace as any).marker?.color || '#999',
          }} />
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {trace.name || `Trace ${i + 1}`}
          </span>
          <button onClick={() => toggleVisibility(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--ink)' }}>
            {trace.visible === false ? <EyeOff size={10} /> : <Eye size={10} />}
          </button>
        </div>
      ))}
    </div>
  );
};
