import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAutoSave } from '@/hooks/useAutoSave';
import { useErrorTracker } from '@/hooks/useErrorTracker';

describe('useAutoSave', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize with no saved state', () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useAutoSave({ data: 'test', saveFn, intervalMs: 1000, debounceMs: 100 }),
    );
    expect(result.current.lastSaved).toBeNull();
    expect(result.current.isSaving).toBe(false);
    expect(result.current.hasUnsavedChanges).toBe(true);
  });

  it('should call saveFn after debounce delay', async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    renderHook(() =>
      useAutoSave({ data: 'test', saveFn, intervalMs: 60000, debounceMs: 500 }),
    );

    await act(async () => {
      vi.advanceTimersByTime(600);
    });

    expect(saveFn).toHaveBeenCalledTimes(1);
  });

  it('should not save when disabled', async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    renderHook(() =>
      useAutoSave({ data: 'test', saveFn, intervalMs: 1000, debounceMs: 100, enabled: false }),
    );

    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    expect(saveFn).not.toHaveBeenCalled();
  });

  it('should mark saved after successful save', async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useAutoSave({ data: 'test', saveFn, intervalMs: 60000, debounceMs: 100 }),
    );

    await act(async () => {
      vi.advanceTimersByTime(200);
    });

    expect(result.current.hasUnsavedChanges).toBe(false);
    expect(result.current.lastSaved).not.toBeNull();
  });
});

describe('useErrorTracker', () => {
  it('should capture errors manually', () => {
    const { result } = renderHook(() => useErrorTracker());
    const entry = result.current.capture('custom', 'test error');
    expect(entry.message).toBe('test error');
    expect(entry.type).toBe('custom');
  });

  it('should retrieve recent errors', () => {
    const { result } = renderHook(() => useErrorTracker());
    result.current.capture('custom', 'error 1');
    result.current.capture('custom', 'error 2');
    const recent = result.current.getRecentErrors(1);
    expect(recent).toHaveLength(1);
    expect(recent[0].message).toBe('error 2');
  });

  it('should clear errors', () => {
    const { result } = renderHook(() => useErrorTracker());
    result.current.capture('custom', 'error');
    result.current.clearErrors();
    expect(result.current.getErrors()).toHaveLength(0);
  });

  it('should respect maxEntries', () => {
    const { result } = renderHook(() => useErrorTracker({ maxEntries: 2 }));
    result.current.capture('custom', 'e1');
    result.current.capture('custom', 'e2');
    result.current.capture('custom', 'e3');
    expect(result.current.getErrors()).toHaveLength(2);
  });
});
