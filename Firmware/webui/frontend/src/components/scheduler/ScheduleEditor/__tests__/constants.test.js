/**
 * Tests for Schedule Editor constants
 * Verifies constants match backend schema in webui/backend/lib/schedule_schema.py
 */

import { describe, it, expect } from 'vitest'
import {
  SCHEDULE_LIMITS,
  TRIGGER_TYPES,
  SOLAR_EVENTS,
  MOON_PHASES,
  DAYS_OF_WEEK,
  SENSOR_TYPES,
  SENSOR_COMPARISONS,
  TRIGGER_DEFAULTS,
  TIME_FORMAT_REGEX,
  validateNumericInput,
  isValidSolarEvent,
} from '../constants'

describe('SCHEDULE_LIMITS', () => {
  it('should match backend schema validation limits', () => {
    expect(SCHEDULE_LIMITS.NAME_MAX_LENGTH).toBe(200)
    expect(SCHEDULE_LIMITS.DESCRIPTION_MAX_LENGTH).toBe(2000)
    expect(SCHEDULE_LIMITS.MAX_ACTIONS_PER_PATTERN).toBe(20)
    expect(SCHEDULE_LIMITS.MAX_PATTERNS_PER_SCHEDULE).toBe(10)
    expect(SCHEDULE_LIMITS.MAX_OFFSET_MINUTES).toBe(1440) // 24 hours
    expect(SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES).toBe(10080) // 7 days
    expect(SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES).toBe(1)
    expect(SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES).toBe(60)
    expect(SCHEDULE_LIMITS.MAX_OFFSET_DAYS).toBe(7)
  })

  it('should have all required limit fields', () => {
    const requiredFields = [
      'NAME_MAX_LENGTH',
      'DESCRIPTION_MAX_LENGTH',
      'MAX_ACTIONS_PER_PATTERN',
      'MAX_PATTERNS_PER_SCHEDULE',
      'MAX_OFFSET_MINUTES',
      'MAX_INTERVAL_MINUTES',
      'MIN_INTERVAL_MINUTES',
      'MAX_COOLDOWN_MINUTES',
      'MAX_OFFSET_DAYS',
    ]

    requiredFields.forEach((field) => {
      expect(SCHEDULE_LIMITS).toHaveProperty(field)
      expect(typeof SCHEDULE_LIMITS[field]).toBe('number')
      expect(SCHEDULE_LIMITS[field]).toBeGreaterThan(0)
    })
  })
})

describe('TRIGGER_TYPES', () => {
  it('should have all 6 trigger types from backend including cron for expert mode', () => {
    const expectedTypes = ['interval', 'solar', 'moon_phase', 'fixed_time', 'sensor', 'cron']
    const actualTypes = Object.keys(TRIGGER_TYPES)

    expect(actualTypes).toHaveLength(6)
    expect(actualTypes.sort()).toEqual(expectedTypes.sort())
  })

  it('should have required fields for each trigger type', () => {
    Object.entries(TRIGGER_TYPES).forEach(([key, config]) => {
      expect(config).toHaveProperty('value')
      expect(config).toHaveProperty('label')
      expect(config).toHaveProperty('icon')
      expect(config).toHaveProperty('description')

      expect(config.value).toBe(key)
      expect(typeof config.label).toBe('string')
      expect(typeof config.icon).toBe('string')
      expect(typeof config.description).toBe('string')
    })
  })

  it('should have valid icon names', () => {
    const validIcons = [
      'ClockIcon',
      'SunIcon',
      'MoonIcon',
      'BoltIcon',
      'CalendarIcon',
      'CodeBracketIcon',
    ]

    Object.values(TRIGGER_TYPES).forEach(({ icon }) => {
      expect(validIcons).toContain(icon)
    })
  })
})

