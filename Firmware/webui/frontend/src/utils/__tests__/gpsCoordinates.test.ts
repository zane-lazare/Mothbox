/**
 * Unit tests for GPS coordinate utilities (TypeScript implementation).
 *
 * This test module mirrors the Python test suite from Tests/unit/test_gps_coordinates.py
 * to ensure identical behavior between backend and frontend implementations.
 *
 * Test Coverage:
 * - decimalToDMS(): Convert decimal degrees to DMS format
 * - dmsToDecimal(): Convert DMS format to decimal degrees
 * - validateCoordinate(): Validate coordinate ranges
 * - formatCoordinateDisplay(): Format coordinates for display
 * - Round-trip accuracy: Decimal → DMS → Decimal
 *
 * Test Data Sources (matching Python):
 * - San Francisco: (37.7749, -122.4194)
 * - Sydney: (-33.8688, 151.2093)
 * - North Pole: (90.0, 0.0)
 * - South Pole: (-90.0, 0.0)
 * - Date Line: (0.0, ±180.0)
 * - Null Island: (0.0, 0.0)
 */

import { describe, test, expect } from 'vitest';
import {
  decimalToDMS,
  dmsToDecimal,
  validateCoordinate,
  formatCoordinateDisplay,
  formatCoordinatePair,
} from '../gpsCoordinates';

// ============================================================================
// TestDecimalToDMS: Test decimal to DMS conversion
// ============================================================================

