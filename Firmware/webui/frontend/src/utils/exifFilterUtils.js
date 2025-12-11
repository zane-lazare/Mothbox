/**
 * EXIF Filter Utilities
 *
 * Client-side filtering of photos based on camera settings (ISO, aperture, shutter speed).
 * Handles various EXIF data formats and missing values gracefully.
 */

/**
 * Parse ISO value from EXIF data
 * @param {string|number|undefined} exifValue - Raw EXIF ISO value
 * @returns {number|null} Parsed ISO number or null if invalid
 */
export function parseIso(exifValue) {
  if (exifValue === undefined || exifValue === null) {
    return null;
  }

  // Handle numeric values
  if (typeof exifValue === 'number') {
    return isNaN(exifValue) ? null : exifValue;
  }

  // Handle string values
  if (typeof exifValue === 'string') {
    const parsed = parseInt(exifValue, 10);
    return isNaN(parsed) ? null : parsed;
  }

  return null;
}

/**
 * Parse aperture (f-number) from EXIF data
 * @param {string|number|undefined} exifValue - Raw EXIF aperture value (e.g., "f/2.8", "2.8", 2.8)
 * @returns {number|null} Parsed f-number or null if invalid
 */
export function parseAperture(exifValue) {
  if (exifValue === undefined || exifValue === null) {
    return null;
  }

  // Handle numeric values
  if (typeof exifValue === 'number') {
    return isNaN(exifValue) ? null : exifValue;
  }

  // Handle string values
  if (typeof exifValue === 'string') {
    // Trim whitespace first, then strip "f/" prefix if present
    const cleaned = exifValue.trim().replace(/^f\//i, '');
    const parsed = parseFloat(cleaned);
    return isNaN(parsed) ? null : parsed;
  }

  return null;
}

/**
 * Convert shutter speed to decimal seconds
 * @param {string|number} value - Shutter speed in various formats ("1/500", "0.5", "2", 1/500, 0.5)
 * @returns {number|null} Shutter speed in seconds or null if invalid
 */
export function shutterSpeedToSeconds(value) {
  if (value === undefined || value === null) {
    return null;
  }

  // Handle numeric values
  if (typeof value === 'number') {
    return isNaN(value) ? null : value;
  }

  // Handle string values
  if (typeof value === 'string') {
    const trimmed = value.trim();

    // Handle fraction format (e.g., "1/500")
    if (trimmed.includes('/')) {
      const parts = trimmed.split('/');
      if (parts.length !== 2) {
        return null;
      }

      const numerator = parseFloat(parts[0]);
      const denominator = parseFloat(parts[1]);

      if (isNaN(numerator) || isNaN(denominator) || denominator === 0) {
        return null;
      }

      return numerator / denominator;
    }

    // Handle decimal string (e.g., "0.5", "2")
    const parsed = parseFloat(trimmed);
    return isNaN(parsed) ? null : parsed;
  }

  return null;
}

/**
 * Parse shutter speed from EXIF data
 * Alias for shutterSpeedToSeconds for consistency with other parse functions
 * @param {string|number|undefined} exifValue - Raw EXIF shutter speed value
 * @returns {number|null} Shutter speed in seconds or null if invalid
 */
export function parseShutterSpeed(exifValue) {
  return shutterSpeedToSeconds(exifValue);
}

/**
 * Filter photos by ISO range
 * @param {Array} photos - Array of photo objects with EXIF data
 * @param {Object} range - ISO range { min: number|null, max: number|null }
 * @returns {Array} Filtered photos
 */
export function filterByIso(photos, range) {
  if (!range || (range.min === null && range.max === null)) {
    return photos;
  }

  return photos.filter(photo => {
    // If no EXIF data at all, exclude if filter is set
    if (!photo.exif) {
      return false;
    }

    const iso = parseIso(photo.exif.iso);

    // If photo has no ISO but filter is set, exclude
    if (iso === null) {
      return false;
    }

    // Apply min filter
    if (range.min !== null && iso < range.min) {
      return false;
    }

    // Apply max filter
    if (range.max !== null && iso > range.max) {
      return false;
    }

    return true;
  });
}

/**
 * Filter photos by aperture range
 * @param {Array} photos - Array of photo objects with EXIF data
 * @param {Object} range - Aperture range { min: number|null, max: number|null }
 * @returns {Array} Filtered photos
 */
export function filterByAperture(photos, range) {
  if (!range || (range.min === null && range.max === null)) {
    return photos;
  }

  return photos.filter(photo => {
    // If no EXIF data at all, exclude if filter is set
    if (!photo.exif) {
      return false;
    }

    const aperture = parseAperture(photo.exif.aperture);

    // If photo has no aperture but filter is set, exclude
    if (aperture === null) {
      return false;
    }

    // Apply min filter
    if (range.min !== null && aperture < range.min) {
      return false;
    }

    // Apply max filter
    if (range.max !== null && aperture > range.max) {
      return false;
    }

    return true;
  });
}

/**
 * Filter photos by shutter speed range
 * @param {Array} photos - Array of photo objects with EXIF data
 * @param {Object} range - Shutter speed range { min: string|number|null, max: string|number|null }
 * @returns {Array} Filtered photos
 */
export function filterByShutterSpeed(photos, range) {
  if (!range || (range.min === null && range.max === null)) {
    return photos;
  }

  // Convert range values to seconds for comparison
  const minSeconds = range.min !== null ? shutterSpeedToSeconds(range.min) : null;
  const maxSeconds = range.max !== null ? shutterSpeedToSeconds(range.max) : null;

  return photos.filter(photo => {
    // If no EXIF data at all, exclude if filter is set
    if (!photo.exif) {
      return false;
    }

    const shutterSpeed = parseShutterSpeed(photo.exif.shutter_speed);

    // If photo has no shutter speed but filter is set, exclude
    if (shutterSpeed === null) {
      return false;
    }

    // Apply min filter (note: smaller value = faster shutter speed)
    if (minSeconds !== null && shutterSpeed < minSeconds) {
      return false;
    }

    // Apply max filter
    if (maxSeconds !== null && shutterSpeed > maxSeconds) {
      return false;
    }

    return true;
  });
}

/**
 * Filter photos by camera settings (ISO, aperture, shutter speed)
 * @param {Array} photos - Array of photo objects with EXIF data
 * @param {Object} cameraSettings - Camera settings filters
 * @param {Object} cameraSettings.iso - ISO range { min: number|null, max: number|null }
 * @param {Object} cameraSettings.aperture - Aperture range { min: number|null, max: number|null }
 * @param {Object} cameraSettings.shutterSpeed - Shutter speed range { min: string|number|null, max: string|number|null }
 * @returns {Array} Filtered photos matching all criteria (AND logic)
 */
export function filterPhotosByExif(photos, cameraSettings) {
  if (!photos || !Array.isArray(photos)) {
    return [];
  }

  // If no camera settings provided, return all photos
  if (!cameraSettings) {
    return photos;
  }

  let filtered = photos;

  // Apply ISO filter
  if (cameraSettings.iso) {
    filtered = filterByIso(filtered, cameraSettings.iso);
  }

  // Apply aperture filter
  if (cameraSettings.aperture) {
    filtered = filterByAperture(filtered, cameraSettings.aperture);
  }

  // Apply shutter speed filter
  if (cameraSettings.shutterSpeed) {
    filtered = filterByShutterSpeed(filtered, cameraSettings.shutterSpeed);
  }

  return filtered;
}
