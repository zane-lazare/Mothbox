import PropTypes from 'prop-types';
import MetadataField from './MetadataField';
import { formatTimestamp } from '../../utils/metadataFormatters';

/**
 * CaptureTab Component
 *
 * Displays comprehensive photo capture metadata including timestamp,
 * exposure settings, ISO, aperture, focal length, and advanced settings.
 *
 * Features:
 * - Formatted timestamp display
 * - Exposure settings (shutter speed, ISO, aperture, focal length)
 * - Advanced settings (white balance, flash status)
 * - Copyable fields for technical values
 * - Empty state handling
 * - Graceful handling of missing/null values
 *
 * @component
 * @example
 * const metadata = {
 *   capture: {
 *     timestamp: '2024-10-15T14:30:00',
 *     exposure_time: '1/500',
 *     iso: 400,
 *     f_number: 'f/2.8',
 *     focal_length: '24mm',
 *     white_balance: 'Auto',
 *     flash: false
 *   }
 * };
 * return <CaptureTab data={metadata} />
 */
function CaptureTab({ data }) {
  // Handle null or undefined data
  if (!data) {
    return (
      <div className="text-gray-500 text-sm">
        No capture data available
      </div>
    );
  }

  const capture = data.capture || {};

  return (
    <div className="space-y-6">
      {/* Basic Capture Information */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Capture Details
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="Timestamp"
            value={formatTimestamp(capture.timestamp)}
            copyable={!!capture.timestamp}
          />
          <MetadataField
            label="Exposure Time"
            value={capture.exposure_time || 'N/A'}
            copyable={!!capture.exposure_time}
          />
          <MetadataField
            label="ISO"
            value={capture.iso !== undefined && capture.iso !== null ? capture.iso.toString() : 'N/A'}
            copyable={capture.iso !== undefined && capture.iso !== null}
          />
          <MetadataField
            label="Aperture"
            value={capture.f_number || 'N/A'}
            copyable={!!capture.f_number}
          />
          <MetadataField
            label="Focal Length"
            value={capture.focal_length || 'N/A'}
            copyable={!!capture.focal_length}
          />
        </div>
      </div>

      {/* Advanced Settings */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-b dark:border-gray-600 pb-2">
          Advanced Settings
        </h3>
        <div className="space-y-2">
          <MetadataField
            label="White Balance"
            value={capture.white_balance || 'N/A'}
            copyable={!!capture.white_balance}
          />
          <MetadataField
            label="Flash"
            value={capture.flash !== undefined && capture.flash !== null
              ? (capture.flash ? 'Fired' : 'Did not fire')
              : 'N/A'}
            copyable={false}
          />
        </div>
      </div>
    </div>
  );
}

CaptureTab.propTypes = {
  /**
   * Full metadata object from backend API
   */
  data: PropTypes.shape({
    capture: PropTypes.shape({
      /** Timestamp string */
      timestamp: PropTypes.string,
      /** Exposure time (e.g., "1/500") */
      exposure_time: PropTypes.string,
      /** F-number (aperture) */
      f_number: PropTypes.number,
      /** ISO sensitivity */
      iso: PropTypes.number,
      /** Focal length (e.g., "24mm") */
      focal_length: PropTypes.string,
      /** White balance setting */
      white_balance: PropTypes.string,
      /** Flash status */
      flash: PropTypes.string,
    }),
  }),
};

export default CaptureTab;
