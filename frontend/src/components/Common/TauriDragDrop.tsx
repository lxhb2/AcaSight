/**
 * TauriDragDrop — 全局文件拖拽处理
 * 在Tauri桌面端监听文件拖放事件，触发文件导入
 */
import { useEffect, useCallback } from 'react';
import { isTauri, onFileDrop, type FileDropEvent } from '@/lib/tauri-adapter';

interface TauriDragDropProps {
  onFilesDropped: (paths: string[]) => void;
}

export const TauriDragDrop: React.FC<TauriDragDropProps> = ({ onFilesDropped }) => {
  const handleDrop = useCallback((event: FileDropEvent) => {
    onFilesDropped(event.paths);
  }, [onFilesDropped]);

  useEffect(() => {
    if (!isTauri()) return;

    let unlisten: (() => void) | null = null;

    onFileDrop(handleDrop).then(fn => {
      unlisten = fn;
    });

    return () => {
      unlisten?.();
    };
  }, [handleDrop]);

  return null; // No UI — invisible event listener
};
