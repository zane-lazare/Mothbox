/**
 * React Query hooks for Schedule Pattern operations (Issue #223)
 *
 * Provides utility hooks for Schedule Pattern configuration:
 * - Trigger-specific helpers (interval, solar, moon phase)
 * - Schedule template operations
 * - Human-readable descriptions
 *
 * Core CRUD operations are re-exported from useSchedules.js for convenience.
 *
 * Naming Convention:
 * - Query hooks: use<Resource> (e.g., useSchedules)
 * - Mutation hooks: use<Action><Resource> (e.g., useDuplicateSchedule)
 * - Utility hooks: use<Utility> (e.g., useTriggerDescription)
 */

import { useMemo } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { QUERY_KEYS } from '../utils/queryKeys'
import {
  getSchedule,
  createSchedule,
  updateSchedule,
  deleteSchedule,
} from '../utils/schedulerApi'

// =============================================================================
// Re-exports from useSchedules.js
// =============================================================================
// Core CRUD operations are re-exported for convenience, allowing consumers
// to import all schedule-related hooks from a single file

export {
  useSchedules,
  useSchedule,
  useActiveSchedule,
  useSchedulePreview,
  useBuiltinSchedules,
  useCreateSchedule,
  useUpdateSchedule,
  useDeleteSchedule,
  useActivateSchedule,
  useDeactivateSchedule,
  useValidateSchedule,
} from './useSchedules'

// =============================================================================
// Configuration
// =============================================================================

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
    console.error(`[SchedulePattern ${operation}]:`, error.message || error)
  }
}

// =============================================================================
// Utility Hooks
// =============================================================================

/**
 * Generate human-readable trigger description
 *
 * Returns a descriptive string for a schedule's trigger configuration.
 * Useful for displaying trigger information in UI lists and detail views.
 *
 * @param {Object|null} schedule - Schedule object
 * @param {Array} [schedule.events] - Array of event objects
 * @returns {string} Human-readable trigger description
 *
 * @example
 * const schedule = {
 *   events: [{
 *     trigger: { type: 'interval', interval_minutes: 60, time_window: { start_time: '21:00', end_time: '05:00' } }
 *   }]
 * }
 * const description = useTriggerDescription(schedule)
 * // "Every 60 minutes from 21:00 to 05:00"
 *
 * @example
 * const schedule = {
 *   events: [{
 *     trigger: { type: 'solar', solar_event: 'sunset', offset_minutes: 30 }
 *   }]
 * }
 * const description = useTriggerDescription(schedule)
 * // "At sunset + 30 minutes"
 *
 * @example
 * const schedule = {
 *   events: [{
 *     trigger: { type: 'moon_phase', phases: ['full'], offset_days: 2 }
 *   }]
 * }
 * const description = useTriggerDescription(schedule)
 * // "On full moon ±2 days"
 */
export function useTriggerDescription(schedule) {
  return useMemo(() => {
    if (!schedule?.events?.length) return 'Unknown trigger'

    const trigger = schedule.events[0]?.trigger
    if (!trigger?.type) return 'Unknown trigger'

    switch (trigger.type) {
      case 'interval': {
        const minutes = trigger.interval_minutes ?? 60
        const window = trigger.time_window
        if (window?.start_time && window?.end_time) {
          return `Every ${minutes} minutes from ${window.start_time} to ${window.end_time}`
        }
        return `Every ${minutes} minutes`
      }

      case 'solar': {
        const event = trigger.solar_event ?? 'sunset'
        const offset = trigger.offset_minutes ?? 0
        if (offset === 0) {
          return `At ${event}`
        }
        const sign = offset > 0 ? '+' : ''
        return `At ${event} ${sign}${offset} minutes`
      }

      case 'moon_phase': {
        const phases = trigger.phases ?? ['full']
        const offset = trigger.offset_days ?? 0
        const phaseStr = phases.join(', ')
        if (offset === 0) {
          return `On ${phaseStr} moon`
        }
        return `On ${phaseStr} moon ±${Math.abs(offset)} days`
      }

      case 'fixed_time': {
        const time = trigger.time ?? '21:00'
        const days = trigger.days_of_week
        if (days && days.length > 0 && days.length < 7) {
          const dayNames = days.map(d => ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][d]).join(', ')
          return `At ${time} on ${dayNames}`
        }
        return `At ${time} daily`
      }

      case 'sensor': {
        const sensor = trigger.sensor_type ?? 'unknown'
        const condition = trigger.condition ?? 'threshold'
        return `When ${sensor} ${condition}`
      }

      default:
        return 'Unknown trigger'
    }
  }, [schedule])
}

