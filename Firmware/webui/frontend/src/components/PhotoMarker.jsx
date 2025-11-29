import { Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { MAP_CONFIG } from '@/constants/config'

// Import marker icons
import icon from 'leaflet/dist/images/marker-icon.png'
import iconShadow from 'leaflet/dist/images/marker-shadow.png'

// Fix default Leaflet marker icon issue in React
// https://github.com/Leaflet/Leaflet/issues/4968
let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})

L.Marker.prototype.options.icon = DefaultIcon

/**
 * PhotoMarker Component
 *
 * Displays a marker on the map with a popup showing the photo thumbnail.
 * Clicking the marker or the "View" button opens the lightbox.
 *
 * @param {Object} location - Photo location data
 * @param {string} location.photo_path - Photo file path (e.g., "2024-11-10/photo_001.jpg")
 * @param {string} location.filename - Photo filename
 * @param {number} location.latitude - Photo latitude coordinate
 * @param {number} location.longitude - Photo longitude coordinate
 * @param {string} [location.thumbnail_url] - Thumbnail URL (optional)
 * @param {Function} [onClick] - Callback when marker/button clicked (receives location object)
 */
export default function PhotoMarker({ location, onClick }) {
  const { latitude, longitude, filename, thumbnail_url } = location

  const handleMarkerClick = () => {
    if (onClick) {
      onClick(location)
    }
  }

  const handleViewClick = (e) => {
    e.preventDefault()
    if (onClick) {
      onClick(location)
    }
  }

  return (
    <Marker
      position={[latitude, longitude]}
      eventHandlers={{
        click: handleMarkerClick,
      }}
    >
      <Popup maxWidth={MAP_CONFIG.POPUP.MAX_WIDTH}>
        <div className="flex flex-col items-center gap-2">
          {thumbnail_url && (
            <img
              src={thumbnail_url}
              alt={filename}
              style={{
                width: `${MAP_CONFIG.POPUP.THUMBNAIL_SIZE}px`,
                height: 'auto',
              }}
              className="rounded shadow-sm"
            />
          )}

          <div className="text-sm text-gray-700 font-medium text-center">{filename}</div>

          <button
            onClick={handleViewClick}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-sm"
          >
            View
          </button>
        </div>
      </Popup>
    </Marker>
  )
}