describe('SOLAR_EVENTS', () => {
  it('should have all 15 solar events from backend', () => {
    expect(SOLAR_EVENTS).toHaveLength(15)
  })

  it('should match backend solar event values', () => {
    const expectedEvents = [
      'dawn',
      'sunrise',
      'noon',
      'sunset',
      'dusk',
      'civil_dawn',
      'civil_dusk',
      'nautical_dawn',
      'nautical_dusk',
      'astronomical_dawn',
      'astronomical_dusk',
      'golden_hour_start',
      'golden_hour_end',
      'blue_hour_start',
      'blue_hour_end',
    ]

    const actualEvents = SOLAR_EVENTS.map((event) => event.value)
    expect(actualEvents.sort()).toEqual(expectedEvents.sort())
  })

  it('should have required fields for each solar event', () => {
    SOLAR_EVENTS.forEach((event) => {
      expect(event).toHaveProperty('value')
      expect(event).toHaveProperty('label')
      expect(event).toHaveProperty('description')

      expect(typeof event.value).toBe('string')
      expect(typeof event.label).toBe('string')
      expect(typeof event.description).toBe('string')
      expect(event.label.length).toBeGreaterThan(0)
      expect(event.description.length).toBeGreaterThan(0)
    })
  })

  it('should be in chronological order throughout the day', () => {
    const expectedOrder = [
      'astronomical_dawn',
      'nautical_dawn',
      'civil_dawn',
      'blue_hour_start',
      'dawn',
      'sunrise',
      'golden_hour_start',
      'noon',
      'golden_hour_end',
      'sunset',
      'dusk',
      'blue_hour_end',
      'civil_dusk',
      'nautical_dusk',
      'astronomical_dusk',
    ]

    const actualOrder = SOLAR_EVENTS.map((event) => event.value)
    expect(actualOrder).toEqual(expectedOrder)
  })
})

describe('MOON_PHASES', () => {
  it('should have all 8 moon phases from backend', () => {
    expect(MOON_PHASES).toHaveLength(8)
  })

  it('should match backend moon phase values', () => {
    const expectedPhases = [
      'new',
      'waxing_crescent',
      'first_quarter',
      'waxing_gibbous',
      'full',
      'waning_gibbous',
      'last_quarter',
      'waning_crescent',
    ]

    const actualPhases = MOON_PHASES.map((phase) => phase.value)
    expect(actualPhases).toEqual(expectedPhases)
  })

  it('should have required fields for each moon phase', () => {
    MOON_PHASES.forEach((phase) => {
      expect(phase).toHaveProperty('value')
      expect(phase).toHaveProperty('label')

      expect(typeof phase.value).toBe('string')
      expect(typeof phase.label).toBe('string')
      expect(phase.label.length).toBeGreaterThan(0)
    })
  })

  it('should be in lunar cycle order', () => {
    const expectedOrder = [
      'new',
      'waxing_crescent',
      'first_quarter',
      'waxing_gibbous',
      'full',
      'waning_gibbous',
      'last_quarter',
      'waning_crescent',
    ]

    const actualOrder = MOON_PHASES.map((phase) => phase.value)
    expect(actualOrder).toEqual(expectedOrder)
  })
})

describe('DAYS_OF_WEEK', () => {
  it('should have all 7 days', () => {
    expect(DAYS_OF_WEEK).toHaveLength(7)
  })

  it('should follow ISO 8601 (0=Monday, 6=Sunday)', () => {
    expect(DAYS_OF_WEEK[0].value).toBe(0)
    expect(DAYS_OF_WEEK[0].label).toBe('Monday')
    expect(DAYS_OF_WEEK[6].value).toBe(6)
    expect(DAYS_OF_WEEK[6].label).toBe('Sunday')
  })

  it('should have required fields for each day', () => {
    DAYS_OF_WEEK.forEach((day) => {
      expect(day).toHaveProperty('value')
      expect(day).toHaveProperty('label')
      expect(day).toHaveProperty('shortLabel')

      expect(typeof day.value).toBe('number')
      expect(typeof day.label).toBe('string')
      expect(typeof day.shortLabel).toBe('string')
      expect(day.value).toBeGreaterThanOrEqual(0)
      expect(day.value).toBeLessThanOrEqual(6)
    })
  })

  it('should have valid short labels', () => {
    const expectedShortLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    const actualShortLabels = DAYS_OF_WEEK.map((day) => day.shortLabel)

    expect(actualShortLabels).toEqual(expectedShortLabels)
  })
})

