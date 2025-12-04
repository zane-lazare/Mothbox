import { useState, memo, useCallback } from 'react'
import { GALLERY_CONFIG } from '../constants/config'
import ProgressiveImage from './ProgressiveImage'
import QuickTagButton from './gallery/QuickTagButton'

/**
 * PhotoGridItem Component
 *
 * Grid view photo card with thumbnail, hover overlay, and quick-tag button.
 * Used in gallery grid view for compact photo display.
 * Features progressive loading with blur-up effect for smooth UX.
 *
 * @param {Object} props - Component props
 * @param {Object} props.photo - Photo data object
 * @param {string} props.photo.path - Photo file path
 * @param {string} props.photo.filename - Photo filename
 * @param {string} props.photo.date - ISO date string
 * @param {Function} props.onClick - Click handler for viewing photo
 */
function PhotoGridItem({ photo, onClick }) {
  const [isHovered, setIsHovered] = useState(false)
  const [isTagDropdownOpen, setIsTagDropdownOpen] = useState(false)

  const handlePhotoClick = useCallback(() => {
    if (isTagDropdownOpen) {
      // Close dropdown when clicking photo area
      setIsTagDropdownOpen(false)
    } else {
      onClick(photo)
    }
  }, [isTagDropdownOpen, onClick, photo])

  return (
    <div
      className="relative group"
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

      {/* Quick Tag Button - positioned in top-right */}
      <div
        className={`
          absolute top-2 right-2 z-10
          transition-opacity duration-150
          ${isHovered || isTagDropdownOpen ? 'opacity-100' : 'opacity-0'}
        `}
      >
        <QuickTagButton
          filename={photo.filename}
          onDropdownOpenChange={setIsTagDropdownOpen}
        />
      </div>
    </div>
  )
}

export default memo(PhotoGridItem)
