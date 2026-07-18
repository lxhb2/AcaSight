/**
 * 格式转换对话框组件
 * 支持 Markdown / docx / PDF 之间的格式互转
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  X, ArrowRight, Loader2, Download, FileText, FileDown,
  Upload,
} from 'lucide-react';
import { convertApi } from '@/services/documentService';
import type { Template } from '@/services/documentService';
import { saveFile, openFile } from '@/lib/tauri-adapter';

/** 源格式 */
type SourceFormat = 'markdown' | 'docx';
/** 目标格式 */
type TargetFormat = 'docx' | 'pdf' | 'markdown';

interface ConvertDialogProps {
  /** 是否可见 */
  visible: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 预填充的源内容 */
  sourceContent?: string;
  /** 预填充的源格式 */
  sourceType?: SourceFormat;
}

export const ConvertDialog: React.FC<ConvertDialogProps> = ({
  visible,
  onClose,
  sourceContent,
  sourceType,
}) => {
  const [srcFormat, setSrcFormat] = useState<SourceFormat>(sourceType || 'markdown');
  const [tgtFormat, setTgtFormat] = useState<TargetFormat>('docx');
  const [content, setContent] = useState(sourceContent || '');
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [converting, setConverting] = useState(false);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [resultText, setResultText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // docx 文件选择状态
  const [docxFileName, setDocxFileName] = useState<string>('');
  const [docxBase64, setDocxBase64] = useState<string>('');

  // 初始化源格式时自动选择合理的目标格式
  useEffect(() => {
    if (srcFormat === 'markdown') {
      setTgtFormat('docx');
    } else if (srcFormat === 'docx') {
      setTgtFormat('markdown');
    }
  }, [srcFormat]);

  // 加载转换模板
  useEffect(() => {
    if (visible) {
      convertApi.getConvertTemplates().then(setTemplates).catch(() => setTemplates([]));
    }
  }, [visible]);

  // 重置状态
  useEffect(() => {
    if (visible) {
      setContent(sourceContent || '');
      setSrcFormat(sourceType || 'markdown');
      setResultBlob(null);
      setResultText(null);
      setError(null);
      setSelectedTemplate(null);
      setDocxFileName('');
      setDocxBase64('');
    }
  }, [visible, sourceContent, sourceType]);

  /** 执行转换 */
  const handleConvert = useCallback(async () => {
    // Markdown 源需要内容，docx 源需要文件
    if (srcFormat === 'markdown' && !content.trim()) return;
    if (srcFormat === 'docx' && !docxBase64) return;

    setConverting(true);
    setResultBlob(null);
    setResultText(null);
    setError(null);

    try {
      const templatePath = selectedTemplate || undefined;

      if (srcFormat === 'markdown' && tgtFormat === 'docx') {
        const blob = await convertApi.mdToDocx(content, templatePath);
        setResultBlob(blob);
      } else if (srcFormat === 'markdown' && tgtFormat === 'pdf') {
        const blob = await convertApi.mdToPdf(content, templatePath);
        setResultBlob(blob);
      } else if (srcFormat === 'docx' && tgtFormat === 'markdown') {
        // 使用文件选择器读取的 base64
        const md = await convertApi.docxToMd(docxBase64);
        setResultText(md);
      } else {
        setError('不支持的转换格式组合');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '转换失败');
    } finally {
      setConverting(false);
    }
  }, [content, srcFormat, tgtFormat, selectedTemplate, docxBase64]);

  /** 下载结果 */
  const handleDownload = useCallback(async () => {
    if (resultBlob) {
      const ext = tgtFormat === 'docx' ? 'docx' : tgtFormat === 'pdf' ? 'pdf' : 'md';
      const fileName = `converted.${ext}`;
      const buffer = new Uint8Array(await resultBlob.arrayBuffer());
      await saveFile(buffer, {
        filters: [{ name: ext.toUpperCase(), extensions: [ext] }],
        defaultPath: fileName,
      });
    } else if (resultText) {
      await saveFile(resultText, {
        filters: [{ name: 'Markdown', extensions: ['md'] }],
        defaultPath: 'converted.md',
      });
    }
  }, [resultBlob, resultText, tgtFormat]);

  /** 选择 docx 文件 */
  const handleSelectDocx = useCallback(async () => {
    try {
      const files = await openFile({
        filters: [{ name: 'Word 文档', extensions: ['docx'] }],
        title: '选择 DOCX 文件',
      });
      if (files.length > 0) {
        const file = files[0];
        setDocxFileName(file.name);
        // 将 Uint8Array 转为 base64
        const base64 = btoa(
          Array.from(file.content)
            .map(b => String.fromCharCode(b))
            .join('')
        );
        setDocxBase64(base64);
      }
    } catch {
      // 用户取消选择，忽略
    }
  }, []);

  if (!visible) return null;

  /** 获取可用的目标格式列表 */
  const getTargetFormats = (): TargetFormat[] => {
    if (srcFormat === 'markdown') return ['docx', 'pdf'];
    return ['markdown'];
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div
        style={{
          width: 520, maxHeight: '80vh',
          borderRadius: 12, background: 'var(--canvas, #1a1a2e)',
          border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          overflow: 'hidden', display: 'flex', flexDirection: 'column',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* 标题栏 */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 16px', borderBottom: '1px solid var(--hairline, rgba(255,255,255,0.06))',
          background: 'var(--glass-bg, rgba(255,255,255,0.03))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileDown size={16} style={{ color: 'var(--accent, #6366f1)' }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--body, #e0e0e0)' }}>
              格式转换
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--mute, #888)', padding: 4, borderRadius: 4,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* 内容区 */}
        <div style={{ padding: 16, overflow: 'auto', flex: 1 }}>
          {/* 格式选择行 */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
          }}>
            {/* 源格式 */}
            <select
              value={srcFormat}
              onChange={e => setSrcFormat(e.target.value as SourceFormat)}
              style={{
                padding: '6px 10px', borderRadius: 6, fontSize: 12,
                background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
                color: 'var(--body, #e0e0e0)', outline: 'none', cursor: 'pointer',
              }}
            >
              <option value="markdown">Markdown</option>
              <option value="docx">DOCX</option>
            </select>

            <ArrowRight size={16} style={{ color: 'var(--mute, #888)' }} />

            {/* 目标格式 */}
            <select
              value={tgtFormat}
              onChange={e => setTgtFormat(e.target.value as TargetFormat)}
              style={{
                padding: '6px 10px', borderRadius: 6, fontSize: 12,
                background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
                color: 'var(--body, #e0e0e0)', outline: 'none', cursor: 'pointer',
              }}
            >
              {getTargetFormats().map(f => (
                <option key={f} value={f}>{f.toUpperCase()}</option>
              ))}
            </select>

            {/* 模板选择 */}
            {templates.length > 0 && (
              <div style={{ position: 'relative', marginLeft: 'auto' }}>
                <select
                  value={selectedTemplate || ''}
                  onChange={e => setSelectedTemplate(e.target.value || null)}
                  style={{
                    padding: '6px 10px', borderRadius: 6, fontSize: 12,
                    background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                    border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
                    color: 'var(--body, #e0e0e0)', outline: 'none', cursor: 'pointer',
                  }}
                >
                  <option value="">无模板</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* 源内容输入 */}
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: 'var(--mute, #888)', marginBottom: 4, display: 'block' }}>
              源内容
            </label>
            {srcFormat === 'markdown' ? (
              <textarea
                value={content}
                onChange={e => setContent(e.target.value)}
                placeholder="粘贴 Markdown 内容..."
                style={{
                  width: '100%', height: 140, padding: 10, borderRadius: 6, fontSize: 12,
                  background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                  border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
                  color: 'var(--body, #e0e0e0)', outline: 'none', resize: 'vertical',
                  fontFamily: 'monospace', lineHeight: 1.5,
                }}
              />
            ) : (
              <div style={{
                display: 'flex', flexDirection: 'column', gap: 8,
                padding: 16, borderRadius: 6,
                background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                border: '1px dashed var(--hairline, rgba(255,255,255,0.2))',
                alignItems: 'center', justifyContent: 'center',
              }}>
                {docxFileName ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--body, #e0e0e0)', fontSize: 12 }}>
                    <FileText size={16} style={{ color: 'var(--accent, #6366f1)' }} />
                    <span>{docxFileName}</span>
                    <button
                      onClick={() => { setDocxFileName(''); setDocxBase64(''); }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--mute, #888)', padding: 0 }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <span style={{ fontSize: 12, color: 'var(--mute, #888)' }}>请选择 DOCX 文件</span>
                )}
                <button
                  onClick={handleSelectDocx}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '6px 16px', borderRadius: 6, fontSize: 12,
                    background: 'var(--accent, #6366f1)', color: '#fff',
                    border: 'none', cursor: 'pointer',
                  }}
                >
                  <Upload size={14} />
                  选择文件
                </button>
              </div>
            )}
          </div>

          {/* 转换按钮 */}
          <button
            onClick={handleConvert}
            disabled={converting || (srcFormat === 'markdown' ? !content.trim() : !docxBase64)}
            style={{
              width: '100%', padding: '8px 16px', borderRadius: 6, fontSize: 13,
              background: 'var(--accent, #6366f1)', color: '#fff',
              border: 'none', cursor: converting ? 'wait' : 'pointer',
              opacity: converting || (srcFormat === 'markdown' ? !content.trim() : !docxBase64) ? 0.6 : 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            {converting ? (
              <><Loader2 size={14} className="animate-spin" /> 转换中...</>
            ) : (
              <>转换</>
            )}
          </button>

          {/* 错误提示 */}
          {error && (
            <div style={{
              marginTop: 12, padding: '8px 12px', borderRadius: 6,
              background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)',
              color: '#ef4444', fontSize: 12,
            }}>
              {error}
            </div>
          )}

          {/* 转换结果预览 */}
          {(resultBlob || resultText) && (
            <div style={{ marginTop: 12 }}>
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                marginBottom: 8,
              }}>
                <span style={{ fontSize: 11, color: 'var(--mute, #888)' }}>
                  转换结果
                </span>
                <button
                  onClick={handleDownload}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '4px 10px', borderRadius: 6, fontSize: 12,
                    background: '#10b981', color: '#fff', border: 'none', cursor: 'pointer',
                  }}
                >
                  <Download size={13} /> 下载
                </button>
              </div>
              {resultText ? (
                <div style={{
                  padding: 10, borderRadius: 6, fontSize: 12,
                  background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                  border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
                  color: 'var(--body, #e0e0e0)', fontFamily: 'monospace',
                  maxHeight: 200, overflow: 'auto', whiteSpace: 'pre-wrap',
                  lineHeight: 1.5,
                }}>
                  {resultText}
                </div>
              ) : (
                <div style={{
                  padding: 10, borderRadius: 6, fontSize: 12,
                  background: 'var(--bg-secondary, rgba(255,255,255,0.05))',
                  border: '1px solid var(--hairline, rgba(255,255,255,0.1))',
                  color: 'var(--mute, #888)',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <FileText size={14} />
                  文件已生成（{resultBlob ? `${(resultBlob.size / 1024).toFixed(1)} KB` : ''}），点击下载保存
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
