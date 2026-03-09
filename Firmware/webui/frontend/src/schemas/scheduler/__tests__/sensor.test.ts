import { describe, it, expect } from 'vitest'
import { sensorTriggerSchema, type SensorTriggerFormData } from '../sensor'
import {
  SCHEDULE_LIMITS,
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
} from '../../../components/scheduler/ScheduleEditor/constants'
import { TYPE, RANGE, SCHEDULER } from '../../../constants/errorMessages'

/** Return the first Zod issue message from a failed parse, or null. */
function firstError(
  result: { success: boolean; error?: { issues: { message: string }[] } },
): string | null {
  if (result.success) return null
  return result.error?.issues[0]?.message ?? null
}

const VALID_INPUT = {
  sensor_type: 'motion',
  comparison: 'gt',
  threshold: 50,
  cooldown_minutes: 5,
}

describe('sensorTriggerSchema', () => {
  describe('valid values', () => {
    it('accepts valid sensor config (all fields valid)', () => {
      const result = sensorTriggerSchema.safeParse(VALID_INPUT)
      expect(result.success).toBe(true)
    })

    it('accepts all valid sensor types', () => {
      for (const sensor of SENSOR_TYPES) {
        const result = sensorTriggerSchema.safeParse({
          ...VALID_INPUT,
          sensor_type: sensor.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts all valid comparison operators', () => {
      for (const comp of SENSOR_COMPARISONS) {
        const result = sensorTriggerSchema.safeParse({
          ...VALID_INPUT,
          comparison: comp.value,
        })
        expect(result.success).toBe(true)
      }
    })

    it('accepts zero threshold', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        threshold: 0,
      })
      expect(result.success).toBe(true)
    })

    it('accepts cooldown at max', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES,
      })
      expect(result.success).toBe(true)
    })

    it('accepts cooldown at minimum (1)', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 1,
      })
      expect(result.success).toBe(true)
    })
  })

  describe('sensor_type rejection', () => {
    it('rejects invalid sensor_type', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 'invalid_sensor',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidSensorType)
    })

    it('rejects numeric sensor_type', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        sensor_type: 123,
      })
      expect(result.success).toBe(false)
    })

    it('rejects undefined sensor_type', () => {
      const { sensor_type: _, ...rest } = VALID_INPUT
      const result = sensorTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('comparison rejection', () => {
    it('rejects invalid comparison', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        comparison: 'invalid_op',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(SCHEDULER.invalidComparison)
    })

    it('rejects numeric comparison', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        comparison: 42,
      })
      expect(result.success).toBe(false)
    })

    it('rejects undefined comparison', () => {
      const { comparison: _, ...rest } = VALID_INPUT
      const result = sensorTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('threshold rejection', () => {
    it('rejects negative threshold', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        threshold: -1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe('Threshold must be 0 or greater')
    })

    it('rejects string threshold', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        threshold: '50',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Threshold'))
    })

    it('rejects undefined threshold', () => {
      const { threshold: _, ...rest } = VALID_INPUT
      const result = sensorTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('cooldown_minutes rejection', () => {
    it('rejects cooldown below 1', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 0,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(RANGE.min(1, 'minute'))
    })

    it('rejects cooldown exceeding MAX_COOLDOWN_MINUTES', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES + 1,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(
        RANGE.max(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES, 'minutes'),
      )
    })

    it('rejects non-integer cooldown', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: 5.5,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.integer('Cooldown'))
    })

    it('rejects string cooldown', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: '5',
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Cooldown'))
    })

    it('rejects NaN cooldown', () => {
      const result = sensorTriggerSchema.safeParse({
        ...VALID_INPUT,
        cooldown_minutes: NaN,
      })
      expect(result.success).toBe(false)
      expect(firstError(result)).toBe(TYPE.number('Cooldown'))
    })

    it('rejects undefined cooldown', () => {
      const { cooldown_minutes: _, ...rest } = VALID_INPUT
      const result = sensorTriggerSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })
  })

  describe('type inference', () => {
    it('inferred type matches expected shape', () => {
      const data: SensorTriggerFormData = {
        sensor_type: 'motion',
        comparison: 'gt',
        threshold: 50,
        cooldown_minutes: 5,
      }
      expect(data.sensor_type).toBe('motion')
      expect(data.comparison).toBe('gt')
      expect(data.threshold).toBe(50)
      expect(data.cooldown_minutes).toBe(5)
    })
  })
})
