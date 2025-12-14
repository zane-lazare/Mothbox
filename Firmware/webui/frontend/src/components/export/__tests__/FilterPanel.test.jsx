import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FilterPanel from '../FilterPanel';

// Create QueryClient wrapper for tests
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

const renderWithQueryClient = (ui) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>
  );
};

describe('FilterPanel', () => {
  const defaultFilter = {
    date_start: null,
    date_end: null,
    deployment: null,
    tags: [],
    series_type: null,
    has_species: false,
  };

  it('renders all filter controls', () => {
    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/deployment/i)).toBeInTheDocument();
    expect(screen.getByText(/tags/i)).toBeInTheDocument(); // This is a heading, not a label
    expect(screen.getByText(/series type/i)).toBeInTheDocument(); // This is a heading, not a label
    expect(screen.getByLabelText(/only photos with species/i)).toBeInTheDocument();
  });

  it('validates date range (start <= end)', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    renderWithQueryClient(
      <FilterPanel
        filter={{ ...defaultFilter, date_start: '2024-01-15' }}
        onChange={onChange}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    const endDateInput = screen.getByLabelText(/end date/i);
    await user.type(endDateInput, '2024-01-01');

    // Should show validation error or prevent invalid date
    expect(screen.getByText(/end date must be after start date/i)).toBeInTheDocument();
  });

  it('updates filter on control changes', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={onChange}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    // Change start date
    const startDateInput = screen.getByLabelText(/start date/i);
    await user.type(startDateInput, '2024-01-01');
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ date_start: '2024-01-01' })
    );

    // Toggle has_species
    const speciesCheckbox = screen.getByLabelText(/only photos with species/i);
    await user.click(speciesCheckbox);
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ has_species: true })
    );
  });

  it('shows photo count', () => {
    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={150}
        isLoadingCount={false}
      />
    );

    expect(screen.getByText(/150 photos match/i)).toBeInTheDocument();
  });

  it('shows loading state for photo count', () => {
    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={null}
        isLoadingCount={true}
      />
    );

    expect(screen.getByText(/counting/i)).toBeInTheDocument();
  });

  it('respects disabled prop', () => {
    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={100}
        isLoadingCount={false}
        disabled
      />
    );

    expect(screen.getByLabelText(/start date/i)).toBeDisabled();
    expect(screen.getByLabelText(/end date/i)).toBeDisabled();
    expect(screen.getByLabelText(/deployment/i)).toBeDisabled();
    expect(screen.getByLabelText(/only photos with species/i)).toBeDisabled();
  });

  it('expands and collapses correctly', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    const toggleButton = screen.getByRole('button', { name: /photo filters/i });

    // Initially expanded
    expect(screen.getByLabelText(/start date/i)).toBeVisible();

    // Collapse
    await user.click(toggleButton);
    const startDateAfterCollapse = screen.queryByLabelText(/start date/i);
    expect(startDateAfterCollapse).toBeNull(); // Element is removed from DOM when collapsed

    // Expand
    await user.click(toggleButton);
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
  });

  it('shows series type radio options', () => {
    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    expect(screen.getByRole('radio', { name: /all/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /hdr only/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /focus bracket only/i })).toBeInTheDocument();
  });

  it('updates series type on radio change', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();

    renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={onChange}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    const hdrRadio = screen.getByRole('radio', { name: /hdr only/i });
    await user.click(hdrRadio);

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ series_type: 'hdr' })
    );
  });

  it('displays chevron icon that rotates on expand/collapse', async () => {
    const user = userEvent.setup();
    const { container } = renderWithQueryClient(
      <FilterPanel
        filter={defaultFilter}
        onChange={vi.fn()}
        photoCount={100}
        isLoadingCount={false}
      />
    );

    const toggleButton = screen.getByRole('button', { name: /photo filters/i });
    const chevron = container.querySelector('[data-testid="chevron-icon"]');

    expect(chevron).toBeInTheDocument();

    // Initially expanded - should have rotate-90 class
    expect(chevron).toHaveClass('rotate-90');

    // Collapse
    await user.click(toggleButton);
    expect(chevron).not.toHaveClass('rotate-90');

    // Expand
    await user.click(toggleButton);
    expect(chevron).toHaveClass('rotate-90');
  });
});