/**
 * Get default configuration for interval triggers
 *
 * Returns a memoized default configuration object for interval-based triggers.
 * Use this when creating new interval triggers to ensure consistent defaults.
 *
 * @returns {Object} Default interval trigger configuration
 *
 * @example
 * const defaults = useIntervalTriggerDefaults()
 * const newTrigger = {
 *   type: 'interval',
 *   ...defaults
 * }
 * // { type: 'interval', interval_minutes: 60, time_window: { start_time: '21:00', end_time: '05:00' } }
 */
export function useIntervalTriggerDefaults() {
  return useMemo(() => ({
    interval_minutes: 60,
    time_window: {
      start_time: '21:00',
      end_time: '05:00',
    },
  }), [])
}

/**
 * Get default configuration for solar triggers
 *
 * Returns a memoized default configuration object for solar-based triggers.
 * Use this when creating new solar triggers to ensure consistent defaults.
 *
 * @returns {Object} Default solar trigger configuration
 *
 * @example
 * const defaults = useSolarTriggerDefaults()
 * const newTrigger = {
 *   type: 'solar',
 *   ...defaults
 * }
 * // { type: 'solar', solar_event: 'sunset', offset_minutes: 30, days_of_week: null }
 */
export function useSolarTriggerDefaults() {
  return useMemo(() => ({
    solar_event: 'sunset',
    offset_minutes: 30,
    days_of_week: null,
  }), [])
}

/**
 * Get default configuration for moon phase triggers
 *
 * Returns a memoized default configuration object for moon phase triggers.
 * Use this when creating new moon phase triggers to ensure consistent defaults.
 *
 * @returns {Object} Default moon phase trigger configuration
 *
 * @example
 * const defaults = useMoonPhaseTriggerDefaults()
 * const newTrigger = {
 *   type: 'moon_phase',
 *   ...defaults
 * }
 * // { type: 'moon_phase', phases: ['full'], offset_days: 0, time_window: null }
 */
export function useMoonPhaseTriggerDefaults() {
  return useMemo(() => ({
    phases: ['full'],
    offset_days: 0,
    time_window: null,
  }), [])
}

// =============================================================================
// Composite Hooks
// =============================================================================

/**
 * Combined schedule pattern operations
 *
 * Returns combined mutation hooks with aggregate state for all schedule
 * pattern operations. Useful for UIs that need to track loading state
 * across multiple operations.
 *
 * @returns {Object} Combined operations and state
 * @returns {Object} create - Create schedule mutation object
 * @returns {Object} update - Update schedule mutation object
 * @returns {Object} delete - Delete schedule mutation object
 * @returns {boolean} isPending - True if any mutation is in progress
 * @returns {Array} errors - Array of errors from failed mutations
 *
 * @example
 * const { create, update, delete: deleteOp, isPending, errors } = useSchedulePatternOperations()
 *
 * const handleCreate = () => {
 *   create.mutate({
 *     name: 'Evening Moths',
 *     events: [...]
 *   })
 * }
 *
 * return (
 *   <div>
 *     {isPending && <Spinner />}
 *     {errors.length > 0 && <ErrorList errors={errors} />}
 *     <Button onClick={handleCreate} disabled={isPending}>Create</Button>
 *   </div>
 * )
 */
