import { describe, it, expect } from 'vitest'
import {
  gpsSettingsSchema,
  GPS_SETTINGS_DEFAULTS,
  BAUDRATE_VALUES,
} from '../gps-settings'

/** Build a valid config, optionally overriding specific fields. */
function validConfig(overrides: Record<string, unknown> = {}) {
  return { ...GPS_SETTINGS_DEFAULTS, ...overrides }
}

describe('gpsSettingsSchema', () => {
  describe('BAUDRATE_VALUES', () => {
    it('contains the expected baud rates', () => {
      expect([...BAUDRATE_VALUES]).toEqual([4800, 9600, 19200, 38400, 57600, 115200])
    })
  })

  describe('GPS_SETTINGS_DEFAULTS', () => {
    it('passes schema validation', () => {
      const result = gpsSettingsSchema.safeParse(GPS_SETTINGS_DEFAULTS)
      expect(result.success).toBe(true)
    })
  })

  describe('valid config', () => {
    it('accepts a complete valid config', () => {
      const result = gpsSettingsSchema.safeParse(validConfig())
      expect(result.success).toBe(true)
    })

    it('accepts config with all fields overridden', () => {
      const result = gpsSettingsSchema.safeParse({
        enabled: true,
        device: '/dev/ttyUSB0',
        baudrate: 115200,
        timeout: 30,
        timeout_hot: 10,
        timeout_warm: 90,
        timeout_cold: 120,
        timeout_almanac: 600,
      })
      expect(result.success).toBe(true)
    })
  })

  describe('device path validation', () => {
    it.each([
      '/dev/ttyAMA0',
      '/dev/ttyS0',
      '/dev/ttyUSB0',
      '/dev/serial0',
      '/dev/ttyAMA1',
      '/dev/ttyUSB2',
    ])('accepts valid device path: %s', (device) => {
      const result = gpsSettingsSchema.safeParse(validConfig({ device }))
      expect(result.success).toBe(true)
    })

    it('rejects empty device path', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ device: '' }))
      expect(result.success).toBe(false)
    })

    it('rejects path not starting with /dev/', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ device: '/tmp/ttyAMA0' }))
      expect(result.success).toBe(false)
    })

    it('rejects invalid device format like /dev/sda1', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ device: '/dev/sda1' }))
      expect(result.success).toBe(false)
    })

    it('rejects bare device name without /dev/ prefix', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ device: 'ttyAMA0' }))
      expect(result.success).toBe(false)
    })
  })

  describe('baudrate validation', () => {
    it.each(BAUDRATE_VALUES)('accepts valid baudrate: %d', (baudrate) => {
      const result = gpsSettingsSchema.safeParse(validConfig({ baudrate }))
      expect(result.success).toBe(true)
    })

    it('coerces string "9600" to number 9600', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ baudrate: '9600' }))
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.baudrate).toBe(9600)
      }
    })

    it('rejects invalid baudrate 12345', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ baudrate: 12345 }))
      expect(result.success).toBe(false)
    })
  })

  describe('timeout_hot validation', () => {
    it('accepts value at minimum (5)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_hot: 5 }))
      expect(result.success).toBe(true)
    })

    it('accepts value at maximum (60)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_hot: 60 }))
      expect(result.success).toBe(true)
    })

    it('rejects value below minimum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_hot: 4 }))
      expect(result.success).toBe(false)
    })

    it('rejects value above maximum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_hot: 61 }))
      expect(result.success).toBe(false)
    })

    it('coerces string to number', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_hot: '15' }))
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.timeout_hot).toBe(15)
      }
    })
  })

  describe('timeout_warm validation', () => {
    it('accepts value at minimum (30)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_warm: 30 }))
      expect(result.success).toBe(true)
    })

    it('accepts value at maximum (180)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_warm: 180 }))
      expect(result.success).toBe(true)
    })

    it('rejects value below minimum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_warm: 29 }))
      expect(result.success).toBe(false)
    })

    it('rejects value above maximum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_warm: 181 }))
      expect(result.success).toBe(false)
    })

    it('coerces string to number', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_warm: '60' }))
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.timeout_warm).toBe(60)
      }
    })
  })

  describe('timeout_cold validation', () => {
    it('accepts value at minimum (60)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_cold: 60 }))
      expect(result.success).toBe(true)
    })

    it('accepts value at maximum (300)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_cold: 300 }))
      expect(result.success).toBe(true)
    })

    it('rejects value below minimum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_cold: 59 }))
      expect(result.success).toBe(false)
    })

    it('rejects value above maximum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_cold: 301 }))
      expect(result.success).toBe(false)
    })

    it('coerces string to number', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_cold: '90' }))
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.timeout_cold).toBe(90)
      }
    })
  })

  describe('timeout_almanac validation', () => {
    it('accepts value at minimum (300)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_almanac: 300 }))
      expect(result.success).toBe(true)
    })

    it('accepts value at maximum (1800)', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_almanac: 1800 }))
      expect(result.success).toBe(true)
    })

    it('rejects value below minimum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_almanac: 299 }))
      expect(result.success).toBe(false)
    })

    it('rejects value above maximum', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_almanac: 1801 }))
      expect(result.success).toBe(false)
    })

    it('coerces string to number', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout_almanac: '1200' }))
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.timeout_almanac).toBe(1200)
      }
    })
  })

  describe('timeout (base, legacy pass-through)', () => {
    it('accepts positive values (no upper bound — backend-only field)', () => {
      expect(gpsSettingsSchema.safeParse(validConfig({ timeout: 1 })).success).toBe(true)
      expect(gpsSettingsSchema.safeParse(validConfig({ timeout: 300 })).success).toBe(true)
    })

    it('rejects zero and negative values', () => {
      expect(gpsSettingsSchema.safeParse(validConfig({ timeout: 0 })).success).toBe(false)
      expect(gpsSettingsSchema.safeParse(validConfig({ timeout: -1 })).success).toBe(false)
    })

    it('coerces string to number', () => {
      const result = gpsSettingsSchema.safeParse(validConfig({ timeout: '10' }))
      expect(result.success).toBe(true)
      if (result.success) {
        expect(result.data.timeout).toBe(10)
      }
    })
  })

  describe('missing required fields', () => {
    it('rejects missing enabled', () => {
      const { enabled: _enabled, ...rest } = validConfig()
      const result = gpsSettingsSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects missing device', () => {
      const { device: _device, ...rest } = validConfig()
      const result = gpsSettingsSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects missing baudrate', () => {
      const { baudrate: _baudrate, ...rest } = validConfig()
      const result = gpsSettingsSchema.safeParse(rest)
      expect(result.success).toBe(false)
    })

    it('rejects empty object', () => {
      const result = gpsSettingsSchema.safeParse({})
      expect(result.success).toBe(false)
    })
  })
})
