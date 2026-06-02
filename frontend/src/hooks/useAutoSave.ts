import { useState, useEffect, useCallback, useRef } from 'react';

interface UseAutoSaveOptions<T> {
  data: T;
  saveFn: (data: T) => Promise<void> | void;
  intervalMs?: number;
  debounceMs?: number;
  enabled?: boolean;
  onError?: (error: unknown) => void;
}

interface UseAutoSaveReturn {
  lastSaved: Date | null;
  isSaving: boolean;
  hasUnsavedChanges: boolean;
  saveNow: () => Promise<void>;
  markSaved: () => void;
}

export function useAutoSave<T>({
  data,
  saveFn,
  intervalMs = 30000,
  debounceMs = 2000,
  enabled = true,
  onError,
}: UseAutoSaveOptions<T>): UseAutoSaveReturn {
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(true);

  const dataRef = useRef(data);
  const lastSavedDataRef = useRef(data);
  const saveFnRef = useRef(saveFn);
  const onErrorRef = useRef(onError);
  saveFnRef.current = saveFn;
  onErrorRef.current = onError;

  useEffect(() => {
    dataRef.current = data;
    if (data !== lastSavedDataRef.current) {
      setHasUnsavedChanges(true);
    }
  }, [data]);

  const saveNow = useCallback(async () => {
    if (isSaving) return;
    setIsSaving(true);
    try {
      await saveFnRef.current(dataRef.current);
      lastSavedDataRef.current = dataRef.current;
      setLastSaved(new Date());
      setHasUnsavedChanges(false);
    } catch (e: unknown) {
      onErrorRef.current?.(e);
    } finally {
      setIsSaving(false);
    }
  }, [isSaving]);

  const markSaved = useCallback(() => {
    lastSavedDataRef.current = dataRef.current;
    setLastSaved(new Date());
    setHasUnsavedChanges(false);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const debounceTimer = setTimeout(() => {
      if (hasUnsavedChanges) {
        saveNow();
      }
    }, debounceMs);

    return () => clearTimeout(debounceTimer);
  }, [hasUnsavedChanges, debounceMs, enabled, saveNow]);

  useEffect(() => {
    if (!enabled) return;

    const interval = setInterval(() => {
      if (hasUnsavedChanges) {
        saveNow();
      }
    }, intervalMs);

    return () => clearInterval(interval);
  }, [hasUnsavedChanges, intervalMs, enabled, saveNow]);

  useEffect(() => {
    if (!enabled) return;

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedChanges, enabled]);

  return { lastSaved, isSaving, hasUnsavedChanges, saveNow, markSaved };
}
