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
import type { AxiosResponse } from 'axios'

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
// Types
// =============================================================================

/**
 * Schedule category
 */
export type ScheduleCategory = 'user' | 'built-in'

/**
 * Trigger types
 */
export type TriggerType = 'solar' | 'interval' | 'fixed' | 'moon' | 'sensor' | 'cron' | 'recurring_days'

/**
 * Solar events
 */
export type SolarEvent = 'sunrise' | 'sunset' | 'dawn' | 'dusk'

/**
 * Action types
 */
export type ActionType = 'take_photo' | 'attract_on' | 'attract_off' | 'flash_on' | 'flash_off' | 'gps_sync' | 'service'

/**
 * Trigger configuration (solar)
 */
export interface SolarTrigger {
  type: 'solar'
  solar_event: SolarEvent
  offset_minutes?: number
}

/**
 * Trigger configuration (interval)
 */
export interface IntervalTrigger {
  type: 'interval'
  interval_minutes: number
  start_time?: string
  end_time?: string
}

/**
 * Trigger configuration (fixed time)
 */
export interface FixedTrigger {
  type: 'fixed'
  time: string
  days?: string[]
}

/**
 * Trigger configuration (cron)
 */
export interface CronTrigger {
  type: 'cron'
  expression: string
}

/**
 * Trigger configuration (recurring days)
 */
export interface RecurringDaysTrigger {
  type: 'recurring_days'
  time: string
  days: string[]
}

/**
 * Trigger configuration (union type)
 */
export type Trigger = SolarTrigger | IntervalTrigger | FixedTrigger | CronTrigger | RecurringDaysTrigger

/**
 * Event/routine definition
 */
export interface ScheduleEvent {
  name: string
  action: ActionType
  trigger: Trigger
  enabled?: boolean
  metadata?: Record<string, unknown>
}

/**
 * Schedule metadata
 */
export interface ScheduleMetadata {
  id: string
  name: string
  category: ScheduleCategory
  description?: string
  events: ScheduleEvent[]
  created_at?: string
  modified_at?: string
  metadata?: Record<string, unknown>
}

/**
 * Schedule creation data
 */
export interface ScheduleCreateData {
  name: string
  description?: string
  events: ScheduleEvent[]
  metadata?: Record<string, unknown>
}

/**
 * Schedule update data (partial)
 */
export interface ScheduleUpdateData {
  name?: string
  description?: string
  events?: ScheduleEvent[]
  metadata?: Record<string, unknown>
}

/**
 * Schedule list response
 */
export interface ScheduleListResponse {
  schedules: ScheduleMetadata[]
  total: number
}

/**
 * Schedule list params
 */
export interface ScheduleListParams {
  include_builtin?: boolean
}

/**
 * Schedule create/update response
 */
export interface ScheduleOperationResponse {
  id: string
  message: string
  schedule: ScheduleMetadata
}

/**
 * Schedule delete response
 */
export interface ScheduleDeleteResponse {
  message: string
  id: string
}

/**
 * Active schedule response
 */
export interface ActiveScheduleResponse {
  active_schedule: ScheduleMetadata | null
}

/**
 * Schedule activation options
 */
export interface ScheduleActivationOptions {
  create_deployment?: boolean
}

/**
 * Schedule activation response
 */
export interface ScheduleActivationResponse {
  message: string
  schedule_id: string
  deployment_created?: boolean
}

/**
 * Schedule deactivation response
 */
export interface ScheduleDeactivationResponse {
  message: string
  schedule_id: string
}

/**
 * Next action item
 */
export interface NextAction {
  time: string
  action_name: string
  action_type: ActionType
  routine_id: string
}

/**
 * Next actions response
 */
export interface NextActionsResponse {
  actions: NextAction[]
  schedule_id: string | null
  coordinates_source: 'gps' | 'timezone' | 'explicit' | null
  total_stored: number
}

/**
 * Next actions params
 */
export interface NextActionsParams {
  limit?: number
}

/**
 * Schedule execution preview
 */
export interface ScheduleExecution {
  event_name: string
  action: ActionType
  scheduled_time: string
  trigger_info?: Record<string, unknown>
}

/**
 * Schedule preview params
 */
export interface SchedulePreviewParams {
  days?: number
  lat?: number
  lon?: number
  tz?: string
}

/**
 * Schedule preview response
 */
export interface SchedulePreviewResponse {
  schedule_id: string
  preview_days: number
  executions: ScheduleExecution[]
  total: number
}

/**
 * Validation result
 */
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * Conflict information
 */
export interface ConflictInfo {
  type: string
  severity: 'blocking' | 'warning'
  message: string
  routines?: string[]
}

/**
 * Draft validation data
 */
export interface DraftValidationData {
  routines: ScheduleEvent[]
  days?: number
  latitude?: number
  longitude?: number
  timezone?: string
}

