import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionHistoryPanel } from '@/components/Writing/VersionHistoryPanel';
import { versionHistoryApi } from '@/services/api';

vi.mock('@/services/api', () => ({
  versionHistoryApi: {
    list: vi.fn(),
    getVersion: vi.fn(),
    compare: vi.fn(),
    restore: vi.fn(),
    save: vi.fn(),
    getLatest: vi.fn(),
  },
}));

const mockVersions = [
  { version_id: 'v1', version_num: 1, timestamp: 1700000000, note: 'Initial', author: 'User', is_full: true, content_length: 100 },
  { version_id: 'v2', version_num: 2, timestamp: 1700001000, note: 'Updated', author: 'User', is_full: true, content_length: 200 },
];

describe('VersionHistoryPanel', () => {
  beforeEach(() => {
    vi.mocked(versionHistoryApi.list).mockResolvedValue({ success: true, data: mockVersions } as never);
    vi.mocked(versionHistoryApi.getVersion).mockResolvedValue({
      success: true,
      data: { version_id: 'v1', version_num: 1, timestamp: 1700000000, note: 'Initial', author: 'User', content: 'Hello world' },
    } as never);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render version list', async () => {
    render(<VersionHistoryPanel documentId="doc1" />);

    await waitFor(() => {
      expect(screen.getByText('v1')).toBeInTheDocument();
      expect(screen.getByText('v2')).toBeInTheDocument();
    });
  });

  it('should show loading state', () => {
    vi.mocked(versionHistoryApi.list).mockReturnValue(new Promise(() => {}) as never);
    render(<VersionHistoryPanel documentId="doc1" />);
    expect(screen.getByText(/加载/i)).toBeInTheDocument();
  });

  it('should show empty state when no versions', async () => {
    vi.mocked(versionHistoryApi.list).mockResolvedValue({ success: true, data: [] } as never);
    render(<VersionHistoryPanel documentId="doc1" />);

    await waitFor(() => {
      expect(screen.getByText(/暂无/i)).toBeInTheDocument();
    });
  });

  it('should expand version detail on click', async () => {
    const user = userEvent.setup();
    render(<VersionHistoryPanel documentId="doc1" />);

    await waitFor(() => {
      expect(screen.getByText('v1')).toBeInTheDocument();
    });

    await user.click(screen.getByText('v1'));

    await waitFor(() => {
      expect(screen.getByText('Hello world')).toBeInTheDocument();
    });
  });
});
