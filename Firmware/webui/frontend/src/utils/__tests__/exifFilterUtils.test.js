import { describe, it, expect } from 'vitest';
import {
  parseIso,
  parseAperture,
  parseShutterSpeed,
  shutterSpeedToSeconds,
  filterByIso,
  filterByAperture,
  filterByShutterSpeed,
  filterPhotosByExif,
} from '../exifFilterUtils';

describe('parseIso', () => {
  it('should parse integer ISO value', () => {
    expect(parseIso(400)).toBe(400);
    expect(parseIso(100)).toBe(100);
    expect(parseIso(3200)).toBe(3200);
  });

  it('should parse string ISO value', () => {
    expect(parseIso('400')).toBe(400);
    expect(parseIso('100')).toBe(100);
    expect(parseIso('3200')).toBe(3200);
  });

  it('should return null for invalid ISO', () => {
    expect(parseIso('invalid')).toBe(null);
    expect(parseIso('abc')).toBe(null);
    expect(parseIso(NaN)).toBe(null);
  });

  it('should handle undefined', () => {
    expect(parseIso(undefined)).toBe(null);
  });

  it('should handle null', () => {
    expect(parseIso(null)).toBe(null);
  });
});

describe('parseAperture', () => {
  it('should parse f/2.8 format', () => {
    expect(parseAperture('f/2.8')).toBe(2.8);
    expect(parseAperture('F/5.6')).toBe(5.6);
    expect(parseAperture('f/1.4')).toBe(1.4);
  });

  it('should parse numeric aperture without prefix', () => {
    expect(parseAperture('2.8')).toBe(2.8);
    expect(parseAperture('5.6')).toBe(5.6);
    expect(parseAperture(2.8)).toBe(2.8);
  });

  it('should return null for invalid aperture', () => {
    expect(parseAperture('invalid')).toBe(null);
    expect(parseAperture('f/abc')).toBe(null);
    expect(parseAperture(NaN)).toBe(null);
  });

  it('should handle undefined', () => {
    expect(parseAperture(undefined)).toBe(null);
  });

  it('should handle null', () => {
    expect(parseAperture(null)).toBe(null);
  });

  it('should handle aperture with whitespace', () => {
    expect(parseAperture('  f/2.8  ')).toBe(2.8);
    expect(parseAperture('  5.6  ')).toBe(5.6);
  });
});

describe('shutterSpeedToSeconds', () => {
  it('should parse fraction format (1/500)', () => {
    expect(shutterSpeedToSeconds('1/500')).toBe(1/500);
    expect(shutterSpeedToSeconds('1/250')).toBe(1/250);
    expect(shutterSpeedToSeconds('1/60')).toBe(1/60);
  });

  it('should parse decimal string', () => {
    expect(shutterSpeedToSeconds('0.5')).toBe(0.5);
    expect(shutterSpeedToSeconds('0.002')).toBe(0.002);
  });

  it('should parse whole number string as seconds', () => {
    expect(shutterSpeedToSeconds('2')).toBe(2);
    expect(shutterSpeedToSeconds('5')).toBe(5);
    expect(shutterSpeedToSeconds('10')).toBe(10);
  });

  it('should parse 1/2 as 0.5', () => {
    expect(shutterSpeedToSeconds('1/2')).toBe(0.5);
  });

  it('should handle numeric values', () => {
    expect(shutterSpeedToSeconds(0.5)).toBe(0.5);
    expect(shutterSpeedToSeconds(2)).toBe(2);
    expect(shutterSpeedToSeconds(1/500)).toBeCloseTo(0.002, 5);
  });

  it('should return null for invalid format', () => {
    expect(shutterSpeedToSeconds('invalid')).toBe(null);
    expect(shutterSpeedToSeconds('1/0')).toBe(null);
    expect(shutterSpeedToSeconds('abc/def')).toBe(null);
  });

  it('should handle undefined', () => {
    expect(shutterSpeedToSeconds(undefined)).toBe(null);
  });

  it('should handle null', () => {
    expect(shutterSpeedToSeconds(null)).toBe(null);
  });

  it('should handle NaN', () => {
    expect(shutterSpeedToSeconds(NaN)).toBe(null);
  });

  it('should handle malformed fractions', () => {
    expect(shutterSpeedToSeconds('1/2/3')).toBe(null);
    expect(shutterSpeedToSeconds('/')).toBe(null);
  });
});

describe('parseShutterSpeed', () => {
  it('should be an alias for shutterSpeedToSeconds', () => {
    expect(parseShutterSpeed('1/500')).toBe(shutterSpeedToSeconds('1/500'));
    expect(parseShutterSpeed('0.5')).toBe(shutterSpeedToSeconds('0.5'));
    expect(parseShutterSpeed(2)).toBe(shutterSpeedToSeconds(2));
  });
});

