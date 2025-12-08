import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { LIGHTBOX_CONFIG, Z_INDEX } from '../constants/config'
import useZoomPan from '../hooks/useZoomPan'
import useTouchGestures from '../hooks/useTouchGestures'
import useImagePreload from '../hooks/useImagePreload'
import { debounce, throttle } from '../utils/performance'
import { getPhotoUrl } from '../utils/api'
import MetadataPanel from './metadata/MetadataPanel'
import MetadataErrorBoundary from './metadata/MetadataErrorBoundary'
import { formatCoordinateDisplay } from '../utils/gpsCoordinates'

/**
 * Adaptive Photo Lightbox Component
 *
 * Full-screen modal lightbox with zoom, pan, and touch gesture support.
 * Supports both desktop (mouse/keyboard) and mobile (touch) interactions.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Object|null} props.photo - Current photo to display {path, filename, date, size, latitude, longitude, altitude, ...}
 * @param {Array<Object>} props.photos - Array of all photos for navigation
 * @param {Function} props.onClose - Callback when lightbox closes
 * @param {Function} props.onNavigate - Callback when navigating to different photo (photo) => void
 * @param {Function} [props.onLocationClick] - Optional callback when location is clicked (lat, lon) => void
 *
 * @example
 * <PhotoLightbox
 *   photo={selectedPhoto}
 *   photos={allPhotos}
 *   onClose={() => setSelectedPhoto(null)}
 *   onNavigate={setSelectedPhoto}
 *   onLocationClick={(lat, lon) => centerMapOnLocation(lat, lon)}
 * />
 *
 * @features
 * - Desktop: Mouse wheel zoom, click-drag pan, keyboard navigation (arrows, +/-, ESC)
 * - Mobile: Pinch-to-zoom, touch pan, swipe navigation, double-tap zoom toggle
 * - Accessibility: WCAG 2.1 AA compliant, screen reader support, focus trap
 * - Performance: GPU-accelerated transforms (translate3d), progressive image loading
 * - Visual feedback: Loading spinner, error messages, zoom indicator
 * - Location display: GPS coordinates in DMS format with altitude (when available)
 *
 * @accessibility
 * - Full keyboard navigation support
 * - Focus trap when open (tab cycles through controls)
 * - ARIA labels and live regions for screen readers
 * - Zoom level announcements
 * - 44px minimum touch targets (WCAG AAA)
 *
 * @performance
 * - GPU-accelerated CSS transforms (60 FPS target)
 * - Debounced resize handlers (300ms)
 * - Progressive image preloading (adjacent images)
 * - Efficient event listeners with cleanup
 *
 * @see https://github.com/Digital-Naturalism-Laboratories/Mothbox/issues/101
 * @see https://github.com/Digital-Naturalism-Laboratories/Mothbox/issues/119
 */

/**
 * Format file size from bytes to human-readable string
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted size (e.g., "1.5 MB")
 */
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

/**
 * Format date string to YYYY-MM-DD
 * Preserves the calendar date regardless of timezone by using UTC methods
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date or 'Invalid Date' if parsing fails
 */
