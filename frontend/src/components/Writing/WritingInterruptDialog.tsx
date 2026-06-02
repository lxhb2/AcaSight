/**
 * WritingInterruptDialog — AI 写作人机交互中断对话框
 * 
 * 当 AI 写作推进至数据/图表/图片章节时触发，提供 3 种素材模式：
 * 1. 上传本地文件
 * 2. AI 自动生成图表
 * 3. 从已有作品选择
 */

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Upload, Sparkles, Image, X,
  Check, ChevronRight,
  Loader2, FileText,
} from 'lucide-react';
import { agentApi } from '@/services/api';

// ─── 类型 ───

export type InterruptMode = 'upload' | 'auto_generate' | 'select_existing' | 'skip';

export interface InterruptConfig {
  sectionTitle: string;    // 当前章节标题
  sectionType: string;     // data / chart / figure / table
  description: string;     // 中断描述
}

export interface ExistingChart {
  id: string;
  name: string;
  type: string;
  preview_url?: string;
  created_at: string;
}

export interface InterruptResult {
  mode: InterruptMode;
  files?: File[];
  filePaths?: string[];
  chartId?: string;
  chartIds?: string[];
  autoDescription?: string;
  dataContent?: string;   // 上传的数据文件内容
}

// ─── 关键词检测 ───

const INTERRUPT_KEYWORDS: { keywords: string[]; type: string }[] = [
  { keywords: ['数据', '实验数据', '原始数据', '测试数据'], type: 'data' },
  { keywords: ['图表', '如图', '见图', '下表', '见表', 'Figure', 'Fig', 'Table', '图 '], type: 'chart' },
  { keywords: ['插图', '照片', '图像', 'SEM', 'TEM', '显微镜', '电镜'], type: 'figure' },
  { keywords: ['表格', '统计表', '对比表', '数据表'], type: 'table' },
];

export function detectInterruptPoint(sectionTitle: string, sectionContent: string): InterruptConfig | null {
  for (const group of INTERRUPT_KEYWORDS) {
    for (const kw of group.keywords) {
      if (sectionTitle.includes(kw) || sectionContent.includes(kw)) {
        return {
          sectionTitle,
          sectionType: group.type,
          description: getInterruptDescription(group.type, sectionTitle),
        };
      }
    }
  }
  return null;
}

function getInterruptDescription(type: string, title: string): string {
  switch (type) {
    case 'data':
      return `正在撰写「${title}」，本章节可能涉及实验数据。请选择数据来源：`;
    case 'chart':
      return `正在撰写「${title}」，需要插入图表。请选择图表来源：`;
    case 'figure':
      return `正在撰写「${title}」，需要插入图片。请选择图片来源：`;
    case 'table':
      return `正在撰写「${title}」，需要插入表格。请选择表格来源：`;
    default:
      return `正在撰写「${title}」，需要插入素材。请选择来源：`;
  }
}

// ─── 组件 Props ───

interface WritingInterruptDialogProps {
  config: InterruptConfig;
  onConfirm: (result: InterruptResult) => void;
  onSkip: () => void;
  onCancel: () => void;
  existingCharts: ExistingChart[];
  onLoadExistingCharts: () => void;
}

// ─── 主组件 ───

