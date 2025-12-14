import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useSinglePhotoExport } from '../useSinglePhotoExport'
import * as useExportJobs from '../useExportJobs'
import * as exportApi from '../../utils/exportApi'

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
    loading: vi.fn(),
    dismiss: vi.fn(),
  },
}))

// Create wrapper for react-query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('useSinglePhotoExport', () => {
  let mockCreateExportJob
  let mockUseExportJob

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock the hooks with default implementations
    mockCreateExportJob = {
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      isError: false,
      error: null,
      data: null,
    }

    mockUseExportJob = {
      data: null,
      isLoading: false,
      isError: false,
      error: null,
    }

    vi.spyOn(useExportJobs, 'useCreateExportJob').mockReturnValue(mockCreateExportJob)
    vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('exportPhoto', () => {
    it('creates job with photo_paths filter containing single photo', async () => {
      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      expect(mockCreateExportJob.mutate).toHaveBeenCalledWith(
        {
          format: 'json',
          filter: {
            photo_paths: ['/photos/moth.jpg'],
          },
        },
        expect.any(Object)
      )
    })

    it('supports all export formats', async () => {
      const formats = ['json', 'csv', 'darwin_core', 'inaturalist']

      for (const format of formats) {
        const { result } = renderHook(() => useSinglePhotoExport(), {
          wrapper: createWrapper(),
        })

        act(() => {
          result.current.exportPhoto('/photos/moth.jpg', format)
        })

        expect(mockCreateExportJob.mutate).toHaveBeenCalledWith(
          {
            format,
            filter: {
              photo_paths: ['/photos/moth.jpg'],
            },
          },
          expect.any(Object)
        )

        vi.clearAllMocks()
      }
    })

    it('shows loading toast when job creation starts', async () => {
      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      expect(toast.loading).toHaveBeenCalledWith('Preparing export...')
    })

    it('handles job creation failure gracefully', async () => {
      const mockError = new Error('Failed to create job')

      mockCreateExportJob.mutate.mockImplementation((data, { onError }) => {
        if (onError) onError(mockError)
      })

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.error).toBe(mockError)
        expect(toast.error).toHaveBeenCalledWith('Failed to start export')
        expect(toast.dismiss).toHaveBeenCalled()
      })
    })
  })

  describe('isExporting state', () => {
    it('returns isExporting=false initially', () => {
      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      expect(result.current.isExporting).toBe(false)
    })

    it('returns isExporting=true while job is pending', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: { job_id: 'test-job-id', status: 'pending' },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })
    })

    it('returns isExporting=true while job is running', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'running',
          progress: { current: 50, total: 100, percent: 50, phase: 'exporting' }
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })
    })

    it('returns isExporting=false when job completes', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'completed',
          output_path: '/exports/moth.json'
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(false)
      })
    })
  })

  describe('polling behavior', () => {
    it('polls for job status while active', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      // useExportJob hook automatically polls when jobId is set
      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        // Verify useExportJob is called with the job ID (enabling polling)
        expect(useExportJobs.useExportJob).toHaveBeenCalledWith('test-job-id')
      })
    })

    it('does not poll when no job is active', () => {
      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      // Initially, no job ID, so polling is disabled
      expect(useExportJobs.useExportJob).toHaveBeenCalledWith(null)
      expect(result.current.isExporting).toBe(false)
    })
  })

  describe('progress tracking', () => {
    it('exposes progress during export', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'running',
          progress: {
            current: 75,
            total: 100,
            percent: 75,
            phase: 'finalizing'
          }
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.progress).toEqual({
          current: 75,
          total: 100,
          percent: 75,
          phase: 'finalizing'
        })
      })
    })

    it('returns null progress when no job is active', () => {
      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      expect(result.current.progress).toBeNull()
    })

    it('returns null progress when job has no progress data', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'pending',
          // No progress data
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.progress).toBeNull()
      })
    })
  })

  describe('automatic download on completion', () => {
    it('triggers download when job completes', async () => {
      // Mock document.createElement for anchor element
      const mockAnchor = {
        href: '',
        download: '',
        click: vi.fn(),
        style: {},
      }
      const originalCreateElement = document.createElement.bind(document)
      const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
        if (tag === 'a') {
          return mockAnchor
        }
        return originalCreateElement(tag)
      })
      const originalAppendChild = document.body.appendChild.bind(document.body)
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
        if (node === mockAnchor) {
          return node
        }
        return originalAppendChild(node)
      })
      const originalRemoveChild = document.body.removeChild.bind(document.body)
      const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation((node) => {
        if (node === mockAnchor) {
          return node
        }
        return originalRemoveChild(node)
      })

      vi.spyOn(exportApi, 'getExportJobDownloadUrl').mockReturnValue('/api/export/jobs/test-job-id/download')

      // Start with running job
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: { job_id: 'test-job-id', status: 'running' },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result, rerender } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      // Wait for job to be created
      await waitFor(() => {
        expect(useExportJobs.useExportJob).toHaveBeenCalledWith('test-job-id')
      })

      // Simulate job completion by updating the mock
      mockUseExportJob = {
        data: { job_id: 'test-job-id', status: 'completed', output_path: '/exports/moth.json' },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      rerender()

      await waitFor(() => {
        expect(mockAnchor.href).toBe('/api/export/jobs/test-job-id/download')
        expect(mockAnchor.click).toHaveBeenCalled()
        expect(toast.success).toHaveBeenCalledWith('Export downloaded successfully')
      })

      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
      removeChildSpy.mockRestore()
    })

    it('does not trigger download for pending jobs', async () => {
      const mockAnchor = {
        href: '',
        download: '',
        click: vi.fn(),
        style: {},
      }
      const originalCreateElement = document.createElement.bind(document)
      const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
        if (tag === 'a') {
          return mockAnchor
        }
        return originalCreateElement(tag)
      })

      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: { job_id: 'test-job-id', status: 'pending' },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })

      expect(mockAnchor.click).not.toHaveBeenCalled()
      createElementSpy.mockRestore()
    })

    it('does not trigger download for running jobs', async () => {
      const mockAnchor = {
        href: '',
        download: '',
        click: vi.fn(),
        style: {},
      }
      const originalCreateElement = document.createElement.bind(document)
      const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag) => {
        if (tag === 'a') {
          return mockAnchor
        }
        return originalCreateElement(tag)
      })

      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'running',
          progress: { current: 50, total: 100, percent: 50, phase: 'exporting' }
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })

      expect(mockAnchor.click).not.toHaveBeenCalled()
      createElementSpy.mockRestore()
    })
  })

  describe('error handling', () => {
    it('sets error state when export fails', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      // Start with running job
      mockUseExportJob = {
        data: { job_id: 'test-job-id', status: 'running' },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result, rerender } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })

      // Simulate job failure by updating the mock
      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'failed',
          error_message: 'Export processing failed'
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      rerender()

      await waitFor(() => {
        expect(result.current.error).toBe('Export processing failed')
        expect(toast.error).toHaveBeenCalledWith('Export failed: Export processing failed')
      })
    })

    it('handles generic error message for failed jobs without error_message', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      // Start with running job
      mockUseExportJob = {
        data: { job_id: 'test-job-id', status: 'running' },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      const { result, rerender } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })

      // Simulate job failure by updating the mock (no error_message)
      mockUseExportJob = {
        data: {
          job_id: 'test-job-id',
          status: 'failed',
          // No error_message
        },
        isLoading: false,
        isError: false,
        error: null,
      }
      vi.spyOn(useExportJobs, 'useExportJob').mockReturnValue(mockUseExportJob)

      rerender()

      await waitFor(() => {
        expect(result.current.error).toBe('Unknown error')
        expect(toast.error).toHaveBeenCalledWith('Export failed: Unknown error')
      })
    })
  })

  describe('reset', () => {
    it('clears error and progress state', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onError }) => {
        if (onError) onError(new Error('Test error'))
      })

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(result.current.error).not.toBeNull()
      })

      act(() => {
        result.current.reset()
      })

      expect(result.current.error).toBeNull()
      expect(result.current.progress).toBeNull()
      expect(result.current.isExporting).toBe(false)
    })

    it('resets jobId to stop polling', async () => {
      mockCreateExportJob.mutate.mockImplementation((data, { onSuccess }) => {
        if (onSuccess) {
          onSuccess({ data: { job_id: 'test-job-id' } })
        }
      })

      const { result } = renderHook(() => useSinglePhotoExport(), {
        wrapper: createWrapper(),
      })

      act(() => {
        result.current.exportPhoto('/photos/moth.jpg', 'json')
      })

      await waitFor(() => {
        expect(useExportJobs.useExportJob).toHaveBeenCalledWith('test-job-id')
      })

      act(() => {
        result.current.reset()
      })

      // After reset, polling should be disabled (jobId = null)
      await waitFor(() => {
        expect(useExportJobs.useExportJob).toHaveBeenCalledWith(null)
      })
    })
  })
})