describe('SENSOR_TYPES', () => {
  it('should have all 3 sensor types from backend', () => {
    expect(SENSOR_TYPES).toHaveLength(3)
  })

  it('should match backend sensor type values', () => {
    const expectedTypes = ['motion', 'light', 'temperature']
    const actualTypes = SENSOR_TYPES.map((type) => type.value)

    expect(actualTypes.sort()).toEqual(expectedTypes.sort())
  })

  it('should have required fields for each sensor type', () => {
    SENSOR_TYPES.forEach((type) => {
      expect(type).toHaveProperty('value')
      expect(type).toHaveProperty('label')
      expect(type).toHaveProperty('description')

      expect(typeof type.value).toBe('string')
      expect(typeof type.label).toBe('string')
      expect(typeof type.description).toBe('string')
      expect(type.description.length).toBeGreaterThan(0)
    })
  })
})

describe('SENSOR_COMPARISONS', () => {
  it('should have all 5 comparison operators from backend', () => {
    expect(SENSOR_COMPARISONS).toHaveLength(5)
  })

  it('should match backend comparison values', () => {
    const expectedComparisons = ['gt', 'lt', 'eq', 'gte', 'lte']
    const actualComparisons = SENSOR_COMPARISONS.map((comp) => comp.value)

    expect(actualComparisons).toEqual(expectedComparisons)
  })

  it('should have required fields for each comparison', () => {
    SENSOR_COMPARISONS.forEach((comp) => {
      expect(comp).toHaveProperty('value')
      expect(comp).toHaveProperty('label')
      expect(comp).toHaveProperty('symbol')

      expect(typeof comp.value).toBe('string')
      expect(typeof comp.label).toBe('string')
      expect(typeof comp.symbol).toBe('string')
      expect(comp.symbol.length).toBeGreaterThan(0)
    })
  })

  it('should have valid symbols', () => {
    const symbols = SENSOR_COMPARISONS.map((comp) => comp.symbol)
    const validSymbols = ['>', '<', '=', '≥', '≤']

    expect(symbols).toEqual(validSymbols)
  })
})

