import { describe, it, expect } from 'vitest'
import { formatTimestamp, formatErrorMessage } from '../helpers'

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

describe('formatErrorMessage', () => {
  it('formats error with message', () => {
    const error = new Error('Network timeout')
    const result = formatErrorMessage(error, 'Error loading photos')
    expect(result).toBe('Error loading photos: Network timeout')
  })

  it('uses fallback for error without message', () => {
    const result = formatErrorMessage({}, 'Error loading photos')
    expect(result).toBe('Error loading photos: An unexpected error occurred')
  })

  it('uses fallback for null error', () => {
    const result = formatErrorMessage(null, 'Error loading photos')
    expect(result).toBe('Error loading photos: An unexpected error occurred')
  })

  it('uses fallback for undefined error', () => {
    const result = formatErrorMessage(undefined, 'Error loading photos')
    expect(result).toBe('Error loading photos: An unexpected error occurred')
  })

  it('uses custom fallback when provided', () => {
    const result = formatErrorMessage(null, 'Failed to save', 'Unknown error')
    expect(result).toBe('Failed to save: Unknown error')
  })

  it('handles error object with empty string message', () => {
    const error = { message: '' }
    const result = formatErrorMessage(error, 'Error loading photos')
    expect(result).toBe('Error loading photos: An unexpected error occurred')
  })

  it('handles different prefix messages', () => {
    const error = new Error('Connection refused')
    const result = formatErrorMessage(error, 'Error loading more photos')
    expect(result).toBe('Error loading more photos: Connection refused')
  })
})
