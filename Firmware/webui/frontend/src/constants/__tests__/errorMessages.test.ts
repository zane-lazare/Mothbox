import { describe, it, expect } from 'vitest'
import {
  REQUIRED,
  RANGE,
  LENGTH,
  TYPE,
  FORMAT,
  COORDINATES,
  GPS,
  DEPLOYMENT,
  SCHEDULER,
  CRON,
  PRESET,
  TAG,
  SPECIES,
  METADATA,
  NETWORK,
  VALIDATION,
} from '../errorMessages'

describe('errorMessages', () => {
  describe('REQUIRED', () => {
    it('field() generates required message with name', () => {
      expect(REQUIRED.field('Preset name')).toBe('Preset name is required')
    })

    it('field() works with different names', () => {
      expect(REQUIRED.field('Device path')).toBe('Device path is required')
      expect(REQUIRED.field('Schedule name')).toBe('Schedule name is required')
      expect(REQUIRED.field('Deployment name')).toBe('Deployment name is required')
    })

    it('selection() generates selection message', () => {
      expect(REQUIRED.selection('Action type')).toBe('Action type must be selected')
    })

    it('selection() works with different names', () => {
      expect(REQUIRED.selection('Day')).toBe('Day must be selected')
    })
  })

  describe('RANGE', () => {
    it('min() without unit', () => {
      expect(RANGE.min(5)).toBe('Must be at least 5')
    })

    it('min() with unit and space', () => {
      expect(RANGE.min(5, 's')).toBe('Must be at least 5 s')
    })

    it('max() without unit', () => {
      expect(RANGE.max(100)).toBe('Cannot exceed 100')
    })

    it('max() with unit', () => {
      expect(RANGE.max(60, 's')).toBe('Cannot exceed 60 s')
    })

    it('between() without unit', () => {
      expect(RANGE.between(1, 10)).toBe('Must be between 1 and 10')
    })

    it('between() with unit', () => {
      expect(RANGE.between(1, 100, 'minutes')).toBe('Must be between 1 and 100 minutes')
    })
  })

  describe('LENGTH', () => {
    it('min() generates minimum length message', () => {
      expect(LENGTH.min(3)).toBe('Must be at least 3 characters')
    })

    it('max() generates maximum length message', () => {
      expect(LENGTH.max(50)).toBe('Must be 50 characters or less')
    })

    it('max() with different values', () => {
      expect(LENGTH.max(200)).toBe('Must be 200 characters or less')
    })
  })

  describe('TYPE', () => {
    it('number() with label', () => {
      expect(TYPE.number('Interval')).toBe('Interval must be a number')
    })

    it('number() without label', () => {
      expect(TYPE.number()).toBe('Must be a number')
    })

    it('integer() with label', () => {
      expect(TYPE.integer('Offset')).toBe('Offset must be a whole number')
    })

    it('integer() without label', () => {
      expect(TYPE.integer()).toBe('Must be a whole number')
    })

    it('string() with label', () => {
      expect(TYPE.string('Cron expression')).toBe('Cron expression must be a string')
    })

    it('string() without label', () => {
      expect(TYPE.string()).toBe('Must be a string')
    })
  })

  describe('FORMAT', () => {
    it('time is generic HH:MM message', () => {
      expect(FORMAT.time).toBe('Must be in HH:MM format')
    })

    it('validTime includes "valid time" phrasing', () => {
      expect(FORMAT.validTime).toBe('Must be a valid time in HH:MM format')
    })

    it('timeRequired uses "Time must be" phrasing', () => {
      expect(FORMAT.timeRequired).toBe('Time must be in HH:MM format')
    })

    it('timeOrSolar for time-window schema', () => {
      expect(FORMAT.timeOrSolar).toBe('Must be valid HH:MM time or solar event')
    })

    it('url is a valid URL message', () => {
      expect(FORMAT.url).toBe('Please enter a valid URL (e.g., https://example.com)')
    })
  })

  describe('COORDINATES', () => {
    it('latitude message', () => {
      expect(COORDINATES.latitude).toBe('Latitude must be between -90 and 90')
    })

    it('longitude message', () => {
      expect(COORDINATES.longitude).toBe('Longitude must be between -180 and 180')
    })
  })

  describe('GPS', () => {
    it('invalidPath message', () => {
      expect(GPS.invalidPath).toBe(
        'Invalid device path format. Expected /dev/ttyAMA0, /dev/ttyUSB0, etc.'
      )
    })

    it('invalidBaudrate message', () => {
      expect(GPS.invalidBaudrate).toBe('Invalid baudrate')
    })

    it('timeoutMin() with no space before unit', () => {
      expect(GPS.timeoutMin(5)).toBe('Must be at least 5s')
      expect(GPS.timeoutMin(30)).toBe('Must be at least 30s')
      expect(GPS.timeoutMin(60)).toBe('Must be at least 60s')
      expect(GPS.timeoutMin(300)).toBe('Must be at least 300s')
    })

    it('timeoutMax() with no space before unit', () => {
      expect(GPS.timeoutMax(60)).toBe('Cannot exceed 60s')
      expect(GPS.timeoutMax(180)).toBe('Cannot exceed 180s')
      expect(GPS.timeoutMax(300)).toBe('Cannot exceed 300s')
      expect(GPS.timeoutMax(1800)).toBe('Cannot exceed 1800s')
    })
  })

  describe('DEPLOYMENT', () => {
    it('endBeforeStart message', () => {
      expect(DEPLOYMENT.endBeforeStart).toBe('End date must be on or after start date')
    })

    it('maxCustomFields() with count', () => {
      expect(DEPLOYMENT.maxCustomFields(50)).toBe('Maximum 50 custom fields')
    })
  })

  describe('SCHEDULER', () => {
    it('sameStartEnd message', () => {
      expect(SCHEDULER.sameStartEnd).toBe('Start and end times cannot be the same')
    })

    it('invalidSolarEvent message', () => {
      expect(SCHEDULER.invalidSolarEvent).toBe('Invalid solar event')
    })

    it('invalidMoonPhase message', () => {
      expect(SCHEDULER.invalidMoonPhase).toBe('Invalid moon phase')
    })

    it('invalidSensorType message', () => {
      expect(SCHEDULER.invalidSensorType).toBe('Invalid sensor type')
    })

    it('invalidComparison message', () => {
      expect(SCHEDULER.invalidComparison).toBe('Invalid comparison operator')
    })
  })

  describe('CRON', () => {
    it('format message', () => {
      expect(CRON.format).toBe('Must be 5 space-separated cron fields')
    })
  })

  describe('PRESET', () => {
    it('alphanumericOnly message', () => {
      expect(PRESET.alphanumericOnly).toBe(
        'Name can only contain letters, numbers, and underscores'
      )
    })
  })

  describe('TAG', () => {
    it('empty message', () => {
      expect(TAG.empty).toBe('Tag cannot be empty')
    })

    it('tooLong message', () => {
      expect(TAG.tooLong).toBe('Tag is too long')
    })

    it('minRequired message', () => {
      expect(TAG.minRequired).toBe('At least one tag is required')
    })

    it('tooMany message', () => {
      expect(TAG.tooMany).toBe('Too many tags')
    })
  })

  describe('SPECIES', () => {
    it('nameTooLong message', () => {
      expect(SPECIES.nameTooLong).toBe('Species name is too long')
    })

    it('commonNameTooLong message', () => {
      expect(SPECIES.commonNameTooLong).toBe('Common name is too long')
    })

    it('urlTooLong message', () => {
      expect(SPECIES.urlTooLong).toBe('URL is too long')
    })
  })

  describe('METADATA', () => {
    it('duplicateKey() generates message with key name', () => {
      expect(METADATA.duplicateKey('habitat')).toBe('Duplicate key: "habitat"')
    })

    it('duplicateKey() with different keys', () => {
      expect(METADATA.duplicateKey('temperature')).toBe('Duplicate key: "temperature"')
    })
  })

  describe('NETWORK', () => {
    it('connectionError message', () => {
      expect(NETWORK.connectionError).toBe('Unable to save. Please check your connection.')
    })

    it('serverError message', () => {
      expect(NETWORK.serverError).toBe('Server error. Please try again later.')
    })

    it('timeout message', () => {
      expect(NETWORK.timeout).toBe('Request timed out. Please try again.')
    })
  })

  describe('VALIDATION', () => {
    it('general message', () => {
      expect(VALIDATION.general).toBe('Please fix the errors above.')
    })

    it('requiredField message', () => {
      expect(VALIDATION.requiredField).toBe('This field is required.')
    })
  })

  // Verify exact strings that existing schemas depend on
  describe('backwards compatibility with existing schemas', () => {
    it('preset name required', () => {
      expect(REQUIRED.field('Preset name')).toBe('Preset name is required')
    })

    it('deployment name required', () => {
      expect(REQUIRED.field('Deployment name')).toBe('Deployment name is required')
    })

    it('schedule name required', () => {
      expect(REQUIRED.field('Schedule name')).toBe('Schedule name is required')
    })

    it('field name required', () => {
      expect(REQUIRED.field('Field name')).toBe('Field name is required')
    })

    it('cron expression required', () => {
      expect(REQUIRED.field('Cron expression')).toBe('Cron expression is required')
    })

    it('interval type messages', () => {
      expect(TYPE.number('Interval')).toBe('Interval must be a number')
      expect(TYPE.integer('Interval')).toBe('Interval must be a whole number')
    })

    it('offset type messages', () => {
      expect(TYPE.number('Offset')).toBe('Offset must be a number')
      expect(TYPE.integer('Offset')).toBe('Offset must be a whole number')
    })

    it('threshold type messages', () => {
      expect(TYPE.number('Threshold')).toBe('Threshold must be a number')
    })

    it('cooldown type messages', () => {
      expect(TYPE.number('Cooldown')).toBe('Cooldown must be a number')
      expect(TYPE.integer('Cooldown')).toBe('Cooldown must be a whole number')
    })

    it('cron string type message', () => {
      expect(TYPE.string('Cron expression')).toBe('Cron expression must be a string')
    })

    it('fixed-time format', () => {
      expect(FORMAT.validTime).toBe('Must be a valid time in HH:MM format')
    })

    it('moon-phase and pre-condition time format', () => {
      expect(FORMAT.timeRequired).toBe('Time must be in HH:MM format')
    })

    it('time-window format', () => {
      expect(FORMAT.timeOrSolar).toBe('Must be valid HH:MM time or solar event')
    })

    it('GPS timeout messages match schema exactly', () => {
      expect(GPS.timeoutMin(5)).toBe('Must be at least 5s')
      expect(GPS.timeoutMax(60)).toBe('Cannot exceed 60s')
      expect(GPS.timeoutMin(30)).toBe('Must be at least 30s')
      expect(GPS.timeoutMax(180)).toBe('Cannot exceed 180s')
      expect(GPS.timeoutMin(60)).toBe('Must be at least 60s')
      expect(GPS.timeoutMax(300)).toBe('Cannot exceed 300s')
      expect(GPS.timeoutMin(300)).toBe('Must be at least 300s')
      expect(GPS.timeoutMax(1800)).toBe('Cannot exceed 1800s')
    })

    it('deployment end before start', () => {
      expect(DEPLOYMENT.endBeforeStart).toBe('End date must be on or after start date')
    })

    it('deployment max custom fields', () => {
      expect(DEPLOYMENT.maxCustomFields(50)).toBe('Maximum 50 custom fields')
    })

    it('coordinate ranges match schema', () => {
      expect(COORDINATES.latitude).toBe('Latitude must be between -90 and 90')
      expect(COORDINATES.longitude).toBe('Longitude must be between -180 and 180')
    })

    it('deployment length max messages', () => {
      expect(LENGTH.max(200)).toBe('Must be 200 characters or less')
      expect(LENGTH.max(50)).toBe('Must be 50 characters or less')
    })

    it('preset alphanumeric', () => {
      expect(PRESET.alphanumericOnly).toBe(
        'Name can only contain letters, numbers, and underscores'
      )
    })

    it('tag messages match schema', () => {
      expect(TAG.empty).toBe('Tag cannot be empty')
      expect(TAG.tooLong).toBe('Tag is too long')
      expect(TAG.minRequired).toBe('At least one tag is required')
      expect(TAG.tooMany).toBe('Too many tags')
    })

    it('species messages match schema', () => {
      expect(SPECIES.nameTooLong).toBe('Species name is too long')
      expect(SPECIES.commonNameTooLong).toBe('Common name is too long')
      expect(SPECIES.urlTooLong).toBe('URL is too long')
    })

    it('metadata duplicate key', () => {
      expect(METADATA.duplicateKey('habitat')).toBe('Duplicate key: "habitat"')
    })

    it('URL format', () => {
      expect(FORMAT.url).toBe('Please enter a valid URL (e.g., https://example.com)')
    })

    it('name min length', () => {
      expect(LENGTH.min(3)).toBe('Must be at least 3 characters')
    })

    it('deployment range messages', () => {
      expect(RANGE.between(-90, 90)).toBe('Must be between -90 and 90')
      expect(RANGE.between(-180, 180)).toBe('Must be between -180 and 180')
    })
  })
})
