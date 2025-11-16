import { GALLERY_CONFIG } from '../constants/config'
import ProgressiveImage from './ProgressiveImage'

/**
 * PhotoGridItem Component
 *
 * Grid view photo card with thumbnail and hover overlay.
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
export default function PhotoGridItem({ photo, onClick }) {
  return (
    <button
      type="button"
      className="cursor-pointer group relative focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-lg"
      onClick={() => onClick(photo)}
      aria-label={`View photo: ${photo.filename}, taken on ${new Date(photo.date).toLocaleString()}`}
    >
      <ProgressiveImage
        photoPath={photo.path}
        alt={photo.filename}
        className={`w-full ${GALLERY_CONFIG.LAYOUT.PHOTO_HEIGHT} object-cover rounded-lg shadow hover:shadow-lg transition-shadow`}
        thumbnailSize={GALLERY_CONFIG.THUMBNAIL.SIZE}
        fullSize={256}
      />
      <div className="absolute inset-0 bg-transparent group-hover:bg-black/30 group-focus:bg-black/30 transition-all rounded-lg flex items-center justify-center pointer-events-none">
        <span className="text-white opacity-0 group-hover:opacity-100 group-focus:opacity-100 text-sm">
          View
        </span>
      </div>
    </button>
  )
}
