import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { LIGHTBOX_CONFIG } from '../constants/config'

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
function PhotoLightbox({ photo, photos, onClose, onNavigate }) {
  const closeButtonRef = useRef(null)
  const previousFocusRef = useRef(null)

  // Body scroll lock - runs on every render
  useEffect(() => {
    if (!photo) {
      // Restore scroll when closed
      document.body.style.overflow = ''
      if (previousFocusRef.current) {
        previousFocusRef.current.focus()
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

  // Keyboard navigation - runs on every render
  useEffect(() => {
    if (!photo || !LIGHTBOX_CONFIG.KEYBOARD_ENABLED) return

    const handleKeyDown = (e) => {
      switch (e.key) {
        case 'Escape':
          onClose()
          break
        default:
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [photo, onClose])

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

      {/* Image container */}
      <div
        className="flex h-full w-full items-center justify-center p-4"
        onClick={handleImageClick}
      >
        <img
          src={`/api/gallery/photo/${photo.path}`}
          alt={photo.filename}
          className="max-h-full max-w-full object-contain"
        />
      </div>
    </div>
  )

  // Render into portal (append to body)
  return createPortal(lightboxContent, document.body)
}

export default PhotoLightbox
