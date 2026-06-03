import React from 'react';
import { Settings } from 'lucide-react';
import { usePlotStore } from '@/store/plotStore';

export const XRDConfigPanel: React.FC = () => {
  const { xrdConfig, updateXrdConfig, currentThemeId, setCurrentThemeId } = usePlotStore();

  return (
    <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
      <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 4 }}>
        <Settings size={12} /> 绘图参数
      </div>

      {/* Y offset */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, marginBottom: 4 }}>
        <span style={{ color: 'var(--mute)', whiteSpace: 'nowrap', minWidth: 50 }}>Y偏移量</span>
        <input type="range" min={0.5} max={3} step={0.1} value={xrdConfig.y_offset} onChange={(e) => updateXrdConfig({ y_offset: parseFloat(e.target.value) })} style={{ flex: 1, height: 3, accentColor: 'var(--accent)' }} />
        <span style={{ color: 'var(--mute)', minWidth: 24, textAlign: 'right' }}>{xrdConfig.y_offset.toFixed(1)}</span>
      </div>

      {/* 2θ range */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 9, color: 'var(--mute)' }}>2θ Min</span>
          <input type="number" value={xrdConfig.two_theta_range[0]} onChange={(e) => updateXrdConfig({ two_theta_range: [parseFloat(e.target.value) || 0, xrdConfig.two_theta_range[1]] })} style={{ width: '100%', padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }} />
        </div>
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 9, color: 'var(--mute)' }}>2θ Max</span>
          <input type="number" value={xrdConfig.two_theta_range[1]} onChange={(e) => updateXrdConfig({ two_theta_range: [xrdConfig.two_theta_range[0], parseFloat(e.target.value) || 90] })} style={{ width: '100%', padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }} />
        </div>
      </div>

      {/* Line width */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, marginBottom: 4 }}>
        <span style={{ color: 'var(--mute)', whiteSpace: 'nowrap', minWidth: 50 }}>线宽</span>
        <input type="range" min={0.3} max={3} step={0.1} value={xrdConfig.line_width} onChange={(e) => updateXrdConfig({ line_width: parseFloat(e.target.value) })} style={{ flex: 1, height: 3, accentColor: 'var(--accent)' }} />
        <span style={{ color: 'var(--mute)', minWidth: 24, textAlign: 'right' }}>{xrdConfig.line_width.toFixed(1)}</span>
      </div>

      {/* Stick width */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, marginBottom: 4 }}>
        <span style={{ color: 'var(--mute)', whiteSpace: 'nowrap', minWidth: 50 }}>棒图线宽</span>
        <input type="range" min={0.5} max={4} step={0.5} value={xrdConfig.stick_width} onChange={(e) => updateXrdConfig({ stick_width: parseFloat(e.target.value) })} style={{ flex: 1, height: 3, accentColor: 'var(--accent)' }} />
        <span style={{ color: 'var(--mute)', minWidth: 24, textAlign: 'right' }}>{xrdConfig.stick_width.toFixed(1)}</span>
      </div>

      {/* Toggles */}
      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, cursor: 'pointer', marginBottom: 3 }}>
        <input type="checkbox" checked={xrdConfig.show_hkl} onChange={(e) => updateXrdConfig({ show_hkl: e.target.checked })} />
        显示 hkl 标注
      </label>
      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, cursor: 'pointer', marginBottom: 3 }}>
        <input type="checkbox" checked={xrdConfig.show_y_ticks} onChange={(e) => updateXrdConfig({ show_y_ticks: e.target.checked })} />
        显示 Y 轴刻度
      </label>

      {/* Theme selector */}
      <div style={{ marginTop: 6 }}>
        <span style={{ fontSize: 9, color: 'var(--mute)', display: 'block', marginBottom: 3 }}>期刊主题</span>
        <select value={currentThemeId} onChange={(e) => setCurrentThemeId(e.target.value)} style={{ width: '100%', padding: '3px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }}>
          <option value="default">默认学术</option>
          <option value="nature">Nature</option>
          <option value="science">Science</option>
          <option value="acs">ACS</option>
          <option value="rsc">RSC</option>
          <option value="elsevier">Elsevier</option>
        </select>
      </div>
    </div>
  );
};
