/**
 * React Query hooks for Scheduler UI API (Issue #221)
 *
 * Provides hooks for managing scheduler operations:
 * - useSchedules: List all schedules
 * - useSchedule: Get single schedule
 * - useActiveSchedule: Get active schedule
 * - useSchedulePreview: Get schedule preview
 * - useBuiltinSchedules: List built-in schedules
 * - useCreateSchedule: Create new schedule
 * - useUpdateSchedule: Update existing schedule
 * - useDeleteSchedule: Delete schedule
 * - useActivateSchedule: Activate schedule
 * - useDeactivateSchedule: Deactivate schedule
 * - useValidateSchedule: Validate schedule configuration
 *
 * Routine hooks are in useRoutines.js (Issue #222, #322):
 * - useBuiltinRoutines: List built-in routines
 * - useValidateRoutine: Validate routine
 * - useRoutineDuration: Calculate routine duration
 *
 * Naming Convention:
 * - Query hooks: use<Resource> (e.g., useSchedules, useSchedule)
 * - Mutation hooks: use<Action><Resource> (e.g., useCreateSchedule, useDeleteSchedule)
 * - Validation hooks: useValidate<Resource> - intentionally distinct from CRUD mutations
 *   as they return validation results without modifying data
 *
 * Query Options:
 * All query hooks accept an optional queryOptions parameter to customize React Query behavior
 * (e.g., refetchInterval, onSuccess, onError). These are spread after the default options.
 */

import { useQuery, useMutation, useQueryClient, type UseQueryOptions, type UseMutationOptions } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listSchedules,
  getSchedule,
  getActiveSchedule,
  getSchedulePreview,
  listBuiltinSchedules,
  createSchedule,
  updateSchedule,
  deleteSchedule,
  cloneSchedule,
  activateSchedule,
  deactivateSchedule,
  validateSchedule,
  getNextActions,
  type ScheduleListParams,
  type ScheduleListResponse,
  type ScheduleMetadata,
  type ScheduleCreateData,
  type ScheduleUpdateData,
  type ScheduleOperationResponse,
  type ScheduleDeleteResponse,
  type ActiveScheduleResponse,
  type ScheduleActivationOptions,
  type ScheduleActivationResponse,
  type ScheduleDeactivationResponse,
  type NextActionsParams,
  type NextActionsResponse,
  type SchedulePreviewParams,
  type SchedulePreviewResponse,
  type ValidationResult,
  type BuiltInSchedulesResponse,
} from '../utils/schedulerApi'

// =============================================================================
// Configuration
// =============================================================================

/**
 * Query cache configuration for scheduler data.
 *
 * STALE_TIME (5 min): How long data is considered "fresh" before refetching.
 * Schedules change infrequently (user-initiated only), so 5 minutes is
 * reasonable. This reduces API calls while keeping data reasonably current.
 *
 * Note: We use React Query defaults for:
 * - gcTime (5 min): Garbage collection time for inactive queries
 * - refetchOnWindowFocus (true): Refresh when user returns to tab
 *
 * These defaults are appropriate since schedules should refresh when the
 * user returns to the app, and inactive queries can be garbage collected
 * relatively quickly.
 */
const QUERY_CONFIG = {
  STALE_TIME: 5 * 60 * 1000, // 5 minutes
}

/**
 * Centralized mutation error handler for development debugging.
 *
 * Logs errors to console in development mode only. In production,
 * errors are surfaced via React Query's isError/error properties.
 *
 * @param error - The error from the mutation
 * @param operation - Name of the operation for context
 */
function handleMutationError(error: Error, operation: string): void {
  if (import.meta.env.DEV) {
    console.error(`[Scheduler ${operation}]:`, error.message || error)
  }
  // Note: Could integrate error reporting service here in future
  // e.g., Sentry.captureException(error, { tags: { operation } })
}

// =============================================================================
// Type Definitions for Hook Parameters
// =============================================================================

/**
 * Options for useSchedules query
 */
type UseSchedulesOptions = Omit<
  UseQueryOptions<ScheduleListResponse, Error, ScheduleListResponse, readonly unknown[]>,
  'queryKey' | 'queryFn' | 'initialData'
> & { initialData?: () => undefined }

/**
 * Options for useSchedule query
 */
