import { describe, it, expect } from 'vitest'
import { formatTimestamp } from '../helpers'

describe('formatTimestamp', () => {
  it('returns "Never" for zero timestamp', () => {
    expect(formatTimestamp(0)).toBe('Never')
  })

  it('returns "Never" for null timestamp', () => {
    expect(formatTimestamp(null)).toBe('Never')
  })

  it('returns "Never" for undefined timestamp', () => {
    expect(formatTimestamp(undefined)).toBe('Never')
  })

  it('formats valid timestamp correctly', () => {
    const timestamp = 1698768000 // 2023-10-31 12:00:00 UTC
    const result = formatTimestamp(timestamp)
    // Date formatting is locale-dependent, so just verify it contains the year
    expect(result).toContain('2023')
    expect(result).not.toBe('Never')
  })

  it('handles very old timestamps', () => {
    const timestamp = 946684800 // 2000-01-01 00:00:00 UTC
    const result = formatTimestamp(timestamp)
    expect(result).toContain('2000')
    expect(result).not.toBe('Never')
  })

  it('handles future timestamps', () => {
    const timestamp = 2000000000 // 2033-05-18 03:33:20 UTC
    const result = formatTimestamp(timestamp)
    expect(result).toContain('2033')
    expect(result).not.toBe('Never')
  })
})
