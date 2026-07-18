/**
 * OnlyOffice 文档编辑器组件
 * 嵌入 OnlyOffice 编辑器，支持编辑/查看模式
 */

import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { Loader2, AlertTriangle, FileText, ArrowLeftRight, RefreshCw, ExternalLink } from 'lucide-react';
import { documentApi } from '@/services/documentService';
import type { OnlyOfficeConfig } from '@/services/documentService';
import { OnlyOfficeConnector, checkOnlyOfficeAvailability } from '@/lib/onlyoffice-connector';
import { useDocumentBridgeStore } from '@/store/documentBridgeStore';
import { usePanelSwitchStore } from '@/store/panelSwitchStore';
import { ConvertDialog } from '@/components/Convert/ConvertDialog';
import { isTauri } from '@/lib/tauri-adapter';

/** OnlyOffice Document Server 默认地址 */
const DEFAULT_OO_SERVER = 'http://localhost:8080';

interface DocumentEditorProps {
  /** 文档 ID */
  docId: string;
  /** 编辑模式 */
  mode?: 'edit' | 'view';
  /** 保存回调 */
  onSaved?: () => void;
  /** 错误回调 */
  onError?: (error: string) => void;
}

export const DocumentEditor: React.FC<DocumentEditorProps> = ({
  docId,
  mode = 'edit',
  onSaved,
  onError,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const connectorRef = useRef<OnlyOfficeConnector | null>(null);
  const containerId = useMemo(() => `oo-editor-${docId}-${Date.now()}`, [docId]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ooAvailable, setOoAvailable] = useState(true);
  const [docTitle, setDocTitle] = useState('');

  // 文档桥接 & 面板切换
  const extractFromOffice = useDocumentBridgeStore((s) => s.extractFromOffice);
  const requestPanelSwitch = usePanelSwitchStore((s) => s.requestSwitch);

  // 格式转换对话框
  const [showConvertDialog, setShowConvertDialog] = useState(false);

  // 提取到 AI 写作台
  const [extracting, setExtracting] = useState(false);
  const handleExtractToWriting = useCallback(async () => {
    setExtracting(true);
    const msgId = extractFromOffice(docId);
    // 轮询消息状态
    const checkInterval = setInterval(() => {
      const msg = useDocumentBridgeStore.getState().messages.find(m => m.id === msgId);
      if (msg?.status === 'completed') {
        clearInterval(checkInterval);
        setExtracting(false);
        // 切换到写作面板
        requestPanelSwitch('writing');
      } else if (msg?.status === 'failed') {
        clearInterval(checkInterval);
        setExtracting(false);
        setError(msg.error || '提取 Markdown 失败');
      }
    }, 500);
    // 超时保护
    setTimeout(() => { clearInterval(checkInterval); setExtracting(false); }, 30000);
  }, [docId, extractFromOffice, requestPanelSwitch]);

  /** 初始化编辑器 */
  const initEditor = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      // 1. 检测 OnlyOffice 可用性
      const serverUrl = DEFAULT_OO_SERVER;
      const available = await checkOnlyOfficeAvailability(serverUrl);
      setOoAvailable(available);

      if (!available) {
        setError('OnlyOffice Document Server 不可用，请确保服务已启动');
        setLoading(false);
        return;
      }

      // 2. 获取文档配置
      const doc = await documentApi.getDocument(docId);
      setDocTitle(doc.title);

      if (!doc.onlyoffice_config) {
        setError('文档缺少 OnlyOffice 配置信息');
        setLoading(false);
        return;
      }

      // 3. 合并编辑模式
      const config: OnlyOfficeConfig = {
        ...doc.onlyoffice_config,
        editorConfig: {
          ...doc.onlyoffice_config.editorConfig,
          mode,
          lang: 'zh',
        },
      };

      // 4. 创建连接器并初始化
      const connector = new OnlyOfficeConnector({ serverUrl });
      connectorRef.current = connector;

      await connector.init(containerId, config, {
        onReady: () => {
          setLoading(false);
        },
        onSave: () => {
          onSaved?.();
        },
        onError: (err) => {
          const msg = `${err.errorCode}: ${err.errorDescription}`;
          setError(msg);
          onError?.(msg);
          setLoading(false);
        },
        onClose: () => {
          // 编辑器关闭
        },
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : '加载文档失败';
      setError(msg);
      onError?.(msg);
      setLoading(false);
    }
  }, [docId, mode, containerId, onSaved, onError]);

  useEffect(() => {
    initEditor();

    return () => {
      // 组件卸载时销毁编辑器
      connectorRef.current?.destroy();
      connectorRef.current = null;
    };
  }, [initEditor]);

  /** 重试加载 */
  const handleRetry = useCallback(() => {
    connectorRef.current?.destroy();
    connectorRef.current = null;
    initEditor();
  }, [initEditor]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* 顶部标题栏 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '6px 12px',
        borderBottom: '1px solid var(--hairline, rgba(255,255,255,0.06))',
        background: 'var(--glass-bg, rgba(255,255,255,0.03))',
        fontSize: 13, fontWeight: 500,
        color: 'var(--body, #e0e0e0)',
      }}>
        <FileText size={14} style={{ color: 'var(--accent, #6366f1)' }} />
        <span>{docTitle || '文档编辑器'}</span>
        <div style={{ flex: 1 }} />
        {/* 提取到 AI 写作台 */}
        <button
          onClick={handleExtractToWriting}
          disabled={extracting}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '3px 10px', borderRadius: 4, fontSize: 11,
            border: '1px solid var(--accent, #6366f1)',
            background: 'transparent', color: 'var(--accent, #6366f1)',
            cursor: extracting ? 'wait' : 'pointer',
            opacity: extracting ? 0.6 : 1,
          }}
        >
          {extracting ? <Loader2 size={12} className="animate-spin" /> : <ArrowLeftRight size={12} />}
          提取到 AI 写作台
        </button>
        {/* 格式转换 */}
        <button
          onClick={() => setShowConvertDialog(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '3px 10px', borderRadius: 4, fontSize: 11,
            border: '1px solid var(--hairline, rgba(255,255,255,0.15))',
            background: 'transparent', color: 'var(--body, #e0e0e0)',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={12} />
          格式转换
        </button>
        <span style={{
          fontSize: 10, padding: '2px 8px', borderRadius: 10,
          background: ooAvailable ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)',
          color: ooAvailable ? '#10b981' : '#ef4444',
        }}>
          {ooAvailable ? 'OnlyOffice 已连接' : 'OnlyOffice 不可用'}
        </span>
      </div>

      {/* 编辑器容器 */}
      <div style={{ flex: 1, position: 'relative' }}>
        {/* 加载状态 */}
        {loading && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 10,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 12,
            background: 'var(--canvas, #1a1a2e)',
          }}>
            <Loader2 size={32} className="animate-spin" style={{ color: 'var(--accent, #6366f1)' }} />
            <span style={{ fontSize: 13, color: 'var(--mute, #888)' }}>
              正在加载文档编辑器...
            </span>
          </div>
        )}

        {/* 错误状态 */}
        {error && (
          <div style={{
            position: 'absolute', inset: 0, zIndex: 10,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', gap: 12,
            background: 'var(--canvas, #1a1a2e)',
          }}>
            <AlertTriangle size={40} style={{ color: '#f59e0b' }} />
            <div style={{ fontSize: 14, color: 'var(--body, #e0e0e0)', textAlign: 'center', maxWidth: 360 }}>
              {error}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={handleRetry}
                style={{
                  padding: '6px 16px', borderRadius: 6, fontSize: 12,
                  background: 'var(--accent, #6366f1)', color: '#fff',
                  border: 'none', cursor: 'pointer',
                }}
              >
                重试
              </button>
              {isTauri() && !ooAvailable && (
                <button
                  onClick={async () => {
                    try {
                      const { invoke } = await import('@tauri-apps/api/core');
                      await invoke('open_file_in_system', { path: docId });
                    } catch (e) {
                      console.error('打开文件失败:', e);
                    }
                  }}
                  style={{
                    padding: '6px 16px', borderRadius: 6, fontSize: 12,
                    background: 'transparent', color: 'var(--body, #e0e0e0)',
                    border: '1px solid var(--hairline, rgba(255,255,255,0.15))', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4,
                  }}
                >
                  <ExternalLink size={12} />
                  用系统默认程序打开
                </button>
              )}
            </div>
          </div>
        )}

        {/* OnlyOffice 编辑器挂载点 */}
        <div
          ref={containerRef}
          id={containerId}
          style={{ width: '100%', height: '100%' }}
        />
      </div>

      {/* 格式转换对话框 */}
      <ConvertDialog
        visible={showConvertDialog}
        onClose={() => setShowConvertDialog(false)}
        sourceContent=""
        sourceType="docx"
      />
    </div>
  );
};
