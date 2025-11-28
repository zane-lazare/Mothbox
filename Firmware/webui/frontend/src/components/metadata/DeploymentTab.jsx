import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatGPSCoordinate, formatDecimalCoordinate, formatAltitude } from '../../utils/metadataFormatters';

/**
 * DeploymentTab Component
 *
 * Displays Mothbox deployment metadata including device information,
 * firmware version, capture type, series details, and GPS location.
 *
 * Features:
 * - Mothbox ID (copyable)
 * - Capture Type (instant, test, scheduled, etc.)
 * - Firmware version (copyable)
 * - Series type (HDR/focus bracket/single)
 * - Series count and index
 * - GPS location with coordinates in decimal and DMS formats
 * - Altitude (for 3D fixes)
 * - GPS quality indicators (satellites, HDOP)
 * - Map link to view location
 * - Empty state handling
 * - Graceful handling of missing fields
 *
 * @component
 * @example
 * const metadata = {
 *   deployment: {
 *     mothbox_id: 'mothbox-backyard',
 *     capture_type: 'instant',
 *     firmware_version: '5',
 *     series_type: 'single',
 *     series_count: null,
 *     series_index: null
 *   },
 *   location: {
 *     latitude: 40.7128,
 *     longitude: -74.0060,
 *     altitude: 10.5,
 *     satellites: 8,
 *     hdop: 1.2
 *   }
 * };
 * return <DeploymentTab data={metadata} />
 */
function DeploymentTab({ data }) {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No deployment data available
      </div>
    );
  }

  const deployment = data.deployment || {};
  const location = data.location || {};
  const {
    mothbox_id,
    capture_type,
    firmware_version,
    series_type,
    series_count,
    series_index,
  } = deployment;

  // Check if location data is valid
  const hasValidGPS = location.latitude !== undefined &&
    location.latitude !== null &&
    location.longitude !== undefined &&
    location.longitude !== null;

  // Format coordinates if available
  let latDMS, lonDMS, mapsUrl;
  if (hasValidGPS) {
    latDMS = formatGPSCoordinate(location.latitude, 'lat');
    lonDMS = formatGPSCoordinate(location.longitude, 'lon');
    mapsUrl = `https://www.google.com/maps?q=${encodeURIComponent(location.latitude)},${encodeURIComponent(location.longitude)}`;
  }

  const showAltitude = location.altitude !== undefined && location.altitude !== null;

  // Format capture type for display
  const formatCaptureType = (type) => {
    if (!type) return 'N/A';
    const types = {
      'instant': 'Instant Capture',
      'test': 'Test Capture',
      'scheduled': 'Scheduled',
      'bracket': 'Focus Bracket',
      'hdr': 'HDR',
    };
    return types[type] || type;
  };

  return (
    <div className="space-y-6">
      {/* Device Info Section */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Device Info
        </h3>
        <div className="space-y-2">
          {/* Mothbox ID */}
          <MetadataField
            label="Mothbox ID"
            value={mothbox_id || 'N/A'}
            copyable={!!mothbox_id}
          />

          {/* Capture Type */}
          <MetadataField
            label="Capture Type"
            value={formatCaptureType(capture_type)}
            copyable={false}
          />

          {/* Firmware Version */}
          <MetadataField
            label="Firmware Version"
            value={firmware_version || 'N/A'}
            copyable={!!firmware_version}
          />
        </div>
      </div>

      {/* Series Info Section - only show if any series data exists */}
      {(series_type !== undefined || (series_count !== null && series_count !== undefined) || (series_index !== null && series_index !== undefined)) && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
            Series Info
          </h3>
          <div className="space-y-2">
            {/* Series Type */}
            <MetadataField
              label="Series Type"
              value={series_type || 'single'}
              copyable={false}
            />

            {/* Series Count */}
            {series_count !== null && series_count !== undefined && (
              <MetadataField
                label="Series Count"
                value={series_count.toString()}
                copyable={false}
              />
            )}

            {/* Series Index */}
            {series_index !== null && series_index !== undefined && (
              <MetadataField
                label="Series Index"
                value={series_index.toString()}
                copyable={false}
              />
            )}
          </div>
        </div>
      )}

      {/* GPS Location Section */}
      {hasValidGPS ? (
        <>
          {/* Decimal Degrees */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
              GPS Location
            </h3>
            <div className="space-y-2">
              <MetadataField
                label="Latitude"
                value={`${formatDecimalCoordinate(location.latitude)}°`}
                copyable={true}
              />
              <MetadataField
                label="Longitude"
                value={`${formatDecimalCoordinate(location.longitude)}°`}
                copyable={true}
              />
              {showAltitude && (
                <MetadataField
                  label="Altitude"
                  value={formatAltitude(location.altitude)}
                  copyable={true}
                />
              )}
            </div>
          </div>

          {/* DMS Format */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
              DMS Format
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

          {/* GPS Quality */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
              GPS Quality
            </h3>
            <div className="space-y-2">
              <MetadataField
                label="Satellites"
                value={location.satellites !== undefined && location.satellites !== null ? location.satellites.toString() : 'N/A'}
              />
              <MetadataField
                label="HDOP"
                value={location.hdop !== undefined && location.hdop !== null ? location.hdop.toString() : 'N/A'}
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
        </>
      ) : (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
            GPS Location
          </h3>
          <div className="text-gray-500 text-sm">
            No GPS information available
          </div>
        </div>
      )}
    </div>
  );
}

DeploymentTab.propTypes = {
  /**
   * Full metadata object from backend API
   */
  data: PropTypes.shape({
    deployment: PropTypes.shape({
      /** Mothbox device identifier */
      mothbox_id: PropTypes.string,
      /** How the photo was captured (instant, test, scheduled, etc.) */
      capture_type: PropTypes.string,
      /** Firmware version string */
      firmware_version: PropTypes.string,
      /** Series type (single, hdr, focus_bracket) */
      series_type: PropTypes.string,
      /** Number of photos in series */
      series_count: PropTypes.number,
      /** Index of this photo in series */
      series_index: PropTypes.number,
    }),
    location: PropTypes.shape({
      /** Latitude in decimal degrees */
      latitude: PropTypes.number,
      /** Longitude in decimal degrees */
      longitude: PropTypes.number,
      /** Altitude in meters (only for 3D fix) */
      altitude: PropTypes.number,
      /** GPS timestamp */
      gps_timestamp: PropTypes.string,
      /** Number of satellites used */
      satellites: PropTypes.number,
      /** Horizontal dilution of precision */
      hdop: PropTypes.number,
    }),
  }),
};

export default DeploymentTab;
