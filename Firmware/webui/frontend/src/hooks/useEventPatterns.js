/**
 * React Query hooks for Event Pattern operations (Issue #222)
 *
 * Provides hooks for managing event patterns:
 * - useBuiltinPatterns: List built-in event patterns
 * - useValidatePattern: Validate event pattern configuration
 * - usePatternDuration: Calculate pattern duration from actions
 *
 * Naming Convention:
 * - Query hooks: use<Resource> (e.g., useBuiltinPatterns)
 * - Mutation hooks: use<Action><Resource> (e.g., useValidatePattern)
 * - Utility hooks: use<Utility> (e.g., usePatternDuration)
 *
 * Query Options:
 * All query hooks accept an optional queryOptions parameter to customize React Query behavior
 * (e.g., refetchInterval, onSuccess, onError). These are spread after the default options.
 */

import { useMemo } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  listBuiltinPatterns,
  validatePattern,
} from '../utils/schedulerApi'

// =============================================================================
// Configuration
// =============================================================================

/**
 * Query cache configuration for event pattern data.
 *
 * STALE_TIME (5 min): How long data is considered "fresh" before refetching.
 * Built-in patterns are static (loaded from disk), so 5 minutes is appropriate.
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
    console.error(`[EventPattern ${operation}]:`, error.message || error)
  }
}

// =============================================================================
// Query Hooks
// =============================================================================

/**
 * List built-in event patterns
 *
 * Fetches pre-defined event patterns extracted from built-in schedules.
 * Built-in patterns are read-only templates that can be used when creating
 * new schedules or understanding common pattern structures.
 *
 * @param {Object} [queryOptions] - React Query options (refetchInterval, onSuccess, etc.)
 * @returns {Object} React Query result
 * @returns {Object} data - { patterns: [...], total, warnings }
 * @returns {boolean} isLoading - Whether initial query is loading
 * @returns {boolean} isError - Whether an error occurred
 * @returns {Object} error - Error object if query failed
 *
 * @example
 * const { data, isLoading } = useBuiltinPatterns()
 * if (data) {
 *   console.log(`${data.total} built-in patterns`)
 *   data.patterns.forEach(p => console.log(p.name))
 * }
 */
export function useBuiltinPatterns(queryOptions = {}) {
  return useQuery({
    queryKey: QUERY_KEYS.BUILTIN_PATTERNS,
    queryFn: async () => {
      const response = await listBuiltinPatterns()
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
 * Validate event pattern mutation
 *
 * Validates a pattern structure without saving it. Useful for providing
 * real-time validation feedback in pattern builder UIs.
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
 * const { mutate, isPending, data } = useValidatePattern()
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
 *         console.log('Pattern is valid!')
 *       } else {
 *         console.error('Validation error:', response.data.error)
 *       }
 *     }
 *   })
 * }
 */
export function useValidatePattern() {
  return useMutation({
    mutationFn: (data) => validatePattern(data),
    onError: (error) => handleMutationError(error, 'validatePattern'),
  })
}

// =============================================================================
// Utility Hooks
// =============================================================================

/**
 * Calculate the total duration of a pattern based on action offsets
 *
 * Returns the maximum offset_minutes value from all actions in the pattern.
 * This represents how long the pattern takes to complete from start to finish.
 *
 * Useful for:
 * - Displaying pattern duration in UI
 * - Checking if patterns fit within time windows
 * - Scheduling calculations
 *
 * **Performance Note:** This hook uses useMemo with the pattern object as a
 * dependency. If the parent component creates a new pattern object on each
 * render (even with the same data), useMemo will recalculate because the
 * object reference changes. To prevent unnecessary recalculations, callers
 * should memoize the pattern object.
 *
 * @param {Object|null} pattern - Event pattern object (should be memoized)
 * @param {Array} [pattern.actions] - Array of action objects with offset_minutes
 * @returns {number} Maximum offset in minutes, or 0 if no actions
 *
 * @example
 * // Good: Pattern is memoized, duration only recalculates when data changes
 * const pattern = useMemo(() => ({
 *   name: 'UV Capture Cycle',
 *   actions: [
 *     { action_type: 'gpio', action_name: 'attract_on', offset_minutes: 0 },
 *     { action_type: 'camera', action_name: 'takephoto', offset_minutes: 5 },
 *     { action_type: 'gpio', action_name: 'attract_off', offset_minutes: 15 }
 *   ]
 * }), [])
 * const duration = usePatternDuration(pattern) // "15"
 *
 * @example
 * // Also good: Pattern comes from React Query (already stable reference)
 * const { data } = useBuiltinPatterns()
 * const duration = usePatternDuration(data?.patterns?.[0])
 */
export function usePatternDuration(pattern) {
  return useMemo(() => {
    if (!pattern?.actions?.length) return 0
    return Math.max(...pattern.actions.map(a => a.offset_minutes ?? 0))
  }, [pattern])
}

export default useBuiltinPatterns
