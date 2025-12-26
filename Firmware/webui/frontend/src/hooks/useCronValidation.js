/**
 * React Query hook for cron expression validation (Issue #233)
 *
 * Provides real-time validation of cron expressions with debounced input
 * to reduce unnecessary API calls while typing.
 *
 * Features:
 * - Debounced input (300ms) to avoid excessive API calls
 * - TanStack Query integration for caching and error handling
 * - Only fetches when expression is non-empty
 * - Returns validation status, human-readable description, and next executions
 *
 * @example
 * const { data, isLoading, isError } = useCronValidation("0 21 * * *")
 * if (data?.valid) {
 *   console.log(data.description) // "At 21:00 every day"
 *   console.log(data.next_executions) // ["2024-12-26T21:00:00", ...]
 * }
 */

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import { validateCronExpression } from '../utils/cronApi'

// =============================================================================
// Configuration
// =============================================================================

/**
 * Debounce delay in milliseconds.
 * 300ms provides a good balance:
 * - Fast enough to feel responsive
 * - Slow enough to avoid API calls on every keystroke
 */
const DEBOUNCE_DELAY_MS = 300

/**
 * Query stale time in milliseconds.
 * 1 minute is reasonable since cron validation results are deterministic
 * and don't change over time for the same expression.
 */
const STALE_TIME_MS = 60 * 1000

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for validating cron expressions with debouncing
 *
 * @param {string} expression - Cron expression to validate (e.g., "0 * * * *")
 * @param {Object} [options] - Hook options
 * @param {number} [options.count=5] - Number of next execution times to fetch
 * @param {Object} [options.queryOptions] - Additional React Query options
 * @returns {Object} React Query result with additional errorMessage property
 * @returns {Object} data - Validation result
 * @returns {boolean} data.valid - Whether expression is valid
 * @returns {string} data.expression - The validated expression
 * @returns {string} data.description - Human-readable description (if valid)
 * @returns {Array<string>} data.next_executions - Next execution times (if valid)
 * @returns {string} data.error - Error message (if invalid)
 * @returns {boolean} isLoading - Whether query is loading
 * @returns {boolean} isError - Whether query failed
 * @returns {Object} error - Error object if query failed
 * @returns {string|null} errorMessage - Normalized error message for UI display
 *
 * @example
 * // Basic usage with normalized error message
 * const { data, isLoading, errorMessage } = useCronValidation(expression)
 * if (errorMessage) {
 *   showError(errorMessage)
 * }
 *
 * @example
 * // With custom count and options
 * const { data, isLoading } = useCronValidation(expression, {
 *   count: 10,
 *   queryOptions: { onSuccess: (data) => console.log(data) }
 * })
 */
export function useCronValidation(expression, options = {}) {
  const { count = 5, queryOptions = {} } = options

  // Debounce the expression to avoid excessive API calls
  const [debouncedExpression, setDebouncedExpression] = useState(expression)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedExpression(expression)
    }, DEBOUNCE_DELAY_MS)

    return () => clearTimeout(timer)
  }, [expression])

  const query = useQuery({
    queryKey: QUERY_KEYS.CRON_VALIDATION(debouncedExpression),
    queryFn: () => validateCronExpression(debouncedExpression, count),
    enabled: Boolean(debouncedExpression?.trim()),
    staleTime: STALE_TIME_MS,
    ...queryOptions,
  })

  // Normalize error messages for consistent UX
  const getErrorMessage = () => {
    if (query.isError) {
      // Network/server error
      const serverError = query.error?.response?.data?.error
      if (serverError) return serverError
      if (query.error?.message) return `Validation failed: ${query.error.message}`
      return 'Unable to validate expression. Please try again.'
    }
    if (query.data?.valid === false) {
      // Validation error from API
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
