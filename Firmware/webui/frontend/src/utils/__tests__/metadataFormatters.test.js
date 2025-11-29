import { describe, it, expect } from 'vitest'
import {
  formatGPSCoordinate,
  decimalToDMS,
  formatAltitude,
  formatExposureTime,
  formatAperture,
  formatISO,
  formatFocalLength,
  formatTimestamp,
  formatFileSize,
} from '../metadataFormatters'

describe('formatGPSCoordinate', () => {
  it('formats positive latitude correctly', () => {
    expect(formatGPSCoordinate(34.0522, 'lat')).toBe('34°03\'07.9" N')
  })

  it('formats negative latitude correctly', () => {
    expect(formatGPSCoordinate(-34.0522, 'lat')).toBe('34°03\'07.9" S')
  })

  it('formats positive longitude correctly', () => {
    expect(formatGPSCoordinate(118.2437, 'lon')).toBe('118°14\'37.3" E')
  })

  it('formats negative longitude correctly', () => {
    expect(formatGPSCoordinate(-118.2437, 'lon')).toBe('118°14\'37.3" W')
  })

  it('formats zero latitude correctly', () => {
    expect(formatGPSCoordinate(0, 'lat')).toBe('0°00\'00.0" N')
  })

  it('formats zero longitude correctly', () => {
    expect(formatGPSCoordinate(0, 'lon')).toBe('0°00\'00.0" E')
  })

  it('returns "N/A" for null value', () => {
    expect(formatGPSCoordinate(null, 'lat')).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatGPSCoordinate(undefined, 'lon')).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatGPSCoordinate(NaN, 'lat')).toBe('N/A')
  })

  it('handles boundary latitude values', () => {
    expect(formatGPSCoordinate(90, 'lat')).toBe('90°00\'00.0" N')
    expect(formatGPSCoordinate(-90, 'lat')).toBe('90°00\'00.0" S')
  })

  it('handles boundary longitude values', () => {
    expect(formatGPSCoordinate(180, 'lon')).toBe('180°00\'00.0" E')
    expect(formatGPSCoordinate(-180, 'lon')).toBe('180°00\'00.0" W')
  })

  it('handles very small decimal values', () => {
    expect(formatGPSCoordinate(0.001, 'lat')).toBe('0°00\'03.6" N')
  })

  it('returns "N/A" for invalid type parameter', () => {
    expect(formatGPSCoordinate(34.0522, 'invalid')).toBe('N/A')
  })

  it('returns "N/A" for missing type parameter', () => {
    expect(formatGPSCoordinate(34.0522)).toBe('N/A')
  })
})

describe('decimalToDMS', () => {
  it('converts positive decimal to DMS', () => {
    const result = decimalToDMS(34.0522)
    expect(result.degrees).toBe(34)
    expect(result.minutes).toBe(3)
    expect(result.seconds).toBeCloseTo(7.92, 1)
  })

  it('converts negative decimal to DMS with positive values', () => {
    const result = decimalToDMS(-34.0522)
    expect(result.degrees).toBe(34)
    expect(result.minutes).toBe(3)
    expect(result.seconds).toBeCloseTo(7.92, 1)
  })

  it('converts zero to DMS', () => {
    const result = decimalToDMS(0)
    expect(result.degrees).toBe(0)
    expect(result.minutes).toBe(0)
    expect(result.seconds).toBe(0)
  })

  it('converts fractional degrees correctly', () => {
    const result = decimalToDMS(12.5)
    expect(result.degrees).toBe(12)
    expect(result.minutes).toBe(30)
    expect(result.seconds).toBe(0)
  })

  it('handles very small values', () => {
    const result = decimalToDMS(0.001)
    expect(result.degrees).toBe(0)
    expect(result.minutes).toBe(0)
    expect(result.seconds).toBeCloseTo(3.6, 1)
  })

  it('handles boundary value 90 degrees', () => {
    const result = decimalToDMS(90)
    expect(result.degrees).toBe(90)
    expect(result.minutes).toBe(0)
    expect(result.seconds).toBe(0)
  })

  it('handles boundary value 180 degrees', () => {
    const result = decimalToDMS(180)
    expect(result.degrees).toBe(180)
    expect(result.minutes).toBe(0)
    expect(result.seconds).toBe(0)
  })
})

