import { useState, memo, useCallback } from 'react'
import { GALLERY_CONFIG, Z_INDEX } from '../constants/config'
import ProgressiveImage from './ProgressiveImage'
import QuickTagButton from './gallery/QuickTagButton'
import PhotoContextMenu from './gallery/PhotoContextMenu'
import { useSelectionContext } from '../contexts/SelectionContext'

export interface PhotoGridItemPhoto {
  path: string
  filename: string
  date: string
  size?: number
  timestamp?: number
}

export interface PhotoGridItemProps {
  photo: PhotoGridItemPhoto
  onClick?: (photo: PhotoGridItemPhoto) => void
  index?: number
  photos?: PhotoGridItemPhoto[]
}

/**
 * PhotoGridItem Component
 *
 * Grid view photo card with thumbnail, hover overlay, and quick-tag button.
 * Used in gallery grid view for compact photo display.
 * Features progressive loading with blur-up effect for smooth UX.
 * Supports selection mode with checkbox overlay for bulk operations.
 */
function PhotoGridItem({ photo, onClick, index, photos }: PhotoGridItemProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [isTagDropdownOpen, setIsTagDropdownOpen] = useState(false)
  const [contextMenuOpen, setContextMenuOpen] = useState(false)
  const [contextMenuPosition, setContextMenuPosition] = useState({ x: 0, y: 0 })

  // Use selection context directly (returns null when not in provider)
  const selectionContext = useSelectionContext()

  const isSelectMode = selectionContext?.isSelectMode || false
  const isSelected = selectionContext?.isSelected(photo.path) || false
  const togglePhoto = selectionContext?.togglePhoto
  const selectRange = selectionContext?.selectRange

  const handlePhotoClick = useCallback((e: React.MouseEvent) => {
    // In select mode, clicking photo toggles selection (not lightbox)
    if (isSelectMode && togglePhoto) {
      e.stopPropagation()

      // Handle Shift+Click for range selection
      if (e.shiftKey && index !== undefined && photos && selectRange) {
        selectRange(index, photos.map(p => p.path))
      } else {
        togglePhoto(photo.path, index ?? 0)
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

  const handleCheckboxChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation()
    if (togglePhoto) {
      // Handle Shift+Click for range selection on checkbox
      if ((e.nativeEvent as MouseEvent).shiftKey && index !== undefined && photos && selectRange) {
        selectRange(index, photos.map(p => p.path))
      } else {
        togglePhoto(photo.path, index ?? 0)
      }
    }
  }, [togglePhoto, selectRange, photo.path, index, photos])

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()  // Prevent browser context menu
    setContextMenuPosition({ x: e.clientX, y: e.clientY })
    setContextMenuOpen(true)
  }, [])

  return (
    <div
      className={`
        relative group
        ${isSelectMode && isSelected ? 'ring-2 ring-blue-500 ring-offset-2 rounded-lg' : ''}
      `}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onContextMenu={handleContextMenu}
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

      {/* Context Menu */}
      <PhotoContextMenu
        photo={photo as any}
        isOpen={contextMenuOpen}
        onClose={() => setContextMenuOpen(false)}
        position={contextMenuPosition}
      />
    </div>
  )
}

export default memo(PhotoGridItem)