describe('filterByIso', () => {
  const photos = [
    { path: 'photo1.jpg', exif: { iso: 100 } },
    { path: 'photo2.jpg', exif: { iso: 400 } },
    { path: 'photo3.jpg', exif: { iso: 800 } },
    { path: 'photo4.jpg', exif: { iso: 1600 } },
    { path: 'photo5.jpg', exif: { iso: '200' } }, // String ISO
    { path: 'photo6.jpg', exif: {} }, // No ISO
    { path: 'photo7.jpg' }, // No EXIF
  ];

  it('should filter photos within ISO range', () => {
    const filtered = filterByIso(photos, { min: 200, max: 800 });
    expect(filtered).toHaveLength(3);
    expect(filtered.map(p => p.path)).toEqual(['photo2.jpg', 'photo3.jpg', 'photo5.jpg']);
  });

  it('should filter with min only', () => {
    const filtered = filterByIso(photos, { min: 800, max: null });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo3.jpg', 'photo4.jpg']);
  });

  it('should filter with max only', () => {
    const filtered = filterByIso(photos, { min: null, max: 400 });
    expect(filtered).toHaveLength(3);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg', 'photo5.jpg']);
  });

  it('should return all photos when both min and max are null', () => {
    const filtered = filterByIso(photos, { min: null, max: null });
    expect(filtered).toHaveLength(7);
  });

  it('should exclude photos without ISO when filter is set', () => {
    const filtered = filterByIso(photos, { min: 100, max: 1600 });
    expect(filtered).toHaveLength(5);
    expect(filtered.map(p => p.path)).not.toContain('photo6.jpg');
    expect(filtered.map(p => p.path)).not.toContain('photo7.jpg');
  });

  it('should return all photos when range is null', () => {
    const filtered = filterByIso(photos, null);
    expect(filtered).toHaveLength(7);
  });

  it('should return all photos when range is undefined', () => {
    const filtered = filterByIso(photos, undefined);
    expect(filtered).toHaveLength(7);
  });

  it('should handle empty photo array', () => {
    const filtered = filterByIso([], { min: 100, max: 800 });
    expect(filtered).toHaveLength(0);
  });
});

describe('filterByAperture', () => {
  const photos = [
    { path: 'photo1.jpg', exif: { aperture: 1.4 } },
    { path: 'photo2.jpg', exif: { aperture: 2.8 } },
    { path: 'photo3.jpg', exif: { aperture: 'f/5.6' } }, // String aperture
    { path: 'photo4.jpg', exif: { aperture: 8 } },
    { path: 'photo5.jpg', exif: {} }, // No aperture
    { path: 'photo6.jpg' }, // No EXIF
  ];

  it('should filter photos within aperture range', () => {
    const filtered = filterByAperture(photos, { min: 2.8, max: 8 });
    expect(filtered).toHaveLength(3);
    expect(filtered.map(p => p.path)).toEqual(['photo2.jpg', 'photo3.jpg', 'photo4.jpg']);
  });

  it('should filter with min only', () => {
    const filtered = filterByAperture(photos, { min: 5.6, max: null });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo3.jpg', 'photo4.jpg']);
  });

  it('should filter with max only', () => {
    const filtered = filterByAperture(photos, { min: null, max: 2.8 });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg']);
  });

  it('should return all photos when both min and max are null', () => {
    const filtered = filterByAperture(photos, { min: null, max: null });
    expect(filtered).toHaveLength(6);
  });

  it('should exclude photos without aperture when filter is set', () => {
    const filtered = filterByAperture(photos, { min: 1.4, max: 8 });
    expect(filtered).toHaveLength(4);
    expect(filtered.map(p => p.path)).not.toContain('photo5.jpg');
    expect(filtered.map(p => p.path)).not.toContain('photo6.jpg');
  });

  it('should return all photos when range is null', () => {
    const filtered = filterByAperture(photos, null);
    expect(filtered).toHaveLength(6);
  });
});

describe('filterByShutterSpeed', () => {
  const photos = [
    { path: 'photo1.jpg', exif: { shutter_speed: '1/500' } },
    { path: 'photo2.jpg', exif: { shutter_speed: '1/250' } },
    { path: 'photo3.jpg', exif: { shutter_speed: '1/60' } },
    { path: 'photo4.jpg', exif: { shutter_speed: '0.5' } }, // Decimal
    { path: 'photo5.jpg', exif: { shutter_speed: 2 } }, // Numeric
    { path: 'photo6.jpg', exif: {} }, // No shutter speed
    { path: 'photo7.jpg' }, // No EXIF
  ];

  it('should filter photos within shutter speed range', () => {
    const filtered = filterByShutterSpeed(photos, { min: '1/500', max: '1/60' });
    expect(filtered).toHaveLength(3);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg', 'photo3.jpg']);
  });

  it('should filter with min only', () => {
    const filtered = filterByShutterSpeed(photos, { min: '1/60', max: null });
    expect(filtered).toHaveLength(3);
    expect(filtered.map(p => p.path)).toEqual(['photo3.jpg', 'photo4.jpg', 'photo5.jpg']);
  });

  it('should filter with max only', () => {
    const filtered = filterByShutterSpeed(photos, { min: null, max: '1/250' });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg']);
  });

  it('should return all photos when both min and max are null', () => {
    const filtered = filterByShutterSpeed(photos, { min: null, max: null });
    expect(filtered).toHaveLength(7);
  });

  it('should exclude photos without shutter speed when filter is set', () => {
    const filtered = filterByShutterSpeed(photos, { min: '1/500', max: 2 });
    expect(filtered).toHaveLength(5);
    expect(filtered.map(p => p.path)).not.toContain('photo6.jpg');
    expect(filtered.map(p => p.path)).not.toContain('photo7.jpg');
  });

  it('should handle numeric range values', () => {
    const filtered = filterByShutterSpeed(photos, { min: 0.002, max: 0.5 });
    expect(filtered).toHaveLength(4);
  });

  it('should return all photos when range is null', () => {
    const filtered = filterByShutterSpeed(photos, null);
    expect(filtered).toHaveLength(7);
  });
});