describe('decimalToDMS', () => {
  describe('happy path conversions', () => {
    test('converts positive latitude to North (San Francisco)', () => {
      // Act: Convert decimal latitude to DMS
      const result = decimalToDMS(37.7749, true);

      // Assert: Verify DMS conversion
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);
      expect(result.minutes).toBe(46);
      // 0.7749 * 60 = 46.494 minutes
      // 0.494 * 60 = 29.64 seconds
      expect(Math.abs(result.seconds - 29.64)).toBeLessThan(0.01);
    });

    test('converts negative latitude to South (Sydney)', () => {
      // Act: Convert negative latitude to DMS
      const result = decimalToDMS(-33.8688, true);

      // Assert: Verify DMS conversion
      expect(result.reference).toBe('S');
      expect(result.degrees).toBe(33);
      expect(result.minutes).toBe(52);
      // 0.8688 * 60 = 52.128 minutes
      // 0.128 * 60 = 7.68 seconds
      expect(Math.abs(result.seconds - 7.68)).toBeLessThan(0.01);
    });

    test('converts positive longitude to East (Sydney)', () => {
      // Act: Convert positive longitude to DMS
      const result = decimalToDMS(151.2093, false);

      // Assert: Verify DMS conversion
      expect(result.reference).toBe('E');
      expect(result.degrees).toBe(151);
      expect(result.minutes).toBe(12);
      // 0.2093 * 60 = 12.558 minutes
      // 0.558 * 60 = 33.48 seconds
      expect(Math.abs(result.seconds - 33.48)).toBeLessThan(0.01);
    });

    test('converts negative longitude to West (San Francisco)', () => {
      // Act: Convert negative longitude to DMS
      const result = decimalToDMS(-122.4194, false);

      // Assert: Verify DMS conversion
      expect(result.reference).toBe('W');
      expect(result.degrees).toBe(122);
      expect(result.minutes).toBe(25);
      // 0.4194 * 60 = 25.164 minutes
      // 0.164 * 60 = 9.84 seconds
      expect(Math.abs(result.seconds - 9.84)).toBeLessThan(0.01);
    });
  });

  describe('edge cases', () => {
    test('handles zero latitude (Equator)', () => {
      // Act: Convert zero latitude
      const result = decimalToDMS(0.0, true);

      // Assert: Verify zero handling (defaults to North)
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(0);
      expect(result.minutes).toBe(0);
      expect(result.seconds).toBe(0.0);
    });

    test('handles zero longitude (Prime Meridian)', () => {
      // Act: Convert zero longitude
      const result = decimalToDMS(0.0, false);

      // Assert: Verify zero handling (defaults to East)
      expect(result.reference).toBe('E');
      expect(result.degrees).toBe(0);
      expect(result.minutes).toBe(0);
      expect(result.seconds).toBe(0.0);
    });

    test('handles North Pole (90°N)', () => {
      // Act: Convert north pole latitude
      const result = decimalToDMS(90.0, true);

      // Assert: Verify extreme latitude
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(90);
      expect(result.minutes).toBe(0);
      expect(result.seconds).toBe(0.0);
    });

    test('handles South Pole (-90°S)', () => {
      // Act: Convert south pole latitude
      const result = decimalToDMS(-90.0, true);

      // Assert: Verify extreme latitude
      expect(result.reference).toBe('S');
      expect(result.degrees).toBe(90);
      expect(result.minutes).toBe(0);
      expect(result.seconds).toBe(0.0);
    });

    test('handles International Date Line East (180°E)', () => {
      // Act: Convert date line longitude (positive)
      const result = decimalToDMS(180.0, false);

      // Assert: Verify date line handling
      expect(result.reference).toBe('E');
      expect(result.degrees).toBe(180);
      expect(result.minutes).toBe(0);
      expect(result.seconds).toBe(0.0);
    });

    test('handles International Date Line West (-180°W)', () => {
      // Act: Convert date line longitude (negative)
      const result = decimalToDMS(-180.0, false);

      // Assert: Verify date line handling
      expect(result.reference).toBe('W');
      expect(result.degrees).toBe(180);
      expect(result.minutes).toBe(0);
      expect(result.seconds).toBe(0.0);
    });

    test('handles seconds near 60.0 (rounding overflow)', () => {
      // Act: Test coordinate that produces seconds = 59.999...
      // 37 + (46/60) + (59.999/3600) = 37.78333305...
      const testCoord = 37 + (46 / 60) + (59.999 / 3600);
      const result = decimalToDMS(testCoord, true);

      // Assert: Seconds should be < 60 (either carry-over or clamping)
      expect(result.seconds).toBeLessThan(60.0);
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);

      // Either carry-over occurred (minutes=47, seconds~0.0) or clamping (minutes=46, seconds<60)
      if (result.seconds < 1.0) {
        expect(result.minutes).toBe(47);
      } else {
        expect(result.minutes).toBe(46);
        expect(result.seconds).toBeLessThan(60.0);
      }
    });
  });

  describe('input validation', () => {
    test('throws error for latitude > 90°', () => {
      expect(() => decimalToDMS(91.0, true)).toThrow(/latitude.*range/i);
    });

    test('throws error for latitude < -90°', () => {
      expect(() => decimalToDMS(-91.0, true)).toThrow(/latitude.*range/i);
    });

    test('throws error for longitude > 180°', () => {
      expect(() => decimalToDMS(181.0, false)).toThrow(/longitude.*range/i);
    });

    test('throws error for longitude < -180°', () => {
      expect(() => decimalToDMS(-181.0, false)).toThrow(/longitude.*range/i);
    });

    test('throws error for NaN coordinate', () => {
      expect(() => decimalToDMS(NaN, true)).toThrow(/NaN/i);
    });

    test('throws error for Infinity coordinate', () => {
      expect(() => decimalToDMS(Infinity, true)).toThrow(/infinity/i);
    });

    test('throws error for negative Infinity coordinate', () => {
      expect(() => decimalToDMS(-Infinity, true)).toThrow(/infinity/i);
    });

    test('throws error for null coordinate', () => {
      expect(() => decimalToDMS(null as any, true)).toThrow(/null.*undefined/i);
    });

    test('throws error for undefined coordinate', () => {
      expect(() => decimalToDMS(undefined as any, true)).toThrow(/null.*undefined/i);
    });
  });

  describe('parametrized tests', () => {
    test.each([
      [37.7749, true, 37, 'N'],      // San Francisco latitude
      [-33.8688, true, 33, 'S'],     // Sydney latitude
      [151.2093, false, 151, 'E'],   // Sydney longitude
      [-122.4194, false, 122, 'W'],  // San Francisco longitude
      [0.0, true, 0, 'N'],           // Equator
      [0.0, false, 0, 'E'],          // Prime Meridian
      [90.0, true, 90, 'N'],         // North Pole
      [-90.0, true, 90, 'S'],        // South Pole
      [180.0, false, 180, 'E'],      // Date Line East
      [-180.0, false, 180, 'W'],     // Date Line West
    ])(
      'converts %f to correct DMS (%s)',
      (decimal, isLatitude, expectedDegrees, expectedRef) => {
        // Act: Convert decimal to DMS
        const result = decimalToDMS(decimal, isLatitude);

        // Assert: Verify degrees and reference
        expect(result.degrees).toBe(expectedDegrees);
        expect(result.reference).toBe(expectedRef);
        expect(result.minutes).toBeGreaterThanOrEqual(0);
        expect(result.minutes).toBeLessThanOrEqual(59);
        expect(result.seconds).toBeGreaterThanOrEqual(0.0);
        expect(result.seconds).toBeLessThan(60.0);
      }
    );
  });
});

