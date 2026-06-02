import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TemplateGallery } from '@/components/Writing/TemplateGallery';
import { writingTemplatesApi } from '@/services/api';

vi.mock('@/services/api', () => ({
  writingTemplatesApi: {
    list: vi.fn(),
    getCategories: vi.fn(),
    create: vi.fn(),
    delete: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
  },
}));

const mockTemplates = [
  {
    id: 't1', name: '本科毕业论文', description: '标准本科毕业论文模板', category: '论文',
    tags: ['本科'], sections: [{ title: '绪论', description: '研究背景', required: true }],
    style: {}, is_builtin: true,
  },
  {
    id: 't2', name: '期刊论文', description: 'SCI期刊论文模板', category: '论文',
    tags: ['SCI'], sections: [{ title: 'Abstract', description: '摘要', required: true }],
    style: {}, is_builtin: false,
  },
];

describe('TemplateGallery', () => {
  beforeEach(() => {
    vi.mocked(writingTemplatesApi.list).mockResolvedValue({ success: true, data: mockTemplates } as never);
    vi.mocked(writingTemplatesApi.getCategories).mockResolvedValue({ success: true, data: ['论文'] } as never);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render template list', async () => {
    render(<TemplateGallery />);

    await waitFor(() => {
      expect(screen.getByText('本科毕业论文')).toBeInTheDocument();
      expect(screen.getByText('期刊论文')).toBeInTheDocument();
    });
  });

  it('should show categories', async () => {
    render(<TemplateGallery />);

    await waitFor(() => {
      const categoryElements = screen.getAllByText(/论文/);
      expect(categoryElements.length).toBeGreaterThan(0);
    });
  });

  it('should filter by search query', async () => {
    const user = userEvent.setup();
    render(<TemplateGallery />);

    await waitFor(() => {
      expect(screen.getByText('本科毕业论文')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/搜索/i);
    await user.type(searchInput, 'SCI');

    expect(screen.queryByText('本科毕业论文')).not.toBeInTheDocument();
    expect(screen.getByText('期刊论文')).toBeInTheDocument();
  });

  it('should show create form on button click', async () => {
    const user = userEvent.setup();
    render(<TemplateGallery />);

    await waitFor(() => {
      expect(screen.getByText('本科毕业论文')).toBeInTheDocument();
    });

    await user.click(screen.getByText(/创建/i));
    expect(screen.getByPlaceholderText(/模板名称/i)).toBeInTheDocument();
  });

  it('should call onApply when apply button clicked', async () => {
    const onApply = vi.fn();
    const user = userEvent.setup();
    render(<TemplateGallery onApply={onApply} />);

    await waitFor(() => {
      expect(screen.getByText('本科毕业论文')).toBeInTheDocument();
    });

    await user.click(screen.getByText('本科毕业论文'));

    await waitFor(() => {
      expect(screen.getByText(/应用/i)).toBeInTheDocument();
    });

    await user.click(screen.getByText(/应用/i));
    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({ id: 't1' }));
  });
});