describe('TRIGGER_DEFAULTS', () => {
  it('should have defaults for all trigger types', () => {
    const expectedTypes = ['interval', 'solar', 'moon_phase', 'fixed_time', 'sensor']

    expectedTypes.forEach((type) => {
      expect(TRIGGER_DEFAULTS).toHaveProperty(type)
    })
  })

  it('should have trigger_type field matching the key', () => {
    Object.entries(TRIGGER_DEFAULTS).forEach(([key, config]) => {
      expect(config.trigger_type).toBe(key)
    })
  })

  describe('interval defaults', () => {
    const defaults = TRIGGER_DEFAULTS.interval

    it('should have valid structure', () => {
      expect(defaults.trigger_type).toBe('interval')
      expect(defaults.interval_minutes).toBe(60)
      expect(defaults.time_window_start).toBe('00:00')
      expect(defaults.time_window_end).toBe('23:59')
      expect(defaults.days_of_week).toEqual([0, 1, 2, 3, 4, 5, 6])
    })

    it('should have valid interval_minutes', () => {
      expect(defaults.interval_minutes).toBeGreaterThanOrEqual(
        SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES
      )
      expect(defaults.interval_minutes).toBeLessThanOrEqual(
        SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES
      )
    })
  })

  describe('solar defaults', () => {
    const defaults = TRIGGER_DEFAULTS.solar

    it('should have valid structure', () => {
      expect(defaults.trigger_type).toBe('solar')
      expect(defaults.solar_event).toBe('sunset')
      expect(defaults.offset_minutes).toBe(0)
      expect(defaults.days_of_week).toEqual([0, 1, 2, 3, 4, 5, 6])
    })

    it('should have valid solar_event', () => {
      const validEvents = SOLAR_EVENTS.map((event) => event.value)
      expect(validEvents).toContain(defaults.solar_event)
    })

    it('should have valid offset_minutes', () => {
      expect(Math.abs(defaults.offset_minutes)).toBeLessThanOrEqual(
        SCHEDULE_LIMITS.MAX_OFFSET_MINUTES
      )
    })
  })

  describe('moon_phase defaults', () => {
    const defaults = TRIGGER_DEFAULTS.moon_phase

    it('should have valid structure', () => {
      expect(defaults.trigger_type).toBe('moon_phase')
      expect(defaults.moon_phase).toBe('full')
      expect(defaults.time_of_day).toBe('20:00')
      expect(defaults.offset_days).toBe(0)
    })

    it('should have valid moon_phase', () => {
      const validPhases = MOON_PHASES.map((phase) => phase.value)
      expect(validPhases).toContain(defaults.moon_phase)
    })

    it('should have valid time_of_day format', () => {
      expect(defaults.time_of_day).toMatch(TIME_FORMAT_REGEX)
    })

    it('should have valid offset_days', () => {
      expect(Math.abs(defaults.offset_days)).toBeLessThanOrEqual(
        SCHEDULE_LIMITS.MAX_OFFSET_DAYS
      )
    })
  })

  describe('fixed_time defaults', () => {
    const defaults = TRIGGER_DEFAULTS.fixed_time

    it('should have valid structure', () => {
      expect(defaults.trigger_type).toBe('fixed_time')
      expect(defaults.time_of_day).toBe('12:00')
      expect(defaults.days_of_week).toEqual([0, 1, 2, 3, 4, 5, 6])
    })

    it('should have valid time_of_day format', () => {
      expect(defaults.time_of_day).toMatch(TIME_FORMAT_REGEX)
    })
  })

  describe('sensor defaults', () => {
    const defaults = TRIGGER_DEFAULTS.sensor

    it('should have valid structure', () => {
      expect(defaults.trigger_type).toBe('sensor')
      expect(defaults.sensor_type).toBe('light')
      expect(defaults.comparison).toBe('lt')
      expect(defaults.threshold).toBe(100)
      expect(defaults.cooldown_minutes).toBe(5)
    })

    it('should have valid sensor_type', () => {
      const validTypes = SENSOR_TYPES.map((type) => type.value)
      expect(validTypes).toContain(defaults.sensor_type)
    })

    it('should have valid comparison', () => {
      const validComparisons = SENSOR_COMPARISONS.map((comp) => comp.value)
      expect(validComparisons).toContain(defaults.comparison)
    })

    it('should have valid cooldown_minutes', () => {
      expect(defaults.cooldown_minutes).toBeGreaterThanOrEqual(0)
      expect(defaults.cooldown_minutes).toBeLessThanOrEqual(
        SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES
      )
    })
  })
})

describe('TIME_FORMAT_REGEX', () => {
  it('should match valid time formats', () => {
    const validTimes = [
      '00:00',
      '12:00',
      '23:59',
      '08:30',
      '15:45',
      '00:01',
      '23:58',
    ]

    validTimes.forEach((time) => {
      expect(time).toMatch(TIME_FORMAT_REGEX)
    })
  })

  it('should not match invalid time formats', () => {
    const invalidTimes = [
      '24:00', // Invalid hour
      '12:60', // Invalid minute
      '1:00', // Missing leading zero
      '12:5', // Missing leading zero
      '25:00', // Invalid hour
      '12', // Missing minutes
      '12:00:00', // Too many parts
      'noon', // Not a time
      '', // Empty string
    ]

    invalidTimes.forEach((time) => {
      expect(time).not.toMatch(TIME_FORMAT_REGEX)
    })
  })

  it('should validate hours 00-23', () => {
    for (let hour = 0; hour < 24; hour++) {
      const time = `${hour.toString().padStart(2, '0')}:00`
      expect(time).toMatch(TIME_FORMAT_REGEX)
    }

    expect('24:00').not.toMatch(TIME_FORMAT_REGEX)
  })

  it('should validate minutes 00-59', () => {
    for (let minute = 0; minute < 60; minute++) {
      const time = `12:${minute.toString().padStart(2, '0')}`
      expect(time).toMatch(TIME_FORMAT_REGEX)
    }

    expect('12:60').not.toMatch(TIME_FORMAT_REGEX)
  })
})

