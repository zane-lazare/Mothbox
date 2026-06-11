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
import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { validateDraftRoutines, type DraftValidationResponse, type ScheduleEvent } from '../utils/schedulerApi'
import type { AxiosResponse } from 'axios'

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
// Types
// =============================================================================

/**
 * Hook options for configuring draft validation
 */
export interface UseValidateDraftOptions {
  /** Number of days to preview (default: 1 for editor) */
  days?: number
  /** Latitude for solar calculations */
  latitude?: number
  /** Longitude for solar calculations */
  longitude?: number
  /** Timezone for time resolution */
  timezone?: string
  /** Additional React Query options */
  queryOptions?: Partial<UseQueryOptions<DraftValidationResponse>>
}

/**
 * Hook return type
 */
export interface UseValidateDraftReturn {
  /** Function to trigger validation with routines array */
  validateDraft: (routines: ScheduleEvent[]) => void
  /** Validation result from API */
  conflictReport: DraftValidationResponse | undefined
  /** Whether validation is in progress */
  isValidating: boolean
  /** Whether validation failed */
  isError: boolean
  /** Error object if validation failed */
  error: Error | null
  /** Reset validation state */
  reset: () => void
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for validating draft routines with debouncing
 *
 * @param options - Hook options
 * @returns Hook result
 */
export function useValidateDraft(options: UseValidateDraftOptions = {}): UseValidateDraftReturn {
  const {
    days = 1,
    latitude,
    longitude,
    timezone,
    queryOptions = {},
  } = options

  // Track the routines to validate (debounced)
  const [debouncedRoutines, setDebouncedRoutines] = useState<ScheduleEvent[] | null>(null)
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)

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
    queryFn: async (): Promise<DraftValidationResponse | null> => {
      if (!debouncedRoutines?.length) {
        return null
      }

      const params: {
        routines: ScheduleEvent[]
        days: number
        latitude?: number
        longitude?: number
        timezone?: string
      } = { routines: debouncedRoutines, days }

      if (latitude !== undefined && longitude !== undefined) {
        params.latitude = latitude
        params.longitude = longitude
      }
      if (timezone) {
        params.timezone = timezone
      }

      const response: AxiosResponse<DraftValidationResponse> = await validateDraftRoutines(params)
      return response.data
    },
    enabled: Boolean(routinesHash),
    staleTime: STALE_TIME_MS,
    ...queryOptions,
  })

  /**
   * Trigger validation with debouncing
   * @param routines - Array of routine objects to validate
   */
  const validateDraft = useCallback((routines: ScheduleEvent[]) => {
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    // Filter to only routines with valid structure
    const validRoutines = routines?.filter(r =>
      r?.trigger?.type && r?.action
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
    conflictReport: query.data ?? undefined,
    isValidating: query.isFetching,
    isError: query.isError,
    error: query.error,
    reset,
  }
}

export default useValidateDraft