describe('formatAltitude', () => {
  it('formats positive altitude in meters', () => {
    expect(formatAltitude(1234.5)).toBe('1234.5 m')
  })

  it('formats negative altitude in meters', () => {
    expect(formatAltitude(-123.4)).toBe('-123.4 m')
  })

  it('formats zero altitude', () => {
    expect(formatAltitude(0)).toBe('0 m')
  })

  it('returns "N/A" for null value', () => {
    expect(formatAltitude(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatAltitude(undefined)).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatAltitude(NaN)).toBe('N/A')
  })

  it('handles very large altitude values', () => {
    expect(formatAltitude(8848.86)).toBe('8848.9 m')
  })

  it('handles very small altitude values', () => {
    expect(formatAltitude(0.1)).toBe('0.1 m')
  })

  it('rounds to one decimal place', () => {
    expect(formatAltitude(123.456)).toBe('123.5 m')
  })
})

describe('formatExposureTime', () => {
  it('formats exposure time as fraction for values < 1', () => {
    expect(formatExposureTime(0.005)).toBe('1/200s')
  })

  it('formats exposure time as seconds for values >= 1', () => {
    expect(formatExposureTime(2.5)).toBe('2.5s')
  })

  it('formats very fast shutter speed', () => {
    expect(formatExposureTime(0.001)).toBe('1/1000s')
  })

  it('formats medium shutter speed', () => {
    expect(formatExposureTime(0.0333)).toBe('1/30s')
  })

  it('formats one second exposure', () => {
    expect(formatExposureTime(1)).toBe('1s')
  })

  it('formats long exposure', () => {
    expect(formatExposureTime(30)).toBe('30s')
  })

  it('returns "N/A" for null value', () => {
    expect(formatExposureTime(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatExposureTime(undefined)).toBe('N/A')
  })

  it('returns "N/A" for zero value', () => {
    expect(formatExposureTime(0)).toBe('N/A')
  })

  it('returns "N/A" for negative value', () => {
    expect(formatExposureTime(-0.5)).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatExposureTime(NaN)).toBe('N/A')
  })

  it('rounds fractional denominators correctly', () => {
    expect(formatExposureTime(0.00667)).toBe('1/150s')
  })
})

describe('formatAperture', () => {
  it('formats aperture value correctly', () => {
    expect(formatAperture(2.8)).toBe('f/2.8')
  })

  it('formats whole number aperture', () => {
    expect(formatAperture(8)).toBe('f/8')
  })

  it('formats very wide aperture', () => {
    expect(formatAperture(1.4)).toBe('f/1.4')
  })

  it('formats very narrow aperture', () => {
    expect(formatAperture(22)).toBe('f/22')
  })

  it('returns "N/A" for null value', () => {
    expect(formatAperture(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatAperture(undefined)).toBe('N/A')
  })

  it('returns "N/A" for zero value', () => {
    expect(formatAperture(0)).toBe('N/A')
  })

  it('returns "N/A" for negative value', () => {
    expect(formatAperture(-2.8)).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatAperture(NaN)).toBe('N/A')
  })

  it('rounds to one decimal place', () => {
    expect(formatAperture(2.83456)).toBe('f/2.8')
  })
})

describe('formatISO', () => {
  it('formats ISO value correctly', () => {
    expect(formatISO(800)).toBe('ISO 800')
  })

  it('formats low ISO value', () => {
    expect(formatISO(100)).toBe('ISO 100')
  })

  it('formats high ISO value', () => {
    expect(formatISO(25600)).toBe('ISO 25600')
  })

  it('returns "N/A" for null value', () => {
    expect(formatISO(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatISO(undefined)).toBe('N/A')
  })

  it('returns "N/A" for zero value', () => {
    expect(formatISO(0)).toBe('N/A')
  })

  it('returns "N/A" for negative value', () => {
    expect(formatISO(-100)).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatISO(NaN)).toBe('N/A')
  })

  it('formats decimal ISO values by rounding', () => {
    expect(formatISO(800.5)).toBe('ISO 801')
  })
})

