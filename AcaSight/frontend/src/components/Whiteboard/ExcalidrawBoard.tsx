import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import { Save, Download, Upload, Trash2 } from 'lucide-react';

interface ExcalidrawBoardProps {
  boardId?: string;
  onSave?: (id: string, json: string) => void;
}

const STORAGE_PREFIX = 'acasight-wb-';

export const ExcalidrawBoard: React.FC<ExcalidrawBoardProps> = ({
  boardId,
  onSave,
}) => {
  const [excalidrawAPI, setExcalidrawAPI] = useState<ExcalidrawImperativeAPI | null>(null);
  const [saving, setSaving] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    document.documentElement.classList.contains('dark') ? 'dark' : 'light'
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const storageKey = boardId || 'default';

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.classList.contains('dark') ? 'dark' : 'light');
    });
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!excalidrawAPI) return;
    try {
      const saved = localStorage.getItem(`${STORAGE_PREFIX}${storageKey}`);
      if (saved) {
        const data = JSON.parse(saved);
        if (data.elements) {
          excalidrawAPI.updateScene({
            elements: data.elements,
            appState: data.appState,
          });
        }
      }
    } catch (e) {
      console.warn('Load board failed:', e);
    }
  }, [excalidrawAPI, storageKey]);

  const handleSave = useCallback(() => {
    if (!excalidrawAPI) return;
    setSaving(true);
    try {
      const elements = excalidrawAPI.getSceneElements();
      const appState = excalidrawAPI.getAppState();
      const data = { elements, appState: { viewBackgroundColor: appState.viewBackgroundColor } };
      localStorage.setItem(`${STORAGE_PREFIX}${storageKey}`, JSON.stringify(data));
      onSave?.(storageKey, JSON.stringify(data));
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }, [excalidrawAPI, storageKey, onSave]);

  const handleExportJSON = useCallback(() => {
    if (!excalidrawAPI) return;
    try {
      const elements = excalidrawAPI.getSceneElements();
      const appState = excalidrawAPI.getAppState();
      const files = excalidrawAPI.getFiles();
      const exportData = {
        type: 'excalidraw',
        version: 2,
        source: 'acasight',
        elements,
        appState: {
          viewBackgroundColor: appState.viewBackgroundColor,
          gridSize: appState.gridSize,
        },
        files: Object.fromEntries(
          Object.entries(files).map(([id, file]) => [
            id,
            { ...file, dataURL: file.dataURL },
          ])
        ),
      };
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `whiteboard-${storageKey}.excalidraw`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    }
  }, [excalidrawAPI, storageKey]);

  const handleImportJSON = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string);
        const elements = data.elements || [];
        const appState = data.appState || {};
        if (excalidrawAPI) {
          excalidrawAPI.updateScene({ elements, appState });
          localStorage.setItem(
            `${STORAGE_PREFIX}${storageKey}`,
            JSON.stringify({ elements, appState })
          );
        }
      } catch (err) {
        console.error(err);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  }, [excalidrawAPI, storageKey]);

  const handleClear = useCallback(() => {
    if (excalidrawAPI && confirm('确定清空白板？')) {
      excalidrawAPI.updateScene({ elements: [] });
      localStorage.removeItem(`${STORAGE_PREFIX}${storageKey}`);
    }
  }, [excalidrawAPI, storageKey]);

  const btnClass =
    'p-1.5 rounded hover:bg-[var(--bg-hover)] text-[var(--body)] hover:text-[var(--ink)] transition-colors border-none bg-transparent cursor-pointer flex items-center gap-1 text-xs';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        background: 'var(--bg-primary)',
        color: 'var(--ink)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '4px 8px',
          borderBottom: '1px solid var(--border-color)',
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: 12, color: 'var(--mute)', marginRight: 8 }}>
          白板
        </span>
        <div
          style={{
            width: 1,
            height: 20,
            background: 'var(--border-color)',
            margin: '0 4px',
          }}
        />
        <button
          onClick={handleSave}
          disabled={saving}
          title="保存到本地"
          className={btnClass}
        >
          <Save size={14} />
          {saving ? '保存中...' : '保存'}
        </button>
        <button
          onClick={handleExportJSON}
          title="导出为 .excalidraw JSON 文件"
          className={btnClass}
        >
          <Download size={14} />
          导出
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          title="导入 .excalidraw JSON 文件"
          className={btnClass}
        >
          <Upload size={14} />
          导入
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,.excalidraw"
          onChange={handleImportJSON}
          style={{ display: 'none' }}
        />
        <div style={{ flex: 1 }} />
        <button
          onClick={handleClear}
          title="清空白板"
          className={btnClass}
          style={{ color: '#ef4444' }}
        >
          <Trash2 size={14} />
          清空
        </button>
      </div>

      <div style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
        <style>{`
          .excalidraw .ToolIcon__icon {
            width: 32px !important;
            height: 32px !important;
          }
          .excalidraw .ToolIcon_type_radio + .ToolIcon__icon svg,
          .excalidraw .ToolIcon_type_checkbox + .ToolIcon__icon svg {
            width: 16px !important;
            height: 16px !important;
          }
          .excalidraw .App-toolbar {
            padding: 2px !important;
          }
          .excalidraw .Island {
            padding: 2px !important;
          }
          .excalidraw .App-toolbar-container {
            gap: 2px !important;
          }
          .excalidraw .sidebar-trigger {
            width: 36px !important;
            height: 36px !important;
          }
          .excalidraw .sidebar-trigger__label {
            font-size: 10px !important;
          }
          .excalidraw .ToolIcon__keybinding {
            font-size: 8px !important;
          }
        `}</style>
        <Excalidraw
          excalidrawAPI={(api: ExcalidrawImperativeAPI) => setExcalidrawAPI(api)}
          initialData={{
            appState: {
              theme,
              viewBackgroundColor: theme === 'dark' ? '#1a1a1a' : '#ffffff',
            },
          }}
          UIOptions={{
            canvasActions: {
              changeViewBackgroundColor: true,
              clearCanvas: true,
              export: { saveFileToDisk: true },
              loadScene: false,
              saveToActiveFile: true,
              toggleTheme: true,
            },
            tools: { image: true },
          }}
          langCode="zh-CN"
          theme={theme}
          onChange={() => {}}
        />
      </div>
    </div>
  );
};
