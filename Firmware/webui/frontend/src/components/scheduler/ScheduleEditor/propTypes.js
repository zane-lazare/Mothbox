/**
 * Shared PropTypes for Schedule Editor Components (Issue #262)
 *
 * This module provides centralized PropTypes definitions for the ScheduleEditor
 * component family, eliminating duplication and ensuring consistency across:
 * - ScheduleEditor
 * - RoutineList, RoutineCard, NewRoutineCard
 * - TriggerForm, TriggerSelector
 * - PreviewSection
 *
 * @module components/scheduler/ScheduleEditor/propTypes
 */

import PropTypes from 'prop-types';

/**
 * PropTypes shape for time window configuration.
 * Used in interval triggers to define when executions can occur.
 *
 * @example
 * {
 *   start_time: '21:00',
 *   end_time: '05:00',
 *   start_offset_minutes: 30,
 *   end_offset_minutes: 0
 * }
 */
export const TimeWindowPropType = PropTypes.shape({
  start_time: PropTypes.string,
  end_time: PropTypes.string,
  start_offset_minutes: PropTypes.number,
  end_offset_minutes: PropTypes.number,
});

/**
 * PropTypes shape for time window validation errors.
 * Used within TriggerErrorsPropType for time window field errors.
 */
export const TimeWindowErrorsPropType = PropTypes.shape({
  start_time: PropTypes.string,
  end_time: PropTypes.string,
  general: PropTypes.string,
});

/**
 * PropTypes shape for trigger validation errors.
 * Each field corresponds to a potential error message for that trigger field.
 */
export const TriggerErrorsPropType = PropTypes.shape({
  trigger_type: PropTypes.string,
  interval_minutes: PropTypes.string,
  time_window: TimeWindowErrorsPropType,
  solar_event: PropTypes.string,
  offset_minutes: PropTypes.string,
  moon_phase: PropTypes.string,
  time_of_day: PropTypes.string,
  offset_days: PropTypes.string,
  sensor_type: PropTypes.string,
  comparison: PropTypes.string,
  threshold: PropTypes.string,
  cooldown_minutes: PropTypes.string,
  days_of_week: PropTypes.string,
});

/**
 * PropTypes shape for trigger configuration.
 * Supports all trigger types: interval, solar, moon_phase, fixed_time, sensor,
 * recurring_days, and cron.
 *
 * @example
 * // Interval trigger
 * {
 *   trigger_type: 'interval',
 *   interval_minutes: 60,
 *   time_window: { start_time: '21:00', end_time: '05:00' },
 *   days_of_week: [0, 1, 2, 3, 4]
 * }
 *
 * @example
 * // Solar trigger
 * {
 *   trigger_type: 'solar',
 *   solar_event: 'sunset',
 *   offset_minutes: 30
 * }
 *
 * @example
 * // Cron trigger
 * {
 *   trigger_type: 'cron',
 *   cron_expression: '0 20 * * *'
 * }
 */
export const TriggerPropType = PropTypes.shape({
  trigger_type: PropTypes.oneOf([
    'interval', 'solar', 'moon_phase', 'fixed_time',
    'sensor', 'recurring_days', 'cron'
  ]),
  // Interval trigger fields
  interval_minutes: PropTypes.number,
  time_window: TimeWindowPropType,
  // Solar trigger fields
  solar_event: PropTypes.string,
  offset_minutes: PropTypes.number,
  // Moon phase trigger fields
  moon_phase: PropTypes.string,
  phases: PropTypes.arrayOf(PropTypes.string),
  time_of_day: PropTypes.string,
  offset_days: PropTypes.number,
  // Fixed time trigger fields
  times: PropTypes.arrayOf(PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.shape({ id: PropTypes.string, value: PropTypes.string })
  ])),
  // Recurring days trigger fields
  days: PropTypes.arrayOf(PropTypes.number),
  time: PropTypes.string,
  // Cron trigger fields
  cron_expression: PropTypes.string,
  // Sensor trigger fields
  sensor_type: PropTypes.string,
  comparison: PropTypes.string,
  threshold: PropTypes.number,
  cooldown_minutes: PropTypes.number,
  // Common fields
  days_of_week: PropTypes.arrayOf(PropTypes.number),
});

