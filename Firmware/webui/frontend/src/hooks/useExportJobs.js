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

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listExportJobs,
  getExportJob,
  createExportJob,
  cancelExportJob,
  deleteExportJob,
} from '../utils/exportApi'

/**
 * List all export jobs with optional filtering and pagination
 *
 * @param {Object} [options] - Query options
 * @param {string} [options.status] - Filter by status (pending, running, completed, failed, cancelled, expired)
 * @param {number} [options.limit=50] - Max results (max: 100)
 * @param {number} [options.offset=0] - Pagination offset
 * @returns {Object} React Query result
 * @returns {Object} data - { jobs: [...], total, limit, offset }
 * @returns {boolean} isLoading - Whether initial query is loading
 * @returns {boolean} isError - Whether an error occurred
 * @returns {Object} error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useExportJobs({ status: 'completed', limit: 10 })
 * if (data) {
 *   console.log(`${data.total} completed jobs`)
 *   data.jobs.forEach(job => console.log(job.job_id))
 * }
 */
export function useExportJobs(options = {}) {
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
 * @param {string|null} jobId - Job ID (null to disable query)
 * @returns {Object} React Query result
 * @returns {Object} data - Job details with progress: { job_id, status, format, progress: { current, total, percent, phase }, ... }
 * @returns {boolean} isLoading - Whether initial query is loading
 * @returns {boolean} isError - Whether an error occurred
 * @returns {Object} error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useExportJob('550e8400-e29b-41d4-a716-446655440000')
 * if (data?.status === 'running') {
 *   console.log(`Progress: ${data.progress.percent}%`)
 *   console.log(`Phase: ${data.progress.phase}`)
 * }
 */
export function useExportJob(jobId) {
  return useQuery({
    queryKey: QUERY_KEYS.EXPORT_JOB(jobId),
    queryFn: async () => {
      const response = await getExportJob(jobId)
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
  })
}

/**
 * Create new export job mutation
 *
 * Invalidates job list cache on success to show new job.
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function (fire and forget)
 * @returns {Function} mutateAsync - Async mutation function (returns promise)
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
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
export function useCreateExportJob() {
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
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function with jobId parameter
 * @returns {Function} mutateAsync - Async mutation function
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
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
export function useCancelExportJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId) => cancelExportJob(jobId),
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
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function with jobId parameter
 * @returns {Function} mutateAsync - Async mutation function
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
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
export function useDeleteExportJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (jobId) => deleteExportJob(jobId),
    onSuccess: (response, jobId) => {
      // Invalidate specific job cache
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOB(jobId) })
      // Invalidate job list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.EXPORT_JOBS })
    },
  })
}