/**
 * Draft validation response
 */
export interface DraftValidationResponse {
  valid: boolean
  has_warnings: boolean
  conflicts: ConflictInfo[]
  total_conflicts: number
  blocking_conflicts: number
}

/**
 * Built-in schedule item
 */
export interface BuiltInSchedule {
  schedule_id: string
  name: string
  description?: string
  trigger_type: TriggerType
  enabled: boolean
  is_active: boolean
}

/**
 * Built-in schedules list response
 */
export interface BuiltInSchedulesResponse {
  schedules: BuiltInSchedule[]
  total: number
}

/**
 * Built-in pattern/routine
 */
export interface BuiltInPattern {
  pattern_id: string
  name: string
  description?: string
  category: 'built-in'
  actions: ScheduleEvent[]
  source_schedule?: string
  duration_minutes?: number
}

/**
 * Built-in patterns list response
 */
export interface BuiltInPatternsResponse {
  patterns: BuiltInPattern[]
  warnings: string[]
}

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
export const listSchedules = (params: ScheduleListParams = {}): Promise<AxiosResponse<ScheduleListResponse>> =>
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
export const getSchedule = (id: string): Promise<AxiosResponse<ScheduleMetadata>> =>
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
export const createSchedule = (data: ScheduleCreateData): Promise<AxiosResponse<ScheduleOperationResponse>> =>
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
export const updateSchedule = (id: string, data: ScheduleUpdateData): Promise<AxiosResponse<ScheduleOperationResponse>> =>
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
export const deleteSchedule = (id: string): Promise<AxiosResponse<ScheduleDeleteResponse>> =>
  api.delete(`${SCHEDULER_API_PREFIX}/schedules/${id}`, { timeout: API_TIMEOUT_MS })

/**
 * Clone an existing schedule
 *
 * @param {string} id - Schedule ID to clone
 * @param {Object} [data] - Clone options
 * @param {string} [data.name] - Custom name for the clone
 * @returns {Promise<Object>} Axios response with cloned schedule
 *
 * Response: {
 *   message: "Schedule cloned",
 *   schedule: { ... }
 * }
 */
export const cloneSchedule = (id: string, data: { name?: string } = {}): Promise<AxiosResponse<ScheduleOperationResponse>> =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules/${id}/clone`, data, { timeout: API_TIMEOUT_MS })

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
export const getActiveSchedule = (): Promise<AxiosResponse<ActiveScheduleResponse>> =>
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
export const activateSchedule = (id: string, options: ScheduleActivationOptions = {}): Promise<AxiosResponse<ScheduleActivationResponse>> =>
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
export const deactivateSchedule = (): Promise<AxiosResponse<ScheduleDeactivationResponse>> =>
  api.post(`${SCHEDULER_API_PREFIX}/schedules/deactivate`, {}, { timeout: API_TIMEOUT_MS })

/**
 * Get next actions for the active schedule
 *
 * Reads pre-expanded cron entries from persistent storage, avoiding
 * the need to recalculate solar times via the preview API.
 *
 * @param {Object} [params] - Query parameters
 * @param {number} [params.limit] - Maximum number of actions (default: 5, max: 100)
 * @returns {Promise<Object>} Axios response with next actions
 *
 * Response: {
 *   actions: [
 *     {
 *       time: "ISO 8601 datetime",
 *       action_name: "Attract On",
 *       action_type: "attract_on",
 *       routine_id: "routine-123"
 *     },
 *     ...
 *   ],
 *   schedule_id: "string" | null,
 *   coordinates_source: "gps" | "timezone" | "explicit" | null,
 *   total_stored: number
 * }
 *
 * Issue #331: Store cron entries in active_state.json
 */
export const getNextActions = (params: NextActionsParams = {}): Promise<AxiosResponse<NextActionsResponse>> =>
  api.get(`${SCHEDULER_API_PREFIX}/active/next-actions`, { params, timeout: API_TIMEOUT_MS })

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
export const getSchedulePreview = (id: string, params: SchedulePreviewParams = {}): Promise<AxiosResponse<SchedulePreviewResponse>> =>
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
export const validateSchedule = (id: string, data: ScheduleCreateData | ScheduleUpdateData): Promise<AxiosResponse<ValidationResult>> =>
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
export const validateDraftRoutines = (data: DraftValidationData): Promise<AxiosResponse<DraftValidationResponse>> =>
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
export const listBuiltinSchedules = (): Promise<AxiosResponse<BuiltInSchedulesResponse>> =>
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
export const listBuiltinRoutines = (): Promise<AxiosResponse<BuiltInPatternsResponse>> =>
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
export const validateRoutine = (data: ScheduleEvent): Promise<AxiosResponse<ValidationResult>> =>
  api.post(`${SCHEDULER_API_PREFIX}/patterns/validate`, data, { timeout: API_TIMEOUT_MS })
