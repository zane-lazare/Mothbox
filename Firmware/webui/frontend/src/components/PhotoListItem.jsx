import { getThumbnailUrl } from '../utils/api'
import { formatDate, formatSize } from '../utils/helpers'
import ProgressiveImage from './ProgressiveImage'

/**
 * PhotoListItem Component
 *
 * List view photo card with horizontal layout showing thumbnail + metadata.
 * Used in gallery list view to display photos with more detail than grid view.
 *
 * @param {Object} props - Component props
 * @param {Object} props.photo - Photo data object
 * @param {string} props.photo.path - Photo file path
 * @param {string} props.photo.filename - Photo filename
 * @param {string} props.photo.date - ISO date string
 * @param {number} [props.photo.size] - File size in bytes (optional)
 * @param {Function} props.onClick - Click handler for viewing photo
 */
export default function PhotoListItem({ photo, onClick }) {
  return (
    <button
      type="button"
      onClick={() => onClick(photo)}
      aria-label={`View photo: ${photo.filename}, taken on ${formatDate(photo.date)}`}
      className="flex gap-4 p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500 text-left w-full"
    >
      {/* Thumbnail */}
      <ProgressiveImage
        src={getThumbnailUrl(photo.path)}
        alt={photo.filename}
        className="w-48 h-32 object-cover rounded flex-shrink-0"
        iconSize={80}
      />

      {/* Metadata */}
      <div className="flex flex-col justify-center min-w-0 flex-1">
        <h3 className="text-lg font-semibold text-gray-900 truncate">{photo.filename}</h3>
        <p className="text-sm text-gray-600 mt-1">{formatDate(photo.date)}</p>
        {photo.size && <p className="text-sm text-gray-500 mt-1">{formatSize(photo.size)}</p>}
      </div>
    </button>
  )
}
