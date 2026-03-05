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
})
