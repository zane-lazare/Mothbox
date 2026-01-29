/**
 * React Query hook for draft schedule validation
 *
 * Provides real-time conflict detection for unsaved routines with debounced
 * input to reduce unnecessary API calls while editing.
 *
 * Features:
 * - Debounced input (400ms) to avoid excessive API calls during editing
 * - TanStack Query integration for caching and error handling
 * - Only validates when routines have valid triggers and actions
 * - Returns conflict report with severity levels
 *
 * @example
 * const { conflictReport, isValidating, validateDraft } = useValidateDraft()
 *
 * // Trigger validation when routines change
 * useEffect(() => {
 *   if (routines.length > 0) {
 *     validateDraft(routines)
 *   }
 * }, [routines, validateDraft])
 *
 * // Display conflicts
 * if (conflictReport?.conflicts?.length > 0) {
 *   console.log(`${conflictReport.total_conflicts} conflicts detected`)
 * }
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { validateDraftRoutines } from '../utils/schedulerApi'

// =============================================================================
// Configuration
// =============================================================================

/**
 * Debounce delay in milliseconds.
 * 400ms provides a good balance:
 * - Fast enough to feel responsive after editing
 * - Slow enough to avoid API calls on every keystroke
 */
const DEBOUNCE_DELAY_MS = 400

/**
 * Query stale time in milliseconds.
 * 30 seconds is reasonable since conflict detection results may change
 * as the current time advances (affecting solar/interval triggers).
 */
const STALE_TIME_MS = 30 * 1000

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for validating draft routines with debouncing
 *
 * @param {Object} [options] - Hook options
 * @param {number} [options.days=1] - Number of days to preview (default: 1 for editor)
 * @param {number} [options.latitude] - Latitude for solar calculations
 * @param {number} [options.longitude] - Longitude for solar calculations
 * @param {string} [options.timezone] - Timezone for time resolution
 * @param {Object} [options.queryOptions] - Additional React Query options
 * @returns {Object} Hook result
 * @returns {Function} validateDraft - Function to trigger validation with routines array
 * @returns {Object|null} conflictReport - Validation result from API
 * @returns {boolean} isValidating - Whether validation is in progress
 * @returns {boolean} isError - Whether validation failed
 * @returns {Object|null} error - Error object if validation failed
 * @returns {Function} reset - Reset validation state
 */
export function useValidateDraft(options = {}) {
  const {
    days = 1,
    latitude,
    longitude,
    timezone,
    queryOptions = {},
  } = options

  // Track the routines to validate (debounced)
  const [debouncedRoutines, setDebouncedRoutines] = useState(null)
  const debounceTimerRef = useRef(null)

  // Create stable hash of routines for query key
  const routinesHash = useMemo(() => {
    if (!debouncedRoutines?.length) return null
    try {
      return JSON.stringify(debouncedRoutines)
    } catch {
      return null
    }
  }, [debouncedRoutines])

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

  // Validation query
  const query = useQuery({
    queryKey: ['scheduler', 'draft-validation', routinesHash, days, latitude, longitude, timezone],
    queryFn: async () => {
      if (!debouncedRoutines?.length) {
        return null
      }

      const params = { routines: debouncedRoutines, days }
      if (latitude !== undefined && longitude !== undefined) {
        params.latitude = latitude
        params.longitude = longitude
      }
      if (timezone) {
        params.timezone = timezone
      }

      const response = await validateDraftRoutines(params)
      return response.data
    },
    enabled: Boolean(routinesHash),
    staleTime: STALE_TIME_MS,
    ...queryOptions,
  })

  /**
   * Trigger validation with debouncing
   * @param {Array} routines - Array of routine objects to validate
   */
  const validateDraft = useCallback((routines) => {
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    // Filter to only routines with valid structure
    const validRoutines = routines?.filter(r =>
      r?.trigger?.trigger_type && r?.actions?.length > 0
    ) || []

    // Set debounced value after delay
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedRoutines(validRoutines.length > 0 ? validRoutines : null)
    }, DEBOUNCE_DELAY_MS)
  }, [])

  /**
   * Reset validation state
   */
  const reset = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    setDebouncedRoutines(null)
  }, [])

  return {
    validateDraft,
    conflictReport: query.data,
    isValidating: query.isFetching,
    isError: query.isError,
    error: query.error,
    reset,
  }
}

export default useValidateDraft
