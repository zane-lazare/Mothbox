/**
 * Cluster Utilities for Map-Lightbox Integration
 *
 * This module provides utilities for extracting photo lists from cluster markers
 * for navigation in the lightbox component. It handles cluster markers from
 * react-leaflet-cluster and ensures consistent photo ordering.
 *
 * Key functions:
 * - extractPhotosFromCluster: Extract all photos from a cluster marker
 * - findPhotoIndexInCluster: Find the index of a specific photo in a cluster
 * - sortPhotosByTimestamp: Sort photos by timestamp in ascending order
 *
 * Usage:
 * ```javascript
 * import { extractPhotosFromCluster, findPhotoIndexInCluster } from './clusterUtils'
 *
 * // Extract photos from cluster marker
 * const photos = extractPhotosFromCluster(clusterMarker)
 *
 * // Find index of specific photo
 * const index = findPhotoIndexInCluster(photos, '2024-11-10/photo_001.jpg')
 * ```
 */

/**
 * Extract all photos from a cluster marker.
 *
 * Recursively extracts photos from cluster markers, including nested clusters
 * (spiderfied clusters). Photos are automatically sorted by timestamp.
 *
 * @param {Object} clusterMarker - Leaflet cluster marker with getAllChildMarkers method
 * @returns {Array} Array of photo objects sorted by timestamp (ascending)
 *
 * @example
 * const photos = extractPhotosFromCluster(clusterMarker)
 * // Returns: [{ filename, path, latitude, longitude, timestamp }, ...]
 */
export function extractPhotosFromCluster(clusterMarker) {
  // Handle null/undefined
  if (!clusterMarker) {
    return []
  }

  // Check if marker has getAllChildMarkers method (cluster marker)
  if (typeof clusterMarker.getAllChildMarkers !== 'function') {
    return []
  }

  // Get all child markers from cluster
  const childMarkers = clusterMarker.getAllChildMarkers()

  if (!childMarkers || childMarkers.length === 0) {
    return []
  }

  // Extract photo data from markers (handle nested clusters recursively)
  const photos = []

  for (const marker of childMarkers) {
    // Check if this is a nested cluster
    if (typeof marker.getAllChildMarkers === 'function') {
      // Recursively extract photos from nested cluster
      const nestedPhotos = extractPhotosFromCluster(marker)
      photos.push(...nestedPhotos)
    } else if (marker.options && typeof marker.options === 'object') {
      // Extract photo data from marker options
      // Validate that we have at least some photo data
      if (marker.options.filename || marker.options.path) {
        photos.push({ ...marker.options })
      }
    }
  }

  // Sort photos by timestamp before returning
  return sortPhotosByTimestamp(photos)
}

/**
 * Find the index of a specific photo in a cluster by path.
 *
 * Performs case-sensitive exact path matching to locate the photo.
 * Returns the first occurrence if duplicate paths exist.
 *
 * @param {Array} photos - Array of photo objects
 * @param {string} photoPath - Photo path to search for
 * @returns {number} Index of photo in array, or -1 if not found
 *
 * @example
 * const index = findPhotoIndexInCluster(photos, '2024-11-10/photo_001.jpg')
 * // Returns: 0 (if photo is first in array)
 */
export function findPhotoIndexInCluster(photos, photoPath) {
  // Handle null/undefined inputs
  if (!photos || !photoPath) {
    return -1
  }

  // Handle non-array photos
  if (!Array.isArray(photos)) {
    return -1
  }

  // Find index by exact path match
  return photos.findIndex((photo) => photo && photo.path === photoPath)
}

/**
 * Sort photos by timestamp in ascending order (earliest first).
 *
 * Creates a copy of the array and sorts by timestamp. Photos without
 * timestamps or with invalid timestamps are placed at the end.
 * Uses stable sort to maintain relative order for equal timestamps.
 *
 * @param {Array} photos - Array of photo objects
 * @returns {Array} New sorted array (does not mutate original)
 *
 * @example
 * const sorted = sortPhotosByTimestamp(photos)
 * // Returns: Photos sorted by timestamp ascending
 */
export function sortPhotosByTimestamp(photos) {
  // Handle null/undefined
  if (!photos) {
    return []
  }

  // Handle non-array
  if (!Array.isArray(photos)) {
    return []
  }

  // Handle empty array
  if (photos.length === 0) {
    return []
  }

  // Create copy to avoid mutating original
  const photosCopy = [...photos]

  // Sort by timestamp (ascending)
  photosCopy.sort((a, b) => {
    const timestampA = a?.timestamp
    const timestampB = b?.timestamp

    // Handle missing/invalid timestamps
    const isValidA = isValidTimestamp(timestampA)
    const isValidB = isValidTimestamp(timestampB)

    // Photos without valid timestamps go to end
    if (!isValidA && !isValidB) {
      return 0 // Maintain relative order
    }
    if (!isValidA) {
      return 1 // a goes after b
    }
    if (!isValidB) {
      return -1 // b goes after a
    }

    // Both valid - convert to numbers and compare
    const numA = Number(timestampA)
    const numB = Number(timestampB)

    return numA - numB
  })

  return photosCopy
}

/**
 * Check if a timestamp value is valid.
 *
 * @private
 * @param {*} timestamp - Timestamp value to validate
 * @returns {boolean} True if timestamp is valid number
 */
function isValidTimestamp(timestamp) {
  // Reject null/undefined
  if (timestamp === null || timestamp === undefined) {
    return false
  }

  // Convert to number
  const num = Number(timestamp)

  // Check if it's a valid number (not NaN, not Infinity)
  return Number.isFinite(num)
}