/**
 * PropTypes shape for an action within a pattern.
 *
 * @example
 * {
 *   action_id: 'abc-123',
 *   type: 'gpio',
 *   parameters: { pin: 'attract_on' }
 * }
 */
export const ActionPropType = PropTypes.shape({
  action_id: PropTypes.string,
  type: PropTypes.string.isRequired,
  parameters: PropTypes.object,
});

/**
 * PropTypes shape for an event pattern.
 * Patterns define reusable sequences of actions.
 *
 * @example
 * {
 *   pattern_id: 'pattern-123',
 *   name: 'UV Capture Cycle',
 *   description: 'Turn on UV, capture photo, turn off UV',
 *   actions: [
 *     { action_id: '1', type: 'gpio', parameters: { pin: 'uv_on' } },
 *     { action_id: '2', type: 'camera', parameters: {} },
 *     { action_id: '3', type: 'gpio', parameters: { pin: 'uv_off' } }
 *   ],
 *   category: 'user',
 *   tags: ['uv', 'capture']
 * }
 */
export const PatternPropType = PropTypes.shape({
  pattern_id: PropTypes.string,
  name: PropTypes.string.isRequired,
  description: PropTypes.string,
  actions: PropTypes.arrayOf(ActionPropType).isRequired,
  category: PropTypes.string,
  tags: PropTypes.arrayOf(PropTypes.string),
});

/**
 * PropTypes shape for date range configuration.
 * Used to define schedule validity period.
 *
 * @example
 * {
 *   start_date: '2024-06-01',
 *   end_date: '2024-08-31'
 * }
 */
export const DateRangePropType = PropTypes.shape({
  start_date: PropTypes.string,
  end_date: PropTypes.string,
});

/**
 * PropTypes shape for pattern selection in EventPatternSelector.
 * Indicates whether pattern comes from library or is custom-defined.
 *
 * @example
 * {
 *   source: 'library',
 *   pattern: { pattern_id: '123', name: 'UV Cycle', ... }
 * }
 */
export const PatternSelectionPropType = PropTypes.shape({
  source: PropTypes.oneOf(['library', 'custom']),
  pattern: PatternPropType,
});

/**
 * PropTypes shape for a complete schedule.
 * Used by ScheduleEditor for the main schedule prop.
 *
 * @example
 * {
 *   schedule_id: 'sched-123',
 *   name: 'Summer Moth Survey',
 *   description: 'Nightly moth capture from June to August',
 *   trigger: { trigger_type: 'solar', ... },
 *   event_patterns: [{ pattern_id: '1', name: 'UV Cycle', ... }],
 *   date_range: { start_date: '2024-06-01', end_date: '2024-08-31' }
 * }
 */
export const SchedulePropType = PropTypes.shape({
  schedule_id: PropTypes.string,
  name: PropTypes.string,
  description: PropTypes.string,
  trigger: TriggerPropType,
  event_patterns: PropTypes.arrayOf(PatternPropType),
  date_range: DateRangePropType,
});

/**
 * PropTypes shape for an action within a routine.
 * Note: This differs from ActionPropType which is for pattern actions.
 *
 * @example
 * {
 *   id: 'action-1',
 *   action_type: 'gpio',
 *   action_name: 'attract_on',
 *   offset_minutes: 5
 * }
 */
export const RoutineActionPropType = PropTypes.shape({
  id: PropTypes.string,
  action_type: PropTypes.string,
  action_name: PropTypes.string,
  offset_minutes: PropTypes.number,
});

/**
 * PropTypes shape for a routine configuration.
 * Routines combine a trigger with a sequence of actions.
 *
 * @example
 * {
 *   routine_id: 'routine-123',
 *   name: 'Nightly Photo Capture',
 *   trigger: { trigger_type: 'solar', solar_event: 'sunset' },
 *   actions: [
 *     { id: '1', action_type: 'gpio', action_name: 'attract_on' },
 *     { id: '2', action_type: 'camera', action_name: 'takephoto' }
 *   ]
 * }
 */
export const RoutinePropType = PropTypes.shape({
  routine_id: PropTypes.string,
  name: PropTypes.string,
  trigger: TriggerPropType,
  actions: PropTypes.arrayOf(RoutineActionPropType),
});
