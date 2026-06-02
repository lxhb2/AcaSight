import { describe, it, expect, vi, beforeEach } from 'vitest';

global.fetch = vi.fn();

function mockFetchResponse(data: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(data),
  } as Response;
}

describe('api.ts request function', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should call fetch with correct base URL for GET requests', async () => {
    const mockData = { query: 'test', sources: [], results: {} };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockFetchResponse(mockData),
    );

    const { searchApi } = await import('@/services/api');
    await searchApi.search('test', ['semantic_scholar']);

    expect(fetch).toHaveBeenCalledTimes(1);
    const [url] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain('/api/search');
  });

  it('should call fetch with POST method for write endpoints', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockFetchResponse({ connected: true }),
    );

    const { aiConfigApi } = await import('@/services/api');
    await aiConfigApi.testProvider({ provider: 'openai' });

    expect(fetch).toHaveBeenCalledTimes(1);
    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options?.method).toBe('POST');
  });

  it('should throw on non-ok response', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockFetchResponse({ detail: 'Not Found' }, false, 404),
    );

    const { searchApi } = await import('@/services/api');
    await expect(
      searchApi.search('test'),
    ).rejects.toThrow('Not Found');
  });

  it('should throw with status text when error body is not JSON', async () => {
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 500,
      headers: new Headers(),
      json: () => Promise.reject(new Error('not json')),
    } as Response);

    const { searchApi } = await import('@/services/api');
    await expect(
      searchApi.search('test'),
    ).rejects.toThrow('HTTP 500');
  });
});

describe('api.ts exported types', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('should export AIConfig interface via aiConfigApi', async () => {
    const mockConfig = {
      default_provider: 'openai',
      default_model: 'gpt-4',
      providers: {},
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockFetchResponse(mockConfig),
    );

    const { aiConfigApi } = await import('@/services/api');
    const result = await aiConfigApi.getConfig();
    expect(result.default_provider).toBe('openai');
    expect(result.default_model).toBe('gpt-4');
  });

  it('should export OutlineNode/PaperOutline via writingApi.generateOutline', async () => {
    const mockOutline = {
      success: true,
      data: {
        title: 'Test Paper',
        outline: [
          { level: 1, title: 'Intro', sections: [] },
          { level: 1, title: 'Methods', sections: [{ level: 2, title: 'Data', sections: [] }] },
        ],
        keywords: ['test'],
        estimated_total_words: 5000,
      },
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      mockFetchResponse(mockOutline),
    );

    const { writingApi } = await import('@/services/api');
    const result = await writingApi.generateOutline({ topic: 'test' });
    expect(result.success).toBe(true);
    expect(result.data.title).toBe('Test Paper');
    expect(result.data.outline).toHaveLength(2);
    expect(result.data.outline[1].sections).toHaveLength(1);
  });
});
