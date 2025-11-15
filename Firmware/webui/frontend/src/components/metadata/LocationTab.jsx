import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatGPSCoordinate, formatAltitude } from '../../utils/metadataFormatters';

/**
 * LocationTab Component
 *
 * Displays GPS location information including decimal coordinates, DMS format,
 * altitude (for 3D fixes), and GPS quality indicators. Provides a map link
 * for visualizing the location on Google Maps.
 *
 * @component
 * @param {Object} props - Component props
 * @param {Object|null} props.data - GPS location metadata object
 * @param {number} [props.data.lat] - Latitude in decimal degrees
 * @param {number} [props.data.lon] - Longitude in decimal degrees
 * @param {number} [props.data.gps_fix_mode] - GPS fix mode (0=no fix, 1=no fix, 2=2D, 3=3D)
 * @param {number} [props.data.alt] - Altitude in meters (only shown for 3D fix)
 * @param {number} [props.data.gps_satellites_used] - Number of satellites used
 * @param {number} [props.data.gps_hdop] - Horizontal dilution of precision
 * @param {number} [props.data.gps_pdop] - Position dilution of precision
 *
 * @example
 * const gpsData = {
 *   lat: 40.7128,
 *   lon: -74.0060,
 *   gps_fix_mode: 3,
 *   alt: 10.5,
 *   gps_satellites_used: 8,
 *   gps_hdop: 1.2,
 *   gps_pdop: 2.1
 * };
 *
 * <LocationTab data={gpsData} />
 */
const LocationTab = ({ data }) => {
  // Check if data is valid and has GPS fix
  const hasValidGPS = data &&
    data.lat !== undefined &&
    data.lat !== null &&
    data.lon !== undefined &&
    data.lon !== null &&
    data.gps_fix_mode > 0;

  if (!hasValidGPS) {
    return (
      <div className="flex items-center justify-center h-32 text-gray-500">
        <p>No GPS information available</p>
      </div>
    );
  }

  const { lat, lon, gps_fix_mode, alt, gps_satellites_used, gps_hdop, gps_pdop } = data;

  // Format coordinates in DMS format with cardinal directions using utility function
  const latDMS = formatGPSCoordinate(lat, 'lat');
  const lonDMS = formatGPSCoordinate(lon, 'lon');

  // Create Google Maps link
  const mapsUrl = `https://www.google.com/maps?q=${lat},${lon}`;

  // Only show altitude for 3D fix
  const showAltitude = gps_fix_mode === 3 && alt !== undefined && alt !== null;

  return (
    <div className="space-y-6">
      {/* Decimal Degrees Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">
          Decimal Degrees
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Latitude"
            value={`${lat}°`}
            copyable={true}
          />
          <MetadataField
            label="Longitude"
            value={`${lon}°`}
            copyable={true}
          />
          {showAltitude && (
            <MetadataField
              label="Altitude"
              value={formatAltitude(alt)}
              copyable={true}
            />
          )}
        </div>
      </div>

      {/* DMS Format Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">
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
        <h3 className="text-sm font-semibold text-gray-700 mb-3 border-b pb-2">
          GPS Quality
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Satellites"
            value={gps_satellites_used !== undefined ? gps_satellites_used.toString() : 'N/A'}
          />
          <MetadataField
            label="HDOP"
            value={gps_hdop !== undefined ? gps_hdop.toString() : 'N/A'}
          />
          <MetadataField
            label="PDOP"
            value={gps_pdop !== undefined ? gps_pdop.toString() : 'N/A'}
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
    lat: PropTypes.number,
    lon: PropTypes.number,
    gps_fix_mode: PropTypes.number,
    alt: PropTypes.number,
    gps_satellites_used: PropTypes.number,
    gps_hdop: PropTypes.number,
    gps_pdop: PropTypes.number,
  }),
};

export default LocationTab;