describe('formatFocalLength', () => {
  it('formats focal length correctly', () => {
    expect(formatFocalLength(50)).toBe('50mm')
  })

  it('formats wide angle focal length', () => {
    expect(formatFocalLength(24)).toBe('24mm')
  })

  it('formats telephoto focal length', () => {
    expect(formatFocalLength(200)).toBe('200mm')
  })

  it('formats decimal focal length', () => {
    expect(formatFocalLength(50.5)).toBe('50.5mm')
  })

  it('returns "N/A" for null value', () => {
    expect(formatFocalLength(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatFocalLength(undefined)).toBe('N/A')
  })

  it('returns "N/A" for zero value', () => {
    expect(formatFocalLength(0)).toBe('N/A')
  })

  it('returns "N/A" for negative value', () => {
    expect(formatFocalLength(-50)).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatFocalLength(NaN)).toBe('N/A')
  })

  it('rounds to one decimal place', () => {
    expect(formatFocalLength(50.456)).toBe('50.5mm')
  })
})

describe('formatTimestamp', () => {
  it('formats valid Unix timestamp correctly', () => {
    const timestamp = 1698768000 // 2023-10-31 12:00:00 UTC
    const result = formatTimestamp(timestamp)
    expect(result).toContain('2023')
    expect(result).not.toBe('N/A')
  })

  it('formats ISO 8601 string correctly', () => {
    const isoString = '2023-10-31T12:00:00Z'
    const result = formatTimestamp(isoString)
    expect(result).toContain('2023')
    expect(result).not.toBe('N/A')
  })

  it('formats Date object correctly', () => {
    const date = new Date('2023-10-31T12:00:00Z')
    const result = formatTimestamp(date)
    expect(result).toContain('2023')
    expect(result).not.toBe('N/A')
  })

  it('returns "N/A" for null value', () => {
    expect(formatTimestamp(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatTimestamp(undefined)).toBe('N/A')
  })

  it('returns "N/A" for empty string', () => {
    expect(formatTimestamp('')).toBe('N/A')
  })

  it('returns "N/A" for invalid date string', () => {
    expect(formatTimestamp('invalid-date')).toBe('N/A')
  })

  it('handles very old timestamps', () => {
    const timestamp = 946684800 // 2000-01-01 00:00:00 UTC
    const result = formatTimestamp(timestamp)
    expect(result).toContain('2000')
    expect(result).not.toBe('N/A')
  })

  it('handles future timestamps', () => {
    const timestamp = 2000000000 // 2033-05-18 03:33:20 UTC
    const result = formatTimestamp(timestamp)
    expect(result).toContain('2033')
    expect(result).not.toBe('N/A')
  })

  it('handles millisecond timestamps', () => {
    const timestamp = 1698768000000 // Milliseconds
    const result = formatTimestamp(timestamp)
    expect(result).toContain('2023')
    expect(result).not.toBe('N/A')
  })
})

describe('formatFileSize', () => {
  it('formats bytes correctly', () => {
    expect(formatFileSize(500)).toBe('500 B')
  })

  it('formats kilobytes correctly', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB')
  })

  it('formats megabytes correctly', () => {
    expect(formatFileSize(1048576)).toBe('1.0 MB')
  })

  it('formats gigabytes correctly', () => {
    expect(formatFileSize(1073741824)).toBe('1.0 GB')
  })

  it('formats terabytes correctly', () => {
    expect(formatFileSize(1099511627776)).toBe('1.0 TB')
  })

  it('formats zero bytes', () => {
    expect(formatFileSize(0)).toBe('0 B')
  })

  it('formats fractional kilobytes', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB')
  })

  it('formats fractional megabytes', () => {
    expect(formatFileSize(5242880)).toBe('5.0 MB')
  })

  it('returns "N/A" for null value', () => {
    expect(formatFileSize(null)).toBe('N/A')
  })

  it('returns "N/A" for undefined value', () => {
    expect(formatFileSize(undefined)).toBe('N/A')
  })

  it('returns "N/A" for negative value', () => {
    expect(formatFileSize(-1024)).toBe('N/A')
  })

  it('returns "N/A" for NaN value', () => {
    expect(formatFileSize(NaN)).toBe('N/A')
  })

  it('rounds to one decimal place', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB')
  })

  it('handles very large files', () => {
    const largeSize = 5 * 1024 * 1024 * 1024 * 1024 // 5 TB
    expect(formatFileSize(largeSize)).toBe('5.0 TB')
  })
})