export const WritingInterruptDialog: React.FC<WritingInterruptDialogProps> = ({
  config, onConfirm, onSkip, onCancel,
  existingCharts, onLoadExistingCharts,
}) => {
  const [selectedMode, setSelectedMode] = useState<InterruptMode>('upload');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [uploadedPaths, setUploadedPaths] = useState<string[]>([]);
  const [autoDescription, setAutoDescription] = useState('');
  const [selectedChartIds, setSelectedChartIds] = useState<Set<string>>(new Set());
  const [dataContent, setDataContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedPreview, setGeneratedPreview] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 加载已有作品
  useEffect(() => {
    if (selectedMode === 'select_existing') {
      onLoadExistingCharts();
    }
  }, [selectedMode, onLoadExistingCharts]);

  // 文件选择
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setUploadedFiles(files);
    setUploadedPaths(files.map(f => f.name));

    // 读取数据文件内容
    files.forEach(file => {
      if (file.name.endsWith('.csv') || file.name.endsWith('.txt') || file.name.endsWith('.json')) {
        const reader = new FileReader();
        reader.onload = () => setDataContent(prev => prev + '\n' + (reader.result as string));
        reader.readAsText(file);
      }
    });
  }, []);

  // AI 生成图表
  const handleAutoGenerate = useCallback(async () => {
    if (!autoDescription.trim()) return;
    setIsGenerating(true);
    try {
      const data = await agentApi.callTool({
        tool_name: 'chart_auto_generate',
        arguments: {
          description: autoDescription,
          chart_type: config.sectionType === 'figure' ? 'sem-image' : 'scatter',
        },
      });
      if (data.success) {
        setGeneratedPreview(JSON.stringify(data.result, null, 2));
      }
    } catch (_e: unknown) {
      console.error('Auto generate failed:', _e);
    }
    setIsGenerating(false);
  }, [autoDescription, config.sectionType]);

  // 确认提交
  const handleConfirm = useCallback(() => {
    const result: InterruptResult = {
      mode: selectedMode,
      files: uploadedFiles,
      filePaths: uploadedPaths,
      autoDescription: selectedMode === 'auto_generate' ? autoDescription : undefined,
      dataContent: dataContent || undefined,
      chartIds: selectedMode === 'select_existing' ? Array.from(selectedChartIds) : undefined,
    };
    onConfirm(result);
  }, [selectedMode, uploadedFiles, uploadedPaths, autoDescription, dataContent, selectedChartIds, onConfirm]);

  // 切换图表选择
  const toggleChart = (id: string) => {
    setSelectedChartIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
    }}>
      <div style={{
        background: 'var(--bg-primary, #fff)', borderRadius: 16, padding: '24px 28px',
        maxWidth: 560, width: '90%', maxHeight: '80vh', overflow: 'auto',
        color: 'var(--ink, #1a1a2e)', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} color="var(--accent, #6366f1)" />
            AI 写作中断 — 素材选择
          </h3>
          <button onClick={onCancel}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 4 }}>
            <X size={18} />
          </button>
        </div>

        <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 20 }}>{config.description}</p>

        {/* Mode Selection */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexDirection: 'column' }}>
          {[
            { mode: 'upload' as InterruptMode, icon: Upload, label: '模式一：上传本地文件', desc: '实验图片、数据文件、开题报告等', color: '#10b981' },
            { mode: 'auto_generate' as InterruptMode, icon: Sparkles, label: '模式二：AI 自动生成', desc: '使用科研绘图 Skill 生成图表', color: '#6366f1' },
            { mode: 'select_existing' as InterruptMode, icon: Image, label: '模式三：从已有作品选择', desc: '历史保存的图表与内嵌对象', color: '#f59e0b' },
          ].map(item => (
            <div key={item.mode}
              onClick={() => setSelectedMode(item.mode)}
              style={{
                padding: '12px 16px', borderRadius: 10, cursor: 'pointer',
                border: `2px solid ${selectedMode === item.mode ? item.color : 'var(--border-color, #e2e8f0)'}`,
                background: selectedMode === item.mode ? `${item.color}10` : 'var(--bg-secondary, #f8fafc)',
                display: 'flex', alignItems: 'center', gap: 10,
                transition: 'all 0.15s',
              }}>
              <item.icon size={20} color={item.color} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600 }}>{item.label}</div>
                <div style={{ fontSize: 11, color: 'var(--muted)' }}>{item.desc}</div>
              </div>
              {selectedMode === item.mode && <Check size={16} color={item.color} />}
            </div>
          ))}
        </div>

        {/* Mode Content */}
        <div style={{ marginBottom: 20, minHeight: 60 }}>
          {/* Upload mode */}
          {selectedMode === 'upload' && (
            <div>
              <input ref={fileInputRef} type="file" multiple
                accept=".png,.jpg,.jpeg,.gif,.csv,.txt,.json,.xlsx,.xls,.pdf,.doc,.docx"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              <button onClick={() => fileInputRef.current?.click()}
                style={{
                  width: '100%', padding: '12px', borderRadius: 8,
                  border: '2px dashed var(--border-color)', background: 'transparent',
                  cursor: 'pointer', color: 'var(--muted)', fontSize: 13,
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
                }}>
                <Upload size={24} />
                <span>点击上传文件</span>
                <span style={{ fontSize: 11 }}>支持图片、CSV、Excel、PDF 等</span>
              </button>
              {uploadedPaths.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--success, #10b981)' }}>
                  已选择: {uploadedPaths.join(', ')}
                </div>
              )}
            </div>
          )}

          {/* Auto generate mode */}
          {selectedMode === 'auto_generate' && (
            <div>
              <textarea
                value={autoDescription}
                onChange={e => setAutoDescription(e.target.value)}
                placeholder="描述你需要的图表，例如：XRD 衍射图谱，x 轴为 2θ(10-80°)，y 轴为强度..."
                style={{
                  width: '100%', height: 80, padding: '8px 12px', borderRadius: 8,
                  border: '1px solid var(--border-color)', background: 'var(--bg-secondary)',
                  color: 'var(--ink)', fontSize: 13, resize: 'vertical', outline: 'none',
                }}
              />
              <button onClick={handleAutoGenerate} disabled={isGenerating || !autoDescription.trim()}
                style={{
                  marginTop: 8, padding: '6px 16px', borderRadius: 6, border: 'none',
                  background: (isGenerating || !autoDescription.trim()) ? 'var(--muted)' : 'var(--accent)',
                  color: '#fff', cursor: 'pointer', fontSize: 12,
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                {isGenerating ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />}
                {isGenerating ? '生成中...' : '预览生成'}
              </button>
              {generatedPreview && (
                <div style={{ marginTop: 8, padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, fontSize: 11,
                  color: 'var(--success)', maxHeight: 120, overflow: 'auto' }}>
                  图表配置已生成（可在绘图面板中进一步编辑）
                </div>
              )}
            </div>
          )}

          {/* Select existing mode */}
          {selectedMode === 'select_existing' && (
            <div>
              {existingCharts.length === 0 ? (
                <div style={{ padding: 16, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
                  暂无已保存的图表作品
                </div>
              ) : (
                <div style={{ maxHeight: 160, overflow: 'auto', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                  {existingCharts.map(chart => (
                    <div key={chart.id}
                      onClick={() => toggleChart(chart.id)}
                      style={{
                        padding: '8px 12px', borderBottom: '1px solid var(--border-color)',
                        display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
                        background: selectedChartIds.has(chart.id) ? 'rgba(99,102,241,0.08)' : 'transparent',
                      }}>
                      <input type="checkbox" checked={selectedChartIds.has(chart.id)} readOnly style={{ margin: 0 }} />
                      <FileText size={14} />
                      <div style={{ flex: 1, fontSize: 12 }}>
                        <div style={{ fontWeight: 500 }}>{chart.name}</div>
                        <div style={{ color: 'var(--muted)', fontSize: 10 }}>{chart.type} · {chart.created_at}</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onSkip}
            style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid var(--border-color)',
              background: 'transparent', color: 'var(--muted)', cursor: 'pointer', fontSize: 12 }}>
            跳过（本章不插入图表）
          </button>
          <button onClick={handleConfirm}
            style={{ padding: '8px 24px', borderRadius: 8, border: 'none',
              background: 'var(--accent, #6366f1)', color: '#fff', cursor: 'pointer', fontSize: 13, fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 6 }}>
            确认插入 <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};