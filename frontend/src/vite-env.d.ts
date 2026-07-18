/// <reference types="vite/client" />

declare module '*?url' {
  const url: string;
  export default url;
}

// Intl.Segmenter polyfill types (ES2022+)
interface SegmenterSegment {
  segment: string;
  index: number;
  input: string;
  isWordLike?: boolean;
}

interface SegmenterOptions {
  granularity?: 'grapheme' | 'word' | 'sentence';
  localeMatcher?: 'best fit' | 'lookup';
}

interface Segmenter {
  segment(input: string): Iterable<SegmenterSegment>;
  resolvedOptions(): { locale: string; granularity: string };
}

declare namespace Intl {
  const Segmenter: {
    new (locales?: string | string[], options?: SegmenterOptions): Segmenter;
    supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: 'best fit' | 'lookup' }): string[];
  };
}
