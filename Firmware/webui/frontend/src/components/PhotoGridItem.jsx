import { useState, memo, useCallback } from 'react'
import { GALLERY_CONFIG, Z_INDEX } from '../constants/config'
import ProgressiveImage from './ProgressiveImage'
import QuickTagButton from './gallery/QuickTagButton'
import { useSelectionContext } from '../contexts/SelectionContext'

/**
 * PhotoGridItem Component
 *
 * Grid view photo card with thumbnail, hover overlay, and quick-tag button.
 * Used in gallery grid view for compact photo display.
 * Features progressive loading with blur-up effect for smooth UX.
 * Supports selection mode with checkbox overlay for bulk operations.
 *
 * @param {Object} props - Component props
 * @param {Object} props.photo - Photo data object
 * @param {string} props.photo.path - Photo file path
 * @param {string} props.photo.filename - Photo filename
 * @param {string} props.photo.date - ISO date string
 * @param {Function} props.onClick - Click handler for viewing photo (disabled in select mode)
 * @param {number} [props.index] - Photo index in grid (required for Shift+Click range selection)
 * @param {Array} [props.photos] - All photos array (required for Shift+Click range selection)
 */
function PhotoGridItem({ photo, onClick, index, photos }) {
  const [isHovered, setIsHovered] = useState(false)
  const [isTagDropdownOpen, setIsTagDropdownOpen] = useState(false)

  // Use selection context directly (returns null when not in provider)
  const selectionContext = useSelectionContext()

  const isSelectMode = selectionContext?.isSelectMode || false
  const isSelected = selectionContext?.isSelected(photo.path) || false
  const togglePhoto = selectionContext?.togglePhoto
  const selectRange = selectionContext?.selectRange

  const handlePhotoClick = useCallback((e) => {
    // In select mode, clicking photo toggles selection (not lightbox)
    if (isSelectMode && togglePhoto) {
      e.stopPropagation()

      // Handle Shift+Click for range selection
      if (e.shiftKey && index !== undefined && photos && selectRange) {
        selectRange(index, photos.map(p => p.path))
      } else {
        togglePhoto(photo.path, index)
      }
      return
    }

    // Normal mode: handle tag dropdown and lightbox
    if (isTagDropdownOpen) {
      // Close dropdown when clicking photo area
      setIsTagDropdownOpen(false)
    } else {
      onClick?.(photo)
    }
  }, [isSelectMode, isTagDropdownOpen, togglePhoto, selectRange, photo, index, photos, onClick])

  const handleCheckboxChange = useCallback((e) => {
    e.stopPropagation()
    if (togglePhoto) {
      togglePhoto(photo.path, index)
    }
  }, [togglePhoto, photo.path, index])

  return (
    <div
      className={`
        relative group
        ${isSelectMode && isSelected ? 'ring-2 ring-blue-500 ring-offset-2 rounded-lg' : ''}
      `}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <button
        type="button"
        className="cursor-pointer w-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
        onClick={handlePhotoClick}
        aria-label={`View photo: ${photo.filename}, taken on ${new Date(photo.date).toLocaleString()}`}
      >
        <ProgressiveImage
          photoPath={photo.path}
          alt={photo.filename}
          className={`w-full ${GALLERY_CONFIG.LAYOUT.PHOTO_HEIGHT} object-cover rounded-lg shadow hover:shadow-lg transition-shadow`}
          thumbnailSize={GALLERY_CONFIG.THUMBNAIL.SIZE}
          fullSize={256}
        />
        <div className="absolute inset-0 bg-transparent group-hover:bg-black/30 group-focus-within:bg-black/30 transition-all rounded-lg flex items-center justify-center pointer-events-none">
          <span className="text-white opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 text-sm">
            View
          </span>
        </div>
      </button>

      {/* Checkbox - positioned in top-left (only in select mode) */}
      {isSelectMode && (
        <div className={`absolute top-2 left-2 ${Z_INDEX.PHOTO_CONTROLS}`}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={handleCheckboxChange}
            onClick={(e) => e.stopPropagation()}
            aria-label={`Select ${photo.filename}`}
            className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
        </div>
      )}

      {/* Quick Tag Button - positioned in top-right */}
      <div
        className={`
          absolute top-2 right-2 ${Z_INDEX.PHOTO_CONTROLS}
          transition-opacity duration-150
          ${isHovered || isTagDropdownOpen ? 'opacity-100' : 'opacity-0'}
        `}
      >
        <QuickTagButton
          filename={photo.path}
          onDropdownOpenChange={setIsTagDropdownOpen}
        />
      </div>
    </div>
  )
}

export default memo(PhotoGridItem)
