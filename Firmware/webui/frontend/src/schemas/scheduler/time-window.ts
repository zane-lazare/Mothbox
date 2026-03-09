import { z } from 'zod'
import {
  SOLAR_EVENTS,
  TIME_FORMAT_REGEX,
  type SolarEventValue,
} from '../../components/scheduler/ScheduleEditor/constants'
import { REQUIRED, TYPE, RANGE, FORMAT } from '../../constants/errorMessages'

/**
 * Schema for fields owned by TimeWindowInput:
 * start_time + end_time + start_offset_minutes + end_offset_minutes.
 *
 * Each time field accepts either HH:MM format or a valid solar event string.
 * No cross-field validation — mixed time warning is UI-only.
 */

const TIME_WINDOW_MAX_OFFSET_MINUTES = 120

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  SolarEventValue,
  ...SolarEventValue[],
]

const timeValue = z
  .string({ error: REQUIRED.field('Time') })
  .refine(
    (v) =>
      TIME_FORMAT_REGEX.test(v) ||
      solarEventValues.includes(v as SolarEventValue),
    FORMAT.timeOrSolar,
  )

export const timeWindowSchema = z.object({
  start_time: timeValue,
  end_time: timeValue,
  start_offset_minutes: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.min(-TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.max(TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .default(0),
  end_offset_minutes: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.min(-TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .max(
      TIME_WINDOW_MAX_OFFSET_MINUTES,
      RANGE.max(TIME_WINDOW_MAX_OFFSET_MINUTES, 'minutes'),
    )
    .default(0),
})

export type TimeWindowFormData = z.infer<typeof timeWindowSchema>
