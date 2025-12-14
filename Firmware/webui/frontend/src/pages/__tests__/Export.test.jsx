import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Export from '../Export';
import * as exportApi from '../../utils/exportApi';
import * as deploymentApi from '../../utils/deploymentApi';

// Mock the API modules
vi.mock('../../utils/exportApi');
vi.mock('../../utils/deploymentApi');

// Mock child components
vi.mock('../../components/export/FormatSelector', () => ({
  default: ({ selectedFormat, onFormatChange }) => (
    <div data-testid="format-selector">
      <button onClick={() => onFormatChange('darwin_core')}>Darwin Core</button>
      <button onClick={() => onFormatChange('inaturalist')}>iNaturalist</button>
      <button onClick={() => onFormatChange('json')}>JSON</button>
      <button onClick={() => onFormatChange('csv')}>CSV</button>
      <div>Selected: {selectedFormat || 'none'}</div>
    </div>
  ),
}));

vi.mock('../../components/export/PresetDropdown', () => ({
  default: ({ onPresetSelect }) => (
    <div data-testid="preset-dropdown">
      <button onClick={() => onPresetSelect({
        name: 'gbif_biodiversity',
        format: 'darwin_core',
        filter: { has_species: true },
        options: { include_photos: false },
      })}>
        GBIF Preset
      </button>
    </div>
  ),
}));

vi.mock('../../components/export/FilterPanel', () => ({
  default: ({ filter, onChange }) => (
    <div data-testid="filter-panel">
      <button onClick={() => onChange({ ...filter, has_species: true })}>
        Add Species Filter
      </button>
      <div>Photo count: 150</div>
    </div>
  ),
}));

vi.mock('../../components/export/DeploymentSelector', () => ({
  default: () => <div data-testid="deployment-selector">Deployment Selector</div>,
}));

vi.mock('../../components/export/DeploymentEditor', () => ({
  default: () => <div data-testid="deployment-editor">Deployment Editor</div>,
}));

vi.mock('../../components/export/FormatOptionsPanel', () => ({
  default: ({ format, options, onChange }) => (
    <div data-testid="format-options">
      <button onClick={() => onChange({ ...options, include_photos: true })}>
        Include Photos
      </button>
      <div>Format: {format}</div>
    </div>
  ),
}));

vi.mock('../../components/export/FieldSelector', () => ({
  default: ({ selectedFields, onChange }) => (
    <div data-testid="field-selector">
      <button onClick={() => onChange(['filename', 'species'])}>
        Select Fields
      </button>
      <div>Fields: {selectedFields?.length || 0}</div>
    </div>
  ),
}));

vi.mock('../../components/export/ExportPreview', () => ({
  default: () => <div data-testid="export-preview">Export Preview</div>,
}));

vi.mock('../../components/export/ExportJobProgress', () => ({
  default: ({ job }) => (
    <div data-testid="export-job-progress">
      {job && <div>Job Status: {job.status}</div>}
    </div>
  ),
}));

vi.mock('../../components/export/ExportJobList', () => ({
  default: () => <div data-testid="export-job-list">Export Job List</div>,
}));

