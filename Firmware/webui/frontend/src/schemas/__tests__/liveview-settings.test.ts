import { describe, it, expect } from 'vitest'
import {
  liveviewSettingsSchema,
  validateLiveviewSettings,
  formatLiveviewValidationErrors,
  type LiveviewValidationError,
} from '../liveview-settings'

describe('liveviewSettingsSchema', () => {
  describe('boolean fields', () => {
    it('accepts actual booleans', () => {
      const result = liveviewSettingsSchema.safeParse({ focus_peaking_enabled: true })
      expect(result.success).toBe(true)
    })

    it('accepts string "true"/"false"', () => {
      const result = liveviewSettingsSchema.safeParse({ awb_enable: 'true' })
      expect(result.success).toBe(true)
    })

    it('rejects invalid boolean strings', () => {
      const result = liveviewSettingsSchema.safeParse({ ae_enable: 'yes' })
      expect(result.success).toBe(false)
    })
  })

  describe('enum fields', () => {
    it('accepts valid af_mode values (0, 1, 2)', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: 0 }).success).toBe(true)
      expect(liveviewSettingsSchema.safeParse({ af_mode: 2 }).success).toBe(true)
    })

    it('accepts string-encoded integers', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: '1' }).success).toBe(true)
    })

    it('rejects out-of-range enum values', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: 5 }).success).toBe(false)
    })

    it('rejects non-numeric strings', () => {
      expect(liveviewSettingsSchema.safeParse({ af_mode: 'abc' }).success).toBe(false)
    })
  })

  describe('range fields', () => {
    it('accepts sharpness within range (0.0 - 4.0)', () => {
      expect(liveviewSettingsSchema.safeParse({ sharpness: 2.5 }).success).toBe(true)
    })

    it('rejects sharpness out of range', () => {
      expect(liveviewSettingsSchema.safeParse({ sharpness: 5.0 }).success).toBe(false)
    })

    it('accepts brightness at boundaries (-1.0 to 1.0)', () => {
      expect(liveviewSettingsSchema.safeParse({ brightness: -1.0 }).success).toBe(true)
      expect(liveviewSettingsSchema.safeParse({ brightness: 1.0 }).success).toBe(true)
    })

    it('accepts exposure_time integer (1 to 999999)', () => {
      expect(liveviewSettingsSchema.safeParse({ exposure_time: 50000 }).success).toBe(true)
    })

    it('rejects exposure_time at 0', () => {
      expect(liveviewSettingsSchema.safeParse({ exposure_time: 0 }).success).toBe(false)
    })
  })

  describe('string enum fields', () => {
    it('accepts valid focus_peaking_colour', () => {
      expect(liveviewSettingsSchema.safeParse({ focus_peaking_colour: 'green' }).success).toBe(true)
    })

    it('rejects invalid focus_peaking_colour', () => {
      expect(liveviewSettingsSchema.safeParse({ focus_peaking_colour: 'purple' }).success).toBe(false)
    })

    it('accepts valid focus_peaking_algorithm', () => {
      expect(liveviewSettingsSchema.safeParse({ focus_peaking_algorithm: 'sobel' }).success).toBe(true)
    })
  })

  describe('passthrough for unknown keys', () => {
    it('passes through keys not in the schema', () => {
      const result = liveviewSettingsSchema.safeParse({ unknown_key: 'value', sharpness: 1.0 })
      expect(result.success).toBe(true)
    })
  })
})

describe('validateLiveviewSettings', () => {
  it('returns empty array for valid settings', () => {
    const errors = validateLiveviewSettings({ sharpness: 2.0, brightness: 0.5 })
    expect(errors).toEqual([])
  })

  it('returns errors for invalid settings', () => {
    const errors = validateLiveviewSettings({ sharpness: 5.0, brightness: 2.0 })
    expect(errors).toHaveLength(2)
    expect(errors[0]).toMatchObject({ key: 'sharpness' })
    expect(errors[1]).toMatchObject({ key: 'brightness' })
  })

  it('converts camelCase keys to snake_case via toBackendKey', () => {
    const errors = validateLiveviewSettings({ colourGainRed: 2.0 })
    expect(errors).toEqual([])
  })

  it('rejects invalid value after camelCase key conversion', () => {
    const errors = validateLiveviewSettings({ colourGainRed: 0.5 })
    expect(errors).toHaveLength(1)
    expect(errors[0].key).toBe('colour_gains_red')
  })

  it('passes through unknown camelCase keys without error', () => {
    const errors = validateLiveviewSettings({ someUnknownSetting: 'whatever' })
    expect(errors).toEqual([])
  })
})

describe('formatLiveviewValidationErrors', () => {
  it('returns empty string for no errors', () => {
    expect(formatLiveviewValidationErrors([])).toBe('')
  })

  it('formats errors with count header', () => {
    const errors: LiveviewValidationError[] = [
      { key: 'sharpness', value: 5.0, message: 'Sharpness must be between 0.0 and 4.0' },
    ]
    const result = formatLiveviewValidationErrors(errors)
    expect(result).toContain('1 error')
    expect(result).toContain('sharpness')
  })

  it('truncates at maxErrors', () => {
    const errors: LiveviewValidationError[] = Array.from({ length: 10 }, (_, i) => ({
      key: `key_${i}`,
      value: i,
      message: `Error ${i}`,
    }))
    const result = formatLiveviewValidationErrors(errors, 3)
    expect(result).toContain('and 7 more')
  })
})
