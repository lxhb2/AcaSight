import { describe, it, expect } from 'vitest';

interface UnifiedPaper {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  doi?: string;
  journal?: string;
  cited_by_count?: number;
  is_open_access: boolean;
  pdf_url?: string;
  source: string;
  source_label: string;
}

const SOURCE_LABELS: Record<string, string> = {
  core: 'CORE',
  openalex: 'OpenAlex',
  semanticscholar: 'Semantic Scholar',
  crossref: 'Crossref',
  europepmc: 'Europe PMC',
  arxiv: 'arXiv',
};

const CURRENT_YEAR = new Date().getFullYear();

function normalizePaper(raw: Record<string, unknown>, source: string): UnifiedPaper {
  return {
    id: (raw.id as string) || (raw.doi as string) || (raw.arxiv_id as string) || `${source}-${Math.random().toString(36).slice(2)}`,
    title: ((raw.title as string) || 'Untitled').trim(),
    authors: Array.isArray(raw.authors) ? raw.authors as string[] : [],
    year: raw.year ? Number(raw.year) : null,
    abstract: ((raw.abstract as string) || '').replace(/<[^>]*>/g, '').trim(),
    doi: (raw.doi as string) || undefined,
    journal: (raw.journal as string) || undefined,
    cited_by_count: raw.cited_by_count != null ? (raw.cited_by_count as number) : undefined,
    is_open_access: Boolean(raw.is_open_access),
    pdf_url: (raw.pdf_url as string) || undefined,
    source,
    source_label: SOURCE_LABELS[source] || source,
  };
}

function mergeResults(sourceResults: Record<string, { results: Record<string, unknown>[] }>): UnifiedPaper[] {
  const allPapers: UnifiedPaper[] = [];
  const seenDois = new Set<string>();
  const seenTitles = new Set<string>();

  for (const [source, data] of Object.entries(sourceResults)) {
    const results = data?.results || [];
    for (const raw of results) {
      if (!raw || typeof raw !== 'object') continue;
      const paper = normalizePaper(raw, source);
      const normTitle = paper.title.toLowerCase().replace(/[^a-z0-9\u4e00-\u9fff]/g, '');
      if (paper.doi && seenDois.has(paper.doi.toLowerCase())) continue;
      if (seenTitles.has(normTitle)) continue;
      if (paper.doi) seenDois.add(paper.doi.toLowerCase());
      seenTitles.add(normTitle);
      allPapers.push(paper);
    }
  }

  return allPapers;
}

function sortPapers(papers: UnifiedPaper[], sort: string, _query?: string): UnifiedPaper[] {
  const sorted = [...papers];
  switch (sort) {
    case 'citations':
      sorted.sort((a, b) => (b.cited_by_count ?? 0) - (a.cited_by_count ?? 0));
      break;
    case 'date_desc':
      sorted.sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
      break;
    case 'date_asc':
      sorted.sort((a, b) => (a.year ?? 9999) - (b.year ?? 9999));
      break;
  }
  return sorted;
}

function getYearRange(filter: string): { from?: number; to?: number } {
  const now = new Date().getFullYear();
  switch (filter) {
    case '2025': return { from: 2025, to: 2025 };
    case '2024': return { from: 2024, to: 2024 };
    case '2023': return { from: 2023, to: 2023 };
    case '3y': return { from: now - 2, to: now };
    case '5y': return { from: now - 4, to: now };
    default: return {};
  }
}

describe('SearchPage - normalizePaper', () => {
  it('should normalize a complete paper record', () => {
    const raw = {
      id: '123',
      title: '  Deep Learning  ',
      authors: ['Alice', 'Bob'],
      year: 2024,
      abstract: 'A study on <b>deep</b> learning',
      doi: '10.1234/test',
      journal: 'Nature',
      cited_by_count: 42,
      is_open_access: true,
      pdf_url: 'https://example.com/paper.pdf',
    };
    const paper = normalizePaper(raw, 'core');
    expect(paper.id).toBe('123');
    expect(paper.title).toBe('Deep Learning');
    expect(paper.authors).toEqual(['Alice', 'Bob']);
    expect(paper.year).toBe(2024);
    expect(paper.abstract).toBe('A study on deep learning');
    expect(paper.doi).toBe('10.1234/test');
    expect(paper.source_label).toBe('CORE');
    expect(paper.is_open_access).toBe(true);
  });

  it('should handle minimal paper record', () => {
    const paper = normalizePaper({}, 'semanticscholar');
    expect(paper.title).toBe('Untitled');
    expect(paper.authors).toEqual([]);
    expect(paper.year).toBeNull();
    expect(paper.abstract).toBe('');
    expect(paper.is_open_access).toBe(false);
    expect(paper.source_label).toBe('Semantic Scholar');
  });

  it('should strip HTML from abstract', () => {
    const paper = normalizePaper({ abstract: '<p>Hello</p> <b>World</b>' }, 'core');
    expect(paper.abstract).toBe('Hello World');
  });

  it('should use doi as fallback id', () => {
    const paper = normalizePaper({ doi: '10.1234/fallback' }, 'core');
    expect(paper.id).toBe('10.1234/fallback');
  });

  it('should handle non-array authors', () => {
    const paper = normalizePaper({ authors: 'Alice, Bob' }, 'core');
    expect(paper.authors).toEqual([]);
  });
});