type UseScheduleOptions = Omit<
  UseQueryOptions<ScheduleMetadata, Error, ScheduleMetadata, readonly unknown[]>,
  'queryKey' | 'queryFn' | 'initialData'
> & { initialData?: () => undefined }

/**
 * Options for useActiveSchedule query
 */
type UseActiveScheduleOptions = Omit<
  UseQueryOptions<ActiveScheduleResponse, Error, ActiveScheduleResponse, readonly unknown[]>,
  'queryKey' | 'queryFn' | 'initialData'
> & { initialData?: () => undefined }

/**
 * Options for useNextActions query
 */
type UseNextActionsOptions = Omit<
  UseQueryOptions<NextActionsResponse, Error, NextActionsResponse, readonly unknown[]>,
  'queryKey' | 'queryFn' | 'initialData'
> & { initialData?: () => undefined }

/**
 * Options for useSchedulePreview query
 */
type UseSchedulePreviewOptions = Omit<
  UseQueryOptions<SchedulePreviewResponse, Error, SchedulePreviewResponse, readonly unknown[]>,
  'queryKey' | 'queryFn' | 'initialData'
> & { initialData?: () => undefined }

/**
 * Options for useBuiltinSchedules query
 */
type UseBuiltinSchedulesOptions = Omit<
  UseQueryOptions<BuiltInSchedulesResponse, Error, BuiltInSchedulesResponse, readonly unknown[]>,
  'queryKey' | 'queryFn' | 'initialData'
> & { initialData?: () => undefined }

/**
 * Mutation variables for useUpdateSchedule
 */
interface UpdateScheduleVariables {
  id: string
  data: ScheduleUpdateData
}

/**
 * Mutation variables for useCloneSchedule
 */
interface CloneScheduleVariables {
  id: string
  name?: string
}

/**
 * Mutation variables for useActivateSchedule
 */
interface ActivateScheduleVariables {
  id: string
  options?: ScheduleActivationOptions
}

/**
 * Mutation variables for useValidateSchedule
 */
interface ValidateScheduleVariables {
  id: string
  data: ScheduleCreateData | ScheduleUpdateData
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * List all schedules
 *
 * @param params - API parameters
 * @param params.include_builtin - Include built-in schedules
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 * @returns data - { schedules: [...], total }
 * @returns isLoading - Whether initial query is loading
 * @returns isError - Whether an error occurred
 * @returns error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useSchedules()
 * if (data) {
 *   console.log(`${data.total} schedules`)
 *   data.schedules.forEach(s => console.log(s.name))
 * }
 *
 * @example
 * // With custom options
 * const { data } = useSchedules(
 *   { include_builtin: true },
 *   { refetchInterval: 60000 }
 * )
 */
export function useSchedules(params: ScheduleListParams = {}, queryOptions: UseSchedulesOptions = {}) {
  const { include_builtin } = params

  // Build query key that includes params for proper cache separation
  // This ensures different param combinations have separate cache entries
  const queryKey = include_builtin !== undefined
    ? [...QUERY_KEYS.SCHEDULES, { include_builtin }] as const
    : QUERY_KEYS.SCHEDULES

  return useQuery({
    queryKey,
    queryFn: async () => {
      const apiParams: ScheduleListParams = {}
      if (include_builtin !== undefined) {
        apiParams.include_builtin = include_builtin
      }
      const response = await listSchedules(apiParams)
      return response.data
    },
    staleTime: QUERY_CONFIG.STALE_TIME,
    ...queryOptions,
  })
}

/**
 * Get single schedule by ID
 *
 * @param id - Schedule ID (null to disable query)
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 * @returns data - Schedule details
 * @returns isLoading - Whether initial query is loading
 * @returns isError - Whether an error occurred
 * @returns error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useSchedule('schedule_1')
 * if (data) {
 *   console.log(`Schedule: ${data.name}`)
 *   console.log(`Events: ${data.events.length}`)
 * }
 */
export function useSchedule(id: string | null, queryOptions: UseScheduleOptions = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.SCHEDULE(id || ''),
    queryFn: async () => {
      if (!id) throw new Error('Schedule ID is required')
      const response = await getSchedule(id)
      return response.data
    },
    enabled: !!id, // Disable query if id is null/undefined
    staleTime: QUERY_CONFIG.STALE_TIME, // 5 minutes
    ...queryOptions,
  })
}

