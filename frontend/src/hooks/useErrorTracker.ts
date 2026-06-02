import { useCallback, useEffect, useRef } from 'react';

interface ErrorEntry {
  id: string;
  timestamp: number;
  type: 'runtime' | 'promise' | 'render' | 'network' | 'custom';
  message: string;
  stack?: string;
  metadata?: Record<string, unknown>;
}

interface UseErrorTrackerOptions {
  maxEntries?: number;
  onCapture?: (entry: ErrorEntry) => void;
}

export function useErrorTracker(options: UseErrorTrackerOptions = {}) {
  const { maxEntries = 100, onCapture } = options;
  const errorsRef = useRef<ErrorEntry[]>([]);
  const onCaptureRef = useRef(onCapture);
  onCaptureRef.current = onCapture;

  const capture = useCallback(
    (type: ErrorEntry['type'], message: string, stack?: string, metadata?: Record<string, unknown>) => {
      const entry: ErrorEntry = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        timestamp: Date.now(),
        type,
        message,
        stack,
        metadata,
      };

      errorsRef.current = [entry, ...errorsRef.current].slice(0, maxEntries);
      onCaptureRef.current?.(entry);
      return entry;
    },
    [maxEntries],
  );

  useEffect(() => {
    const handleRuntimeError = (event: ErrorEvent) => {
      capture('runtime', event.message, event.error?.stack, {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
      });
      event.preventDefault();
    };

    const handlePromiseRejection = (event: PromiseRejectionEvent) => {
      const message =
        event.reason instanceof Error
          ? event.reason.message
          : String(event.reason);
      const stack =
        event.reason instanceof Error ? event.reason.stack : undefined;
      capture('promise', message, stack);
      event.preventDefault();
    };

    window.addEventListener('error', handleRuntimeError);
    window.addEventListener('unhandledrejection', handlePromiseRejection);

    return () => {
      window.removeEventListener('error', handleRuntimeError);
      window.removeEventListener('unhandledrejection', handlePromiseRejection);
    };
  }, [capture]);

  const getErrors = useCallback(() => errorsRef.current, []);
  const getRecentErrors = useCallback(
    (count = 10) => errorsRef.current.slice(0, count),
    [],
  );
  const clearErrors = useCallback(() => {
    errorsRef.current = [];
  }, []);

  return { capture, getErrors, getRecentErrors, clearErrors };
}