export function useSchedulePatternOperations() {
  const queryClient = useQueryClient()

  const create = useMutation({
    mutationFn: (data) => createSchedule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES })
    },
    onError: (error) => handleMutationError(error, 'create'),
  })

  const update = useMutation({
    mutationFn: ({ id, data }) => updateSchedule(id, data),
    onSuccess: async (_, { id }) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULE(id) }),
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES }),
      ])
    },
    onError: (error) => handleMutationError(error, 'update'),
  })

  const deleteOp = useMutation({
    mutationFn: (id) => deleteSchedule(id),
    onSuccess: async (_, id) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULE(id) }),
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES }),
      ])
    },
    onError: (error) => handleMutationError(error, 'delete'),
  })

  const isPending = create.isPending || update.isPending || deleteOp.isPending

  const errors = [
    create.error,
    update.error,
    deleteOp.error,
  ].filter(Boolean)

  return {
    create,
    update,
    delete: deleteOp,
    isPending,
    errors,
  }
}

/**
 * Duplicate an existing schedule
 *
 * Creates a copy of an existing schedule with a new name. This is useful
 * for creating variations of schedules without starting from scratch.
 *
 * Workflow:
 * 1. Fetch source schedule by ID
 * 2. Create new schedule with modified name
 * 3. Invalidate schedules cache
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function with { sourceId, newName } parameter
 * @returns {Function} mutateAsync - Async mutation function
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useDuplicateSchedule()
 *
 * const handleDuplicate = (sourceId) => {
 *   mutate({
 *     sourceId,
 *     newName: 'Copy of Evening Moths'
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Duplicated:', response.data.id)
 *     },
 *     onError: (error) => {
 *       console.error('Failed to duplicate:', error.message)
 *     }
 *   })
 * }
 */
export function useDuplicateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ sourceId, newName }) => {
      // Fetch source schedule
      const response = await getSchedule(sourceId)
      const sourceSchedule = response.data

      // Create copy with new name and removed ID
      const { id: _id, schedule_id: _scheduleId, created_at: _createdAt, modified_at: _modifiedAt, ...scheduleData } = sourceSchedule
      const newSchedule = {
        ...scheduleData,
        name: newName,
      }

      // Create new schedule
      return createSchedule(newSchedule)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES })
    },
    onError: (error) => handleMutationError(error, 'duplicate'),
  })
}

/**
 * Create schedule from built-in template
 *
 * Creates a new user schedule based on a built-in schedule template.
 * Allows customization of the template before creating the new schedule.
 *
 * Workflow:
 * 1. Fetch built-in schedule by ID
 * 2. Apply customizations (name, description, events, etc.)
 * 3. Create new user schedule
 * 4. Invalidate schedules cache
 *
 * @returns {Object} React Query mutation result
 * @returns {Function} mutate - Mutation function with { templateId, customizations } parameter
 * @returns {Function} mutateAsync - Async mutation function
 * @returns {boolean} isPending - Whether mutation is in progress
 * @returns {boolean} isError - Whether mutation failed
 * @returns {Object} error - Error object if mutation failed
 * @returns {Object} data - Response data on success
 *
 * @example
 * const { mutate, isPending } = useScheduleFromTemplate()
 *
 * const handleCreateFromTemplate = () => {
 *   mutate({
 *     templateId: 'sunset_moths',
 *     customizations: {
 *       name: 'My Sunset Moths',
 *       description: 'Modified sunset schedule',
 *       events: [
 *         // Optionally override events
 *       ]
 *     }
 *   }, {
 *     onSuccess: (response) => {
 *       console.log('Created from template:', response.data.id)
 *     }
 *   })
 * }
 */
export function useScheduleFromTemplate() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ templateId, customizations }) => {
      // Fetch built-in schedule template
      const response = await getSchedule(templateId)
      const template = response.data

      // Remove read-only fields and apply customizations
      const { id: _id, schedule_id: _scheduleId, created_at: _createdAt, modified_at: _modifiedAt, category: _category, ...templateData } = template
      const newSchedule = {
        ...templateData,
        ...customizations,
      }

      // Create new user schedule
      return createSchedule(newSchedule)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SCHEDULES })
    },
    onError: (error) => handleMutationError(error, 'fromTemplate'),
  })
}

export default useTriggerDescription