// ============================================================================
// TestDMSToDecimal: Test DMS to decimal conversion
// ============================================================================

describe('dmsToDecimal', () => {
  describe('happy path conversions', () => {
    test('converts North latitude DMS to decimal (San Francisco)', () => {
      // Act: Convert DMS to decimal
      const decimal = dmsToDecimal(37, 46, 29.64, 'N');

      // Assert: Verify decimal conversion
      expect(Math.abs(decimal - 37.7749)).toBeLessThan(0.0001);
    });

    test('converts South latitude DMS to decimal (Sydney)', () => {
      // Act: Convert DMS to decimal
      const decimal = dmsToDecimal(33, 52, 7.68, 'S');

      // Assert: Verify decimal conversion (negative for South)
      expect(Math.abs(decimal - (-33.8688))).toBeLessThan(0.0001);
    });

    test('converts East longitude DMS to decimal (Sydney)', () => {
      // Act: Convert DMS to decimal
      const decimal = dmsToDecimal(151, 12, 33.48, 'E');

      // Assert: Verify decimal conversion
      expect(Math.abs(decimal - 151.2093)).toBeLessThan(0.0001);
    });

    test('converts West longitude DMS to decimal (San Francisco)', () => {
      // Act: Convert DMS to decimal
      const decimal = dmsToDecimal(122, 25, 9.84, 'W');

      // Assert: Verify decimal conversion (negative for West)
      expect(Math.abs(decimal - (-122.4194))).toBeLessThan(0.0001);
    });

    test('converts zero coordinates', () => {
      // Act: Convert zero DMS to decimal
      const latDecimal = dmsToDecimal(0, 0, 0.0, 'N');
      const lonDecimal = dmsToDecimal(0, 0, 0.0, 'E');

      // Assert: Verify zero handling
      expect(latDecimal).toBe(0.0);
      expect(lonDecimal).toBe(0.0);
    });
  });

  describe('input validation', () => {
    test('throws error for invalid reference', () => {
      expect(() => dmsToDecimal(37, 46, 29.64, 'X' as any)).toThrow(/invalid reference/i);
    });

    test('throws error for empty reference', () => {
      expect(() => dmsToDecimal(37, 46, 29.64, '' as any)).toThrow(/invalid reference/i);
    });
  });

  describe('parametrized tests', () => {
    test.each([
      [37, 46, 29.64, 'N', 37.7749],       // San Francisco lat
      [33, 52, 7.68, 'S', -33.8688],       // Sydney lat
      [151, 12, 33.48, 'E', 151.2093],     // Sydney lon
      [122, 25, 9.84, 'W', -122.4194],     // San Francisco lon
      [0, 0, 0.0, 'N', 0.0],               // Zero north
      [0, 0, 0.0, 'E', 0.0],               // Zero east
      [90, 0, 0.0, 'N', 90.0],             // North Pole
      [90, 0, 0.0, 'S', -90.0],            // South Pole
      [180, 0, 0.0, 'E', 180.0],           // Date Line East
      [180, 0, 0.0, 'W', -180.0],          // Date Line West
    ])(
      'converts %d° %d\' %f" %s to %f',
      (degrees, minutes, seconds, ref, expected) => {
        // Act: Convert DMS to decimal
        const decimal = dmsToDecimal(degrees, minutes, seconds, ref as 'N' | 'S' | 'E' | 'W');

        // Assert: Verify conversion
        expect(Math.abs(decimal - expected)).toBeLessThan(0.0001);
      }
    );
  });
});

