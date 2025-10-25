import { describe, it, expect } from 'vitest'
import {
  validateDevicePath,
  validateBaudrate,
  validateTimeout,
  validateGPSConfig
} from '../gpsValidation'

describe('validateDevicePath', () => {
  it('accepts valid Raspberry Pi UART path', () => {
    const result = validateDevicePath('/dev/ttyAMA0')
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts valid USB serial path', () => {
    const result = validateDevicePath('/dev/ttyUSB0')
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts valid standard serial path', () => {
    const result = validateDevicePath('/dev/ttyS0')
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts generic serial path', () => {
    const result = validateDevicePath('/dev/serial0')
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('rejects empty path', () => {
    const result = validateDevicePath('')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('cannot be empty')
  })

  it('rejects null path', () => {
    const result = validateDevicePath(null)
    expect(result.valid).toBe(false)
    expect(result.error).toContain('cannot be empty')
  })

  it('rejects path not starting with /dev/', () => {
    const result = validateDevicePath('/home/ttyAMA0')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('must start with /dev/')
  })

  it('rejects invalid device format', () => {
    const result = validateDevicePath('/dev/random')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('Invalid device path format')
  })
})

describe('validateBaudrate', () => {
  it('accepts valid baudrate 9600', () => {
    const result = validateBaudrate(9600)
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts valid baudrate 115200', () => {
    const result = validateBaudrate(115200)
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts all standard baudrates', () => {
    const validBaudrates = [4800, 9600, 19200, 38400, 57600, 115200]
    validBaudrates.forEach(baudrate => {
      const result = validateBaudrate(baudrate)
      expect(result.valid).toBe(true)
    })
  })

  it('rejects invalid baudrate', () => {
    const result = validateBaudrate(12345)
    expect(result.valid).toBe(false)
    expect(result.error).toContain('must be one of')
  })

  it('rejects non-integer baudrate', () => {
    const result = validateBaudrate(9600.5)
    expect(result.valid).toBe(false)
    expect(result.error).toContain('must be an integer')
  })

  it('rejects string baudrate', () => {
    const result = validateBaudrate('9600')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('must be an integer')
  })
})

describe('validateTimeout', () => {
  it('accepts valid timeout 10 seconds', () => {
    const result = validateTimeout(10)
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts minimum timeout 5 seconds', () => {
    const result = validateTimeout(5)
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('accepts maximum timeout 300 seconds', () => {
    const result = validateTimeout(300)
    expect(result.valid).toBe(true)
    expect(result.error).toBeNull()
  })

  it('rejects timeout below minimum', () => {
    const result = validateTimeout(3)
    expect(result.valid).toBe(false)
    expect(result.error).toContain('at least 5 seconds')
  })

  it('rejects timeout above maximum', () => {
    const result = validateTimeout(400)
    expect(result.valid).toBe(false)
    expect(result.error).toContain('cannot exceed 300 seconds')
  })

  it('rejects non-numeric timeout', () => {
    const result = validateTimeout('10')
    expect(result.valid).toBe(false)
    expect(result.error).toContain('must be a number')
  })
})

describe('validateGPSConfig', () => {
  it('validates complete valid config', () => {
    const config = {
      device: '/dev/ttyAMA0',
      baudrate: 9600,
      timeout: 10
    }
    const result = validateGPSConfig(config)
    expect(result.valid).toBe(true)
    expect(result.errors).toEqual({})
  })

  it('detects invalid device path', () => {
    const config = {
      device: '/invalid/path',
      baudrate: 9600,
      timeout: 10
    }
    const result = validateGPSConfig(config)
    expect(result.valid).toBe(false)
    expect(result.errors.device).toBeDefined()
  })

  it('detects invalid baudrate', () => {
    const config = {
      device: '/dev/ttyAMA0',
      baudrate: 12345,
      timeout: 10
    }
    const result = validateGPSConfig(config)
    expect(result.valid).toBe(false)
    expect(result.errors.baudrate).toBeDefined()
  })

  it('detects invalid timeout', () => {
    const config = {
      device: '/dev/ttyAMA0',
      baudrate: 9600,
      timeout: 1000
    }
    const result = validateGPSConfig(config)
    expect(result.valid).toBe(false)
    expect(result.errors.timeout).toBeDefined()
  })

  it('detects multiple errors', () => {
    const config = {
      device: '/invalid',
      baudrate: 12345,
      timeout: 1
    }
    const result = validateGPSConfig(config)
    expect(result.valid).toBe(false)
    expect(result.errors.device).toBeDefined()
    expect(result.errors.baudrate).toBeDefined()
    expect(result.errors.timeout).toBeDefined()
  })

  it('handles partial config validation', () => {
    const config = {
      timeout: 20
    }
    const result = validateGPSConfig(config)
    expect(result.valid).toBe(true)
    expect(result.errors).toEqual({})
  })
})
