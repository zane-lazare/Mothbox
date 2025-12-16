import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DeploymentSelector from '../DeploymentSelector';

// Mock useDeployments hook
vi.mock('../../../hooks/useDeployments', () => ({
  default: vi.fn()
}));

import useDeployments from '../../../hooks/useDeployments';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('DeploymentSelector', () => {
  const mockOnChange = vi.fn();
  const mockOnCreateNew = vi.fn();
  const mockOnEdit = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dropdown with deployment options', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' },
          { directory: '/photos/deployment2', name: 'Smoky Mountains Study' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });

  it('shows "Create new deployment" option', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const options = screen.getAllByRole('option');
      // Second option should be "Create new deployment"
      expect(options[1]).toHaveTextContent(/create new deployment/i);
    });
  });

  it('displays deployment names in dropdown', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' },
          { directory: '/photos/deployment2', name: 'Smoky Mountains Study' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByText('Oak Ridge Survey')).toBeInTheDocument();
      expect(screen.getByText('Smoky Mountains Study')).toBeInTheDocument();
    });
  });

  it('calls onChange when deployment selected', async () => {
    const user = userEvent.setup();
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    const select = screen.getByRole('combobox');
    await user.selectOptions(select, '/photos/deployment1');

    expect(mockOnChange).toHaveBeenCalledWith('/photos/deployment1');
  });

  it('calls onCreateNew when create option selected', async () => {
    const user = userEvent.setup();
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    const select = screen.getByRole('combobox');
    await user.selectOptions(select, '__create_new__');

    expect(mockOnCreateNew).toHaveBeenCalled();
    expect(mockOnChange).not.toHaveBeenCalled();
  });

  it('shows edit button when deployment selected', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value="/photos/deployment1"
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const editButton = screen.getByRole('button', { name: /edit/i });
      expect(editButton).toBeInTheDocument();
    });
  });

  it('hides edit button when no deployment selected', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    });
  });

  it('calls onEdit when edit button clicked', async () => {
    const user = userEvent.setup();
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value="/photos/deployment1"
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument();
    });

    const editButton = screen.getByRole('button', { name: /edit/i });
    await user.click(editButton);

    expect(mockOnEdit).toHaveBeenCalled();
  });

  it('respects disabled prop', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
        disabled
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    const select = screen.getByRole('combobox');
    expect(select).toBeDisabled();
  });

  it('shows loading state while fetching deployments', () => {
    useDeployments.mockReturnValue({
      data: null,
      isLoading: true,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('shows error state when fetch fails', async () => {
    useDeployments.mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed to load deployments')
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(screen.getByText(/failed to load deployments/i)).toBeInTheDocument();
    });
  });

  it('shows empty state when no deployments exist', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: []
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      // Should still show "Create new deployment" option
      expect(screen.getByText(/create new deployment/i)).toBeInTheDocument();
    });
  });

  it('displays selected deployment name', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' },
          { directory: '/photos/deployment2', name: 'Smoky Mountains Study' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value="/photos/deployment1"
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const select = screen.getByRole('combobox');
      expect(select).toHaveValue('/photos/deployment1');
    });
  });

  it('has correct accessibility attributes', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('aria-label', 'Select deployment');
    });
  });

  it('sorts deployments alphabetically by name', async () => {
    useDeployments.mockReturnValue({
      data: {
        deployments: [
          { directory: '/photos/deployment2', name: 'Zebra Study' },
          { directory: '/photos/deployment1', name: 'Alpha Survey' },
          { directory: '/photos/deployment3', name: 'Beta Research' }
        ]
      },
      isLoading: false,
      error: null
    });

    render(
      <DeploymentSelector
        value={null}
        onChange={mockOnChange}
        onCreateNew={mockOnCreateNew}
        onEdit={mockOnEdit}
      />,
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const options = screen.getAllByRole('option');
      // Skip first two options (Select... and Create new...)
      expect(options[2]).toHaveTextContent('Alpha Survey');
      expect(options[3]).toHaveTextContent('Beta Research');
      expect(options[4]).toHaveTextContent('Zebra Study');
    });
  });

  describe('allowNone functionality', () => {
    it('shows default label when allowNone is false', async () => {
      useDeployments.mockReturnValue({
        data: {
          deployments: [
            { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
          ]
        },
        isLoading: false,
        error: null
      });

      render(
        <DeploymentSelector
          value={null}
          onChange={mockOnChange}
          onCreateNew={mockOnCreateNew}
          onEdit={mockOnEdit}
          allowNone={false}
        />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options[0]).toHaveTextContent('Select a deployment...');
      });
    });

    it('shows custom none label when allowNone is true', async () => {
      useDeployments.mockReturnValue({
        data: {
          deployments: [
            { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
          ]
        },
        isLoading: false,
        error: null
      });

      render(
        <DeploymentSelector
          value={null}
          onChange={mockOnChange}
          onCreateNew={mockOnCreateNew}
          onEdit={mockOnEdit}
          allowNone={true}
          noneLabel="None - use photo EXIF data"
        />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options[0]).toHaveTextContent('None - use photo EXIF data');
      });
    });

    it('uses default noneLabel when not specified', async () => {
      useDeployments.mockReturnValue({
        data: {
          deployments: [
            { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
          ]
        },
        isLoading: false,
        error: null
      });

      render(
        <DeploymentSelector
          value={null}
          onChange={mockOnChange}
          onCreateNew={mockOnCreateNew}
          onEdit={mockOnEdit}
          allowNone={true}
        />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options[0]).toHaveTextContent('None - use photo data');
      });
    });

    it('calls onChange with null when empty value selected with allowNone', async () => {
      const user = userEvent.setup();
      useDeployments.mockReturnValue({
        data: {
          deployments: [
            { directory: '/photos/deployment1', name: 'Oak Ridge Survey' }
          ]
        },
        isLoading: false,
        error: null
      });

      render(
        <DeploymentSelector
          value="/photos/deployment1"
          onChange={mockOnChange}
          onCreateNew={mockOnCreateNew}
          onEdit={mockOnEdit}
          allowNone={true}
        />,
        { wrapper: createWrapper() }
      );

      await waitFor(() => {
        expect(screen.getByRole('combobox')).toBeInTheDocument();
      });

      const select = screen.getByRole('combobox');
      await user.selectOptions(select, '');

      expect(mockOnChange).toHaveBeenCalledWith(null);
    });
  });
});