/**
 * Get currently active schedule
 *
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 * @returns data - { active_schedule: {...} | null }
 * @returns isLoading - Whether initial query is loading
 * @returns isError - Whether an error occurred
 * @returns error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useActiveSchedule()
 * if (data?.active_schedule) {
 *   console.log(`Active: ${data.active_schedule.name}`)
 * }
 */
export function useActiveSchedule(queryOptions: UseActiveScheduleOptions = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.ACTIVE_SCHEDULE,
    queryFn: async () => {
      const response = await getActiveSchedule()
      return response.data
    },
    staleTime: QUERY_CONFIG.STALE_TIME, // 5 minutes
    ...queryOptions,
  })
}

/**
 * Get next actions for the active schedule
 *
 * Reads pre-expanded cron entries from persistent storage, avoiding
 * the need to recalculate solar times via the preview API.
 *
 * @param params - API parameters
 * @param params.limit - Maximum number of actions (default: 5, max: 100)
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 * @returns data - { actions: [...], schedule_id, coordinates_source, total_stored }
 * @returns isLoading - Whether initial query is loading
 * @returns isError - Whether an error occurred
 * @returns error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useNextActions({ limit: 10 })
 * if (data?.actions?.length > 0) {
 *   const next = data.actions[0]
 *   console.log(`Next: ${next.time} ${next.action_name}`)
 * }
 *
 * Issue #331: Store cron entries in active_state.json
 */
export function useNextActions(params: NextActionsParams = {}, queryOptions: UseNextActionsOptions = {}) {
  const { limit } = params

  // Build query key that includes params for proper cache separation
  const queryKeyParams: NextActionsParams = {}
  if (limit !== undefined) queryKeyParams.limit = limit

  return useQuery({
    queryKey: [...QUERY_KEYS.NEXT_ACTIONS, queryKeyParams] as const,
    queryFn: async () => {
      const response = await getNextActions(queryKeyParams)
      return response.data
    },
    staleTime: 30 * 1000, // 30 seconds - shorter than default since actions change over time
    ...queryOptions,
  })
}

/**
 * Get schedule preview (next N executions)
 *
 * @param id - Schedule ID (null to disable query)
 * @param params - Preview parameters
 * @param params.days - Number of days to preview (default: 7)
 * @param params.lat - Latitude for solar/moon calculations
 * @param params.lon - Longitude for solar/moon calculations
 * @param params.tz - Timezone (e.g., "America/New_York")
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 * @returns data - { schedule_id, preview_days, executions: [...], total }
 * @returns isLoading - Whether initial query is loading
 * @returns isError - Whether an error occurred
 * @returns error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useSchedulePreview('schedule_1', { days: 14 })
 * if (data) {
 *   console.log(`Next ${data.total} executions`)
 *   data.executions.forEach(e => console.log(e.scheduled_time))
 * }
 */
export function useSchedulePreview(id: string | null, params: SchedulePreviewParams = {}, queryOptions: UseSchedulePreviewOptions = {}) {
  const { days, lat, lon, tz } = params

  // Only include defined params in query key to avoid cache misses from undefined values
  const queryKeyParams: SchedulePreviewParams = {}
  if (days !== undefined) queryKeyParams.days = days
  if (lat !== undefined) queryKeyParams.lat = lat
  if (lon !== undefined) queryKeyParams.lon = lon
  if (tz !== undefined) queryKeyParams.tz = tz

  return useQuery({
    queryKey: [...QUERY_KEYS.SCHEDULE_PREVIEW(id || ''), queryKeyParams] as const,
    queryFn: async () => {
      if (!id) throw new Error('Schedule ID is required')
      const response = await getSchedulePreview(id, queryKeyParams)
      return response.data
    },
    enabled: !!id,
    staleTime: QUERY_CONFIG.STALE_TIME,
    ...queryOptions,
  })
}

/**
 * List built-in schedules
 *
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 * @returns data - { schedules: [...], total }
 * @returns isLoading - Whether initial query is loading
 * @returns isError - Whether an error occurred
 * @returns error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useBuiltinSchedules()
 * if (data) {
 *   console.log(`${data.total} built-in schedules`)
 *   data.schedules.forEach(s => console.log(s.name))
 * }
 */
