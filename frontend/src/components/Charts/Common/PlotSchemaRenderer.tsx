import React, { useMemo, useCallback, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import type { PlotSchema } from '@/types/plot';

const Plot = createPlotlyComponent(Plotly);

interface PlotSchemaRendererProps {
  schema: PlotSchema | null;
  onElementClick?: (traceIndex: number, pointIndex: number) => void;
  height?: string | number;
}

export const PlotSchemaRenderer: React.FC<PlotSchemaRendererProps> = ({
  schema,
  onElementClick,
  height = '100%',
}) => {
  const chartRef = useRef<any>(null);

  const traces = useMemo(() => {
    if (!schema?.traces) return [];
    return schema.traces.map((t) => {
      const { _row, _col, ...rest } = t as any;
      return rest;
    });
  }, [schema]);

  const layout = useMemo(() => {
    if (!schema?.layout) return {};
    const layout = { ...schema.layout };
    // Handle subplots
    if (schema.subplots) {
      layout.grid = {
        rows: schema.subplots.rows,
        columns: schema.subplots.cols,
        rowheights: schema.subplots.row_heights,
        shared_xaxes: schema.subplots.shared_xaxes,
        shared_yaxes: schema.subplots.shared_yaxes,
        subplots: undefined as any,
      };
    }
    // Add annotations
    if (schema.annotations) {
      layout.annotations = schema.annotations;
    }
    return layout;
  }, [schema]);

  const config = useMemo(
    () => ({
      displayModeBar: true as const,
      displaylogo: false,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d'],
      responsive: true,
    }),
    []
  );

  const handleClick = useCallback(
    (eventData: any) => {
      if (!onElementClick || !eventData?.points?.length) return;
      const point = eventData.points[0];
      onElementClick(point.curveNumber, point.pointNumber);
    },
    [onElementClick]
  );

  if (!schema) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height, color: 'var(--mute)' }}>
        <p>暂无图表数据</p>
      </div>
    );
  }

  return (
    <Plot
      ref={chartRef}
      data={traces}
      layout={layout}
      config={config}
      style={{ width: '100%', height }}
      useResizeHandler
      onClick={handleClick}
    />
  );
};