// ============================================================================
// TestValidateCoordinate: Test coordinate validation
// ============================================================================

describe('validateCoordinate', () => {
  describe('valid coordinates', () => {
    test('accepts valid mid-range latitude', () => {
      const result = validateCoordinate(37.7749, 'latitude');
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    test('accepts valid mid-range longitude', () => {
      const result = validateCoordinate(-122.4194, 'longitude');
      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    test('accepts latitude boundaries (±90°)', () => {
      const northPole = validateCoordinate(90.0, 'latitude');
      const southPole = validateCoordinate(-90.0, 'latitude');

      expect(northPole.isValid).toBe(true);
      expect(southPole.isValid).toBe(true);
    });

    test('accepts longitude boundaries (±180°)', () => {
      const dateLineEast = validateCoordinate(180.0, 'longitude');
      const dateLineWest = validateCoordinate(-180.0, 'longitude');

      expect(dateLineEast.isValid).toBe(true);
      expect(dateLineWest.isValid).toBe(true);
    });
  });

  describe('invalid coordinates', () => {
    test('rejects latitude > 90°', () => {
      const result = validateCoordinate(91.0, 'latitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/latitude.*range/i);
    });

    test('rejects latitude < -90°', () => {
      const result = validateCoordinate(-91.0, 'latitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/latitude.*range/i);
    });

    test('rejects longitude > 180°', () => {
      const result = validateCoordinate(181.0, 'longitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/longitude.*range/i);
    });

    test('rejects longitude < -180°', () => {
      const result = validateCoordinate(-181.0, 'longitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/longitude.*range/i);
    });

    test('rejects NaN coordinate', () => {
      const result = validateCoordinate(NaN, 'latitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/NaN/i);
    });

    test('rejects Infinity coordinate', () => {
      const result = validateCoordinate(Infinity, 'latitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/infinity/i);
    });

    test('rejects null coordinate', () => {
      const result = validateCoordinate(null as any, 'latitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/null.*undefined/i);
    });

    test('rejects undefined coordinate', () => {
      const result = validateCoordinate(undefined as any, 'latitude');
      expect(result.isValid).toBe(false);
      expect(result.error).toMatch(/null.*undefined/i);
    });
  });
});

// ============================================================================
// TestFormatCoordinateDisplay: Test coordinate formatting
// ============================================================================

describe('formatCoordinateDisplay', () => {
  describe('DMS format', () => {
    test('formats North latitude as DMS', () => {
      const formatted = formatCoordinateDisplay(37.7749, true, 'dms');

      expect(formatted).toContain('37°');
      expect(formatted).toContain("46'");
      expect(formatted).toContain('N');
    });

    test('formats West longitude as DMS', () => {
      const formatted = formatCoordinateDisplay(-122.4194, false, 'dms');

      expect(formatted).toContain('122°');
      expect(formatted).toContain("25'");
      expect(formatted).toContain('W');
    });

    test('formats South latitude as DMS', () => {
      const formatted = formatCoordinateDisplay(-33.8688, true, 'dms');

      expect(formatted).toContain('33°');
      expect(formatted).toContain("52'");
      expect(formatted).toContain('S');
    });
  });

  describe('decimal format', () => {
    test('formats North latitude as decimal', () => {
      const formatted = formatCoordinateDisplay(37.7749, true, 'decimal');

      expect(formatted).toContain('37.7749');
      expect(formatted).toContain('°N');
      expect(formatted).not.toContain('-');
    });

    test('formats South latitude as decimal (absolute value with S)', () => {
      const formatted = formatCoordinateDisplay(-33.8688, true, 'decimal');

      expect(formatted).toContain('33.8688');
      expect(formatted).toContain('°S');
      expect(formatted).not.toContain('-');
    });

    test('formats East longitude as decimal', () => {
      const formatted = formatCoordinateDisplay(151.2093, false, 'decimal');

      expect(formatted).toContain('151.2093');
      expect(formatted).toContain('°E');
    });
  });

  describe('short format', () => {
    test('formats North latitude as short', () => {
      const formatted = formatCoordinateDisplay(37.7749, true, 'short');

      expect(formatted).toContain('37.77');
      expect(formatted).toContain('°N');
    });

    test('formats East longitude as short', () => {
      const formatted = formatCoordinateDisplay(151.2093, false, 'short');

      expect(formatted).toContain('151.21');
      expect(formatted).toContain('°E');
    });
  });

  describe('invalid format', () => {
    test('throws error for invalid format type', () => {
      expect(() => formatCoordinateDisplay(37.7749, true, 'invalid' as any)).toThrow(/invalid format/i);
    });
  });

  describe('default format', () => {
    test('uses DMS format by default', () => {
      const formatted = formatCoordinateDisplay(37.7749, true);

      expect(formatted).toContain('°');
      expect(formatted).toContain("'");
      expect(formatted).toContain('"');
      expect(formatted).toContain('N');
    });
  });
});

// ============================================================================
// TestRoundTripAccuracy: Test decimal ↔ DMS conversion accuracy
// ============================================================================

describe('round-trip accuracy', () => {
  describe('decimal → DMS → decimal', () => {
    test.each([
      [37.7749, true],      // San Francisco lat
      [-122.4194, false],   // San Francisco lon
      [-33.8688, true],     // Sydney lat
      [151.2093, false],    // Sydney lon
      [0.0, true],          // Equator
      [0.0, false],         // Prime Meridian
      [90.0, true],         // North Pole
      [-90.0, true],        // South Pole
      [180.0, false],       // Date Line East
      [-180.0, false],      // Date Line West
      [31.5, true],         // Dead Sea lat
      [35.5, false],        // Dead Sea lon
      [27.9881, true],      // Mount Everest lat
      [86.9250, false],     // Mount Everest lon
    ])(
      'round-trip accuracy for %f (%s)',
      (decimal, isLatitude) => {
        // Act: Convert decimal → DMS → decimal
        const dms = decimalToDMS(decimal, isLatitude);
        const decimalResult = dmsToDecimal(dms.degrees, dms.minutes, dms.seconds, dms.reference);

        // Assert: Round-trip accuracy within 0.00001° (~1 meter at equator)
        const precision = 0.00001;
        const error = Math.abs(decimalResult - decimal);
        expect(error).toBeLessThan(precision);
      }
    );
  });
});

// ============================================================================
// TestFormatCoordinatePair: Test coordinate pair formatting
// ============================================================================

describe('formatCoordinatePair', () => {
  describe('format options', () => {
    test('formats San Francisco coordinates as DMS (default)', () => {
      // Act: Format coordinate pair
      const result = formatCoordinatePair(37.7749, -122.4194);

      // Assert: Verify both coordinates are present
      expect(result).toContain('37°');
      expect(result).toContain('N');
      expect(result).toContain('122°');
      expect(result).toContain('W');
    });

    test('formats coordinate pair as decimal', () => {
      // Act: Format coordinate pair
      const result = formatCoordinatePair(37.7749, -122.4194, 'decimal');

      // Assert: Verify decimal format
      expect(result).toContain('°N');
      expect(result).toContain('°W');
    });

    test('formats coordinate pair as short', () => {
      // Act: Format coordinate pair
      const result = formatCoordinatePair(37.7749, -122.4194, 'short');

      // Assert: Verify short format
      expect(result).toContain('N');
      expect(result).toContain('W');
    });
  });

  describe('all hemispheres', () => {
    test('handles all 4 hemisphere combinations', () => {
      // Act: Test all hemisphere combinations
      const neResult = formatCoordinatePair(51.5, 0.1);       // London-ish (NE)
      const seResult = formatCoordinatePair(-33.87, 151.21);  // Sydney (SE)
      const swResult = formatCoordinatePair(-34.6, -58.4);    // Buenos Aires (SW)
      const nwResult = formatCoordinatePair(37.77, -122.42);  // San Francisco (NW)

      // Assert: Verify hemisphere references
      expect(neResult).toContain('N');
      expect(neResult).toContain('E');
      expect(seResult).toContain('S');
      expect(seResult).toContain('E');
      expect(swResult).toContain('S');
      expect(swResult).toContain('W');
      expect(nwResult).toContain('N');
      expect(nwResult).toContain('W');
    });
  });

  describe('edge cases', () => {
    test('handles Null Island, North Pole, and South Pole', () => {
      // Act: Test edge cases
      const nullIsland = formatCoordinatePair(0.0, 0.0);
      const northPole = formatCoordinatePair(90.0, 0.0);
      const southPole = formatCoordinatePair(-90.0, 0.0);

      // Assert: Should not crash and should have valid format
      expect(nullIsland).toBeTruthy();
      expect(northPole).toContain('N');
      expect(southPole).toContain('S');
    });
  });

  describe('input validation', () => {
    test('throws error for invalid latitude (> 90°)', () => {
      expect(() => formatCoordinatePair(91.0, 0.0)).toThrow(/latitude/i);
    });

    test('throws error for invalid longitude (> 180°)', () => {
      expect(() => formatCoordinatePair(0.0, 181.0)).toThrow(/longitude/i);
    });
  });
});

// ============================================================================
// TestPrecisionControl: Test configurable precision for DMS seconds
// ============================================================================

describe('precision control', () => {
  describe('decimalToDMS with seconds precision', () => {
    test('precision=0 (whole seconds, ±30m accuracy)', () => {
      // Act: Convert with precision=0
      const result = decimalToDMS(37.7749, true, 0);

      // Assert: Seconds should be whole number
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);
      expect(result.minutes).toBe(46);
      expect(Number.isInteger(result.seconds)).toBe(true);
      expect(result.seconds).toBeGreaterThanOrEqual(29);
      expect(result.seconds).toBeLessThanOrEqual(30);
    });

    test('precision=1 (1 decimal place, ±3m accuracy)', () => {
      // Act: Convert with precision=1
      const result = decimalToDMS(37.7749, true, 1);

      // Assert: Verify 1 decimal place
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);
      expect(result.minutes).toBe(46);
      expect(Math.abs(result.seconds - 29.6)).toBeLessThan(0.05);
    });

    test('precision=2 (2 decimal places, ±30cm accuracy) - DEFAULT', () => {
      // Act: Convert with default precision (should be 2)
      const result = decimalToDMS(37.7749, true);

      // Assert: Verify 2 decimal places (default behavior)
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);
      expect(result.minutes).toBe(46);
      expect(Math.abs(result.seconds - 29.64)).toBeLessThan(0.01);
    });

    test('precision=4 (4 decimal places, ±3mm accuracy)', () => {
      // Act: Convert with precision=4
      const result = decimalToDMS(37.7749, true, 4);

      // Assert: Verify 4 decimal places
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);
      expect(result.minutes).toBe(46);
      expect(Math.abs(result.seconds - 29.64)).toBeLessThan(0.0001);
    });

    test('precision=6 (6 decimal places, ±0.03mm accuracy) - MAXIMUM', () => {
      // Act: Convert with precision=6
      const result = decimalToDMS(37.7749, true, 6);

      // Assert: Verify 6 decimal places
      expect(result.reference).toBe('N');
      expect(result.degrees).toBe(37);
      expect(result.minutes).toBe(46);
      expect(Math.abs(result.seconds - 29.64)).toBeLessThan(0.000001);
    });

    test('throws error for negative precision', () => {
      expect(() => decimalToDMS(37.7749, true, -1)).toThrow(/secondsPrecision.*range/i);
    });

    test('throws error for precision > 6', () => {
      expect(() => decimalToDMS(37.7749, true, 7)).toThrow(/secondsPrecision.*range/i);
    });

    test('throws error for non-integer precision', () => {
      expect(() => decimalToDMS(37.7749, true, 2.5)).toThrow(/secondsPrecision/i);
    });

    test.each([
      [0, 29, 30],           // ±30m accuracy
      [1, 29.6, 29.7],       // ±3m accuracy
      [2, 29.63, 29.65],     // ±30cm accuracy
      [3, 29.639, 29.641],   // ±3cm accuracy
      [4, 29.6399, 29.6401], // ±3mm accuracy
    ])(
      'precision=%i produces seconds in range [%f, %f]',
      (precision, expectedMin, expectedMax) => {
        // Act: Convert with specified precision
        const result = decimalToDMS(37.7749, true, precision);

        // Assert: Verify seconds in expected range
        expect(result.seconds).toBeGreaterThanOrEqual(expectedMin);
        expect(result.seconds).toBeLessThanOrEqual(expectedMax);
      }
    );
  });

  describe('formatCoordinateDisplay with precision', () => {
    test('formats with different precision values', () => {
      // Act: Format with different precisions
      const fmt0 = formatCoordinateDisplay(37.7749, true, 'dms', 0);
      const fmt2 = formatCoordinateDisplay(37.7749, true, 'dms', 2);
      const fmt4 = formatCoordinateDisplay(37.7749, true, 'dms', 4);

      // Assert: Verify different format strings
      expect(fmt0).toContain("37°46'");
      expect(fmt0).toContain('"N');
      expect(fmt2).toContain("37°46'");
      expect(fmt2).toContain('"N');
      expect(fmt4).toContain("37°46'");
      expect(fmt4).toContain('"N');

      // Verify precision affects decimal places in output
      // precision=0: "30\"N" or "29\"N"
      expect(fmt0).toMatch(/\d+"N/);
      // precision=2: "29.64\"N"
      expect(fmt2).toMatch(/\d+\.\d{2}"N/);
      // precision=4: "29.6400\"N"
      expect(fmt4).toMatch(/\d+\.\d{4}"N/);
    });

    test('precision only affects DMS format, not decimal or short', () => {
      // Act: Format with different formats
      const dms = formatCoordinateDisplay(37.7749, true, 'dms', 4);
      const decimal = formatCoordinateDisplay(37.7749, true, 'decimal', 4);
      const short = formatCoordinateDisplay(37.7749, true, 'short', 4);

      // Assert: DMS should be affected, others should not
      expect(dms).toContain("37°46'");
      expect(decimal).toContain('37.774900°N'); // Always 6 decimal places
      expect(short).toContain('37.77°N'); // Always 2 decimal places
    });
  });

  describe('formatCoordinatePair with precision', () => {
    test('formats coordinate pair with custom precision', () => {
      // Act: Format with precision=4
      const result = formatCoordinatePair(37.7749, -122.4194, 'dms', 4);

      // Assert: Verify both coordinates present
      expect(result).toContain("37°46'");
      expect(result).toContain("122°25'");
      expect(result).toContain('N');
      expect(result).toContain('W');

      // Verify 4 decimal places in seconds
      expect(result).toMatch(/\d+\.\d{4}"/);
    });

    test('uses default precision=2 when not specified', () => {
      // Act: Format without precision parameter
      const result = formatCoordinatePair(37.7749, -122.4194);

      // Assert: Should use default precision=2
      expect(result).toContain("37°46'");
      expect(result).toMatch(/\d+\.\d{2}"/); // 2 decimal places
    });
  });
});
