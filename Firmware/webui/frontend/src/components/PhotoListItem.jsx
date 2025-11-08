import { getThumbnailUrl } from '../utils/api'

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
  /**
   * Format date for display
   * @param {string} isoDate - ISO date string
   * @returns {string} Formatted date
   */
  const formatDate = (isoDate) => {
    try {
      const date = new Date(isoDate)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return isoDate
    }
  }

  /**
   * Format file size for display
   * @param {number} bytes - File size in bytes
   * @returns {string} Formatted size (e.g., "1.5 MB")
   */
  const formatSize = (bytes) => {
    if (!bytes) return null

    const kb = bytes / 1024
    if (kb < 1024) {
      return `${kb.toFixed(1)} KB`
    }

    const mb = kb / 1024
    return `${mb.toFixed(1)} MB`
  }

  return (
    <button
      type="button"
      onClick={() => onClick(photo)}
      aria-label={`View photo: ${photo.filename}, taken on ${formatDate(photo.date)}`}
      className="flex gap-4 p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500 text-left w-full"
    >
      {/* Thumbnail */}
      <img
        src={getThumbnailUrl(photo.path)}
        alt={photo.filename}
        loading="lazy"
        onError={(e) => {
          // Fallback to gray placeholder on error
          e.target.src =
            'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="150"%3E%3Crect fill="%23e5e7eb" width="200" height="150"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" fill="%239ca3af" font-size="14"%3EImage Error%3C/text%3E%3C/svg%3E'
          e.target.onerror = null // Prevent infinite loop
        }}
        className="w-48 h-32 object-cover rounded flex-shrink-0"
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
