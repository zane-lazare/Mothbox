import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useExportJobs, useExportJob, useCreateExportJob, useCancelExportJob, useDeleteExportJob } from '../useExportJobs'
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

describe('useExportJobs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches export jobs list successfully', async () => {
    const mockJobs = {
      jobs: [
        { job_id: '1', status: 'completed', format: 'darwin_core' },
        { job_id: '2', status: 'running', format: 'json' },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    }

    vi.spyOn(exportApi, 'listExportJobs').mockResolvedValue({ data: mockJobs })

    const { result } = renderHook(() => useExportJobs(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockJobs)
    expect(exportApi.listExportJobs).toHaveBeenCalledWith({
      status: undefined,
      limit: 50,
      offset: 0,
    })
  })

  it('passes filter parameters to API', async () => {
    const mockJobs = { jobs: [], total: 0, limit: 10, offset: 0 }
    vi.spyOn(exportApi, 'listExportJobs').mockResolvedValue({ data: mockJobs })

    const { result } = renderHook(
      () => useExportJobs({ status: 'completed', limit: 10, offset: 20 }),
      { wrapper: createWrapper() }
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(exportApi.listExportJobs).toHaveBeenCalledWith({
      status: 'completed',
      limit: 10,
      offset: 20,
    })
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Network error')
    vi.spyOn(exportApi, 'listExportJobs').mockRejectedValue(mockError)

    const { result } = renderHook(() => useExportJobs(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useExportJob', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches single job successfully', async () => {
    const mockJob = {
      job_id: '1',
      status: 'completed',
      format: 'darwin_core',
      progress: { current: 100, total: 100, percent: 100 },
    }

    vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({ data: mockJob })

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data).toEqual(mockJob)
    expect(exportApi.getExportJob).toHaveBeenCalledWith('1')
  })

  it('polls when job is running', async () => {
    const runningJob = {
      job_id: '1',
      status: 'running',
      format: 'json',
      progress: { current: 50, total: 100, percent: 50 },
    }

    vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({ data: runningJob })

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // Should enable polling with 5s interval when status is running
    expect(result.current.data.status).toBe('running')
  })

  it('does not poll when job is completed', async () => {
    const completedJob = {
      job_id: '1',
      status: 'completed',
      format: 'json',
      progress: { current: 100, total: 100, percent: 100 },
    }

    vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({ data: completedJob })

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // Polling should be disabled for completed status
    expect(result.current.data.status).toBe('completed')
  })

  it('does not poll when job is failed', async () => {
    const failedJob = {
      job_id: '1',
      status: 'failed',
      format: 'json',
      error_message: 'Export failed',
    }

    vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({ data: failedJob })

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data.status).toBe('failed')
  })

  it('does not poll when job is cancelled', async () => {
    const cancelledJob = {
      job_id: '1',
      status: 'cancelled',
      format: 'json',
    }

    vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({ data: cancelledJob })

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data.status).toBe('cancelled')
  })

  it('does not poll when job is expired', async () => {
    const expiredJob = {
      job_id: '1',
      status: 'expired',
      format: 'json',
    }

    vi.spyOn(exportApi, 'getExportJob').mockResolvedValue({ data: expiredJob })

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(result.current.data.status).toBe('expired')
  })

  it('is disabled when jobId is null', () => {
    const { result } = renderHook(() => useExportJob(null), {
      wrapper: createWrapper(),
    })

    expect(result.current.data).toBeUndefined()
    expect(result.current.isLoading).toBe(false)
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Job not found')
    vi.spyOn(exportApi, 'getExportJob').mockRejectedValue(mockError)

    const { result } = renderHook(() => useExportJob('1'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useCreateExportJob', () => {
  let queryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates export job successfully', async () => {
    const mockJobData = {
      format: 'darwin_core',
      filter: { has_species: true },
    }

    const mockResponse = {
      job_id: '1',
      status: 'pending',
      format: 'darwin_core',
    }

    vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCreateExportJob(), { wrapper })

    result.current.mutate(mockJobData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(exportApi.createExportJob).toHaveBeenCalled()
    expect(exportApi.createExportJob.mock.calls[0][0]).toEqual(mockJobData)
    expect(result.current.data.data).toEqual(mockResponse)
  })

  it('invalidates job list cache on success', async () => {
    const mockJobData = { format: 'json' }
    const mockResponse = { job_id: '1', status: 'pending', format: 'json' }

    vi.spyOn(exportApi, 'createExportJob').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCreateExportJob(), { wrapper })

    result.current.mutate(mockJobData)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-jobs'],
    })
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Invalid format')
    vi.spyOn(exportApi, 'createExportJob').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCreateExportJob(), { wrapper })

    result.current.mutate({ format: 'invalid' })

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useCancelExportJob', () => {
  let queryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('cancels export job successfully', async () => {
    const mockResponse = { success: true, message: 'Job cancelled' }

    vi.spyOn(exportApi, 'cancelExportJob').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCancelExportJob(), { wrapper })

    result.current.mutate('1')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(exportApi.cancelExportJob).toHaveBeenCalledWith('1')
    expect(result.current.data.data).toEqual(mockResponse)
  })

  it('invalidates job and job list cache on success', async () => {
    const mockResponse = { success: true, message: 'Job cancelled' }

    vi.spyOn(exportApi, 'cancelExportJob').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useCancelExportJob(), { wrapper })

    result.current.mutate('1')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-jobs', '1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-jobs'],
    })
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Cannot cancel completed job')
    vi.spyOn(exportApi, 'cancelExportJob').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useCancelExportJob(), { wrapper })

    result.current.mutate('1')

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})

describe('useDeleteExportJob', () => {
  let queryClient

  beforeEach(() => {
    vi.clearAllMocks()
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deletes export job successfully', async () => {
    const mockResponse = { success: true, message: 'Job deleted' }

    vi.spyOn(exportApi, 'deleteExportJob').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDeleteExportJob(), { wrapper })

    result.current.mutate('1')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(exportApi.deleteExportJob).toHaveBeenCalledWith('1')
    expect(result.current.data.data).toEqual(mockResponse)
  })

  it('invalidates job and job list cache on success', async () => {
    const mockResponse = { success: true, message: 'Job deleted' }

    vi.spyOn(exportApi, 'deleteExportJob').mockResolvedValue({ data: mockResponse })

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useDeleteExportJob(), { wrapper })

    result.current.mutate('1')

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-jobs', '1'],
    })
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['export-jobs'],
    })
  })

  it('handles API errors gracefully', async () => {
    const mockError = new Error('Cannot delete running job')
    vi.spyOn(exportApi, 'deleteExportJob').mockRejectedValue(mockError)

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )

    const { result } = renderHook(() => useDeleteExportJob(), { wrapper })

    result.current.mutate('1')

    await waitFor(() => expect(result.current.isError).toBe(true))

    expect(result.current.error).toBe(mockError)
  })
})
