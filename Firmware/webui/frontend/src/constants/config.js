/**
 * UI Configuration Constants
 *
 * Centralized configuration for frontend UI behavior and settings.
 * Modify these values to adjust the user experience without searching through code.
 *
 * @module constants/config
 */

/**
 * Gallery component configuration
 *
 * @property {number} PAGE_SIZE - Number of photos to load per page in infinite scroll
 *   - Should be a multiple of grid column counts for clean layout
 *   - Current: 12 = 6 rows mobile (2 cols), 3 rows medium (4 cols), 2 rows large (6 cols)
 *   - Alternative: 24 for faster scrolling (12/6/4 rows respectively)
 *
 * @property {number} SKELETON_COUNT - Number of skeleton loaders to show while fetching
 *   - Should match PAGE_SIZE for consistent visual experience
 *
 * @property {Object} GRID_COLUMNS - Responsive grid configuration (matches Tailwind breakpoints)
 *   - mobile: 2 columns (default, <768px)
 *   - medium: 4 columns (md breakpoint, ≥768px)
 *   - large: 6 columns (lg breakpoint, ≥1024px)
 *
 * @property {Object} INFINITE_SCROLL - Infinite scroll behavior configuration
 *   - THRESHOLD: IntersectionObserver threshold (0.0-1.0) - when to trigger loading
 *   - ROOT_MARGIN: Distance before sentinel to start loading (px)
 *   - SENTINEL_HEIGHT: Height of scroll sentinel element (Tailwind class)
 *
 * @property {Object} LAYOUT - Visual layout configuration
 *   - PHOTO_HEIGHT: Photo card height (Tailwind class)
 *   - GRID_GAP: Spacing between grid items (Tailwind class)
 */
export const GALLERY_CONFIG = {
  PAGE_SIZE: 12,
  SKELETON_COUNT: 12,
  GRID_COLUMNS: {
    mobile: 2, // default
    medium: 4, // md: 768px+
    large: 6, // lg: 1024px+
  },
  INFINITE_SCROLL: {
    THRESHOLD: 0.5, // Trigger when 50% of sentinel is visible
    ROOT_MARGIN: '100px', // Start loading 100px before sentinel
    SENTINEL_HEIGHT: 'h-20', // 5rem = 80px
  },
  LAYOUT: {
    PHOTO_HEIGHT: 'h-32', // 8rem = 128px
    GRID_GAP: 'gap-4', // 1rem = 16px
  },
}

/**
 * API configuration
 *
 * @property {string} BASE_URL - API base URL (from environment variable or default)
 * @property {number} DEFAULT_TIMEOUT - Default request timeout in milliseconds
 * @property {number} GPS_SYNC_TIMEOUT - Extended timeout for GPS sync operations
 */
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_URL || '/api',
  DEFAULT_TIMEOUT: 30000, // 30 seconds
  GPS_SYNC_TIMEOUT: 60000, // 60 seconds
}

/**
 * Toast notification configuration
 *
 * @property {number} DEFAULT_DURATION - Default toast display duration in milliseconds
 * @property {number} ERROR_DURATION - Error toast display duration
 * @property {number} SUCCESS_DURATION - Success toast display duration
 */
export const TOAST_CONFIG = {
  DEFAULT_DURATION: 4000, // 4 seconds
  ERROR_DURATION: 6000, // 6 seconds
  SUCCESS_DURATION: 3000, // 3 seconds
}