describe('Constants integrity', () => {
  it('should not have duplicate values in SOLAR_EVENTS', () => {
    const values = SOLAR_EVENTS.map((event) => event.value)
    const uniqueValues = new Set(values)

    expect(values.length).toBe(uniqueValues.size)
  })

  it('should not have duplicate values in MOON_PHASES', () => {
    const values = MOON_PHASES.map((phase) => phase.value)
    const uniqueValues = new Set(values)

    expect(values.length).toBe(uniqueValues.size)
  })

  it('should not have duplicate values in SENSOR_TYPES', () => {
    const values = SENSOR_TYPES.map((type) => type.value)
    const uniqueValues = new Set(values)

    expect(values.length).toBe(uniqueValues.size)
  })

  it('should not have duplicate values in SENSOR_COMPARISONS', () => {
    const values = SENSOR_COMPARISONS.map((comp) => comp.value)
    const uniqueValues = new Set(values)

    expect(values.length).toBe(uniqueValues.size)
  })

  it('should not have duplicate values in DAYS_OF_WEEK', () => {
    const values = DAYS_OF_WEEK.map((day) => day.value)
    const uniqueValues = new Set(values)

    expect(values.length).toBe(uniqueValues.size)
  })
})

describe('validateNumericInput', () => {
  describe('basic validation', () => {
    it('should return number for valid numeric string', () => {
      expect(validateNumericInput('42')).toBe(42)
      expect(validateNumericInput('0')).toBe(0)
      expect(validateNumericInput('-10')).toBe(-10)
      expect(validateNumericInput('3.14')).toBe(3.14)
    })

    it('should return number for numeric input', () => {
      expect(validateNumericInput(42)).toBe(42)
      expect(validateNumericInput(0)).toBe(0)
      expect(validateNumericInput(-10)).toBe(-10)
    })

    it('should return null for NaN', () => {
      expect(validateNumericInput('abc')).toBeNull()
      expect(validateNumericInput('12abc')).toBeNull()
      expect(validateNumericInput(NaN)).toBeNull()
      expect(validateNumericInput('')).toBeNull()
    })

    it('should return null for Infinity', () => {
      expect(validateNumericInput(Infinity)).toBeNull()
      expect(validateNumericInput(-Infinity)).toBeNull()
      expect(validateNumericInput('Infinity')).toBeNull()
    })
  })

  describe('min/max constraints', () => {
    it('should return null when below min', () => {
      expect(validateNumericInput(5, 10)).toBeNull()
      expect(validateNumericInput(-1, 0)).toBeNull()
      expect(validateNumericInput('5', 10)).toBeNull()
    })

    it('should return number when at min', () => {
      expect(validateNumericInput(10, 10)).toBe(10)
      expect(validateNumericInput(0, 0)).toBe(0)
    })

    it('should return null when above max', () => {
      expect(validateNumericInput(15, undefined, 10)).toBeNull()
      expect(validateNumericInput(100, 0, 50)).toBeNull()
    })

    it('should return number when at max', () => {
      expect(validateNumericInput(10, undefined, 10)).toBe(10)
      expect(validateNumericInput(50, 0, 50)).toBe(50)
    })

    it('should return number when within range', () => {
      expect(validateNumericInput(5, 0, 10)).toBe(5)
      expect(validateNumericInput(0, -10, 10)).toBe(0)
      expect(validateNumericInput(-5, -10, 0)).toBe(-5)
    })

    it('should handle min only', () => {
      expect(validateNumericInput(100, 0)).toBe(100)
      expect(validateNumericInput(-1, 0)).toBeNull()
    })

    it('should handle max only', () => {
      expect(validateNumericInput(-100, undefined, 0)).toBe(-100)
      expect(validateNumericInput(1, undefined, 0)).toBeNull()
    })
  })

  describe('SCHEDULE_LIMITS integration', () => {
    it('should validate interval_minutes with SCHEDULE_LIMITS', () => {
      const min = SCHEDULE_LIMITS.MIN_INTERVAL_MINUTES
      const max = SCHEDULE_LIMITS.MAX_INTERVAL_MINUTES

      expect(validateNumericInput(60, min, max)).toBe(60)
      expect(validateNumericInput(0, min, max)).toBeNull()
      expect(validateNumericInput(10081, min, max)).toBeNull()
    })

    it('should validate cooldown_minutes with SCHEDULE_LIMITS', () => {
      const max = SCHEDULE_LIMITS.MAX_COOLDOWN_MINUTES

      expect(validateNumericInput(30, 0, max)).toBe(30)
      expect(validateNumericInput(61, 0, max)).toBeNull()
      expect(validateNumericInput(-1, 0, max)).toBeNull()
    })

    it('should validate offset_minutes with symmetric range', () => {
      const max = SCHEDULE_LIMITS.MAX_OFFSET_MINUTES

      expect(validateNumericInput(0, -max, max)).toBe(0)
      expect(validateNumericInput(720, -max, max)).toBe(720)
      expect(validateNumericInput(-720, -max, max)).toBe(-720)
      expect(validateNumericInput(1441, -max, max)).toBeNull()
      expect(validateNumericInput(-1441, -max, max)).toBeNull()
    })

    it('should validate offset_days with symmetric range', () => {
      const max = SCHEDULE_LIMITS.MAX_OFFSET_DAYS

      expect(validateNumericInput(0, -max, max)).toBe(0)
      expect(validateNumericInput(7, -max, max)).toBe(7)
      expect(validateNumericInput(-7, -max, max)).toBe(-7)
      expect(validateNumericInput(8, -max, max)).toBeNull()
      expect(validateNumericInput(-8, -max, max)).toBeNull()
    })
  })

  describe('edge cases', () => {
    it('should handle undefined and null input', () => {
      expect(validateNumericInput(undefined)).toBeNull()
      expect(validateNumericInput(null)).toBe(0) // Number(null) === 0
    })

    it('should handle whitespace strings', () => {
      expect(validateNumericInput('  42  ')).toBe(42)
      expect(validateNumericInput('   ')).toBeNull()
    })

    it('should handle scientific notation', () => {
      expect(validateNumericInput('1e2')).toBe(100)
      expect(validateNumericInput('1e-2')).toBe(0.01)
    })
  })
})

