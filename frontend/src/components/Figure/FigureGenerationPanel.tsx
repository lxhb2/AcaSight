import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ImagePlus, Upload, X, Sparkles,
  Loader2, RefreshCw, Palette, Maximize2, ZoomIn,
  AlertTriangle, Eye, Wand2, Download,
  Sliders, FileImage, RotateCcw, ChevronDown, ChevronUp,
  Code, BarChart3, GitBranch,
} from 'lucide-react';
import { paperBananaApi, type PaperBananaPlotResult, type PaperBananaStyle } from '@/services/api';
import { LazyImage } from '@/components/Common/LazyImage';

type GenerationMode = 'plot' | 'diagram';

const COLOR_SCHEMES = [
  { id: 'default', nameKey: 'figure.colorDefault', colors: ['#6366f1', '#06b6d4', '#10b981', '#f59e0b'] },
  { id: 'warm', nameKey: 'figure.colorWarm', colors: ['#ef4444', '#f97316', '#eab308', '#f59e0b'] },
  { id: 'cool', nameKey: 'figure.colorCool', colors: ['#3b82f6', '#6366f1', '#8b5cf6', '#06b6d4'] },
  { id: 'earth', nameKey: 'figure.colorEarth', colors: ['#92400e', '#a16207', '#4d7c0f', '#166534'] },
  { id: 'grayscale', nameKey: 'figure.colorGrayscale', colors: ['#374151', '#6b7280', '#9ca3af', '#d1d5db'] },
  { id: 'nature', nameKey: 'figure.colorNature', colors: ['#059669', '#0891b2', '#7c3aed', '#db2777'] },
];

interface ReferenceImage {
  id: string;
  file: File;
  preview: string;
  label: string;
}

interface GenerationParams {
  prompt: string;
  mode: GenerationMode;
  styleGuide: string;
  colorScheme: string;
  maxCriticRounds: number;
  enhancePrompt: boolean;
  referenceImages: ReferenceImage[];
}

interface FigureGenerationPanelProps {
  onInsertToWriting?: (imageUrl: string, caption: string) => void;
}