export function useBuiltinSchedules(queryOptions: UseBuiltinSchedulesOptions = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.BUILTIN_SCHEDULES,
    queryFn: async () => {
      const response = await listBuiltinSchedules()
      return response.data
    },
    staleTime: QUERY_CONFIG.STALE_TIME, // 5 minutes - built-in schedules are static
    ...queryOptions,
  })
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Create new schedule mutation
 *
 * Invalidates schedules list cache on success.
 *
 * @returns React Query mutation result
 * @returns mutate - Mutation function (fire and forget)
 * @returns mutateAsync - Async mutation function (returns promise)
 * @returns isPending - Whether mutation is in progress
 * @returns isError - Whether mutation failed
 * @returns error - Error object if mutation failed
 * @returns data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useCreateSchedule()
 *
 * const handleCreate = () => {
 *   mutate({
 *     name: 'Evening Moths',
 *     description: 'Capture moths after sunset',
 *     events: [
 *       {
 *         name: 'evening_capture',
 *         action: 'take_photo',
 *         trigger: { type: 'solar', solar_event: 'sunset', offset_minutes: 30 }
 *       }
 *     ]
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Created:', response.data.id)
 *     },
 *     onError: (error) => {
 *       console.error('Failed:', error.message)
 *     }
 *   })
 * }
 */
export function useCreateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ScheduleCreateData) => createSchedule(data),
    onSuccess: () => {
      // Invalidate all schedule list variants (with and without include_builtin)
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false })
    },
    onError: (error: Error) => handleMutationError(error, 'create'),
  })
}

/**
 * Update schedule mutation
 *
 * Invalidates schedule cache and schedules list on success.
 *
 * @returns React Query mutation result
 * @returns mutate - Mutation function with { id, data } parameter
 * @returns mutateAsync - Async mutation function
 * @returns isPending - Whether mutation is in progress
 * @returns isError - Whether mutation failed
 * @returns error - Error object if mutation failed
 * @returns data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useUpdateSchedule()
 *
 * const handleUpdate = (id) => {
 *   mutate({
 *     id,
 *     data: { description: 'Updated description' }
 *   }, {
 *     onSuccess: () => {
 *       console.log('Updated')
 *     }
 *   })
 * }
 */
export function useUpdateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: UpdateScheduleVariables) => updateSchedule(id, data),
    onSuccess: async (_, { id }) => {
      // Invalidate caches in parallel to avoid race conditions
      // Use exact: false for SCHEDULES to invalidate all variants (with/without include_builtin)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULE(id) }),
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false }),
      ])
    },
    onError: (error: Error) => handleMutationError(error, 'update'),
  })
}

/**
 * Delete schedule mutation
 *
 * Invalidates schedule cache and schedules list on success.
 *
 * @returns React Query mutation result
 * @returns mutate - Mutation function with id parameter
 * @returns mutateAsync - Async mutation function
 * @returns isPending - Whether mutation is in progress
 * @returns isError - Whether mutation failed
 * @returns error - Error object if mutation failed
 * @returns data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useDeleteSchedule()
 * const [showConfirm, setShowConfirm] = useState(false)
 * const [idToDelete, setIdToDelete] = useState(null)
 *
 * const handleDeleteClick = (id) => {
 *   setIdToDelete(id)
 *   setShowConfirm(true)
 * }
 *
 * const handleConfirmDelete = () => {
 *   mutate(idToDelete, {
 *     onSuccess: () => setShowConfirm(false)
 *   })
 * }
 *
 * <ConfirmDialog
 *   isOpen={showConfirm}
 *   onClose={() => setShowConfirm(false)}
 *   onConfirm={handleConfirmDelete}
 *   title="Delete Schedule?"
 *   message="This action cannot be undone."
 *   confirmLabel="Delete"
 *   variant="danger"
 *   isLoading={isPending}
 * />
 */
export function useDeleteSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => deleteSchedule(id),
    onSuccess: async (_, id) => {
      // Invalidate caches in parallel to avoid race conditions
      // Use exact: false for SCHEDULES to invalidate all variants (with/without include_builtin)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULE(id) }),
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false }),
      ])
    },
    onError: (error: Error) => handleMutationError(error, 'delete'),
  })
}

