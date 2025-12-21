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
 */

import { api } from './api'

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
export const listSchedules = (params = {}) => api.get('/scheduler/ui/schedules', { params })

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
export const getSchedule = (id) => api.get(`/scheduler/ui/schedules/${id}`)

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
export const createSchedule = (data) => api.post('/scheduler/ui/schedules', data)

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
export const updateSchedule = (id, data) => api.put(`/scheduler/ui/schedules/${id}`, data)

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
export const deleteSchedule = (id) => api.delete(`/scheduler/ui/schedules/${id}`)

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
export const getActiveSchedule = () => api.get('/scheduler/ui/schedules/active')

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
  api.post(`/scheduler/ui/schedules/${id}/activate`, options)

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
export const deactivateSchedule = () => api.post('/scheduler/ui/schedules/deactivate')

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
  api.get(`/scheduler/ui/schedules/${id}/preview`, { params })

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
  api.post(`/scheduler/ui/schedules/${id}/validate`, data)

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
 *       id: "sunset_moths",
 *       name: "Sunset Moths",
 *       description: "Capture moths at dusk",
 *       category: "builtin",
 *       ...
 *     },
 *     ...
 *   ],
 *   total: 3
 * }
 */
export const listBuiltinSchedules = () => api.get('/scheduler/ui/schedules/builtin')

/**
 * List built-in event patterns
 *
 * @returns {Promise<Object>} Axios response with built-in patterns
 *
 * Response: {
 *   patterns: [
 *     {
 *       id: "hourly_interval",
 *       name: "Hourly Interval",
 *       description: "Take photos every hour",
 *       category: "builtin",
 *       events: [...],
 *       ...
 *     },
 *     ...
 *   ],
 *   total: 5
 * }
 */
export const listBuiltinPatterns = () => api.get('/scheduler/ui/patterns/builtin')

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
export const validatePattern = (data) => api.post('/scheduler/ui/patterns/validate', data)