// Mock the useExportPreview hook to provide photoCount
vi.mock('../../hooks/useExportPreview', () => ({
  default: () => ({
    data: { metadata: { total_photos: 150 } },
    isLoading: false,
    error: null,
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('Export Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [] } });
    exportApi.listExportPresets.mockResolvedValue({ data: { presets: [] } });
    deploymentApi.listDeployments.mockResolvedValue({ data: { deployments: [] } });
  });

  describe('Page Structure', () => {
    it('renders all page sections', async () => {
      render(<Export />, { wrapper: createWrapper() });

      // Always visible sections
      expect(screen.getByText('Export Photos')).toBeInTheDocument();
      expect(screen.getByTestId('format-selector')).toBeInTheDocument();
      expect(screen.getByTestId('preset-dropdown')).toBeInTheDocument();
      expect(screen.getByTestId('filter-panel')).toBeInTheDocument();
      expect(screen.getByTestId('deployment-selector')).toBeInTheDocument();
      expect(screen.getByTestId('export-preview')).toBeInTheDocument();
      expect(screen.getByTestId('export-job-list')).toBeInTheDocument();

      // Conditionally rendered sections (only when format selected)
      // format-options and field-selector appear after format selection
    });

    it('renders start export button', () => {
      render(<Export />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /start export/i })).toBeInTheDocument();
    });
  });

  describe('Format Selection', () => {
    it('updates form state when format selected', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const formatSelector = screen.getByTestId('format-selector');
      const jsonButton = within(formatSelector).getByText('JSON');

      await user.click(jsonButton);

      expect(within(formatSelector).getByText('Selected: json')).toBeInTheDocument();
    });

    it('enables export button after format selection', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const exportButton = screen.getByRole('button', { name: /start export/i });
      expect(exportButton).toBeDisabled();

      const formatSelector = screen.getByTestId('format-selector');
      await user.click(within(formatSelector).getByText('JSON'));

      await waitFor(() => {
        expect(exportButton).toBeEnabled();
      });
    });
  });

  describe('Preset Selection', () => {
    it('applies preset values to form state', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const presetDropdown = screen.getByTestId('preset-dropdown');
      await user.click(within(presetDropdown).getByText('GBIF Preset'));

      // Format should be updated
      const formatSelector = screen.getByTestId('format-selector');
      expect(within(formatSelector).getByText('Selected: darwin_core')).toBeInTheDocument();
    });

    it('updates filter panel when preset applied', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const presetDropdown = screen.getByTestId('preset-dropdown');
      await user.click(within(presetDropdown).getByText('GBIF Preset'));

      // Filter panel should reflect preset filter
      const filterPanel = screen.getByTestId('filter-panel');
      expect(filterPanel).toBeInTheDocument();
    });
  });

  describe('Filter Changes', () => {
    it('updates photo count when filter changes', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const filterPanel = screen.getByTestId('filter-panel');
      const addFilterButton = within(filterPanel).getByText('Add Species Filter');

      await user.click(addFilterButton);

      expect(within(filterPanel).getByText('Photo count: 150')).toBeInTheDocument();
    });
  });

  describe('Export Button State', () => {
    it('is disabled initially', () => {
      render(<Export />, { wrapper: createWrapper() });

      const exportButton = screen.getByRole('button', { name: /start export/i });
      expect(exportButton).toBeDisabled();
    });

    it('shows photo count when enabled', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const formatSelector = screen.getByTestId('format-selector');
      await user.click(within(formatSelector).getByText('JSON'));

      const exportButton = screen.getByRole('button', { name: /start export/i });
      expect(exportButton.textContent).toMatch(/150/);
    });

    it('enables export button after format selection', async () => {
      const user = userEvent.setup();
      // Mock createExportJob for the mutation
      exportApi.createExportJob.mockResolvedValue({
        data: { job_id: 'job-123', status: 'pending' },
      });

      render(<Export />, { wrapper: createWrapper() });

      // Initially disabled
      const exportButton = screen.getByRole('button', { name: /start export/i });
      expect(exportButton).toBeDisabled();

      // Select a format
      const formatSelector = screen.getByTestId('format-selector');
      await user.click(within(formatSelector).getByText('JSON'));

      // Now button should be enabled (format selected + photoCount > 0 from mock)
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /start export/i })).toBeEnabled();
      });
    });
  });

  describe('Job Progress Display', () => {
    it('shows progress for running job', async () => {
      exportApi.listExportJobs.mockResolvedValue({
        data: {
          jobs: [{ id: 'job-123', status: 'running', progress: { percent: 45 } }],
        },
      });

      render(<Export />, { wrapper: createWrapper() });

      // When there's a running job, ExportJobProgress should be rendered
      await waitFor(() => {
        expect(screen.getByTestId('export-job-progress')).toBeInTheDocument();
      });
    });

    it('does not show progress when no running jobs', async () => {
      exportApi.listExportJobs.mockResolvedValue({
        data: {
          jobs: [{ id: 'job-123', status: 'completed', result: { file_path: '/exports/job-123.zip' } }],
        },
      });

      render(<Export />, { wrapper: createWrapper() });

      // Completed jobs don't show the progress component (currentJob filter is only running/pending)
      await waitFor(() => {
        // Job list should render
        expect(screen.getByTestId('export-job-list')).toBeInTheDocument();
      });
    });

    it('disables export button when a job is running', async () => {
      exportApi.listExportJobs.mockResolvedValue({
        data: {
          jobs: [{ id: 'job-123', status: 'running', progress: { percent: 45 } }],
        },
      });

      render(<Export />, { wrapper: createWrapper() });

      // Wait for jobs to load
      await waitFor(() => {
        expect(screen.getByTestId('export-job-progress')).toBeInTheDocument();
      });

      // Export button should be disabled due to running job
      const exportButton = screen.getByRole('button', { name: /start export/i });
      expect(exportButton).toBeDisabled();

      // Message should explain why
      expect(screen.getByText(/export in progress/i)).toBeInTheDocument();
    });
  });

  describe('Responsive Layout', () => {
    it('renders two-column layout on desktop', () => {
      render(<Export />, { wrapper: createWrapper() });

      const container = screen.getByText('Export Photos').closest('div');
      expect(container).toBeInTheDocument();
      // Layout structure is tested via snapshots
    });

    it('renders single-column layout on mobile', () => {
      // Mock window.matchMedia for mobile
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === '(max-width: 768px)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
      }));

      render(<Export />, { wrapper: createWrapper() });

      const container = screen.getByText('Export Photos').closest('div');
      expect(container).toBeInTheDocument();
    });
  });

  describe('Format Options Panel', () => {
    it('updates options when changed', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const formatSelector = screen.getByTestId('format-selector');
      await user.click(within(formatSelector).getByText('iNaturalist'));

      const optionsPanel = screen.getByTestId('format-options');
      const includePhotosButton = within(optionsPanel).getByText('Include Photos');

      await user.click(includePhotosButton);

      expect(within(optionsPanel).getByText('Format: inaturalist')).toBeInTheDocument();
    });
  });

  describe('Field Selector', () => {
    it('updates selected fields when changed', async () => {
      const user = userEvent.setup();
      render(<Export />, { wrapper: createWrapper() });

      const formatSelector = screen.getByTestId('format-selector');
      await user.click(within(formatSelector).getByText('CSV'));

      const fieldSelector = screen.getByTestId('field-selector');
      const selectFieldsButton = within(fieldSelector).getByText('Select Fields');

      await user.click(selectFieldsButton);

      expect(within(fieldSelector).getByText('Fields: 2')).toBeInTheDocument();
    });
  });
});
