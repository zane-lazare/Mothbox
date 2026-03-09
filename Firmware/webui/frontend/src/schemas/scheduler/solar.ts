import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  SOLAR_EVENTS,
  type SolarEventValue,
} from '../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE, SCHEDULER } from '../../constants/errorMessages'

/**
 * Schema for fields owned by SolarTriggerForm: solar_event + offset_minutes.
 *
 * DaysOfWeekSelector has its own schema (future migration) and is
 * pass-through here.
 */

const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  SolarEventValue,
  ...SolarEventValue[],
]

export const solarTriggerSchema = z.object({
  solar_event: z.enum(solarEventValues, {
    error: SCHEDULER.invalidSolarEvent,
  }),
  offset_minutes: z
    .number({ error: TYPE.number('Offset') })
    .int(TYPE.integer('Offset'))
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      RANGE.min(-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES, 'minutes'),
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      RANGE.max(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES, 'minutes'),
    ),
})

export type SolarTriggerFormData = z.infer<typeof solarTriggerSchema>
