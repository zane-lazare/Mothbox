/**
 * Thumbnail URL builder utility
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

/**
 * Constructs a thumbnail URL for a given photo path
 * @param path - The file path of the photo
 * @returns The complete thumbnail URL
 */
export function getThumbnailUrl(path: string): string {
  if (!path) return ''
  return `${API_BASE_URL}/photos/thumbnail?path=${encodeURIComponent(path)}`
}

/**
 * Constructs a full-size photo URL for a given photo path
 * @param path - The file path of the photo
 * @returns The complete photo URL
 */
export function getPhotoUrl(path: string): string {
  if (!path) return ''
  return `${API_BASE_URL}/photos/full?path=${encodeURIComponent(path)}`
}