describe('isValidSolarEvent', () => {
  it('should return true for valid solar events', () => {
    expect(isValidSolarEvent('sunset')).toBe(true)
    expect(isValidSolarEvent('sunrise')).toBe(true)
    expect(isValidSolarEvent('civil_dawn')).toBe(true)
    expect(isValidSolarEvent('astronomical_dusk')).toBe(true)
    expect(isValidSolarEvent('noon')).toBe(true)
  })

  it('should return false for invalid solar events', () => {
    expect(isValidSolarEvent('invalid_event')).toBe(false)
    expect(isValidSolarEvent('midnight')).toBe(false)
    expect(isValidSolarEvent('')).toBe(false)
    expect(isValidSolarEvent('SUNSET')).toBe(false) // case-sensitive
  })

  it('should return false for non-string values', () => {
    expect(isValidSolarEvent(null)).toBe(false)
    expect(isValidSolarEvent(undefined)).toBe(false)
    expect(isValidSolarEvent(123)).toBe(false)
  })

  it('should return false for time strings', () => {
    expect(isValidSolarEvent('12:00')).toBe(false)
    expect(isValidSolarEvent('00:00')).toBe(false)
    expect(isValidSolarEvent('23:59')).toBe(false)
  })

  it('should validate all SOLAR_EVENTS values', () => {
    SOLAR_EVENTS.forEach((event) => {
      expect(isValidSolarEvent(event.value)).toBe(true)
    })
  })
})
