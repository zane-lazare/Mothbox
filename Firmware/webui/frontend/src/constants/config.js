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
 *   - Original spec from Issue #136: 9 photos per page for faster initial load
 *   - Current: 9 = 4.5 rows mobile (2 cols), 2.25 rows medium (4 cols), 1.5 rows large (6 cols)
 *   - Note: Partial rows are acceptable; prioritizes faster loading over perfect grid alignment
 *   - Alternative: 12 for cleaner grid (6/3/2 rows), 24 for faster scrolling (12/6/4 rows)
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
  PAGE_SIZE: 9,
  SKELETON_COUNT: 9,
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

/**
 * Gallery user-facing messages
 *
 * Centralized message strings for the Gallery component to eliminate duplication
 * and provide a single source of truth for all user-facing text.
 *
 * @property {Object} LOADING - Loading state messages
 *   - INITIAL: Displayed when first loading the gallery
 *   - MORE: Displayed when loading additional photos during infinite scroll
 *
 * @property {Object} ERROR - Error state messages
 *   - INITIAL: Prefix for initial gallery load errors
 *   - PAGINATION: Prefix for errors when loading more photos
 *   - FALLBACK: Default error message when error.message is unavailable
 *     Note: Uses "An unexpected error occurred" for consistency with ErrorBoundary
 *
 * @property {string} EMPTY - Message shown when no photos exist in the gallery
 * @property {string} END - Message shown when all photos have been loaded (end of infinite scroll)
 */
export const GALLERY_MESSAGES = {
  LOADING: {
    INITIAL: 'Loading gallery...',
    MORE: 'Loading more photos...',
  },
  ERROR: {
    INITIAL: 'Error loading photos',
    PAGINATION: 'Error loading more photos',
    FALLBACK: 'An unexpected error occurred',
  },
  EMPTY: 'No photos yet',
  END: 'No more photos to load',
}