export const FigureGenerationPanel: React.FC<FigureGenerationPanelProps> = ({ onInsertToWriting }) => {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [params, setParams] = useState<GenerationParams>({
    prompt: '',
    mode: 'plot',
    styleGuide: '',
    colorScheme: 'default',
    maxCriticRounds: 2,
    enhancePrompt: true,
    referenceImages: [],
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [generatedCaption, setGeneratedCaption] = useState('');
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [criticReports, setCriticReports] = useState<PaperBananaPlotResult['critic_reports']>([]);
  const [roundsCompleted, setRoundsCompleted] = useState(0);
  const [availableStyles, setAvailableStyles] = useState<PaperBananaStyle[]>([]);
  const [generationHistory, setGenerationHistory] = useState<Array<{
    id: string;
    imageUrl: string;
    prompt: string;
    timestamp: number;
  }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    paperBananaApi.getStyles().then(res => {
      if (res.styles) setAvailableStyles(res.styles);
    }).catch(() => {});
  }, []);

  const updateParam = useCallback(<K extends keyof GenerationParams>(key: K, value: GenerationParams[K]) => {
    setParams(prev => ({ ...prev, [key]: value }));
  }, []);

  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newImages: ReferenceImage[] = [];
    Array.from(files).forEach(file => {
      if (!file.type.startsWith('image/')) return;
      const preview = URL.createObjectURL(file);
      newImages.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        preview,
        label: file.name,
      });
    });
    setParams(prev => ({
      ...prev,
      referenceImages: [...prev.referenceImages, ...newImages].slice(0, 4),
    }));
    if (e.target) e.target.value = '';
  }, []);

  const removeReferenceImage = useCallback((id: string) => {
    setParams(prev => {
      const img = prev.referenceImages.find(r => r.id === id);
      if (img) URL.revokeObjectURL(img.preview);
      return { ...prev, referenceImages: prev.referenceImages.filter(r => r.id !== id) };
    });
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!params.prompt.trim()) return;
    setIsGenerating(true);
    setGeneratedImage(null);
    setGeneratedCode(null);
    setCriticReports([]);
    setRoundsCompleted(0);
    setError(null);

    try {
      let result: { success: boolean; data: PaperBananaPlotResult };
      if (params.mode === 'plot') {
        result = await paperBananaApi.generatePlot({
          data: params.prompt,
          visual_intent: params.enhancePrompt ? 'auto' : params.prompt,
          style_guide: params.styleGuide || undefined,
          max_critic_rounds: params.maxCriticRounds,
        });
      } else {
        result = await paperBananaApi.generateDiagram({
          methodology: params.prompt,
          caption: params.prompt,
          style_guide: params.styleGuide || undefined,
          max_critic_rounds: params.maxCriticRounds,
        });
      }

      if (result.success && result.data) {
        const { data } = result;
        const imageUrl = `data:image/png;base64,${data.image_base64}`;
        setGeneratedImage(imageUrl);
        setGeneratedCaption(data.description || `Figure: ${params.prompt.slice(0, 80)}`);
        setGeneratedCode(data.code || null);
        setCriticReports(data.critic_reports || []);
        setRoundsCompleted(data.rounds_completed || 0);
        setGenerationHistory(prev => [{
          id: `gen-${Date.now()}`,
          imageUrl,
          prompt: params.prompt,
          timestamp: Date.now(),
        }, ...prev].slice(0, 10));
      } else {
        setError(t('figure.generationFailed'));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setIsGenerating(false);
    }
  }, [params, t]);

  const handleRegenerate = useCallback(() => {
    handleGenerate();
  }, [handleGenerate]);

  const handleInsert = useCallback(() => {
    if (generatedImage && onInsertToWriting) {
      onInsertToWriting(generatedImage, generatedCaption);
    }
  }, [generatedImage, generatedCaption, onInsertToWriting]);

  const handleDownload = useCallback(() => {
    if (!generatedImage) return;
    const a = document.createElement('a');
    a.href = generatedImage;
    a.download = `figure-${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }, [generatedImage]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflow: 'auto', padding: '0 16px 16px' }}>
        {/* Mode Toggle */}
        <div style={{ marginTop: 12, display: 'flex', gap: 4, padding: 3, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
          {([
            { id: 'plot' as GenerationMode, icon: <BarChart3 size={12} />, labelKey: 'figure.modePlot' },
            { id: 'diagram' as GenerationMode, icon: <GitBranch size={12} />, labelKey: 'figure.modeDiagram' },
          ]).map(m => (
            <button
              key={m.id}
              onClick={() => updateParam('mode', m.id)}
              style={{
                flex: 1, padding: '5px 10px', borderRadius: 'var(--radius-sm)', fontSize: 11,
                background: params.mode === m.id ? 'var(--accent)' : 'transparent',
                color: params.mode === m.id ? 'var(--on-primary)' : 'var(--body)',
                border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
                fontWeight: params.mode === m.id ? 600 : 400, transition: 'all 0.12s',
              }}
            >
              {m.icon} {t(m.labelKey)}
            </button>
          ))}
        </div>

        {/* Prompt Input */}
        <div style={{ marginTop: 10 }}>
          <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
            {params.mode === 'plot' ? t('figure.dataInput') : t('figure.promptLabel')}
          </label>
          <textarea
            value={params.prompt}
            onChange={e => updateParam('prompt', e.target.value)}
            placeholder={params.mode === 'plot' ? t('figure.dataPlaceholder') : t('figure.promptPlaceholder')}
            rows={3}
            style={{
              width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              background: 'var(--canvas)', border: '1px solid var(--hairline)',
              color: 'var(--ink)', fontSize: 12, resize: 'vertical',
              outline: 'none', lineHeight: 1.5, fontFamily: 'inherit',
            }}
          />
        </div>

        {/* Reference Images */}
        <div style={{ marginTop: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)' }}>
              {t('figure.referenceImages')} ({params.referenceImages.length}/4)
            </label>
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                fontSize: 11, padding: '3px 10px', borderRadius: 'var(--radius-sm)',
                background: 'var(--accent-bg-soft)', border: '1px solid var(--hairline)',
                color: 'var(--accent)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
              }}
            >
              <Upload size={11} /> {t('figure.uploadRef')}
            </button>
            <input ref={fileInputRef} type="file" accept="image/*" multiple onChange={handleImageUpload} style={{ display: 'none' }} />
          </div>
          {params.referenceImages.length > 0 ? (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {params.referenceImages.map(img => (
                <div key={img.id} style={{ position: 'relative', width: 72, height: 72, borderRadius: 'var(--radius-sm)', overflow: 'hidden', border: '1px solid var(--hairline)' }}>
                  <LazyImage src={img.preview} alt={img.label} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  <button onClick={() => removeReferenceImage(img.id)} style={{ position: 'absolute', top: 2, right: 2, width: 18, height: 18, borderRadius: '50%', background: 'rgba(0,0,0,0.6)', border: 'none', color: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <X size={10} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div onClick={() => fileInputRef.current?.click()} style={{ padding: '16px 12px', borderRadius: 'var(--radius-sm)', border: '1px dashed var(--hairline)', background: 'var(--canvas-soft)', textAlign: 'center', cursor: 'pointer' }}>
              <ImagePlus size={20} style={{ color: 'var(--mute)', marginBottom: 4 }} />
              <div style={{ fontSize: 11, color: 'var(--mute)' }}>{t('figure.dropImages')}</div>
            </div>
          )}
        </div>

        {/* Style Guide Selection */}
        {availableStyles.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
              {t('figure.styleGuide')}
            </label>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button
                onClick={() => updateParam('styleGuide', '')}
                style={{
                  padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${!params.styleGuide ? 'var(--accent)' : 'var(--hairline)'}`,
                  background: !params.styleGuide ? 'var(--accent-bg-soft)' : 'transparent',
                  color: !params.styleGuide ? 'var(--accent)' : 'var(--body)',
                  cursor: 'pointer', fontSize: 10,
                }}
              >
                {t('figure.styleAuto')}
              </button>
              {availableStyles.map(style => (
                <button
                  key={style.id}
                  onClick={() => updateParam('styleGuide', style.id)}
                  style={{
                    padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${params.styleGuide === style.id ? 'var(--accent)' : 'var(--hairline)'}`,
                    background: params.styleGuide === style.id ? 'var(--accent-bg-soft)' : 'transparent',
                    color: params.styleGuide === style.id ? 'var(--accent)' : 'var(--body)',
                    cursor: 'pointer', fontSize: 10,
                  }}
                >
                  {style.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Color Scheme */}
        <div style={{ marginTop: 14 }}>
          <label style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
            <Palette size={11} style={{ marginRight: 4, verticalAlign: 'middle' }} />
            {t('figure.colorScheme')}
          </label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {COLOR_SCHEMES.map(scheme => (
              <button
                key={scheme.id}
                onClick={() => updateParam('colorScheme', scheme.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '4px 8px', borderRadius: 'var(--radius-sm)',
                  border: `1px solid ${params.colorScheme === scheme.id ? 'var(--accent)' : 'var(--hairline)'}`,
                  background: params.colorScheme === scheme.id ? 'var(--accent-bg-soft)' : 'transparent',
                  cursor: 'pointer', transition: 'all 0.12s',
                }}
              >
                <div style={{ display: 'flex', gap: 2 }}>
                  {scheme.colors.map((c, i) => (
                    <div key={i} style={{ width: 10, height: 10, borderRadius: 2, background: c }} />
                  ))}
                </div>
                <span style={{ fontSize: 10, color: params.colorScheme === scheme.id ? 'var(--accent)' : 'var(--body)' }}>
                  {t(scheme.nameKey)}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Settings */}
        <div style={{ marginTop: 14 }}>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, width: '100%',
              padding: '6px 0', background: 'none', border: 'none',
              color: 'var(--body)', cursor: 'pointer', fontSize: 11, fontWeight: 500,
            }}
          >
            <Sliders size={12} /> {t('figure.advancedSettings')}
            {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {showAdvanced && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 10, padding: '10px 12px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
              <div>
                <label style={{ fontSize: 10, color: 'var(--mute)', marginBottom: 4, display: 'block' }}>{t('figure.maxCriticRounds')}</label>
                <div style={{ display: 'flex', gap: 6 }}>
                  {[1, 2, 3].map(n => (
                    <button
                      key={n}
                      onClick={() => updateParam('maxCriticRounds', n)}
                      style={{
                        flex: 1, padding: '5px 4px', borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${params.maxCriticRounds === n ? 'var(--accent)' : 'var(--hairline)'}`,
                        background: params.maxCriticRounds === n ? 'var(--accent-bg-soft)' : 'transparent',
                        color: params.maxCriticRounds === n ? 'var(--accent)' : 'var(--body)',
                        cursor: 'pointer', fontSize: 10, textAlign: 'center',
                      }}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--body)', cursor: 'pointer' }}>
                <input type="checkbox" checked={params.enhancePrompt} onChange={e => updateParam('enhancePrompt', e.target.checked)} style={{ accentColor: 'var(--accent)' }} />
                <Wand2 size={12} style={{ color: 'var(--accent)' }} />
                {t('figure.enhancePrompt')}
              </label>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div style={{ marginTop: 12, padding: '8px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--danger-soft)', border: '1px solid var(--danger)', fontSize: 11, color: 'var(--danger)', display: 'flex', alignItems: 'flex-start', gap: 6 }}>
            <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Generation Result */}
        {(generatedImage || isGenerating) && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sparkles size={14} style={{ color: 'var(--accent)' }} />
                {t('figure.generationResult')}
                {roundsCompleted > 0 && <span style={{ fontSize: 9, color: 'var(--mute)', fontWeight: 400 }}>({roundsCompleted} {t('figure.criticRounds')})</span>}
              </span>
              {generatedImage && (
                <div style={{ display: 'flex', gap: 4 }}>
                  {generatedCode && (
                    <button onClick={() => setShowCode(!showCode)} title={t('figure.viewCode')} style={{ padding: 4, borderRadius: 'var(--radius-sm)', background: showCode ? 'var(--accent-bg-soft)' : 'var(--canvas-soft)', border: '1px solid var(--hairline)', color: showCode ? 'var(--accent)' : 'var(--body)', cursor: 'pointer' }}>
                      <Code size={13} />
                    </button>
                  )}
                  <button onClick={() => setShowPreview(!showPreview)} title={t('figure.preview')} style={{ padding: 4, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: 'pointer' }}>
                    {showPreview ? <Maximize2 size={13} /> : <ZoomIn size={13} />}
                  </button>
                  <button onClick={handleRegenerate} title={t('figure.regenerate')} style={{ padding: 4, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: 'pointer' }}>
                    <RefreshCw size={13} />
                  </button>
                  <button onClick={handleDownload} title={t('figure.download')} style={{ padding: 4, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: 'pointer' }}>
                    <Download size={13} />
                  </button>
                </div>
              )}
            </div>

            {isGenerating ? (
              <div style={{ height: 200, borderRadius: 'var(--radius-sm)', border: '1px solid var(--hairline)', background: 'var(--canvas-soft)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                <Loader2 size={28} className="animate-spin" style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: 12, color: 'var(--body)' }}>{t('figure.generating')}</span>
                <div style={{ width: 160, height: 3, borderRadius: 2, background: 'var(--hairline)', overflow: 'hidden' }}>
                  <div style={{ width: '40%', height: '100%', background: 'var(--accent)', borderRadius: 2, animation: 'pulse 1.5s ease-in-out infinite' }} />
                </div>
              </div>
            ) : generatedImage && (
              <div style={{ borderRadius: 'var(--radius-sm)', border: '1px solid var(--hairline)', overflow: 'hidden' }}>
                <LazyImage src={generatedImage} alt={generatedCaption} style={{ width: '100%', height: showPreview ? 'auto' : 200, objectFit: 'contain', background: 'var(--canvas)' }} />
                <div style={{ padding: '8px 10px', borderTop: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 10, color: 'var(--mute)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{generatedCaption}</span>
                  {onInsertToWriting && (
                    <button onClick={handleInsert} style={{ fontSize: 10, padding: '3px 10px', borderRadius: 'var(--radius-sm)', background: 'var(--accent)', color: 'var(--on-primary)', border: 'none', cursor: 'pointer', fontWeight: 500, display: 'flex', alignItems: 'center', gap: 3 }}>
                      <FileImage size={10} /> {t('figure.insertToDoc')}
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Code Preview */}
            {showCode && generatedCode && (
              <div style={{ marginTop: 8, borderRadius: 'var(--radius-sm)', border: '1px solid var(--hairline)', overflow: 'hidden' }}>
                <div style={{ padding: '4px 10px', background: 'var(--canvas-soft)', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 10, fontWeight: 500, color: 'var(--mute)' }}>matplotlib</span>
                  <button onClick={() => { navigator.clipboard.writeText(generatedCode); }} style={{ fontSize: 9, padding: '2px 6px', borderRadius: 'var(--radius-sm)', background: 'var(--canvas)', border: '1px solid var(--hairline)', color: 'var(--body)', cursor: 'pointer' }}>
                    {t('common.copy')}
                  </button>
                </div>
                <pre style={{ margin: 0, padding: '8px 10px', fontSize: 10, lineHeight: 1.5, color: 'var(--ink)', background: 'var(--canvas)', overflow: 'auto', maxHeight: 200, fontFamily: 'monospace' }}>
                  {generatedCode}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* Critic Reports (from Pipeline) */}
        {criticReports.length > 0 && !isGenerating && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Eye size={14} style={{ color: 'var(--cyan)' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{t('figure.criticResult')}</span>
              <span style={{ fontSize: 9, color: 'var(--mute)' }}>({criticReports.length} {t('figure.criticRounds')})</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {criticReports.map((report, idx) => (
                <div key={idx} style={{ padding: 10, borderRadius: 'var(--radius-sm)', background: 'var(--canvas-soft)', border: '1px solid var(--hairline)' }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--ink)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <AlertTriangle size={10} style={{ color: 'var(--warning)' }} />
                    {t('figure.criticRound')} {idx + 1}
                  </div>
                  {report.suggestions && (
                    <div style={{ fontSize: 10, color: 'var(--body)', lineHeight: 1.5, marginBottom: report.revised_description ? 6 : 0 }}>
                      {report.suggestions}
                    </div>
                  )}
                  {report.revised_description && (
                    <div style={{ fontSize: 9, color: 'var(--mute)', fontStyle: 'italic', borderTop: '1px solid var(--hairline)', paddingTop: 4, marginTop: 4 }}>
                      {t('figure.revisedDesc')}: {report.revised_description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Generation History */}
        {generationHistory.length > 1 && (
          <div style={{ marginTop: 14 }}>
            <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--mute)', marginBottom: 6, display: 'block' }}>
              {t('figure.history')} ({generationHistory.length})
            </span>
            <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingBottom: 4 }}>
              {generationHistory.map(item => (
                <div
                  key={item.id}
                  onClick={() => { setGeneratedImage(item.imageUrl); setGeneratedCaption(`Figure: ${item.prompt.slice(0, 80)}`); }}
                  style={{
                    width: 56, height: 56, borderRadius: 'var(--radius-sm)', overflow: 'hidden',
                    border: generatedImage === item.imageUrl ? '2px solid var(--accent)' : '1px solid var(--hairline)',
                    cursor: 'pointer', flexShrink: 0,
                  }}
                >
                  <LazyImage src={item.imageUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Bottom Action Bar */}
      <div style={{ padding: '10px 16px', borderTop: '1px solid var(--hairline)', background: 'var(--glass-bg)', display: 'flex', gap: 8 }}>
        <button
          onClick={handleGenerate}
          disabled={isGenerating || !params.prompt.trim()}
          style={{
            flex: 1, padding: '8px 16px', borderRadius: 'var(--radius-sm)',
            background: 'var(--accent)', color: 'var(--on-primary)', border: 'none',
            cursor: isGenerating || !params.prompt.trim() ? 'not-allowed' : 'pointer',
            fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            opacity: isGenerating || !params.prompt.trim() ? 0.6 : 1,
          }}
        >
          {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
          {isGenerating ? t('figure.generating') : t('figure.generate')}
        </button>
        {generatedImage && (
          <button
            onClick={handleRegenerate}
            disabled={isGenerating}
            style={{
              padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              background: 'var(--canvas-soft)', border: '1px solid var(--hairline)',
              color: 'var(--body)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            <RotateCcw size={14} />
          </button>
        )}
      </div>
    </div>
  );
};
