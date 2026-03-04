import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  SOLAR_EVENTS,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by SolarTriggerForm: solar_event + offset_minutes.
 *
 * DaysOfWeekSelector has its own schema (future migration) and is
 * pass-through here.
 */

type SolarEventValue = (typeof SOLAR_EVENTS)[number]['value']
const solarEventValues = SOLAR_EVENTS.map((e) => e.value) as [
  SolarEventValue,
  ...SolarEventValue[],
]

export const solarTriggerSchema = z.object({
  solar_event: z.enum(solarEventValues, {
    error: 'Invalid solar event',
  }),
  offset_minutes: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      `Offset must be at least ${-SCHEDULE_LIMITS.MAX_OFFSET_MINUTES} minutes`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_MINUTES,
      `Offset cannot exceed ${SCHEDULE_LIMITS.MAX_OFFSET_MINUTES} minutes`,
    ),
})

export type SolarTriggerFormData = z.infer<typeof solarTriggerSchema>
