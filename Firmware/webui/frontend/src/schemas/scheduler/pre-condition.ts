import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  TIME_FORMAT_REGEX,
} from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT, SCHEDULER } from '../../constants/errorMessages'

/** Cross-field error when start and end times match. */
export const TIME_WINDOW_SAME_ERROR = SCHEDULER.sameStartEnd

/** Sensor types allowed in pre-conditions (excludes motion per issue #325) */
export const ALLOWED_SENSOR_TYPES = ['light', 'temperature'] as const

/**
 * Schema for the optional time window nested inside a pre-condition.
 * Simple HH:MM-only times (no solar events, no offsets).
 * Cross-field: start_time !== end_time.
 */
export const preConditionTimeWindowSchema = z
  .object({
    start_time: z
      .string({ error: REQUIRED.field('Start time') })
      .regex(TIME_FORMAT_REGEX, FORMAT.timeRequired),
    end_time: z
      .string({ error: REQUIRED.field('End time') })
      .regex(TIME_FORMAT_REGEX, FORMAT.timeRequired),
  })
  // This condition is also derived inline in PreConditionForm.tsx (timeWindowError)
  // because RHF mode:'onChange' does not run the resolver on mount.
  // If this condition changes, update both locations.
  .refine((data) => data.start_time !== data.end_time, {
    message: TIME_WINDOW_SAME_ERROR,
    path: ['end_time'],
  })

/**
 * Schema for fields owned by PreConditionForm.
 * The enable/disable toggle is component-level state, not validated here.
 */
export const preConditionSchema = z.object({
  sensor_type: z.enum(ALLOWED_SENSOR_TYPES, {
    error: SCHEDULER.invalidSensorType,
  }),
  comparison: z.enum(['lt', 'gt', 'eq'], {
    error: SCHEDULER.invalidComparison,
  }),
  threshold: z
    .number({ error: TYPE.number('Threshold') })
    .min(0, 'Threshold must be non-negative'),
  cooldown_minutes: z
    .number({ error: TYPE.number('Cooldown') })
    .min(
      SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES,
      RANGE.min(SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES, 'minutes'),
    )
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, 'minutes'),
    ),
  time_window: preConditionTimeWindowSchema.nullable().default(null),
})

export type PreConditionFormData = z.infer<typeof preConditionSchema>