describe('filterPhotosByExif', () => {
  const photos = [
    {
      path: 'photo1.jpg',
      exif: { iso: 100, aperture: 2.8, shutter_speed: '1/500' }
    },
    {
      path: 'photo2.jpg',
      exif: { iso: 400, aperture: 5.6, shutter_speed: '1/250' }
    },
    {
      path: 'photo3.jpg',
      exif: { iso: 800, aperture: 8, shutter_speed: '1/60' }
    },
    {
      path: 'photo4.jpg',
      exif: { iso: 1600, aperture: 1.4, shutter_speed: '1/1000' }
    },
    {
      path: 'photo5.jpg',
      exif: { iso: 200 } // Partial EXIF
    },
    {
      path: 'photo6.jpg',
      exif: {} // Empty EXIF
    },
    {
      path: 'photo7.jpg' // No EXIF
    },
  ];

  it('should return all photos when no filters are set', () => {
    const filtered = filterPhotosByExif(photos, {});
    expect(filtered).toHaveLength(7);
  });

  it('should filter by ISO only', () => {
    const filtered = filterPhotosByExif(photos, {
      iso: { min: 400, max: 800 }
    });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo2.jpg', 'photo3.jpg']);
  });

  it('should filter by aperture only', () => {
    const filtered = filterPhotosByExif(photos, {
      aperture: { min: 2.8, max: 5.6 }
    });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg']);
  });

  it('should filter by shutter speed only', () => {
    const filtered = filterPhotosByExif(photos, {
      shutterSpeed: { min: '1/500', max: '1/250' }
    });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg']);
  });

  it('should combine all filters with AND logic', () => {
    const filtered = filterPhotosByExif(photos, {
      iso: { min: 100, max: 800 },
      aperture: { min: 2.8, max: 8 },
      shutterSpeed: { min: '1/500', max: '1/60' }
    });
    expect(filtered).toHaveLength(3);
    expect(filtered.map(p => p.path)).toEqual(['photo1.jpg', 'photo2.jpg', 'photo3.jpg']);
  });

  it('should handle photos with missing EXIF fields', () => {
    const filtered = filterPhotosByExif(photos, {
      iso: { min: 100, max: 1600 },
      aperture: { min: 1.4, max: 8 }
    });
    // photo5 has ISO but no aperture, should be excluded
    expect(filtered).toHaveLength(4);
    expect(filtered.map(p => p.path)).not.toContain('photo5.jpg');
  });

  it('should return empty array for null photos', () => {
    const filtered = filterPhotosByExif(null, {});
    expect(filtered).toEqual([]);
  });

  it('should return empty array for undefined photos', () => {
    const filtered = filterPhotosByExif(undefined, {});
    expect(filtered).toEqual([]);
  });

  it('should return all photos when cameraSettings is null', () => {
    const filtered = filterPhotosByExif(photos, null);
    expect(filtered).toHaveLength(7);
  });

  it('should return all photos when cameraSettings is undefined', () => {
    const filtered = filterPhotosByExif(photos, undefined);
    expect(filtered).toHaveLength(7);
  });

  it('should handle multiple filters with some null ranges', () => {
    const filtered = filterPhotosByExif(photos, {
      iso: { min: 400, max: null }, // min only
      aperture: { min: null, max: null }, // no filter
      shutterSpeed: { min: null, max: '1/250' } // max only
    });
    expect(filtered).toHaveLength(2);
    expect(filtered.map(p => p.path)).toEqual(['photo2.jpg', 'photo4.jpg']);
  });

  it('should handle empty photo array', () => {
    const filtered = filterPhotosByExif([], {
      iso: { min: 100, max: 800 }
    });
    expect(filtered).toHaveLength(0);
  });

  it('should handle strict filtering that returns no results', () => {
    const filtered = filterPhotosByExif(photos, {
      iso: { min: 10000, max: 20000 } // Unrealistic range
    });
    expect(filtered).toHaveLength(0);
  });

  it('should return all photos when all filters have null ranges', () => {
    const filtered = filterPhotosByExif(photos, {
      iso: { min: null, max: null },
      aperture: { min: null, max: null },
      shutterSpeed: { min: null, max: null }
    });
    expect(filtered).toHaveLength(7);
  });
});
