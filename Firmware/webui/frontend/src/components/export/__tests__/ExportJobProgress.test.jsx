import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExportJobProgress from '../ExportJobProgress';

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

describe('ExportJobProgress', () => {
  describe('Pending State', () => {
    it('shows waiting message for pending job', () => {
      const job = {
        id: 'job-123',
        status: 'pending',
        progress: { current: 0, total: 100, percent: 0 },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByText(/waiting to start/i)).toBeInTheDocument();
    });

    it('does not show progress bar for pending job', () => {
      const job = {
        id: 'job-123',
        status: 'pending',
        progress: { current: 0, total: 100, percent: 0 },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  describe('Running State', () => {
    it('renders progress bar with correct percentage', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 45,
          total: 100,
          percent: 45,
          phase: 'exporting',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute('aria-valuenow', '45');
      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('shows phase name correctly', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 30,
          total: 100,
          percent: 30,
          phase: 'collecting',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByText(/collecting/i)).toBeInTheDocument();
    });

    it('shows photo count', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 45,
          total: 100,
          percent: 45,
          phase: 'exporting',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByText(/45.*100.*photo/i)).toBeInTheDocument();
    });

    it('renders cancel button', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 45,
          total: 100,
          percent: 45,
          phase: 'exporting',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('calls cancelJob when cancel button clicked', async () => {
      const user = userEvent.setup();
      const onCancel = vi.fn();

      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 45,
          total: 100,
          percent: 45,
          phase: 'exporting',
        },
      };

      render(<ExportJobProgress job={job} onCancel={onCancel} />, {
        wrapper: createWrapper(),
      });

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      await waitFor(() => {
        expect(onCancel).toHaveBeenCalledWith('job-123');
      });
    });

    it('handles all phase names', () => {
      const phases = ['initializing', 'collecting', 'exporting', 'finalizing'];

      phases.forEach((phase) => {
        const job = {
          id: 'job-123',
          status: 'running',
          progress: {
            current: 25,
            total: 100,
            percent: 25,
            phase,
          },
        };

        const { unmount } = render(<ExportJobProgress job={job} />, {
          wrapper: createWrapper(),
        });

        expect(screen.getByText(new RegExp(phase, 'i'))).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('Completed State', () => {
    it('shows success message', () => {
      const job = {
        id: 'job-123',
        status: 'completed',
        progress: {
          current: 100,
          total: 100,
          percent: 100,
          phase: 'completed',
        },
        result: {
          file_path: '/exports/job-123.zip',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByText(/export completed/i)).toBeInTheDocument();
    });

    it('shows download button', () => {
      const job = {
        id: 'job-123',
        status: 'completed',
        progress: {
          current: 100,
          total: 100,
          percent: 100,
          phase: 'completed',
        },
        result: {
          file_path: '/exports/job-123.zip',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /download/i })).toBeInTheDocument();
    });

    it('download button opens download URL', async () => {
      const user = userEvent.setup();
      window.open = vi.fn();

      const job = {
        id: 'job-123',
        status: 'completed',
        progress: {
          current: 100,
          total: 100,
          percent: 100,
          phase: 'completed',
        },
        result: {
          file_path: '/exports/job-123.zip',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      const downloadButton = screen.getByRole('button', { name: /download/i });
      await user.click(downloadButton);

      expect(window.open).toHaveBeenCalledWith(
        expect.stringContaining('/api/export/jobs/job-123/download'),
        '_blank'
      );
    });
  });

  describe('Failed State', () => {
    it('shows error message', () => {
      const job = {
        id: 'job-123',
        status: 'failed',
        error: 'Export failed due to disk space',
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByRole('heading', { name: /export failed/i })).toBeInTheDocument();
      expect(screen.getByText(/disk space/i)).toBeInTheDocument();
    });

    it('shows retry option', () => {
      const job = {
        id: 'job-123',
        status: 'failed',
        error: 'Export failed',
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    it('calls onRetry when retry button clicked', async () => {
      const user = userEvent.setup();
      const onRetry = vi.fn();

      const job = {
        id: 'job-123',
        status: 'failed',
        error: 'Export failed',
      };

      render(<ExportJobProgress job={job} onRetry={onRetry} />, {
        wrapper: createWrapper(),
      });

      const retryButton = screen.getByRole('button', { name: /retry/i });
      await user.click(retryButton);

      await waitFor(() => {
        expect(onRetry).toHaveBeenCalled();
      });
    });
  });

  describe('Cancelled State', () => {
    it('shows cancelled message', () => {
      const job = {
        id: 'job-123',
        status: 'cancelled',
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      expect(screen.getByRole('heading', { name: /export cancelled/i })).toBeInTheDocument();
    });
  });

  describe('No Job', () => {
    it('renders nothing when no job provided', () => {
      const { container } = render(<ExportJobProgress job={null} />, {
        wrapper: createWrapper(),
      });

      expect(container.firstChild).toBeNull();
    });
  });

  describe('Progress Bar Visual', () => {
    it('renders progress bar with correct width style', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 67,
          total: 100,
          percent: 67,
          phase: 'exporting',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      const progressBar = screen.getByRole('progressbar');
      const progressFill = progressBar.querySelector('[style*="width"]');

      expect(progressFill).toHaveStyle({ width: '67%' });
    });

    it('handles 0% progress', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 0,
          total: 100,
          percent: 0,
          phase: 'initializing',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '0');
    });

    it('handles 100% progress', () => {
      const job = {
        id: 'job-123',
        status: 'running',
        progress: {
          current: 100,
          total: 100,
          percent: 100,
          phase: 'finalizing',
        },
      };

      render(<ExportJobProgress job={job} />, { wrapper: createWrapper() });

      const progressBar = screen.getByRole('progressbar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '100');
    });
  });
});
