import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatGPSCoordinate, formatDecimalCoordinate, formatAltitude } from '../../utils/metadataFormatters';

/**
 * LocationTab Component
 *
 * Displays GPS location information including decimal coordinates, DMS format,
 * altitude (for 3D fixes), and GPS quality indicators. Provides a map link
 * for visualizing the location on Google Maps.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Object|null} props.data - Full metadata object from backend API
 * @param {Object} [props.data.location] - GPS location metadata
 * @param {number} [props.data.location.latitude] - Latitude in decimal degrees
 * @param {number} [props.data.location.longitude] - Longitude in decimal degrees
 * @param {number} [props.data.location.altitude] - Altitude in meters (only for 3D fix)
 * @param {string} [props.data.location.gps_timestamp] - GPS timestamp
 * @param {number} [props.data.location.satellites] - Number of satellites used
 * @param {number} [props.data.location.hdop] - Horizontal dilution of precision
 *
 * @example
 * const metadata = {
 *   location: {
 *     latitude: 40.7128,
 *     longitude: -74.0060,
 *     altitude: 10.5,
 *     satellites: 8,
 *     hdop: 1.2
 *   }
 * };
 *
 * <LocationTab data={metadata} />
 */
const LocationTab = ({ data }) => {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <p>No GPS information available</p>
      </div>
    );
  }

  const location = data.location || {};

  // Check if data is valid and has GPS fix
  const hasValidGPS = location.latitude !== undefined &&
    location.latitude !== null &&
    location.longitude !== undefined &&
    location.longitude !== null;

  if (!hasValidGPS) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <p>No GPS information available</p>
      </div>
    );
  }

  const { latitude, longitude, altitude, satellites, hdop } = location;

  // Format coordinates in DMS format with cardinal directions using utility function
  const latDMS = formatGPSCoordinate(latitude, 'lat');
  const lonDMS = formatGPSCoordinate(longitude, 'lon');

  // Create Google Maps link with properly encoded coordinates to prevent XSS
  const mapsUrl = `https://www.google.com/maps?q=${encodeURIComponent(latitude)},${encodeURIComponent(longitude)}`;

  // Only show altitude if available
  const showAltitude = altitude !== undefined && altitude !== null;

  return (
    <div className="space-y-6">
      {/* Decimal Degrees Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Decimal Degrees
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Latitude"
            value={`${formatDecimalCoordinate(latitude)}°`}
            copyable={true}
          />
          <MetadataField
            label="Longitude"
            value={`${formatDecimalCoordinate(longitude)}°`}
            copyable={true}
          />
          {showAltitude && (
            <MetadataField
              label="Altitude"
              value={formatAltitude(altitude)}
              copyable={true}
            />
          )}
        </div>
      </div>

      {/* DMS Format Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Degrees, Minutes, Seconds (DMS)
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Latitude"
            value={latDMS}
          />
          <MetadataField
            label="Longitude"
            value={lonDMS}
          />
        </div>
      </div>

      {/* GPS Quality Indicators */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          GPS Quality
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Satellites"
            value={satellites !== undefined && satellites !== null ? satellites.toString() : 'N/A'}
          />
          <MetadataField
            label="HDOP"
            value={hdop !== undefined && hdop !== null ? hdop.toString() : 'N/A'}
          />
        </div>
      </div>

      {/* Map Link */}
      <div className="pt-2">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z"
            />
          </svg>
          View on Map
        </a>
      </div>
    </div>
  );
};

LocationTab.propTypes = {
  data: PropTypes.shape({
    location: PropTypes.shape({
      latitude: PropTypes.number,
      longitude: PropTypes.number,
      altitude: PropTypes.number,
      gps_timestamp: PropTypes.string,
      satellites: PropTypes.number,
      hdop: PropTypes.number,
    }),
  }),
};

export default LocationTab;
