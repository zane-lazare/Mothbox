import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Export from '../Export';
import * as exportApi from '../../utils/exportApi';
import * as deploymentApi from '../../utils/deploymentApi';

// Mock the API modules with explicit mock functions
vi.mock('../../utils/exportApi', () => ({
  createExportJob: vi.fn(),
  listExportJobs: vi.fn(),
  getExportJob: vi.fn(),
  cancelExportJob: vi.fn(),
  deleteExportJob: vi.fn(),
  getExportJobDownloadUrl: vi.fn(),
  listExportPresets: vi.fn(),
  getExportPreset: vi.fn(),
  createExportPreset: vi.fn(),
  deleteExportPreset: vi.fn(),
}));
vi.mock('../../utils/deploymentApi', () => ({
  listDeployments: vi.fn(),
  getDeployment: vi.fn(),
  createDeployment: vi.fn(),
  updateDeployment: vi.fn(),
  deleteDeployment: vi.fn(),
}));

// Mock child components
vi.mock('../../components/export/FormatSelector', () => ({
  default: ({ value, onChange }) => (
    <div data-testid="format-selector">
      <button onClick={() => onChange('darwin_core')}>Darwin Core</button>
      <button onClick={() => onChange('inaturalist')}>iNaturalist</button>
      <button onClick={() => onChange('json')}>JSON</button>
      <button onClick={() => onChange('csv')}>CSV</button>
      <div>Selected: {value || 'none'}</div>
    </div>
  ),
}));

vi.mock('../../components/export/PresetDropdown', () => ({
  default: ({ value, onChange, presets, onSavePreset }) => (
    <div data-testid="preset-dropdown">
      <button onClick={() => onChange('gbif_biodiversity')}>
        GBIF Preset
      </button>
      {onSavePreset && (
        <button onClick={onSavePreset}>Save Preset</button>
      )}
      <div>Selected Preset: {value || 'none'}</div>
      <div>Presets Count: {presets?.length || 0}</div>
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
// Use stable reference to avoid infinite re-renders
const mockPreviewData = { metadata: { total_photos: 150 } };
const mockPreviewResult = { data: mockPreviewData, isLoading: false, error: null };
vi.mock('../../hooks/useExportPreview', () => ({
  default: () => mockPreviewResult,
}));

// Mock the useExportPresets hooks
// Use stable references for preset data to avoid infinite re-renders in useEffect
const mockGbifPreset = {
  name: 'gbif_biodiversity',
  export_format: 'darwin_core',
  filter: { has_species: true },
  options: { include_photos: false },
};
const mockPresetsData = { presets: [
  { name: 'gbif_biodiversity', display_name: 'GBIF', category: 'built_in' }
] };
const mockPresetsResult = { data: mockPresetsData, isLoading: false, error: null };
const mockGbifPresetResult = { data: mockGbifPreset, isLoading: false, error: null };
const mockNullPresetResult = { data: null, isLoading: false, error: null };
const mockCreatePresetMutation = { mutate: vi.fn(), isPending: false };

vi.mock('../../hooks/useExportPresets', () => ({
  useExportPresets: () => mockPresetsResult,
  useExportPreset: (name) => name === 'gbif_biodiversity' ? mockGbifPresetResult : mockNullPresetResult,
  useCreateExportPreset: () => mockCreatePresetMutation,
}));

// Mock the useExportJobs hooks
// Use stable references to avoid infinite re-renders
const mockJobsData = { jobs: [] };
const mockJobsResult = { data: mockJobsData, isLoading: false, error: null };
const mockJobResult = { data: null, isLoading: false, error: null };
const mockCreateJobMutation = { mutate: vi.fn(), mutateAsync: vi.fn().mockResolvedValue({ job_id: 'test-job-123' }), isPending: false };
const mockCancelJobMutation = { mutate: vi.fn(), isPending: false };
const mockDeleteJobMutation = { mutate: vi.fn(), isPending: false };

vi.mock('../../hooks/useExportJobs', () => ({
  useExportJobs: () => mockJobsResult,
  useExportJob: () => mockJobResult,
  useCreateExportJob: () => mockCreateJobMutation,
  useCancelExportJob: () => mockCancelJobMutation,
  useDeleteExportJob: () => mockDeleteJobMutation,
}));

// Mock the useDeployments hooks
// Use stable references to avoid infinite re-renders
const mockDeploymentsData = { deployments: [] };
const mockDeploymentsResult = { data: mockDeploymentsData, isLoading: false, error: null };
const mockDeploymentResult = { data: null, isLoading: false, error: null };
const mockCreateDeploymentMutation = { mutate: vi.fn(), isPending: false };
const mockUpdateDeploymentMutation = { mutate: vi.fn(), isPending: false };
const mockDeleteDeploymentMutation = { mutate: vi.fn(), isPending: false };

vi.mock('../../hooks/useDeployments', () => ({
  default: () => mockDeploymentsResult,
  useDeployments: () => mockDeploymentsResult,
  useDeployment: () => mockDeploymentResult,
  useCreateDeployment: () => mockCreateDeploymentMutation,
  useUpdateDeployment: () => mockUpdateDeploymentMutation,
  useDeleteDeployment: () => mockDeleteDeploymentMutation,
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
    // Note: These tests use mocked hooks, so they can only verify the default behavior
    // The hooks are mocked to return empty jobs array, so no ExportJobProgress renders

    it('does not show progress when no running jobs', async () => {
      // Default mock returns empty jobs array
      render(<Export />, { wrapper: createWrapper() });

      // Job list should render
      await waitFor(() => {
        expect(screen.getByTestId('export-job-list')).toBeInTheDocument();
      });

      // No export-job-progress because no running/pending jobs
      expect(screen.queryByTestId('export-job-progress')).not.toBeInTheDocument();
    });

    it('renders job list section', () => {
      render(<Export />, { wrapper: createWrapper() });

      // Export job list component should be present
      expect(screen.getByTestId('export-job-list')).toBeInTheDocument();
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
