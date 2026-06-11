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
 * Routine hooks are in useRoutines.ts (Issue #222, #322):
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
} from '../utils/schedulerApi'

// =============================================================================
// Types
// =============================================================================

interface SchedulesParams {
  include_builtin?: boolean
}

interface NextActionsParams {
  limit?: number
}

interface SchedulePreviewParams {
  days?: number
  lat?: number
  lon?: number
  tz?: string
}

interface CloneScheduleParams {
  id: string
  name?: string
}

interface ActivateScheduleParams {
  id: string
  options?: Record<string, unknown>
}

type SchedulesListResponse = unknown
type ScheduleResponse = unknown
type ActiveScheduleResponse = unknown
type NextActionsResponse = unknown
type SchedulePreviewResponse = unknown
type BuiltinSchedulesResponse = unknown
type CreateScheduleRequest = unknown
type UpdateScheduleRequest = unknown
type ValidateScheduleRequest = unknown

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
function handleMutationError(error: unknown, operation: string): void {
  if (import.meta.env.DEV) {
    const errorMessage = error instanceof Error ? error.message : String(error)
    console.error(`[Scheduler ${operation}]:`, errorMessage)
  }
  // Note: Could integrate error reporting service here in future
  // e.g., Sentry.captureException(error, { tags: { operation } })
}

/**
 * List all schedules
 *
 * @param params - API parameters
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
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
export function useSchedules(
  params: SchedulesParams = {},
  queryOptions: Omit<UseQueryOptions<SchedulesListResponse, Error>, 'queryKey' | 'queryFn'> = {}
) {
  const { include_builtin } = params

  // Build query key that includes params for proper cache separation
  // This ensures different param combinations have separate cache entries
  const queryKey = include_builtin !== undefined
    ? [...QUERY_KEYS.SCHEDULES, { include_builtin }]
    : QUERY_KEYS.SCHEDULES

  return useQuery<SchedulesListResponse, Error>({
    queryKey,
    queryFn: async () => {
      const apiParams: SchedulesParams = {}
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
 *
 * @example
 * const { data, isLoading } = useSchedule('schedule_1')
 * if (data) {
 *   console.log(`Schedule: ${data.name}`)
 *   console.log(`Events: ${data.events.length}`)
 * }
 */
