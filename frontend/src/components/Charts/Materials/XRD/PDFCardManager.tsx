import React, { useCallback, useRef, useState } from 'react';
import { Trash2 } from 'lucide-react';
import { usePlotStore } from '@/store/plotStore';
import { plotApi } from '@/services/plotService';

const CARD_COLORS = ['#d62728', '#1f77b4', '#2ca02c', '#9467bd', '#ff7f0e'];

export const PDFCardManager: React.FC = () => {
  const { pdfCards, addPdfCard, removePdfCard, clearPdfCards } = usePlotStore();
  const [manualInput, setManualInput] = useState('');
  const [cardId, setCardId] = useState('');
  const cifRef = useRef<HTMLInputElement>(null);
  const jadeRef = useRef<HTMLInputElement>(null);

  // Parse manual input: "2theta intensity" per line
  const handleManualAdd = useCallback(() => {
    if (!manualInput.trim()) return;
    const lines = manualInput.trim().split('\n');
    const twoTheta: number[] = [];
    const intensity: number[] = [];
    for (const line of lines) {
      const parts = line.trim().split(/[\t,;\s]+/).filter(Boolean);
      if (parts.length >= 2) {
        const x = parseFloat(parts[0]);
        const y = parseFloat(parts[1]);
        if (!isNaN(x) && !isNaN(y)) {
          twoTheta.push(x);
          intensity.push(y);
        }
      }
    }
    if (twoTheta.length > 0) {
      const color = CARD_COLORS[pdfCards.length % CARD_COLORS.length];
      addPdfCard({ two_theta: twoTheta, intensity, card_id: cardId || `PDF#${pdfCards.length + 1}`, color });
      setManualInput('');
      setCardId('');
    }
  }, [manualInput, cardId, pdfCards.length, addPdfCard]);

  // CIF file import
  const handleCifImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await plotApi.parseCif(file);
      if (result.error) {
        alert(result.error);
        return;
      }
      const color = CARD_COLORS[pdfCards.length % CARD_COLORS.length];
      addPdfCard({
        two_theta: result.two_theta,
        intensity: result.intensity,
        card_id: result.card_info?.formula || file.name.replace('.cif', ''),
        color,
        hkl: result.hkl,
      });
    } catch (err) {
      alert('CIF解析失败: ' + (err instanceof Error ? err.message : String(err)));
    }
    e.target.value = '';
  }, [pdfCards.length, addPdfCard]);

  // Jade txt import
  const handleJadeImport = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const result = await plotApi.parseJade(file);
      const color = CARD_COLORS[pdfCards.length % CARD_COLORS.length];
      addPdfCard({
        two_theta: result.two_theta,
        intensity: result.intensity,
        card_id: file.name.replace(/\.[^.]+$/, ''),
        color,
        hkl: result.hkl,
      });
    } catch (err) {
      alert('Jade文件解析失败: ' + (err instanceof Error ? err.message : String(err)));
    }
    e.target.value = '';
  }, [pdfCards.length, addPdfCard]);

  return (
    <div style={{ padding: 8, borderBottom: '1px solid var(--border-color)' }}>
      <div style={{ fontSize: 11, color: 'var(--mute)', marginBottom: 6 }}>PDF 标准卡片</div>

      {/* Import buttons */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
        <button onClick={() => cifRef.current?.click()} title="从CIF文件解析" style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>
          CIF
        </button>
        <button onClick={() => jadeRef.current?.click()} title="从Jade txt导入" style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>
          Jade
        </button>
        <button onClick={() => setManualInput('20.5 30\n26.6 100\n36.5 50')} title="手动输入" style={{ flex: 1, padding: '4px 0', borderRadius: 4, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>
          手动
        </button>
      </div>
      <input ref={cifRef} type="file" accept=".cif" onChange={handleCifImport} style={{ display: 'none' }} />
      <input ref={jadeRef} type="file" accept=".txt,.csv" onChange={handleJadeImport} style={{ display: 'none' }} />

      {/* Manual input */}
      {manualInput !== '' && (
        <div style={{ marginBottom: 6 }}>
          <input value={cardId} onChange={(e) => setCardId(e.target.value)} placeholder="卡片编号 (如 PDF#46-1045)" style={{ width: '100%', padding: '3px 6px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', marginBottom: 3 }} />
          <textarea value={manualInput} onChange={(e) => setManualInput(e.target.value)} placeholder="2θ Intensity (每行一组)" style={{ width: '100%', height: 60, padding: '3px 6px', fontSize: 10, borderRadius: 3, border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--ink)', resize: 'vertical' }} />
          <div style={{ display: 'flex', gap: 4, marginTop: 3 }}>
            <button onClick={handleManualAdd} style={{ flex: 1, padding: '3px 0', borderRadius: 3, border: 'none', background: 'var(--accent)', color: '#fff', cursor: 'pointer', fontSize: 10 }}>添加</button>
            <button onClick={() => setManualInput('')} style={{ padding: '3px 8px', borderRadius: 3, border: '1px solid var(--border-color)', background: 'transparent', color: 'var(--ink)', cursor: 'pointer', fontSize: 10 }}>取消</button>
          </div>
        </div>
      )}

      {/* Card list */}
      {pdfCards.length > 0 && (
        <div style={{ maxHeight: 100, overflow: 'auto' }}>
          {pdfCards.map((card, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 0', fontSize: 11 }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: card.color, flexShrink: 0 }} />
              <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{card.card_id}</span>
              <span style={{ color: 'var(--mute)', fontSize: 9 }}>{card.two_theta.length}peaks</span>
              <button onClick={() => removePdfCard(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ef4444', padding: 0 }}><Trash2 size={10} /></button>
            </div>
          ))}
        </div>
      )}
      {pdfCards.length > 0 && (
        <button onClick={clearPdfCards} style={{ marginTop: 3, fontSize: 9, color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>清除全部</button>
      )}
    </div>
  );
};
