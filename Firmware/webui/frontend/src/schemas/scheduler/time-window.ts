import { z } from 'zod'
import {
  SOLAR_EVENTS,
  TIME_FORMAT_REGEX,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by TimeWindowInput:
 * start_time + end_time + start_offset_minutes + end_offset_minutes.
 *
 * Each time field accepts either HH:MM format or a valid solar event string.
 * No cross-field validation — mixed time warning is UI-only.
 */

const TIME_WINDOW_MAX_OFFSET_MINUTES = 120

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  string,
  ...string[],
]

const timeValue = z
  .string({ error: 'Time is required' })
  .refine(
    (v) => TIME_FORMAT_REGEX.test(v) || solarEventValues.includes(v),
    'Must be valid HH:MM time or solar event',
  )

export const timeWindowSchema = z.object({
  start_time: timeValue,
  end_time: timeValue,
  start_offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset must be at least ${-TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .default(0),
  end_offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset must be at least ${-TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${TIME_WINDOW_MAX_OFFSET_MINUTES} minutes`,
    )
    .default(0),
})

export type TimeWindowFormData = z.infer<typeof timeWindowSchema>
