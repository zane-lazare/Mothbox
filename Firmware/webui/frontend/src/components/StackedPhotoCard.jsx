import PropTypes from 'prop-types'
import { useCallback } from 'react'
import LazyImage from './LazyImage'
import { GALLERY_CONFIG } from '../constants/config'

/**
 * StackedPhotoCard Component
 *
 * Displays a photo series (HDR, Focus Bracket) as visually stacked cards.
 * Shows up to 3 photos with offset layers and a badge indicating count and type.
 *
 * Visual Design:
 * ┌─────────────────┐  ← Photo 3 (back, offset +8px X/Y)
 * │ ┌─────────────┐ │  ← Photo 2 (middle, offset +4px X/Y)
 * │ │ ┌─────────┐ │ │  ← Photo 1 (front, cover photo)
 * │ │ │         │ │ │
 * │ │ │  Cover  │ │ │
 * │ │ │  Photo  │ │ │
 * │ │ │         │ │ │
 * │ │ │  [3 HDR]│ │ │  ← Series badge
 * │ │ └─────────┘ │ │
 * │ └─────────────┘ │
 * └─────────────────┘
 *
 * @param {Object} props - Component props
 * @param {Object} props.series - Series data object
 * @param {string} props.series.series_id - Unique series identifier
 * @param {string} props.series.series_type - Series type ('hdr' or 'focus_bracket')
 * @param {Array} props.series.photos - Array of photo objects in the series
 * @param {number} props.series.count - Total number of photos in series
 * @param {string} props.series.cover_photo - Path to the cover photo
 * @param {Function} [props.onCardClick] - Handler when card is clicked (receives series)
 * @param {Function} [props.onPhotoClick] - Handler when opening photo (receives cover photo)
 * @param {boolean} [props.isLoading=false] - Show loading skeleton state
 */
export default function StackedPhotoCard({
  series,
  onCardClick,
  onPhotoClick,
  isLoading = false,
}) {
  const { series_type, photos, count } = series

  // Get up to 3 photos for stacking
  const stackedPhotos = photos.slice(0, 3)

  // Format series type for display
  const formatSeriesType = (type) => {
    switch (type) {
      case 'hdr':
        return 'HDR'
      case 'focus_bracket':
        return 'FB'
      default:
        return type
    }
  }

  // Format ARIA label for accessibility
  const getAriaLabel = () => {
    const typeLabel = series_type === 'focus_bracket' ? 'Focus bracket' : 'HDR'
    return `${typeLabel} series: ${count} photos`
  }

  // Handle click on the card
  const handleClick = useCallback(() => {
    if (onPhotoClick && photos.length > 0) {
      onPhotoClick(photos[0])
    }
    if (onCardClick) {
      onCardClick(series)
    }
  }, [onCardClick, onPhotoClick, series, photos])

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        handleClick()
      }
    },
    [handleClick]
  )

  // Loading skeleton state
  if (isLoading) {
    return (
      <div className="relative w-full h-64">
        {/* Skeleton stacked layers */}
        <div className="absolute inset-0 transform translate-x-2 translate-y-2 rounded-lg bg-gray-200 animate-pulse" />
        <div className="absolute inset-0 transform translate-x-1 translate-y-1 rounded-lg bg-gray-200 animate-pulse" />
        <div className="absolute inset-0 rounded-lg bg-gray-300 animate-pulse" />
      </div>
    )
  }

  // Handle empty series edge case
  if (!photos || photos.length === 0) {
    return (
      <div
        role="group"
        aria-label={getAriaLabel()}
        tabIndex={0}
        className="relative w-full h-64 cursor-pointer group focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg active:scale-[0.98] transition-transform touch-manipulation"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
      >
        <div className="absolute inset-0 rounded-lg bg-gray-200 flex items-center justify-center">
          <span className="text-gray-500">Empty series</span>
        </div>
      </div>
    )
  }

  // Z-index values for proper stacking order (back to front)
  const zIndexClasses = ['z-10', 'z-20', 'z-30']
  // Offset values for stacked effect (back to front)
  const offsets = [
    'translate-x-2 translate-y-2',
    'translate-x-1 translate-y-1',
    'translate-x-0 translate-y-0',
  ]
  // Shadow intensity (back to front)
  const shadows = ['shadow-sm', 'shadow-md', 'shadow-lg']

  // Reverse for rendering (back layers first, front last)
  const renderOrder = [...stackedPhotos].reverse()

  return (
    <div
      role="group"
      aria-label={getAriaLabel()}
      tabIndex={0}
      className="relative w-full h-64 cursor-pointer group focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg active:scale-[0.98] transition-transform touch-manipulation"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
    >
      {/* Stacked photo layers */}
      {renderOrder.map((photo, renderIndex) => {
        // Calculate actual index (reverse of render order)
        const actualIndex = stackedPhotos.length - 1 - renderIndex
        const zIndex = zIndexClasses[actualIndex] || 'z-10'
        const offset = offsets[actualIndex] || offsets[0]
        const shadow = shadows[actualIndex] || shadows[0]
        const isFront = actualIndex === stackedPhotos.length - 1

        return (
          <div
            key={photo.path}
            className={`absolute inset-0 transform ${offset} rounded-lg overflow-hidden ${shadow} ${zIndex} ${
              isFront
                ? 'transition-transform duration-200 group-hover:scale-[1.02] group-focus:scale-[1.02]'
                : ''
            }`}
          >
            <LazyImage
              photo={photo}
              size={GALLERY_CONFIG.THUMBNAIL.SIZE}
              alt={photo.filename}
              className="w-full h-full object-cover"
              aspectRatio={GALLERY_CONFIG.THUMBNAIL.ASPECT_RATIO}
            />
          </div>
        )
      })}

      {/* Series badge - bottom right corner */}
      <div className="absolute bottom-2 right-2 z-40 px-2 py-1 bg-black/70 text-white text-xs font-medium rounded">
        {count} {formatSeriesType(series_type)}
      </div>
    </div>
  )
}

StackedPhotoCard.propTypes = {
  series: PropTypes.shape({
    series_id: PropTypes.string.isRequired,
    series_type: PropTypes.string.isRequired,
    photos: PropTypes.arrayOf(
      PropTypes.shape({
        path: PropTypes.string.isRequired,
        filename: PropTypes.string.isRequired,
        date: PropTypes.string,
      })
    ).isRequired,
    count: PropTypes.number.isRequired,
    cover_photo: PropTypes.string,
  }).isRequired,
  onCardClick: PropTypes.func,
  onPhotoClick: PropTypes.func,
  isLoading: PropTypes.bool,
}
