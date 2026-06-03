import React, { useState, useCallback } from 'react';

interface AxisLabelEditorProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
}

const SUPERSCRIPTS: Record<string, string> = { '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾', 'n': 'ⁿ' };
const SUBSCRIPTS: Record<string, string> = { '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉', '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎' };

export const AxisLabelEditor: React.FC<AxisLabelEditorProps> = ({ value, onChange, label = '轴标签' }) => {
  const [mode, setMode] = useState<'normal' | 'sup' | 'sub'>('normal');

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.ctrlKey && e.key === 'ArrowUp') {
      e.preventDefault();
      setMode('sup');
    } else if (e.ctrlKey && e.key === 'ArrowDown') {
      e.preventDefault();
      setMode('sub');
    } else if (e.key === 'Escape' || (e.ctrlKey && e.key === 'ArrowRight')) {
      setMode('normal');
    }
  }, []);

  const handleInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target;
    const newValue = input.value;
    if (mode === 'sup' || mode === 'sub') {
      const map = mode === 'sup' ? SUPERSCRIPTS : SUBSCRIPTS;
      const lastChar = newValue.slice(-1);
      const converted = map[lastChar] || lastChar;
      onChange(newValue.slice(0, -1) + converted);
    } else {
      onChange(newValue);
    }
  }, [mode, onChange]);

  return (
    <div>
      <span style={{ fontSize: 9, color: 'var(--mute)', display: 'block', marginBottom: 2 }}>{label}</span>
      <div style={{ display: 'flex', gap: 2, alignItems: 'center' }}>
        <input
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          style={{ flex: 1, padding: '2px 4px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)' }}
          placeholder="输入标签..."
        />
        <button
          onClick={() => setMode(mode === 'sup' ? 'normal' : 'sup')}
          style={{ padding: '2px 4px', fontSize: 9, borderRadius: 3, border: mode === 'sup' ? '2px solid var(--accent)' : '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer' }}
          title="上标模式 (Ctrl+↑)"
        >X²</button>
        <button
          onClick={() => setMode(mode === 'sub' ? 'normal' : 'sub')}
          style={{ padding: '2px 4px', fontSize: 9, borderRadius: 3, border: mode === 'sub' ? '2px solid var(--accent)' : '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer' }}
          title="下标模式 (Ctrl+↓)"
        >X₂</button>
      </div>
      {mode !== 'normal' && (
        <div style={{ fontSize: 8, color: 'var(--accent)', marginTop: 1 }}>
          {mode === 'sup' ? '上标' : '下标'}模式 — 输入字符自动转换，Esc退出
        </div>
      )}
    </div>
  );
};