describe('SearchPage - mergeResults', () => {
  it('should merge papers from multiple sources', () => {
    const results = {
      core: { results: [{ id: '1', title: 'Paper A', doi: '10.1/a' }] },
      openalex: { results: [{ id: '2', title: 'Paper B', doi: '10.1/b' }] },
    };
    const merged = mergeResults(results as never);
    expect(merged).toHaveLength(2);
    expect(merged[0].source).toBe('core');
    expect(merged[1].source).toBe('openalex');
  });

  it('should deduplicate by DOI (case-insensitive)', () => {
    const results = {
      core: { results: [{ id: '1', title: 'Paper A', doi: '10.1/A' }] },
      openalex: { results: [{ id: '2', title: 'Paper B', doi: '10.1/a' }] },
    };
    const merged = mergeResults(results as never);
    expect(merged).toHaveLength(1);
  });

  it('should deduplicate by normalized title', () => {
    const results = {
      core: { results: [{ id: '1', title: 'Deep Learning for NLP' }] },
      openalex: { results: [{ id: '2', title: 'deep-learning for nlp' }] },
    };
    const merged = mergeResults(results as never);
    expect(merged).toHaveLength(1);
  });

  it('should handle empty results', () => {
    expect(mergeResults({})).toEqual([]);
  });

  it('should skip null/invalid entries', () => {
    const results = {
      core: { results: [null, undefined, { id: '1', title: 'Valid' }] as unknown[] },
    };
    const merged = mergeResults(results as never);
    expect(merged).toHaveLength(1);
    expect(merged[0].title).toBe('Valid');
  });
});

describe('SearchPage - sortPapers', () => {
  const papers: UnifiedPaper[] = [
    { id: '1', title: 'Old Paper', authors: [], year: 2020, abstract: '', is_open_access: false, source: 'core', source_label: 'CORE', cited_by_count: 100 },
    { id: '2', title: 'New Paper', authors: [], year: 2024, abstract: '', is_open_access: false, source: 'core', source_label: 'CORE', cited_by_count: 10 },
    { id: '3', title: 'Mid Paper', authors: [], year: 2022, abstract: '', is_open_access: false, source: 'core', source_label: 'CORE', cited_by_count: 50 },
  ];

  it('should sort by citations descending', () => {
    const sorted = sortPapers(papers, 'citations');
    expect(sorted[0].cited_by_count).toBe(100);
    expect(sorted[2].cited_by_count).toBe(10);
  });

  it('should sort by date descending', () => {
    const sorted = sortPapers(papers, 'date_desc');
    expect(sorted[0].year).toBe(2024);
    expect(sorted[2].year).toBe(2020);
  });

  it('should sort by date ascending', () => {
    const sorted = sortPapers(papers, 'date_asc');
    expect(sorted[0].year).toBe(2020);
    expect(sorted[2].year).toBe(2024);
  });

  it('should not mutate original array', () => {
    const original = [...papers];
    sortPapers(papers, 'citations');
    expect(papers).toEqual(original);
  });
});

describe('SearchPage - getYearRange', () => {
  it('should return specific year range', () => {
    expect(getYearRange('2024')).toEqual({ from: 2024, to: 2024 });
    expect(getYearRange('2025')).toEqual({ from: 2025, to: 2025 });
  });

  it('should return 3-year range', () => {
    const range = getYearRange('3y');
    expect(range.from).toBe(CURRENT_YEAR - 2);
    expect(range.to).toBe(CURRENT_YEAR);
  });

  it('should return 5-year range', () => {
    const range = getYearRange('5y');
    expect(range.from).toBe(CURRENT_YEAR - 4);
    expect(range.to).toBe(CURRENT_YEAR);
  });

  it('should return empty for "all"', () => {
    expect(getYearRange('all')).toEqual({});
  });
});
