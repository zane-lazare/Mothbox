import { describe, it, expect } from 'vitest'
import { formatCoordinateDisplay, decimalToDMS } from '../coordinateFormat'

describe('decimalToDMS', () => {
  it('converts positive latitude', () => {
    const result = decimalToDMS(37.7749, true)
    expect(result.degrees).toBe(37)
    expect(result.minutes).toBe(46)
    expect(result.reference).toBe('N')
  })

  it('converts negative longitude', () => {
    const result = decimalToDMS(-122.4194, false)
    expect(result.degrees).toBe(122)
    expect(result.reference).toBe('W')
  })

  it('respects secondsPrecision', () => {
    const result = decimalToDMS(37.7749, true, 4)
    expect(result.seconds.toFixed(4)).toBe('29.6400')
  })

  it('throws for NaN', () => {
    expect(() => decimalToDMS(NaN, true)).toThrow('NaN')
  })

  it('throws for out-of-range latitude', () => {
    expect(() => decimalToDMS(91, true)).toThrow('Invalid latitude')
  })

  // --- Edge cases ported from gpsCoordinates.test.ts ---

  it('handles Null Island (0, 0)', () => {
    const lat = decimalToDMS(0, true)
    expect(lat).toEqual({ degrees: 0, minutes: 0, seconds: 0, reference: 'N' })
    const lon = decimalToDMS(0, false)
    expect(lon).toEqual({ degrees: 0, minutes: 0, seconds: 0, reference: 'E' })
  })

  it('handles North Pole (90)', () => {
    const result = decimalToDMS(90, true)
    expect(result).toEqual({ degrees: 90, minutes: 0, seconds: 0, reference: 'N' })
  })

  it('handles South Pole (-90)', () => {
    const result = decimalToDMS(-90, true)
    expect(result).toEqual({ degrees: 90, minutes: 0, seconds: 0, reference: 'S' })
  })

  it('handles date line (180)', () => {
    const result = decimalToDMS(180, false)
    expect(result).toEqual({ degrees: 180, minutes: 0, seconds: 0, reference: 'E' })
  })

  it('handles anti-meridian (-180)', () => {
    const result = decimalToDMS(-180, false)
    expect(result).toEqual({ degrees: 180, minutes: 0, seconds: 0, reference: 'W' })
  })

  it('respects precision 0 (no decimals in seconds)', () => {
    const result = decimalToDMS(37.7749, true, 0)
    expect(result.seconds).toBe(30) // rounded from 29.64
    expect(Number.isInteger(result.seconds)).toBe(true)
  })

  it('respects precision 4', () => {
    const result = decimalToDMS(37.7749, true, 4)
    expect(result.seconds.toFixed(4)).toBe('29.6400')
  })

  it('respects precision 6', () => {
    const result = decimalToDMS(37.7749, true, 6)
    expect(result.seconds.toFixed(6)).toBe('29.640000')
  })

  it('handles seconds overflow from rounding', () => {
    // 37.99999: fractional part 0.99999 * 60 = 59.9994 minutes
    // floor(59.9994) = 59 minutes, (59.9994 - 59) * 60 = 59.964 seconds
    // With precision 0: round(59.964) = 60 → should overflow to minutes+1
    const result = decimalToDMS(37.99999, true, 0)
    expect(result.seconds).toBeLessThan(60)
    // Verify the cascade: minutes should have absorbed the overflow
    expect(result.minutes).toBeLessThan(60)
  })

  it('throws for Infinity', () => {
    expect(() => decimalToDMS(Infinity, true)).toThrow('infinity')
    expect(() => decimalToDMS(-Infinity, false)).toThrow('infinity')
  })

  it('throws for null (via as any)', () => {
    expect(() => decimalToDMS(null as any, true)).toThrow('null')
  })

  it('throws for undefined (via as any)', () => {
    expect(() => decimalToDMS(undefined as any, true)).toThrow('null')
  })

  it('throws for invalid secondsPrecision -1', () => {
    expect(() => decimalToDMS(37.0, true, -1)).toThrow('Invalid secondsPrecision')
  })

  it('throws for invalid secondsPrecision 7', () => {
    expect(() => decimalToDMS(37.0, true, 7)).toThrow('Invalid secondsPrecision')
  })

  it('throws for non-integer secondsPrecision 1.5', () => {
    expect(() => decimalToDMS(37.0, true, 1.5)).toThrow('Invalid secondsPrecision')
  })

  it('throws for out-of-range longitude (181)', () => {
    expect(() => decimalToDMS(181, false)).toThrow('Invalid longitude')
  })
})

describe('formatCoordinateDisplay', () => {
  it('formats DMS (default)', () => {
    const result = formatCoordinateDisplay(37.7749, true)
    expect(result).toMatch(/37°46'.*"N/)
  })

  it('formats decimal', () => {
    const result = formatCoordinateDisplay(37.7749, true, 'decimal')
    expect(result).toContain('°N')
    expect(result).toMatch(/37\.774900/)
  })

  it('formats short', () => {
    const result = formatCoordinateDisplay(37.7749, true, 'short')
    expect(result).toBe('37.77°N')
  })

  it('throws for invalid format', () => {
    // @ts-expect-error testing invalid input
    expect(() => formatCoordinateDisplay(37.7749, true, 'invalid')).toThrow('Invalid format')
  })

  // --- Edge cases ported from gpsCoordinates.test.ts ---

  it('formats all 3 formats for a negative longitude (W reference)', () => {
    const dms = formatCoordinateDisplay(-122.4194, false, 'dms')
    expect(dms).toMatch(/122°25'.*"W/)

    const decimal = formatCoordinateDisplay(-122.4194, false, 'decimal')
    expect(decimal).toContain('°W')
    expect(decimal).toMatch(/122\.419400/)

    const short = formatCoordinateDisplay(-122.4194, false, 'short')
    expect(short).toBe('122.42°W')
  })

  it('DMS with precision 0 has no decimal in seconds', () => {
    const result = formatCoordinateDisplay(37.7749, true, 'dms', 0)
    // Should contain e.g. 30" not 29.64"
    expect(result).toMatch(/\d+"N$/)
    expect(result).not.toContain('.')
  })

  it('DMS with precision 4', () => {
    const result = formatCoordinateDisplay(37.7749, true, 'dms', 4)
    expect(result).toMatch(/29\.6400"N/)
  })
})
