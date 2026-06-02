import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { workspaceStateApi } from '@/services/api';

interface WorkspaceState {
  activeWorkspaceId: string;
  panelStates: Record<string, { open: boolean; width: number }>;
  writingDrafts: Record<string, string>;
  searchHistory: string[];
  recentFiles: string[];
  lastSaved: number | null;
  isSyncing: boolean;

  setActiveWorkspace: (id: string) => void;
  setPanelState: (panelId: string, open: boolean, width?: number) => void;
  setWritingDraft: (documentId: string, content: string) => void;
  removeWritingDraft: (documentId: string) => void;
  addSearchHistory: (query: string) => void;
  clearSearchHistory: () => void;
  addRecentFile: (path: string) => void;
  syncToServer: () => Promise<void>;
  restoreFromServer: (workspaceId?: string) => Promise<void>;
}

const DEFAULT_WORKSPACE_ID = 'default';

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      activeWorkspaceId: DEFAULT_WORKSPACE_ID,
      panelStates: {},
      writingDrafts: {},
      searchHistory: [],
      recentFiles: [],
      lastSaved: null,
      isSyncing: false,

      setActiveWorkspace: (id) => set({ activeWorkspaceId: id }),

      setPanelState: (panelId, open, width) =>
        set((s) => ({
          panelStates: {
            ...s.panelStates,
            [panelId]: { open, width: width ?? s.panelStates[panelId]?.width ?? 400 },
          },
        })),

      setWritingDraft: (documentId, content) =>
        set((s) => ({
          writingDrafts: { ...s.writingDrafts, [documentId]: content },
        })),

      removeWritingDraft: (documentId) =>
        set((s) => {
          const drafts = { ...s.writingDrafts };
          delete drafts[documentId];
          return { writingDrafts: drafts };
        }),

      addSearchHistory: (query) =>
        set((s) => {
          const filtered = s.searchHistory.filter((q) => q !== query);
          return { searchHistory: [query, ...filtered].slice(0, 50) };
        }),

      clearSearchHistory: () => set({ searchHistory: [] }),

      addRecentFile: (path) =>
        set((s) => {
          const filtered = s.recentFiles.filter((p) => p !== path);
          return { recentFiles: [path, ...filtered].slice(0, 20) };
        }),

      syncToServer: async () => {
        const state = get();
        if (state.isSyncing) return;
        set({ isSyncing: true });
        try {
          const { activeWorkspaceId, panelStates, writingDrafts, searchHistory, recentFiles } = state;
          await workspaceStateApi.save(activeWorkspaceId, {
            panelStates,
            writingDrafts,
            searchHistory,
            recentFiles,
          });
          set({ lastSaved: Date.now() });
        } catch (_e: unknown) {
          // silent — local state is still preserved
        } finally {
          set({ isSyncing: false });
        }
      },

      restoreFromServer: async (workspaceId) => {
        const id = workspaceId ?? get().activeWorkspaceId;
        set({ isSyncing: true });
        try {
          const res = await workspaceStateApi.restore(id);
          if (res.data?.state) {
            const serverState = res.data.state as Record<string, unknown>;
            set({
              activeWorkspaceId: id,
              panelStates: (serverState.panelStates as WorkspaceState['panelStates']) ?? {},
              writingDrafts: (serverState.writingDrafts as WorkspaceState['writingDrafts']) ?? {},
              searchHistory: (serverState.searchHistory as WorkspaceState['searchHistory']) ?? [],
              recentFiles: (serverState.recentFiles as WorkspaceState['recentFiles']) ?? [],
            });
          }
        } catch (_e: unknown) {
          // silent — local state is still preserved
        } finally {
          set({ isSyncing: false });
        }
      },
    }),
    {
      name: 'acasight-workspace',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        activeWorkspaceId: state.activeWorkspaceId,
        panelStates: state.panelStates,
        writingDrafts: state.writingDrafts,
        searchHistory: state.searchHistory,
        recentFiles: state.recentFiles,
      }),
    },
  ),
);
