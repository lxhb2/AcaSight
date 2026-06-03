import { create } from 'zustand';
import type { PlotSchema, XRDDataSet, PDFCard, XRDConfig } from '@/types/plot';
import { DEFAULT_XRD_CONFIG } from '@/types/plot';

export type PlotPhase = 'idle' | 'importing' | 'processing' | 'rendering' | 'exporting';

export interface PlotEditorState {
  selectedElement: string | null; // trace key
  layers: LayerConfig[];
}

export interface LayerConfig {
  id: string;
  name: string;
  type: 'curve' | 'stick' | 'annotation';
  visible: boolean;
  color?: string;
}

interface PlotState {
  // Phase
  phase: PlotPhase;
  setPhase: (phase: PlotPhase) => void;

  // Core schema
  plotSchema: PlotSchema | null;
  setPlotSchema: (schema: PlotSchema | null) => void;

  // XRD specific
  xrdDatasets: XRDDataSet[];
  addXrdDataset: (dataset: XRDDataSet) => void;
  removeXrdDataset: (index: number) => void;
  updateXrdDataset: (index: number, dataset: Partial<XRDDataSet>) => void;
  clearXrdDatasets: () => void;

  pdfCards: PDFCard[];
  addPdfCard: (card: PDFCard) => void;
  removePdfCard: (index: number) => void;
  updatePdfCard: (index: number, card: Partial<PDFCard>) => void;
  clearPdfCards: () => void;

  xrdConfig: XRDConfig;
  updateXrdConfig: (config: Partial<XRDConfig>) => void;

  // Editor
  editorState: PlotEditorState;
  setSelectedElement: (key: string | null) => void;

  // Theme
  currentThemeId: string;
  setCurrentThemeId: (id: string) => void;

  // Async task
  processingTaskId: string | null;
  setProcessingTaskId: (id: string | null) => void;

  // Reset
  reset: () => void;
}

const initialState = {
  phase: 'idle' as PlotPhase,
  plotSchema: null,
  xrdDatasets: [],
  pdfCards: [],
  xrdConfig: DEFAULT_XRD_CONFIG,
  editorState: { selectedElement: null, layers: [] },
  currentThemeId: 'default',
  processingTaskId: null,
};

export const usePlotStore = create<PlotState>((set) => ({
  ...initialState,

  setPhase: (phase) => set({ phase }),
  setPlotSchema: (plotSchema) => set({ plotSchema }),

  // XRD datasets
  addXrdDataset: (dataset) => set((s) => ({ xrdDatasets: [...s.xrdDatasets, dataset] })),
  removeXrdDataset: (index) => set((s) => ({ xrdDatasets: s.xrdDatasets.filter((_, i) => i !== index) })),
  updateXrdDataset: (index, dataset) =>
    set((s) => ({
      xrdDatasets: s.xrdDatasets.map((d, i) => (i === index ? { ...d, ...dataset } : d)),
    })),
  clearXrdDatasets: () => set({ xrdDatasets: [] }),

  // PDF cards
  addPdfCard: (card) => set((s) => ({ pdfCards: [...s.pdfCards, card] })),
  removePdfCard: (index) => set((s) => ({ pdfCards: s.pdfCards.filter((_, i) => i !== index) })),
  updatePdfCard: (index, card) =>
    set((s) => ({
      pdfCards: s.pdfCards.map((c, i) => (i === index ? { ...c, ...card } : c)),
    })),
  clearPdfCards: () => set({ pdfCards: [] }),

  // Config
  updateXrdConfig: (config) => set((s) => ({ xrdConfig: { ...s.xrdConfig, ...config } })),

  // Editor
  setSelectedElement: (key) =>
    set((s) => ({ editorState: { ...s.editorState, selectedElement: key } })),

  // Theme
  setCurrentThemeId: (id) => set({ currentThemeId: id }),

  // Async
  setProcessingTaskId: (id) => set({ processingTaskId: id }),

  // Reset
  reset: () => set(initialState),
}));
