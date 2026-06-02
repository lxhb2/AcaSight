import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  PenTool, Loader2, AlertTriangle, Download, RotateCcw,
  Wand2, Scissors, Replace, Wrench, CheckCircle2, XCircle,
  ChevronDown, ChevronUp, ZoomIn, ZoomOut, MousePointer2,
  Code, Image as ImageIcon, Copy,
} from 'lucide-react';
import {
  figureEditApi,
  type MethodToSvgResult,
  type SegmentResult,
  type FigureEditStatus,
} from '@/services/api';

type EditorMode = 'select' | 'pan';
type EditorTab = 'generate' | 'edit' | 'code';

interface SelectedElement {
  id: string;
  tag: string;
  attributes: Record<string, string>;
  index: number;
}

export const SvgEditorPanel: React.FC = () => {
  const { t } = useTranslation();
  const svgContainerRef = useRef<HTMLDivElement>(null);

  const [activeTab, setActiveTab] = useState<EditorTab>('generate');
  const [methodText, setMethodText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [svgResult, setSvgResult] = useState<MethodToSvgResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [serviceStatus, setServiceStatus] = useState<FigureEditStatus | null>(null);

  const [editorMode, setEditorMode] = useState<EditorMode>('select');
  const [selectedElement, setSelectedElement] = useState<SelectedElement | null>(null);
  const [zoom, setZoom] = useState(1);

  const [isSegmenting, setIsSegmenting] = useState(false);
  const [segmentResult, setSegmentResult] = useState<SegmentResult | null>(null);

  const [isFixing, setIsFixing] = useState(false);
  const [fixResult, setFixResult] = useState<{ svg_code: string; was_valid: boolean; errors: string[] } | null>(null);

  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({ settings: false, status: false });

  useEffect(() => {
    figureEditApi.getStatus().then(res => {
      if (res.data) setServiceStatus(res.data);
    }).catch(() => {});
  }, []);

  const toggleSection = useCallback((section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const handleMethodToSvg = useCallback(async () => {
    if (!methodText.trim()) return;
    setIsGenerating(true);
    setError(null);
    setSvgResult(null);
    setSegmentResult(null);
    setFixResult(null);
    setSelectedElement(null);

    try {
      const res = await figureEditApi.methodToSvg(methodText, {
        samPrompts: 'icon',
        placeholderMode: 'label',
        minScore: 0.5,
        mergeThreshold: 0.9,
        optimizeIterations: 2,
      });
      if (res.success && res.data) {
        setSvgResult(res.data);
        setSvgContent(res.data.svg_content);
        setActiveTab('edit');
      } else {
        setError(t('svgEditor.generateFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setIsGenerating(false);
    }
  }, [methodText, t]);

  const handleSegment = useCallback(async () => {
    if (!svgContent) return;
    setIsSegmenting(true);
    setError(null);

    try {
      const svgBlob = new Blob([svgContent], { type: 'image/svg+xml' });
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error('Canvas not available');

      const img = new Image();
      const url = URL.createObjectURL(svgBlob);

      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = reject;
        img.src = url;
      });

      canvas.width = img.naturalWidth || 800;
      canvas.height = img.naturalHeight || 600;
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);

      const base64 = canvas.toDataURL('image/png').split(',')[1];
      const res = await figureEditApi.segment(base64, 'icon', 0.5);

      if (res.success && res.data) {
        setSegmentResult(res.data);
      } else {
        setError(t('svgEditor.segmentFailed'));
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setIsSegmenting(false);
    }
  }, [svgContent, t]);

  const handleFixSvg = useCallback(async () => {
    if (!svgContent) return;
    setIsFixing(true);
    setError(null);

    try {
      const res = await figureEditApi.fixSvg(svgContent);
      if (res.success && res.data) {
        setFixResult(res.data);
        if (!res.data.was_valid) {
          setSvgContent(res.data.svg_code);
        }
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setIsFixing(false);
    }
  }, [svgContent]);

  const handleSvgClick = useCallback((e: React.MouseEvent) => {
    const target = e.target as SVGElement;
    if (!target || !svgContainerRef.current) return;

    const svgEl = svgContainerRef.current.querySelector('svg');
    if (!svgEl) return;

    if (target === svgEl) {
      setSelectedElement(null);
      return;
    }

    const allElements = svgEl.querySelectorAll('*');
    let idx = 0;
    for (const el of allElements) {
      if (el === target) {
        const attrs: Record<string, string> = {};
        for (const attr of Array.from(target.attributes)) {
          attrs[attr.name] = attr.value;
        }
        setSelectedElement({
          id: attrs.id || `el-${idx}`,
          tag: target.tagName,
          attributes: attrs,
          index: idx,
        });
        break;
      }
      idx++;
    }
  }, []);

  const handleExportSvg = useCallback(() => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'figure.svg';
    a.click();
    URL.revokeObjectURL(url);
  }, [svgContent]);

  const handleExportPng = useCallback(() => {
    if (!svgContent) return;
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    img.onload = () => {
      canvas.width = img.naturalWidth * 2;
      canvas.height = img.naturalHeight * 2;
      ctx.scale(2, 2);
      ctx.drawImage(img, 0, 0);
      URL.revokeObjectURL(url);

      canvas.toBlob(pngBlob => {
        if (!pngBlob) return;
        const pngUrl = URL.createObjectURL(pngBlob);
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = 'figure.png';
        a.click();
        URL.revokeObjectURL(pngUrl);
      });
    };
    img.src = url;
  }, [svgContent]);

  const handleCopySvgCode = useCallback(() => {
    if (!svgContent) return;
    navigator.clipboard.writeText(svgContent);
  }, [svgContent]);

  const handleReset = useCallback(() => {
    setSvgContent(null);
    setSvgResult(null);
    setSegmentResult(null);
    setFixResult(null);
    setSelectedElement(null);
    setError(null);
    setActiveTab('generate');
  }, []);

  const handleSvgCodeEdit = useCallback((newCode: string) => {
    setSvgContent(newCode);
    setSelectedElement(null);
    setFixResult(null);
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflow: 'auto', padding: '0 16px 16px' }}>
        {/* Tab Bar */}
        <div style={{ display: 'flex', gap: 0, marginTop: 12, borderBottom: '1px solid var(--hairline)' }}>
          {([
            { id: 'generate' as EditorTab, icon: <Wand2 size={13} />, labelKey: 'svgEditor.tabGenerate' },
            { id: 'edit' as EditorTab, icon: <PenTool size={13} />, labelKey: 'svgEditor.tabEdit' },
            { id: 'code' as EditorTab, icon: <Code size={13} />, labelKey: 'svgEditor.tabCode' },
          ]).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              disabled={tab.id !== 'generate' && !svgContent}
              style={{
                flex: 1, padding: '8px 0', fontSize: 11, fontWeight: activeTab === tab.id ? 600 : 400,
                color: activeTab === tab.id ? 'var(--accent)' : (svgContent || tab.id === 'generate') ? 'var(--body)' : 'var(--mute)',
                background: 'none', border: 'none',
                borderBottom: activeTab === tab.id ? '2px solid var(--accent)' : '2px solid transparent',
                cursor: (svgContent || tab.id === 'generate') ? 'pointer' : 'not-allowed',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                transition: 'all 0.15s', opacity: (svgContent || tab.id === 'generate') ? 1 : 0.4,
              }}
            >
              {tab.icon} {t(tab.labelKey)}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-soft)', border: '1px solid var(--danger)', fontSize: 11, color: 'var(--danger)', display: 'flex', alignItems: 'flex-start', gap: 6 }}>
            <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Generate Tab */}
        {activeTab === 'generate' && (
          <div style={{ marginTop: 12 }}>
            <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
              {t('svgEditor.methodInput')}
            </label>
            <textarea
              value={methodText}
              onChange={e => setMethodText(e.target.value)}
              placeholder={t('svgEditor.methodPlaceholder')}
              rows={6}
              disabled={isGenerating}
              style={{
                width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                background: 'var(--canvas)', border: '1px solid var(--hairline)',
                color: 'var(--ink)', fontSize: 12, resize: 'none',
                outline: 'none', lineHeight: 1.5, fontFamily: 'inherit',
              }}
            />

            {/* Service Status */}
            {serviceStatus && (
              <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 9, padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: serviceStatus.sam3_available ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)', color: serviceStatus.sam3_available ? 'var(--accent)' : 'var(--mute)', border: `1px solid ${serviceStatus.sam3_available ? 'var(--accent)' : 'var(--hairline)'}`, display: 'flex', alignItems: 'center', gap: 3 }}>
                  {serviceStatus.sam3_available ? <CheckCircle2 size={9} /> : <XCircle size={9} />}
                  SAM3 ({serviceStatus.sam3_backend})
                </span>
                {serviceStatus.placeholder_modes.map(m => (
                  <span key={m} style={{ fontSize: 9, padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', color: 'var(--body)', border: '1px solid var(--hairline)' }}>
                    {m}
                  </span>
                ))}
              </div>
            )}

            {/* Advanced Settings */}
            <div style={{ marginTop: 10 }}>
              <button onClick={() => toggleSection('settings')} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', color: 'var(--mute)', cursor: 'pointer', fontSize: 10 }}>
                {expandedSections.settings ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                {t('svgEditor.advancedSettings')}
              </button>
              {expandedSections.settings && (
                <div style={{ marginTop: 6, padding: 10, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: 'var(--body)' }}>{t('svgEditor.placeholderMode')}</span>
                    <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 500 }}>label</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: 'var(--body)' }}>{t('svgEditor.minScore')}</span>
                    <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 500 }}>0.5</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: 'var(--body)' }}>{t('svgEditor.mergeThreshold')}</span>
                    <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 500 }}>0.9</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 10, color: 'var(--body)' }}>{t('svgEditor.optimizeIterations')}</span>
                    <span style={{ fontSize: 10, color: 'var(--accent)', fontWeight: 500 }}>2</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Edit Tab */}
        {activeTab === 'edit' && svgContent && (
          <div style={{ marginTop: 12 }}>
            {/* Editor Toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
              <button
                onClick={() => setEditorMode('select')}
                style={{
                  padding: '4px 8px', borderRadius: 'var(--radius-sm)', fontSize: 10,
                  background: editorMode === 'select' ? 'var(--accent-bg-soft)' : 'transparent',
                  color: editorMode === 'select' ? 'var(--accent)' : 'var(--body)',
                  border: `1px solid ${editorMode === 'select' ? 'var(--accent)' : 'var(--hairline)'}`,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3,
                }}
              >
                <MousePointer2 size={12} /> {t('svgEditor.selectMode')}
              </button>
              <button
                onClick={() => setEditorMode('pan')}
                style={{
                  padding: '4px 8px', borderRadius: 'var(--radius-sm)', fontSize: 10,
                  background: editorMode === 'pan' ? 'var(--accent-bg-soft)' : 'transparent',
                  color: editorMode === 'pan' ? 'var(--accent)' : 'var(--body)',
                  border: `1px solid ${editorMode === 'pan' ? 'var(--accent)' : 'var(--hairline)'}`,
                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3,
                }}
              >
                {t('svgEditor.panMode')}
              </button>
              <div style={{ width: 1, height: 16, background: 'var(--hairline)' }} />
              <button onClick={() => setZoom(z => Math.min(3, z + 0.2))} style={{ padding: '4px 6px', borderRadius: 'var(--radius-sm)', background: 'transparent', border: '1px solid var(--hairline)', cursor: 'pointer', color: 'var(--body)' }}><ZoomIn size={12} /></button>
              <span style={{ fontSize: 10, color: 'var(--mute)', minWidth: 32, textAlign: 'center' }}>{Math.round(zoom * 100)}%</span>
              <button onClick={() => setZoom(z => Math.max(0.3, z - 0.2))} style={{ padding: '4px 6px', borderRadius: 'var(--radius-sm)', background: 'transparent', border: '1px solid var(--hairline)', cursor: 'pointer', color: 'var(--body)' }}><ZoomOut size={12} /></button>
              <div style={{ width: 1, height: 16, background: 'var(--hairline)' }} />
              <button onClick={handleSegment} disabled={isSegmenting || !serviceStatus?.sam3_available} title={t('svgEditor.segmentTooltip')} style={{ padding: '4px 6px', borderRadius: 'var(--radius-sm)', background: 'transparent', border: '1px solid var(--hairline)', cursor: isSegmenting || !serviceStatus?.sam3_available ? 'not-allowed' : 'pointer', color: 'var(--body)', opacity: isSegmenting || !serviceStatus?.sam3_available ? 0.4 : 1, display: 'flex', alignItems: 'center', gap: 3 }}>
                {isSegmenting ? <Loader2 size={12} className="animate-spin" /> : <Scissors size={12} />}
              </button>
              <button onClick={handleFixSvg} disabled={isFixing} title={t('svgEditor.fixTooltip')} style={{ padding: '4px 6px', borderRadius: 'var(--radius-sm)', background: 'transparent', border: '1px solid var(--hairline)', cursor: isFixing ? 'not-allowed' : 'pointer', color: 'var(--body)', opacity: isFixing ? 0.4 : 1, display: 'flex', alignItems: 'center', gap: 3 }}>
                {isFixing ? <Loader2 size={12} className="animate-spin" /> : <Wrench size={12} />}
              </button>
            </div>

            {/* SVG Canvas */}
            <div
              ref={svgContainerRef}
              onClick={editorMode === 'select' ? handleSvgClick : undefined}
              style={{
                border: '1px solid var(--hairline)', borderRadius: 'var(--radius-sm)',
                background: 'var(--canvas-soft)', overflow: 'auto',
                minHeight: 300, maxHeight: 500, cursor: editorMode === 'select' ? 'default' : 'grab',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                padding: 8,
              }}
            >
              <div
                style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.15s ease' }}
                dangerouslySetInnerHTML={{ __html: svgContent || '' }}
              />
            </div>

            {/* Selected Element Info */}
            {selectedElement && (
              <div style={{ marginTop: 8, padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', border: '1px solid var(--accent)', fontSize: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                  <MousePointer2 size={10} style={{ color: 'var(--accent)' }} />
                  <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{t('svgEditor.selectedElement')}</span>
                  <span style={{ color: 'var(--body)' }}>&lt;{selectedElement.tag}&gt;</span>
                  {selectedElement.id && <span style={{ color: 'var(--mute)' }}>#{selectedElement.id}</span>}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {Object.entries(selectedElement.attributes).slice(0, 6).map(([k, v]) => (
                    <span key={k} style={{ fontSize: 9, padding: '1px 4px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', color: 'var(--body)' }}>
                      {k}={v.length > 20 ? v.slice(0, 20) + '...' : v}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Segment Result */}
            {segmentResult && (
              <div style={{ marginTop: 8 }}>
                <button onClick={() => toggleSection('segment')} style={{ display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '6px 0', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', fontSize: 11, fontWeight: 600 }}>
                  <Scissors size={13} style={{ color: 'var(--cyan)' }} />
                  {t('svgEditor.segmentResult')} ({segmentResult.total})
                  {expandedSections.segment ? <ChevronUp size={12} style={{ marginLeft: 'auto' }} /> : <ChevronDown size={12} style={{ marginLeft: 'auto' }} />}
                </button>
                {expandedSections.segment && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    {segmentResult.detections.map((det, i) => (
                      <div key={i} style={{ padding: '4px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', fontSize: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{det.label}</span>
                        <span style={{ color: 'var(--mute)' }}>score: {det.score.toFixed(2)}</span>
                        <span style={{ color: 'var(--mute)' }}>area: {det.area.toFixed(0)}</span>
                        <button style={{ marginLeft: 'auto', padding: '2px 6px', borderRadius: 'var(--radius-sm)', background: 'var(--accent-bg-soft)', border: '1px solid var(--accent)', color: 'var(--accent)', cursor: 'pointer', fontSize: 9, display: 'flex', alignItems: 'center', gap: 2 }}>
                          <Replace size={9} /> {t('svgEditor.replace')}
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Fix Result */}
            {fixResult && (
              <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: fixResult.was_valid ? 'var(--accent-bg-soft)' : 'var(--danger-soft)', border: `1px solid ${fixResult.was_valid ? 'var(--accent)' : 'var(--danger)'}`, fontSize: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: fixResult.errors.length > 0 ? 4 : 0 }}>
                  {fixResult.was_valid ? <CheckCircle2 size={12} style={{ color: 'var(--accent)' }} /> : <AlertTriangle size={12} style={{ color: 'var(--danger)' }} />}
                  <span style={{ fontWeight: 600, color: fixResult.was_valid ? 'var(--accent)' : 'var(--danger)' }}>
                    {fixResult.was_valid ? t('svgEditor.svgValid') : t('svgEditor.svgFixed')}
                  </span>
                </div>
                {fixResult.errors.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    {fixResult.errors.map((err, i) => (
                      <div key={i} style={{ color: 'var(--danger)', fontSize: 9 }}>• {err}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Generation Info */}
            {svgResult && (
              <div style={{ marginTop: 8, padding: '6px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>{t('svgEditor.iconCount')}: <span style={{ color: 'var(--body)', fontWeight: 600 }}>{svgResult.icon_count}</span></span>
                <span style={{ fontSize: 9, color: 'var(--mute)' }}>SVG: <span style={{ color: 'var(--body)' }}>{(svgContent?.length ?? 0).toLocaleString()} chars</span></span>
              </div>
            )}
          </div>
        )}

        {/* Code Tab */}
        {activeTab === 'code' && svgContent && (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
              <button onClick={handleCopySvgCode} style={{ padding: '4px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', gap: 3 }}>
                <Copy size={10} /> {t('svgEditor.copyCode')}
              </button>
              <button onClick={handleFixSvg} disabled={isFixing} style={{ padding: '4px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: isFixing ? 'not-allowed' : 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', gap: 3, opacity: isFixing ? 0.4 : 1 }}>
                {isFixing ? <Loader2 size={10} className="animate-spin" /> : <Wrench size={10} />} {t('svgEditor.fixSvg')}
              </button>
            </div>
            <textarea
              value={svgContent}
              onChange={e => handleSvgCodeEdit(e.target.value)}
              spellCheck={false}
              style={{
                width: '100%', minHeight: 400, padding: '8px 10px', borderRadius: 'var(--radius-sm)',
                background: 'var(--canvas)', border: '1px solid var(--hairline)',
                color: 'var(--ink)', fontSize: 11, fontFamily: 'monospace',
                lineHeight: 1.5, resize: 'vertical', outline: 'none',
                tabSize: 2,
              }}
            />
          </div>
        )}
      </div>

      {/* Bottom Action Bar */}
      <div style={{
        padding: '10px 16px', borderTop: '1px solid var(--hairline)',
        background: 'var(--glass-bg)', display: 'flex', gap: 8,
      }}>
        {activeTab === 'generate' && (
          <button
            onClick={handleMethodToSvg}
            disabled={!methodText.trim() || isGenerating}
            style={{
              flex: 1, padding: '8px 16px', borderRadius: 'var(--radius-sm)',
              background: 'var(--accent)', color: 'var(--on-primary)', border: 'none',
              cursor: !methodText.trim() || isGenerating ? 'not-allowed' : 'pointer',
              fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              opacity: !methodText.trim() || isGenerating ? 0.6 : 1,
            }}
          >
            {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />}
            {isGenerating ? t('svgEditor.generating') : t('svgEditor.generateSvg')}
          </button>
        )}
        {activeTab === 'edit' && svgContent && (
          <>
            <button
              onClick={handleExportSvg}
              style={{
                flex: 1, padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                background: 'var(--accent)', color: 'var(--on-primary)', border: 'none',
                cursor: 'pointer', fontSize: 12, fontWeight: 500,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}
            >
              <Download size={14} /> {t('svgEditor.exportSvg')}
            </button>
            <button
              onClick={handleExportPng}
              style={{
                padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                background: 'var(--accent-bg-soft)', color: 'var(--accent)', border: '1px solid var(--accent)',
                cursor: 'pointer', fontSize: 12, fontWeight: 500,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
              }}
            >
              <ImageIcon size={14} /> {t('svgEditor.exportPng')}
            </button>
            <button
              onClick={handleReset}
              style={{
                padding: '8px 12px', borderRadius: 'var(--radius-sm)',
                background: 'var(--canvas-soft)', color: 'var(--body)', border: '1px solid var(--hairline)',
                cursor: 'pointer', fontSize: 12,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <RotateCcw size={14} />
            </button>
          </>
        )}
        {activeTab === 'code' && svgContent && (
          <button
            onClick={handleExportSvg}
            style={{
              flex: 1, padding: '8px 16px', borderRadius: 'var(--radius-sm)',
              background: 'var(--accent)', color: 'var(--on-primary)', border: 'none',
              cursor: 'pointer', fontSize: 12, fontWeight: 500,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            <Download size={14} /> {t('svgEditor.exportSvg')}
          </button>
        )}
      </div>
    </div>
  );
};
