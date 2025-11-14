import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { LIGHTBOX_CONFIG } from '../constants/config'
import useZoomPan from '../hooks/useZoomPan'

/**
 * PhotoLightbox Component
 *
 * Full-screen photo viewer with zoom, pan, and navigation capabilities.
 *
 * @param {Object} props
 * @param {Object|null} props.photo - Photo object to display (null = closed)
 * @param {Array} props.photos - Full array of photos for navigation
 * @param {Function} props.onClose - Callback when lightbox closes
 * @param {Function} props.onNavigate - Callback when navigating to different photo
 */
function PhotoLightbox({ photo, photos = [], onClose, onNavigate }) {
  const closeButtonRef = useRef(null)
  const previousFocusRef = useRef(null)
  const imageRef = useRef(null)
  const containerRef = useRef(null)

  // Image and container dimensions
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 })
  const [containerDimensions, setContainerDimensions] = useState({ width: 0, height: 0 })

  // Panning state
  const [isPanning, setIsPanning] = useState(false)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })

  // Zoom indicator auto-hide
  const [showZoomIndicator, setShowZoomIndicator] = useState(false)
  const zoomIndicatorTimerRef = useRef(null)

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

  // Track image dimensions when loaded
  useEffect(() => {
    if (!imageRef.current) return

    const handleImageLoad = () => {
      if (imageRef.current) {
        setImageDimensions({
          width: imageRef.current.naturalWidth,
          height: imageRef.current.naturalHeight,
        })
      }
    }

    // If image already loaded
    if (imageRef.current.complete) {
      handleImageLoad()
    } else {
      imageRef.current.addEventListener('load', handleImageLoad)
    }

    return () => {
      if (imageRef.current) {
        imageRef.current.removeEventListener('load', handleImageLoad)
      }
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

    // Update on window resize
    window.addEventListener('resize', updateContainerDimensions)
    return () => window.removeEventListener('resize', updateContainerDimensions)
  }, [photo])

  // Show zoom indicator when zoom changes
  useEffect(() => {
    setShowZoomIndicator(true)

    // Clear existing timer
    if (zoomIndicatorTimerRef.current) {
      clearTimeout(zoomIndicatorTimerRef.current)
    }

    // Hide after 2 seconds
    zoomIndicatorTimerRef.current = setTimeout(() => {
      setShowZoomIndicator(false)
    }, 2000)

    return () => {
      if (zoomIndicatorTimerRef.current) {
        clearTimeout(zoomIndicatorTimerRef.current)
      }
    }
  }, [zoom])

  // Body scroll lock - runs on every render
  useEffect(() => {
    if (!photo) {
      // Restore scroll when closed
      document.body.style.overflow = ''
      if (previousFocusRef.current) {
        previousFocusRef.current.focus()
        previousFocusRef.current = null
      }
      return
    }

    // Lock scroll when open
    previousFocusRef.current = document.activeElement
    document.body.style.overflow = 'hidden'

    // Focus close button on open
    const timer = setTimeout(() => {
      closeButtonRef.current?.focus()
    }, 100)

    return () => {
      clearTimeout(timer)
      document.body.style.overflow = ''
    }
  }, [photo])

  // Navigation logic (must be defined before useEffect that uses it)
  const currentIndex = photo ? photos.findIndex((p) => p.path === photo.path) : -1
  const hasMultiplePhotos = photos.length > 1

  const handleNavigate = (direction) => {
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
  }

  // Handle mouse move for panning
  const handleMouseMove = (e) => {
    if (!isPanning) return

    setPan({
      x: e.clientX - panStart.x,
      y: e.clientY - panStart.y,
    })
  }

  // Handle mouse up (end panning)
  const handleMouseUp = () => {
    setIsPanning(false)
  }

  // Add global mouse event listeners for panning
  useEffect(() => {
    if (!isPanning) return

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isPanning, panStart, pan, setPan])

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
        default:
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [photo, onClose, handleNavigate])

  // Don't render if no photo selected (after hooks!)
  if (!photo) {
    return null
  }

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
  }

  // Format date
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString)
      return date.toISOString().split('T')[0]
    } catch {
      return dateString
    }
  }

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
    setPanStart({
      x: e.clientX - pan.x,
      y: e.clientY - pan.y,
    })
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

  const lightboxContent = (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="lightbox-title"
      aria-describedby="lightbox-description"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-90 transition-opacity duration-200 ease-out"
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

      {/* Close button */}
      <button
        ref={closeButtonRef}
        type="button"
        aria-label="Close photo viewer"
        onClick={onClose}
        className="absolute top-4 right-4 z-10 rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white"
      >
        <svg
          className="h-6 w-6"
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
      </div>

      {/* Navigation buttons - only show if multiple photos */}
      {hasMultiplePhotos && (
        <>
          {/* Previous button */}
          <button
            type="button"
            aria-label="Previous photo"
            onClick={() => handleNavigate('prev')}
            className="absolute left-4 top-1/2 z-10 -translate-y-1/2 rounded-lg bg-black bg-opacity-50 p-3 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white"
          >
            <svg
              className="h-6 w-6"
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

          {/* Next button */}
          <button
            type="button"
            aria-label="Next photo"
            onClick={() => handleNavigate('next')}
            className="absolute right-4 top-1/2 z-10 -translate-y-1/2 rounded-lg bg-black bg-opacity-50 p-3 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white"
          >
            <svg
              className="h-6 w-6"
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

      {/* Zoom controls */}
      <div className="absolute top-20 right-4 z-10 flex flex-col gap-2">
        <button
          type="button"
          aria-label="Zoom in"
          onClick={handleZoomInClick}
          disabled={zoom >= LIGHTBOX_CONFIG.ZOOM_MAX}
          className="rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white disabled:opacity-30"
        >
          <svg
            className="h-6 w-6"
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
          className="rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white disabled:opacity-30"
        >
          <svg
            className="h-6 w-6"
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
            className="rounded-lg bg-black bg-opacity-50 p-2 text-white transition-all hover:bg-opacity-75 focus:outline-none focus:ring-2 focus:ring-white"
          >
            <svg
              className="h-6 w-6"
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

      {/* Zoom indicator */}
      {showZoomIndicator && (
        <div className="absolute top-1/2 left-1/2 z-20 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-black bg-opacity-75 px-4 py-2 text-2xl font-bold text-white transition-opacity">
          {Math.round(zoom * 100)}%
        </div>
      )}

      {/* Image container */}
      <div
        ref={containerRef}
        className="flex h-full w-full items-center justify-center p-4"
        onClick={handleImageClick}
      >
        <img
          ref={imageRef}
          src={`/api/gallery/photo/${photo.path}`}
          alt={photo.filename}
          className="max-h-full max-w-full object-contain select-none"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            cursor: zoom > 1.0 ? (isPanning ? 'grabbing' : 'grab') : 'default',
            transition: isPanning ? 'none' : 'transform 0.1s ease-out',
          }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          draggable={false}
        />
      </div>
    </div>
  )

  // Render into portal (append to body)
  return createPortal(lightboxContent, document.body)
}

export default PhotoLightbox
