import { z } from 'zod'
import {
  SCHEDULE_LIMITS,
  MOON_PHASES,
  type MoonPhaseValue,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by MoonPhaseTriggerForm:
 * moon_phase + time_of_day + offset_days.
 */

const moonPhaseValues = MOON_PHASES.map((p) => p.value) as [
  MoonPhaseValue,
  ...MoonPhaseValue[],
]

export const moonPhaseTriggerSchema = z.object({
  moon_phase: z.enum(moonPhaseValues, {
    error: 'Invalid moon phase',
  }),
  time_of_day: z
    .string({ error: 'Time is required' })
    .regex(/^([01]\d|2[0-3]):[0-5]\d$/, 'Time must be in HH:MM format'),
  offset_days: z
    .number({ error: 'Offset must be a number' })
    .int('Offset must be a whole number')
    .min(
      -SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      `Offset must be at least ${-SCHEDULE_LIMITS.MAX_OFFSET_DAYS} days`,
    )
    .max(
      SCHEDULE_LIMITS.MAX_OFFSET_DAYS,
      `Offset cannot exceed ${SCHEDULE_LIMITS.MAX_OFFSET_DAYS} days`,
    ),
})

export type MoonPhaseTriggerFormData = z.infer<typeof moonPhaseTriggerSchema>
