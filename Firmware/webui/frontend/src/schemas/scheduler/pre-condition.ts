import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  TIME_FORMAT_REGEX,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for the optional time window nested inside a pre-condition.
 * Simple HH:MM-only times (no solar events, no offsets).
 * Cross-field: start_time !== end_time.
 */
export const preConditionTimeWindowSchema = z
  .object({
    start_time: z
      .string({ error: 'Start time is required' })
      .regex(TIME_FORMAT_REGEX, 'Time must be in HH:MM format'),
    end_time: z
      .string({ error: 'End time is required' })
      .regex(TIME_FORMAT_REGEX, 'Time must be in HH:MM format'),
  })
  .refine((data) => data.start_time !== data.end_time, {
    message: 'Start and end times cannot be the same',
    path: ['end_time'],
  })

/**
 * Schema for fields owned by PreConditionForm.
 * The enable/disable toggle is component-level state, not validated here.
 */
export const preConditionSchema = z.object({
  sensor_type: z.enum(['light', 'temperature'], {
    error: 'Invalid sensor type',
  }),
  comparison: z.enum(['lt', 'gt', 'eq'], {
    error: 'Invalid comparison operator',
  }),
  threshold: z
    .number({ error: 'Threshold must be a number' })
    .min(0, 'Threshold must be non-negative'),
  cooldown_minutes: z
    .number({ error: 'Cooldown must be a number' })
    .min(
      SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES,
      `Cooldown must be at least ${SCHEDULE_LIMITS.MIN_COOLDOWN_MINUTES} minutes`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      `Cooldown cannot exceed ${SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES} minutes`,
    ),
  time_window: preConditionTimeWindowSchema.nullable().default(null),
})

export type PreConditionFormData = z.infer<typeof preConditionSchema>
