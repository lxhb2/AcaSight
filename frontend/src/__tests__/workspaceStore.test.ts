import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWorkspaceStore } from '@/store/workspaceStore';

describe('useWorkspaceStore', () => {
  beforeEach(() => {
    localStorage.clear();
    useWorkspaceStore.setState({
      activeWorkspaceId: 'default',
      panelStates: {},
      writingDrafts: {},
      searchHistory: [],
      recentFiles: [],
    });
  });

  it('should set panel state', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    act(() => {
      result.current.setPanelState('search', true, 320);
    });
    expect(result.current.panelStates.search).toEqual({ open: true, width: 320 });
  });

  it('should manage writing drafts', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    act(() => {
      result.current.setWritingDraft('doc1', 'Hello world');
    });
    expect(result.current.writingDrafts.doc1).toBe('Hello world');

    act(() => {
      result.current.removeWritingDraft('doc1');
    });
    expect(result.current.writingDrafts.doc1).toBeUndefined();
  });

  it('should manage search history with dedup and limit', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    act(() => {
      result.current.addSearchHistory('query1');
      result.current.addSearchHistory('query2');
      result.current.addSearchHistory('query1');
    });
    expect(result.current.searchHistory).toEqual(['query1', 'query2']);
    expect(result.current.searchHistory[0]).toBe('query1');
  });

  it('should clear search history', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    act(() => {
      result.current.addSearchHistory('query1');
      result.current.clearSearchHistory();
    });
    expect(result.current.searchHistory).toEqual([]);
  });

  it('should manage recent files with dedup and limit', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    act(() => {
      for (let i = 0; i < 25; i++) {
        result.current.addRecentFile(`file${i}.pdf`);
      }
    });
    expect(result.current.recentFiles).toHaveLength(20);
    expect(result.current.recentFiles[0]).toBe('file24.pdf');
  });

  it('should persist state to localStorage', () => {
    const { result } = renderHook(() => useWorkspaceStore());
    act(() => {
      result.current.setPanelState('search', true, 320);
      result.current.addSearchHistory('test query');
    });

    const stored = localStorage.getItem('acasight-workspace');
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!);
    expect(parsed.state.panelStates.search).toEqual({ open: true, width: 320 });
    expect(parsed.state.searchHistory).toContain('test query');
  });
});
