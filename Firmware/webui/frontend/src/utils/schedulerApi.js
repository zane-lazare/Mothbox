/**
 * Scheduler API functions for Issue #221
 *
 * Provides API integration for scheduler CRUD operations:
 * - Schedule CRUD (list, get, create, update, delete)
 * - Active schedule management (get, activate, deactivate)
 * - Preview and validation
 * - Built-in schedules and patterns
 *
 * All functions follow the pattern from utils/api.js:
 * - Use the global `api` axios instance for CSRF handling
 * - Return axios response objects (access data via .data)
 * - Let axios throw errors for React Query to handle
 *
 * Security Note:
 * Error messages from server responses are passed through to React components.
 * React automatically escapes content rendered in JSX (e.g., {error.message}),
 * preventing XSS attacks. Do NOT use dangerouslySetInnerHTML with error messages.
 */

import { api } from './api'

// =============================================================================
// Configuration
// =============================================================================

/**
 * API request timeout in milliseconds.
 *
 * Set to 30 seconds to accommodate:
 * - Preview calculations with many solar/moon events
 * - Slow network connections on remote Mothbox devices
 * - Server-side schedule validation with complex patterns
 *
 * Axios will throw an error with code 'ECONNABORTED' on timeout.
 */
const API_TIMEOUT_MS = 30000

/**
 * Scheduler UI API base path (relative to api.baseURL from utils/api.js).
 * Extracted as constant for:
 * - Easy updates if API versioning is added
 * - Clearer intent in function calls
 * - Simpler testing/mocking
 */
const SCHEDULER_API_PREFIX = '/scheduler/ui'

// =============================================================================
// Schedule CRUD
// =============================================================================

/**
 * List all schedules
 *
 * @param {Object} [params] - Query parameters
 * @param {boolean} [params.include_builtin] - Include built-in schedules
 * @returns {Promise<Object>} Axios response with schedules list
 *
 * Response: {
 *   schedules: [
 *     {
 *       id: "schedule_id",
 *       name: "Evening Moths",
 *       category: "user",
 *       description: "Capture moths after sunset",
 *       events: [...],
 *       ...
 *     },
 *     ...
 *   ],
 *   total: 5
 * }
 */
export const listSchedules = (params = {}) =>
  api.get(`${SCHEDULER_API_PREFIX}/schedules`, { params, timeout: API_TIMEOUT_MS })

/**
 * Get schedule by ID
 *
 * @param {string} id - Schedule ID
 * @returns {Promise<Object>} Axios response with schedule details
 *
 * Response: {
 *   id: "schedule_id",
 *   name: "Evening Moths",
 *   category: "user",
 *   description: "Capture moths after sunset",
 *   events: [
 *     {
 *       name: "evening_capture",
 *       action: "take_photo",
 *       trigger: { type: "solar", solar_event: "sunset", offset_minutes: 30 },
 *       ...
 *     },
 *     ...
 *   ],
 *   created_at: "2024-12-01T10:00:00Z",
 *   modified_at: "2024-12-15T14:30:00Z"
 * }
 */
export const getSchedule = (id) =>
  api.get(`${SCHEDULER_API_PREFIX}/schedules/${id}`, { timeout: API_TIMEOUT_MS })

/**
 * Create new schedule
 *
 * @param {Object} data - Schedule data
 * @param {string} data.name - Schedule name (required)
 * @param {string} [data.description] - Schedule description
 * @param {Array} data.events - Event definitions (required)
 * @param {Object} [data.metadata] - Additional metadata
 * @returns {Promise<Object>} Axios response with created schedule
 *
 * Response: {
 *   id: "schedule_id",
 *   message: "Schedule created",
 *   schedule: { ... }
 * }
 */
export const createSchedule = (data) =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules`, data, { timeout: API_TIMEOUT_MS })

/**
 * Update existing schedule
 *
 * @param {string} id - Schedule ID
 * @param {Object} data - Schedule data (partial update supported)
 * @param {string} [data.name] - Schedule name
 * @param {string} [data.description] - Schedule description
 * @param {Array} [data.events] - Event definitions
 * @param {Object} [data.metadata] - Additional metadata
 * @returns {Promise<Object>} Axios response with updated schedule
 *
 * Response: {
 *   id: "schedule_id",
 *   message: "Schedule updated",
 *   schedule: { ... }
 * }
 */
export const updateSchedule = (id, data) =>
  api.put(`${SCHEDULER_API_PREFIX}/schedules/${id}`, data, { timeout: API_TIMEOUT_MS })

/**
 * Delete schedule
 *
 * @param {string} id - Schedule ID
 * @returns {Promise<Object>} Axios response with success status
 *
 * Response: {
 *   message: "Schedule deleted",
 *   id: "schedule_id"
 * }
 */
export const deleteSchedule = (id) =>
  api.delete(`${SCHEDULER_API_PREFIX}/schedules/${id}`, { timeout: API_TIMEOUT_MS })

// =============================================================================
// Active Schedule
// =============================================================================

/**
 * Get currently active schedule
 *
 * @returns {Promise<Object>} Axios response with active schedule or null
 *
 * Response: {
 *   active_schedule: {
 *     id: "schedule_id",
 *     name: "Evening Moths",
 *     activated_at: "2024-12-15T10:00:00Z",
 *     ...
 *   } | null
 * }
 */
export const getActiveSchedule = () =>
  api.get(`${SCHEDULER_API_PREFIX}/schedules/active`, { timeout: API_TIMEOUT_MS })

/**
 * Activate a schedule
 *
 * @param {string} id - Schedule ID
 * @param {Object} [options] - Activation options
 * @param {boolean} [options.create_deployment] - Create deployment metadata
 * @returns {Promise<Object>} Axios response with activation status
 *
 * Response: {
 *   message: "Schedule activated",
 *   schedule_id: "schedule_id",
 *   deployment_created: true
 * }
 */
export const activateSchedule = (id, options = {}) =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules/${id}/activate`, options, { timeout: API_TIMEOUT_MS })

