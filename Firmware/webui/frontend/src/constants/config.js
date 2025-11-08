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
 *   - Set to 24 for adaptive 2-3 screen loads across all device sizes
 *   - Desktop (4 cols): 6 rows, Medium (3 cols): 8 rows, Mobile (2 cols): 12 rows
 *   - Guarantees infinite scroll sentinel enters viewport for automatic next page load
 *   - Thumbnail payload: 24 × ~32KB = ~768KB (acceptable for high-quality 256px thumbnails)
 *
 * @property {number} SKELETON_COUNT - Number of skeleton loaders to show while fetching
 *   - Should match PAGE_SIZE for consistent visual experience
 *
 * @property {Object} GRID_COLUMNS - Responsive grid configuration (matches Tailwind breakpoints)
 *   - mobile: 2 columns (portrait, <640px)
 *   - small: 3 columns (landscape phones, ≥640px)
 *   - medium: 3 columns (tablets, ≥768px)
 *   - large: 4 columns (desktop, ≥1024px) - reduced from 6 for larger thumbnail display
 *
 * @property {Object} INFINITE_SCROLL - Infinite scroll behavior configuration
 *   - THRESHOLD: IntersectionObserver threshold (0.0-1.0) - when to trigger loading
 *   - ROOT_MARGIN: Distance before sentinel to start loading (px)
 *   - SENTINEL_HEIGHT: Height of scroll sentinel element (Tailwind class)
 *
 * @property {Object} LAYOUT - Visual layout configuration
 *   - PHOTO_HEIGHT: Photo card height (Tailwind class) - h-64 = 256px for high-quality display
 *   - GRID_GAP: Spacing between grid items (Tailwind class)
 *
 * @property {Object} THUMBNAIL - Thumbnail sizing configuration
 *   - SIZE: Backend thumbnail size (256px for high quality, already cached)
 *   - ASPECT_RATIO: Expected ratio for Mothbox camera (9152x6944 = ~1.318:1)
 */
export const GALLERY_CONFIG = {
  PAGE_SIZE: 24,
  SKELETON_COUNT: 24,
  GRID_COLUMNS: {
    mobile: 2, // portrait phones (<640px)
    small: 3, // landscape phones (≥640px)
    medium: 3, // tablets (≥768px)
    large: 4, // desktop (≥1024px)
  },
  INFINITE_SCROLL: {
    THRESHOLD: 0.5, // Trigger when 50% of sentinel is visible
    ROOT_MARGIN: '100px', // Start loading 100px before sentinel
    SENTINEL_HEIGHT: 'h-20', // 5rem = 80px
  },
  LAYOUT: {
    PHOTO_HEIGHT: 'h-64', // 16rem = 256px (high-quality display)
    GRID_GAP: 'gap-4', // 1rem = 16px
  },
  THUMBNAIL: {
    SIZE: 256, // Backend thumbnail size (256px high quality, already cached)
    ASPECT_RATIO: 4 / 3, // Expected aspect ratio for Mothbox camera (9152x6944 = ~1.318:1)
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
