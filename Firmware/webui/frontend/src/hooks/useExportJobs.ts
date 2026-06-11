/**
 * React Query hooks for Export Jobs (Issue #125)
 *
 * Provides hooks for managing export job queue with auto-polling:
 * - useExportJobs: List jobs with filtering and pagination
 * - useExportJob: Single job with auto-polling when running
 * - useCreateExportJob: Create new export job
 * - useCancelExportJob: Cancel running job
 * - useDeleteExportJob: Delete job and output files
 *
 * Auto-polling behavior:
 * - useExportJob polls at 5s interval when job status is "running" or "pending"
 * - Polling stops when job reaches terminal state (completed, failed, cancelled, expired)
 * - This provides real-time progress updates in the UI without manual refresh
 */

import { useQuery, useMutation, useQueryClient, UseQueryResult, UseMutationResult } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listExportJobs,
  getExportJob,
  createExportJob,
  cancelExportJob,
  deleteExportJob,
} from '../utils/exportApi'
import type { ExportJob } from '../types'

type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'expired'

interface ExportJobsOptions {
  status?: JobStatus
  limit?: number
  offset?: number
}

interface ExportJobsData {
  jobs: ExportJob[]
  total: number
  limit: number
  offset: number
}

interface ExportJobProgress {
  current: number
  total: number
  percent: number
  phase: string
}

interface ExportJobDetail extends ExportJob {
  progress: ExportJobProgress
}

interface CreateExportJobParams {
  format: 'darwin_core' | 'inaturalist' | 'json' | 'csv'
  filter?: Record<string, unknown>
  options?: Record<string, unknown>
}

/**
 * List all export jobs with optional filtering and pagination
 *
 * @param options - Query options
 * @param options.status - Filter by status (pending, running, completed, failed, cancelled, expired)
 * @param options.limit - Max results (max: 100)
 * @param options.offset - Pagination offset
 * @returns React Query result
 *
 * @example
 * const { data, isLoading } = useExportJobs({ status: 'completed', limit: 10 })
 * if (data) {
 *   console.log(`${data.total} completed jobs`)
 *   data.jobs.forEach(job => console.log(job.job_id))
 * }
 */
export function useExportJobs(options: ExportJobsOptions = {}): UseQueryResult<ExportJobsData, Error> {
  const { status, limit = 50, offset = 0 } = options

  return useQuery({
    queryKey: [...QUERY_KEYS.EXPORT_JOBS, { status, limit, offset }],
    queryFn: async () => {
      const response = await listExportJobs({ status, limit, offset })
      return response.data
    },
    staleTime: 10 * 1000, // 10 seconds - relatively fresh for job list
  })
}

/**
 * Get single export job with auto-polling for running jobs
 *
 * Automatically polls at 5s interval when job is in active state (pending or running).
 * Polling stops when job reaches terminal state (completed, failed, cancelled, expired).
 *
 * @param jobId - Job ID (null to disable query)
 * @returns React Query result
 *
 * @example
 * const { data, isLoading } = useExportJob('550e8400-e29b-41d4-a716-446655440000')
 * if (data?.status === 'running') {
 *   console.log(`Progress: ${data.progress.percent}%`)
 *   console.log(`Phase: ${data.progress.phase}`)
 * }
 */
export function useExportJob(jobId: string | null): UseQueryResult<ExportJobDetail, Error> {
  return useQuery({
    queryKey: QUERY_KEYS.EXPORT_JOB(jobId!),
    queryFn: async () => {
      const response = await getExportJob(jobId!)
      return response.data
    },
    enabled: !!jobId, // Disable query if jobId is null/undefined
    staleTime: 0, // Always refetch to get latest progress
    // Auto-polling: Poll every 5 seconds when job is in active state
    refetchInterval: (query) => {
      const status = query.state.data?.status
      // Poll when job is pending or running
      if (status === 'pending' || status === 'running') {
        return 5000 // 5 seconds
      }
      // Stop polling for terminal states
      return false
    },
    // Stop polling when tab is not visible to prevent resource waste
    refetchIntervalInBackground: false,
  })
}

/**
 * Create new export job mutation
 *
 * Invalidates job list cache on success to show new job.
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useCreateExportJob()
 *
 * const handleCreate = () => {
 *   mutate({
 *     format: 'darwin_core',
 *     filter: { has_species: true }
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Job created:', response.data.job_id)
 *     },
 *     onError: (error) => {
 *       console.error('Failed:', error.message)
 *     }
 *   })
 * }
 */
export function useCreateExportJob(): UseMutationResult<unknown, Error, CreateExportJobParams> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: createExportJob,
    onSuccess: () => {
      // Invalidate job list to show new job
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOBS })
    },
  })
}

/**
 * Cancel export job mutation
 *
 * Invalidates job cache and job list on success.
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useCancelExportJob()
 *
 * const handleCancel = (jobId) => {
 *   mutate(jobId, {
 *     onSuccess: () => {
 *       console.log('Job cancelled')
 *     }
 *   })
 * }
 */
export function useCancelExportJob(): UseMutationResult<unknown, Error, string> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => cancelExportJob(jobId),
    onSuccess: (response, jobId) => {
      // Invalidate specific job to update status immediately
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOB(jobId) })
      // Invalidate job list to update counts
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOBS })
    },
  })
}

/**
 * Delete export job mutation
 *
 * Invalidates job cache and job list on success.
 * Cannot delete running jobs - must cancel first.
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useDeleteExportJob()
 *
 * const handleDelete = (jobId) => {
 *   if (confirm('Delete this job?')) {
 *     mutate(jobId, {
 *       onSuccess: () => {
 *         console.log('Job deleted')
 *       }
 *     })
 *   }
 * }
 */
export function useDeleteExportJob(): UseMutationResult<unknown, Error, string> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId: string) => deleteExportJob(jobId),
    onSuccess: (response, jobId) => {
      // Invalidate specific job cache
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOB(jobId) })
      // Invalidate job list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOBS })
    },
  })
}
