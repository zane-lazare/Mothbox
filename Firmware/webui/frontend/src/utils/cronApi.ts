/**
 * Cron Expression API functions for Issue #233
 *
 * Provides API integration for cron expression validation and preview:
 * - Validate cron expressions
 * - Get next execution times
 * - Get human-readable descriptions
 *
 * All functions follow the pattern from utils/api.js:
 * - Use the global `api` axios instance for CSRF handling
 * - Return axios response objects (access data via .data)
 * - Let axios throw errors for React Query to handle
 */

import { api } from './api'

// =============================================================================
// Configuration
// =============================================================================

/**
 * Scheduler UI API base path (relative to api.baseURL from utils/api.js).
 * This is the same prefix used in schedulerApi.js for consistency.
 */
export const SCHEDULER_API_PREFIX = '/scheduler/ui'

/**
 * API request timeout in milliseconds.
 * Set to 10 seconds for cron validation (should be fast).
 */
const API_TIMEOUT_MS = 10000

// =============================================================================
// Types
// =============================================================================

/**
 * Cron validation response (success)
 */
interface CronValidationSuccess {
  valid: true
  expression: string
  description: string
  next_executions: string[]
}

/**
 * Cron validation response (error)
 */
interface CronValidationError {
  valid: false
  expression: string
  error: string
}

/**
 * Cron validation response (union type)
 */
export type CronValidationResponse = CronValidationSuccess | CronValidationError

// =============================================================================
// Cron Validation
// =============================================================================

/**
 * Validate a cron expression and get next executions preview
 *
 * @param {string} expression - Cron expression to validate (e.g., "0 * * * *")
 * @param {number} [count=5] - Number of next execution times to return (default: 5)
 * @returns {Promise<Object>} Axios response with validation results
 *
 * Response on success (valid expression): {
 *   valid: true,
 *   expression: "0 * * * *",
 *   description: "At minute 0 of every hour",
 *   next_executions: [
 *     "2024-12-26T14:00:00",
 *     "2024-12-26T15:00:00",
 *     "2024-12-26T16:00:00",
 *     "2024-12-26T17:00:00",
 *     "2024-12-26T18:00:00"
 *   ]
 * }
 *
 * Response on error (invalid expression): {
 *   valid: false,
 *   expression: "invalid * * * *",
 *   error: "Invalid cron expression: invalid is not a valid minute value"
 * }
 *
 * @example
 * const response = await validateCronExpression("0 21 * * *", 3)
 * console.log(response.data.description) // "At 21:00 every day"
 * console.log(response.data.next_executions) // ["2024-12-26T21:00:00", ...]
 */
export const validateCronExpression = async (expression: string, count: number = 5): Promise<CronValidationResponse> => {
  const response = await api.post(
    `${SCHEDULER_API_PREFIX}/cron/validate`,
    { expression, count },
    { timeout: API_TIMEOUT_MS }
  )
  return response.data
}
