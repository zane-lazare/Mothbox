/**
 * React Query hooks for Routine operations (Issue #222, #322)
 *
 * Provides hooks for managing routines:
 * - useBuiltinRoutines: List built-in routines
 * - useValidateRoutine: Validate routine configuration
 * - useRoutineDuration: Calculate routine duration from actions
 *
 * Naming Convention:
 * - Query hooks: use<Resource> (e.g., useBuiltinRoutines)
 * - Mutation hooks: use<Action><Resource> (e.g., useValidateRoutine)
 * - Utility hooks: use<Utility> (e.g., useRoutineDuration)
 *
 * Query Options:
 * All query hooks accept an optional queryOptions parameter to customize React Query behavior
 * (e.g., refetchInterval, onSuccess, onError). These are spread after the default options.
 */

import { useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listBuiltinRoutines,
  validateRoutine,
} from '../utils/schedulerApi'

// =============================================================================
// Configuration
// =============================================================================

/**
 * Query cache configuration for routine data.
 *
 * STALE_TIME (5 min): How long data is considered "fresh" before refetching.
 * Built-in routines are static (loaded from disk), so 5 minutes is appropriate.
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
 * @param {Error} error - The error from the mutation
 * @param {string} operation - Name of the operation for context
 */
function handleMutationError(error, operation) {
  if (import.meta.env.DEV) {
    console.error(`[Routine ${operation}]:`, error.message || error)
  }
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * List built-in routines
 *
 * Fetches pre-defined routines extracted from built-in schedules.
 * Built-in routines are read-only templates that can be used when creating
 * new schedules or understanding common routine structures.
 *
 * @param {Object} [queryOptions] - React Query options (refetchInterval, onSuccess, etc.)
 * @returns {Object} React Query result
 * @returns {Object} data - { patterns: [...], total, warnings }
 * @returns {boolean} isLoading - Whether initial query is loading
 * @returns {boolean} isError - Whether an error occurred
 * @returns {Object} error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useBuiltinRoutines()
 * if (data) {
 *   console.log(`${data.total} built-in routines`)
 *   data.patterns.forEach(p => console.log(p.name))
 * }
 */
export function useBuiltinRoutines(queryOptions = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.BUILTIN_ROUTINES,
    queryFn: async () => {
      const response = await listBuiltinRoutines()
      return response.data
    },
    staleTime: QUERY_CONFIG.STALE_TIME,
    ...queryOptions,
  })
}

// =============================================================================
// Mutation Hooks
// =============================================================================

/**
 * Validate routine mutation
 *
 * Validates a routine structure without saving it. Useful for providing
 * real-time validation feedback in routine builder UIs.
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function (fire and forget)
 * @returns {Function} mutateAsync - Async mutation function (returns promise)
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success { valid, pattern?, error? }
 *
 * @example
 * const { mutate, isPending, data } = useValidateRoutine()
 *
 * const handleValidate = () => {
 *   mutate({
 *     name: 'UV Capture Cycle',
 *     description: 'Turn on UV, capture, turn off',
 *     actions: [
 *       { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
 *       { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
 *       { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
 *     ]
 *   }, {
 *     onSuccess: (response) => {
 *       if (response.data.valid) {
 *         console.log('Routine is valid!')
 *       } else {
 *         console.error('Validation error:', response.data.error)
 *       }
 *     }
 *   })
 * }
 */
export function useValidateRoutine() {
  return useMutation({
    mutationFn: (data) => validateRoutine(data),
    onError: (error) => handleMutationError(error, 'validateRoutine'),
  })
}

// =============================================================================
// Utility Hooks
// =============================================================================

/**
 * Calculate the total duration of a routine based on action offsets
 *
 * Returns the maximum offset_minutes value from all actions in the routine.
 * This represents how long the routine takes to complete from start to finish.
 *
 * Useful for:
 * - Displaying routine duration in UI
 * - Checking if routines fit within time windows
 * - Scheduling calculations
 *
 * **Performance Note:** This hook uses useMemo with the routine object as a
 * dependency. If the parent component creates a new routine object on each
 * render (even with the same data), useMemo will recalculate because the
 * object reference changes. To prevent unnecessary recalculations, callers
 * should memoize the routine object.
 *
 * @param {Object|null} routine - Routine object (should be memoized)
 * @param {Array} [routine.actions] - Array of action objects with offset_minutes
 * @returns {number} Maximum offset in minutes, or 0 if no actions.
 *   Decimal values are supported and preserved (e.g., 5.5 for 5m 30s).
 *
 * @example
 * // Good: Routine is memoized, duration only recalculates when data changes
 * const routine = useMemo(() => ({
 *   name: 'UV Capture Cycle',
 *   actions: [
 *     { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
 *     { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
 *     { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
 *   ]
 * }), [])
 * const duration = useRoutineDuration(routine) // "15"
 *
 * @example
 * // Also good: Routine comes from React Query (already stable reference)
 * const { data } = useBuiltinRoutines()
 * const duration = useRoutineDuration(data?.patterns?.[0])
 */
export function useRoutineDuration(routine) {
  return useMemo(() => {
    if (!routine?.actions?.length) return 0
    return Math.max(...routine.actions.map(a => a.offset_minutes ?? 0))
  }, [routine])
}

export default useBuiltinRoutines