export function useSchedule(
  id: string | null,
  queryOptions: Omit<UseQueryOptions<ScheduleResponse, Error>, 'queryKey' | 'queryFn' | 'enabled'> = {}
) {
  return useQuery<ScheduleResponse, Error>({
    queryKey: QUERY_KEYS.SCHEDULE(id),
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
 *
 * @example
 * const { data, isLoading } = useActiveSchedule()
 * if (data?.active_schedule) {
 *   console.log(`Active: ${data.active_schedule.name}`)
 * }
 */
export function useActiveSchedule(
  queryOptions: Omit<UseQueryOptions<ActiveScheduleResponse, Error>, 'queryKey' | 'queryFn'> = {}
) {
  return useQuery<ActiveScheduleResponse, Error>({
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
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
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
export function useNextActions(
  params: NextActionsParams = {},
  queryOptions: Omit<UseQueryOptions<NextActionsResponse, Error>, 'queryKey' | 'queryFn'> = {}
) {
  const { limit } = params

  // Build query key that includes params for proper cache separation
  const queryKeyParams: NextActionsParams = {}
  if (limit !== undefined) queryKeyParams.limit = limit

  return useQuery<NextActionsResponse, Error>({
    queryKey: [...QUERY_KEYS.NEXT_ACTIONS, queryKeyParams],
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
 * @param queryOptions - React Query options (refetchInterval, onSuccess, etc.)
 * @returns React Query result
 *
 * @example
 * const { data, isLoading } = useSchedulePreview('schedule_1', { days: 14 })
 * if (data) {
 *   console.log(`Next ${data.total} executions`)
 *   data.executions.forEach(e => console.log(e.scheduled_time))
 * }
 */
export function useSchedulePreview(
  id: string | null,
  params: SchedulePreviewParams = {},
  queryOptions: Omit<UseQueryOptions<SchedulePreviewResponse, Error>, 'queryKey' | 'queryFn' | 'enabled'> = {}
) {
  const { days, lat, lon, tz } = params

  // Only include defined params in query key to avoid cache misses from undefined values
  const queryKeyParams: SchedulePreviewParams = {}
  if (days !== undefined) queryKeyParams.days = days
  if (lat !== undefined) queryKeyParams.lat = lat
  if (lon !== undefined) queryKeyParams.lon = lon
  if (tz !== undefined) queryKeyParams.tz = tz

  return useQuery<SchedulePreviewResponse, Error>({
    queryKey: [...QUERY_KEYS.SCHEDULE_PREVIEW(id), queryKeyParams],
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
 *
 * @example
 * const { data, isLoading } = useBuiltinSchedules()
 * if (data) {
 *   console.log(`${data.total} built-in schedules`)
 *   data.schedules.forEach(s => console.log(s.name))
 * }
 */
export function useBuiltinSchedules(
  queryOptions: Omit<UseQueryOptions<BuiltinSchedulesResponse, Error>, 'queryKey' | 'queryFn'> = {}
) {
  return useQuery<BuiltinSchedulesResponse, Error>({
    queryKey: QUERY_KEYS.BUILTIN_SCHEDULES,
    queryFn: async () => {
      const response = await listBuiltinSchedules()
      return response.data
    },
    staleTime: QUERY_CONFIG.STALE_TIME, // 5 minutes - built-in schedules are static
    ...queryOptions,
  })
}

/**
 * Create new schedule mutation
 *
 * Invalidates schedules list cache on success.
 *
 * @returns React Query mutation result
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
export function useCreateSchedule(
  options: Omit<UseMutationOptions<unknown, Error, CreateScheduleRequest>, 'mutationFn'> = {}
) {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, CreateScheduleRequest>({
    mutationFn: (data) => createSchedule(data),
    onSuccess: () => {
      // Invalidate all schedule list variants (with and without include_builtin)
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false })
    },
    onError: (error) => handleMutationError(error, 'create'),
    ...options,
  })
}

/**
 * Update schedule mutation
 *
 * Invalidates schedule cache and schedules list on success.
 *
 * @returns React Query mutation result
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
export function useUpdateSchedule(
  options: Omit<UseMutationOptions<unknown, Error, { id: string; data: UpdateScheduleRequest }>, 'mutationFn'> = {}
) {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, { id: string; data: UpdateScheduleRequest }>({
    mutationFn: ({ id, data }) => updateSchedule(id, data),
    onSuccess: async (_, { id }) => {
      // Invalidate caches in parallel to avoid race conditions
      // Use exact: false for SCHEDULES to invalidate all variants (with/without include_builtin)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULE(id) }),
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false }),
      ])
    },
    onError: (error) => handleMutationError(error, 'update'),
    ...options,
  })
}

/**
 * Delete schedule mutation
 *
 * Invalidates schedule cache and schedules list on success.
 *
 * @returns React Query mutation result
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
export function useDeleteSchedule(
  options: Omit<UseMutationOptions<unknown, Error, string>, 'mutationFn'> = {}
) {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, string>({
    mutationFn: (id) => deleteSchedule(id),
    onSuccess: async (_, id) => {
      // Invalidate caches in parallel to avoid race conditions
      // Use exact: false for SCHEDULES to invalidate all variants (with/without include_builtin)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULE(id) }),
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false }),
      ])
    },
    onError: (error) => handleMutationError(error, 'delete'),
    ...options,
  })
}

/**
 * Clone schedule mutation
 *
 * Creates a copy of an existing schedule. Invalidates schedules list cache on success.
 *
 * @returns React Query mutation result
 *
 * @example
 * const { mutateAsync, isPending } = useCloneSchedule()
 * const response = await mutateAsync({ id: 'schedule_1' })
 * const clonedSchedule = response.data.schedule
 */
export function useCloneSchedule(
  options: Omit<UseMutationOptions<unknown, Error, CloneScheduleParams>, 'mutationFn'> = {}
) {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, CloneScheduleParams>({
    mutationFn: ({ id, name }) => cloneSchedule(id, name ? { name } : {}),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES, exact: false })
    },
    onError: (error) => handleMutationError(error, 'clone'),
    ...options,
  })
}

/**
 * Activate schedule mutation
 *
 * Invalidates active schedule and schedules list on success.
 *
 * @returns React Query mutation result
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
export function useActivateSchedule(
  options: Omit<UseMutationOptions<unknown, Error, ActivateScheduleParams>, 'mutationFn'> = {}
) {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, ActivateScheduleParams>({
    mutationFn: ({ id, options }) => activateSchedule(id, options),
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
    onError: (error) => handleMutationError(error, 'activate'),
    ...options,
  })
}

/**
 * Deactivate schedule mutation
 *
 * Invalidates active schedule and schedules list on success.
 *
 * @returns React Query mutation result
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
export function useDeactivateSchedule(
  options: Omit<UseMutationOptions<unknown, Error, void>, 'mutationFn'> = {}
) {
  const queryClient = useQueryClient()

  return useMutation<unknown, Error, void>({
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
    onError: (error) => handleMutationError(error, 'deactivate'),
    ...options,
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
export function useValidateSchedule(
  options: Omit<UseMutationOptions<unknown, Error, { id: string; data: ValidateScheduleRequest }>, 'mutationFn'> = {}
) {
  return useMutation<unknown, Error, { id: string; data: ValidateScheduleRequest }>({
    mutationFn: ({ id, data }) => validateSchedule(id, data),
    onError: (error) => handleMutationError(error, 'validate'),
    ...options,
  })
}

export default useSchedules

// =============================================================================
// Re-exports for backward compatibility (Issue #222)
// =============================================================================
// Routine hooks have been moved to useRoutines.ts (renamed from useEventPatterns.js in #322)
// useRoutineDuration is a utility hook for calculating routine duration
// These re-exports maintain backward compatibility for existing imports
export { useBuiltinRoutines, useValidateRoutine, useRoutineDuration } from './useRoutines'