/**
 * Deactivate currently active schedule
 *
 * @returns {Promise<Object>} Axios response with deactivation status
 *
 * Response: {
 *   message: "Schedule deactivated",
 *   schedule_id: "schedule_id"
 * }
 */
export const deactivateSchedule = () =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules/deactivate`, {}, { timeout: API_TIMEOUT_MS })

// =============================================================================
// Preview/Validation
// =============================================================================

/**
 * Get schedule preview (next N executions)
 *
 * @param {string} id - Schedule ID
 * @param {Object} [params] - Preview parameters
 * @param {number} [params.days] - Number of days to preview (default: 7)
 * @param {number} [params.lat] - Latitude for solar/moon calculations
 * @param {number} [params.lon] - Longitude for solar/moon calculations
 * @param {string} [params.tz] - Timezone (e.g., "America/New_York")
 * @returns {Promise<Object>} Axios response with preview executions
 *
 * Response: {
 *   schedule_id: "schedule_id",
 *   preview_days: 7,
 *   executions: [
 *     {
 *       event_name: "evening_capture",
 *       action: "take_photo",
 *       scheduled_time: "2024-12-15T18:30:00Z",
 *       trigger_info: { ... }
 *     },
 *     ...
 *   ],
 *   total: 14
 * }
 */
export const getSchedulePreview = (id, params = {}) =>
  api.get(`${SCHEDULER_API_PREFIX}/schedules/${id}/preview`, { params, timeout: API_TIMEOUT_MS })

/**
 * Validate schedule configuration
 *
 * @param {string} id - Schedule ID
 * @param {Object} data - Schedule data to validate
 * @returns {Promise<Object>} Axios response with validation results
 *
 * Response: {
 *   valid: true,
 *   errors: [],
 *   warnings: ["Solar events require GPS coordinates"]
 * }
 */
export const validateSchedule = (id, data) =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules/${id}/validate`, data, { timeout: API_TIMEOUT_MS })

/**
 * Validate draft routines for conflicts without requiring saved schedule.
 *
 * Useful for real-time conflict detection in the schedule editor before saving.
 *
 * @param {Object} data - Draft validation data
 * @param {Array} data.routines - Array of routine objects to validate
 * @param {number} [data.days] - Number of days to preview (default: 7)
 * @param {number} [data.latitude] - Latitude for solar calculations
 * @param {number} [data.longitude] - Longitude for solar calculations
 * @param {string} [data.timezone] - Timezone (default: UTC)
 * @returns {Promise<Object>} Axios response with validation results
 *
 * Response: {
 *   valid: true/false,
 *   has_warnings: true/false,
 *   conflicts: [...],
 *   total_conflicts: number,
 *   blocking_conflicts: number
 * }
 */
export const validateDraftRoutines = (data) =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules/validate-draft`, data, { timeout: API_TIMEOUT_MS })

// =============================================================================
// Built-in Resources
// =============================================================================

/**
 * List built-in schedules
 *
 * @returns {Promise<Object>} Axios response with built-in schedules
 *
 * Response: {
 *   schedules: [
 *     {
 *       schedule_id: "sunset_moths",
 *       name: "Sunset Moths",
 *       description: "Capture moths at dusk",
 *       trigger_type: "solar",
 *       enabled: true,
 *       is_active: false,
 *       ...
 *     },
 *     ...
 *   ],
 *   total: 3
 * }
 */
export const listBuiltinSchedules = () =>
  api.get(`${SCHEDULER_API_PREFIX}/schedules/builtin`, { timeout: API_TIMEOUT_MS })

/**
 * List built-in event patterns
 *
 * @returns {Promise<Object>} Axios response with built-in patterns
 *
 * Response: {
 *   patterns: [
 *     {
 *       pattern_id: "uv_capture_cycle",
 *       name: "UV Capture Cycle",
 *       description: "Turn on UV, capture photo, turn off",
 *       category: "built-in",
 *       actions: [...],
 *       source_schedule: "Nightly Moth Survey",
 *       duration_minutes: 15,
 *       ...
 *     },
 *     ...
 *   ],
 *   warnings: []
 * }
 */
export const listBuiltinRoutines = () =>
  api.get(`${SCHEDULER_API_PREFIX}/patterns/builtin`, { timeout: API_TIMEOUT_MS })

/**
 * Validate event pattern
 *
 * @param {Object} data - Event pattern data to validate
 * @param {string} data.name - Event name
 * @param {string} data.action - Event action
 * @param {Object} data.trigger - Trigger configuration
 * @returns {Promise<Object>} Axios response with validation results
 *
 * Response: {
 *   valid: true,
 *   errors: [],
 *   warnings: []
 * }
 */
export const validateRoutine = (data) =>
  api.post(`${SCHEDULER_API_PREFIX}/patterns/validate`, data, { timeout: API_TIMEOUT_MS })
