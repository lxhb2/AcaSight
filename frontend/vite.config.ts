import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

const withVisualizer = process.env.ANALYZE === '1';

async function getPlugins() {
  const plugins = [react()];
  if (withVisualizer) {
    const { visualizer } = await import('rollup-plugin-visualizer');
    plugins.push(
      visualizer({
        filename: 'dist/stats.html',
        open: false,
        gzipSize: true,
        brotliSize: true,
      }),
    );
  }
  return plugins;
}

function chunkStrategy(id: string): string | undefined {
  if (!id.includes('node_modules')) return undefined;

  const heavyChunks: [RegExp, string][] = [
    [/plotly\.js|react-plotly\.js/, 'plotly'],
    [/@excalidraw\/excalidraw/, 'excalidraw'],
    [/mermaid/, 'mermaid'],
    [/katex|@milkdown/, 'milkdown'],
    [/react-pdf|pdfjs-dist/, 'pdf'],
    [/react-force-graph/, 'force-graph'],
    [/monaco-editor/, 'monaco'],
    [/recharts/, 'recharts'],
    [/fabric/, 'fabric'],
    [/exceljs/, 'exceljs'],
    [/jspdf|html2canvas/, 'pdf-export'],
  ];

  for (const [re, chunk] of heavyChunks) {
    if (re.test(id)) return chunk;
  }

  return undefined;
}

export default defineConfig(async () => ({
  plugins: await getPlugins(),
  define: {
    global: 'globalThis',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    dedupe: ['react', 'react-dom'],
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: chunkStrategy,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.d.ts',
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/__tests__/setup.ts',
        'src/main.tsx',
        'src/types/**',
      ],
    },
  },
}));
