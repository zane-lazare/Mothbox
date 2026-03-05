import { z } from 'zod'
import {
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
  SCHEDULE_LIMITS,
} from '../../components/scheduler/ScheduleEditor/constants'

/**
 * Schema for fields owned by SensorTriggerForm:
 * sensor_type + comparison + threshold + cooldown_minutes.
 */

// z.enum requires a non-empty tuple — guard against empty constants
const sensorTypeValues = SENSOR_TYPES.map((s) => s.value) as [string, ...string[]]
if (sensorTypeValues.length === 0) throw new Error('SENSOR_TYPES must not be empty')
const comparisonValues = SENSOR_COMPARISONS.map((c) => c.value) as [string, ...string[]]
if (comparisonValues.length === 0) throw new Error('SENSOR_COMPARISONS must not be empty')

export const sensorTriggerSchema = z.object({
  sensor_type: z.enum(sensorTypeValues, { error: 'Invalid sensor type' }),
  comparison: z.enum(comparisonValues, { error: 'Invalid comparison operator' }),
  threshold: z
    .number({ error: 'Threshold must be a number' })
    .min(0, 'Threshold must be 0 or greater'),
  cooldown_minutes: z
    .number({ error: 'Cooldown must be a number' })
    .int('Cooldown must be a whole number')
    .min(1, 'Cooldown must be at least 1 minute')
    .max(
      SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      `Cooldown cannot exceed ${SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES} minutes`,
    ),
})

export type SensorTriggerFormData = z.infer<typeof sensorTriggerSchema>
