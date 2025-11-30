/**
 * Generates a thumbnail URL for a photo path.
 * Centralizes URL encoding and construction for consistency.
 *
 * @param {string} path - Photo path (relative from PHOTOS_DIR)
 * @param {number} [size] - Optional thumbnail size in pixels
 * @returns {string} Encoded thumbnail URL
 */
export function getThumbnailUrl(path, size = null) {
  const encoded = encodeURIComponent(path || '')
  return size
    ? `/api/gallery/thumbnail/${encoded}?size=${size}`
    : `/api/gallery/thumbnail/${encoded}`
}
