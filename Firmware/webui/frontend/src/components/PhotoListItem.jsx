import { useState, memo, useCallback } from 'react'
import { formatDate, formatSize } from '../utils/helpers'
import ProgressiveImage from './ProgressiveImage'
import QuickTagButton from './gallery/QuickTagButton'
import { useSelectionContext } from '../contexts/SelectionContext'
import { Z_INDEX } from '../constants/config'

/**
 * PhotoListItem Component
 *
 * List view photo card with horizontal layout showing thumbnail + metadata.
 * Used in gallery list view to display photos with more detail than grid view.
 * Features progressive loading with blur-up effect for smooth UX.
 * Supports selection mode with checkbox overlay for bulk operations.
 *
 * @param {Object} props - Component props
 * @param {Object} props.photo - Photo data object
 * @param {string} props.photo.path - Photo file path
 * @param {string} props.photo.filename - Photo filename
 * @param {string} props.photo.date - ISO date string
 * @param {number} [props.photo.size] - File size in bytes (optional)
 * @param {Function} props.onClick - Click handler for viewing photo (disabled in select mode)
 * @param {number} [props.index] - Photo index in list (required for Shift+Click range selection)
 * @param {Array} [props.photos] - All photos array (required for Shift+Click range selection)
 */
function PhotoListItem({ photo, onClick, index, photos }) {
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
        onClick={handlePhotoClick}
        aria-label={`View photo: ${photo.filename}, taken on ${formatDate(photo.date)}`}
        className="flex gap-4 p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500 text-left w-full"
      >
        {/* Thumbnail with progressive loading */}
        <div className="relative flex-shrink-0">
          <ProgressiveImage
            photoPath={photo.path}
            alt={photo.filename}
            className="w-48 h-32 object-cover rounded"
            iconSize={80}
            thumbnailSize={64}
            fullSize={256}
          />
          {/* Hover overlay on thumbnail */}
          <div className="absolute inset-0 bg-transparent group-hover:bg-black/20 group-focus-within:bg-black/20 transition-all rounded pointer-events-none" />
        </div>

        {/* Metadata */}
        <div className="flex flex-col justify-center min-w-0 flex-1">
          <h3 className="text-lg font-semibold text-gray-900 truncate">{photo.filename}</h3>
          <p className="text-sm text-gray-600 mt-1">{formatDate(photo.date)}</p>
          {photo.size && <p className="text-sm text-gray-500 mt-1">{formatSize(photo.size)}</p>}
        </div>
      </button>

      {/* Checkbox - positioned in top-left of thumbnail (only in select mode) */}
      {isSelectMode && (
        <div className={`absolute top-6 left-6 ${Z_INDEX.PHOTO_CONTROLS}`}>
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
          absolute top-4 right-4 ${Z_INDEX.PHOTO_CONTROLS}
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

export default memo(PhotoListItem)
