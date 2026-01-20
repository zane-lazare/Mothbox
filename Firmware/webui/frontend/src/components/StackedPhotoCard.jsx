import PropTypes from 'prop-types'
import { useCallback, memo, useRef, useEffect } from 'react'
import LazyImage from './LazyImage'
import { GALLERY_CONFIG, STACKED_CARD_CONFIG, Z_INDEX } from '../constants/config'
import useSelection from '../hooks/useSelection'

const { Z_INDEX_CLASSES, OFFSETS, SHADOWS } = STACKED_CARD_CONFIG

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
function StackedPhotoCard({
  series,
  onCardClick,
  onPhotoClick,
  isLoading = false,
}) {
  // === ALL HOOKS MUST BE CALLED BEFORE ANY CONDITIONAL RETURNS ===
  // React's rules of hooks require hooks to be called in the same order every render

  const checkboxRef = useRef(null)

  // Get selection state from context
  // Note: This will throw if not wrapped in SelectionProvider, which is the correct behavior
  // The component should be wrapped in SelectionProvider at the app level
  const selectionState = useSelection()

  // Derive values safely (series may be null/undefined)
  const photos = series?.photos || []
  const count = series?.count || 0
  const series_type = series?.series_type || ''

  // Get up to 3 photos for stacking
  const stackedPhotos = photos.slice(0, 3)

  // Extract cover photo for stable useCallback dependency
  // Normalize to object format (series API returns strings, not objects)
  const rawCoverPhoto = stackedPhotos[0]
  const coverPhoto = rawCoverPhoto
    ? (typeof rawCoverPhoto === 'string'
        ? { path: rawCoverPhoto, filename: rawCoverPhoto.split('/').pop() }
        : rawCoverPhoto)
    : null

  // Selection mode state (with safe defaults)
  const isSelectMode = selectionState?.isSelectMode || false
  const selectPhoto = selectionState?.selectPhoto
  const deselectPhoto = selectionState?.deselectPhoto
  const isSelected = selectionState?.isSelected

  // Get all photo paths in series (handle both string and object formats)
  const seriesPhotoPaths = photos.map(photo =>
    typeof photo === 'string' ? photo : photo.path
  )

  // Check selection state of series
  const selectedInSeries = seriesPhotoPaths.filter(path => isSelected?.(path))
  const allSelected = selectedInSeries.length === seriesPhotoPaths.length && seriesPhotoPaths.length > 0
  const someSelected = selectedInSeries.length > 0 && !allSelected
  const noneSelected = selectedInSeries.length === 0

  // Update checkbox indeterminate state when selection changes
  useEffect(() => {
    if (checkboxRef.current) {
      checkboxRef.current.indeterminate = someSelected
    }
  }, [someSelected])

  // Handle series selection toggle
  const handleSeriesSelection = useCallback((e) => {
    e.stopPropagation()

    if (!selectPhoto || !deselectPhoto) return

    if (allSelected) {
      // Deselect all in series
      seriesPhotoPaths.forEach(path => deselectPhoto(path))
    } else {
      // Select all in series (up to MAX_SELECTION)
      seriesPhotoPaths.forEach(path => {
        if (!isSelected?.(path)) {
          selectPhoto(path)
        }
      })
    }
  }, [allSelected, seriesPhotoPaths, selectPhoto, deselectPhoto, isSelected])

  // Handle click on the card
  const handleClick = useCallback(() => {
    // In select mode, clicking card toggles series selection
    if (isSelectMode) {
      handleSeriesSelection({ stopPropagation: () => {} })
      return
    }

    // Normal mode: open lightbox
    if (onPhotoClick && coverPhoto) {
      onPhotoClick(coverPhoto)
    }
    if (onCardClick) {
      onCardClick(series)
    }
  }, [isSelectMode, handleSeriesSelection, onCardClick, onPhotoClick, coverPhoto, series])

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

  // === CONDITIONAL RETURNS AFTER ALL HOOKS ===

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

  // Guard against undefined/null series after loading
  if (!series) {
    return null
  }

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

  // Reverse for rendering (back layers first, front last)
  const renderOrder = [...stackedPhotos].reverse()

  // Determine selection visual state
  const hasSelectedPhotos = !noneSelected
  const cardClassName = `relative w-full h-64 cursor-pointer group focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg active:scale-[0.98] transition-transform touch-manipulation ${
    hasSelectedPhotos && isSelectMode ? 'ring-4 ring-blue-600 ring-offset-2' : ''
  }`

  return (
    <div
      role="group"
      aria-label={getAriaLabel()}
      tabIndex={0}
      className={cardClassName}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
    >
      {/* Stacked photo layers */}
      {renderOrder.map((photo, renderIndex) => {
        // Calculate actual index (reverse of render order)
        const actualIndex = stackedPhotos.length - 1 - renderIndex
        const zIndex = Z_INDEX_CLASSES[actualIndex] || 'z-10'
        const offset = OFFSETS[actualIndex] || OFFSETS[0]
        const shadow = SHADOWS[actualIndex] || SHADOWS[0]
        const isFront = actualIndex === stackedPhotos.length - 1
        // Normalize photo to object format (series API returns strings, not objects)
        const photoObj = typeof photo === 'string'
          ? { path: photo, filename: photo.split('/').pop() }
          : photo

        return (
          <div
            key={photoObj.path}
            className={`absolute inset-0 transform ${offset} rounded-lg overflow-hidden ${shadow} ${zIndex} ${
              isFront
                ? 'transition-transform duration-200 group-hover:scale-[1.02] group-focus:scale-[1.02]'
                : ''
            }`}
          >
            <LazyImage
              photo={photoObj}
              size={GALLERY_CONFIG.THUMBNAIL.SIZE}
              alt={photoObj.filename}
              className="w-full h-full object-cover"
              aspectRatio={GALLERY_CONFIG.THUMBNAIL.ASPECT_RATIO}
            />
          </div>
        )
      })}

      {/* Selection checkbox - top left corner (only in select mode) */}
      {isSelectMode && (
        <div className={`absolute top-2 left-2 ${Z_INDEX.MODAL}`}>
          <input
            type="checkbox"
            ref={checkboxRef}
            checked={allSelected}
            onChange={handleSeriesSelection}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select all ${count} photos in series`}
            className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
        </div>
      )}

      {/* Series badge - bottom right corner */}
      <div className={`absolute bottom-2 right-2 ${Z_INDEX.TOOLBAR} px-2 py-1 bg-black/80 text-white text-xs font-medium rounded`}>
        {count} {formatSeriesType(series_type)}
      </div>
    </div>
  )
}

StackedPhotoCard.propTypes = {
  /** Series data - can be null/undefined (component returns null in that case) */
  series: PropTypes.shape({
    series_id: PropTypes.string.isRequired,
    series_type: PropTypes.string.isRequired,
    photos: PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.string, // Series API returns paths as strings
        PropTypes.shape({
          path: PropTypes.string.isRequired,
          filename: PropTypes.string.isRequired,
          date: PropTypes.string,
        }),
      ])
    ).isRequired,
    count: PropTypes.number.isRequired,
    cover_photo: PropTypes.string,
  }),
  onCardClick: PropTypes.func,
  onPhotoClick: PropTypes.func,
  isLoading: PropTypes.bool,
}

export default memo(StackedPhotoCard)
