import React, { useState, useRef, useCallback, useMemo, memo } from 'react'
import ThumbnailSkeleton from './ThumbnailSkeleton'
import { HOVER_POPUP_CONFIG } from '../constants/config'
import { useSwipeNavigation } from '../hooks/useSwipeNavigation'

/**
 * ThumbnailGrid - 3x3 grid of photo thumbnails
 *
 * Displays a responsive grid of photo thumbnails with loading states,
 * progressive image loading, and click handlers. Used in hover popups
 * and cluster previews to show multiple photos at a location.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Array<Object>} [props.photos=[]] - Array of photo objects
 * @param {string} props.photos[].photo_id - Photo identifier (required)
 * @param {number} [props.photos[].lat] - Latitude coordinate
 * @param {number} [props.photos[].lon] - Longitude coordinate
 * @param {string} [props.photos[].timestamp] - Photo timestamp
 * @param {Array<string>} [props.photos[].tags] - Photo tags
 * @param {number} [props.maxPhotos=9] - Maximum photos to display in grid
 * @param {number} [props.thumbnailSize=128] - Size of each thumbnail in pixels
 * @param {Function} [props.onPhotoClick] - Callback when thumbnail is clicked
 * @param {boolean} [props.isLoading=false] - Show skeleton loaders
 * @param {string} [props.className=''] - Additional CSS classes
 * @param {boolean} [props.enableSwipe=false] - Enable swipe navigation for mobile
 * @param {boolean} [props.showPagination=false] - Show page indicators when swiping enabled
 *
 * @example
 * // Basic usage with photo array
 * <ThumbnailGrid
 *   photos={photos}
 *   onPhotoClick={(photo) => console.log('Clicked:', photo.photo_id)}
 * />
 *
 * @example
 * // Loading state with custom size
 * <ThumbnailGrid
 *   photos={photos}
 *   isLoading={true}
 *   thumbnailSize={256}
 *   maxPhotos={6}
 * />
 *
 * @example
 * // Empty state
 * <ThumbnailGrid photos={[]} />
 */

export interface ThumbnailGridPhoto {
  path: string
  filename?: string
  thumbnail_url?: string
  lat?: number
  lon?: number
  latitude?: number
  longitude?: number
  timestamp?: string
  tags?: string[]
}

export interface ThumbnailGridProps {
  photos?: ThumbnailGridPhoto[]
  maxPhotos?: number
  thumbnailSize?: number
  onPhotoClick?: (photo: ThumbnailGridPhoto) => void
  isLoading?: boolean
  className?: string
  enableSwipe?: boolean
  showPagination?: boolean
}

function ThumbnailGrid({
  photos = [],
  maxPhotos = HOVER_POPUP_CONFIG.MAX_PHOTOS,
  thumbnailSize = HOVER_POPUP_CONFIG.THUMBNAIL_SIZE,
  onPhotoClick,
  isLoading = false,
  className = '',
  enableSwipe = false,
  showPagination = false,
}: ThumbnailGridProps) {
  // State for keyboard navigation
  const [focusedIndex, setFocusedIndex] = useState(0)
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([])

  // Calculate grid columns from config (used for keyboard navigation)
  const gridColumns = HOVER_POPUP_CONFIG.GRID_SIZE

  // Mapping of grid sizes to Tailwind classes (required for JIT purging)
  const gridColsClass = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-4',
  }[gridColumns] || 'grid-cols-3'

  // Setup swipe navigation if enabled
  const { currentPage, totalPages, startIndex, endIndex, handlers } = useSwipeNavigation({
    totalItems: photos?.length || 0,
    visibleItems: maxPhotos,
  })

  // Memoize display photos and remaining count to avoid recalculation
  const { displayPhotos, remainingCount } = useMemo(() => {
    const display = enableSwipe
      ? photos?.slice(startIndex, endIndex) || []
      : photos?.slice(0, maxPhotos) || []

    const remaining = enableSwipe
      ? (photos?.length || 0) - endIndex
      : (photos?.length || 0) - maxPhotos

    return { displayPhotos: display, remainingCount: remaining }
  }, [photos, enableSwipe, startIndex, endIndex, maxPhotos])

  /**
   * Handle keyboard navigation within the grid
   * Supports arrow keys, Home, End, Enter, and Space
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
      const maxIndex = displayPhotos.length - 1
      let newIndex = index

      switch (e.key) {
        case 'ArrowRight':
          newIndex = Math.min(index + 1, maxIndex)
          break
        case 'ArrowLeft':
          newIndex = Math.max(index - 1, 0)
          break
        case 'ArrowDown':
          newIndex = Math.min(index + gridColumns, maxIndex)
          break
        case 'ArrowUp':
          newIndex = Math.max(index - gridColumns, 0)
          break
        case 'Home':
          newIndex = 0
          break
        case 'End':
          newIndex = maxIndex
          break
        case 'Enter':
        case ' ':
          e.preventDefault()
          onPhotoClick?.(displayPhotos[index])
          return
        default:
          return
      }

      e.preventDefault()
      setFocusedIndex(newIndex)
      buttonRefs.current[newIndex]?.focus()
    },
    [displayPhotos, onPhotoClick, gridColumns]
  )

  // Loading state - show skeleton loaders
  if (isLoading) {
    return (
      <div className={`grid ${gridColsClass} gap-1 ${className}`}>
        {Array.from({ length: maxPhotos }).map((_, index) => (
          <ThumbnailSkeleton key={index} size={thumbnailSize} />
        ))}
      </div>
    )
  }

  // Empty state - no photos available
  if (!photos || photos.length === 0) {
    return (
      <div className={`text-sm text-gray-500 text-center p-4 ${className}`}>
        No photos available
      </div>
    )
  }

  // Render photo grid
  return (
    <div className="relative">
      <div
        className={`grid ${gridColsClass} gap-1 ${className}`}
        {...(enableSwipe ? handlers : {})}
      >
        {displayPhotos.map((photo, index) => (
          <button
            key={photo.path}
            ref={(el) => { buttonRefs.current[index] = el }}
            type="button"
            tabIndex={index === focusedIndex ? 0 : -1}
            onClick={() => onPhotoClick?.(photo)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className="focus:outline-none focus:ring-2 focus:ring-blue-500 rounded overflow-hidden"
          >
            <img
              src={photo.thumbnail_url || `/api/gallery/thumbnail/${photo.path}?size=${thumbnailSize}`}
              alt={photo.filename || photo.path}
              loading="lazy"
              className="w-full h-full object-cover cursor-pointer hover:opacity-80 transition-opacity"
              style={{ width: thumbnailSize, height: thumbnailSize }}
            />
          </button>
        ))}
        {remainingCount > 0 && (
          <div className="col-span-3 text-xs text-gray-500 text-center mt-1">
            +{remainingCount} more photos
          </div>
        )}
      </div>

      {/* Pagination indicators (only shown when swipe is enabled and showPagination is true) */}
      {enableSwipe && showPagination && totalPages > 1 && (
        <div className="flex justify-center gap-1 mt-2">
          {Array.from({ length: totalPages }).map((_, index) => (
            <div
              key={index}
              className={`w-2 h-2 rounded-full transition-colors ${
                index === currentPage ? 'bg-blue-500' : 'bg-gray-300'
              }`}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default memo(ThumbnailGrid)
