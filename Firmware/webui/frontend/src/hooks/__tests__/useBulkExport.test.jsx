import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import useBulkExport from '../useBulkExport'
import * as exportApi from '../../utils/exportApi'

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

describe('useBulkExport', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initial State', () => {
    it('returns initial state correctly', () => {
      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      expect(result.current.isExporting).toBe(false)
      expect(result.current.progress).toBeNull()
      expect(result.current.error).toBeNull()
      expect(result.current.jobId).toBeNull()
      expect(result.current.downloadUrl).toBeNull()
      expect(typeof result.current.exportPhotos).toBe('function')
      expect(typeof result.current.cancel).toBe('function')
      expect(typeof result.current.reset).toBe('function')
    })
  })

  describe('exportPhotos', () => {
    it('creates export job with photo_paths filter', async () => {
      const mockJobResponse = {
        data: {
          job_id: 'test-job-123',
          status: 'pending',
          format: 'darwin_core',
        },
      }

      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue(mockJobResponse)
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'test-job-123',
          status: 'pending',
          progress: { current: 0, total: 5, percent: 0, phase: 'initializing' },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['photo1.jpg', 'photo2.jpg', 'photo3.jpg'], 'darwin_core')
      })

      // Check first argument (data) matches expected structure
      const callArgs = exportApi.createExportJob.mock.calls[0]
      expect(callArgs[0]).toEqual({
        format: 'darwin_core',
        filter: {
          photo_paths: ['photo1.jpg', 'photo2.jpg', 'photo3.jpg'],
        },
      })
    })

    it('sets jobId after successful creation', async () => {
      const mockJobResponse = {
        data: {
          job_id: 'test-job-123',
          status: 'pending',
          format: 'json',
        },
      }

      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue(mockJobResponse)
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'test-job-123',
          status: 'pending',
          progress: { current: 0, total: 2, percent: 0 },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['photo1.jpg', 'photo2.jpg'], 'json')
      })

      expect(result.current.jobId).toBe('test-job-123')
    })

    it('sets isExporting to true after job creation', async () => {
      const mockJobResponse = {
        data: {
          job_id: 'test-job-123',
          status: 'pending',
        },
      }

      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue(mockJobResponse)
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'test-job-123',
          status: 'running',
          progress: { current: 0, total: 5, percent: 0 },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['photo1.jpg'], 'csv')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })
    })

    it('handles creation errors', async () => {
      const mockError = new Error('Rate limit exceeded')
      vi.spyOn(exportApi, 'createExportJob').mockRejectedValue(mockError)

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        try {
          await result.current.exportPhotos(['photo1.jpg'], 'json')
        } catch {
          // Expected to throw
        }
      })

      expect(result.current.error).toBeTruthy()
      expect(result.current.isExporting).toBe(false)
    })
  })

  describe('Progress tracking', () => {
    it('returns isExporting true when job is pending', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-1', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-1',
          status: 'pending',
          progress: { current: 0, total: 10, percent: 0, phase: 'initializing' },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })
    })

    it('returns isExporting true when job is running', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-1', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-1',
          status: 'running',
          progress: { current: 5, total: 10, percent: 50, phase: 'exporting' },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'csv')
      })

      await waitFor(() => {
        expect(result.current.isExporting).toBe(true)
      })
    })

    it('returns progress from job data', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-1', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-1',
          status: 'running',
          progress: { current: 7, total: 10, percent: 70, phase: 'exporting' },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await waitFor(() => {
        expect(result.current.progress).toEqual({
          current: 7,
          total: 10,
          percent: 70,
          phase: 'exporting',
        })
      })
    })

    it('returns error when job fails', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-1', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-1',
          status: 'failed',
          error: 'Export failed: invalid photos',
          progress: { current: 3, total: 10, percent: 30 },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await waitFor(() => {
        expect(result.current.error).toBe('Export failed: invalid photos')
        expect(result.current.isExporting).toBe(false)
      })
    })
  })

  describe('Completion', () => {
    it('returns downloadUrl when job completes', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-123', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-123',
          status: 'completed',
          progress: { current: 10, total: 10, percent: 100, phase: 'completed' },
        },
      })
      vi.spyOn(exportApi, 'getExportJobDownloadUrl').mockReturnValue('/api/export/jobs/job-123/download')

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await waitFor(() => {
        expect(result.current.downloadUrl).toBe('/api/export/jobs/job-123/download')
        expect(result.current.isExporting).toBe(false)
      })
    })

    it('calls onComplete callback when job completes', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-123', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-123',
          status: 'completed',
          progress: { current: 10, total: 10, percent: 100 },
        },
      })
      vi.spyOn(exportApi, 'getExportJobDownloadUrl').mockReturnValue('/api/export/jobs/job-123/download')

      const onComplete = vi.fn()
      const { result } = renderHook(() => useBulkExport({ onComplete }), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await waitFor(() => {
        expect(onComplete).toHaveBeenCalledTimes(1)
      })
    })
  })

  describe('Cancellation', () => {
    it('cancel function cancels running job', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-123', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-123',
          status: 'running',
          progress: { current: 5, total: 10, percent: 50 },
        },
      })
      vi.spyOn(exportApi, 'cancelExportJob').mockResolvedValue({
        data: { success: true },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await act(async () => {
        await result.current.cancel()
      })

      expect(exportApi.cancelExportJob).toHaveBeenCalledWith('job-123')
    })

    it('cancel does nothing when no job is active', async () => {
      vi.spyOn(exportApi, 'cancelExportJob').mockResolvedValue({
        data: { success: true },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.cancel()
      })

      expect(exportApi.cancelExportJob).not.toHaveBeenCalled()
    })
  })

  describe('Reset', () => {
    it('reset clears all state', async () => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-123', status: 'pending' },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-123',
          status: 'completed',
          progress: { current: 10, total: 10, percent: 100 },
        },
      })
      vi.spyOn(exportApi, 'getExportJobDownloadUrl').mockReturnValue('/api/export/jobs/job-123/download')

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['p1.jpg'], 'json')
      })

      await waitFor(() => {
        expect(result.current.jobId).toBe('job-123')
      })

      act(() => {
        result.current.reset()
      })

      expect(result.current.jobId).toBeNull()
      expect(result.current.isExporting).toBe(false)
      expect(result.current.progress).toBeNull()
      expect(result.current.error).toBeNull()
      expect(result.current.downloadUrl).toBeNull()
    })
  })

  describe('Format support', () => {
    it.each([
      ['darwin_core'],
      ['inaturalist'],
      ['json'],
      ['csv'],
    ])('supports %s format', async (format) => {
      vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({
        data: { job_id: 'job-1', status: 'pending', format },
      })
      vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({
        data: {
          job_id: 'job-1',
          status: 'pending',
          format,
          progress: { current: 0, total: 1, percent: 0 },
        },
      })

      const { result } = renderHook(() => useBulkExport(), {
        wrapper: createWrapper(),
      })

      await act(async () => {
        await result.current.exportPhotos(['photo.jpg'], format)
      })

      // Check first argument (data) matches expected structure
      const callArgs = exportApi.createExportJob.mock.calls[0]
      expect(callArgs[0]).toEqual({
        format,
        filter: { photo_paths: ['photo.jpg'] },
      })
    })
  })
})
