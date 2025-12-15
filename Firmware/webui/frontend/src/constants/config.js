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
 *
 * @property {Object} LAZY_IMAGE - Lazy image loading configuration (IntersectionObserver)
 *   - ROOT_MARGIN: Distance before viewport to start loading (e.g., '100px')
 *   - THRESHOLD: Percentage of image visibility to trigger load (0.0-1.0)
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
    ASPECT_RATIO: 9152 / 6944, // Mothbox camera aspect ratio (~1.318:1, slightly wider than 4:3)
  },
  LAZY_IMAGE: {
    ROOT_MARGIN: '100px', // Start loading images 100px before they enter viewport
    THRESHOLD: 0.1, // Trigger when 10% of image is visible
  },
  VIRTUALIZATION: {
    ENABLED: false, // Disabled due to react-window 2.2.3 bug with React 18 StrictMode
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
 * @property {string} VIEW_MODES.MAP - Map view mode (GPS-tagged photos on Leaflet map)
 * @property {string} DEFAULT_VIEW - Default view mode when no preference set
 * @property {string} STORAGE_KEY - localStorage/backend preference key for view mode
 */
export const VIEW_CONFIG = {
  VIEW_MODES: {
    GRID: 'grid',
    LIST: 'list',
    MAP: 'map',
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

/**
 * Map Component Configuration
 *
 * Leaflet map configuration for displaying GPS-tagged photo locations.
 * Uses OpenStreetMap tiles (free, no API key required).
 *
 * @property {Array<number>} DEFAULT_CENTER - Default map center coordinates [lat, lon] for world view
 * @property {number} DEFAULT_ZOOM - Default zoom level (2 = world view)
 * @property {number} MIN_ZOOM - Minimum allowed zoom level (2 = world view)
 * @property {number} MAX_ZOOM - Maximum allowed zoom level (18 = street-level detail)
 *
 * @property {string} TILE_URL - OpenStreetMap tile server URL template
 *   - {s}: Subdomain for load balancing (a/b/c)
 *   - {z}: Zoom level
 *   - {x}/{y}: Tile coordinates
 * @property {string} ATTRIBUTION - OpenStreetMap copyright attribution (required by license)
 *
 * @property {Object} CLUSTER - Marker clustering configuration (Leaflet.markercluster)
 *   - MAX_RADIUS: Pixel radius for grouping nearby markers into clusters
 *   - SPIDERFY_ON_MAX_ZOOM: Expand clustered markers at max zoom level
 *   - SHOW_COVERAGE_ON_HOVER: Show cluster coverage area on mouse hover
 *
 * @property {Object} POPUP - Popup window configuration for photo markers
 *   - MAX_WIDTH: Maximum popup width in pixels
 *   - THUMBNAIL_SIZE: Thumbnail image size in pixels (128px for fast loading)
 */
export const MAP_CONFIG = {
  // Default map center (world view)
  DEFAULT_CENTER: [0, 0],
  DEFAULT_ZOOM: 2,

  // Zoom limits
  MIN_ZOOM: 2,
  MAX_ZOOM: 18,

  // OpenStreetMap tile provider
  TILE_URL: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  ATTRIBUTION:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',

  // Marker clustering
  CLUSTER: {
    MAX_RADIUS: 40, // Pixel radius for clustering
    SPIDERFY_ON_MAX_ZOOM: true,
    SHOW_COVERAGE_ON_HOVER: false,
  },

  // Popup configuration
  POPUP: {
    MAX_WIDTH: 200,
    THUMBNAIL_SIZE: 128,
  },

  // Photo batch size for map page lightbox navigation
  PHOTO_BATCH_SIZE: 100,
}

/**
 * Clustering Configuration
 *
 * Geographic clustering configuration for grouping nearby photos on the map.
 * Clustering happens on the backend using Haversine distance calculation.
 *
 * @property {boolean} DEFAULT_ENABLED - Enable clustering by default
 * @property {number} DEFAULT_RADIUS - Default clustering radius in meters (100m)
 * @property {number} MIN_RADIUS - Minimum allowed radius in meters (10m)
 * @property {number} MAX_RADIUS - Maximum allowed radius in meters (5000m = 5km)
 * @property {number} RADIUS_STEP - Step size for radius slider (10m increments)
 * @property {number} DEFAULT_MIN_SIZE - Minimum photos required to form a cluster
 * @property {string} STORAGE_KEY - localStorage key for persisting settings
 */
export const CLUSTERING_CONFIG = {
  DEFAULT_ENABLED: true,
  DEFAULT_RADIUS: 100, // meters
  MIN_RADIUS: 10,
  MAX_RADIUS: 5000,
  RADIUS_STEP: 10,
  DEFAULT_MIN_SIZE: 2,
  STORAGE_KEY: 'mothbox_clustering_settings',
}

/**
 * Hover Popup Configuration (Issue #117)
 *
 * Configuration for the interactive hover popup on map cluster markers.
 * Displays a 3x3 thumbnail grid preview of photos at each location.
 *
 * @property {number} GRID_SIZE - Grid dimensions (3 = 3x3 grid)
 * @property {number} THUMBNAIL_SIZE - Size of thumbnails in pixels (128px for balanced quality)
 * @property {number} DEBOUNCE_MS - Debounce delay for hover detection (ms)
 * @property {number} SHOW_DELAY_MS - Delay before showing popup (ms)
 * @property {number} HIDE_DELAY_MS - Delay before hiding popup to prevent flicker (ms)
 * @property {number} MAX_PHOTOS - Maximum photos to display in grid
 * @property {number} POPUP_WIDTH - Popup container width in pixels
 * @property {number} Z_INDEX - Z-index for popup layering (must match Z_INDEX.MAP_POPUP)
 * @property {number} SWIPE_THRESHOLD - Minimum swipe distance for mobile navigation (px)
 * @property {number} ANIMATION_DURATION - Fade animation duration (ms)
 */
export const HOVER_POPUP_CONFIG = {
  GRID_SIZE: 3,
  THUMBNAIL_SIZE: 128,
  DEBOUNCE_MS: 150,
  SHOW_DELAY_MS: 100,
  HIDE_DELAY_MS: 200,
  MAX_PHOTOS: 9,
  POPUP_WIDTH: 280,
  Z_INDEX: 1100,
  SWIPE_THRESHOLD: 50,
  ANIMATION_DURATION: 100,
}

/**
 * Metadata Field Validation Limits
 *
 * Maximum character lengths for metadata fields.
 * Must match backend sidecar_metadata.py constants.
 *
 * @property {number} MAX_TAG_LENGTH - Maximum length for individual tags (50 chars)
 * @property {number} MAX_SPECIES_LENGTH - Maximum length for species scientific name (200 chars)
 * @property {number} MAX_COMMON_NAME_LENGTH - Maximum length for species common name (200 chars)
 * @property {number} MAX_NOTES_LENGTH - Maximum length for notes field (10000 chars)
 * @property {number} MAX_REFERENCE_URL_LENGTH - Maximum length for reference URL (500 chars)
 */
export const METADATA_VALIDATION = {
  MAX_TAG_LENGTH: 50,
  MAX_SPECIES_LENGTH: 200,
  MAX_COMMON_NAME_LENGTH: 200,
  MAX_NOTES_LENGTH: 10000,
  MAX_REFERENCE_URL_LENGTH: 500,
}

/**
 * Species Identification Configuration
 *
 * Configuration for species identification metadata fields.
 *
 * @property {Array<Object>} CONFIDENCE_OPTIONS - Available confidence levels for species ID
 *   - value: Internal value stored in metadata
 *   - label: User-facing display label
 */
export const SPECIES_CONFIG = {
  CONFIDENCE_OPTIONS: [
    { value: 'certain', label: 'Certain' },
    { value: 'probable', label: 'Probable' },
    { value: 'possible', label: 'Possible' },
    { value: 'unknown', label: 'Unknown' },
  ],
}

/**
 * Stacked Photo Card Configuration
 *
 * Visual styling for stacked photo cards (HDR, Focus Bracket series).
 *
 * @property {Array<string>} Z_INDEX_CLASSES - Z-index Tailwind classes for stacking order
 * @property {Array<string>} OFFSETS - Transform classes for visual offset (back to front)
 * @property {Array<string>} SHADOWS - Shadow classes for depth effect (back to front)
 */
export const STACKED_CARD_CONFIG = {
  Z_INDEX_CLASSES: ['z-10', 'z-20', 'z-30'],
  OFFSETS: [
    'translate-x-2 translate-y-2',
    'translate-x-1 translate-y-1',
    'translate-x-0 translate-y-0',
  ],
  SHADOWS: ['shadow-sm', 'shadow-md', 'shadow-lg'],
}

/**
 * Tag Autocomplete Configuration
 *
 * Configuration for tag autocomplete/suggestion functionality.
 *
 * @property {number} DEBOUNCE_MS - Debounce delay for API calls (ms)
 * @property {number} MIN_CHARS - Minimum characters before fetching suggestions
 * @property {number} MAX_SUGGESTIONS - Maximum number of suggestions to return
 * @property {number} CACHE_STALE_TIME - Cache stale time in ms (5 minutes)
 * @property {number} CACHE_GC_TIME - Cache garbage collection time in ms (10 minutes)
 */
export const TAG_AUTOCOMPLETE_CONFIG = {
  DEBOUNCE_MS: 200,
  MIN_CHARS: 2,
  MAX_SUGGESTIONS: 10,
  CACHE_STALE_TIME: 5 * 60 * 1000,  // 5 minutes
  CACHE_GC_TIME: 10 * 60 * 1000,    // 10 minutes
}

/**
 * API Limits Configuration
 *
 * Backend API limits for bulk operations. These values MUST match the
 * backend constants in webui/backend/constants.py.
 *
 * Verify at runtime via GET /api/system/config/limits if needed.
 *
 * @property {number} MAX_BATCH_SIZE - Max files per bulk sidecar operation (tags, species)
 * @property {number} MAX_BULK_DELETE - Max files per bulk delete operation
 */
export const API_LIMITS = {
  MAX_BATCH_SIZE: 100,    // Backend: MAX_BULK_FILES
  MAX_BULK_DELETE: 100,   // Backend: MAX_BULK_DELETE
}

/**
 * Export Format Configuration
 *
 * Available export formats for bulk photo export.
 * Must match backend ExportJobFormat enum in lib/export_job_types.py.
 *
 * @property {string} id - Format identifier (matches backend enum value)
 * @property {string} name - User-facing format name
 * @property {string} description - Brief description of the format
 */
export const EXPORT_FORMATS = [
  {
    id: 'darwin_core',
    name: 'Darwin Core',
    description: 'For GBIF biodiversity portals',
  },
  {
    id: 'inaturalist',
    name: 'iNaturalist',
    description: 'With XMP sidecars',
  },
  {
    id: 'json',
    name: 'JSON',
    description: 'All metadata fields',
  },
  {
    id: 'csv',
    name: 'CSV',
    description: 'Excel compatible',
  },
]

/**
 * Valid export format IDs (derived from EXPORT_FORMATS)
 * Used for input validation in useBulkExport hook.
 */
export const VALID_EXPORT_FORMAT_IDS = EXPORT_FORMATS.map(f => f.id)

/**
 * Z-Index Layer System
 *
 * Centralized z-index values to prevent layering conflicts.
 * Higher numbers appear above lower numbers.
 *
 * Layer hierarchy (bottom to top):
 * 1. PHOTO_CONTROLS (10) - Checkboxes, quick actions on photo cards
 * 2. DROPDOWN (30) - Search bar, autocomplete dropdowns
 * 3. TOOLBAR (40) - Floating action bars
 * 4. MODAL (50) - Modals, lightbox, full overlays
 * 5. MAP_CONTROLS (1000) - Leaflet map controls
 * 6. MAP_POPUP (1100) - Map hover popups (above Leaflet)
 *
 * @property {string} PHOTO_CONTROLS - Photo overlay elements (checkboxes, quick actions)
 * @property {string} DROPDOWN - Dropdowns that need to appear above photo content
 * @property {string} TOOLBAR - Floating toolbars (bulk actions)
 * @property {string} MODAL - Full-screen overlays (lightbox, modals)
 * @property {string} MAP_CONTROLS - Leaflet map control layer
 * @property {number} MAP_POPUP - Map hover popup (numeric for inline style)
 */
export const Z_INDEX = {
  PHOTO_CONTROLS: 'z-10',    // Checkboxes, quick tag buttons on photos
  DROPDOWN: 'z-30',          // Search bar dropdowns, autocomplete
  TOOLBAR: 'z-40',           // Bulk actions toolbar, floating buttons
  MODAL: 'z-[1200]',         // Modals, lightbox, overlays (above map elements)
  MAP_CONTROLS: 'z-[1000]',  // Leaflet map controls layer
  MAP_POPUP: 1100,           // Map hover popup (numeric for inline style)
}