/**
 * Clone schedule mutation
 *
 * Creates a copy of an existing schedule. Invalidates schedules list cache on success.
 *
 * @returns React Query mutation result
 * @returns mutateAsync - Async mutation function with { id, name? } parameter
 * @returns isPending - Whether mutation is in progress
 *
 * @example
 * const { mutateAsync, isPending } = useCloneSchedule()
 * const response = await mutateAsync({ id: 'schedule_1' })
 * const clonedSchedule = response.data.schedule
 */
export function useCloneSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, name }: CloneScheduleVariables) => cloneSchedule(id, name ? { name } : {}),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false })
    },
    onError: (error: Error) => handleMutationError(error, 'clone'),
  })
}

/**
 * Activate schedule mutation
 *
 * Invalidates active schedule and schedules list on success.
 *
 * @returns React Query mutation result
 * @returns mutate - Mutation function with { id, options } parameter
 * @returns mutateAsync - Async mutation function
 * @returns isPending - Whether mutation is in progress
 * @returns isError - Whether mutation failed
 * @returns error - Error object if mutation failed
 * @returns data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useActivateSchedule()
 *
 * const handleActivate = (id) => {
 *   mutate({
 *     id,
 *     options: { create_deployment: true }
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Activated:', response.data.schedule_id)
 *     }
 *   })
 * }
 */
export function useActivateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, options }: ActivateScheduleVariables) => activateSchedule(id, options),
    onSuccess: async () => {
      // Refetch queries to ensure UI updates immediately after activation
      // Using refetchQueries instead of invalidateQueries ensures the refetch completes
      // before onSuccess returns, which is critical for E2E tests that check for banner visibility
      // Use exact: false for SCHEDULES to refetch all variants (with/without include_builtin)
      await Promise.all([
        queryClient.refetchQueries({ queryKey: QUERY_KEYS.ACTIVE_SCHEDULE }),
        queryClient.refetchQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false }),
      ])
    },
    onError: (error: Error) => handleMutationError(error, 'activate'),
  })
}

/**
 * Deactivate schedule mutation
 *
 * Invalidates active schedule and schedules list on success.
 *
 * @returns React Query mutation result
 * @returns mutate - Mutation function (no parameters)
 * @returns mutateAsync - Async mutation function
 * @returns isPending - Whether mutation is in progress
 * @returns isError - Whether mutation failed
 * @returns error - Error object if mutation failed
 * @returns data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useDeactivateSchedule()
 *
 * const handleDeactivate = () => {
 *   mutate(undefined, {
 *     onSuccess: () => {
 *       console.log('Deactivated')
 *     }
 *   })
 * }
 */
export function useDeactivateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => deactivateSchedule(),
    onSuccess: async () => {
      // Refetch queries to ensure UI updates immediately after deactivation
      // Using refetchQueries instead of invalidateQueries ensures the refetch completes
      // before onSuccess returns, which is critical for E2E tests that check for banner visibility
      // Use exact: false for SCHEDULES to refetch all variants (with/without include_builtin)
      await Promise.all([
        queryClient.refetchQueries({ queryKey: QUERY_KEYS.ACTIVE_SCHEDULE }),
        queryClient.refetchQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false }),
      ])
    },
    onError: (error: Error) => handleMutationError(error, 'deactivate'),
  })
}

/**
 * Validate schedule configuration mutation
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutate, isPending } = useValidateSchedule()
 * mutate({ id: 'schedule_1', data: scheduleData })
 */
export function useValidateSchedule() {
  return useMutation({
    mutationFn: ({ id, data }: ValidateScheduleVariables) => validateSchedule(id, data),
    onError: (error: Error) => handleMutationError(error, 'validate'),
  })
}

export default useSchedules

// =============================================================================
// Re-exports for backward compatibility (Issue #222)
// =============================================================================
// Routine hooks have been moved to useRoutines.js (renamed from useEventPatterns.js in #322)
// useRoutineDuration is a utility hook for calculating routine duration
// These re-exports maintain backward compatibility for existing imports
export { useBuiltinRoutines, useValidateRoutine, useRoutineDuration } from './useRoutines'