const formatDate = (dateString) => {
  try {
    const date = new Date(dateString)
    // new Date() doesn't throw on invalid input - it returns Invalid Date object
    if (isNaN(date.getTime())) {
      console.warn('[PhotoLightbox] Invalid timestamp:', dateString)
      return 'Invalid Date'
    }
    // Use UTC methods to avoid timezone conversion issues
    const year = date.getUTCFullYear()
    const month = String(date.getUTCMonth() + 1).padStart(2, '0')
    const day = String(date.getUTCDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  } catch (error) {
    console.warn('[PhotoLightbox] Date parsing error:', dateString, error)
    return 'Invalid Date'
  }
}

/**
 * LocationHeader Component - Displays GPS coordinates and altitude
 * @param {Object} props - Component props
 * @param {number|null} props.latitude - Latitude in decimal degrees
 * @param {number|null} props.longitude - Longitude in decimal degrees
 * @param {number|null} [props.altitude] - Altitude in meters (optional)
 * @param {Function} [props.onLocationClick] - Optional callback when clicked (lat, lon) => void
 */
function LocationHeader({ latitude, longitude, altitude, onLocationClick }) {
  // Check if GPS coordinates are available (must be numbers, 0 is valid)
  const hasGPS = typeof latitude === 'number' && typeof longitude === 'number'

  // Handle location click
  const handleClick = () => {
    if (onLocationClick && hasGPS) {
      onLocationClick(latitude, longitude)
    }
  }

  if (!hasGPS) {
    return (
      <div className="location-header" data-testid="location-header">
        <span className="no-location text-gray-400">Location not available</span>
      </div>
    )
  }

  // Format coordinates as DMS
  const latDisplay = formatCoordinateDisplay(latitude, true, 'dms')
  const lonDisplay = formatCoordinateDisplay(longitude, false, 'dms')

  // Determine if coordinates should be clickable
  const coordinatesElement = onLocationClick ? (
    <button
      type="button"
      onClick={handleClick}
      className="coordinates text-blue-400 hover:text-blue-300 cursor-pointer transition-colors"
      data-testid="location-coordinates"
      aria-label={`Location: ${latDisplay}, ${lonDisplay}`}
    >
      {latDisplay}, {lonDisplay}
    </button>
  ) : (
    <span className="coordinates" data-testid="location-coordinates">
      {latDisplay}, {lonDisplay}
    </span>
  )

  return (
    <div className="location-header" data-testid="location-header">
      {coordinatesElement}
      {typeof altitude === 'number' && (
        <span className="altitude ml-2 text-gray-300">
          Alt: {altitude}m
        </span>
      )}
    </div>
  )
}

function PhotoLightbox({ photo, photos = [], onClose, onNavigate, onLocationClick }) {
  const closeButtonRef = useRef(null)
  const previousFocusRef = useRef(null)
  const imageRef = useRef(null)
  const containerRef = useRef(null)
  const dialogRef = useRef(null)
  const panStartRef = useRef({ x: 0, y: 0 })

  // Image and container dimensions
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 })
  const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 })

  // Loading and error states
  const [isImageLoading, setIsImageLoading] = useState(true)
  const [imageError, setImageError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const MAX_RETRIES = 3

  // Panning state
  const [isPanning, setIsPanning] = useState(false)

  // Zoom indicator auto-hide
  const [showZoomIndicator, setShowZoomIndicator] = useState(false)
  const zoomIndicatorTimerRef = useRef(null)

  // Debounced zoom announcement for screen readers (prevents spam during wheel zoom)
  const [announcedZoom, setAnnouncedZoom] = useState(1.0)
  const zoomAnnouncementTimerRef = useRef(null)

  // Calculate current index for preloading (memoized to avoid O(n) on every render)
  const currentIndex = useMemo(
    () => (photo ? photos.findIndex((p) => p.path === photo.path) : -1),
    [photos, photo]
  )

  // Zoom and pan hook
  const { zoom, pan, setZoom, setPan, handleZoomIn, handleZoomOut, handleWheel, resetZoom } =
    useZoomPan({
      minZoom: LIGHTBOX_CONFIG.ZOOM_MIN,
      maxZoom: LIGHTBOX_CONFIG.ZOOM_MAX,
      zoomStep: LIGHTBOX_CONFIG.ZOOM_STEP,
      imageWidth: imageDimensions.width,
      imageHeight: imageDimensions.height,
      containerWidth: containerDimensions.width,
      containerHeight: containerDimensions.height,
    })

  // Throttle wheel events to prevent performance issues (wheel can fire 50+ events/sec)
  // 16ms = ~60fps maximum update rate
  const throttledHandleWheel = useMemo(() => throttle(handleWheel, 16), [handleWheel])

  // Cleanup throttled wheel handler on unmount
  useEffect(() => {
    return () => {
      throttledHandleWheel.cancel()
    }
  }, [throttledHandleWheel])

  // Image preloading hook (preloads adjacent images for smooth navigation)
  useImagePreload({
    currentPhoto: photo,
    photos,
    currentIndex,
  })

  // Track image dimensions when loaded
  useEffect(() => {
    const currentImageRef = imageRef.current
    if (!currentImageRef) return

    // Reset states when photo changes
    setIsImageLoading(true)
    setImageError(false)
    setRetryCount(0)

    const handleImageLoad = () => {
      if (currentImageRef) {
        setImageDimensions({
          width: currentImageRef.naturalWidth,
          height: currentImageRef.naturalHeight,
        })
        setIsImageLoading(false)
      }
    }

    const handleImageError = () => {
      setImageError(true)
      setIsImageLoading(false)
    }

    // If image already loaded (check naturalWidth to ensure dimensions are available)
    if (currentImageRef.complete && currentImageRef.naturalWidth > 0) {
      handleImageLoad()
    } else {
      currentImageRef.addEventListener('load', handleImageLoad)
      currentImageRef.addEventListener('error', handleImageError)
    }

    return () => {
      currentImageRef.removeEventListener('load', handleImageLoad)
      currentImageRef.removeEventListener('error', handleImageError)
    }
  }, [photo])

  // Track container dimensions
  useEffect(() => {
    if (!containerRef.current) return

    const updateContainerDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setContainerDimensions({
          width: rect.width,
          height: rect.height,
        })
      }
    }

    updateContainerDimensions()

    // Debounce resize handler for better performance
    const debouncedUpdate = debounce(
      updateContainerDimensions,
      LIGHTBOX_CONFIG.PERFORMANCE.DEBOUNCE_RESIZE_MS
    )

    // Update on window resize
    window.addEventListener('resize', debouncedUpdate)
    return () => {
      window.removeEventListener('resize', debouncedUpdate)
      debouncedUpdate.cancel()
    }
  }, [photo])

  // Show zoom indicator when zoom changes
  useEffect(() => {
    setShowZoomIndicator(true)

    // Clear existing timer
    if (zoomIndicatorTimerRef.current) {
      clearTimeout(zoomIndicatorTimerRef.current)
      zoomIndicatorTimerRef.current = null
    }

    // Hide after 2 seconds
    zoomIndicatorTimerRef.current = setTimeout(() => {
      setShowZoomIndicator(false)
    }, 2000)

    return () => {
      if (zoomIndicatorTimerRef.current) {
        clearTimeout(zoomIndicatorTimerRef.current)
        zoomIndicatorTimerRef.current = null
      }
    }
  }, [zoom])

  // Debounce zoom announcements for screen readers (prevent spam during continuous zoom)
  useEffect(() => {
    // Clear existing announcement timer
    if (zoomAnnouncementTimerRef.current) {
      clearTimeout(zoomAnnouncementTimerRef.current)
    }

    // Announce zoom after 500ms of no changes (user finished zooming)
    zoomAnnouncementTimerRef.current = setTimeout(() => {
      setAnnouncedZoom(zoom)
    }, 500)

    return () => {
      if (zoomAnnouncementTimerRef.current) {
        clearTimeout(zoomAnnouncementTimerRef.current)
        zoomAnnouncementTimerRef.current = null
      }
    }
  }, [zoom])

  // Body scroll lock and focus management
  useEffect(() => {
    if (!photo) return

    // Lock scroll when open and save previous focus
    previousFocusRef.current = document.activeElement
    document.body.classList.add('lightbox-open')

    // Focus close button on open (after browser paint)
    const frameId = requestAnimationFrame(() => {
      closeButtonRef.current?.focus()
    })

    return () => {
      cancelAnimationFrame(frameId)
      document.body.classList.remove('lightbox-open')
      // Restore focus to previous element (only if still in DOM)
      if (previousFocusRef.current?.isConnected) {
        previousFocusRef.current.focus()
      }
    }
  }, [photo])

  // Navigation logic (must be defined before useEffect that uses it)
  const hasMultiplePhotos = photos.length > 1

  const handleNavigate = useCallback((direction) => {
    if (!photo || !onNavigate || !hasMultiplePhotos) return

    let newIndex
    if (direction === 'next') {
      newIndex = currentIndex + 1
      if (newIndex >= photos.length) {
        newIndex = LIGHTBOX_CONFIG.WRAP_NAVIGATION ? 0 : currentIndex
      }
    } else {
      newIndex = currentIndex - 1
      if (newIndex < 0) {
        newIndex = LIGHTBOX_CONFIG.WRAP_NAVIGATION ? photos.length - 1 : currentIndex
      }
    }

    if (newIndex !== currentIndex) {
      onNavigate(photos[newIndex])
    }
  }, [photo, onNavigate, hasMultiplePhotos, currentIndex, photos])

  // Touch gestures hook for mobile support
  const { handleTouchStart, handleTouchMove, handleTouchEnd } = useTouchGestures({
    imageRef,
    zoom,
    setZoom,
    pan,
    setPan,
    onNavigate: handleNavigate,
    isZoomed: zoom > 1.0,
    imageWidth: imageDimensions.width,
    imageHeight: imageDimensions.height,
    minZoom: LIGHTBOX_CONFIG.ZOOM_MIN,
    maxZoom: LIGHTBOX_CONFIG.ZOOM_MAX,
  })

  // Handle mouse move for panning
  const handleMouseMove = useCallback((e) => {
    if (!isPanning || !panStartRef.current) return

    setPan({
      x: e.clientX - panStartRef.current.x,
      y: e.clientY - panStartRef.current.y,
    })
  }, [isPanning, setPan])

  // Handle mouse up (end panning)
  const handleMouseUp = useCallback(() => {
    setIsPanning(false)
  }, [])

  // Add global mouse event listeners for panning
  useEffect(() => {
    if (!isPanning) return

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isPanning, handleMouseMove, handleMouseUp])

  // Keyboard navigation - runs on every render
  useEffect(() => {
    if (!photo || !LIGHTBOX_CONFIG.KEYBOARD_ENABLED) return

    const handleKeyDown = (e) => {
      switch (e.key) {
        case 'Escape':
          onClose()
          break
        case 'ArrowLeft':
          e.preventDefault()
          handleNavigate('prev')
          break
        case 'ArrowRight':
          e.preventDefault()
          handleNavigate('next')
          break
        case '+':
        case '=': // For keyboards where + is Shift+=
          e.preventDefault()
          handleZoomIn()
          break
        case '-':
        case '_': // For keyboards where - is Shift+_
          e.preventDefault()
          handleZoomOut()
          break
        default:
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [photo, onClose, handleNavigate, handleZoomIn, handleZoomOut])

  // Focus trap - keep focus within dialog
  useEffect(() => {
    if (!photo || !dialogRef.current) return

    const handleTabKey = (e) => {
      if (e.key !== 'Tab') return

      const focusableElements = dialogRef.current.querySelectorAll(
        'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )

      // Early return if no focusable elements found
      if (focusableElements.length === 0) return

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      // Shift+Tab on first element: go to last
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault()
        lastElement.focus()
      }
      // Tab on last element: go to first
      else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener('keydown', handleTabKey)
    return () => document.removeEventListener('keydown', handleTabKey)
  }, [photo])

  // Memoized transform string for image positioning
  const imageTransform = useMemo(
    () => `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${zoom})`,
    [pan.x, pan.y, zoom]
  )

  // Handle backdrop click
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // Handle image click (prevent close)
  const handleImageClick = (e) => {
    e.stopPropagation()
  }

  // Handle mouse down for panning
  const handleMouseDown = (e) => {
    if (zoom <= 1.0) return // Only pan when zoomed

    setIsPanning(true)
    panStartRef.current = {
      x: e.clientX - pan.x,
      y: e.clientY - pan.y,
    }
  }

  // Zoom controls handlers with zoom indicator
  const handleZoomInClick = () => {
    handleZoomIn()
  }

  const handleZoomOutClick = () => {
    handleZoomOut()
  }

  const handleResetZoomClick = () => {
    resetZoom()
  }

  // Don't render if no photo selected (after all hooks for Rules of Hooks compliance)
  if (!photo) {
    return null
  }

  const lightboxContent = (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="lightbox-title"
      aria-describedby="lightbox-description"
      className={`fixed inset-0 ${Z_INDEX.MODAL} flex items-center justify-center bg-black bg-opacity-90 transition-opacity duration-200 ease-out`}
      onClick={handleBackdropClick}
    >
      {/* Screen reader title */}
      <h2 id="lightbox-title" className="sr-only">
        Photo Viewer: {photo.filename}
      </h2>

      {/* Screen reader description */}
      <div id="lightbox-description" className="sr-only">
        Use arrow keys to navigate, +/- to zoom, ESC to close
      </div>

      {/* Zoom level announcement for screen readers (debounced to prevent spam) */}
      <div aria-live="polite" className="sr-only">
        Zoom level: {Math.round(announcedZoom * 100)}%
      </div>

      {/* Close button - touch-friendly sizing */}
      <button
        ref={closeButtonRef}
        type="button"
        aria-label="Close photo viewer"
        onClick={onClose}
        className="absolute top-4 right-4 z-10 rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white md:p-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
      >
        <svg
          className="h-6 w-6 md:h-6 md:w-6"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Photo metadata */}
      <div className="absolute top-4 left-4 z-10 rounded-lg bg-black bg-opacity-50 p-3 text-white">
        <h3 className="text-sm font-semibold">{photo.filename}</h3>
        <p className="text-xs text-gray-300">
          {formatDate(photo.date)} • {formatFileSize(photo.size)}
        </p>
        <LocationHeader
          latitude={photo.latitude}
          longitude={photo.longitude}
          altitude={photo.altitude}
          onLocationClick={onLocationClick}
        />
      </div>

      {/* Navigation buttons - only show if multiple photos */}
      {hasMultiplePhotos && (
        <>
          {/* Previous button - touch-friendly */}
          <button
            type="button"
            aria-label="Previous photo"
            onClick={() => handleNavigate('prev')}
            className="absolute left-4 top-1/2 z-10 -translate-y-1/2 rounded-lg bg-black bg-opacity-50 p-3 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <svg
              className="h-6 w-6 md:h-6 md:w-6"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M15 19l-7-7 7-7" />
            </svg>
          </button>

          {/* Next button - touch-friendly */}
          <button
            type="button"
            aria-label="Next photo"
            onClick={() => handleNavigate('next')}
            className="absolute right-4 top-1/2 z-10 -translate-y-1/2 rounded-lg bg-black bg-opacity-50 p-3 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <svg
              className="h-6 w-6 md:h-6 md:w-6"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M9 5l7 7-7 7" />
            </svg>
          </button>

          {/* Photo counter */}
          <div className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-lg bg-black bg-opacity-50 px-3 py-1 text-sm text-white">
            {currentIndex + 1} / {photos.length}
          </div>
        </>
      )}

      {/* Zoom controls - mobile: bottom-right, desktop: top-right */}
      <div className="absolute bottom-4 right-4 md:top-20 md:bottom-auto z-10 flex flex-col gap-2">
        <button
          type="button"
          aria-label="Zoom in"
          onClick={handleZoomInClick}
          disabled={zoom >= LIGHTBOX_CONFIG.ZOOM_MAX}
          className="rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white disabled:opacity-30 min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          <svg
            className="h-6 w-6 md:h-6 md:w-6"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M12 4v16m8-8H4" />
          </svg>
        </button>
        <button
          type="button"
          aria-label="Zoom out"
          onClick={handleZoomOutClick}
          disabled={zoom <= LIGHTBOX_CONFIG.ZOOM_MIN}
          className="rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white disabled:opacity-30 min-h-[44px] min-w-[44px] flex items-center justify-center"
        >
          <svg
            className="h-6 w-6 md:h-6 md:w-6"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M20 12H4" />
          </svg>
        </button>
        {zoom > 1.0 && (
          <button
            type="button"
            aria-label="Reset zoom"
            onClick={handleResetZoomClick}
            className="rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white min-h-[44px] min-w-[44px] flex items-center justify-center"
          >
            <svg
              className="h-6 w-6 md:h-6 md:w-6"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}
      </div>

      {/* Zoom indicator - mobile: higher position to avoid thumb */}
      {showZoomIndicator && (
        <div className="absolute top-1/3 md:top-1/2 left-1/2 z-20 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-black bg-opacity-75 px-4 py-2 text-2xl font-bold text-white transition-opacity">
          {Math.round(zoom * 100)}%
        </div>
      )}

      {/* Main content container - flex layout for photo + metadata panel */}
      <div className="flex flex-col md:flex-row gap-4 h-full w-full p-4">
        {/* Image container - flex-1 to fill remaining space */}
        <div
          ref={containerRef}
          className="flex-1 flex items-center justify-center relative"
          onClick={handleImageClick}
        >
          {/* Loading spinner */}
          {isImageLoading && !imageError && (
            <div
              className="absolute inset-0 flex items-center justify-center"
              role="status"
              aria-label="Loading image"
            >
              <div className="h-12 w-12 animate-spin rounded-full border-b-2 border-white"></div>
            </div>
          )}

          {/* Error message */}
          {imageError && (
            <div
              className="absolute inset-0 flex flex-col items-center justify-center text-white"
              role="alert"
            >
              <svg
                className="mb-4 h-16 w-16 text-red-400"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-lg font-semibold">Failed to load image</p>
              <p className="text-sm text-gray-300 mt-2">{photo.filename}</p>
              {retryCount >= MAX_RETRIES ? (
                <p className="mt-4 text-sm text-red-300 max-w-md text-center">
                  Maximum retry attempts reached ({MAX_RETRIES}). The image may be corrupted, missing, or
                  the server may be experiencing issues.
                </p>
              ) : (
                <button
                  onClick={() => {
                    setImageError(false)
                    setIsImageLoading(true)
                    setRetryCount((prev) => prev + 1)
                    // Force image reload with cache-busting query parameter
                    if (imageRef.current) {
                      const currentSrc = imageRef.current.src.split('?')[0]
                      imageRef.current.src = `${currentSrc}?t=${Date.now()}`
                    }
                  }}
                  className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900"
                >
                  Retry {retryCount > 0 && `(${retryCount}/${MAX_RETRIES})`}
                </button>
              )}
            </div>
          )}

          {/* Image */}
          <img
            ref={imageRef}
            src={getPhotoUrl(photo.path)}
            alt={`Photo taken on ${formatDate(photo.date)}`}
            className="max-h-full max-w-full object-contain select-none"
            style={{
              transform: imageTransform,
              cursor: zoom > 1.0 ? (isPanning ? 'grabbing' : 'grab') : 'default',
              transition: isPanning ? 'none' : 'transform 0.1s ease-out',
              touchAction: zoom > 1.0 ? 'none' : 'pan-y', // Prevent browser gestures when zoomed
              willChange: zoom > 1.0 ? 'transform' : 'auto', // GPU acceleration hint when zoomed
              opacity: isImageLoading || imageError ? 0 : 1, // Hide image while loading or on error
            }}
            onWheel={throttledHandleWheel}
            onMouseDown={handleMouseDown}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            draggable={false}
          />
        </div>

        {/* Metadata panel - hidden on mobile, side panel on desktop */}
        <div className="hidden md:block md:w-96 bg-white dark:bg-gray-800 rounded-lg overflow-hidden">
          <MetadataErrorBoundary photoPath={photo.path}>
            <MetadataPanel photoPath={photo.path} />
          </MetadataErrorBoundary>
        </div>
      </div>
    </div>
  )

  // Render into portal (append to body)
  return createPortal(lightboxContent, document.body)
}

export default PhotoLightbox
