/**
 * Shared TypeScript types for Schedule Editor Components (Issue #455)
 *
 * This module provides centralized TypeScript interfaces for the ScheduleEditor
 * component family, replacing the runtime PropTypes definitions in propTypes.js
 * with compile-time type checking.
 *
 * Used by:
 * - ScheduleEditor
 * - RoutineList, RoutineCard, NewRoutineCard
 * - TriggerForm, TriggerSelector
 * - MiniTimeline
 *
 * @module components/scheduler/ScheduleEditor/scheduler-types
 */

import type { SolarEventValue, MoonPhaseValue } from './constants'

// ---------------------------------------------------------------------------
// Time Window
// ---------------------------------------------------------------------------

/**
 * Time window configuration for interval triggers.
 * Defines when executions can occur within a day.
 *
 * @example
 * {
 *   start_time: '21:00',
 *   end_time: '05:00',
 *   start_offset_minutes: 30,
 *   end_offset_minutes: 0
 * }
 */
export interface TimeWindow {
  start_time: string
  end_time: string
  start_offset_minutes?: number
  end_offset_minutes?: number
}

/**
 * Validation errors for time window fields.
 */
export interface TimeWindowErrors {
  start_time?: string
  end_time?: string
  general?: string
}

// ---------------------------------------------------------------------------
// Trigger Types
// ---------------------------------------------------------------------------

/** Union of all supported trigger type identifiers. */
export type TriggerType =
  | 'interval'
  | 'solar'
  | 'moon_phase'
  | 'fixed_time'
  | 'sensor'
  | 'cron'
  | 'recurring_days'

/**
 * Base trigger fields shared by all trigger types.
 */
export interface BaseTrigger {
  trigger_type: TriggerType
  days_of_week?: number[] | null
}

/**
 * Interval trigger: fires at regular time intervals within an optional window.
 */
export interface IntervalTrigger extends BaseTrigger {
  trigger_type: 'interval'
  interval_minutes: number
  time_window?: TimeWindow | null
}

/**
 * Solar trigger: fires based on sun position events.
 */
export interface SolarTrigger extends BaseTrigger {
  trigger_type: 'solar'
  solar_event: SolarEventValue
  offset_minutes: number
}

/**
 * Moon phase trigger: fires on specific moon phases.
 */
export interface MoonPhaseTrigger extends BaseTrigger {
  trigger_type: 'moon_phase'
  moon_phase: MoonPhaseValue
  phases?: string[]
  time_of_day?: string
  offset_days?: number
}

/**
 * Fixed time trigger: fires at specific times of day.
 */
export interface FixedTimeTrigger extends BaseTrigger {
  trigger_type: 'fixed_time'
  time_of_day: string
  times?: string[]
}

/**
 * Sensor trigger: fires based on sensor readings exceeding a threshold.
 */
export interface SensorTrigger extends BaseTrigger {
  trigger_type: 'sensor'
  sensor_type: string
  comparison: string
  threshold: number
  cooldown_minutes: number
}

/**
 * Cron trigger: fires according to a standard 5-field cron expression.
 */
export interface CronTrigger extends BaseTrigger {
  trigger_type: 'cron'
  cron_expression: string
}

/**
 * Recurring days trigger: fires on specific days at a given time.
 */
export interface RecurringDaysTrigger extends BaseTrigger {
  trigger_type: 'recurring_days'
  days?: number[]
  time?: string
}

/**
 * Discriminated union of all trigger types.
 * The `trigger_type` field acts as the discriminant.
 */
export type Trigger =
  | IntervalTrigger
  | SolarTrigger
  | MoonPhaseTrigger
  | FixedTimeTrigger
  | SensorTrigger
  | CronTrigger
  | RecurringDaysTrigger

// ---------------------------------------------------------------------------
// Trigger Errors
// ---------------------------------------------------------------------------

/**
 * Validation errors for trigger fields.
 * Each key corresponds to a trigger field that may have an error message.
 */
export interface TriggerErrors {
  trigger_type?: string
  interval_minutes?: string
  time_window?: TimeWindowErrors
  solar_event?: string
  offset_minutes?: string
  moon_phase?: string
  time_of_day?: string
  offset_days?: string
  sensor_type?: string
  comparison?: string
  threshold?: string
  cooldown_minutes?: string
  days_of_week?: string
  cron_expression?: string
  phases?: string
  times?: string
  days?: string
  time?: string
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

/**
 * An action within a routine.
 *
 * @example
 * {
 *   id: 'action-1',
 *   action_type: 'gpio',
 *   action_name: 'attract_on',
 *   offset_minutes: 5
 * }
 */
export interface RoutineAction {
  id: string
  action_type: string
  action_name: string
  offset_minutes?: number
}

// ---------------------------------------------------------------------------
// Pre-Conditions
// ---------------------------------------------------------------------------

/**
 * Sensor pre-condition that gates routine execution.
 * The routine only executes when the sensor reading meets the condition.
 */
export interface PreCondition {
  trigger_type: string
  sensor_type: string
  comparison: string
  threshold: number
  cooldown_minutes: number
  time_window?: TimeWindow | null
}

// ---------------------------------------------------------------------------
// Routines
// ---------------------------------------------------------------------------

/**
 * A routine combines a trigger with a sequence of actions.
 *
 * @example
 * {
 *   routine_id: 'routine-123',
 *   name: 'Nightly Photo Capture',
 *   trigger: { trigger_type: 'solar', solar_event: 'sunset', offset_minutes: 0 },
 *   actions: [
 *     { id: '1', action_type: 'gpio', action_name: 'attract_on' },
 *     { id: '2', action_type: 'camera', action_name: 'takephoto' }
 *   ]
 * }
 */
export interface Routine {
  routine_id: string
  name?: string
  trigger: Trigger
  actions: RoutineAction[]
  pre_condition?: PreCondition | null
}

// ---------------------------------------------------------------------------
// Schedules
// ---------------------------------------------------------------------------

/**
 * A complete schedule (Schema 3.0).
 * Schedules use a routine-based model where each routine has its own trigger.
 *
 * @example
 * {
 *   schedule_id: 'sched-123',
 *   name: 'Overnight Moth Survey',
 *   description: 'UV lights at dusk, photos every 15 minutes',
 *   routines: [...],
 *   is_active: false,
 *   use_seconds_timing: false,
 *   created_at: '2024-01-01T00:00:00',
 *   updated_at: '2024-01-01T00:00:00'
 * }
 */
export interface Schedule {
  schedule_id: string
  name: string
  description: string
  routines: Routine[]
  is_active?: boolean
  is_builtin?: boolean
  use_seconds_timing?: boolean
  enabled?: boolean
  created_at?: string
  updated_at?: string
  modified_at?: string
}

// ---------------------------------------------------------------------------
// Conflict Report
// ---------------------------------------------------------------------------

/**
 * Result of schedule conflict detection.
 * Returned by the backend when validating or activating schedules.
 */
export interface ConflictReport {
  valid?: boolean
  has_warnings?: boolean
  has_blocking_conflicts?: boolean
  conflicts?: Array<{
    type: string
    message: string
    severity?: string
  }>
  total_conflicts?: number
  blocking_conflicts?: number
}
