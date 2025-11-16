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
  VIRTUALIZATION: {
    ENABLED: true, // Enable virtual scrolling for large galleries
    MIN_PHOTOS_FOR_VIRTUALIZATION: 100, // Minimum photo count to activate virtualization
    OVERSCAN_ROW_COUNT: 2, // Rows to render above/below viewport for smooth scrolling
    ITEM_SIZE: 272, // Photo height (256px) + gap (16px)
    ESTIMATED_ITEM_SIZE: 272, // For variable sizing (currently fixed size)
    SCROLL_THROTTLE_MS: 16, // ~60fps scroll handling
    MAX_CACHED_IMAGES: 100, // LRU cache size for image preloading (Step 6)
    PRELOAD_DISTANCE: 3, // Rows to preload ahead/behind (Step 6)
    VIEWPORT_HEIGHT_RATIO: 0.8, // Viewport height as ratio of window height (80%)
    MIN_VIEWPORT_HEIGHT: 600, // Minimum viewport height in pixels (600px)
    RESIZE_DEBOUNCE_MS: 150, // Debounce delay for resize events (balances responsiveness vs performance)
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
 * View mode configuration for gallery
 *
 * @property {Object} VIEW_MODES - Available gallery view modes
 * @property {string} VIEW_MODES.GRID - Grid view mode (multi-column thumbnail grid)
 * @property {string} VIEW_MODES.LIST - List view mode (single-column with metadata)
 * @property {string} DEFAULT_VIEW - Default view mode when no preference set
 * @property {string} STORAGE_KEY - localStorage/backend preference key for view mode
 */
export const VIEW_CONFIG = {
  VIEW_MODES: {
    GRID: 'grid',
    LIST: 'list',
  },
  DEFAULT_VIEW: 'grid',
  STORAGE_KEY: 'gallery_view_mode',
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

/**
 * Photo Lightbox Configuration
 *
 * Controls behavior of the adaptive photo lightbox component with zoom, pan, and touch gestures.
 *
 * @property {number} ANIMATION_DURATION - Duration of lightbox open/close animations (milliseconds)
 * @property {number} ZOOM_MIN - Minimum zoom level (1.0 = 100%, original size)
 * @property {number} ZOOM_MAX - Maximum zoom level (5.0 = 500%, 5x magnification)
 * @property {number} ZOOM_STEP - Zoom increment/decrement step for +/- controls
 * @property {number} ZOOM_DOUBLE_TAP - Zoom level for double-tap zoom-in (mobile)
 * @property {boolean} KEYBOARD_ENABLED - Enable keyboard shortcuts (arrows, +/-, ESC)
 * @property {boolean} WRAP_NAVIGATION - Wrap navigation (last photo → first photo)
 *
 * @property {Object} PERFORMANCE - Performance tuning
 * @property {number} PERFORMANCE.DEBOUNCE_RESIZE_MS - Debounce timeout for window resize events
 *
 * @property {Object} TOUCH_GESTURES - Touch gesture detection thresholds
 * @property {number} TOUCH_GESTURES.DOUBLE_TAP_TIMEOUT - Max time between taps for double-tap (ms)
 * @property {number} TOUCH_GESTURES.TAP_MAX_DURATION - Max touch duration to distinguish tap from drag (ms)
 * @property {number} TOUCH_GESTURES.SWIPE_MIN_DISTANCE - Min horizontal distance for swipe detection (px)
 * @property {number} TOUCH_GESTURES.SWIPE_MIN_VELOCITY - Min swipe speed to distinguish from slow drag (px/ms)
 * @property {number} TOUCH_GESTURES.DOUBLE_TAP_DISTANCE_BASE - Base distance threshold for double-tap (px at 1x DPI)
 *   - Multiplied by devicePixelRatio for DPI-aware detection
 *   - 15px@1x, 30px@2x, 45px@3x for Retina/high-DPI displays
 */
export const LIGHTBOX_CONFIG = {
  ANIMATION_DURATION: 200, // milliseconds
  ZOOM_MIN: 1,
  ZOOM_MAX: 5,
  ZOOM_STEP: 0.5,
  ZOOM_DOUBLE_TAP: 2.5, // Double-tap zoom level (mobile)
  KEYBOARD_ENABLED: true,
  WRAP_NAVIGATION: true, // Wrap to first/last photo

  PERFORMANCE: {
    DEBOUNCE_RESIZE_MS: 150, // Window resize debounce (balances responsiveness vs performance)
  },

  TOUCH_GESTURES: {
    DOUBLE_TAP_TIMEOUT: 300, // Max time between taps to register as double-tap (ms)
    TAP_MAX_DURATION: 200, // Max touch duration to distinguish tap from drag (ms)
    SWIPE_MIN_DISTANCE: 50, // Min horizontal distance for swipe - prevents accidental swipes (px)
    SWIPE_MIN_VELOCITY: 0.3, // Min swipe speed - distinguishes swipe from slow drag (px/ms)
    DOUBLE_TAP_DISTANCE_BASE: 15, // Base distance threshold for double-tap at 1x DPI (px)
  },
}
