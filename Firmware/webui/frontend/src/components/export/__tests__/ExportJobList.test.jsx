import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExportJobList from '../ExportJobList';
import * as exportApi from '../../../utils/exportApi';

vi.mock('../../../utils/exportApi');

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

describe('ExportJobList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock - empty job list
    exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [] } });
  });

  describe('Job List Rendering', () => {
    it('renders job list table', async () => {
      exportApi.listExportJobs.mockResolvedValue({
        data: {
          jobs: [
            {
              id: 'job-1',
              format: 'json',
              status: 'completed',
              progress: { total: 100 },
              created_at: '2024-01-15T10:30:00Z',
            },
          ],
        },
      });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument();
      });
    });

    it('renders table headers when jobs exist', async () => {
      exportApi.listExportJobs.mockResolvedValue({
        data: {
          jobs: [
            {
              id: 'job-1',
              format: 'json',
              status: 'completed',
              progress: { total: 100 },
              created_at: '2024-01-15T10:30:00Z',
            },
          ],
        },
      });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Format')).toBeInTheDocument();
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText(/photo/i)).toBeInTheDocument();
        expect(screen.getByText('Created')).toBeInTheDocument();
        expect(screen.getByText('Actions')).toBeInTheDocument();
      });
    });

    it('renders multiple jobs', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
        {
          id: 'job-2',
          format: 'csv',
          status: 'running',
          progress: { total: 200 },
          created_at: '2024-01-15T11:00:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        expect(rows.length).toBe(3); // header + 2 data rows
      });
    });
  });

  describe('Status Badges', () => {
    it('shows correct status badge for completed job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const badge = screen.getByText(/completed/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass('bg-green-100'); // Success color
      });
    });

    it('shows correct status badge for running job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'running',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const badge = screen.getByText(/running/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass('bg-blue-100'); // Info color
      });
    });

    it('shows correct status badge for failed job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'failed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
          error: 'Export failed',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const badge = screen.getByText(/failed/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass('bg-red-100'); // Error color
      });
    });

    it('shows correct status badge for pending job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'pending',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const badge = screen.getByText(/pending/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass('bg-gray-100'); // Neutral color
      });
    });

    it('shows correct status badge for cancelled job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'cancelled',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const badge = screen.getByText(/cancelled/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass('bg-yellow-100'); // Warning color
      });
    });

    it('shows correct status badge for expired job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'expired',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const badge = screen.getByText(/expired/i);
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveClass('bg-gray-100'); // Neutral color
      });
    });
  });

  describe('Download Button', () => {
    it('shows download button for completed job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
          result: { file_path: '/exports/job-1.zip' },
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
      });
    });

    it('download button opens download URL', async () => {
      const user = userEvent.setup();
      window.open = vi.fn();

      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
          result: { file_path: '/exports/job-1.zip' },
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
      });

      const downloadButton = screen.getByRole('button', { name: /download/i });
      await user.click(downloadButton);

      expect(window.open).toHaveBeenCalledWith(
        expect.stringContaining('/api/export/jobs/job-1/download'),
        '_blank'
      );
    });

    it('does not show download button for non-completed jobs', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'running',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: /download/i })).not.toBeInTheDocument();
      });
    });
  });

  describe('Delete Button', () => {
    it('shows delete button for all jobs', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
      });
    });

    it('shows confirmation dialog before delete', async () => {
      const user = userEvent.setup();

      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
      });

      const deleteButton = screen.getByRole('button', { name: /delete/i });
      await user.click(deleteButton);

      // ConfirmDialog should appear
      await waitFor(() => {
        expect(screen.getByText('Delete Export Job?')).toBeInTheDocument();
      });
    });

    it('calls deleteExportJob when confirmed', async () => {
      const user = userEvent.setup();
      const mockDeleteJob = vi.fn().mockResolvedValue({});
      exportApi.deleteExportJob.mockImplementation(mockDeleteJob);

      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
      });

      const deleteButton = screen.getByRole('button', { name: /delete/i });
      await user.click(deleteButton);

      // Wait for dialog to appear
      await waitFor(() => {
        expect(screen.getByText('Delete Export Job?')).toBeInTheDocument();
      });

      // Click the confirm button in the dialog (the one with red background)
      const dialog = screen.getByRole('alertdialog');
      const confirmButton = within(dialog).getByRole('button', { name: /delete/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockDeleteJob).toHaveBeenCalledWith('job-1');
      });
    });

    it('does not call deleteExportJob when cancelled', async () => {
      const user = userEvent.setup();
      const mockDeleteJob = vi.fn();
      exportApi.deleteExportJob.mockImplementation(mockDeleteJob);

      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
      });

      const deleteButton = screen.getByRole('button', { name: /delete/i });
      await user.click(deleteButton);

      // Wait for dialog to appear
      await waitFor(() => {
        expect(screen.getByText('Delete Export Job?')).toBeInTheDocument();
      });

      // Click cancel button in the dialog
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Dialog should close and delete should not be called
      await waitFor(() => {
        expect(screen.queryByText('Delete Export Job?')).not.toBeInTheDocument();
      });
      expect(mockDeleteJob).not.toHaveBeenCalled();
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no jobs', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/no export jobs yet/i)).toBeInTheDocument();
      });
    });

    it('does not show table when no jobs', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.queryByRole('table')).not.toBeInTheDocument();
      });
    });
  });

  describe('Format Icons', () => {
    it('shows format name for each job', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'darwin_core',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
        {
          id: 'job-2',
          format: 'inaturalist',
          status: 'completed',
          progress: { total: 100 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/darwin core/i)).toBeInTheDocument();
        expect(screen.getByText(/inaturalist/i)).toBeInTheDocument();
      });
    });
  });

  describe('Photo Count', () => {
    it('displays photo count from progress.total', async () => {
      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 150 },
          created_at: '2024-01-15T10:30:00Z',
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('150')).toBeInTheDocument();
      });
    });
  });

  describe('Relative Time', () => {
    it('displays relative time for created_at', async () => {
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

      exportApi.listExportJobs.mockResolvedValue({ data: { jobs: [
        {
          id: 'job-1',
          format: 'json',
          status: 'completed',
          progress: { total: 100 },
          created_at: fiveMinutesAgo,
        },
      ] } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/5 minutes? ago/i)).toBeInTheDocument();
      });
    });
  });

  describe('Pagination', () => {
    it('limits jobs to 10 per page', async () => {
      const jobs = Array.from({ length: 15 }, (_, i) => ({
        id: `job-${i}`,
        format: 'json',
        status: 'completed',
        progress: { total: 100 },
        created_at: '2024-01-15T10:30:00Z',
      }));

      exportApi.listExportJobs.mockResolvedValue({ data: { jobs } });

      render(<ExportJobList />, { wrapper: createWrapper() });

      await waitFor(() => {
        const rows = screen.getAllByRole('row');
        expect(rows.length).toBeLessThanOrEqual(11); // header + 10 data rows
      });
    });
  });
});
