/**
 * React Query hook for cron expression validation (Issue #233)
 *
 * Provides real-time validation of cron expressions with debounced input
 * to reduce unnecessary API calls while typing.
 */

import { useState, useEffect } from 'react'
import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
// @ts-expect-error — queryKeys.js has no type declarations (pre-migration)
import { QUERY_KEYS } from '../utils/queryKeys'
// @ts-expect-error — cronApi.js has no type declarations (pre-migration)
import { validateCronExpression } from '../utils/cronApi'

// -- Types -------------------------------------------------------------------

/** Shape returned by the cron validation API endpoint. */
export interface CronValidationResult {
  valid: boolean
  expression: string
  /** Human-readable description (present when valid) */
  description?: string
  /** ISO timestamps of next N executions (present when valid) */
  next_executions?: string[]
  /** Error message (present when invalid) */
  error?: string
}

export interface UseCronValidationOptions {
  /** Number of next execution times to fetch (default: 5) */
  count?: number
  /** Additional React Query options */
  queryOptions?: Partial<UseQueryOptions<CronValidationResult>>
}

export interface UseCronValidationReturn {
  /** Validation result from the API */
  data: CronValidationResult | undefined
  /** Whether the query is currently loading */
  isLoading: boolean
  /** Whether the query errored */
  isError: boolean
  /** The error object if the query failed */
  error: Error | null
  /** Normalized error message for UI display */
  errorMessage: string | null
}

// -- Configuration -----------------------------------------------------------

/** Debounce delay — 300ms balances responsiveness vs API spam. */
const DEBOUNCE_DELAY_MS = 300

/** Cron validation results are deterministic, so 1 min stale time is fine. */
const STALE_TIME_MS = 60 * 1000

// -- Hook --------------------------------------------------------------------

/**
 * Hook for validating cron expressions with debouncing.
 *
 * @param expression - Cron expression to validate (e.g., "0 * * * *")
 * @param options - Optional count and query overrides
 */
export function useCronValidation(
  expression: string,
  options: UseCronValidationOptions = {},
): UseCronValidationReturn {
  const { count = 5, queryOptions = {} } = options

  // Debounce the expression to avoid excessive API calls
  const [debouncedExpression, setDebouncedExpression] = useState(expression)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedExpression(expression)
    }, DEBOUNCE_DELAY_MS)

    return () => clearTimeout(timer)
  }, [expression])

  const query = useQuery<CronValidationResult>({
    queryKey: QUERY_KEYS.CRON_VALIDATION(debouncedExpression),
    queryFn: () => validateCronExpression(debouncedExpression, count),
    enabled: Boolean(debouncedExpression?.trim()),
    staleTime: STALE_TIME_MS,
    ...queryOptions,
  })

  // Normalize error messages for consistent UX
  const getErrorMessage = (): string | null => {
    if (query.isError) {
      const serverError = (query.error as { response?: { data?: { error?: string } } })
        ?.response?.data?.error
      if (serverError) return serverError
      if (query.error?.message) return `Validation failed: ${query.error.message}`
      return 'Unable to validate expression. Please try again.'
    }
    if (query.data?.valid === false) {
      return query.data.error || 'Invalid cron expression'
    }
    return null
  }

  return {
    ...query,
    errorMessage: getErrorMessage(),
  }
}

export default useCronValidation
